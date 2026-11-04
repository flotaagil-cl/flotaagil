from django.core.management.base import BaseCommand

from apps.reservas.asignacion import expirar_asignaciones


class Command(BaseCommand):
    help = (
        "Expira las asignaciones sin respuesta a los 60 s (RN-04). Pasada manual: de costumbre, Celery beat."
    )

    def handle(self, *args, **opciones):
        self.stdout.write(f"Asignaciones expiradas: {expirar_asignaciones()}")
