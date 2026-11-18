"""HU-71 (DC-72): sugerencias de direcciones mientras se escribe, solo para desarrollo y la demo.

Photon (servidor público de komoot) a través del backend: el navegador no habla con el tercero, las consultas
quedan en caché en Redis y hay un límite por usuario o IP. No se usa Nominatim para autocompletar: su política
de uso lo prohíbe. `SUGERIDOR_DIRECCIONES` = photon | ninguno (photon con DEBUG, ninguno en producción).
"""

import hashlib
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass

from django.conf import settings
from django.core.cache import cache
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from .geocodificador import CENTRO_SANTIAGO, Zona

logger = logging.getLogger(__name__)

MINIMO_CARACTERES = 3
MAXIMO_RESULTADOS = 5
# Chile continental (con margen): lo que se acepta como coordenada sugerida y el recuadro de la búsqueda.
CHILE = Zona(lat_min=-56.0, lat_max=-17.4, lon_min=-76.0, lon_max=-66.0)


@dataclass(frozen=True)
class Sugerencia:
    texto: str
    lat: float
    lon: float


def en_chile(lat: float, lon: float) -> bool:
    return CHILE.lat_min <= lat <= CHILE.lat_max and CHILE.lon_min <= lon <= CHILE.lon_max


def _texto(propiedades: dict) -> str | None:
    """«Av. Providencia 1234, Providencia, Santiago»: calle y número (o el nombre), comuna y ciudad."""
    calle = propiedades.get("street")
    numero = propiedades.get("housenumber")
    nombre = propiedades.get("name")
    primera = f"{calle} {numero}".strip() if calle and numero else (nombre or calle)
    if not primera:
        return None
    partes = [primera]
    if nombre and calle and nombre != primera:
        partes[0] = f"{nombre}, {primera}"
    for clave in ("district", "city", "county"):
        valor = propiedades.get(clave)
        if valor and valor not in partes and not str(valor).startswith("Provincia"):
            partes.append(valor)
    return ", ".join(partes[:3])


class SugeridorPhoton:
    URL = "https://photon.komoot.io/api"
    USER_AGENT = "FlotaAgil-pruebas (+https://github.com/flotaagil-cl/flotaagil)"
    CACHE_S = 24 * 3600

    def __init__(self, timeout: float = 3.0):
        self.timeout = timeout

    def _consultar(self, texto: str, centro: tuple[float, float]) -> dict:
        parametros = urllib.parse.urlencode(
            {
                "q": texto,
                # El servidor público solo acepta default, de, en y fr: «default» da los nombres locales de
                # OpenStreetMap, que en Chile están en español (DC-72).
                "lang": "default",
                "limit": MAXIMO_RESULTADOS * 2,  # se filtran los de fuera de Chile
                "lat": centro[0],
                "lon": centro[1],
                "bbox": f"{CHILE.lon_min},{CHILE.lat_min},{CHILE.lon_max},{CHILE.lat_max}",
            }
        )
        pedido = urllib.request.Request(f"{self.URL}?{parametros}", headers={"User-Agent": self.USER_AGENT})
        # La URL es fija y https; no se abren esquemas arbitrarios.
        with urllib.request.urlopen(pedido, timeout=self.timeout) as respuesta:  # nosec B310
            return json.load(respuesta)

    def sugerir(self, texto: str, centro: tuple[float, float]) -> list[Sugerencia]:
        texto = " ".join(texto.split())
        if len(texto) < MINIMO_CARACTERES:
            return []
        clave = "sugerencias:" + hashlib.sha256(f"{texto.lower()}|{centro}".encode()).hexdigest()
        guardadas = cache.get(clave)
        if guardadas is not None:
            return [Sugerencia(**s) for s in guardadas]
        try:
            datos = self._consultar(texto, centro)
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            # Sin servicio, el campo sigue como texto normal: lista vacía y sin guardar en caché.
            logger.warning("Photon no respondió: %s", error)
            return []
        resultados: list[Sugerencia] = []
        for rasgo in datos.get("features", []):
            propiedades = rasgo.get("properties") or {}
            coordenadas = (rasgo.get("geometry") or {}).get("coordinates") or []
            if propiedades.get("countrycode", "").upper() != "CL" or len(coordenadas) != 2:
                continue
            lon, lat = float(coordenadas[0]), float(coordenadas[1])
            mostrar = _texto(propiedades)
            if not mostrar or not en_chile(lat, lon) or any(r.texto == mostrar for r in resultados):
                continue
            resultados.append(Sugerencia(mostrar, round(lat, 6), round(lon, 6)))
            if len(resultados) == MAXIMO_RESULTADOS:
                break
        cache.set(clave, [asdict(r) for r in resultados], self.CACHE_S)
        return resultados


def proveedor_de_sugerencias() -> str:
    elegido = (getattr(settings, "SUGERIDOR_DIRECCIONES", "") or "").strip().lower()
    if elegido in ("photon", "ninguno"):
        return elegido
    return "photon" if settings.DEBUG else "ninguno"


def obtener_sugeridor() -> SugeridorPhoton | None:
    return SugeridorPhoton() if proveedor_de_sugerencias() == "photon" else None


class SugerenciasThrottle(SimpleRateThrottle):
    """30 por minuto por usuario con sesión o por IP sin ella (THROTTLE_SUGERENCIAS)."""

    scope = "sugerencias"

    def get_cache_key(self, request, view):
        usuario = request.user
        ident = f"u{usuario.pk}" if usuario and usuario.is_authenticated else self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class SugerenciaSerializer(serializers.Serializer):
    texto = serializers.CharField()
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class RespuestaSugerenciasSerializer(serializers.Serializer):
    disponible = serializers.BooleanField(help_text="False si el sugeridor está en «ninguno».")
    sugerencias = SugerenciaSerializer(many=True)


def _centro(request) -> tuple[float, float]:
    """Centro de la zona de la empresa: la del usuario con sesión o la del slug (formularios públicos)."""
    from apps.cuentas.models import Empresa

    empresa = None
    if request.user and request.user.is_authenticated:
        empresa = getattr(request.user, "empresa", None)
    elif slug := request.query_params.get("empresa"):
        empresa = Empresa.objects.filter(slug=slug).select_related("configuracion").first()
    if empresa is None:
        return CENTRO_SANTIAGO
    zona = Zona.de_configuracion(empresa.configuracion)
    return ((zona.lat_min + zona.lat_max) / 2, (zona.lon_min + zona.lon_max) / 2)


class SugerirDireccionesView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [SugerenciasThrottle]

    @extend_schema(
        tags=["direcciones"],
        summary="Sugerencias de direcciones mientras se escribe (HU-71)",
        parameters=[
            OpenApiParameter("q", str, description="Texto escrito (desde 3 caracteres)"),
            OpenApiParameter("empresa", str, required=False, description="Slug, en los formularios públicos"),
        ],
        responses=RespuestaSugerenciasSerializer,
    )
    def get(self, request):
        sugeridor = obtener_sugeridor()
        if sugeridor is None:
            return Response({"disponible": False, "sugerencias": []})
        sugerencias = sugeridor.sugerir(request.query_params.get("q", ""), _centro(request))
        return Response({"disponible": True, "sugerencias": [asdict(s) for s in sugerencias]})
