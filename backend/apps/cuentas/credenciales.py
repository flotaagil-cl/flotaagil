"""Credenciales de los usuarios (HU-10, DC-14): contraseña temporal, cambio de contraseña y revocación
de sesiones.

La contraseña temporal se genera aquí, se guarda solo como hash (PBKDF2) y se entrega una vez en la respuesta
al administrador. Nunca va a la auditoría ni a los logs.
"""

import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as ErrorDeDjango
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad

from .models import Rol, Usuario

# Sin caracteres que se confunden al dictarlos o copiarlos a mano: 0/O/o, 1/l/I/i.
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
LARGO = 14
GRUPOS = ("ABCDEFGHJKLMNPQRSTUVWXYZ", "abcdefghjkmnpqrstuvwxyz", "23456789")


def nueva_password_temporal() -> str:
    """14 caracteres del alfabeto sin ambiguos (unos 80 bits), con al menos una mayúscula, una minúscula y un
    dígito."""
    while True:
        password = "".join(secrets.choice(ALFABETO) for _ in range(LARGO))
        if all(any(c in grupo for c in password) for grupo in GRUPOS):
            return password


def revocar_sesiones(usuario: Usuario) -> int:
    """Deja en la lista negra todos los refresh vigentes del usuario (panel y app). Devuelve cuántos."""
    vigentes = OutstandingToken.objects.filter(
        user=usuario, expires_at__gt=timezone.now(), blacklistedtoken__isnull=True
    )
    nuevos = [BlacklistedToken(token=token) for token in vigentes]
    BlacklistedToken.objects.bulk_create(nuevos, ignore_conflicts=True)
    return len(nuevos)


@transaction.atomic
def asignar_password_temporal(usuario: Usuario, *, por: Usuario) -> tuple[str, datetime]:
    """Genera la temporal, obliga a cambiarla, cierra todas las sesiones y lo deja en auditoría (RN-12)."""
    usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
    primera = not usuario.has_usable_password()
    password = nueva_password_temporal()
    usuario.set_password(password)
    usuario.debe_cambiar_password = True
    usuario.password_temporal_vence = timezone.now() + timedelta(hours=settings.PASSWORD_TEMPORAL_HORAS)
    # Una cuenta bloqueada por intentos fallidos parte de cero con la nueva contraseña.
    usuario.intentos_fallidos, usuario.bloqueado_hasta = 0, None
    usuario.save(
        update_fields=[
            "password",
            "debe_cambiar_password",
            "password_temporal_vence",
            "intentos_fallidos",
            "bloqueado_hasta",
        ]
    )
    revocar_sesiones(usuario)
    auditoria.registrar(
        usuario=por,
        entidad=Entidad.USUARIO,
        entidad_id=usuario.pk,
        accion="GENERAR_PASSWORD" if primera else "RESTABLECER_PASSWORD",
    )
    return password, usuario.password_temporal_vence


@transaction.atomic
def cambiar_password(usuario: Usuario, *, actual: str, nueva: str) -> None:
    """El propio usuario cambia su contraseña (la temporal u otra). Cierra todas sus sesiones."""
    usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
    if not usuario.check_password(actual):
        raise ValidationError({"password_actual": ["La contraseña actual no es correcta."]})
    if actual == nueva:
        raise ValidationError({"password_nueva": ["La nueva contraseña debe ser distinta de la actual."]})
    try:
        validate_password(nueva, usuario)
    except ErrorDeDjango as error:
        raise ValidationError({"password_nueva": list(error.messages)}) from error
    usuario.set_password(nueva)
    usuario.debe_cambiar_password = False
    usuario.password_temporal_vence = None
    usuario.save(update_fields=["password", "debe_cambiar_password", "password_temporal_vence"])
    revocar_sesiones(usuario)
    auditoria.registrar(
        usuario=usuario, entidad=Entidad.USUARIO, entidad_id=usuario.pk, accion="CAMBIAR_PASSWORD"
    )


