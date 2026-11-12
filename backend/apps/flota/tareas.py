"""Tareas de Celery de flota."""

from celery import shared_task

from .retencion import purgar_posiciones


@shared_task
def purgar_posiciones_gps() -> int:
    """RN-15 (DC-48): purga diaria de las posiciones GPS de más de 30 días."""
    return purgar_posiciones()
