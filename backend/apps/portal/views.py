"""Portal público del pasajero (HU-19). Sin autenticación: se protege con throttling por IP,
límite por teléfono y un campo trampa."""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.comun.excepciones import error_con_codigo
from apps.comun.validadores import normalizar_telefono, validar_telefono_e164
from apps.convenios import servicios as convenios
from apps.convenios.serializers import RegistroConvenioSerializer
from apps.cuentas.models import Empresa
from apps.cuentas.serializers import ErrorSerializer
from apps.integraciones.notificaciones import enmascarar_telefono as enmascarar
from apps.reservas import cuentas_pasajero

from . import servicios
from .serializers import (
    CrearCuentaSerializer,
    EmpresaPublicaSerializer,
)


class PortalPorMinuto(AnonRateThrottle):
    scope = "portal_minuto"


class PortalPorHora(AnonRateThrottle):
    scope = "portal_hora"


def _empresa(slug: str) -> Empresa:
    return get_object_or_404(Empresa.objects.select_related("configuracion"), slug=slug, activa=True)


class _VistaPortal(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get_exception_handler(self):
        # Los errores con solo `detail` llevan `code` (p. ej. limite_ip / limite_telefono en el 429).
        return error_con_codigo


class EmpresaPortalView(_VistaPortal):
    @extend_schema(
        tags=["portal"],
        summary="Datos públicos de la empresa para el formulario",
        responses={
            200: EmpresaPublicaSerializer,
            404: OpenApiResponse(description="Empresa inexistente o inactiva"),
        },
    )
    def get(self, request, slug):
        return Response(EmpresaPublicaSerializer(_empresa(slug)).data)


LIMITE = OpenApiResponse(
    response=ErrorSerializer,
    description=(
        "Demasiadas solicitudes. `code`: `limite_ip` (desde la misma IP; con el wifi del aeropuerto muchos "
        "pasajeros la comparten) o `limite_telefono` (varias solicitudes con el mismo número)."
    ),
    examples=[
        OpenApiExample(
            "Por IP",
            value={"detail": servicios.LimiteIP.default_detail, "code": "limite_ip"},
        ),
        OpenApiExample(
            "Por teléfono",
            value={"detail": servicios.LimiteTelefono.default_detail, "code": "limite_telefono"},
        ),
    ],
)


class RegistroEmpresaView(_VistaPortal):
    """HU-34: la empresa cliente se registra y queda EN_REVISION. Mismos límites que el portal y campo
    trampa."""

    throttle_classes = [PortalPorMinuto, PortalPorHora]

    def throttled(self, request, wait):
        raise servicios.LimiteIP(wait)

    @extend_schema(
        tags=["portal"],
        summary="Registrar una empresa con convenio",
        request=RegistroConvenioSerializer,
        responses={
            201: OpenApiResponse(
                description="Registrada: queda en revisión hasta que el administrador la apruebe"
            ),
            400: OpenApiResponse(description="Datos inválidos o correo no disponible"),
            404: OpenApiResponse(description="Empresa inexistente o inactiva"),
            429: LIMITE,
        },
    )
    def post(self, request, slug):
        empresa = _empresa(slug)
        entrada = RegistroConvenioSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        if not entrada.validated_data.get("sitio_web"):
            convenios.registrar(empresa, entrada.validated_data)
        # Con el campo trampa lleno se responde igual, sin crear nada.
        return Response(
            {
                "estado": "EN_REVISION",
                "mensaje": "Recibimos el registro. Te avisaremos por correo cuando se revise.",
            },
            status=status.HTTP_201_CREATED,
        )


class CrearCuentaView(_VistaPortal):
    """HU-35: crea la cuenta pendiente y envía el WhatsApp para confirmarla. Mismos límites que el portal."""

    throttle_classes = [PortalPorMinuto, PortalPorHora]

    def throttled(self, request, wait):
        raise servicios.LimiteIP(wait)

    @extend_schema(
        tags=["portal"],
        summary="Crear una cuenta de pasajero",
        request=CrearCuentaSerializer,
        responses={
            201: OpenApiResponse(
                description="Pendiente: se activa al responder «CONFIRMAR CUENTA» por WhatsApp"
            ),
            400: OpenApiResponse(description="Datos inválidos o correo no disponible"),
            404: OpenApiResponse(description="Empresa inexistente o inactiva"),
            429: LIMITE,
        },
    )
    def post(self, request, slug):
        empresa = _empresa(slug)
        entrada = CrearCuentaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        if not entrada.validated_data.get("sitio_web"):
            cuentas_pasajero.registrar(empresa, entrada.validated_data)
        return Response(
            {
                "estado": "PENDIENTE",
                "mensaje": "Te enviamos un WhatsApp. Responde CONFIRMAR CUENTA para activarla.",
            },
            status=status.HTTP_201_CREATED,
        )


class ActivacionSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128, write_only=True)


class ReenviarActivacionSerializer(ActivacionSerializer):
    telefono = serializers.CharField(
        max_length=24,
        required=False,
        help_text="Para corregir el número: el nuevo WhatsApp en formato E.164.",
    )

    def validate_telefono(self, valor):
        telefono = normalizar_telefono(valor)
        validar_telefono_e164(telefono)
        return telefono


class EstadoActivacionSerializer(serializers.Serializer):
    activa = serializers.BooleanField()
    telefono = serializers.CharField(help_text="Número al que se envió el mensaje, enmascarado.")


class _VistaActivacion(_VistaPortal):
    throttle_classes = [PortalPorMinuto, PortalPorHora]

    def throttled(self, request, wait):
        raise servicios.LimiteIP(wait)


class EstadoActivacionView(_VistaActivacion):
    @extend_schema(
        tags=["portal"],
        summary="¿Ya se activó mi cuenta?",
        request=ActivacionSerializer,
        responses={
            200: EstadoActivacionSerializer,
            400: OpenApiResponse(description="`cuenta_no_encontrada`"),
        },
        description="HU-41: con el correo y la contraseña del alta; la consulta «Activa tu cuenta».",
    )
    def post(self, request, slug):
        entrada = ActivacionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        estado = cuentas_pasajero.estado_activacion(_empresa(slug), **entrada.validated_data)
        return Response({**estado, "telefono": enmascarar(estado["telefono"])})


class ReenviarActivacionView(_VistaActivacion):
    @extend_schema(
        tags=["portal"],
        summary="Reenviar el WhatsApp de activación (o corregir el número)",
        request=ReenviarActivacionSerializer,
        responses={
            200: EstadoActivacionSerializer,
            400: OpenApiResponse(description="`cuenta_no_encontrada` o número inválido"),
            409: OpenApiResponse(description="`cuenta_activa`"),
            429: OpenApiResponse(description="`limite_reenvio` (3 cada 15 min por cuenta) o límite por IP"),
        },
        description="HU-41 (DC-45): la vigencia del mensaje corre desde este envío.",
    )
    def post(self, request, slug):
        entrada = ReenviarActivacionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        cuenta = cuentas_pasajero.reenviar_activacion(_empresa(slug), **entrada.validated_data)
        return Response({"activa": False, "telefono": enmascarar(cuenta.telefono)})
