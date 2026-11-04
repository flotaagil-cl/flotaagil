"""Tareas de Celery de las reservas: WhatsApp, vuelos y expiraciones, con reintento exponencial.

- El WhatsApp sale del worker: la respuesta al conductor o al webhook no espera a Twilio. Cada tarea hace un
  intento; si falla por algo transitorio, Celery reintenta con espera creciente. Agotados los reintentos, el
  mensaje queda en FAILED.
- La consulta inicial de un vuelo sigue en la petición, porque el formulario debe responder si el vuelo existe
  (HU-26). Si la API no responde, el vuelo queda sin verificar y `consultar_vuelo` reintenta aquí.
- Las expiraciones (RN-04, RN-06) corren por beat y pueden ejecutarse varias veces sin efectos duplicados.
"""

import logging
from datetime import datetime

from celery import shared_task
from django.db import OperationalError as ErrorDeBase
from django.db import transaction
from django.utils import timezone
from kombu.exceptions import OperationalError as ErrorDeBroker

from apps.aeropuerto.models import Vuelo
from apps.integraciones.notificaciones import EnvioTransitorio, obtener_notificador
from apps.integraciones.vuelos import VuelosNoDisponibles, obtener_consultor_vuelos

from .models import EstadoEntrega, MensajeWhatsapp, Pasajero, Viaje

logger = logging.getLogger(__name__)

ESPERA_ENVIO_S = 2  # 2, 4, 8, 16 y 32 s
REINTENTOS_ENVIO = 5
ESPERA_VUELO_S = 30  # de 30 s a 16 min
REINTENTOS_VUELO = 6


def encolar(tarea, *args) -> None:
    """Sin broker no se puede enviar: queda en el log y no rompe la acción que ya ocurrió."""
    try:
        tarea.delay(*args)
    except ErrorDeBroker:
        logger.exception("No se pudo encolar %s.", tarea.name)


def al_confirmar(tarea, *args) -> None:
    """Encola tras el commit: si la transacción se revierte, no sale nada."""
    transaction.on_commit(lambda: encolar(tarea, *args), robust=True)


def _enviar(tarea, envio) -> None:
    notificador = obtener_notificador()
    notificador.definitivo = tarea.request.retries >= tarea.max_retries
    try:
        envio(notificador)
    except EnvioTransitorio as error:
        raise tarea.retry(exc=error, countdown=ESPERA_ENVIO_S * 2**tarea.request.retries) from error


def _viaje_para_mensaje(viaje_id: int) -> Viaje | None:
    return (
        Viaje.objects.select_related("pasajero", "empresa", "conductor__usuario", "vehiculo")
        .filter(pk=viaje_id)
        .first()
    )


@shared_task(bind=True, max_retries=REINTENTOS_ENVIO)
def enviar_verificacion(self, viaje_id: int, expira_en: str) -> None:
    viaje = _viaje_para_mensaje(viaje_id)
    if viaje is not None:
        _enviar(self, lambda n: n.solicitar_verificacion(viaje, datetime.fromisoformat(expira_en)))


@shared_task(bind=True, max_retries=REINTENTOS_ENVIO)
def enviar_aviso(self, viaje_id: int, tipo: str) -> None:
    viaje = _viaje_para_mensaje(viaje_id)
    if viaje is not None:
        _enviar(self, lambda n: n.avisar(viaje, tipo))


@shared_task(bind=True, max_retries=REINTENTOS_ENVIO)
def enviar_respuesta(self, pasajero_id: int, viaje_id: int | None, texto: str) -> None:
    pasajero = Pasajero.objects.filter(pk=pasajero_id).first()
    viaje = _viaje_para_mensaje(viaje_id) if viaje_id else None
    if pasajero is not None:
        _enviar(self, lambda n: n.responder(pasajero, viaje, texto))


@shared_task(bind=True, max_retries=REINTENTOS_ENVIO)
def enviar_chat(self, mensaje_id: int) -> None:
    """HU-30. Sin SID ni falla: un reintento o una repetición de la tarea no lo envía dos veces."""
    mensaje = (
        MensajeWhatsapp.objects.select_related("pasajero")
        .filter(pk=mensaje_id, proveedor_sid__isnull=True, estado_entrega=EstadoEntrega.QUEUED)
        .first()
    )
    if mensaje is not None:
        _enviar(self, lambda n: n.enviar_mensaje(mensaje))


def encolar_chat(mensaje_id: int) -> None:
    """Sin broker, el mensaje queda en FAILED: el despachador tiene que verlo, no creer que salió."""
    try:
        enviar_chat.delay(mensaje_id)
    except ErrorDeBroker:
        logger.exception("No se pudo encolar el mensaje %s del chat.", mensaje_id)
        MensajeWhatsapp.objects.filter(pk=mensaje_id).update(estado_entrega=EstadoEntrega.FAILED)


@shared_task(bind=True, max_retries=REINTENTOS_VUELO)
def consultar_vuelo(self, vuelo_id: int) -> None:
    """Vuelo que quedó sin verificar porque la API no respondió al registrarlo."""
    vuelo = Vuelo.objects.filter(pk=vuelo_id, ultima_consulta_en__isnull=True).first()
    if vuelo is None:
        return
    try:
        datos = obtener_consultor_vuelos().consultar(vuelo.numero, vuelo.hora_programada)
    except VuelosNoDisponibles as error:
        if self.request.retries >= self.max_retries:
            logger.warning("Vuelo %s sigue sin verificar tras los reintentos: %s", vuelo.numero, error)
            return
        raise self.retry(exc=error, countdown=ESPERA_VUELO_S * 2**self.request.retries) from error
    if datos is None:
        logger.warning("El vuelo %s no aparece en la API: sigue sin verificar.", vuelo.numero)
        return
    Vuelo.objects.filter(pk=vuelo_id, ultima_consulta_en__isnull=True).update(
        hora_programada=datos.hora_programada,
        hora_estimada=datos.hora_estimada,
        estado_vuelo=datos.estado,
        ultima_consulta_en=timezone.now(),
    )


@shared_task(autoretry_for=(ErrorDeBase,), retry_backoff=True, retry_backoff_max=60, max_retries=3)
def expirar_solicitudes() -> int:
    """RN-06."""
    from .expiracion import expirar_pendientes

    return expirar_pendientes()


@shared_task(autoretry_for=(ErrorDeBase,), retry_backoff=True, retry_backoff_max=60, max_retries=3)
def expirar_asignaciones() -> int:
    """RN-04: sin respuesta a los 60 s."""
    from .asignacion import expirar_asignaciones as expirar

    return expirar()
