"""CC-27 (HU-77, DC-83) y CC-21 (DC-86): apariencia de la empresa (paleta, logo, nombre de marca e iniciales).

La lee y la cambia solo el administrador («Apariencia» no es un módulo asignable al despachador) y cada
cambio queda en AUDITORIA. El portal la obtiene de un endpoint público que solo entrega esos datos de marca.
"""

import unicodedata

from django.core.files.storage import default_storage
from django.db import transaction
from django.http import FileResponse, Http404
from django.urls import reverse
from drf_spectacular.utils import OpenApiTypes, extend_schema, extend_schema_field
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditoria.models import Entidad
from apps.auditoria.servicios import registrar
from apps.comun.permisos import con_roles

from . import logos
from .models import Empresa, Rol
from .paletas import OPCIONES

ACCION = "EDITAR_APARIENCIA"


class LogoSerializer(serializers.Serializer):
    panel = serializers.CharField()
    portal = serializers.CharField()
    app = serializers.CharField()
    correo = serializers.CharField()
    icono = serializers.CharField()


class AparienciaSerializer(serializers.Serializer):
    paleta = serializers.ChoiceField(choices=OPCIONES)
    logo = LogoSerializer(allow_null=True, help_text="Rutas de las versiones; null = sin logo propio")
    nombre_marca = serializers.CharField(allow_blank=True, help_text="Vacío = se muestra la razón social")
    iniciales = serializers.CharField(allow_blank=True, help_text="Se muestran cuando no hay logo")


def _version(carpeta: str) -> str:
    return carpeta.rsplit("/", 1)[-1]


def urls_del_logo(empresa: Empresa) -> dict[str, str] | None:
    if not empresa.logo:
        return None
    version = _version(empresa.logo)
    return {
        variante: reverse("apariencia-logo-publico", args=[empresa.slug, version, variante])
        for variante in logos.VARIANTES
    }


def apariencia_de(empresa: Empresa) -> dict:
    return {
        "paleta": empresa.paleta,
        "logo": urls_del_logo(empresa),
        "nombre_marca": empresa.nombre_marca,
        "iniciales": empresa.iniciales,
    }


@extend_schema_field(AparienciaSerializer)
class CampoApariencia(serializers.Field):
    """La apariencia dentro de la empresa de la sesión (panel y app)."""

    def __init__(self, **kwargs):
        super().__init__(source="*", read_only=True, **kwargs)

    def to_representation(self, empresa):
        return apariencia_de(empresa)


class AparienciaEntradaSerializer(serializers.Serializer):
    """Cambio parcial: solo se modifica lo que viene."""

    paleta = serializers.ChoiceField(choices=OPCIONES, required=False)
    nombre_marca = serializers.CharField(required=False, allow_blank=True, max_length=30)
    iniciales = serializers.CharField(required=False, allow_blank=True, max_length=3)

    def validate_nombre_marca(self, valor: str) -> str:
        # Va en encabezados y en el asunto de los correos: sin saltos de línea ni caracteres de control.
        if any(unicodedata.category(c)[0] == "C" or unicodedata.category(c) in ("Zl", "Zp") for c in valor):
            raise serializers.ValidationError("El nombre de marca no admite saltos de línea.")
        return " ".join(valor.split())

    def validate_iniciales(self, valor: str) -> str:
        valor = valor.upper()
        if valor and (len(valor) > 3 or not valor.isalnum()):
            raise serializers.ValidationError("Usa de 1 a 3 letras o números, sin espacios ni signos.")
        return valor


class LogoEntradaSerializer(serializers.Serializer):
    logo = serializers.FileField(help_text="PNG, JPG o WebP; hasta 2 MB y al menos 256 px de ancho")


class _SoloAdministrador(APIView):
    permission_classes = [con_roles(Rol.ADMINISTRADOR)]

    def _empresa_bloqueada(self, request) -> Empresa:
        return Empresa.objects.select_for_update().get(pk=request.user.empresa_id)

    def _auditar(self, request, previos: dict) -> None:
        registrar(
            usuario=request.user,
            entidad=Entidad.EMPRESA,
            entidad_id=request.user.empresa_id,
            accion=ACCION,
            datos_previos=previos,
        )


