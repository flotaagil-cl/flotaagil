"""RN-06: el pasajero confirma o cancela su solicitud del portal respondiendo por WhatsApp (HU-20).
RN-09: después puede cancelar por WhatsApp solo mientras no tenga conductor asignado (HU-21).

La respuesta llega al webhook (o al comando `simular_whatsapp` en desarrollo) y se procesa una sola vez por
`MessageSid` (idempotencia). La reserva se identifica por el mensaje al que responde
(`OriginalRepliedMessageSid`); si no viene, por la solicitud pendiente más reciente de ese teléfono o por su
única reserva en curso. Con varias reservas en curso y sin esa referencia no se cancela ninguna: se le pide
que cite el mensaje. Los cambios de estado pasan por la máquina de estados (actor PASAJERO).

HU-24: un número del 1 al 5 es la respuesta a la encuesta del viaje citado o, sin cita, del último viaje
finalizado sin calificar. Solo vale dentro de `encuesta_vigencia_horas` (DC-19): más tarde es conversación.
"""

import logging
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.integraciones.notificaciones import enmascarar_telefono, obtener_notificador

from . import estados
from .models import (
    Actor,
    Calificacion,
    DireccionMensaje,
    EstadoEntrega,
    EstadoViaje,
    HistorialEstado,
    MensajeWhatsapp,
    OrigenCancelacion,
    Pasajero,
    TipoMensaje,
    Viaje,
)

logger = logging.getLogger(__name__)

MOTIVO_CANCELACION = "Cancelada por el pasajero por WhatsApp (RN-06)."
MOTIVO_CANCELACION_RN09 = "Cancelada por el pasajero por WhatsApp, sin conductor asignado (RN-09)."
CONFIRMAR = {"confirmar", "confirmo", "si", "sí"}
CANCELAR = {"cancelar", "cancelo"}
# «No» solo responde a la pregunta de la verificación: fuera de ella es conversación, no una cancelación.
CANCELAR_SOLO_PENDIENTE = {"no"}
EN_CURSO = (
    EstadoViaje.SOLICITADO,
    EstadoViaje.ASIGNADO,
    EstadoViaje.ACEPTADO,
    EstadoViaje.EN_CAMINO,
    EstadoViaje.EN_ZONA,
    EstadoViaje.PASAJERO_A_BORDO,
)

RESPUESTAS = {
    "confirmada": "¡Listo! Tu solicitud quedó confirmada. Te avisaremos por aquí cuando asignemos un "
    "conductor.",
    "cancelada": "Tu solicitud quedó cancelada. Si necesitas un viaje, puedes pedir otro cuando quieras.",
    "ya_confirmada": "Tu viaje ya está confirmado. Te avisaremos por aquí cómo avanza.",
    "con_conductor": "Tu viaje ya tiene conductor asignado, así que no se puede cancelar por aquí. "
    "Comunícate con la central.",
    "varias": "Tienes más de un viaje reservado. Para cancelar uno, responde citando el mensaje de ese viaje "
    "o comunícate con la central.",
    "calificada": "¡Gracias por tu calificación!",
    "ya_calificada": "Ya habíamos registrado tu calificación de este viaje. ¡Gracias!",
    "no_vigente": "Esa solicitud ya no está vigente (se anuló o ya fue respondida). Si necesitas un viaje, "
    "pide uno nuevo.",
}


def _accion(boton: str, texto: str, viaje: Viaje | None) -> str | None:
    pendiente = viaje is not None and viaje.estado == EstadoViaje.PENDIENTE_CONFIRMACION
    for valor in (boton, texto):
        palabra = (valor or "").strip().lower()
        if palabra in CONFIRMAR:
            return "confirmar"
        if palabra in CANCELAR or (pendiente and palabra in CANCELAR_SOLO_PENDIENTE):
            return "cancelar"
    return None


def _puntaje(boton: str, texto: str) -> int | None:
    for valor in (boton, texto):
        palabra = (valor or "").strip()
        if palabra in {"1", "2", "3", "4", "5"}:
            return int(palabra)
    return None


