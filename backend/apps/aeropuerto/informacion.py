"""HU-69: información de vuelos para el panel y la app. Solo lee la base: nunca consulta la API de vuelos.

- Llegadas (VUELO, monitoreado por HU-27): recogida sugerida = llegada (estimada o programada) + margen
  nacional o internacional de la empresa (RN-17).
- Salidas (viaje al aeropuerto, HU-39): no se monitorean; «debe estar en el aeropuerto» = despegue menos la
  antelación nacional o internacional de la empresa (DC-42). El viaje no guarda el número del vuelo de salida
  (DC-69).
"""

from datetime import datetime, time, timedelta

from django.db.models import F, Q
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.reservas.models import EstadoViaje, Sentido, TipoVuelo, Viaje

from .models import EstadoVuelo, Vuelo
from .monitoreo import es_internacional, eta_de, margen_de


def recogida_sugerida(vuelo: Vuelo, configuracion):
    return eta_de(vuelo) + margen_de(vuelo, configuracion)


def en_aeropuerto_a_las(viaje: Viaje, configuracion):
    """Hora a la que el pasajero debe estar en el aeropuerto; None si no es una salida con hora de vuelo."""
    if viaje.sentido != Sentido.HACIA_AEROPUERTO or viaje.vuelo_salida_en is None:
        return None
    minutos = (
        configuracion.antelacion_vuelo_internacional_min
        if viaje.vuelo_salida_tipo == TipoVuelo.INTERNACIONAL
        else configuracion.antelacion_vuelo_nacional_min
    )
    return viaje.vuelo_salida_en - timedelta(minutes=minutos)


def datos_del_vuelo(vuelo: Vuelo, configuracion) -> dict:
    """Campos calculados de una llegada (se agregan al VUELO serializado)."""
    return {
        "internacional": es_internacional(vuelo.origen_icao) if vuelo.origen_icao else None,
        "margen_min": int(margen_de(vuelo, configuracion).total_seconds() // 60),
        "recogida_sugerida": recogida_sugerida(vuelo, configuracion),
    }


def vuelos_del_dia(empresa_id: int, dia=None):
    """Viajes de aeropuerto del día (hora de Chile), sin los cancelados, ordenados por la hora del vuelo."""
    dia = dia or timezone.localdate()
    inicio = timezone.make_aware(datetime.combine(dia, time.min))
    fin = inicio + timedelta(days=1)
    return (
        Viaje.objects.filter(empresa_id=empresa_id)
        .exclude(estado=EstadoViaje.CANCELADO)
        .annotate(
            hora_vuelo=Coalesce(
                "vuelo__hora_estimada",
                "vuelo__hora_programada",
                F("vuelo_salida_en"),
            )
        )
        .filter(
            Q(sentido=Sentido.DESDE_AEROPUERTO, vuelo__isnull=False)
            | Q(sentido=Sentido.HACIA_AEROPUERTO, vuelo_salida_en__isnull=False),
            hora_vuelo__gte=inicio,
            hora_vuelo__lt=fin,
        )
        .order_by("hora_vuelo", "pk")
    )


def contadores(viajes) -> dict:
    """Sobre los viajes del día (sin filtros): lo que el despacho debe mirar primero."""
    llegadas = [v for v in viajes if v.sentido == Sentido.DESDE_AEROPUERTO]
    return {
        "demorados": sum(v.vuelo.estado_vuelo == EstadoVuelo.DEMORADO for v in llegadas),
        "cancelados_o_desviados": sum(
            v.vuelo.estado_vuelo in (EstadoVuelo.CANCELADO, EstadoVuelo.DESVIADO) for v in llegadas
        ),
        "sin_conductor": sum(v.conductor_id is None and v.estado != EstadoViaje.FINALIZADO for v in viajes),
        "propuestas_pendientes": sum(v.vuelo.recogida_propuesta is not None for v in llegadas),
    }
