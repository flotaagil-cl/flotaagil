"""Generación dinámica e idempotente de vuelos demo para desarrollo (HU-27, HU-69)."""

from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone

from apps.integraciones.vuelos import DatosVuelo, designador, origen_desarrollo
from apps.reservas.models import Actor, Canal, EstadoViaje, HistorialEstado, Pasajero, Sentido, Viaje

from . import monitoreo
from .models import EstadoVuelo, Vuelo

AEROPUERTO_DIR = "Aeropuerto Arturo Merino Benítez, Pudahuel"
AEROPUERTO_PUNTO = Point(-70.794, -33.393, srid=4326)
DESTINO_PUNTO = Point(-70.612, -33.425, srid=4326)

# 6 vuelos diarios variados: nacionales a tiempo, nacional demorado (+25 min con propuesta),
# internacionales (margen 35 min) y aterrizado temprano para el día en curso.
PARRILLA_VUELOS_DEMO = (
    {
        "numero": "LA 305",
        "hora": time(7, 45),
        "origen_icao": "SCTE",
        "estado_hoy": EstadoVuelo.ATERRIZADO,
        "estado_futuro": EstadoVuelo.PROGRAMADO,
        "demora_min": 0,
        "destino": "Av. Providencia 1234, Providencia",
        "tarifa": 24000,
    },
    {
        "numero": "LA 310",
        "hora": time(11, 30),
        "origen_icao": "SCFA",
        "estado_hoy": EstadoVuelo.PROGRAMADO,
        "estado_futuro": EstadoVuelo.PROGRAMADO,
        "demora_min": 0,
        "destino": "Av. Apoquindo 4500, Las Condes",
        "tarifa": 26000,
    },
    {
        "numero": "H2 204",
        "hora": time(14, 15),
        "origen_icao": "SCIE",
        "estado_hoy": EstadoVuelo.PROGRAMADO,
        "estado_futuro": EstadoVuelo.PROGRAMADO,
        "demora_min": 0,
        "destino": "Plaza de Armas, Santiago",
        "tarifa": 22000,
    },
    {
        "numero": "LA 450",
        "hora": time(16, 40),
        "origen_icao": "SCPE",
        "estado_hoy": EstadoVuelo.DEMORADO,
        "estado_futuro": EstadoVuelo.DEMORADO,
        "demora_min": 25,
        "destino": "Av. Vicuña Mackenna 3000, Ñuñoa",
        "tarifa": 25000,
    },
    {
        "numero": "LA 800",
        "hora": time(19, 20),
        "origen_icao": "KMIA",
        "estado_hoy": EstadoVuelo.PROGRAMADO,
        "estado_futuro": EstadoVuelo.PROGRAMADO,
        "demora_min": 0,
        "destino": "Av. Kennedy 9001, Vitacura",
        "tarifa": 32000,
    },
    {
        "numero": "JA 712",
        "hora": time(21, 10),
        "origen_icao": "SAEZ",
        "estado_hoy": EstadoVuelo.PROGRAMADO,
        "estado_futuro": EstadoVuelo.PROGRAMADO,
        "demora_min": 0,
        "destino": "Av. Apoquindo 3000, Las Condes",
        "tarifa": 28000,
    },
)

PASAJEROS_DEMO = (
    ("Camila Fuentes", "+56900090001"),
    ("Matías Riquelme", "+56900090002"),
    ("Valentina Soto", "+56900090003"),
    ("Sebastián Morales", "+56900090004"),
    ("Javiera Contreras", "+56900090005"),
    ("Tomás Herrera", "+56900090006"),
)


def _modo_desarrollo_sin_api() -> bool:
    return bool(settings.DEBUG) and not getattr(settings, "FLIGHTAWARE_API_KEY", "")


def asegurar_vuelos_demo_vigentes(empresa) -> int:
    """Genera de forma idempotente 6 vuelos diarios (hoy, mañana y pasado mañana) en modo desarrollo.

    Solo corre cuando `settings.DEBUG` está activo y no existe `FLIGHTAWARE_API_KEY`.
    Devuelve la cantidad de vuelos nuevos creados.
    """
    if not _modo_desarrollo_sin_api():
        return 0

    hoy = timezone.localdate()
    dias = [hoy + timedelta(days=offset) for offset in range(3)]
    configuracion = empresa.configuracion
    creados = 0

    with transaction.atomic():
        for offset, dia in enumerate(dias):
            existentes = set(
                Vuelo.objects.filter(viaje__empresa=empresa, fecha=dia).values_list("numero", flat=True)
            )
            existentes_norm = {designador(n) for n in existentes}

            for idx, spec in enumerate(PARRILLA_VUELOS_DEMO):
                numero = spec["numero"]
                if designador(numero) in existentes_norm:
                    continue

                nombre_pax, fono_pax = PASAJEROS_DEMO[idx % len(PASAJEROS_DEMO)]
                pasajero, _ = Pasajero.objects.get_or_create(
                    empresa=empresa, telefono=fono_pax, defaults={"nombre": nombre_pax}
                )

                programada = timezone.make_aware(datetime.combine(dia, spec["hora"]))
                demora = spec["demora_min"]
                estimada = programada + timedelta(minutes=demora) if demora else None
                estado = spec["estado_hoy"] if offset == 0 else spec["estado_futuro"]
                origen_icao = spec["origen_icao"]
                ciudad, aeropuerto = origen_desarrollo(origen_icao)
                margen_min = (
                    configuracion.margen_internacional_min
                    if monitoreo.es_internacional(origen_icao)
                    else configuracion.margen_nacional_min
                )

                viaje = Viaje.objects.create(
                    empresa=empresa,
                    pasajero=pasajero,
                    canal=Canal.TELEFONO,
                    sentido=Sentido.DESDE_AEROPUERTO,
                    origen_dir=AEROPUERTO_DIR,
                    origen_geo=AEROPUERTO_PUNTO,
                    destino_dir=spec["destino"],
                    destino_geo=DESTINO_PUNTO,
                    recogida_en=programada + timedelta(minutes=margen_min),
                    tarifa=spec["tarifa"],
                    estado=EstadoViaje.SOLICITADO,
                )
                HistorialEstado.objects.create(
                    viaje=viaje,
                    estado_anterior=None,
                    estado_nuevo=EstadoViaje.SOLICITADO,
                    actor=Actor.SISTEMA,
                )
                vuelo = Vuelo.objects.create(
                    viaje=viaje,
                    numero=numero,
                    fecha=dia,
                    hora_programada=programada,
                    hora_estimada=estimada,
                    estado_vuelo=estado,
                    origen_icao=origen_icao,
                    origen_ciudad=ciudad,
                    origen_aeropuerto=aeropuerto,
                    ultima_consulta_en=timezone.now(),
                )
                if demora > 0:
                    monitoreo.aplicar(
                        vuelo.pk,
                        DatosVuelo(numero, programada, estimada, estado, origen_icao, ciudad, aeropuerto),
                    )
                existentes_norm.add(designador(numero))
                creados += 1

    return creados
