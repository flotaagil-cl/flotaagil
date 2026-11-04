"""HU-01: indicadores del panel. Los números salen de aquí; /ws/indicadores/ solo avisa que cambiaron.

Reservas del día: por fecha de recogida en hora de Chile, igual que el atajo «Reservas de hoy» del listado.
Vehículos en línea (DC-28): activos y declarados por un conductor en turno, con su cuenta activa.
"""

from django.db.models import Count
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.permisos import con_roles
from apps.cuentas.models import Rol
from apps.flota.models import Conductor, Vehiculo
from apps.flota.tiempo_real import EN_TURNO

from .models import EstadoViaje, Viaje


class ReservasPorEstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=EstadoViaje.choices)
    cantidad = serializers.IntegerField()


class IndicadoresReservasSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    por_estado = ReservasPorEstadoSerializer(many=True, help_text="Todos los estados, también en cero")


class IndicadoresVehiculosSerializer(serializers.Serializer):
    en_linea = serializers.IntegerField()
    fuera_de_linea = serializers.IntegerField()


class IndicadoresSerializer(serializers.Serializer):
    fecha = serializers.DateField(help_text="Hoy, en hora de Chile")
    reservas = IndicadoresReservasSerializer()
    vehiculos = IndicadoresVehiculosSerializer()


def calcular(empresa_id: int) -> dict:
    hoy = timezone.localdate()
    conteos = dict(
        Viaje.objects.filter(empresa_id=empresa_id, recogida_en__date=hoy)
        .order_by()
        .values_list("estado")
        .annotate(n=Count("pk"))
    )
    activos = Vehiculo.objects.filter(empresa_id=empresa_id, activo=True).count()
    en_linea = (
        Conductor.objects.filter(
            usuario__empresa_id=empresa_id,
            usuario__activo=True,
            estado__in=EN_TURNO,
            vehiculo_activo__activo=True,
        )
        .values("vehiculo_activo")
        .distinct()
        .count()
    )
    return {
        "fecha": hoy,
        "reservas": {
            "total": sum(conteos.values()),
            "por_estado": [{"estado": e, "cantidad": conteos.get(e, 0)} for e in EstadoViaje.values],
        },
        "vehiculos": {"en_linea": en_linea, "fuera_de_linea": activos - en_linea},
    }


class IndicadoresView(APIView):
    permission_classes = [con_roles(Rol.ADMINISTRADOR, Rol.DESPACHADOR)]

    @extend_schema(
        tags=["indicadores"],
        summary="Reservas del día por estado y vehículos en línea",
        responses=IndicadoresSerializer,
    )
    def get(self, request):
        return Response(IndicadoresSerializer(calcular(request.user.empresa_id)).data)