class AparienciaView(_SoloAdministrador):
    @extend_schema(tags=["apariencia"], summary="Apariencia de mi empresa", responses=AparienciaSerializer)
    def get(self, request):
        return Response(apariencia_de(Empresa.objects.get(pk=request.user.empresa_id)))

    @extend_schema(
        tags=["apariencia"],
        summary="Cambiar la paleta, el nombre de marca o las iniciales (auditado)",
        request=AparienciaEntradaSerializer,
        responses=AparienciaSerializer,
    )
    def patch(self, request):
        entrada = AparienciaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        with transaction.atomic():
            empresa = self._empresa_bloqueada(request)
            cambios = {c: v for c, v in entrada.validated_data.items() if getattr(empresa, c) != v}
            if cambios:
                previos = {campo: getattr(empresa, campo) for campo in cambios}
                for campo, valor in cambios.items():
                    setattr(empresa, campo, valor)
                empresa.save(update_fields=list(cambios))
                self._auditar(request, previos)
        return Response(apariencia_de(empresa))


class LogoView(_SoloAdministrador):
    parser_classes = [MultiPartParser]

    @extend_schema(
        tags=["apariencia"],
        summary="Subir o reemplazar el logo (auditado)",
        request={"multipart/form-data": LogoEntradaSerializer},
        responses=AparienciaSerializer,
    )
    def post(self, request):
        archivo = request.FILES.get("logo")
        if archivo is None:
            raise serializers.ValidationError({"logo": ["Elige una imagen."]})
        if archivo.size > logos.MAXIMO_BYTES:
            raise serializers.ValidationError({"logo": ["El logo pesa más de 2 MB."]})
        try:
            archivos = logos.procesar(archivo.read())
        except logos.LogoInvalido as error:
            raise serializers.ValidationError({"logo": [str(error)]}) from error
        carpeta = logos.guardar(request.user.empresa_id, archivos)
        try:
            with transaction.atomic():
                empresa = self._empresa_bloqueada(request)
                anterior = empresa.logo
                empresa.logo = carpeta
                empresa.save(update_fields=["logo"])
                self._auditar(request, {"logo": anterior})
                # Los archivos anteriores se borran solo si el cambio quedó guardado.
                transaction.on_commit(lambda: logos.borrar(anterior))
        except Exception:
            logos.borrar(carpeta)
            raise
        return Response(apariencia_de(empresa))

    @extend_schema(
        tags=["apariencia"],
        summary="Quitar el logo y volver al de FlotaÁgil (auditado)",
        request=None,
        # Devuelve la apariencia resultante (sin esto el esquema declara 204 en un DELETE).
        responses={200: AparienciaSerializer},
    )
    def delete(self, request):
        with transaction.atomic():
            empresa = self._empresa_bloqueada(request)
            anterior = empresa.logo
            if anterior:
                empresa.logo = None
                empresa.save(update_fields=["logo"])
                self._auditar(request, {"logo": anterior})
                transaction.on_commit(lambda: logos.borrar(anterior))
        return Response(apariencia_de(empresa))


def _empresa_activa(slug: str) -> Empresa:
    empresa = Empresa.objects.filter(slug=slug, activa=True).first()
    if empresa is None:
        raise Http404("Empresa no encontrada.")
    return empresa


class AparienciaPublicaView(APIView):
    """Sin sesión: solo la marca (paleta, URL del logo, nombre de marca e iniciales), sin otros datos."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        tags=["apariencia"], summary="Apariencia pública de una empresa", responses=AparienciaSerializer
    )
    def get(self, request, slug):
        return Response(apariencia_de(_empresa_activa(slug)))


class LogoPublicoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        tags=["apariencia"],
        summary="Imagen del logo (PNG)",
        responses={(200, "image/png"): OpenApiTypes.BINARY},
    )
    def get(self, request, slug, version, variante):
        empresa = _empresa_activa(slug)
        if variante not in logos.VARIANTES or not empresa.logo or _version(empresa.logo) != version:
            raise Http404("Logo no encontrado.")
        try:
            archivo = default_storage.open(logos.ruta(empresa.logo, variante), "rb")
        except FileNotFoundError as error:
            raise Http404("Logo no encontrado.") from error
        respuesta = FileResponse(archivo, content_type="image/png")
        # La URL cambia con cada logo nuevo, así que se puede guardar en caché sin plazo corto.
        respuesta["Cache-Control"] = "public, max-age=31536000, immutable"
        return respuesta
