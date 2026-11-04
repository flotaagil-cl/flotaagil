"""Tareas de Celery de la fila del aeropuerto."""

from celery import shared_task
from django.db import OperationalError


@shared_task(autoretry_for=(OperationalError,), retry_backoff=True, retry_backoff_max=60, max_retries=3)
def revisar_fila() -> int:
    """HU-29: salida tras `tolerancia_fila_min` fuera de la zona."""
    from .fila import revisar

    return revisar()