def estado_de_acceso(usuario: Usuario) -> str:
    """SIN_PASSWORD, TEMPORAL, TEMPORAL_VENCIDA o ACTIVA."""
    if not usuario.has_usable_password():
        return "SIN_PASSWORD"
    if usuario.debe_cambiar_password:
        vence = usuario.password_temporal_vence
        return "TEMPORAL_VENCIDA" if vence is not None and vence <= timezone.now() else "TEMPORAL"
    return "ACTIVA"


# --- HU-35: recuperar la contraseña por correo (cuentas web de pasajero y convenio) ---

ROLES_RECUPERABLES = (Rol.PASAJERO, Rol.CONVENIO)


def dentro_del_limite(clave: str, maximo: int) -> bool:
    """HU-41: cuenta un envío en la ventana (`RECUPERAR_VENTANA_MIN`); False si ya se llegó al máximo."""
    from django.core.cache import cache

    ventana = settings.RECUPERAR_VENTANA_MIN * 60
    cache.add(f"limite:{clave}", 0, timeout=ventana)
    try:
        envios = cache.incr(f"limite:{clave}")
    except ValueError:  # la clave venció entre add e incr
        cache.set(f"limite:{clave}", 1, timeout=ventana)
        envios = 1
    return envios <= maximo


def pedir_recuperacion(email: str) -> None:
    """Envía el enlace si el correo es de una cuenta activa de pasajero o convenio. No dice si existe."""
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    from .tareas import al_confirmar_correo

    if not dentro_del_limite(f"recuperar:{email.strip().lower()}", settings.RECUPERAR_MAX_ENVIOS):
        return  # HU-41: misma respuesta 202; no se envía más
    usuario = (
        Usuario.objects.filter(email__iexact=email.strip(), activo=True, rol__in=ROLES_RECUPERABLES)
        .select_related("empresa")
        .first()
    )
    if usuario is None or not usuario.has_usable_password():
        return
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)
    # El enlace lleva la empresa para mostrar su marca en la pantalla de la contraseña nueva.
    enlace = f"{settings.WEB_URL_BASE}/recuperar/{uid}/{token}?empresa={usuario.empresa.slug}"
    al_confirmar_correo(
        usuario.email,
        "Recupera tu contraseña de FlotaÁgil",
        f"Hola {usuario.nombre}:\n\nPara elegir una contraseña nueva abre este enlace (vence en "
        f"{settings.PASSWORD_RESET_TIMEOUT // 60} minutos y sirve una sola vez):\n\n{enlace}\n\n"
        "Si no lo pediste, ignora este correo.\n",
    )


@transaction.atomic
def confirmar_recuperacion(uid: str, token: str, nueva: str) -> None:
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_str
    from django.utils.http import urlsafe_base64_decode

    invalido = ValidationError({"token": ["El enlace no es válido o ya venció. Pide uno nuevo."]})
    try:
        pk = int(force_str(urlsafe_base64_decode(uid)))
    except (TypeError, ValueError, OverflowError):
        raise invalido from None
    usuario = (
        Usuario.objects.select_for_update().filter(pk=pk, activo=True, rol__in=ROLES_RECUPERABLES).first()
    )
    if usuario is None or not default_token_generator.check_token(usuario, token):
        raise invalido
    try:
        validate_password(nueva, usuario)
    except ErrorDeDjango as error:
        raise ValidationError({"password": list(error.messages)}) from error
    usuario.set_password(nueva)  # invalida el token: forma parte de su firma
    usuario.debe_cambiar_password, usuario.password_temporal_vence = False, None
    usuario.intentos_fallidos, usuario.bloqueado_hasta = 0, None
    usuario.save(
        update_fields=[
            "password",
            "debe_cambiar_password",
            "password_temporal_vence",
            "intentos_fallidos",
            "bloqueado_hasta",
        ]
    )
    revocar_sesiones(usuario)
    auditoria.registrar(
        usuario=usuario, entidad=Entidad.USUARIO, entidad_id=usuario.pk, accion="RECUPERAR_PASSWORD"
    )
