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

from .models import Usuario

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
