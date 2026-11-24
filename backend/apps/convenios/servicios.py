"""Convenios (HU-11, HU-34). RN-08: desactivar corta el acceso al instante sin afectar el historial.
RN-12: los cambios de estado y de contraseña quedan en auditoría inmutable.

HU-34 (DC-35): la empresa cliente se registra en el portal y queda EN_REVISION con su cuenta (USUARIO de rol
CONVENIO). El administrador la aprueba o la rechaza con motivo, y se le avisa por correo. Puede editar los
datos, desactivar y reactivar, y restablecer la contraseña con una temporal (DC-14). No crea convenios ni
cuentas (decisión del PO del 2026-11-10): los convenios sin cuenta, anteriores a HU-34, quedan como
historial y solo admiten editar los datos y desactivarlos.
"""

import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
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

CAMPOS_EDITABLES = (
    "cliente_nombre",
    "cliente_rut",
    "direccion",
    "encargado_nombre",
    "encargado_telefono",
    "contacto_correo",
    "correos_autorizados",
)


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
    # CC-22 (DC-55): la solicitud pública no tiene cuenta: el resultado va al correo de contacto.
    destino = convenio.usuario.email if convenio.usuario_id else convenio.contacto_correo
    if destino:
        al_confirmar_correo(destino, asunto, texto)


def normalizar_correos(correos) -> list[str]:
    """DC-54: en minúsculas, sin repetidos, en el orden recibido."""
    vistos = []
    for correo in correos or []:
        correo = correo.strip().lower()
        if correo and correo not in vistos:
            vistos.append(correo)
    return vistos


# --- Solicitud pública sin cuenta (HU-53, CC-22) ---


