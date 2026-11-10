"""Convenios (HU-11, HU-34). RN-08: desactivar corta el acceso al instante sin afectar el historial.
RN-12: los cambios de estado y de contraseña quedan en auditoría inmutable.

HU-34 (DC-35): la empresa cliente se registra en el portal y queda EN_REVISION con su cuenta (USUARIO de rol
CONVENIO). El administrador la aprueba o la rechaza con motivo, y se le avisa por correo. Puede editar los
datos, desactivar y reactivar, y restablecer la contraseña con una temporal (DC-14). No crea convenios ni
cuentas (decisión del PO del 2026-11-10): los convenios sin cuenta, anteriores a HU-34, quedan como
historial y solo admiten editar los datos y desactivarlos.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as ErrorDeDjango
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad
from apps.cuentas import credenciales
from apps.cuentas.models import Rol, Usuario
from apps.cuentas.tareas import al_confirmar_correo

from .models import Convenio, EstadoConvenio

CAMPOS_EDITABLES = ("cliente_nombre", "cliente_rut", "direccion", "encargado_nombre", "encargado_telefono")


class EstadoNoPermitido(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "estado_convenio"
    default_detail = "El convenio no admite esa acción en su estado actual."


def _auditar(usuario, convenio: Convenio, accion: str, datos_previos=None, motivo=None) -> None:
    auditoria.registrar(
        usuario=usuario,
        entidad=Entidad.CONVENIO,
        entidad_id=convenio.pk,
        accion=accion,
        motivo=motivo,
        datos_previos=datos_previos,
    )


def _bloquear(convenio: Convenio) -> Convenio:
    return (
        Convenio.objects.select_for_update(of=("self",))
        .select_related("usuario", "empresa")
        .get(pk=convenio.pk)
    )


def _exigir(convenio: Convenio, *estados: str) -> None:
    if convenio.estado not in estados:
        raise EstadoNoPermitido(f"El convenio está {convenio.get_estado_display().lower()}.")


def _avisar(convenio: Convenio, asunto: str, texto: str) -> None:
    if convenio.usuario_id:
        al_confirmar_correo(convenio.usuario.email, asunto, texto)


# --- Registro público (HU-34) ---


@transaction.atomic
def registrar(empresa, datos: dict) -> Convenio:
    """Crea el convenio EN_REVISION y la cuenta del encargado. El correo debe ser nuevo en el sistema."""
    usuario = Usuario(
        empresa=empresa,
        email=datos["email"].strip().lower(),
        nombre=datos["encargado_nombre"],
        rol=Rol.CONVENIO,
    )
    try:
        validate_password(datos["password"], usuario)
    except ErrorDeDjango as error:
        raise ValidationError({"password": list(error.messages)}) from error
    usuario.set_password(datos["password"])
    try:
        with transaction.atomic():
            usuario.save()
    except IntegrityError as error:
        raise ValidationError(
            {"email": ["No se pudo registrar con ese correo. Si ya tienes cuenta, inicia sesión."]}
        ) from error
    convenio = Convenio.objects.create(
        empresa=empresa,
        cliente_nombre=datos["cliente_nombre"],
        cliente_rut=datos["cliente_rut"],
        direccion=datos["direccion"],
        encargado_nombre=datos["encargado_nombre"],
        encargado_telefono=datos["encargado_telefono"],
        estado=EstadoConvenio.EN_REVISION,
        usuario=usuario,
    )
    _auditar(usuario, convenio, "REGISTRO")
    return convenio


# --- Administración (HU-11, HU-34) ---


@transaction.atomic
def editar(convenio: Convenio, datos: dict, *, usuario) -> Convenio:
    convenio = _bloquear(convenio)
    datos = {campo: valor for campo, valor in datos.items() if campo in CAMPOS_EDITABLES}
    previos = {campo: getattr(convenio, campo) for campo in datos if getattr(convenio, campo) != datos[campo]}
    if not previos:
        return convenio
    for campo, valor in datos.items():
        setattr(convenio, campo, valor)
    convenio.save(update_fields=list(previos))
    _auditar(usuario, convenio, "EDICION", previos)
    return convenio


@transaction.atomic
def aprobar(convenio: Convenio, *, usuario) -> Convenio:
    convenio = _bloquear(convenio)
    _exigir(convenio, EstadoConvenio.EN_REVISION)
    convenio.estado, convenio.revisado_por, convenio.revisado_en = (
        EstadoConvenio.APROBADO,
        usuario,
        timezone.now(),
    )
    convenio.save(update_fields=["estado", "revisado_por", "revisado_en"])
    _auditar(usuario, convenio, "APROBACION", {"estado": EstadoConvenio.EN_REVISION})
    _avisar(
        convenio,
        f"Tu convenio con {convenio.empresa.razon_social} fue aprobado",
        f"Hola {convenio.encargado_nombre}:\n\n{convenio.empresa.razon_social} aprobó el convenio de "
        f"{convenio.cliente_nombre}. Ya puedes pedir viajes iniciando sesión en FlotaÁgil.\n",
    )
    return convenio


@transaction.atomic
def rechazar(convenio: Convenio, *, motivo: str, usuario) -> Convenio:
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError({"motivo": ["Indica el motivo del rechazo."]})
    convenio = _bloquear(convenio)
    _exigir(convenio, EstadoConvenio.EN_REVISION)
    convenio.estado, convenio.motivo_rechazo = EstadoConvenio.RECHAZADO, motivo[:200]
    convenio.revisado_por, convenio.revisado_en = usuario, timezone.now()
    convenio.save(update_fields=["estado", "motivo_rechazo", "revisado_por", "revisado_en"])
    _auditar(usuario, convenio, "RECHAZO", {"estado": EstadoConvenio.EN_REVISION}, motivo=motivo[:200])
    _avisar(
        convenio,
        f"Tu solicitud de convenio con {convenio.empresa.razon_social}",
        f"Hola {convenio.encargado_nombre}:\n\n{convenio.empresa.razon_social} no aprobó el convenio de "
        f"{convenio.cliente_nombre}.\n\nMotivo: {motivo[:200]}\n",
    )
    return convenio


@transaction.atomic
def desactivar(convenio: Convenio, *, usuario) -> Convenio:
    """RN-08: la cuenta queda deshabilitada y sus sesiones cerradas al instante; el historial no cambia."""
    convenio = _bloquear(convenio)
    _exigir(convenio, EstadoConvenio.APROBADO)
    convenio.estado = EstadoConvenio.INACTIVO
    convenio.save(update_fields=["estado"])
    if convenio.usuario_id:
        Usuario.objects.filter(pk=convenio.usuario_id).update(activo=False)
        credenciales.revocar_sesiones(convenio.usuario)
    _auditar(usuario, convenio, "DESACTIVACION", {"estado": EstadoConvenio.APROBADO})  # RN-12
    return convenio


@transaction.atomic
def activar(convenio: Convenio, *, usuario) -> Convenio:
    convenio = _bloquear(convenio)
    _exigir(convenio, EstadoConvenio.INACTIVO)
    if convenio.usuario_id is None:
        # Sin cuenta es historial (anterior a HU-34): una vez desactivado no vuelve.
        raise EstadoNoPermitido(
            "Este convenio no tiene cuenta: es historial y no se reactiva.", code="sin_cuenta"
        )
    convenio.estado = EstadoConvenio.APROBADO
    convenio.save(update_fields=["estado"])
    if convenio.usuario_id:
        Usuario.objects.filter(pk=convenio.usuario_id).update(activo=True)
    _auditar(usuario, convenio, "ACTIVACION", {"estado": EstadoConvenio.INACTIVO})  # RN-12
    return convenio


@transaction.atomic
def restablecer_password(convenio: Convenio, *, usuario) -> tuple[str, object]:
    """DC-14: temporal de un solo uso que obliga a cambiarla y cierra las sesiones. Se muestra una vez."""
    convenio = _bloquear(convenio)
    if convenio.usuario_id is None:
        raise EstadoNoPermitido("Este convenio no tiene cuenta.", code="sin_cuenta")
    password, vence = credenciales.asignar_password_temporal(convenio.usuario, por=usuario)
    _auditar(usuario, convenio, "CAMBIO_CLAVE")  # RN-12
    return password, vence
