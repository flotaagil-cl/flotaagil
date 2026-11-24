"""Portal público del pasajero (HU-19). Sin autenticación: se protege con throttling por IP,
límite por teléfono y un campo trampa."""

from datetime import timedelta

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.comun.excepciones import error_con_codigo
from apps.convenios import servicios as convenios
from apps.convenios.serializers import RegistroConvenioSerializer, SolicitudConvenioPublicaSerializer
from apps.cuentas.models import Empresa
from apps.cuentas.serializers import ErrorSerializer
from apps.integraciones.correo import enmascarar as enmascarar_correo
from apps.reservas import cuentas_pasajero

from . import pase as pases
from . import publico, servicios
from .serializers import (
    AutorizacionSerializer,
    CrearCuentaSerializer,
    EmpresaPublicaSerializer,
    EncuestaSerializer,
    PaseConvenioRespuestaSerializer,
    PaseConvenioSerializer,
    ReservaConfirmadaSerializer,
    ReservaPublicaRespuestaSerializer,
    ReservaPublicaSerializer,
    TokenSerializer,
)


class PortalPorMinuto(AnonRateThrottle):
    scope = "portal_minuto"


class PortalPorHora(AnonRateThrottle):
    scope = "portal_hora"


class ReservaPublicaPorHora(AnonRateThrottle):
    scope = "reserva_publica"  # DC-56


def _empresa(slug: str) -> Empresa:
    return get_object_or_404(Empresa.objects.select_related("configuracion"), slug=slug, activa=True)


def _empresa_sin_modulo(slug: str) -> Empresa:
    """DC-51 (CC-22): los formularios públicos son la base; con el módulo, el portal pide con cuenta."""
    empresa = _empresa(slug)
    if empresa.modulo_cuentas:
        raise Http404("Esta empresa recibe los pedidos con cuenta.")
    return empresa


def _empresa_con_modulo(slug: str) -> Empresa:
    """DC-51 (CC-22): crear cuenta y registrar empresa existen solo con el módulo de cuentas."""
    empresa = _empresa(slug)
    if not empresa.modulo_cuentas:
        raise Http404("No disponible para esta empresa.")
    return empresa


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
        empresa = _empresa_con_modulo(slug)
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
    """HU-35 y HU-64: crea la cuenta pendiente y manda el enlace de activación al correo, con los límites
    del portal."""

    throttle_classes = [PortalPorMinuto, PortalPorHora]

    def throttled(self, request, wait):
        raise servicios.LimiteIP(wait)

    @extend_schema(
        tags=["portal"],
        summary="Crear una cuenta de pasajero",
        request=CrearCuentaSerializer,
        responses={
            201: OpenApiResponse(description="Pendiente: se activa con el enlace del correo (24 h, DC-61)"),
            400: OpenApiResponse(description="Datos inválidos o correo no disponible"),
            404: OpenApiResponse(description="Empresa inexistente o inactiva"),
            429: LIMITE,
        },
    )
    def post(self, request, slug):
        empresa = _empresa_con_modulo(slug)
        entrada = CrearCuentaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        if not entrada.validated_data.get("sitio_web"):
            cuentas_pasajero.registrar(empresa, entrada.validated_data)
        return Response(
            {
                "estado": "PENDIENTE",
                "mensaje": "Te enviamos un correo. Abre el enlace para activar tu cuenta.",
            },
            status=status.HTTP_201_CREATED,
        )


class ActivacionSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128, write_only=True)


class EstadoActivacionSerializer(serializers.Serializer):
    activa = serializers.BooleanField()
    correo = serializers.CharField(help_text="Correo al que se envió el enlace, enmascarado.")


class ActivarCuentaSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=200)


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
        empresa = _empresa_con_modulo(slug)
        entrada = ActivacionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        estado = cuentas_pasajero.estado_activacion(empresa, **entrada.validated_data)
        return Response({**estado, "correo": enmascarar_correo(estado["correo"])})


class ReenviarActivacionView(_VistaActivacion):
    @extend_schema(
        tags=["portal"],
        summary="Reenviar el enlace de activación al correo",
        request=ActivacionSerializer,
        responses={
            200: EstadoActivacionSerializer,
            400: OpenApiResponse(description="`cuenta_no_encontrada`"),
            409: OpenApiResponse(description="`cuenta_activa`"),
            429: OpenApiResponse(description="`limite_reenvio` (3 cada 15 min por cuenta) o límite por IP"),
        },
        description="HU-41 y HU-64 (DC-61): el nuevo enlace vale 24 h desde este envío.",
    )
    def post(self, request, slug):
        empresa = _empresa_con_modulo(slug)
        entrada = ActivacionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        cuenta = cuentas_pasajero.reenviar_activacion(empresa, **entrada.validated_data)
        return Response({"activa": False, "correo": enmascarar_correo(cuenta.usuario.email)})


