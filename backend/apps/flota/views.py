"""API de flota (HU-10): vehículos, conductores con sus cuentas y asociación conductor-vehículo.

Solo el administrador, y solo registros de su empresa (RN-13). No hay borrado: un vehículo se desactiva y la
cuenta de un conductor se deshabilita.
"""

from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.comun.permisos import AisladoPorEmpresaMixin, con_roles
from apps.cuentas.models import Rol

from . import importacion, servicios, turnos
from .filtros import ConductorFiltro, VehiculoFiltro
from .models import Conductor, ConductorVehiculo, Vehiculo
from .serializers import (
    AsociarVehiculoSerializer,
    ConductorCrearSerializer,
    ConductorEditarSerializer,
    ConductorSerializer,
    ImportarSerializer,
    InformeImportacionSerializer,
    PasswordTemporalSerializer,
    VehiculoCrearSerializer,
    VehiculoEditarSerializer,
    VehiculoSerializer,
)

EN_VIAJE = OpenApiResponse(description="`conductor_en_viaje`: el conductor está en viaje.")
EN_USO = OpenApiResponse(
    description="`flota_en_uso`: el vehículo está declarado en un turno o tiene un viaje en curso."
)
SOLO_ADMIN = [con_roles(Rol.ADMINISTRADOR)]


def _importar(request, formato, crear):
    """Informe del CSV (200), o con `confirmar` crea todo (201) o nada (400 con el informe)."""
    entrada = ImportarSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    filas, validos = importacion.validar(
        importacion.leer_filas(entrada.validated_data["archivo"], formato), formato
    )
    con_errores = sum(1 for fila in filas if fila["errores"])
    informe = {"filas": filas, "validas": len(validos), "con_errores": con_errores, "creados": 0}
    if not entrada.validated_data["confirmar"]:
        return Response(informe)
    if con_errores:
        return Response(informe, status=status.HTTP_400_BAD_REQUEST)
    informe["creados"] = len(crear(request.user.empresa, validos, usuario=request.user))
    return Response(informe, status=status.HTTP_201_CREATED)


def _documentar_importacion(que: str):
    return extend_schema(
        summary=f"Carga inicial de {que} por CSV",
        tags=["flota"],
        request={"multipart/form-data": ImportarSerializer},
        responses={
            200: OpenApiResponse(InformeImportacionSerializer, description="Informe sin crear nada."),
            201: OpenApiResponse(InformeImportacionSerializer, description="Todos creados."),
            400: OpenApiResponse(
                InformeImportacionSerializer,
                description="Con `confirmar` y filas con errores: no se crea ninguno. Si el archivo no "
                "sirve, el error viene en `archivo`.",
            ),
        },
        description=importacion.__doc__,
    )


@extend_schema_view(
    list=extend_schema(summary="Listar vehículos", tags=["flota"]),
    retrieve=extend_schema(summary="Detalle de un vehículo", tags=["flota"]),
)
class VehiculoViewSet(
    AisladoPorEmpresaMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Vehiculo.objects.prefetch_related(
        Prefetch("asociaciones", queryset=ConductorVehiculo.objects.select_related("conductor__usuario"))
    )
    serializer_class = VehiculoSerializer
    permission_classes = SOLO_ADMIN
    filterset_class = VehiculoFiltro
    http_method_names = ["get", "post", "patch", "head", "options"]

    def _detalle(self, vehiculo, codigo=status.HTTP_200_OK):
        return Response(VehiculoSerializer(self.get_queryset().get(pk=vehiculo.pk)).data, status=codigo)

    @extend_schema(
        summary="Registrar un vehículo",
        tags=["flota"],
        request=VehiculoCrearSerializer,
        responses={201: VehiculoSerializer},
    )
    def create(self, request):
        entrada = VehiculoCrearSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        (vehiculo,) = servicios.crear_vehiculos(
            request.user.empresa, [dict(entrada.validated_data)], usuario=request.user
        )
        return self._detalle(vehiculo, status.HTTP_201_CREATED)

    @extend_schema(
        summary="Editar, activar o desactivar un vehículo",
        tags=["flota"],
        request=VehiculoEditarSerializer,
        responses={200: VehiculoSerializer, 409: EN_USO},
        description="Desactivar quita el vehículo como declarado a los conductores No disponibles. "
        "Responde 409 si está declarado en un turno (Disponible o En viaje) o tiene un viaje en curso.",
    )
    def partial_update(self, request, pk=None):
        vehiculo = self.get_object()
        entrada = VehiculoEditarSerializer(vehiculo, data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        servicios.editar_vehiculo(vehiculo, dict(entrada.validated_data), usuario=request.user)
        return self._detalle(vehiculo)

    @_documentar_importacion("vehículos")
    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser, JSONParser])
    def importar(self, request):
        return _importar(request, importacion.VEHICULOS, servicios.crear_vehiculos)


