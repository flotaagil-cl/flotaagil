from django.core.management.base import BaseCommand

from apps.reservas.expiracion import expirar_pendientes


class Command(BaseCommand):
    help = "Cuenta las solicitudes «Sin confirmar» (RN-06, CC-22): ya no se cancelan solas."

    def handle(self, *args, **opciones):
        self.stdout.write(f"Solicitudes sin confirmar: {expirar_pendientes()}")
