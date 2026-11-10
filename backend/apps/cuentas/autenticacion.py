"""Inicio de sesión con bloqueo tras intentos fallidos, emisión y renovación de tokens JWT."""

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import update_last_login
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Rol, Usuario

ROLES_PANEL = frozenset({Rol.ADMINISTRADOR, Rol.DESPACHADOR})
# HU-33: el inicio de sesión web es uno solo para el panel, el convenio y el pasajero. Las vistas del panel
# siguen exigiendo ROLES_PANEL; las del convenio y del pasajero, su rol.
ROLES_WEB = ROLES_PANEL | {Rol.CONVENIO, Rol.PASAJERO}
ROLES_APP = frozenset({Rol.CONDUCTOR})

# Canal de la sesión: claim que solo emite el servidor en el login.
# Cada refresh rechaza los tokens del otro canal.
CANAL_PANEL = "panel"
CANAL_APP = "app"
ROLES_POR_CANAL = {CANAL_PANEL: ROLES_WEB, CANAL_APP: ROLES_APP}

MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos."


class CuentaBloqueada(AuthenticationFailed):
    default_detail = "La cuenta está bloqueada temporalmente por intentos fallidos. Intenta más tarde."
    default_code = "cuenta_bloqueada"


def _registrar_fallo(usuario: Usuario) -> None:
    """Suma el intento fallido bajo el bloqueo de la fila del usuario, como el acceso del convenio (HU-25):
    dos intentos simultáneos no pueden leer el mismo conteo y contar como uno.

    Se lee el conteo de la base después del bloqueo, no el que traía `usuario`. Si otro intento ya bloqueó la
    cuenta mientras esperábamos, el bloqueo no se extiende. La transacción termina aquí: el error que lanza
    `autenticar` después no la deshace.
    """
    with transaction.atomic():
        fila = (
            Usuario.objects.select_for_update(of=("self",), no_key=True)
            .only("intentos_fallidos", "bloqueado_hasta")
            .get(pk=usuario.pk)
        )
        ahora = timezone.now()
        if fila.bloqueado_hasta is not None and fila.bloqueado_hasta <= ahora:
            fila.intentos_fallidos, fila.bloqueado_hasta = 0, None  # El bloqueo venció: se parte de cero.
        if fila.bloqueado_hasta is None:
            fila.intentos_fallidos = min(fila.intentos_fallidos + 1, settings.LOGIN_MAX_INTENTOS)
            if fila.intentos_fallidos >= settings.LOGIN_MAX_INTENTOS:
                fila.bloqueado_hasta = ahora + settings.LOGIN_BLOQUEO
            fila.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
    usuario.intentos_fallidos, usuario.bloqueado_hasta = fila.intentos_fallidos, fila.bloqueado_hasta


def _bloqueo_vigente(usuario: Usuario) -> bool:
    if usuario.bloqueado_hasta is None:
        return False
    if usuario.bloqueado_hasta > timezone.now():
        return True
    # El bloqueo venció: se parte de cero.
    Usuario.objects.filter(pk=usuario.pk).update(intentos_fallidos=0, bloqueado_hasta=None)
    usuario.intentos_fallidos, usuario.bloqueado_hasta = 0, None
    return False


def autenticar(email: str, password: str, roles_permitidos: frozenset[str]) -> Usuario:
    """Valida credenciales, aplica el bloqueo y el rol del canal (panel o app)."""
    usuario = Usuario.objects.select_related("empresa").filter(email__iexact=email.strip()).first()
    if usuario is None:
        raise AuthenticationFailed(MENSAJE_CREDENCIALES, code="credenciales_invalidas")
    if _bloqueo_vigente(usuario):
        raise CuentaBloqueada()
    if not usuario.check_password(password):
        _registrar_fallo(usuario)
        if usuario.bloqueado_hasta:
            raise CuentaBloqueada()
        raise AuthenticationFailed(MENSAJE_CREDENCIALES, code="credenciales_invalidas")
    if not usuario.activo and usuario.rol == Rol.PASAJERO and hasattr(usuario, "cuenta_pasajero"):
        # HU-35: la cuenta se activa al confirmar el teléfono por WhatsApp.
        raise AuthenticationFailed(
            "Confirma tu cuenta respondiendo el WhatsApp que te enviamos.", code="cuenta_sin_confirmar"
        )
    if not usuario.activo or not usuario.empresa.activa:
        raise AuthenticationFailed("La cuenta está deshabilitada.", code="cuenta_deshabilitada")
    if usuario.rol not in roles_permitidos:
        raise PermissionDenied("Este acceso no corresponde a tu rol.", code="rol_no_permitido")
    vence = usuario.password_temporal_vence
    if usuario.debe_cambiar_password and vence is not None and vence <= timezone.now():
        # DC-14: la temporal no se usó a tiempo; el administrador debe generar otra.
        raise AuthenticationFailed(
            "La contraseña temporal venció. Pide al administrador de tu empresa una nueva.",
            code="password_temporal_vencida",
        )

    if usuario.intentos_fallidos:
        Usuario.objects.filter(pk=usuario.pk).update(intentos_fallidos=0)
        usuario.intentos_fallidos = 0
    update_last_login(None, usuario)
    return usuario


