"""Reglas comunes de las solicitudes web: límites, vuelo y hora de recogida.

Desde HU-40 (CC-18) no hay pedido sin cuenta: las usan el pasajero con cuenta
(`/api/mi-cuenta/solicitudes/`) y la empresa en convenio (`/api/mi-convenio/solicitudes/`)."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import Throttled, ValidationError

from apps.reservas import servicios as reservas
from apps.reservas.models import Canal, Viaje


class LimiteIP(Throttled):
    """429 por IP (throttling de DRF). El `code` permite al portal explicar el caso sin leer el texto."""

    default_code = "limite_ip"
    default_detail = (
        "Se enviaron demasiadas solicitudes desde esta conexión. Espera un momento e intenta de nuevo."
    )


class LimiteTelefono(Throttled):
    """429 por teléfono: demasiadas solicitudes con el mismo número en la ventana."""

    default_code = "limite_telefono"
    default_detail = "Ya enviaste varias solicitudes con este número. Espera unos minutos e intenta de nuevo."


def _verificar_limite_telefono(empresa, telefono: str) -> None:
    """Máximo de solicitudes por número y empresa en la ventana (alineado con RN-06: 3 cada 15 min)."""
    desde = timezone.now() - settings.PORTAL_VENTANA_TELEFONO
    recientes = Viaje.objects.filter(
        empresa=empresa, canal=Canal.WEB, pasajero__telefono=telefono, creado_en__gte=desde
    ).count()
    if recientes >= settings.PORTAL_MAX_SOLICITUDES_POR_TELEFONO:
        raise LimiteTelefono(wait=settings.PORTAL_VENTANA_TELEFONO.total_seconds())


def _hora_de_recogida(datos: dict, config):
    """RN-17: desde el aeropuerto, si no viene la hora de recogida es la llegada + margen.

    VUELO no distingue nacional de internacional (DC-12): se usa el margen nacional.
    """
    if "recogida_en" in datos:
        return datos["recogida_en"]
    return datos["vuelo"]["hora_llegada"] + timedelta(minutes=config.margen_nacional_min)


def vuelo_y_recogida(empresa, datos: dict) -> tuple[dict | None, object]:
    """Vuelo verificado y hora de recogida, que debe respetar la anticipación mínima. También para HU-25."""
    config = empresa.configuracion
    vuelo_verificado = None
    if datos.get("vuelo"):
        # HU-26: la recogida calculada (RN-17) usa la hora de llegada confirmada por la API de vuelos.
        vuelo_verificado = reservas.verificar_vuelo(
            {"numero": datos["vuelo"]["numero"], "hora_programada": datos["vuelo"]["hora_llegada"]}
        )
        datos = {**datos, "vuelo": {**datos["vuelo"], "hora_llegada": vuelo_verificado["hora_programada"]}}
    recogida = _hora_de_recogida(datos, config)
    minimo = timezone.now() + timedelta(minutes=config.anticipacion_minima_min)
    if recogida < minimo:
        minutos = config.anticipacion_minima_min
        raise ValidationError(
            {"recogida_en": [f"La recogida debe ser al menos {minutos} minutos después de ahora."]}
        )
    return vuelo_verificado, recogida
