"""RN-15 (HU-68, CC-19): retención de los mensajes por 12 meses (`RETENCION_MENSAJES_DIAS`, 365 por defecto).

Se borran los mensajes del chat (MENSAJE_CHAT) y el historial de WhatsApp en solo lectura (MENSAJE_WHATSAPP)
más antiguos que el plazo. Las conversaciones quedan (sin esos mensajes); viajes y auditoría no se tocan.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.chat.models import Mensaje

from .models import MensajeWhatsapp


def limite(ahora=None):
    return (ahora or timezone.now()) - timedelta(days=settings.RETENCION_MENSAJES_DIAS)


def purgar_mensajes(ahora=None) -> dict:
    corte = limite(ahora)
    chat, _ = Mensaje.objects.filter(creado_en__lt=corte).delete()
    whatsapp, _ = MensajeWhatsapp.objects.filter(creado_en__lt=corte).delete()
    return {"chat": chat, "whatsapp": whatsapp}
