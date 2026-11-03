"""Webhooks de Twilio WhatsApp (HU-20): mensajes entrantes y estados de entrega.

Públicos (los llama Twilio). Con `TWILIO_AUTH_TOKEN` se exige la firma `X-Twilio-Signature` calculada sobre
`WHATSAPP_URL_BASE` + la ruta; sin token (desarrollo) solo se aceptan con DEBUG activado.
"""

import logging

from django.conf import settings
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.parsers import FormParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.integraciones.notificaciones import firma_valida

from . import verificacion

logger = logging.getLogger(__name__)
TWIML_VACIO = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'


def _autorizado(request) -> bool:
    token = settings.TWILIO_AUTH_TOKEN
    if not token:
        return settings.DEBUG
    url = f"{settings.WHATSAPP_URL_BASE.rstrip('/')}{request.path}"
    parametros = {clave: request.POST.get(clave) for clave in request.POST}
    return firma_valida(token, url, parametros, request.headers.get("X-Twilio-Signature", ""))


class _WebhookTwilio(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    parser_classes = [FormParser]

    def _rechazo(self):
        logger.warning(
            "Webhook de WhatsApp con firma inválida desde %s.", self.request.META.get("REMOTE_ADDR")
        )
        return HttpResponse("Firma inválida.", status=403, content_type="text/plain")


class WebhookEntranteView(_WebhookTwilio):
    @extend_schema(
        tags=["whatsapp"],
        summary="Webhook de Twilio: mensaje entrante del pasajero",
        request={"application/x-www-form-urlencoded": dict},
        responses={
            200: OpenApiResponse(description="TwiML vacío"),
            403: OpenApiResponse(description="Firma inválida"),
        },
        description="Confirmar o Cancelar responde la verificación de RN-06. Idempotente por MessageSid.",
    )
    def post(self, request):
        if not _autorizado(request):
            return self._rechazo()
        resultado = verificacion.procesar_entrante({clave: request.POST.get(clave) for clave in request.POST})
        logger.info("WhatsApp entrante: %s.", resultado)
        return HttpResponse(TWIML_VACIO, content_type="text/xml")


class WebhookEstadoView(_WebhookTwilio):
    @extend_schema(
        tags=["whatsapp"],
        summary="Webhook de Twilio: estado de entrega de un mensaje enviado",
        request={"application/x-www-form-urlencoded": dict},
        responses={204: None, 403: OpenApiResponse(description="Firma inválida")},
    )
    def post(self, request):
        if not _autorizado(request):
            return self._rechazo()
        verificacion.procesar_estado({clave: request.POST.get(clave) for clave in request.POST})
        return HttpResponse(status=204)
