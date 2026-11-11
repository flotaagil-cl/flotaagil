"""HU-36 (CC-17, DC-37): el administrador administra los usuarios del panel de su empresa.

Solo ADMINISTRADOR y DESPACHADOR: los conductores tienen su pantalla (HU-10) y las cuentas de convenio y
pasajero no aparecen. Crear y restablecer usan la contraseña temporal de DC-14 (se muestra una vez, vence a
las 72 h y obliga a cambiarla). Desactivar revoca las sesiones al instante.

Reglas: el administrador no se desactiva ni se quita el rol a sí mismo, y la empresa nunca queda sin al
menos un administrador activo. Las operaciones que podrían dejarla sin administrador bloquean la fila de la
EMPRESA, así que dos administradores que se desactivan mutuamente a la vez no la dejan sin ninguno.
"""

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad

from . import credenciales
from .models import Empresa, Rol, Usuario

ROLES = (Rol.ADMINISTRADOR, Rol.DESPACHADOR)
CORREO_USADO = (
    "Ese correo ya tiene una cuenta en FlotaÁgil. El correo es único en todo el sistema: usa otro (PR-15)."
)


class ReglaUsuarios(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "regla_usuarios"
    default_detail = "La operación no está permitida."


def _auditar(por, usuario, accion: str, previos: dict | None = None) -> None:
    auditoria.registrar(
        usuario=por, entidad=Entidad.USUARIO, entidad_id=usuario.pk, accion=accion, datos_previos=previos
    )


def _bloquear(usuario: Usuario) -> Usuario:
    """Bloquea la empresa (serializa la regla del último administrador) y luego el usuario."""
    Empresa.objects.select_for_update().get(pk=usuario.empresa_id)
    return Usuario.objects.select_for_update().get(pk=usuario.pk)


def _otros_administradores_activos(usuario: Usuario) -> bool:
    return (
        Usuario.objects.filter(empresa_id=usuario.empresa_id, rol=Rol.ADMINISTRADOR, activo=True)
        .exclude(pk=usuario.pk)
        .exists()
    )


@transaction.atomic
def crear(empresa, datos: dict, *, por) -> tuple[Usuario, str, object]:
    usuario = Usuario(
        empresa=empresa,
        email=datos["email"].strip().lower(),
        nombre=datos["nombre"].strip(),
        rol=datos["rol"],
    )
    usuario.set_unusable_password()
    try:
        with transaction.atomic():
            usuario.save()
    except IntegrityError as error:
        raise ValidationError({"email": [CORREO_USADO]}) from error
    _auditar(por, usuario, "CREAR", {"rol": usuario.rol})
    password, vence = credenciales.asignar_password_temporal(usuario, por=por)
    return usuario, password, vence


@transaction.atomic
def editar(usuario: Usuario, datos: dict, *, por) -> Usuario:
    usuario = _bloquear(usuario)
    nuevo_rol = datos.get("rol", usuario.rol)
    if nuevo_rol != usuario.rol:
        if usuario.pk == por.pk:
            raise ReglaUsuarios("No puedes cambiar tu propio rol.", code="propio_rol")
        if (
            usuario.rol == Rol.ADMINISTRADOR
            and usuario.activo
            and not _otros_administradores_activos(usuario)
        ):
            raise ReglaUsuarios(
                "La empresa debe tener al menos un administrador activo.", code="ultimo_administrador"
            )
    previos = {
        campo: getattr(usuario, campo)
        for campo in ("nombre", "rol")
        if campo in datos and datos[campo] != getattr(usuario, campo)
    }
    if not previos:
        return usuario
    for campo in previos:
        setattr(usuario, campo, datos[campo])
    usuario.save(update_fields=list(previos))
    if "rol" in previos:
        # El rol va en el token: con el cambio, las sesiones abiertas deben volver a entrar.
        credenciales.revocar_sesiones(usuario)
    _auditar(por, usuario, "EDITAR", previos)
    return usuario


@transaction.atomic
def cambiar_habilitacion(usuario: Usuario, habilitar: bool, *, por) -> Usuario:
    usuario = _bloquear(usuario)
    if usuario.activo == habilitar:
        return usuario
    if not habilitar:
        if usuario.pk == por.pk:
            raise ReglaUsuarios("No puedes desactivar tu propia cuenta.", code="propia_cuenta")
        if usuario.rol == Rol.ADMINISTRADOR and not _otros_administradores_activos(usuario):
            raise ReglaUsuarios(
                "La empresa debe tener al menos un administrador activo.", code="ultimo_administrador"
            )
    usuario.activo = habilitar
    usuario.save(update_fields=["activo"])
    if not habilitar:
        credenciales.revocar_sesiones(usuario)
    _auditar(por, usuario, "HABILITAR" if habilitar else "DESHABILITAR", {"activo": not habilitar})
    return usuario


def restablecer(usuario: Usuario, *, por) -> tuple[str, object]:
    """DC-14: temporal nueva; cierra sus sesiones. Queda en auditoría (RESTABLECER_PASSWORD)."""
    return credenciales.asignar_password_temporal(usuario, por=por)
