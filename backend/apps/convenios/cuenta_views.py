"""HU-34: API de la cuenta del convenio (`/api/mi-convenio/`). Solo rol CONVENIO; ve solo lo suyo (RN-13)."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.permisos import con_roles
from apps.cuentas.models import Rol
from apps.portal.serializers import SolicitudConvenioSerializer, SolicitudRespuestaSerializer
from apps.reservas.models import Viaje

from . import cuenta
from .models import Convenio

SOLO_CONVENIO = [con_roles(Rol.CONVENIO)]


class MiConvenioSerializer(serializers.ModelSerializer):
    empresa_slug = serializers.CharField(source="empresa.slug")
    empresa = serializers.CharField(source="empresa.razon_social")

    class Meta:
        model = Convenio
        fields = [
            "id",
            "cliente_nombre",
            "cliente_rut",
            "direccion",
            "encargado_nombre",
            "encargado_telefono",
            "estado",
            "motivo_rechazo",
            "empresa",
            "empresa_slug",
        ]


class ReservaDelConvenioSerializer(serializers.ModelSerializer):
    pasajero = serializers.CharField(source="pasajero.nombre")
    estado_texto = serializers.CharField(source="get_estado_display")

    class Meta:
        model = Viaje
        fields = ["id", "estado", "estado_texto", "pasajero", "origen_dir", "destino_dir", "recogida_en"]


class MiConvenioView(APIView):
    permission_classes = SOLO_CONVENIO

    @extend_schema(tags=["mi-convenio"], summary="Mi convenio y su estado", responses=MiConvenioSerializer)
    def get(self, request):
        return Response(MiConvenioSerializer(cuenta.del_usuario(request.user)).data)


class SolicitudMiConvenioView(APIView):
    permission_classes = SOLO_CONVENIO

    @extend_schema(
        tags=["mi-convenio"],
        summary="Pedir un viaje a nombre del convenio",
        request=SolicitudConvenioSerializer,
        responses={
            201: SolicitudRespuestaSerializer,
            409: OpenApiResponse(description="`convenio_no_aprobado`: en revisión o rechazado"),
        },
        description="RN-07: queda SOLICITADO sin verificación por WhatsApp. La declaración de avisos queda "
        "ligada al usuario que reserva (DC-35).",
    )
    def post(self, request):
        convenio = cuenta.del_usuario(request.user)
        entrada = SolicitudConvenioSerializer(data=request.data, context={"empresa": convenio.empresa})
        entrada.is_valid(raise_exception=True)
        _, respuesta = cuenta.crear_solicitud(convenio, entrada.validated_data, usuario=request.user)
        return Response(SolicitudRespuestaSerializer(respuesta).data, status=status.HTTP_201_CREATED)


class ReservasMiConvenioView(ListAPIView):
    permission_classes = SOLO_CONVENIO
    serializer_class = ReservaDelConvenioSerializer

    @extend_schema(tags=["mi-convenio"], summary="Reservas del convenio, de la más reciente a la más antigua")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Viaje.objects.none()
        convenio = cuenta.del_usuario(self.request.user)
        return (
            Viaje.objects.filter(convenio=convenio).select_related("pasajero").order_by("-recogida_en", "-id")
        )
