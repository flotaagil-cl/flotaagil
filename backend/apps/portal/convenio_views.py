"""HU-25: API pública del link del convenio. La protege el token del link, la contraseña y el bloqueo."""

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from apps.cuentas.origen import OrigenPanelPermitido

from . import convenio as servicios
from .serializers import EmpresaPublicaSerializer, SolicitudSerializer
from .servicios import LimiteIP
from .views import PortalPorHora, PortalPorMinuto, _VistaPortal

COOKIE = "convenio_sesion"
RUTA_COOKIE = "/api/convenio/"


class AccesoConvenioSerializer(EmpresaPublicaSerializer):
    """Sin sesión no revela de qué cliente es el convenio."""

    sesion_activa = serializers.BooleanField()
    cliente_nombre = serializers.CharField(allow_null=True)

    class Meta(EmpresaPublicaSerializer.Meta):
        fields = [*EmpresaPublicaSerializer.Meta.fields, "sesion_activa", "cliente_nombre"]


class ContrasenaSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class SesionConvenioSerializer(serializers.Serializer):
    cliente_nombre = serializers.CharField()


class SolicitudConvenioRespuestaSerializer(serializers.Serializer):
    estado = serializers.CharField()
    recogida_en = serializers.DateTimeField()
    mensaje = serializers.CharField()


def _poner_sesion(respuesta: Response, convenio) -> Response:
    respuesta.set_cookie(
        COOKIE,
        servicios.emitir_sesion(convenio),
        max_age=int(settings.CONVENIO_SESION.total_seconds()),
        httponly=True,
        secure=settings.JWT_COOKIE["secure"],
        samesite="Strict",
        path=RUTA_COOKIE,
    )
    return respuesta


NO_DISPONIBLE = OpenApiResponse(description="Link inexistente o convenio inactivo (RN-08)")


class _VistaConvenio(_VistaPortal):
    def throttled(self, request, wait):
        raise LimiteIP(wait)


class AccesoConvenioView(_VistaConvenio):
    @extend_schema(
        tags=["convenio"],
        summary="Estado del link del convenio",
        responses={200: AccesoConvenioSerializer, 404: NO_DISPONIBLE},
        description="Datos para el formulario y si hay sesión. Con sesión, cuenta como uso y la renueva.",
    )
    def get(self, request, token):
        convenio = servicios.convenio_del_link(token)
        activa = servicios.sesion_valida(request.COOKIES.get(COOKIE), convenio)
        datos = {
            **EmpresaPublicaSerializer(convenio.empresa).data,
            "sesion_activa": activa,
            "cliente_nombre": convenio.cliente_nombre if activa else None,
        }
        respuesta = Response(datos)
        return _poner_sesion(respuesta, convenio) if activa else respuesta


class SesionConvenioView(_VistaConvenio):
    permission_classes = [OrigenPanelPermitido]
    throttle_classes = [PortalPorMinuto, PortalPorHora]

    @extend_schema(
        tags=["convenio"],
        summary="Entrar con la contraseña del convenio",
        request=ContrasenaSerializer,
        responses={
            200: SesionConvenioSerializer,
            401: OpenApiResponse(description="`credenciales_invalidas`"),
            404: NO_DISPONIBLE,
            423: OpenApiResponse(description="`convenio_bloqueado`: 5 intentos fallidos (DC-27)"),
        },
        description="Deja la sesión en una cookie httpOnly, que vence tras 2 h sin uso (configurable).",
    )
    def post(self, request, token):
        convenio = servicios.convenio_del_link(token)
        entrada = ContrasenaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        servicios.intentar_acceso(convenio, entrada.validated_data["password"])
        convenio.refresh_from_db(fields=["password_hash"])
        return _poner_sesion(Response({"cliente_nombre": convenio.cliente_nombre}), convenio)


class SalirConvenioView(_VistaConvenio):
    permission_classes = [OrigenPanelPermitido]

    @extend_schema(
        tags=["convenio"],
        summary="Cerrar la sesión del convenio",
        request=None,
        responses={204: None},
    )
    def post(self, request, token):
        respuesta = Response(status=status.HTTP_204_NO_CONTENT)
        respuesta.delete_cookie(COOKIE, path=RUTA_COOKIE, samesite="Strict")
        return respuesta


class SolicitudConvenioView(_VistaConvenio):
    permission_classes = [OrigenPanelPermitido]
    throttle_classes = [PortalPorMinuto, PortalPorHora]

    @extend_schema(
        tags=["convenio"],
        summary="Solicitar un viaje a nombre del convenio",
        request=SolicitudSerializer,
        responses={
            201: SolicitudConvenioRespuestaSerializer,
            401: OpenApiResponse(description="`sesion_convenio_vencida`"),
            404: NO_DISPONIBLE,
        },
        description="Queda SOLICITADO y con el convenio, sin verificar el teléfono por WhatsApp (RN-07).",
    )
    def post(self, request, token):
        convenio = servicios.convenio_del_link(token)
        if not servicios.sesion_valida(request.COOKIES.get(COOKIE), convenio):
            raise servicios.SesionVencida()
        entrada = SolicitudSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        _, datos = servicios.crear_solicitud(convenio, dict(entrada.validated_data))
        respuesta = Response(SolicitudConvenioRespuestaSerializer(datos).data, status=status.HTTP_201_CREATED)
        return _poner_sesion(respuesta, convenio)
