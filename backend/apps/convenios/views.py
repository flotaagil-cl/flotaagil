import django_filters
from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.comun.permisos import AisladoPorEmpresaMixin, con_roles
from apps.cuentas.models import Rol

from . import servicios
from .models import Convenio
from .serializers import (
    ConvenioCreadoSerializer,
    ConvenioCrearSerializer,
    ConvenioDetalleSerializer,
    ConvenioEditarSerializer,
    ConvenioSerializer,
    PasswordNuevaSerializer,
)


class ConvenioFiltro(django_filters.FilterSet):
    activo = django_filters.BooleanFilter()
    q = django_filters.CharFilter(method="buscar", help_text="Cliente o RUT")

    class Meta:
        model = Convenio
        fields = []

    def buscar(self, queryset, nombre, valor):
        valor = valor.strip()
        if not valor:
            return queryset
        return queryset.filter(Q(cliente_nombre__icontains=valor) | Q(cliente_rut__icontains=valor))


@extend_schema_view(
    list=extend_schema(summary="Listar convenios con su volumen de reservas", tags=["convenios"]),
    retrieve=extend_schema(
        summary="Detalle de un convenio, con el token de su link",
        tags=["convenios"],
        responses=ConvenioDetalleSerializer,
    ),
)
class ConvenioViewSet(
    AisladoPorEmpresaMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """HU-11: solo el administrador de la empresa."""

    queryset = Convenio.objects.annotate(reservas=Count("viajes")).order_by("cliente_nombre", "id")
    permission_classes = [con_roles(Rol.ADMINISTRADOR)]
    filterset_class = ConvenioFiltro
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        return ConvenioDetalleSerializer if self.action == "retrieve" else ConvenioSerializer

    def _detalle(self, convenio):
        return ConvenioDetalleSerializer(self.get_queryset().get(pk=convenio.pk)).data

    @extend_schema(
        summary="Crear un convenio",
        tags=["convenios"],
        request=ConvenioCrearSerializer,
        responses={201: ConvenioCreadoSerializer},
        description="Genera el token del link (256 bits) y la contraseña, que se entrega una sola vez.",
    )
    def create(self, request):
        entrada = ConvenioCrearSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        convenio, password = servicios.crear(
            request.user.empresa, dict(entrada.validated_data), usuario=request.user
        )
        return Response({**self._detalle(convenio), "password": password}, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Editar, activar o desactivar un convenio",
        tags=["convenios"],
        request=ConvenioEditarSerializer(partial=True),
        responses=ConvenioDetalleSerializer,
        description="Desactivar invalida el link sin afectar el historial (RN-08). Se audita (RN-12).",
    )
    def partial_update(self, request, pk=None):
        convenio = self.get_object()
        entrada = ConvenioEditarSerializer(data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        servicios.editar(convenio, dict(entrada.validated_data), usuario=request.user)
        return Response(self._detalle(convenio))

    @extend_schema(
        summary="Rotar la contraseña del convenio",
        tags=["convenios"],
        request=None,
        responses=PasswordNuevaSerializer,
        description="La anterior deja de servir. La nueva se entrega una sola vez. Se audita (RN-12).",
    )
    @action(detail=True, methods=["post"], url_path="rotar-password")
    def rotar_password(self, request, pk=None):
        password = servicios.rotar_password(self.get_object(), usuario=request.user)
        return Response({"password": password})