@extend_schema_view(
    list=extend_schema(summary="Listar conductores", tags=["flota"]),
    retrieve=extend_schema(summary="Detalle de un conductor con sus vehículos", tags=["flota"]),
)
class ConductorViewSet(
    AisladoPorEmpresaMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Conductor.objects.select_related("usuario", "vehiculo_activo").prefetch_related(
        Prefetch("asociaciones", queryset=ConductorVehiculo.objects.select_related("vehiculo"))
    )
    campo_empresa = "usuario__empresa"
    serializer_class = ConductorSerializer
    permission_classes = SOLO_ADMIN
    filterset_class = ConductorFiltro
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return super().get_queryset().order_by("usuario__nombre", "id")

    def _detalle(self, conductor, codigo=status.HTTP_200_OK):
        return Response(ConductorSerializer(self.get_queryset().get(pk=conductor.pk)).data, status=codigo)

    @extend_schema(
        summary="Registrar un conductor con su cuenta",
        tags=["flota"],
        request=ConductorCrearSerializer,
        responses={201: ConductorSerializer},
        description="La cuenta (rol CONDUCTOR) queda sin contraseña utilizable: el administrador genera una "
        "temporal con `password/`.",
    )
    def create(self, request):
        entrada = ConductorCrearSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        (conductor,) = servicios.crear_conductores(
            request.user.empresa, [dict(entrada.validated_data)], usuario=request.user
        )
        return self._detalle(conductor, status.HTTP_201_CREATED)

    @_documentar_importacion("conductores")
    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser, JSONParser])
    def importar(self, request):
        return _importar(request, importacion.CONDUCTORES, servicios.crear_conductores)

    @extend_schema(
        summary="Generar o restablecer la contraseña temporal",
        tags=["flota"],
        request=None,
        responses={201: PasswordTemporalSerializer, 409: EN_VIAJE},
        description="Se muestra una sola vez y vence a las PASSWORD_TEMPORAL_HORAS (72 por defecto). "
        "Cierra todas "
        "las sesiones del conductor; al ingresar debe cambiarla (403 `cambio_password_requerido` en el resto "
        "de la API). Queda en auditoría (RN-12).",
    )
    @action(detail=True, methods=["post"])
    def password(self, request, pk=None):
        password, vence = servicios.generar_password(self.get_object(), usuario=request.user)
        respuesta = Response(
            {"password_temporal": password, "vence_en": vence}, status=status.HTTP_201_CREATED
        )
        respuesta["Cache-Control"] = "no-store"
        return respuesta

    @extend_schema(
        summary="Deshabilitar la cuenta del conductor",
        tags=["flota"],
        request=None,
        responses={200: ConductorSerializer, 409: EN_VIAJE},
        description="No puede ingresar, se cierran todas sus sesiones y queda No disponible. "
        "Auditoría (RN-12).",
    )
    @action(detail=True, methods=["post"])
    def deshabilitar(self, request, pk=None):
        conductor = self.get_object()
        servicios.cambiar_habilitacion(conductor, False, usuario=request.user)
        return self._detalle(conductor)

    @extend_schema(
        summary="Terminar el turno de un conductor (cierre administrativo)",
        tags=["turnos"],
        request=inline_serializer("TerminarTurno", {"motivo": serializers.CharField(max_length=200)}),
        responses={
            200: ConductorSerializer,
            400: OpenApiResponse(description="Falta el motivo"),
            409: EN_VIAJE,
        },
        description="HU-31 (DC-32): para un conductor que olvidó terminar su turno. Queda No disponible y el "
        "turno se cierra con CIERRE_ADMINISTRATIVO, en auditoría. 409 `en_viaje` o `sin_turno`.",
    )
    @action(detail=True, methods=["post"], url_path="terminar-turno")
    def terminar_turno(self, request, pk=None):
        conductor = self.get_object()
        turnos.cerrar_administrativo(conductor, motivo=request.data.get("motivo", ""), usuario=request.user)
        return self._detalle(conductor)

    @extend_schema(
        summary="Habilitar la cuenta del conductor",
        tags=["flota"],
        request=None,
        responses={200: ConductorSerializer},
    )
    @action(detail=True, methods=["post"])
    def habilitar(self, request, pk=None):
        conductor = self.get_object()
        servicios.cambiar_habilitacion(conductor, True, usuario=request.user)
        return self._detalle(conductor)

    @extend_schema(
        summary="Editar los datos de un conductor",
        tags=["flota"],
        request=ConductorEditarSerializer(partial=True),
        responses={200: ConductorSerializer},
        description="Nombre, RUT, teléfono y licencia. El email y la contraseña no se editan aquí.",
    )
    def partial_update(self, request, pk=None):
        conductor = self.get_object()
        entrada = ConductorEditarSerializer(data=request.data, partial=True, context={"conductor": conductor})
        entrada.is_valid(raise_exception=True)
        servicios.editar_conductor(conductor, dict(entrada.validated_data), usuario=request.user)
        return self._detalle(conductor)

    @extend_schema(
        summary="Asociar un vehículo al conductor",
        tags=["flota"],
        request=AsociarVehiculoSerializer,
        responses={201: ConductorSerializer},
    )
    @action(detail=True, methods=["post"], url_path="vehiculos")
    def asociar(self, request, pk=None):
        conductor = self.get_object()
        entrada = AsociarVehiculoSerializer(data=request.data, context={"empresa": request.user.empresa})
        entrada.is_valid(raise_exception=True)
        servicios.asociar_vehiculo(conductor, entrada.validated_data["vehiculo"], usuario=request.user)
        return self._detalle(conductor, status.HTTP_201_CREATED)

    @extend_schema(
        summary="Quitar un vehículo al conductor",
        tags=["flota"],
        request=None,
        responses={200: ConductorSerializer, 409: EN_USO},
        description="Si era su vehículo declarado y el conductor está No disponible, la declaración "
        "se borra. Responde 409 si está en turno con ese vehículo.",
    )
    @action(detail=True, methods=["delete"], url_path=r"vehiculos/(?P<vehiculo_id>\d+)")
    def desasociar(self, request, pk=None, vehiculo_id=None):
        conductor = self.get_object()
        vehiculo = Vehiculo.objects.filter(empresa=request.user.empresa, pk=vehiculo_id).first()
        if vehiculo is None:
            raise NotFound()
        servicios.desasociar_vehiculo(conductor, vehiculo, usuario=request.user)
        return self._detalle(conductor)
