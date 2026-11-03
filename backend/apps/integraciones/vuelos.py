"""Consulta de vuelos detrás de un adaptador (HU-26; después la usa el monitoreo de HU-27).

- `ConsultorVuelosDesarrollo`: no llama a ningún servicio. Todo vuelo existe con la hora informada, salvo los
  que empiezan con «ZZ» (sirve para probar el caso «no existe»).
- `ConsultorFlightAware`: FlightAware AeroAPI v4. Se usa cuando `FLIGHTAWARE_API_KEY` está definida.

Solo interesan las llegadas al aeropuerto de la empresa (`AEROPUERTO_IATA`, SCL por defecto, DC-06).
"""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.aeropuerto.models import EstadoVuelo

logger = logging.getLogger(__name__)

# Una llegada estimada este tiempo o más después de la programada se informa como demorada.
UMBRAL_DEMORA = timedelta(minutes=15)


@dataclass(frozen=True)
class DatosVuelo:
    numero: str
    hora_programada: datetime
    hora_estimada: datetime | None
    estado: str


class VuelosNoDisponibles(Exception):
    """La API de vuelos no respondió o respondió con error: no se sabe si el vuelo existe."""


class ConsultorVuelos(Protocol):
    def consultar(self, numero: str, llegada_informada: datetime) -> DatosVuelo | None:
        """La llegada a `AEROPUERTO_IATA` de ese vuelo el mismo día (hora de Chile) más cercana a la
        informada, o None si no existe. Lanza VuelosNoDisponibles si no se pudo consultar."""
        ...


def designador(numero: str) -> str:
    """«la 123» → «LA123»."""
    return "".join(numero.upper().split())


class ConsultorVuelosDesarrollo:
    def consultar(self, numero: str, llegada_informada: datetime) -> DatosVuelo | None:
        if designador(numero).startswith("ZZ"):
            return None
        return DatosVuelo(designador(numero), llegada_informada, None, EstadoVuelo.PROGRAMADO)


def _hora(valor) -> datetime | None:
    return parse_datetime(valor) if valor else None


def estado_de(vuelo: dict, programada: datetime, estimada: datetime | None) -> str:
    if vuelo.get("cancelled"):
        return EstadoVuelo.CANCELADO
    if vuelo.get("diverted"):
        return EstadoVuelo.DESVIADO
    if vuelo.get("actual_in") or vuelo.get("actual_on"):
        return EstadoVuelo.ATERRIZADO
    if estimada and estimada - programada >= UMBRAL_DEMORA:
        return EstadoVuelo.DEMORADO
    return EstadoVuelo.PROGRAMADO


class ConsultorFlightAware:
    URL = "https://aeroapi.flightaware.com/aeroapi/flights/"

    def __init__(self, api_key: str, intentos: int = 3, espera_base: float = 0.5, timeout: float = 5.0):
        self.api_key = api_key
        self.intentos = intentos
        self.espera_base = espera_base
        self.timeout = timeout

    def _pedir(self, numero: str, desde: datetime, hasta: datetime) -> dict:
        parametros = urllib.parse.urlencode(
            {
                "ident_type": "designator",
                "start": desde.isoformat(timespec="seconds"),
                "end": hasta.isoformat(timespec="seconds"),
            }
        )
        peticion = urllib.request.Request(
            f"{self.URL}{urllib.parse.quote(numero)}?{parametros}",
            headers={"x-apikey": self.api_key, "Accept": "application/json"},
        )
        # La URL es fija y https; no se abren esquemas arbitrarios.
        with urllib.request.urlopen(peticion, timeout=self.timeout) as respuesta:  # nosec B310
            return json.load(respuesta)

    def _consultar_con_reintentos(self, numero: str, desde: datetime, hasta: datetime) -> dict:
        for intento in range(self.intentos):
            try:
                return self._pedir(numero, desde, hasta)
            except urllib.error.HTTPError as error:
                if error.code == 404:
                    return {"flights": []}
                if error.code not in (429, 500, 502, 503, 504):
                    raise VuelosNoDisponibles(f"La API de vuelos respondió {error.code}.") from error
                logger.warning(
                    "Consulta de vuelo falló (intento %s/%s): %s", intento + 1, self.intentos, error
                )
            except (urllib.error.URLError, TimeoutError) as error:
                logger.warning(
                    "Consulta de vuelo falló (intento %s/%s): %s", intento + 1, self.intentos, error
                )
            if intento < self.intentos - 1:
                time.sleep(self.espera_base * 2**intento)  # reintento exponencial
        raise VuelosNoDisponibles("La API de vuelos no está disponible.")

    def consultar(self, numero: str, llegada_informada: datetime) -> DatosVuelo | None:
        ident = designador(numero)
        dia = timezone.localtime(llegada_informada).date()
        inicio = timezone.make_aware(datetime.combine(dia, datetime.min.time()))
        # Ventana amplia (salidas desde el día anterior) para incluir vuelos largos que llegan ese día.
        datos = self._consultar_con_reintentos(ident, inicio - timedelta(days=1), inicio + timedelta(days=1))
        candidatos = []
        for vuelo in datos.get("flights", []):
            if (vuelo.get("destination") or {}).get("code_iata") != settings.AEROPUERTO_IATA:
                continue
            programada = _hora(vuelo.get("scheduled_in") or vuelo.get("scheduled_on"))
            if programada is None or timezone.localtime(programada).date() != dia:
                continue
            estimada = _hora(vuelo.get("estimated_in") or vuelo.get("estimated_on"))
            candidatos.append(
                DatosVuelo(
                    vuelo.get("ident_iata") or ident,
                    programada,
                    estimada,
                    estado_de(vuelo, programada, estimada),
                )
            )
        if not candidatos:
            return None
        return min(candidatos, key=lambda v: abs(v.hora_programada - llegada_informada))


def obtener_consultor_vuelos() -> ConsultorVuelos:
    clave = getattr(settings, "FLIGHTAWARE_API_KEY", "")
    return ConsultorFlightAware(clave) if clave else ConsultorVuelosDesarrollo()
