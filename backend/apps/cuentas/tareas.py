"""Tareas de Celery de las cuentas web (HU-33): el correo sale del worker, con reintento exponencial."""

import logging

from celery import shared_task

from apps.integraciones import correo

logger = logging.getLogger(__name__)
ESPERA_CORREO_S = 5  # 5, 10, 20, 40 y 80 s
REINTENTOS_CORREO = 5


@shared_task(bind=True, max_retries=REINTENTOS_CORREO)
def enviar_correo(self, destino: str, asunto: str, texto: str) -> None:
    try:
        correo.enviar(destino, asunto, texto)
    except correo.CorreoTransitorio as error:
        if self.request.retries >= self.max_retries:
            logger.error("No se pudo enviar el correo a %s: %s", correo.enmascarar(destino), error)
            return
        raise self.retry(exc=error, countdown=ESPERA_CORREO_S * 2**self.request.retries) from error


def al_confirmar_correo(destino: str, asunto: str, texto: str) -> None:
    """Encola el correo tras el commit: si la transacción se revierte, no sale."""
    from apps.reservas.tareas import al_confirmar

    al_confirmar(enviar_correo, destino, asunto, texto)
