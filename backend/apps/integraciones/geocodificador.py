"""Geocodificador detrás de un adaptador (DC-05).

- `GeocodificadorDesarrollo`: coordenadas aproximadas y determinísticas por texto, dentro de la zona de
  operación de la empresa. No llama a ningún servicio externo.
- `GeocodificadorGoogle`: Google Geocoding API; se usa cuando `GOOGLE_GEOCODING_API_KEY` está definida.
- `GeocodificadorNominatim` (HU-70, DC-71): Nominatim de OpenStreetMap, solo para desarrollo y pruebas.

`GEOCODIFICADOR` (google | nominatim | desarrollo) elige el proveedor.
"""

import hashlib
import json
import logging
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings

logger = logging.getLogger(__name__)

# Aeropuerto Arturo Merino Benítez (SCL).
AEROPUERTO_SCL = (-33.3930, -70.7858)
CENTRO_SANTIAGO = (-33.4489, -70.6693)
# Radio aproximado (grados) en torno al centro para el geocodificador de desarrollo (~15 km).
RADIO_DESARROLLO = 0.14


@dataclass(frozen=True)
class Coordenadas:
    lat: float
    lon: float


@dataclass(frozen=True)
class Zona:
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

    @classmethod
    def de_configuracion(cls, config) -> "Zona":
        return cls(
            float(config.zona_lat_min),
            float(config.zona_lat_max),
            float(config.zona_lon_min),
            float(config.zona_lon_max),
        )

    def contiene(self, punto: Coordenadas) -> bool:
        return self.lat_min <= punto.lat <= self.lat_max and self.lon_min <= punto.lon <= self.lon_max


class GeocodificacionError(Exception):
    """No se pudo obtener coordenadas para la dirección."""


class Geocodificador(Protocol):
    def geocodificar(self, direccion: str, zona: Zona) -> Coordenadas: ...


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().split())


class GeocodificadorDesarrollo:
    """Misma dirección → mismo punto. «aeropuerto» se ubica en SCL para que los viajes de aeropuerto
    tengan coordenadas creíbles."""

    def geocodificar(self, direccion: str, zona: Zona) -> Coordenadas:
        texto = _normalizar(direccion)
        if not texto:
            raise GeocodificacionError("La dirección está vacía.")
        if "aeropuerto" in texto or "scl" in texto.split():
            return Coordenadas(*AEROPUERTO_SCL)
        resumen = hashlib.sha256(texto.encode()).digest()
        fa = int.from_bytes(resumen[:8], "big") / 2**64
        fb = int.from_bytes(resumen[8:16], "big") / 2**64
        lat = CENTRO_SANTIAGO[0] + (fa * 2 - 1) * RADIO_DESARROLLO
        lon = CENTRO_SANTIAGO[1] + (fb * 2 - 1) * RADIO_DESARROLLO
        # Se acota a la zona de la empresa por si fue configurada más pequeña.
        lat = min(max(lat, zona.lat_min), zona.lat_max)
        lon = min(max(lon, zona.lon_min), zona.lon_max)
        return Coordenadas(round(lat, 6), round(lon, 6))


class GeocodificadorGoogle:
    URL = "https://maps.googleapis.com/maps/api/geocode/json"

    def __init__(self, api_key: str, intentos: int = 3, espera_base: float = 0.5, timeout: float = 5.0):
        self.api_key = api_key
        self.intentos = intentos
        self.espera_base = espera_base
        self.timeout = timeout

    def _consultar(self, direccion: str, zona: Zona) -> dict:
        parametros = urllib.parse.urlencode(
            {
                "address": direccion,
                "key": self.api_key,
                "region": "cl",
                "language": "es",
                "components": "country:CL",
                # Sesgo hacia la zona de operación (no la restringe).
                "bounds": f"{zona.lat_min},{zona.lon_min}|{zona.lat_max},{zona.lon_max}",
            }
        )
        # La URL es fija y https; no se abren esquemas arbitrarios.
        with urllib.request.urlopen(f"{self.URL}?{parametros}", timeout=self.timeout) as respuesta:  # nosec B310
            return json.load(respuesta)

    def geocodificar(self, direccion: str, zona: Zona) -> Coordenadas:
        for intento in range(self.intentos):
            try:
                datos = self._consultar(direccion, zona)
            except (urllib.error.URLError, TimeoutError) as error:
                logger.warning("Geocodificación falló (intento %s/%s): %s", intento + 1, self.intentos, error)
                datos = None
            if datos is not None:
                estado = datos.get("status")
                if estado == "OK":
                    ubicacion = datos["results"][0]["geometry"]["location"]
                    return Coordenadas(float(ubicacion["lat"]), float(ubicacion["lng"]))
                if estado == "ZERO_RESULTS":
                    raise GeocodificacionError("No se encontró la dirección.")
                if estado not in {"OVER_QUERY_LIMIT", "UNKNOWN_ERROR"}:
                    raise GeocodificacionError(f"El servicio de direcciones respondió {estado}.")
            if intento < self.intentos - 1:
                time.sleep(self.espera_base * 2**intento)  # reintento exponencial
        raise GeocodificacionError("El servicio de direcciones no está disponible. Intenta nuevamente.")


