"""HU-35: API de la cuenta del pasajero (`/api/mi-cuenta/`). Solo rol PASAJERO, con la cuenta confirmada; ve
solo las reservas de su teléfono en su empresa (RN-13)."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.permisos import con_roles
from apps.cuentas.models import Rol
from apps.portal.serializers import SolicitudRespuestaSerializer, SolicitudSerializer

from . import cuentas_pasajero as cuentas
from .models import Viaje
from .serializers import HistorialSerializer

SOLO_PASAJERO = [con_roles(Rol.PASAJERO)]


class MiCuentaSerializer(serializers.Serializer):
    nombre = serializers.CharField()
    email = serializers.EmailField(source="usuario.email")
    telefono = serializers.CharField()
    empresa = serializers.CharField(source="empresa.razon_social")
    empresa_slug = serializers.CharField(source="empresa.slug")


class MiReservaSerializer(serializers.ModelSerializer):
    estado_texto = serializers.CharField(source="get_estado_display")
    cancelable = serializers.SerializerMethodField()
    historial = HistorialSerializer(many=True, read_only=True)

    class Meta:
        model = Viaje
        fields = [
            "id",
            "estado",
            "estado_texto",
            "canal",
            "origen_dir",
            "destino_dir",
            "recogida_en",
            "cancelable",
            "historial",
        ]

    def get_cancelable(self, viaje) -> bool:
        return viaje.estado in cuentas.CANCELABLES


class SolicitudCuentaSerializer(SolicitudSerializer):
    """Los datos del pasajero salen de la cuenta: nombre y teléfono se ignoran si vienen."""

    nombre = serializers.CharField(max_length=80, required=False)
    telefono = serializers.CharField(max_length=24, required=False)


class MiCuentaView(APIView):
    permission_classes = SOLO_PASAJERO

    @extend_schema(
        tags=["mi-cuenta"],
        summary="Mi cuenta",
        responses={200: MiCuentaSerializer, 409: OpenApiResponse(description="`cuenta_sin_confirmar`")},
    )
    def get(self, request):
        return Response(MiCuentaSerializer(cuentas.cuenta_activa(request.user)).data)

    @extend_schema(
        tags=["mi-cuenta"],
        summary="Eliminar mi cuenta",
        responses={204: None},
        description="Borra la credencial y el correo; las reservas y el pasajero quedan como de invitado.",
    )
    def delete(self, request):
        cuentas.eliminar(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MisReservasView(ListAPIView):
    permission_classes = SOLO_PASAJERO
    serializer_class = MiReservaSerializer

    @extend_schema(tags=["mi-cuenta"], summary="Mis reservas, incluidas las de invitado, con su historial")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Viaje.objects.none()
        return cuentas.reservas_de(cuentas.cuenta_activa(self.request.user)).prefetch_related(
            "historial__usuario"
        )


class CancelarMiReservaView(APIView):
    permission_classes = SOLO_PASAJERO

    @extend_schema(
        tags=["mi-cuenta"],
        summary="Cancelar una reserva sin conductor asignado (RN-09)",
        request=None,
        responses={200: MiReservaSerializer, 404: None, 409: OpenApiResponse(description="`con_conductor`")},
    )
    def post(self, request, pk):
        cuenta = cuentas.cuenta_activa(request.user)
        viaje = cuentas.cancelar(cuenta, pk, usuario=request.user)
        return Response(
            MiReservaSerializer(Viaje.objects.prefetch_related("historial").get(pk=viaje.pk)).data
        )


class SolicitudMiCuentaView(APIView):
    permission_classes = SOLO_PASAJERO

    @extend_schema(
        tags=["mi-cuenta"],
        summary="Pedir un viaje con mi cuenta",
        request=SolicitudCuentaSerializer,
        responses={201: SolicitudRespuestaSerializer, 429: OpenApiResponse(description="`limite_telefono`")},
        description="Queda SOLICITADO sin verificación por WhatsApp; se mantiene el límite por teléfono.",
    )
    def post(self, request):
        cuenta = cuentas.cuenta_activa(request.user)
        entrada = SolicitudCuentaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        _, respuesta = cuentas.solicitar(cuenta, entrada.validated_data, usuario=request.user)
        return Response(SolicitudRespuestaSerializer(respuesta).data, status=status.HTTP_201_CREATED)
