from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.comun.permisos import AisladoPorEmpresaMixin, con_roles
from apps.cuentas.models import Rol

from . import alertas
from .models import AlertaVuelo
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