class GeocodificadorNominatim:
    """HU-70 (DC-71): Nominatim de OpenStreetMap, solo para desarrollo y pruebas.

    Cumple su política de uso: a lo más 1 solicitud por segundo entre todos los procesos (candado en Redis),
    un User-Agent que identifica la aplicación y caché de los resultados para no repetir consultas.
    """

    URL = "https://nominatim.openstreetmap.org/search"
    USER_AGENT = "FlotaAgil-pruebas (+https://github.com/flotaagil-cl/flotaagil)"
    CANDADO = "nominatim:candado"
    CACHE_DIAS = 30
    # Una dirección que no existe también se recuerda (menos tiempo), para no volver a preguntarla.
    CACHE_NO_ENCONTRADA_S = 3600

    def __init__(
        self,
        intentos: int = 3,
        espera_base: float = 1.0,
        timeout: float = 5.0,
        espera_maxima_candado: float = 5.0,
        dormir=time.sleep,
        reloj=time.monotonic,
    ):
        self.intentos = intentos
        self.espera_base = espera_base
        self.timeout = timeout
        self.espera_maxima_candado = espera_maxima_candado
        self.dormir = dormir
        self.reloj = reloj

    def _clave_cache(self, direccion: str, zona: Zona) -> str:
        texto = f"{_normalizar(direccion)}|{zona.lat_min},{zona.lat_max},{zona.lon_min},{zona.lon_max}"
        return "nominatim:" + hashlib.sha256(texto.encode()).hexdigest()

    def _esperar_turno(self) -> None:
        """1 solicitud por segundo: `cache.add` es atómico en Redis (SET NX) y la llave vence en 1 s."""
        from django.core.cache import cache

        limite = self.reloj() + self.espera_maxima_candado
        while not cache.add(self.CANDADO, 1, timeout=1):
            if self.reloj() >= limite:
                raise GeocodificacionError(
                    "El servicio de direcciones no está disponible. Intenta nuevamente."
                )
            self.dormir(0.2)

    def _consultar(self, direccion: str, zona: Zona) -> list:
        parametros = urllib.parse.urlencode(
            {
                "q": direccion,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "cl",
                "accept-language": "es",
                # Sesgo hacia la zona de operación (no la restringe), como `bounds` en Google.
                "viewbox": f"{zona.lon_min},{zona.lat_max},{zona.lon_max},{zona.lat_min}",
            }
        )
        pedido = urllib.request.Request(f"{self.URL}?{parametros}", headers={"User-Agent": self.USER_AGENT})
        # La URL es fija y https; no se abren esquemas arbitrarios.
        with urllib.request.urlopen(pedido, timeout=self.timeout) as respuesta:  # nosec B310
            return json.load(respuesta)

    def geocodificar(self, direccion: str, zona: Zona) -> Coordenadas:
        from django.core.cache import cache

        if not _normalizar(direccion):
            raise GeocodificacionError("La dirección está vacía.")
        clave = self._clave_cache(direccion, zona)
        guardado = cache.get(clave)
        if guardado == "no_encontrada":
            raise GeocodificacionError("No se encontró la dirección.")
        if guardado:
            return Coordenadas(*guardado)
        for intento in range(self.intentos):
            self._esperar_turno()
            try:
                resultados = self._consultar(direccion, zona)
            except (urllib.error.URLError, TimeoutError, ValueError) as error:
                logger.warning("Nominatim falló (intento %s/%s): %s", intento + 1, self.intentos, error)
                resultados = None
            if resultados is not None:
                if not resultados:
                    cache.set(clave, "no_encontrada", self.CACHE_NO_ENCONTRADA_S)
                    raise GeocodificacionError("No se encontró la dirección.")
                punto = Coordenadas(float(resultados[0]["lat"]), float(resultados[0]["lon"]))
                cache.set(clave, [punto.lat, punto.lon], self.CACHE_DIAS * 86400)
                return punto
            if intento < self.intentos - 1:
                self.dormir(self.espera_base * 2**intento)  # reintento exponencial
        raise GeocodificacionError("El servicio de direcciones no está disponible. Intenta nuevamente.")


PROVEEDORES = ("google", "nominatim", "desarrollo")


def proveedor_de_geocodificacion() -> str:
    """HU-70: manda `GEOCODIFICADOR`; sin él, Google si hay clave y, si no, Nominatim con DEBUG."""
    elegido = (getattr(settings, "GEOCODIFICADOR", "") or "").strip().lower()
    clave = getattr(settings, "GOOGLE_GEOCODING_API_KEY", "")
    if elegido == "google" and not clave:
        logger.warning("GEOCODIFICADOR=google sin GOOGLE_GEOCODING_API_KEY: se usa el de desarrollo.")
        return "desarrollo"
    if elegido in PROVEEDORES:
        return elegido
    if clave:
        return "google"
    return "nominatim" if settings.DEBUG else "desarrollo"


def obtener_geocodificador() -> Geocodificador:
    proveedor = proveedor_de_geocodificacion()
    if proveedor == "google":
        return GeocodificadorGoogle(settings.GOOGLE_GEOCODING_API_KEY)
    if proveedor == "nominatim":
        return GeocodificadorNominatim()
    return GeocodificadorDesarrollo()


def coordenadas_reales() -> bool:
    """DC-30: el de desarrollo inventa puntos a partir del texto; no sirven para navegar."""
    return not isinstance(obtener_geocodificador(), GeocodificadorDesarrollo)
