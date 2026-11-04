"""Desarrollo: simula lo que informaría la API de vuelos, sin FlightAware (HU-27).

python manage.py simular_vuelo <viaje_id> --eta-min 40 [--estado DEMORADO] [--origen SPJC]
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.aeropuerto import monitoreo
from apps.aeropuerto.models import EstadoVuelo, Vuelo
from apps.integraciones.vuelos import DatosVuelo


class Command(BaseCommand):
    help = "Simula una respuesta de la API de vuelos: ETA, estado y origen (solo desarrollo)."

    def add_arguments(self, parser):
        parser.add_argument("viaje", type=int)
        parser.add_argument(
            "--eta-min", type=int, default=0, help="Minutos de cambio sobre la hora programada"
        )
        parser.add_argument("--estado", choices=EstadoVuelo.values, default=EstadoVuelo.DEMORADO)
        parser.add_argument("--origen", default=None, help="ICAO del aeropuerto de origen")

    def handle(self, *args, viaje, eta_min, estado, origen, **opciones):
        if not settings.DEBUG:
            raise CommandError("Solo con DEBUG activado: en producción la información llega de la API.")
        vuelo = Vuelo.objects.filter(viaje_id=viaje).first()
        if vuelo is None:
            raise CommandError(f"El viaje {viaje} no tiene vuelo.")
        eta = vuelo.hora_programada + timedelta(minutes=eta_min)
        vuelo = monitoreo.aplicar(
            vuelo.pk, DatosVuelo(vuelo.numero, vuelo.hora_programada, eta, estado, origen)
        )
        self.stdout.write(f"Vuelo {vuelo.numero}: ETA {eta}; recogida propuesta: {vuelo.recogida_propuesta}")
