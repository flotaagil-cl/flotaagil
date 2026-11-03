import time

from django.core.management.base import BaseCommand

from apps.reservas.asignacion import expirar_asignaciones


class Command(BaseCommand):
    help = "Expira las asignaciones sin respuesta a los 60 s: la reserva vuelve a SOLICITADO (RN-04)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cada",
            type=int,
            default=0,
            help="Repite cada N segundos (modo programador). Sin el argumento corre una vez.",
        )

    def handle(self, *args, cada, **opciones):
        while True:
            expiradas = expirar_asignaciones()
            if expiradas or not cada:
                self.stdout.write(f"Asignaciones expiradas: {expiradas}")
            if not cada:
                return
            time.sleep(cada)
