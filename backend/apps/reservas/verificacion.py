"""RN-06: el pasajero confirma o cancela su solicitud del portal respondiendo por WhatsApp (HU-20).

La respuesta llega al webhook (o al comando `simular_whatsapp` en desarrollo) y se procesa una sola vez por
`MessageSid` (idempotencia). La reserva se identifica por el mensaje al que responde
(`OriginalRepliedMessageSid`) o, si no viene, por la solicitud pendiente más reciente de ese teléfono.
Los cambios de estado pasan por la máquina de estados (actor PASAJERO).
"""

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.integraciones.notificaciones import enmascarar_telefono, obtener_notificador

from . import estados
from .models import (
    Actor,
    DireccionMensaje,
    EstadoEntrega,
    EstadoViaje,
    MensajeWhatsapp,
    OrigenCancelacion,
    Pasajero,
    TipoMensaje,
    Viaje,
)

logger = logging.getLogger(__name__)

MOTIVO_CANCELACION = "Cancelada por el pasajero por WhatsApp (RN-06)."
CONFIRMAR = {"confirmar", "confirmo", "si", "sí"}
CANCELAR = {"cancelar", "cancelo", "no"}

RESPUESTAS = {
    "confirmada": "¡Listo! Tu solicitud quedó confirmada. Te avisaremos por aquí cuando asignemos un "
    "conductor.",
    "cancelada": "Tu solicitud quedó cancelada. Si necesitas un viaje, puedes pedir otro cuando quieras.",
    "no_vigente": "Esa solicitud ya no está vigente (se anuló o ya fue respondida). Si necesitas un viaje, "
    "pide uno nuevo.",
}


def _accion(boton: str, texto: str) -> str | None:
    for valor in (boton, texto):
        palabra = (valor or "").strip().lower()
        if palabra in CONFIRMAR:
            return "confirmar"
        if palabra in CANCELAR:
            return "cancelar"
    return None


def _telefono(direccion: str) -> str:
    return (direccion or "").removeprefix("whatsapp:")


def _viaje_respondido(pasajeros, original_sid: str | None) -> Viaje | None:
    if original_sid:
        mensaje = (
            MensajeWhatsapp.objects.filter(proveedor_sid=original_sid, pasajero__in=pasajeros)
            .select_related("viaje")
            .first()
        )
        if mensaje and mensaje.viaje:
            return mensaje.viaje
    # Sin referencia: la solicitud pendiente más reciente de ese teléfono (en cualquiera de sus empresas).
    return (
        Viaje.objects.filter(pasajero__in=pasajeros, estado=EstadoViaje.PENDIENTE_CONFIRMACION)
        .order_by("-creado_en")
        .first()
    )


def procesar_entrante(datos: dict) -> str:
    """Procesa un mensaje entrante de Twilio (parámetros del webhook). Devuelve qué pasó, para el log y las
    pruebas: repetido, desconocido, sin_accion, confirmada, cancelada o no_vigente."""
    sid = datos.get("MessageSid") or ""
    if sid and MensajeWhatsapp.objects.filter(proveedor_sid=sid).exists():
        return "repetido"
    telefono = _telefono(datos.get("From", ""))
    pasajeros = list(Pasajero.objects.filter(telefono=telefono))
    if not pasajeros:
        logger.info("WhatsApp de un número desconocido (%s): se ignora.", enmascarar_telefono(telefono))
        return "desconocido"

    viaje = _viaje_respondido(pasajeros, datos.get("OriginalRepliedMessageSid"))
    pasajero = viaje.pasajero if viaje else pasajeros[0]
    texto = datos.get("Body") or datos.get("ButtonText") or ""
    try:
        with transaction.atomic():
            MensajeWhatsapp.objects.create(
                pasajero=pasajero,
                viaje=viaje,
                direccion=DireccionMensaje.ENTRANTE,
                tipo=TipoMensaje.SESION,
                cuerpo=texto[:1024],
                proveedor_sid=sid or None,
                estado_entrega=EstadoEntrega.DELIVERED,
            )
    except IntegrityError:
        return "repetido"  # el mismo webhook llegó dos veces a la vez

    accion = _accion(datos.get("ButtonPayload", ""), texto)
    if accion is None:
        return "sin_accion"  # conversación libre: la atiende el despachador (HU-30)
    if viaje is None or viaje.estado != EstadoViaje.PENDIENTE_CONFIRMACION:
        resultado = "no_vigente"
    else:
        resultado = _aplicar(viaje, accion)
    obtener_notificador().responder(pasajero, viaje, RESPUESTAS[resultado])
    return resultado


def _aplicar(viaje: Viaje, accion: str) -> str:
    try:
        if accion == "confirmar":
            estados.transicionar(
                viaje, EstadoViaje.SOLICITADO, desde=EstadoViaje.PENDIENTE_CONFIRMACION, actor=Actor.PASAJERO
            )
            Pasajero.objects.filter(pk=viaje.pasajero_id).update(verificado_en=timezone.now())
            return "confirmada"
        estados.transicionar(
            viaje,
            EstadoViaje.CANCELADO,
            desde=EstadoViaje.PENDIENTE_CONFIRMACION,
            actor=Actor.PASAJERO,
            motivo_cancelacion=MOTIVO_CANCELACION,
            origen_cancelacion=OrigenCancelacion.PASAJERO,
        )
        return "cancelada"
    except estados.TransicionInvalida:
        return "no_vigente"  # expiró o se respondió en el mismo instante


ORDEN_ENTREGA = [EstadoEntrega.QUEUED, EstadoEntrega.SENT, EstadoEntrega.DELIVERED, EstadoEntrega.READ]
ESTADOS_TWILIO = {
    "queued": EstadoEntrega.QUEUED,
    "accepted": EstadoEntrega.QUEUED,
    "sending": EstadoEntrega.QUEUED,
    "sent": EstadoEntrega.SENT,
    "delivered": EstadoEntrega.DELIVERED,
    "read": EstadoEntrega.READ,
    "failed": EstadoEntrega.FAILED,
    "undelivered": EstadoEntrega.FAILED,
}


def procesar_estado(datos: dict) -> bool:
    """Callback de estado de Twilio. Solo avanza (los callbacks pueden llegar desordenados).
    Devuelve True si cambió."""
    nuevo = ESTADOS_TWILIO.get((datos.get("MessageStatus") or "").lower())
    if nuevo is None:
        return False
    with transaction.atomic():
        mensaje = (
            MensajeWhatsapp.objects.select_for_update().filter(proveedor_sid=datos.get("MessageSid")).first()
        )
        if mensaje is None or mensaje.estado_entrega == nuevo:
            return False
        actual = mensaje.estado_entrega
        if (
            actual in ORDEN_ENTREGA
            and nuevo in ORDEN_ENTREGA
            and ORDEN_ENTREGA.index(nuevo) < ORDEN_ENTREGA.index(actual)
        ):
            return False
        mensaje.estado_entrega = nuevo
        mensaje.save(update_fields=["estado_entrega"])
    return True