class ActivarCuentaView(_VistaActivacion):
    @extend_schema(
        tags=["portal"],
        summary="Activar la cuenta con el enlace del correo",
        request=ActivarCuentaSerializer,
        responses={
            200: EstadoActivacionSerializer,
            400: OpenApiResponse(description="`enlace_invalido` o `enlace_vencido`"),
            409: OpenApiResponse(description="`telefono_en_uso`: el teléfono ya es de otra cuenta activa"),
        },
        description="HU-64 (DC-61, CP-56): el enlace vale 24 h; abrirlo de nuevo con la cuenta activa "
        "responde 200. Sin verificar el teléfono, la cuenta ve solo los viajes que pide (DC-65).",
    )
    def post(self, request, slug):
        empresa = _empresa_con_modulo(slug)
        entrada = ActivarCuentaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        cuenta = cuentas_pasajero.activar(empresa, entrada.validated_data["token"])
        return Response({"activa": True, "correo": enmascarar_correo(cuenta.usuario.email)})


class ReservaPublicaView(_VistaPortal):
    # DC-59: el límite por hora es por empresa (ConfiguracionEmpresa) y lo aplica el servicio.
    throttle_classes = [PortalPorMinuto]

    @extend_schema(
        tags=["portal"],
        summary="Reserva pública sin cuenta (empresas sin el módulo de cuentas)",
        request=ReservaPublicaSerializer,
        responses={
            201: ReservaPublicaRespuestaSerializer,
            400: OpenApiResponse(description="Datos inválidos"),
            401: OpenApiResponse(description="CC-23: `pase_vencido` o `pase_invalido`: vuelve a la clave"),
            404: OpenApiResponse(description="Empresa inexistente o con el módulo de cuentas"),
            429: OpenApiResponse(description="`limite_ip` o `limite_correo`"),
        },
        description="HU-51 (CC-22): crea la reserva en PENDIENTE_CONFIRMACION y envía por correo el enlace "
        "para confirmarla (DC-53: hasta 24 h antes de la recogida, o 60 min si falta menos). CC-23 (HU-72): "
        "con `pase` la reserva es del convenio, a nombre de quien la pide; en vehículos separados crea un "
        "viaje por persona con un solo enlace de confirmación.",
    )
    def post(self, request, slug):
        # HU-60: también con el módulo de cuentas, como «Reservar sin cuenta».
        empresa = _empresa(slug)
        entrada = ReservaPublicaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        mensaje = "Te enviamos un correo con el enlace para confirmar tu reserva."
        if datos.get("sitio_web"):  # campo trampa: se responde igual, sin crear nada
            ahora = timezone.now()
            falsa = {"id": 0, "estado": "PENDIENTE_CONFIRMACION", "mensaje": mensaje}
            falsa |= {"recogida_en": datos.get("recogida_en") or ahora, "confirmar_hasta": ahora}
            return Response(ReservaPublicaRespuestaSerializer(falsa).data, status=status.HTTP_201_CREATED)
        ip = PortalPorMinuto().get_ident(request)
        if datos.get("pase"):
            # CC-23 (D2): el pase de convenio es solo del portal base.
            empresa = _empresa_sin_modulo(slug)
            viajes = publico.crear_con_pase(empresa, datos, ip=ip)
            viaje = viajes[0]
            mensaje = (
                f"Te enviamos un correo con un solo enlace para confirmar los {len(viajes)} traslados."
                if len(viajes) > 1
                else mensaje
            )
            return Response(
                ReservaPublicaRespuestaSerializer(
                    {
                        "id": viaje.pk,
                        "estado": viaje.estado,
                        "recogida_en": viaje.recogida_en,
                        "confirmar_hasta": viaje.confirmar_hasta,
                        "confirma_convenio": False,
                        "viajes": len(viajes),
                        "mensaje": mensaje,
                    }
                ).data,
                status=status.HTTP_201_CREATED,
            )
        viaje = publico.crear(empresa, datos, ip=ip)
        if viaje.confirma_convenio:
            mensaje = "Tu correo no está autorizado en el convenio: le pedimos a la empresa que la autorice."
        return Response(
            ReservaPublicaRespuestaSerializer(
                {
                    "id": viaje.pk,
                    "estado": viaje.estado,
                    "recogida_en": viaje.recogida_en,
                    "confirmar_hasta": viaje.confirmar_hasta,
                    "confirma_convenio": viaje.confirma_convenio,
                    "mensaje": mensaje,
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )


class PaseConvenioView(_VistaPortal):
    """CC-23 (HU-72, DC-75): correo + clave del convenio → pase firmado para el formulario público."""

    throttle_classes = [PortalPorMinuto]

    @extend_schema(
        tags=["portal"],
        summary="Pase de convenio con correo y clave (empresas sin el módulo de cuentas)",
        request=PaseConvenioSerializer,
        responses={
            200: PaseConvenioRespuestaSerializer,
            400: OpenApiResponse(description="`clave_invalida`: el mismo error para cualquier fallo"),
            404: OpenApiResponse(description="Empresa inexistente o con el módulo de cuentas"),
            429: OpenApiResponse(description="`limite_ip` o `clave_bloqueada`"),
        },
        description="El correo debe ser el contacto del convenio o uno autorizado. El pase vence según la "
        "configuración de la empresa y se revalida en cada reserva.",
    )
    def post(self, request, slug):
        empresa = _empresa_sin_modulo(slug)
        entrada = PaseConvenioSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        pase, convenio, correo = pases.emitir(
            empresa,
            entrada.validated_data["correo"],
            entrada.validated_data["clave"],
            ip=PortalPorMinuto().get_ident(request),
        )
        vigencia = empresa.configuracion.convenio_pase_vigencia_min
        respuesta = Response(
            PaseConvenioRespuestaSerializer(
                {
                    "pase": pase,
                    "cliente_nombre": convenio.cliente_nombre,
                    "correo": enmascarar_correo(correo),
                    "vence_en": timezone.now() + timedelta(minutes=vigencia),
                }
            ).data
        )
        respuesta["Cache-Control"] = "no-store"
        return respuesta


class SolicitudConvenioView(_VistaPortal):
    throttle_classes = [PortalPorMinuto, ReservaPublicaPorHora]

    @extend_schema(
        tags=["portal"],
        summary="Solicitud pública de convenio (empresas sin el módulo de cuentas)",
        request=SolicitudConvenioPublicaSerializer,
        responses={
            201: inline_serializer("SolicitudConvenioRecibida", {"mensaje": serializers.CharField()}),
            400: OpenApiResponse(description="Datos inválidos"),
            404: OpenApiResponse(description="Empresa inexistente o con el módulo de cuentas"),
            429: OpenApiResponse(description="`limite_ip`"),
        },
        description="HU-53 (CC-22): crea el convenio EN_REVISION sin cuenta; lo revisan el administrador o "
        "el despachador y el resultado llega al correo de contacto.",
    )
    def post(self, request, slug):
        empresa = _empresa_sin_modulo(slug)
        entrada = SolicitudConvenioPublicaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        if not entrada.validated_data.get("sitio_web"):  # campo trampa: se responde igual, sin crear nada
            convenios.solicitar_publico(empresa, entrada.validated_data)
        mensaje = "Recibimos tu solicitud. Te avisaremos por correo cuando se revise."
        return Response({"mensaje": mensaje}, status=status.HTTP_201_CREATED)


class AutorizarReservaView(_VistaPortal):
    throttle_classes = [PortalPorMinuto, PortalPorHora]

    @extend_schema(
        tags=["portal"],
        summary="El contacto del convenio autoriza o rechaza una reserva pública",
        request=AutorizacionSerializer,
        responses={
            200: ReservaConfirmadaSerializer,
            400: OpenApiResponse(description="`enlace_invalido` o decisión inválida"),
            409: OpenApiResponse(description="`enlace_usado`"),
            410: OpenApiResponse(description="`enlace_vencido`"),
        },
        description="HU-54 (CC-22): autorizar la deja SOLICITADO; rechazar la cancela y avisa al "
        "solicitante.",
    )
    def post(self, request, slug):
        empresa = _empresa(slug)
        entrada = AutorizacionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        viaje = publico.autorizar(empresa, datos["token"], datos["decision"])
        return Response(ReservaConfirmadaSerializer(viaje).data)


class EncuestaView(_VistaPortal):
    throttle_classes = [PortalPorMinuto, PortalPorHora]

    @extend_schema(
        tags=["portal"],
        summary="Calificar el viaje desde el correo de la encuesta (1 a 5)",
        request=EncuestaSerializer,
        responses={
            201: inline_serializer("CalificacionRegistrada", {"puntaje": serializers.IntegerField()}),
            400: OpenApiResponse(
                description="`enlace_invalido` (alterado, vencido a los 7 días o sin viaje)"
            ),
            409: OpenApiResponse(description="`ya_calificado`"),
        },
        description="HU-56 (CC-22): misma CALIFICACION de HU-24; opcional (RN-14) y una sola vez.",
    )
    def post(self, request, slug):
        empresa = _empresa(slug)
        entrada = EncuestaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        calificacion = publico.calificar(empresa, datos["token"], datos["puntaje"])
        return Response({"puntaje": calificacion.puntaje}, status=status.HTTP_201_CREATED)


class ConfirmarReservaView(_VistaPortal):
    throttle_classes = [PortalPorMinuto, PortalPorHora]

    @extend_schema(
        tags=["portal"],
        summary="Confirmar la reserva pública con el enlace del correo",
        request=TokenSerializer,
        responses={
            200: ReservaConfirmadaSerializer,
            400: OpenApiResponse(description="`enlace_invalido`"),
            409: OpenApiResponse(description="`enlace_usado`"),
            410: OpenApiResponse(description="`enlace_vencido`: queda «Sin confirmar» (HU-52)"),
        },
        description="HU-51: el enlace firmado vale una sola vez y hasta `confirmar_hasta`. La página lo "
        "envía por POST para que los revisores de enlaces del correo no confirmen solos.",
    )
    def post(self, request, slug):
        empresa = _empresa(slug)
        entrada = TokenSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        viaje = publico.confirmar(empresa, entrada.validated_data["token"])
        return Response(ReservaConfirmadaSerializer(viaje).data)
