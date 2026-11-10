import django_filters
from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.auditoria.models import Auditoria, Entidad
from apps.comun.permisos import AisladoPorEmpresaMixin, con_roles
from apps.cuentas.models import Rol
from apps.flota.serializers import PasswordTemporalSerializer

from . import servicios
from .models import Convenio, EstadoConvenio
from .serializers import (
    ConvenioDetalleSerializer,
    ConvenioEditarSerializer,
    ConvenioSerializer,
    RechazoSerializer,
    RegistroAuditoriaSerializer,
)

CONFLICTO = OpenApiResponse(description="`estado_convenio`: el convenio no admite la acción en su estado.")


class ConvenioFiltro(django_filters.FilterSet):
    estado = django_filters.ChoiceFilter(choices=EstadoConvenio.choices)
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
        summary="Detalle de un convenio",
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

    queryset = (
        Convenio.objects.annotate(reservas=Count("viajes"))
        .select_related("usuario", "revisado_por")
        .order_by("cliente_nombre", "id")
    )
    permission_classes = [con_roles(Rol.ADMINISTRADOR)]
    filterset_class = ConvenioFiltro
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        return ConvenioDetalleSerializer if self.action == "retrieve" else ConvenioSerializer

    def _detalle(self, convenio):
        return ConvenioDetalleSerializer(self.get_queryset().get(pk=convenio.pk)).data

    @extend_schema(
        summary="Editar los datos de un convenio",
        tags=["convenios"],
        request=ConvenioEditarSerializer(partial=True),
        responses=ConvenioDetalleSerializer,
        description="Razón social, RUT, dirección y encargado. El estado cambia con sus acciones. Se audita.",
    )
    def partial_update(self, request, pk=None):
        convenio = self.get_object()
        entrada = ConvenioEditarSerializer(data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        servicios.editar(convenio, dict(entrada.validated_data), usuario=request.user)
        return Response(self._detalle(convenio))

    def _accion(self, funcion, **kwargs):
        convenio = self.get_object()
        funcion(convenio, usuario=self.request.user, **kwargs)
        return Response(self._detalle(convenio))

    @extend_schema(
        summary="Aprobar un convenio en revisión",
        tags=["convenios"],
        request=None,
        responses={200: ConvenioDetalleSerializer, 409: CONFLICTO},
        description="Queda en auditoría y se avisa al encargado por correo.",
    )
    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        return self._accion(servicios.aprobar)

    @extend_schema(
        summary="Rechazar un convenio en revisión",
        tags=["convenios"],
        request=RechazoSerializer,
        responses={200: ConvenioDetalleSerializer, 409: CONFLICTO},
        description="Exige motivo; queda en auditoría y se avisa al encargado por correo.",
    )
    @action(detail=True, methods=["post"])
    def rechazar(self, request, pk=None):
        return self._accion(servicios.rechazar, motivo=request.data.get("motivo", ""))

    @extend_schema(
        summary="Desactivar un convenio",
        tags=["convenios"],
        request=None,
        responses={200: ConvenioDetalleSerializer, 409: CONFLICTO},
        description="RN-08: la cuenta pierde el acceso al instante; el historial no cambia. Se audita.",
    )
    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        return self._accion(servicios.desactivar)

    @extend_schema(
        summary="Reactivar un convenio",
        tags=["convenios"],
        request=None,
        responses={200: ConvenioDetalleSerializer, 409: CONFLICTO},
    )
    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        return self._accion(servicios.activar)

    @extend_schema(
        summary="Restablecer la contraseña de la cuenta del convenio",
        tags=["convenios"],
        request=None,
        responses={201: PasswordTemporalSerializer, 409: CONFLICTO},
        description="DC-14: temporal que se muestra una vez y obliga a cambiarla. Se audita (RN-12).",
    )
    @action(detail=True, methods=["post"], url_path="restablecer-password")
    def restablecer_password(self, request, pk=None):
        password, vence = servicios.restablecer_password(self.get_object(), usuario=request.user)
        respuesta = Response(
            {"password_temporal": password, "vence_en": vence}, status=status.HTTP_201_CREATED
        )
        respuesta["Cache-Control"] = "no-store"
        return respuesta

    @extend_schema(
        summary="Auditoría del convenio",
        tags=["convenios"],
        responses=RegistroAuditoriaSerializer(many=True),
        description="Quién y cuándo cambió el convenio, del más nuevo al más antiguo (RN-12). Solo lectura.",
    )
    @action(detail=True, methods=["get"], filterset_class=None, filter_backends=[])
    def auditoria(self, request, pk=None):
        convenio = self.get_object()
        registros = (
            Auditoria.objects.filter(entidad=Entidad.CONVENIO, entidad_id=convenio.pk)
            .select_related("usuario")
            .order_by("-creado_en", "-id")
        )
        pagina = self.paginate_queryset(registros)
        return self.get_paginated_response(RegistroAuditoriaSerializer(pagina, many=True).data)
