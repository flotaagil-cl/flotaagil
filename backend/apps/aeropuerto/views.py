from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.permisos import AisladoPorEmpresaMixin, con_roles
from apps.cuentas.models import Rol
from apps.reservas.models import Sentido
from apps.reservas.serializers import ViajeSerializer

from . import alertas, informacion
from .models import AlertaVuelo, EstadoVuelo
from .serializers import AlertaVueloSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Registro de alertas de vuelos",
        tags=["alertas"],
        parameters=[
            OpenApiParameter("pendientes", OpenApiTypes.BOOL, description="Solo las que nadie ha atendido"),
        ],
    )
)
class AlertaVueloViewSet(AisladoPorEmpresaMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """HU-28: demora, cancelación, desvío o API sin datos. Las más recientes primero."""

    queryset = AlertaVuelo.objects.select_related("atendida_por").order_by("-creada_en", "-id")
    serializer_class = AlertaVueloSerializer
    permission_classes = [con_roles(Rol.ADMINISTRADOR, Rol.DESPACHADOR)]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("pendientes") == "true":
            queryset = queryset.filter(atendida_en__isnull=True)
        return queryset

    @extend_schema(summary="Marcar una alerta como atendida", tags=["alertas"], request=None)
    @action(detail=True, methods=["post"])
    def atender(self, request, pk=None):
        alerta = alertas.atender(self.get_object(), usuario=request.user)
        return Response(AlertaVueloSerializer(alerta).data)


class ContadoresVuelosSerializer(serializers.Serializer):
    demorados = serializers.IntegerField()
    cancelados_o_desviados = serializers.IntegerField()
    sin_conductor = serializers.IntegerField()
    propuestas_pendientes = serializers.IntegerField()


class VuelosDeHoySerializer(serializers.Serializer):
    fecha = serializers.DateField(help_text="Día de Chile al que corresponden los vuelos.")
    contadores = ContadoresVuelosSerializer(help_text="Sobre todos los viajes del día, sin filtros.")
    viajes = ViajeSerializer(many=True)


class VuelosDeHoyView(APIView):
    """HU-69: viajes de aeropuerto del día de la empresa del usuario. Solo lee la base (sin API de vuelos)."""

    permission_classes = [con_roles(Rol.ADMINISTRADOR, Rol.DESPACHADOR)]

    @extend_schema(
        summary="Vuelos de hoy (llegadas y salidas)",
        tags=["vuelos"],
        parameters=[
            OpenApiParameter(
                "tipo", OpenApiTypes.STR, enum=["llegadas", "salidas"], description="Sin él, ambos"
            ),
            OpenApiParameter(
                "estado",
                OpenApiTypes.STR,
                enum=EstadoVuelo.values,
                description="Estado del vuelo (solo llegadas: las salidas no se monitorean)",
            ),
        ],
        responses=VuelosDeHoySerializer,
    )
    def get(self, request):
        tipo = request.query_params.get("tipo")
        estado = request.query_params.get("estado")
        if tipo not in (None, "", "llegadas", "salidas"):
            raise ValidationError({"tipo": "Use «llegadas» o «salidas»."})
        if estado and estado not in EstadoVuelo.values:
            raise ValidationError({"estado": "Estado de vuelo desconocido."})
        dia = timezone.localdate()
        viajes = list(
            informacion.vuelos_del_dia(request.user.empresa_id, dia).select_related(
                "pasajero", "conductor__usuario", "vehiculo", "convenio", "vuelo", "empresa__configuracion"
            )
        )
        filtrados = [
            v
            for v in viajes
            if (tipo != "llegadas" or v.sentido == Sentido.DESDE_AEROPUERTO)
            and (tipo != "salidas" or v.sentido == Sentido.HACIA_AEROPUERTO)
            and (not estado or (v.sentido == Sentido.DESDE_AEROPUERTO and v.vuelo.estado_vuelo == estado))
        ]
        datos = {"fecha": dia, "contadores": informacion.contadores(viajes), "viajes": filtrados}
        return Response(VuelosDeHoySerializer(datos, context={"request": request}).data)
