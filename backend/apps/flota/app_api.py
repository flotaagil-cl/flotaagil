"""API de la app del conductor: perfil, consentimiento de ubicación (RN-18) y envío de posiciones GPS.

Solo el rol CONDUCTOR. Cada conductor ve y escribe solo lo suyo (el usuario de la sesión), así que el
aislamiento por empresa (RN-13) queda dado por la cuenta.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_field
from rest_framework import serializers, status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.permisos import con_roles
from apps.cuentas.models import Rol
from apps.reservas.models import EstadoViaje, Viaje

from .models import Conductor, EstadoConductor, PosicionGps
from .serializers import VehiculoAsociadoSerializer, VehiculoDeclaradoSerializer

MAX_POR_LOTE = 100
# Estados del viaje en que la posición del conductor se asocia al viaje.
ESTADOS_CON_VIAJE = (
    EstadoViaje.ACEPTADO,
    EstadoViaje.EN_CAMINO,
    EstadoViaje.EN_ZONA,
    EstadoViaje.PASAJERO_A_BORDO,
)
EN_TURNO = (EstadoConductor.DISPONIBLE, EstadoConductor.EN_VIAJE)


class FueraDeTurno(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "fuera_de_turno"
    default_detail = "La ubicación solo se registra en turno (Disponible o En viaje)."


class SinConsentimiento(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "sin_consentimiento"
    default_detail = "Falta el consentimiento informado para registrar la ubicación."


class PerfilConductorSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="usuario.nombre", read_only=True)
    vehiculo_activo = VehiculoDeclaradoSerializer(allow_null=True, read_only=True)
    vehiculos = serializers.SerializerMethodField()

    class Meta:
        model = Conductor
        fields = ["id", "nombre", "estado", "vehiculo_activo", "consentimiento_gps_en", "vehiculos"]
        read_only_fields = fields

    @staticmethod
    @extend_schema_field(VehiculoAsociadoSerializer(many=True))
    def get_vehiculos(conductor):
        activos = [a for a in conductor.asociaciones.all() if a.vehiculo.activo]
        return VehiculoAsociadoSerializer(sorted(activos, key=lambda a: a.vehiculo.patente), many=True).data


class PosicionSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)
    precision_m = serializers.FloatField(min_value=0, required=False, allow_null=True)
    registrada_en = serializers.DateTimeField()


class LotePosicionesSerializer(serializers.Serializer):
    posiciones = PosicionSerializer(many=True, allow_empty=False, max_length=MAX_POR_LOTE)


class ResultadoLoteSerializer(serializers.Serializer):
    recibidas = serializers.IntegerField(help_text="Guardadas ahora")
    repetidas = serializers.IntegerField(help_text="Ya estaban (reenvío del mismo lote)")
    descartadas = serializers.IntegerField(
        help_text="Precisión > 500 m, del futuro o más antiguas que la retención: no se guardan"
    )


def _conductor(request) -> Conductor:
    return (
        Conductor.objects.select_related("usuario", "vehiculo_activo")
        .prefetch_related("asociaciones__vehiculo")
        .get(usuario=request.user)
    )


class _VistaApp(APIView):
    permission_classes = [con_roles(Rol.CONDUCTOR)]


class PerfilView(_VistaApp):
    @extend_schema(
        tags=["app"], summary="Perfil del conductor de la sesión", responses=PerfilConductorSerializer
    )
    def get(self, request):
        return Response(PerfilConductorSerializer(_conductor(request)).data)


class ConsentimientoView(_VistaApp):
    @extend_schema(
        tags=["app"],
        summary="Aceptar el tratamiento de la ubicación (RN-18)",
        request=None,
        responses=PerfilConductorSerializer,
        description="Guarda la fecha de aceptación. Si ya estaba aceptado, la conserva.",
    )
    def post(self, request):
        conductor = _conductor(request)
        if conductor.consentimiento_gps_en is None:
            conductor.consentimiento_gps_en = timezone.now()
            conductor.save(update_fields=["consentimiento_gps_en"])
        return Response(PerfilConductorSerializer(conductor).data)


class PosicionesView(_VistaApp):
    @extend_schema(
        tags=["app"],
        summary="Enviar un lote de posiciones GPS",
        request=LotePosicionesSerializer,
        responses={
            201: ResultadoLoteSerializer,
            409: OpenApiResponse(description="`fuera_de_turno` o `sin_consentimiento` (RN-18)."),
        },
        description=f"Hasta {MAX_POR_LOTE} posiciones por lote. Idempotente: reenviar el mismo lote no "
        "duplica "
        "(única por conductor e instante). Se asocian al viaje en curso del conductor, si hay uno.",
    )
    def post(self, request):
        entrada = LotePosicionesSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        conductor = _conductor(request)
        if conductor.consentimiento_gps_en is None:
            raise SinConsentimiento()
        if conductor.estado not in EN_TURNO:
            raise FueraDeTurno()

        ahora = timezone.now()
        minimo = ahora - timedelta(days=settings.RETENCION_POSICIONES_DIAS)
        maximo = ahora + timedelta(minutes=2)  # tolerancia del reloj del teléfono
        validas, descartadas = [], 0
        for posicion in entrada.validated_data["posiciones"]:
            precision = posicion.get("precision_m")
            if (precision is not None and precision > 500) or not minimo <= posicion[
                "registrada_en"
            ] <= maximo:
                descartadas += 1
                continue
            validas.append(posicion)

        viaje = (
            Viaje.objects.filter(conductor=conductor, estado__in=ESTADOS_CON_VIAJE)
            .order_by("-recogida_en")
            .first()
        )
        nuevas = [
            PosicionGps(
                conductor=conductor,
                viaje=viaje,
                punto=Point(p["lon"], p["lat"], srid=4326),
                precision_m=None if p.get("precision_m") is None else round(p["precision_m"]),
                registrada_en=p["registrada_en"],
            )
            for p in validas
        ]
        with transaction.atomic():
            # En serie por conductor: el conteo de recibidas no se mezcla con otro lote simultáneo.
            list(Conductor.objects.select_for_update().filter(pk=conductor.pk).values_list("pk"))
            antes = PosicionGps.objects.filter(conductor=conductor).count()
            PosicionGps.objects.bulk_create(nuevas, ignore_conflicts=True)
            recibidas = PosicionGps.objects.filter(conductor=conductor).count() - antes
        return Response(
            {"recibidas": recibidas, "repetidas": len(validas) - recibidas, "descartadas": descartadas},
            status=status.HTTP_201_CREATED,
        )
