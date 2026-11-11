"""Datos públicos de la instalación, sin sesión."""

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class ConfiguracionPublicaSerializer(serializers.Serializer):
    soporte_correo = serializers.EmailField(
        allow_null=True,
        help_text="Correo de soporte de FlotaÁgil (SOPORTE_CORREO); null si no está configurado.",
    )


class ConfiguracionPublicaView(APIView):
    """Lo que las pantallas sin sesión necesitan saber de la instalación (ingreso del panel)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["publico"], summary="Configuración pública", responses={200: ConfiguracionPublicaSerializer}
    )
    def get(self, _request):
        return Response({"soporte_correo": settings.SOPORTE_CORREO or None})
