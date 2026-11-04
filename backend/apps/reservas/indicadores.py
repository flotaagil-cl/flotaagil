"""HU-01: indicadores del panel. Los números salen de aquí; /ws/indicadores/ solo avisa que cambiaron.

Reservas del día: por fecha de recogida en hora de Chile, igual que el atajo «Reservas de hoy» del listado.
Vehículos en línea (DC-28): activos y declarados por un conductor en turno, con su cuenta activa. Quedan «sin
señal» si su última posición tiene más de POSICION_CONFIABLE_SEGUNDOS o no tienen ninguna, como en HU-02.
"""

from datetime import timedelta

from django.conf import settings
from django.db.models import Count, OuterRef, Subquery
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.permisos import con_roles
from apps.cuentas.models import Rol
from apps.flota.models import Conductor, PosicionGps, Vehiculo
from apps.flota.tiempo_real import EN_TURNO

from .models import EstadoViaje, Viaje


class ReservasPorEstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=EstadoViaje.choices)
    cantidad = serializers.IntegerField()


class IndicadoresReservasSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    por_estado = ReservasPorEstadoSerializer(many=True, help_text="Todos los estados, también en cero")


class IndicadoresVehiculosSerializer(serializers.Serializer):
    en_linea = serializers.IntegerField(help_text="Con señal más sin señal")
    en_linea_con_senal = serializers.IntegerField()
    en_linea_sin_senal = serializers.IntegerField(help_text="Sin posición hace más de 60 s, o sin ninguna")
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
    ultima = PosicionGps.objects.filter(conductor=OuterRef("pk")).order_by("-registrada_en")
    en_linea = dict(
        Conductor.objects.filter(
            usuario__empresa_id=empresa_id,
            usuario__activo=True,
            estado__in=EN_TURNO,
            vehiculo_activo__activo=True,
        )
        .annotate(ultima=Subquery(ultima.values("registrada_en")[:1]))
        .values_list("vehiculo_activo", "ultima")
    )
    limite = timezone.now() - timedelta(seconds=settings.POSICION_CONFIABLE_SEGUNDOS)
    con_senal = sum(1 for instante in en_linea.values() if instante is not None and instante >= limite)
    return {
        "fecha": hoy,
        "reservas": {
            "total": sum(conteos.values()),
            "por_estado": [{"estado": e, "cantidad": conteos.get(e, 0)} for e in EstadoViaje.values],
        },
        "vehiculos": {
            "en_linea": len(en_linea),
            "en_linea_con_senal": con_senal,
            "en_linea_sin_senal": len(en_linea) - con_senal,
            "fuera_de_linea": activos - len(en_linea),
        },
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
