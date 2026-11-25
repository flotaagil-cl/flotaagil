"""Tareas de Celery de las cuentas web (HU-33): el correo sale del worker, con reintento exponencial."""

import logging

from celery import shared_task

from apps.integraciones import correo

from . import correo_marca
from .models import Empresa

logger = logging.getLogger(__name__)
ESPERA_CORREO_S = 5  # 5, 10, 20, 40 y 80 s
REINTENTOS_CORREO = 5


@shared_task(bind=True, max_retries=REINTENTOS_CORREO)
def enviar_correo(self, destino: str, asunto: str, texto: str, empresa_id: int | None = None) -> None:
    """Con `empresa_id`, el correo lleva el logo y los colores de esa empresa (CC-27)."""
    try:
        correo.enviar(destino, asunto, texto, **_marca(empresa_id, texto))
    except correo.CorreoTransitorio as error:
        if self.request.retries >= self.max_retries:
            logger.error("No se pudo enviar el correo a %s: %s", correo.enmascarar(destino), error)
            return
        raise self.retry(exc=error, countdown=ESPERA_CORREO_S * 2**self.request.retries) from error


def _marca(empresa_id: int | None, texto: str) -> dict:
    empresa = Empresa.objects.filter(pk=empresa_id).first() if empresa_id else None
    if empresa is None:
        return {}
    logo = correo_marca.leer_logo(empresa)
    return {"html": correo_marca.html_del_correo(empresa, texto, con_logo=logo is not None), "logo": logo}


def al_confirmar_correo(destino: str, asunto: str, texto: str, empresa_id: int | None = None) -> None:
    """Encola el correo tras el commit: si la transacción se revierte, no sale."""
    from apps.reservas.tareas import al_confirmar

    al_confirmar(enviar_correo, destino, asunto, texto, empresa_id)
