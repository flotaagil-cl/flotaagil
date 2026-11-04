"""Tareas de Celery del aeropuerto: fila virtual (HU-29) y monitoreo de vuelos (HU-27)."""

import logging

from celery import shared_task
from django.core.cache import cache
from django.db import OperationalError

from apps.integraciones.vuelos import VuelosNoDisponibles, obtener_consultor_vuelos

from . import alertas, monitoreo
from .models import Vuelo

logger = logging.getLogger(__name__)

ESPERA_CONSULTA_S = 30  # 30, 60 y 120 s
REINTENTOS_CONSULTA = 3
# Mientras una consulta sigue reintentando, el barrido de cada minuto no lanza otra por el mismo vuelo.
RESERVA_CONSULTA_S = 300


def reservar_consulta(vuelo_id: int) -> bool:
    return cache.add(f"consulta-vuelo-{vuelo_id}", 1, timeout=RESERVA_CONSULTA_S)


def _liberar_consulta(vuelo_id: int) -> None:
    cache.delete(f"consulta-vuelo-{vuelo_id}")


@shared_task(autoretry_for=(OperationalError,), retry_backoff=True, retry_backoff_max=60, max_retries=3)
def revisar_fila() -> int:
    """HU-29: salida tras `tolerancia_fila_min` fuera de la zona."""
    from .fila import revisar

    return revisar()


@shared_task(autoretry_for=(OperationalError,), retry_backoff=True, retry_backoff_max=60, max_retries=3)
def monitorear_vuelos() -> int:
    """HU-27: encola los vuelos a los que les toca consulta. Devuelve cuántos."""
    encolados = 0
    for vuelo in monitoreo.vuelos_por_consultar():
        if reservar_consulta(vuelo.pk):
            consultar_estado_vuelo.delay(vuelo.pk)
            encolados += 1
    return encolados


@shared_task(bind=True, max_retries=REINTENTOS_CONSULTA)
def consultar_estado_vuelo(self, vuelo_id: int) -> None:
    vuelo = Vuelo.objects.filter(pk=vuelo_id).first()
    if vuelo is None:
        _liberar_consulta(vuelo_id)
        return
    try:
        datos = obtener_consultor_vuelos().consultar(vuelo.numero, vuelo.hora_programada)
    except VuelosNoDisponibles as error:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=error, countdown=ESPERA_CONSULTA_S * 2**self.request.retries) from error
        logger.warning("Vuelo %s sin datos tras los reintentos: %s", vuelo.numero, error)
        alertas.sin_datos(vuelo.viaje, vuelo)
        _liberar_consulta(vuelo_id)
        return
    if datos is None:
        logger.warning("Vuelo %s sin datos: no aparece en la API.", vuelo.numero)
        alertas.sin_datos(vuelo.viaje, vuelo)
    else:
        monitoreo.aplicar(vuelo_id, datos)
    _liberar_consulta(vuelo_id)
