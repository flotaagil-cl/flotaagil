"""HU-35 (CC-16, DC-36): cuenta web opcional del pasajero. El invitado sigue igual.

- Registro por empresa: nombre, teléfono, correo y contraseña. El usuario (rol PASAJERO) queda inactivo y se
  le pide por WhatsApp responder «CONFIRMAR CUENTA» (mismo canal que HU-20). Al confirmar se activa y se liga
  al PASAJERO de ese teléfono en la empresa: recién ahí ve sus reservas, también las de invitado.
- Con la cuenta activa, sus reservas no se verifican otra vez; se mantiene el límite por teléfono del portal.
- Cancela solo sin conductor asignado (RN-09).
- HU-45 (DC-50): el pasajero edita su nombre y su WhatsApp; el número nuevo queda pendiente hasta que
  responda «CONFIRMAR CUENTA» y, si no responde a tiempo, el cambio se descarta. Eliminar la cuenta la
  anonimiza: el USUARIO queda inactivo, sin clave ni sesiones y con un correo no utilizable; la fila
  CUENTA_PASAJERO se borra (no queda nada que guardar en ella); el PASAJERO pasa a «Pasajero eliminado» con
  teléfono NULL y sus mensajes quedan sin contenido. Los viajes, pagos, historial y auditoría se conservan.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as ErrorDeDjango
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad
from apps.cuentas import credenciales
from apps.cuentas.models import Rol, Usuario
from apps.integraciones.notificaciones import AVISO_CONFIRMACION

from . import avisos, estados, tareas
from . import servicios as reservas
from .models import (
    Actor,
    Canal,
    CuentaPasajero,
    EstadoViaje,
    MensajeWhatsapp,
    OrigenCancelacion,
    Pasajero,
    Viaje,
)

PALABRA_CONFIRMAR = "confirmar cuenta"
CANCELABLES = (EstadoViaje.PENDIENTE_CONFIRMACION, EstadoViaje.SOLICITADO)  # RN-09: sin conductor asignado
# HU-45: con un viaje en uno de estos estados la cuenta no se puede eliminar hasta que termine o se cancele.
VIAJE_ACTIVO = (
    EstadoViaje.SOLICITADO,
    EstadoViaje.ASIGNADO,
    EstadoViaje.ACEPTADO,
    EstadoViaje.EN_CAMINO,
    EstadoViaje.EN_ZONA,
    EstadoViaje.PASAJERO_A_BORDO,
)
CUERPO_ELIMINADO = "[eliminado]"
MOTIVO_ELIMINAR = "Cuenta eliminada por el titular"


class SinCuentaActiva(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "cuenta_sin_confirmar"
    default_detail = "Confirma tu cuenta respondiendo el WhatsApp que te enviamos."


class NoCancelable(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "con_conductor"
    default_detail = (
        "Tu viaje ya tiene conductor asignado: no se puede cancelar aquí. Comunícate con la central."
    )


class PrivacidadPendiente(PermissionDenied):
    """DC-44: la cuenta debe aceptar el aviso de privacidad vigente antes de pedir."""

    default_code = "aceptar_privacidad"
    default_detail = "Antes de pedir, acepta el aviso de privacidad."


def texto_confirmacion(cuenta: CuentaPasajero) -> str:
    return (
        f"Hola {cuenta.nombre}, creaste una cuenta en {cuenta.empresa.razon_social}. Para activarla responde "
        f"CONFIRMAR CUENTA. Si no fuiste tú, ignora este mensaje."
    )


def vence_en(cuenta: CuentaPasajero):
    """El mensaje de activación vale `expiracion_verificacion_min` desde el último envío (HU-41)."""
    desde = cuenta.reenviada_en or cuenta.creada_en
    return desde + timedelta(minutes=cuenta.empresa.configuracion.expiracion_verificacion_min)


class TelefonoEnUso(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "telefono_en_uso"
    default_detail = "Ese WhatsApp ya está asociado a otra cuenta de esta empresa."


class ViajeActivo(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "viaje_activo"
    default_detail = "Tienes un viaje en curso. Podrás eliminar tu cuenta cuando termine o lo canceles."


def texto_cambio_telefono(cuenta: CuentaPasajero) -> str:
    return (
        f"Hola {cuenta.nombre}, pediste usar este número en tu cuenta de {cuenta.empresa.razon_social}. Para "
        f"confirmarlo responde CONFIRMAR CUENTA. Si no fuiste tú, ignora este mensaje."
    )


def telefono_pendiente_vigente(cuenta: CuentaPasajero, ahora=None) -> str | None:
    """HU-45: el WhatsApp nuevo por confirmar, o None si no hay o ya venció (el cambio se descarta)."""
    if not cuenta.telefono_pendiente or cuenta.telefono_pendiente_en is None:
        return None
    vence = cuenta.telefono_pendiente_en + timedelta(
        minutes=cuenta.empresa.configuracion.expiracion_verificacion_min
    )
    return cuenta.telefono_pendiente if vence > (ahora or timezone.now()) else None


def _telefono_de_otra_cuenta(cuenta: CuentaPasajero, telefono: str) -> bool:
    return (
        CuentaPasajero.objects.filter(empresa=cuenta.empresa, telefono=telefono, confirmada_en__isnull=False)
        .exclude(pk=cuenta.pk)
        .exists()
    )


class CredencialesPendientes(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "cuenta_no_encontrada"
    default_detail = "No encontramos una cuenta por activar con ese correo y contraseña."


class CuentaYaActiva(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "cuenta_activa"
    default_detail = "Tu cuenta ya está activa: ingresa con tu correo y contraseña."


class LimiteReenvios(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "limite_reenvio"
    default_detail = "Ya te reenviamos el mensaje varias veces. Espera unos minutos e intenta de nuevo."


def cuenta_por_credenciales(empresa, email: str, password: str) -> CuentaPasajero:
    """HU-41: la cuenta de esta empresa con ese correo y contraseña (la del alta). Sin decir cuál falló."""
    usuario = Usuario.objects.filter(email__iexact=email.strip(), rol=Rol.PASAJERO).first()
    cuenta = getattr(usuario, "cuenta_pasajero", None) if usuario else None
    if cuenta is None or cuenta.empresa_id != empresa.pk or not usuario.check_password(password):
        raise CredencialesPendientes()
    return cuenta


def estado_activacion(empresa, email: str, password: str) -> dict:
    cuenta = cuenta_por_credenciales(empresa, email, password)
    return {"activa": cuenta.confirmada_en is not None, "telefono": cuenta.telefono}


@transaction.atomic
def reenviar_activacion(empresa, email: str, password: str, telefono: str | None = None) -> CuentaPasajero:
    """HU-41: reenvía «CONFIRMAR CUENTA», opcionalmente a un número corregido, con límite por cuenta."""
    from apps.cuentas.credenciales import dentro_del_limite

    cuenta = cuenta_por_credenciales(empresa, email, password)
    cuenta = CuentaPasajero.objects.select_for_update().select_related("empresa").get(pk=cuenta.pk)
    if cuenta.confirmada_en is not None:
        raise CuentaYaActiva()
    if not dentro_del_limite(f"activacion:{cuenta.pk}", settings.ACTIVACION_MAX_REENVIOS):
        raise LimiteReenvios()
    campos = ["reenviada_en"]
    if telefono and telefono != cuenta.telefono:
        cuenta.telefono = telefono
        campos.append("telefono")
    cuenta.reenviada_en = timezone.now()
    cuenta.save(update_fields=campos)
    pasajero = reservas.obtener_pasajero(empresa, nombre=cuenta.nombre, telefono=cuenta.telefono)
    tareas.al_confirmar(tareas.enviar_respuesta, pasajero.pk, None, texto_confirmacion(cuenta))
    return cuenta


@transaction.atomic
def registrar(empresa, datos: dict) -> CuentaPasajero:
    """Crea la cuenta pendiente y envía el WhatsApp. Si el correo ya tiene una cuenta pendiente de esta
    empresa, la reemplaza (otro teléfono o un mensaje vencido); cualquier otro uso del correo responde
    400."""
    email = datos["email"].strip().lower()
    existente = Usuario.objects.filter(email__iexact=email).select_related("cuenta_pasajero").first()
    if existente is not None:
        cuenta = getattr(existente, "cuenta_pasajero", None)
        if (
            existente.rol != Rol.PASAJERO
            or cuenta is None
            or cuenta.confirmada_en
            or cuenta.empresa_id != empresa.pk
        ):
            raise ValidationError(
                {"email": ["No se pudo crear la cuenta con ese correo. Si ya tienes una, inicia sesión."]}
            )
        usuario = existente
    else:
        usuario = Usuario(empresa=empresa, email=email, rol=Rol.PASAJERO, activo=False)
    usuario.nombre = datos["nombre"]
    try:
        validate_password(datos["password"], usuario)
    except ErrorDeDjango as error:
        raise ValidationError({"password": list(error.messages)}) from error
    usuario.set_password(datos["password"])
    try:
        with transaction.atomic():
            usuario.save()
    except IntegrityError as error:
        raise ValidationError({"email": ["No se pudo crear la cuenta con ese correo."]}) from error
    CuentaPasajero.objects.filter(usuario=usuario).delete()
    cuenta = CuentaPasajero.objects.create(
        usuario=usuario,
        empresa=empresa,
        nombre=datos["nombre"],
        telefono=datos["telefono"],
        # DC-44: la casilla del alta es la aceptación única (fecha y versión del aviso).
        privacidad_aceptada_en=timezone.now(),
        privacidad_version=settings.AVISO_PRIVACIDAD_VERSION,
    )
    # El mensaje necesita un PASAJERO (MENSAJE_WHATSAPP.pasajero_id). Se crea como invitado si no existía; la
    # cuenta no lo ve hasta confirmar.
    pasajero = reservas.obtener_pasajero(empresa, nombre=datos["nombre"], telefono=datos["telefono"])
    tareas.al_confirmar(tareas.enviar_respuesta, pasajero.pk, None, texto_confirmacion(cuenta))
    return cuenta


def confirmar_por_whatsapp(telefono: str, texto: str) -> str | None:
    """Desde el webhook (HU-20). Devuelve el resultado si el mensaje era «CONFIRMAR CUENTA», o None."""
    if (texto or "").strip().lower() != PALABRA_CONFIRMAR:
        return None
    ahora = timezone.now()
    with transaction.atomic():
        cuentas = list(
            CuentaPasajero.objects.select_for_update(of=("self",))
            .select_related("empresa__configuracion", "usuario")
            .filter(telefono=telefono, confirmada_en__isnull=True)
        )
        vigentes = [c for c in cuentas if vence_en(c) > ahora]
        cambios = [
            c
            for c in CuentaPasajero.objects.select_for_update(of=("self",))
            .select_related("empresa__configuracion", "usuario", "pasajero")
            .filter(telefono_pendiente=telefono, confirmada_en__isnull=False)
            if telefono_pendiente_vigente(c, ahora)
        ]
        confirmados = [c for c in cambios if _aplicar_telefono_nuevo(c, ahora)]
        if confirmados and not vigentes:
            return "telefono_confirmado"
        if not vigentes:
            return "cuenta_no_vigente"
        for cuenta in vigentes:
            if CuentaPasajero.objects.filter(
                empresa=cuenta.empresa, telefono=telefono, confirmada_en__isnull=False
            ).exists():
                continue  # ese teléfono ya tiene cuenta en la empresa
            pasajero, _ = Pasajero.objects.get_or_create(
                empresa=cuenta.empresa, telefono=telefono, defaults={"nombre": cuenta.nombre}
            )
            Pasajero.objects.filter(pk=pasajero.pk).update(verificado_en=ahora)
            cuenta.pasajero, cuenta.confirmada_en = pasajero, ahora
            cuenta.save(update_fields=["pasajero", "confirmada_en"])
            Usuario.objects.filter(pk=cuenta.usuario_id).update(activo=True)
            auditoria.registrar(
                usuario=cuenta.usuario,
                entidad=Entidad.USUARIO,
                entidad_id=cuenta.usuario_id,
                accion="CONFIRMAR_CUENTA",
            )
    return "cuenta_confirmada"


def _aplicar_telefono_nuevo(cuenta: CuentaPasajero, ahora) -> bool:
    """HU-45: el WhatsApp nuevo respondió. La cuenta y su PASAJERO pasan al número nuevo. Si ese número ya
    era de un invitado de la empresa (por ejemplo, el que se creó para enviar la confirmación), es la misma
    persona: sus viajes y mensajes pasan al PASAJERO de la cuenta y el invitado se borra."""
    nuevo = cuenta.telefono_pendiente
    cuenta.telefono_pendiente, cuenta.telefono_pendiente_en = None, None
    if _telefono_de_otra_cuenta(cuenta, nuevo):
        cuenta.save(update_fields=["telefono_pendiente", "telefono_pendiente_en"])
        return False
    propio = cuenta.pasajero
    otro = (
        Pasajero.objects.select_for_update()
        .filter(empresa=cuenta.empresa, telefono=nuevo)
        .exclude(pk=propio.pk)
        .first()
    )
    if otro is not None:
        Viaje.objects.filter(pasajero=otro).update(pasajero=propio)
        MensajeWhatsapp.objects.filter(pasajero=otro).update(pasajero=propio)
        otro.delete()
    Pasajero.objects.filter(pk=propio.pk).update(telefono=nuevo, verificado_en=ahora)
    cuenta.telefono = nuevo
    cuenta.save(update_fields=["telefono", "telefono_pendiente", "telefono_pendiente_en"])
    auditoria.registrar(
        usuario=cuenta.usuario,
        entidad=Entidad.USUARIO,
        entidad_id=cuenta.usuario_id,
        accion="CONFIRMAR_TELEFONO",
    )
    return True


@transaction.atomic
def actualizar_perfil(usuario, datos: dict) -> CuentaPasajero:
    """HU-45: el nombre cambia al tiro (cuenta, PASAJERO y USUARIO); un WhatsApp nuevo queda pendiente y se le
    envía «CONFIRMAR CUENTA». Volver a escribir el número actual descarta el cambio pendiente."""
    from apps.cuentas.credenciales import dentro_del_limite

    cuenta = cuenta_activa(usuario)
    cuenta = (
        CuentaPasajero.objects.select_for_update(of=("self",))
        .select_related("empresa__configuracion", "pasajero")
        .get(pk=cuenta.pk)
    )
    cambios = []
    nombre = datos.get("nombre")
    if nombre is not None and nombre != cuenta.nombre:
        cuenta.nombre = nombre
        cuenta.save(update_fields=["nombre"])
        Pasajero.objects.filter(pk=cuenta.pasajero_id).update(nombre=nombre)
        Usuario.objects.filter(pk=usuario.pk).update(nombre=nombre)
        cambios.append("nombre")
    telefono = datos.get("telefono")
    if telefono == cuenta.telefono and cuenta.telefono_pendiente:
        cuenta.telefono_pendiente, cuenta.telefono_pendiente_en = None, None
        cuenta.save(update_fields=["telefono_pendiente", "telefono_pendiente_en"])
        cambios.append("telefono_pendiente_descartado")
    elif telefono and telefono != cuenta.telefono:
        if _telefono_de_otra_cuenta(cuenta, telefono):
            raise TelefonoEnUso()
        if not dentro_del_limite(f"cambio_telefono:{cuenta.pk}", settings.ACTIVACION_MAX_REENVIOS):
            raise LimiteReenvios()
        cuenta.telefono_pendiente, cuenta.telefono_pendiente_en = telefono, timezone.now()
        cuenta.save(update_fields=["telefono_pendiente", "telefono_pendiente_en"])
        # MENSAJE_WHATSAPP necesita un PASAJERO: el del número nuevo se crea como invitado si no existía.
        destino = reservas.obtener_pasajero(cuenta.empresa, nombre=cuenta.nombre, telefono=telefono)
        tareas.al_confirmar(tareas.enviar_respuesta, destino.pk, None, texto_cambio_telefono(cuenta))
        cambios.append("telefono_pendiente")
    if cambios:
        # Solo qué cambió: el nombre o el número anteriores son datos personales y la auditoría se conserva.
        auditoria.registrar(
            usuario=usuario,
            entidad=Entidad.USUARIO,
            entidad_id=usuario.pk,
            accion="EDITAR_PERFIL",
            datos_previos={"campos": cambios},
        )
    return cuenta


def privacidad_vigente(cuenta: CuentaPasajero) -> bool:
    """DC-44: la cuenta aceptó la versión vigente del aviso de privacidad."""
    return cuenta.privacidad_version == settings.AVISO_PRIVACIDAD_VERSION and bool(
        cuenta.privacidad_aceptada_en
    )


def debe_aceptar_privacidad(usuario) -> bool:
    """DC-44: pasajero con cuenta que no aceptó el aviso vigente (cuentas antiguas o versión nueva)."""
    if usuario.rol != Rol.PASAJERO:
        return False
    cuenta = CuentaPasajero.objects.filter(usuario=usuario).first()
    return cuenta is not None and not privacidad_vigente(cuenta)


@transaction.atomic
def aceptar_privacidad(usuario) -> CuentaPasajero:
    """DC-44: registra la aceptación de la versión vigente y la deja en el PASAJERO de la cuenta."""
    cuenta = CuentaPasajero.objects.select_for_update().get(usuario=usuario)
    ahora = timezone.now()
    cuenta.privacidad_aceptada_en, cuenta.privacidad_version = ahora, settings.AVISO_PRIVACIDAD_VERSION
    cuenta.save(update_fields=["privacidad_aceptada_en", "privacidad_version"])
    if cuenta.pasajero_id:
        Pasajero.objects.filter(pk=cuenta.pasajero_id).update(opt_in_en=ahora, privacidad_aceptada_en=ahora)
    auditoria.registrar(
        usuario=usuario,
        entidad=Entidad.USUARIO,
        entidad_id=usuario.pk,
        accion="ACEPTAR_PRIVACIDAD",
        datos_previos={"version": cuenta.privacidad_version},
    )
    return cuenta


def cuenta_activa(usuario) -> CuentaPasajero:
    cuenta = (
        CuentaPasajero.objects.select_related("pasajero", "empresa__configuracion")
        .filter(usuario=usuario)
        .first()
    )
    if cuenta is None or cuenta.confirmada_en is None:
        raise SinCuentaActiva()
    return cuenta


def reservas_de(cuenta: CuentaPasajero):
    return Viaje.objects.filter(pasajero=cuenta.pasajero).order_by("-recogida_en", "-id")


def solicitar(cuenta: CuentaPasajero, datos: dict, *, usuario) -> tuple[Viaje, dict]:
    """Sin verificación (el teléfono se confirmó al crear la cuenta). Mantiene el límite por teléfono."""
    from apps.portal.servicios import _verificar_limite_telefono, validar_capacidad, vuelo_y_recogida

    if not privacidad_vigente(cuenta):
        raise PrivacidadPendiente()
    empresa = cuenta.empresa
    validar_capacidad(empresa, datos.get("pasajeros", 1))  # DC-43
    _verificar_limite_telefono(empresa, cuenta.pasajero.telefono)
    vuelo, recogida = vuelo_y_recogida(empresa, datos)
    with transaction.atomic():
        viaje = reservas.crear_viaje(
            empresa=empresa,
            datos={
                "pasajero": {"nombre": cuenta.pasajero.nombre, "telefono": cuenta.pasajero.telefono},
                "sentido": datos["sentido"],
                "origen_dir": datos["origen_dir"],
                "destino_dir": datos["destino_dir"],
                "recogida_en": recogida,
                "vuelo": vuelo,
                # HU-39 (DC-42).
                "pasajeros": datos.get("pasajeros", 1),
                "maletas": datos.get("maletas", 0),
                "vuelo_salida": datos.get("vuelo_salida"),
            },
            canal=Canal.WEB,
            estado_inicial=EstadoViaje.SOLICITADO,
            actor=Actor.PASAJERO,
            usuario=usuario,
        )
        # DC-44: el pedido no vuelve a aceptar; el PASAJERO lleva la aceptación de la cuenta.
        aceptada = cuenta.privacidad_aceptada_en
        Pasajero.objects.filter(pk=cuenta.pasajero_id).update(
            opt_in_en=aceptada, privacidad_aceptada_en=aceptada
        )
        avisos.programar(viaje.pk, AVISO_CONFIRMACION)  # HU-21
    return viaje, {
        "estado": viaje.estado,
        "recogida_en": viaje.recogida_en,
        "expira_en": None,
        "mensaje": (
            "Tu solicitud quedó registrada. Te avisaremos por WhatsApp cuando la central asigne un conductor."
        ),
    }


# HU-44: motivos que el pasajero elige al cancelar desde su cuenta (quedan en el texto del motivo).
MOTIVOS_CANCELACION = {
    "CAMBIO_DE_PLANES": "Cambié de planes",
    "VUELO_CANCELADO": "Mi vuelo se canceló",
    "OTRO": "Otro motivo",
}


def cancelar(cuenta: CuentaPasajero, viaje_id: int, *, usuario, motivo: str | None = None) -> Viaje:
    viaje = reservas_de(cuenta).filter(pk=viaje_id).first()
    if viaje is None:
        from django.http import Http404

        raise Http404
    if viaje.estado not in CANCELABLES:
        raise NoCancelable()
    try:
        return estados.transicionar(
            viaje,
            EstadoViaje.CANCELADO,
            actor=Actor.PASAJERO,
            usuario=usuario,
            motivo_cancelacion=(
                f"Cancelada por el pasajero desde su cuenta: {MOTIVOS_CANCELACION[motivo]}."
                if motivo in MOTIVOS_CANCELACION
                else "Cancelada por el pasajero desde su cuenta."
            ),
            origen_cancelacion=OrigenCancelacion.PASAJERO,
        )
    except estados.TransicionInvalida as error:
        raise NoCancelable() from error


@transaction.atomic
def eliminar(usuario) -> None:
    """HU-45 (DC-50): anonimiza la cuenta del titular. Con un viaje activo responde 409 (`viaje_activo`).

    - USUARIO: inactivo, correo `eliminado-<id>@invalid`, clave inutilizable y sesiones revocadas.
    - CUENTA_PASAJERO: se borra; lo único que guardaba eran datos personales (nombre, teléfono, fechas).
    - PASAJERO: «Pasajero eliminado» y teléfono NULL.
    - MENSAJE_WHATSAPP: sin contenido; quedan fecha, tipo y estado.
    - VIAJE, PAGO_VIAJE, HISTORIAL_ESTADO y AUDITORIA se conservan; la auditoría registra la eliminación.
    """
    usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
    cuenta = CuentaPasajero.objects.select_for_update().filter(usuario=usuario).first()
    pasajero_id = cuenta.pasajero_id if cuenta else None
    if pasajero_id and Viaje.objects.filter(pasajero_id=pasajero_id, estado__in=VIAJE_ACTIVO).exists():
        raise ViajeActivo()
    CuentaPasajero.objects.filter(usuario=usuario).delete()
    usuario.set_unusable_password()
    usuario.email = f"eliminado-{usuario.pk}@invalid"
    usuario.nombre = "Cuenta eliminada"
    usuario.activo = False
    usuario.save(update_fields=["password", "email", "nombre", "activo"])
    credenciales.revocar_sesiones(usuario)
    if pasajero_id:
        Pasajero.objects.filter(pk=pasajero_id).update(nombre=Pasajero.NOMBRE_ELIMINADO, telefono=None)
        MensajeWhatsapp.objects.filter(pasajero_id=pasajero_id).update(cuerpo=CUERPO_ELIMINADO)
    auditoria.registrar(
        usuario=usuario,
        entidad=Entidad.USUARIO,
        entidad_id=usuario.pk,
        accion="ELIMINAR_CUENTA",
        motivo=MOTIVO_ELIMINAR,
        datos_previos={"pasajero_id": pasajero_id} if pasajero_id else None,
    )
