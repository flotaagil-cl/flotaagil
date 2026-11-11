"""RN-15: las posiciones GPS se conservan 30 días (`RETENCION_POSICIONES_DIAS`). La purga diaria las
borra por lotes para no bloquear la tabla mientras la app sigue enviando posiciones."""

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import PosicionGps

logger = logging.getLogger(__name__)

LOTE = 5000


def limite(ahora=None):
    """Instante desde el que se conservan las posiciones: todo lo anterior se borra."""
    return (ahora or timezone.now()) - timedelta(days=settings.RETENCION_POSICIONES_DIAS)


def purgar_posiciones(ahora=None, lote: int = LOTE) -> int:
    """Borra las posiciones registradas antes del límite de retención. Devuelve cuántas borró."""
    corte = limite(ahora)
    total = 0
    while True:
        ids = list(PosicionGps.objects.filter(registrada_en__lt=corte).values_list("pk", flat=True)[:lote])
        if not ids:
            break
        borradas, _ = PosicionGps.objects.filter(pk__in=ids).delete()
        total += borradas
    logger.info("Retención GPS (RN-15): %s posiciones anteriores a %s borradas.", total, corte.isoformat())
    return total
