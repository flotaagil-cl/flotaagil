"""HU-35: API de la cuenta del pasajero (`/api/mi-cuenta/`). Solo rol PASAJERO, con la cuenta confirmada; ve
solo las reservas de su teléfono en su empresa (RN-13)."""

from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_field
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.permisos import con_roles
from apps.cuentas.models import Rol
from apps.portal.serializers import SolicitudRespuestaSerializer, SolicitudSerializer

from . import cuentas_pasajero as cuentas
from .models import EstadoViaje, Viaje
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
    """Los datos del pasajero salen de la cuenta: nombre y teléfono se ignoran si vienen. DC-44: el pedido no
    acepta nada (la cuenta ya aceptó una vez); las aceptaciones se ignoran si vienen."""

    nombre = serializers.CharField(max_length=80, required=False)
    telefono = serializers.CharField(max_length=24, required=False)
    acepta_privacidad = serializers.BooleanField(required=False)
    acepta_whatsapp = serializers.BooleanField(required=False)

    def validate_acepta_privacidad(self, valor):
        return valor

    def validate_acepta_whatsapp(self, valor):
        return valor


class PedidoRecibidoSerializer(SolicitudRespuestaSerializer):
    """HU-42: con cuenta, la respuesta trae el número de la reserva (el pasajero solo ve las suyas)."""

    id = serializers.IntegerField(help_text="Número de la reserva, para «Ver mi viaje».")


class AceptarPrivacidadSerializer(serializers.Serializer):
    acepta = serializers.BooleanField()

    def validate_acepta(self, valor):
        if not valor:
            raise serializers.ValidationError("Para seguir debes aceptar el aviso de privacidad.")
        return valor


class PrivacidadAceptadaSerializer(serializers.Serializer):
    aceptada_en = serializers.DateTimeField()
    version = serializers.CharField()


class MiPrivacidadView(APIView):
    permission_classes = SOLO_PASAJERO

    @extend_schema(
        tags=["mi-cuenta"],
        summary="Aceptar el aviso de privacidad vigente",
        request=AceptarPrivacidadSerializer,
        responses={200: PrivacidadAceptadaSerializer},
        description="DC-44: para las cuentas que no lo aceptaron o cuando cambia la versión del aviso.",
    )
    def post(self, request):
        AceptarPrivacidadSerializer(data=request.data).is_valid(raise_exception=True)
        cuenta = cuentas.aceptar_privacidad(request.user)
        datos = {"aceptada_en": cuenta.privacidad_aceptada_en, "version": cuenta.privacidad_version}
        return Response(PrivacidadAceptadaSerializer(datos).data)


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


# HU-43: el pasajero ve a su conductor, el vehículo y la patente desde que el conductor acepta el viaje.
CON_CONDUCTOR_VISIBLE = frozenset(
    {
        EstadoViaje.ACEPTADO,
        EstadoViaje.EN_CAMINO,
        EstadoViaje.EN_ZONA,
        EstadoViaje.PASAJERO_A_BORDO,
        EstadoViaje.FINALIZADO,
    }
)


class PuntoSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class PasoSerializer(serializers.Serializer):
    """Historial para el pasajero: solo el estado y la hora (sin quién lo cambió)."""

    estado = serializers.CharField(source="estado_nuevo")
    creado_en = serializers.DateTimeField()


class ConductorDeMiViajeSerializer(serializers.Serializer):
    nombre = serializers.CharField(source="usuario.nombre")


class VehiculoDeMiViajeSerializer(serializers.Serializer):
    marca_modelo = serializers.CharField()
    patente = serializers.CharField()


class VueloDeMiViajeSerializer(serializers.Serializer):
    numero = serializers.CharField()
    hora_programada = serializers.DateTimeField()
    hora_estimada = serializers.DateTimeField(allow_null=True)
    estado_vuelo = serializers.CharField()


class TuViajeSerializer(serializers.ModelSerializer):
    """HU-43: el viaje del pasajero con su cuenta (solo los suyos)."""

    estado_texto = serializers.CharField(source="get_estado_display")
    cancelable = serializers.SerializerMethodField()
    origen = serializers.SerializerMethodField()
    destino = serializers.SerializerMethodField()
    conductor = serializers.SerializerMethodField()
    vehiculo = serializers.SerializerMethodField()
    vuelo = serializers.SerializerMethodField()
    pasos = PasoSerializer(source="historial", many=True, read_only=True)

    class Meta:
        model = Viaje
        fields = [
            "id",
            "estado",
            "estado_texto",
            "sentido",
            "origen_dir",
            "destino_dir",
            "origen",
            "destino",
            "recogida_en",
            "pasajeros",
            "maletas",
            "vuelo_salida_en",
            "vuelo_salida_tipo",
            "creado_en",
            "cancelable",
            "conductor",
            "vehiculo",
            "vuelo",
            "pasos",
        ]

    def get_cancelable(self, viaje) -> bool:
        return viaje.estado in cuentas.CANCELABLES

    @extend_schema_field(PuntoSerializer)
    def get_origen(self, viaje):
        return {"lat": viaje.origen_geo.y, "lng": viaje.origen_geo.x}

    @extend_schema_field(PuntoSerializer)
    def get_destino(self, viaje):
        return {"lat": viaje.destino_geo.y, "lng": viaje.destino_geo.x}

    @extend_schema_field(ConductorDeMiViajeSerializer(allow_null=True))
    def get_conductor(self, viaje):
        if viaje.estado not in CON_CONDUCTOR_VISIBLE or viaje.conductor is None:
            return None
        return ConductorDeMiViajeSerializer(viaje.conductor).data

    @extend_schema_field(VehiculoDeMiViajeSerializer(allow_null=True))
    def get_vehiculo(self, viaje):
        if viaje.estado not in CON_CONDUCTOR_VISIBLE or viaje.vehiculo is None:
            return None
        return VehiculoDeMiViajeSerializer(viaje.vehiculo).data

    @extend_schema_field(VueloDeMiViajeSerializer(allow_null=True))
    def get_vuelo(self, viaje):
        vuelo = getattr(viaje, "vuelo", None)
        return VueloDeMiViajeSerializer(vuelo).data if vuelo else None


class TuViajeView(RetrieveAPIView):
    permission_classes = SOLO_PASAJERO
    serializer_class = TuViajeSerializer

    @extend_schema(
        tags=["mi-cuenta"],
        summary="Tu viaje (HU-43)",
        description="Solo un viaje del pasajero (404 si no es suyo); conductor y patente desde ACEPTADO.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Viaje.objects.none()
        return (
            cuentas.reservas_de(cuentas.cuenta_activa(self.request.user))
            .select_related("conductor__usuario", "vehiculo", "vuelo")
            .prefetch_related("historial")
        )


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
        responses={
            201: PedidoRecibidoSerializer,
            403: OpenApiResponse(description="`aceptar_privacidad`: falta aceptar el aviso vigente (DC-44)"),
            429: OpenApiResponse(description="`limite_telefono`"),
        },
        description="Queda SOLICITADO sin verificación por WhatsApp; se mantiene el límite por teléfono.",
    )
    def post(self, request):
        cuenta = cuentas.cuenta_activa(request.user)
        entrada = SolicitudCuentaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        viaje, respuesta = cuentas.solicitar(cuenta, entrada.validated_data, usuario=request.user)
        datos = {**respuesta, "id": viaje.pk}
        return Response(PedidoRecibidoSerializer(datos).data, status=status.HTTP_201_CREATED)
