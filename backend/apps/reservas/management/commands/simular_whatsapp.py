"""Desarrollo: simula la respuesta del pasajero a la verificación por WhatsApp (HU-20), sin Twilio.

    python manage.py simular_whatsapp <viaje_id> confirmar|cancelar [--texto "…"]

Arma los mismos datos que enviaría el webhook de Twilio: responde al último mensaje de verificación del
viaje.
"""

import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.reservas.models import DireccionMensaje, MensajeWhatsapp, Viaje
from apps.reservas.verificacion import procesar_entrante


class Command(BaseCommand):
    help = "Simula que el pasajero responde Confirmar o Cancelar por WhatsApp (solo desarrollo)."

    def add_arguments(self, parser):
        parser.add_argument("viaje", type=int)
        parser.add_argument("respuesta", choices=["confirmar", "cancelar", "texto"])
        parser.add_argument("--texto", default="")

    def handle(self, *args, viaje, respuesta, texto, **opciones):
        if not settings.DEBUG:
            raise CommandError("Solo con DEBUG activado: en producción las respuestas llegan por Twilio.")
        reserva = Viaje.objects.select_related("pasajero").filter(pk=viaje).first()
        if reserva is None:
            raise CommandError(f"No existe el viaje {viaje}.")
        original = (
            MensajeWhatsapp.objects.filter(viaje=reserva, direccion=DireccionMensaje.SALIENTE)
            .order_by("-creado_en")
            .first()
        )
        datos = {
            "MessageSid": f"SIM{uuid.uuid4().hex[:31]}",
            "From": f"whatsapp:{reserva.pasajero.telefono}",
            "Body": texto or respuesta.capitalize(),
            "ButtonPayload": "" if respuesta == "texto" else respuesta,
            "OriginalRepliedMessageSid": original.proveedor_sid if original else "",
        }
        resultado = procesar_entrante(datos)
        reserva.refresh_from_db()
        self.stdout.write(f"{resultado}: el viaje {reserva.pk} quedó en {reserva.estado}.")