@transaction.atomic
def solicitar_publico(empresa, datos: dict) -> Convenio:
    """Convenio EN_REVISION sin usuario: lo revisan el administrador o el despachador."""
    convenio = Convenio.objects.create(
        empresa=empresa,
        cliente_nombre=datos["cliente_nombre"],
        cliente_rut=datos["cliente_rut"],
        direccion=datos["direccion"],
        encargado_nombre=datos["contacto_nombre"],
        encargado_telefono=datos["contacto_telefono"],
        contacto_correo=datos["contacto_correo"].strip().lower(),
        viajes_estimados_mes=datos["viajes_estimados_mes"],
        correos_autorizados=normalizar_correos(datos.get("correos_autorizados")),
        estado=EstadoConvenio.EN_REVISION,
    )
    auditoria.registrar(
        usuario=None,
        empresa_id=empresa.pk,
        entidad=Entidad.CONVENIO,
        entidad_id=convenio.pk,
        accion="SOLICITUD_PUBLICA",
    )
    return convenio


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
def aprobar(convenio: Convenio, *, usuario, correos_autorizados=None) -> Convenio:
    """HU-53: quien revisa puede ajustar los correos autorizados al aprobar (DC-54)."""
    convenio = _bloquear(convenio)
    _exigir(convenio, EstadoConvenio.EN_REVISION)
    previos = {"estado": EstadoConvenio.EN_REVISION}
    campos = ["estado", "revisado_por", "revisado_en"]
    if correos_autorizados is not None:
        nuevos = normalizar_correos(correos_autorizados)
        if nuevos != convenio.correos_autorizados:
            previos["correos_autorizados"] = convenio.correos_autorizados
            convenio.correos_autorizados = nuevos
            campos.append("correos_autorizados")
    convenio.estado, convenio.revisado_por, convenio.revisado_en = (
        EstadoConvenio.APROBADO,
        usuario,
        timezone.now(),
    )
    convenio.save(update_fields=campos)
    _auditar(usuario, convenio, "APROBACION", previos)
    if admite_clave(convenio):
        # CC-23 (D1): sin módulo de cuentas, la clave se genera al aprobar y va solo al correo de contacto.
        clave = _asignar_clave(convenio)
        _auditar(usuario, convenio, "CAMBIO_CLAVE", {"clave_version": convenio.clave_version - 1})  # RN-12
        como_pedir = texto_como_pedir(convenio, clave)
    elif convenio.usuario_id:
        como_pedir = "Ya puedes pedir viajes iniciando sesión en FlotaÁgil."
    else:
        como_pedir = (
            "Las reservas hechas en el portal con el RUT de tu empresa y un correo autorizado quedan en el "
            "convenio."
        )
    _avisar(
        convenio,
        f"Tu convenio con {convenio.empresa.razon_social} fue aprobado",
        f"Hola {convenio.encargado_nombre}:\n\n{convenio.empresa.razon_social} aprobó el convenio de "
        f"{convenio.cliente_nombre}. {como_pedir}\n",
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
    campos = ["estado"]
    if convenio.clave_hash:
        # CC-23 (DC-74): la clave muere con la desactivación; al reactivar, el administrador genera una nueva.
        convenio.clave_hash, convenio.clave_version = None, convenio.clave_version + 1
        campos += ["clave_hash", "clave_version"]
    convenio.save(update_fields=campos)
    if convenio.usuario_id:
        Usuario.objects.filter(pk=convenio.usuario_id).update(activo=False)
        credenciales.revocar_sesiones(convenio.usuario)
    _auditar(usuario, convenio, "DESACTIVACION", {"estado": EstadoConvenio.APROBADO})  # RN-12
    return convenio


@transaction.atomic
def activar(convenio: Convenio, *, usuario) -> Convenio:
    convenio = _bloquear(convenio)
    _exigir(convenio, EstadoConvenio.INACTIVO)
    if convenio.usuario_id is None and not admite_clave(convenio):
        # Sin cuenta ni clave es historial (anterior a HU-34): una vez desactivado no vuelve. CC-23 (DC-74):
        # el convenio del portal base sí vuelve, sin clave hasta que el administrador genere una nueva.
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


# --- Clave de convenio del portal base (CC-23, DC-74) ---

# Sin caracteres que se confunden al dictarla o copiarla (0/O, 1/I/L).
ALFABETO_CLAVE = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LARGO_CLAVE = 10


def generar_clave() -> str:
    """Aleatoria, en dos bloques de 5 (p. ej. «ABCDE-23456») para leerla sin errores."""
    crudo = "".join(secrets.choice(ALFABETO_CLAVE) for _ in range(LARGO_CLAVE))
    return f"{crudo[:5]}-{crudo[5:]}"


def normalizar_clave(clave: str) -> str:
    """Se compara sin guiones, espacios ni mayúsculas: lo que importa son los 10 caracteres."""
    return "".join(c for c in (clave or "").upper() if c.isalnum())


def clave_correcta(convenio: Convenio, clave: str) -> bool:
    return bool(convenio.clave_hash) and check_password(normalizar_clave(clave), convenio.clave_hash)


def admite_clave(convenio: Convenio) -> bool:
    """D2: solo los convenios sin cuenta de una empresa sin módulo de cuentas, con correo de contacto."""
    return (
        convenio.usuario_id is None and bool(convenio.contacto_correo) and not convenio.empresa.modulo_cuentas
    )


def _asignar_clave(convenio: Convenio) -> str:
    """Guarda solo el hash y sube la versión (invalida los pases anteriores). Devuelve la clave para el
    correo."""
    clave = generar_clave()
    convenio.clave_hash = make_password(normalizar_clave(clave))
    convenio.clave_version += 1
    convenio.clave_generada_en = timezone.now()
    convenio.save(update_fields=["clave_hash", "clave_version", "clave_generada_en"])
    return clave


def texto_como_pedir(convenio: Convenio, clave: str) -> str:
    return (
        "Para pedir viajes con el convenio, entra al portal, elige «Empresa con convenio» e ingresa tu "
        "correo (este, o uno de los autorizados del convenio) y esta clave:\n\n"
        f"    {clave}\n\n"
        f"Portal: {settings.WEB_URL_BASE}/solicitar/{convenio.empresa.slug}\n\n"
        "La clave sirve para todos los correos autorizados. Guárdala: no la volveremos a mostrar. Si se "
        "pierde o se filtra, pide a la empresa de transporte que genere una nueva."
    )


def _exigir_clave(convenio: Convenio) -> None:
    if not admite_clave(convenio):
        raise EstadoNoPermitido(
            "Este convenio no usa clave: tiene cuenta, no tiene correo de contacto o la empresa usa cuentas.",
            code="sin_clave",
        )


@transaction.atomic
def regenerar_clave(convenio: Convenio, *, usuario) -> Convenio:
    """D1: solo el administrador. Genera una clave nueva (también la primera de un convenio anterior a CC-23),
    invalida la anterior y sus pases, y la envía al correo de contacto. Nunca se muestra en el panel."""
    convenio = _bloquear(convenio)
    _exigir(convenio, EstadoConvenio.APROBADO)
    _exigir_clave(convenio)
    version = convenio.clave_version
    clave = _asignar_clave(convenio)
    _auditar(usuario, convenio, "CAMBIO_CLAVE", {"clave_version": version})  # RN-12
    al_confirmar_correo(
        convenio.contacto_correo,
        f"Nueva clave del convenio con {convenio.empresa.razon_social}",
        f"Hola {convenio.encargado_nombre or ''}:\n\n{convenio.empresa.razon_social} generó una clave nueva "
        f"para el convenio de {convenio.cliente_nombre}. La anterior ya no sirve.\n\n"
        f"{texto_como_pedir(convenio, clave)}\n",
    )
    return convenio


@transaction.atomic
def revocar_clave(convenio: Convenio, *, usuario) -> Convenio:
    """D1: solo el administrador. Sin clave, nadie pide con el convenio desde el portal hasta generar otra."""
    convenio = _bloquear(convenio)
    _exigir_clave(convenio)
    if not convenio.clave_hash:
        raise EstadoNoPermitido("El convenio no tiene una clave vigente.", code="sin_clave")
    version = convenio.clave_version
    convenio.clave_hash, convenio.clave_version = None, version + 1
    convenio.save(update_fields=["clave_hash", "clave_version"])
    _auditar(usuario, convenio, "REVOCACION_CLAVE", {"clave_version": version})  # RN-12
    return convenio
