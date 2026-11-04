from django.core.management.base import BaseCommand

from apps.reservas.expiracion import expirar_pendientes


class Command(BaseCommand):
    help = "Cancela las solicitudes vencidas (RN-06). Pasada manual: de costumbre, Celery beat."

    def handle(self, *args, **opciones):
        self.stdout.write(f"Solicitudes vencidas canceladas: {expirar_pendientes()}")