def ahora() -> datetime:
    """Hora de emisión y renovación de los tokens. Las pruebas la reemplazan para controlar el reloj."""
    return timezone.now()


def emitir_tokens(usuario: Usuario, canal: str) -> RefreshToken:
    """Refresh con el rol, la empresa y el canal como claims; el access los hereda.

    En el panel agrega `sesion_inicio` (epoch del login), que se conserva al rotar y fija el tope absoluto
    de la sesión (JWT_SESION_MAX): el refresh del login no dura más que ese tope.
    """
    momento = ahora()
    refresh = RefreshToken.for_user(usuario)
    refresh["rol"] = usuario.rol
    refresh["empresa_id"] = usuario.empresa_id
    refresh["canal"] = canal
    vida = api_settings.REFRESH_TOKEN_LIFETIME
    if canal == CANAL_PANEL:
        refresh["sesion_inicio"] = int(momento.timestamp())
        vida = min(vida, settings.JWT_SESION_MAX)
    refresh.current_time = momento  # el access del login se calcula desde aquí
    refresh.set_iat(at_time=momento)
    refresh.set_exp(from_time=momento, lifetime=vida)
    return refresh


def vida_cookie(refresh: RefreshToken) -> int:
    """Max-Age de la cookie: lo que le queda al refresh."""
    return max(int(refresh["exp"]) - int(refresh["iat"]), 0)


class SesionRechazada(Exception):
    """El refresh no sirve. `codigo` es sesion_invalida o sesion_expirada (tope del panel)."""

    def __init__(self, codigo: str = "sesion_invalida"):
        super().__init__(codigo)
        self.codigo = codigo


@dataclass(frozen=True)
class Renovacion:
    access: str
    refresh: str
    max_age: int


def renovar(refresh: str, canal: str) -> Renovacion:
    """Rota el refresh del canal si sigue vigente y el usuario puede usarlo; si no, SesionRechazada.

    Las renovaciones del mismo usuario quedan en serie con un bloqueo de su fila: dos peticiones con el mismo
    refresh no pueden ganar las dos (simplejwt solo revisa la lista negra con un SELECT antes de escribirla).
    El bloqueo es FOR NO KEY UPDATE: choca con otra renovación, pero no con las inserciones que solo
    referencian al usuario por FK (como OutstandingToken), que toman KEY SHARE.
    """
    momento = ahora()
    try:
        # Firma, exp (con el reloj de simplejwt) y primera revisión de la lista negra.
        token = RefreshToken(refresh)
    except TokenError as error:
        raise SesionRechazada() from error
    if token.get("canal") != canal:
        # Incluye los tokens emitidos antes de existir el claim: esas sesiones quedan invalidadas.
        raise SesionRechazada()

    restante = None
    if canal == CANAL_PANEL:
        inicio = token.get("sesion_inicio")
        if not isinstance(inicio, int):
            raise SesionRechazada()
        restante = datetime.fromtimestamp(inicio, tz=UTC) + settings.JWT_SESION_MAX - momento
        if restante <= timedelta(0):
            raise SesionRechazada("sesion_expirada")

    with transaction.atomic():
        usuario = (
            Usuario.objects.select_for_update(of=("self",), no_key=True)
            .select_related("empresa")
            .filter(pk=token.get(api_settings.USER_ID_CLAIM))
            .first()
        )
        if (
            usuario is None
            or not usuario.activo
            or not usuario.empresa.activa
            or usuario.rol not in ROLES_POR_CANAL[canal]
        ):
            raise SesionRechazada()
        return _rotar(token, momento, restante)


def _rotar(token: RefreshToken, momento: datetime, restante: timedelta | None) -> Renovacion:
    """Rotación equivalente a TokenRefreshSerializer.validate() de simplejwt 5.5.1, con dos diferencias:
    la lista negra se revisa otra vez después del bloqueo y la vida de los tokens se limita a `restante`.

    IMPORTANTE: simplejwt está fijada en 5.5.1 (requirements.txt). Cualquier cambio de versión obliga a
    revisar esta función contra el serializer de la nueva versión.

    Se llama dentro de transaction.atomic() con la fila del usuario bloqueada (select_for_update, no_key).
    """
    try:
        # Mientras esperábamos el bloqueo otra petición pudo rotar este mismo refresh.
        token.check_blacklist()
    except TokenError as error:
        raise SesionRechazada() from error

    vida_access = api_settings.ACCESS_TOKEN_LIFETIME
    vida_refresh = api_settings.REFRESH_TOKEN_LIFETIME
    if restante is not None:
        vida_access = min(vida_access, restante)
        vida_refresh = min(vida_refresh, restante)

    access = token.access_token
    access.set_iat(at_time=momento)
    access.set_exp(from_time=momento, lifetime=vida_access)

    token.blacklist()
    token.set_jti()
    token.set_exp(from_time=momento, lifetime=vida_refresh)
    token.set_iat(at_time=momento)
    token.outstand()
    return Renovacion(access=str(access), refresh=str(token), max_age=math.ceil(vida_refresh.total_seconds()))
