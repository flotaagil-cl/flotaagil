"""HU-36: API de usuarios del panel (`/api/usuarios/`). Solo administrador; otra empresa responde 404
(RN-13)."""

from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.comun.permisos import AisladoPorEmpresaMixin, con_roles

from . import usuarios_panel as servicios
from .credenciales import estado_de_acceso
from .models import Rol, Usuario

CONFLICTO = OpenApiResponse(
    description="`propio_rol`, `propia_cuenta` o `ultimo_administrador` (la empresa debe tener uno activo)."
)


class UsuarioPanelSerializer(serializers.ModelSerializer):
    acceso = serializers.SerializerMethodField(help_text="SIN_PASSWORD, TEMPORAL, TEMPORAL_VENCIDA o ACTIVA")

    class Meta:
        model = Usuario
        fields = ["id", "nombre", "email", "rol", "activo", "acceso", "last_login"]
        read_only_fields = fields

    def get_acceso(self, usuario) -> str:
        return estado_de_acceso(usuario)


class UsuarioPanelCrearSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=80)
    email = serializers.EmailField(max_length=120)
    rol = serializers.ChoiceField(choices=[Rol.ADMINISTRADOR, Rol.DESPACHADOR])

    def validate_nombre(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("Ingresa el nombre.")
        return valor


class UsuarioPanelEditarSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=80, required=False)
    rol = serializers.ChoiceField(choices=[Rol.ADMINISTRADOR, Rol.DESPACHADOR], required=False)

    def validate_nombre(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("Ingresa el nombre.")
        return valor


class UsuarioCreadoSerializer(UsuarioPanelSerializer):
    password_temporal = serializers.CharField(read_only=True, help_text="Se muestra una sola vez")
    vence_en = serializers.DateTimeField(read_only=True)

    class Meta(UsuarioPanelSerializer.Meta):
        fields = [*UsuarioPanelSerializer.Meta.fields, "password_temporal", "vence_en"]
        read_only_fields = fields


class TemporalSerializer(serializers.Serializer):
    password_temporal = serializers.CharField(help_text="Se muestra una sola vez")
    vence_en = serializers.DateTimeField()


@extend_schema_view(
    list=extend_schema(summary="Usuarios del panel de mi empresa", tags=["usuarios"]),
    retrieve=extend_schema(summary="Detalle de un usuario del panel", tags=["usuarios"]),
)
class UsuarioPanelViewSet(
    AisladoPorEmpresaMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """HU-36: administradores y despachadores de la empresa. Ni conductores, ni convenios, ni pasajeros."""

    queryset = Usuario.objects.filter(rol__in=servicios.ROLES).order_by("nombre", "id")
    serializer_class = UsuarioPanelSerializer
    permission_classes = [con_roles(Rol.ADMINISTRADOR)]
    http_method_names = ["get", "post", "patch", "head", "options"]

    @staticmethod
    def _sin_cache(respuesta: Response) -> Response:
        respuesta["Cache-Control"] = "no-store"
        return respuesta

    @extend_schema(
        summary="Crear un usuario del panel",
        tags=["usuarios"],
        request=UsuarioPanelCrearSerializer,
        responses={
            201: UsuarioCreadoSerializer,
            400: OpenApiResponse(description="Datos inválidos o correo usado"),
        },
        description="Genera una contraseña temporal (DC-14) que se muestra una sola vez. Queda en auditoría.",
    )
    def create(self, request):
        entrada = UsuarioPanelCrearSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        usuario, password, vence = servicios.crear(
            request.user.empresa, entrada.validated_data, por=request.user
        )
        usuario.refresh_from_db()
        datos = {**UsuarioPanelSerializer(usuario).data, "password_temporal": password, "vence_en": vence}
        return self._sin_cache(Response(datos, status=status.HTTP_201_CREATED))

    @extend_schema(
        summary="Editar nombre o rol",
        tags=["usuarios"],
        request=UsuarioPanelEditarSerializer,
        responses={200: UsuarioPanelSerializer, 409: CONFLICTO},
        description="Cambiar el rol cierra las sesiones del usuario. Queda en auditoría.",
    )
    def partial_update(self, request, pk=None):
        usuario = self.get_object()
        entrada = UsuarioPanelEditarSerializer(data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        usuario = servicios.editar(usuario, entrada.validated_data, por=request.user)
        return Response(UsuarioPanelSerializer(usuario).data)

    @extend_schema(
        summary="Desactivar un usuario del panel",
        tags=["usuarios"],
        request=None,
        responses={200: UsuarioPanelSerializer, 409: CONFLICTO},
        description="Revoca sus sesiones al instante. Queda en auditoría.",
    )
    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        usuario = servicios.cambiar_habilitacion(self.get_object(), False, por=request.user)
        return Response(UsuarioPanelSerializer(usuario).data)

    @extend_schema(
        summary="Activar un usuario del panel",
        tags=["usuarios"],
        request=None,
        responses=UsuarioPanelSerializer,
    )
    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        usuario = servicios.cambiar_habilitacion(self.get_object(), True, por=request.user)
        return Response(UsuarioPanelSerializer(usuario).data)

    @extend_schema(
        summary="Restablecer la contraseña con una temporal",
        tags=["usuarios"],
        request=None,
        responses={201: TemporalSerializer},
        description="DC-14: la temporal se muestra una sola vez y cierra sus sesiones.",
    )
    @action(detail=True, methods=["post"])
    def password(self, request, pk=None):
        password, vence = servicios.restablecer(self.get_object(), por=request.user)
        return self._sin_cache(
            Response({"password_temporal": password, "vence_en": vence}, status=status.HTTP_201_CREATED)
        )
