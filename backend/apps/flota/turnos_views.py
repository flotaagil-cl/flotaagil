"""HU-31 (CC-12): API del panel para turnos y cierre de caja. Solo administrador (RN-13: su empresa)."""

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.permisos import con_roles
from apps.cuentas.models import Rol

from . import turnos
from .models import CierreCaja, Turno

SOLO_ADMIN = [con_roles(Rol.ADMINISTRADOR)]
CONFLICTO = OpenApiResponse(
    description="`turno_abierto`, `cierre_repetido` o `viaje_en_ejecucion` (cierre de caja); `en_viaje` o "
    "`sin_turno` (cierre administrativo)."
)


class CierreCajaSerializer(serializers.ModelSerializer):
    responsable = serializers.CharField(source="responsable.nombre")

    class Meta:
        model = CierreCaja
        fields = [
            "id",
            "monto_registrado",
            "monto_rendido",
            "diferencia",
            "observacion",
            "responsable",
            "fecha_cierre",
        ]


class TurnoSerializer(serializers.ModelSerializer):
    conductor = serializers.CharField(source="conductor.usuario.nombre")
    conductor_id = serializers.IntegerField()
    patente = serializers.CharField(source="vehiculo.patente", allow_null=True, default=None)
    cierre_caja = CierreCajaSerializer(allow_null=True, default=None)

    class Meta:
        model = Turno
        fields = [
            "id",
            "conductor_id",
            "conductor",
            "patente",
            "hora_inicio",
            "hora_termino",
            "motivo_termino",
            "cierre_caja",
        ]


class TurnoPorCerrarSerializer(TurnoSerializer):
    efectivo_registrado = serializers.IntegerField(
        source="efectivo", help_text="Efectivo de PAGO_VIAJE del turno"
    )
    viajes_finalizados = serializers.IntegerField()
    con_viaje_en_ejecucion = serializers.BooleanField(help_text="Si es true, aún no se puede cerrar la caja")

    class Meta(TurnoSerializer.Meta):
        fields = [f for f in TurnoSerializer.Meta.fields if f != "cierre_caja"] + [
            "efectivo_registrado",
            "viajes_finalizados",
            "con_viaje_en_ejecucion",
        ]


class CerrarCajaSerializer(serializers.Serializer):
    monto_rendido = serializers.IntegerField(
        min_value=0, max_value=50_000_000, help_text="Efectivo rendido (CLP)"
    )
    observacion = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Obligatoria si lo rendido no coincide con lo registrado.",
    )


class TurnosPorCerrarView(APIView):
    permission_classes = SOLO_ADMIN

    @extend_schema(
        tags=["turnos"],
        summary="Turnos terminados sin cierre de caja",
        responses=TurnoPorCerrarSerializer(many=True),
    )
    def get(self, request):
        return Response(TurnoPorCerrarSerializer(turnos.por_cerrar(request.user.empresa_id), many=True).data)


class TurnosView(APIView):
    permission_classes = SOLO_ADMIN

    @extend_schema(
        tags=["turnos"],
        summary="Historial de turnos de un conductor",
        parameters=[OpenApiParameter("conductor", int, required=True)],
        responses=TurnoSerializer(many=True),
    )
    def get(self, request):
        conductor = serializers.IntegerField().run_validation(request.query_params.get("conductor"))
        consulta = (
            Turno.objects.filter(
                conductor_id=conductor, conductor__usuario__empresa_id=request.user.empresa_id
            )
            .select_related("conductor__usuario", "vehiculo", "cierre_caja__responsable")
            .order_by("-hora_inicio", "-id")[:100]
        )
        return Response(TurnoSerializer(consulta, many=True).data)


class CierreCajaView(APIView):
    permission_classes = SOLO_ADMIN

    @extend_schema(
        tags=["turnos"],
        summary="Cerrar la caja de un turno terminado (CP-36)",
        request=CerrarCajaSerializer,
        responses={
            201: CierreCajaSerializer,
            400: OpenApiResponse(description="Falta la observación"),
            409: CONFLICTO,
        },
        description="Fija el efectivo registrado de los viajes del turno, calcula diferencia = rendido - "
        "registrado y lo deja en AUDITORIA (`CIERRE_CAJA`). Uno por turno.",
    )
    def post(self, request, pk):
        datos = CerrarCajaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        cierre = turnos.cerrar_caja(
            pk,
            empresa_id=request.user.empresa_id,
            monto_rendido=datos.validated_data["monto_rendido"],
            observacion=datos.validated_data.get("observacion"),
            usuario=request.user,
        )
        return Response(CierreCajaSerializer(cierre).data, status=status.HTTP_201_CREATED)
