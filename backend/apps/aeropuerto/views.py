from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.permisos import AisladoPorEmpresaMixin, con_modulo
from apps.cuentas.models import Modulo
from apps.integraciones.vuelos import VuelosNoDisponibles, obtener_consultor_vuelos
from apps.reservas.models import Sentido
from apps.reservas.serializers import ViajeSerializer

from . import alertas, informacion, monitoreo
from .demo import asegurar_vuelos_demo_vigentes
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
    permission_classes = [con_modulo(Modulo.RESERVAS)]  # HU-75: alertas de vuelo de las reservas

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


RANGOS_VUELOS = ("hoy", "manana", "proximos_3_dias")


def _rango_vuelos(rango: str | None) -> tuple:
    hoy = timezone.localdate()
    if rango in (None, "", "hoy"):
        return hoy, 1
    if rango == "manana":
        return hoy + timedelta(days=1), 1
    if rango == "proximos_3_dias":
        return hoy, 3
    raise ValidationError({"rango": "Use «hoy», «manana» o «proximos_3_dias»."})


class VuelosDeHoyView(APIView):
    """HU-69: viajes de aeropuerto del día (o próximos días) de la empresa. Solo lee la base."""

    permission_classes = [con_modulo(Modulo.VUELOS)]  # HU-75

    @extend_schema(
        summary="Vuelos de hoy (llegadas y salidas)",
        tags=["vuelos"],
        parameters=[
            OpenApiParameter(
                "rango",
                OpenApiTypes.STR,
                enum=list(RANGOS_VUELOS),
                description="Ventana de fechas: hoy (por defecto), manana o proximos_3_dias",
            ),
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
        rango = request.query_params.get("rango")
        tipo = request.query_params.get("tipo")
        estado = request.query_params.get("estado")
        dia, dias = _rango_vuelos(rango)
        if tipo not in (None, "", "llegadas", "salidas"):
            raise ValidationError({"tipo": "Use «llegadas» o «salidas»."})
        if estado and estado not in EstadoVuelo.values:
            raise ValidationError({"estado": "Estado de vuelo desconocido."})
        asegurar_vuelos_demo_vigentes(request.user.empresa)
        viajes = list(
            informacion.vuelos_del_dia(request.user.empresa_id, dia, dias=dias).select_related(
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


class ConsultarVuelosRequestSerializer(serializers.Serializer):
    rango = serializers.ChoiceField(
        choices=RANGOS_VUELOS,
        required=False,
        default="hoy",
        help_text="Ventana de días a consultar en el adaptador de vuelos.",
    )


class ConsultarVuelosResponseSerializer(serializers.Serializer):
    consultados = serializers.IntegerField()
    actualizados = serializers.IntegerField()
    sin_datos = serializers.IntegerField()


class ConsultarVuelosAhoraView(APIView):
    """Dispara bajo demanda la consulta del adaptador de vuelos para las llegadas activas del rango."""

    permission_classes = [con_modulo(Modulo.VUELOS)]  # HU-75

    @extend_schema(
        summary="Consultar estado de vuelos ahora",
        tags=["vuelos"],
        request=ConsultarVuelosRequestSerializer,
        responses=ConsultarVuelosResponseSerializer,
    )
    def post(self, request):
        entrada = ConsultarVuelosRequestSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dia, dias = _rango_vuelos(entrada.validated_data.get("rango"))
        asegurar_vuelos_demo_vigentes(request.user.empresa)
        viajes = list(
            informacion.vuelos_del_dia(request.user.empresa_id, dia, dias=dias)
            .filter(sentido=Sentido.DESDE_AEROPUERTO, vuelo__isnull=False)
            .exclude(vuelo__estado_vuelo__in=monitoreo.ESTADOS_FINALES)
            .select_related("vuelo", "empresa__configuracion")[: settings.VUELOS_CONSULTAS_POR_MINUTO]
        )
        consultor = obtener_consultor_vuelos()
        actualizados = sin_datos = 0
        for viaje in viajes:
            vuelo = viaje.vuelo
            try:
                datos = consultor.consultar(vuelo.numero, vuelo.hora_programada)
            except VuelosNoDisponibles:
                alertas.sin_datos(viaje, vuelo)
                sin_datos += 1
                continue
            if datos is None:
                alertas.sin_datos(viaje, vuelo)
                sin_datos += 1
            else:
                monitoreo.aplicar(vuelo.pk, datos)
                actualizados += 1
        return Response(
            ConsultarVuelosResponseSerializer(
                {"consultados": len(viajes), "actualizados": actualizados, "sin_datos": sin_datos}
            ).data
        )