def _encuesta_vigente(viaje: Viaje, ahora) -> bool:
    fin = HistorialEstado.objects.filter(viaje=viaje, estado_nuevo=EstadoViaje.FINALIZADO).first()
    horas = viaje.empresa.configuracion.encuesta_vigencia_horas
    return fin is not None and ahora - fin.creado_en <= timedelta(hours=horas)


def _viaje_a_calificar(pasajeros, original_sid: str | None) -> Viaje | None:
    """El viaje citado, si está finalizado; sin cita, el último finalizado sin calificar. Siempre vigente."""
    ahora = timezone.now()
    finalizados = Viaje.objects.filter(pasajero__in=pasajeros, estado=EstadoViaje.FINALIZADO).select_related(
        "empresa__configuracion"
    )
    if original_sid:
        citado = MensajeWhatsapp.objects.filter(proveedor_sid=original_sid, pasajero__in=pasajeros).first()
        viaje = finalizados.filter(pk=citado.viaje_id).first() if citado else None
        if viaje:
            return viaje if _encuesta_vigente(viaje, ahora) else None
    for viaje in finalizados.filter(calificacion__isnull=True).order_by("-id")[:5]:
        if _encuesta_vigente(viaje, ahora):
            return viaje
    return None


def _calificar(viaje: Viaje, puntaje: int) -> str:
    _, creada = Calificacion.objects.get_or_create(viaje=viaje, defaults={"puntaje": puntaje})
    return "calificada" if creada else "ya_calificada"  # vale la primera respuesta


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
    pendiente = (
        Viaje.objects.filter(pasajero__in=pasajeros, estado=EstadoViaje.PENDIENTE_CONFIRMACION)
        .order_by("-creado_en")
        .first()
    )
    if pendiente:
        return pendiente
    en_curso = list(Viaje.objects.filter(pasajero__in=pasajeros, estado__in=EN_CURSO)[:2])
    return en_curso[0] if len(en_curso) == 1 else None


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

    texto = datos.get("Body") or datos.get("ButtonText") or ""
    puntaje = _puntaje(datos.get("ButtonPayload", ""), texto)
    a_calificar = _viaje_a_calificar(pasajeros, datos.get("OriginalRepliedMessageSid")) if puntaje else None
    viaje = a_calificar or _viaje_respondido(pasajeros, datos.get("OriginalRepliedMessageSid"))
    pasajero = viaje.pasajero if viaje else pasajeros[0]
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

    if a_calificar:
        resultado = _calificar(a_calificar, puntaje)
        obtener_notificador().responder(pasajero, viaje, RESPUESTAS[resultado])
        return resultado

    accion = _accion(datos.get("ButtonPayload", ""), texto, viaje)
    if accion is None:
        return "sin_accion"  # conversación libre: la atiende el despachador (HU-30)
    if viaje is None:
        varias = Viaje.objects.filter(pasajero__in=pasajeros, estado__in=EN_CURSO).exists()
        resultado = "varias" if varias else "no_vigente"
    elif viaje.estado == EstadoViaje.PENDIENTE_CONFIRMACION:
        resultado = _aplicar(viaje, accion)
    else:
        resultado = _despues_de_confirmar(viaje, accion)
    obtener_notificador().responder(pasajero, viaje, RESPUESTAS[resultado])
    return resultado


def _despues_de_confirmar(viaje: Viaje, accion: str) -> str:
    if viaje.estado not in EN_CURSO:
        return "no_vigente"
    if accion == "confirmar":
        return "ya_confirmada"
    if viaje.estado != EstadoViaje.SOLICITADO:
        return "con_conductor"  # RN-09
    try:
        estados.transicionar(
            viaje,
            EstadoViaje.CANCELADO,
            desde=EstadoViaje.SOLICITADO,
            actor=Actor.PASAJERO,
            motivo_cancelacion=MOTIVO_CANCELACION_RN09,
            origen_cancelacion=OrigenCancelacion.PASAJERO,
        )
    except estados.TransicionInvalida:
        viaje.refresh_from_db()  # lo asignaron o lo cancelaron en el mismo instante
        return "con_conductor" if viaje.estado in EN_CURSO else "no_vigente"
    return "cancelada"


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
