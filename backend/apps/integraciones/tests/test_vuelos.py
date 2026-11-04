"""Adaptador de vuelos (HU-26): consultor de desarrollo y FlightAware AeroAPI con respuestas simuladas."""

import io
import json
import urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from apps.aeropuerto.models import EstadoVuelo
from apps.integraciones import vuelos
from apps.integraciones.vuelos import (
    ConsultorFlightAware,
    ConsultorVuelosDesarrollo,
    VuelosNoDisponibles,
    obtener_consultor_vuelos,
)

SANTIAGO = ZoneInfo("America/Santiago")
INFORMADA = datetime(2026, 11, 5, 9, 30, tzinfo=SANTIAGO)  # 12:30 UTC
HOY = datetime(2026, 11, 4, 12, 0, tzinfo=SANTIAGO)  # el vuelo está al alcance de /flights


def vuelo(**cambios):
    return {
        "ident_iata": "LA123",
        "destination": {"code_iata": "SCL"},
        "scheduled_in": "2026-11-05T12:40:00Z",
        "estimated_in": "2026-11-05T12:45:00Z",
        "cancelled": False,
        "diverted": False,
    } | cambios


class FlightAwareFalso(ConsultorFlightAware):
    """Responde con la lista dada o lanza los errores dados, en orden, sin red."""

    def __init__(self, *respuestas, ahora=HOY):
        super().__init__("clave-sintetica", espera_base=0, ahora=lambda: ahora)
        self.respuestas = list(respuestas)
        self.pedidos = []

    def _pedir(self, ruta, parametros):
        self.pedidos.append((ruta, parametros))
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return {"scheduled" if ruta.startswith("/schedules/") else "flights": respuesta}


def http_error(codigo):
    return urllib.error.HTTPError("https://aeroapi.flightaware.com", codigo, "x", {}, io.BytesIO(b""))


class TestDesarrollo:
    def test_existe_con_la_hora_informada(self):
        datos = ConsultorVuelosDesarrollo().consultar("la 123", INFORMADA)
        assert (datos.numero, datos.hora_programada, datos.estado) == (
            "LA123",
            INFORMADA,
            EstadoVuelo.PROGRAMADO,
        )

    def test_zz_no_existe(self):
        assert ConsultorVuelosDesarrollo().consultar("ZZ999", INFORMADA) is None


class TestFlightAware:
    def test_elige_la_llegada_a_scl_del_dia_mas_cercana(self):
        consultor = FlightAwareFalso(
            [
                vuelo(destination={"code_iata": "LIM"}, scheduled_in="2026-11-05T12:30:00Z"),
                vuelo(scheduled_in="2026-11-05T22:00:00Z"),
                vuelo(scheduled_in="2026-11-04T12:30:00Z"),  # otro día
                vuelo(),
            ]
        )
        datos = consultor.consultar("LA 123", INFORMADA)
        assert datos.hora_programada == datetime(2026, 11, 5, 12, 40, tzinfo=ZoneInfo("UTC"))
        assert datos.estado == EstadoVuelo.PROGRAMADO
        ruta, parametros = consultor.pedidos[0]
        assert ruta == "/flights/LA123"
        assert parametros["ident_type"] == "designator"
        assert parametros["start"].startswith("2026-11-04T00:00:00")
        assert parametros["end"].startswith("2026-11-06T00:00:00")

    def test_entrega_el_origen(self):
        datos = FlightAwareFalso([vuelo(origin={"code_iata": "LIM"})]).consultar("LA123", INFORMADA)
        assert datos.origen_iata == "LIM"
        lejos = datetime(2026, 10, 20, 12, 0, tzinfo=SANTIAGO)
        fila = {"ident_iata": "LA123", "scheduled_in": "2026-11-05T12:40:00Z", "origin_iata": "ANF"}
        assert FlightAwareFalso([fila], ahora=lejos).consultar("LA123", INFORMADA).origen_iata == "ANF"

    def test_no_existe(self):
        assert (
            FlightAwareFalso([vuelo(destination={"code_iata": "LIM"})]).consultar("LA123", INFORMADA) is None
        )
        assert FlightAwareFalso(http_error(404)).consultar("LA123", INFORMADA) is None

    @pytest.mark.parametrize(
        ("cambios", "estado"),
        [
            ({"cancelled": True}, EstadoVuelo.CANCELADO),
            ({"diverted": True}, EstadoVuelo.DESVIADO),
            ({"actual_in": "2026-11-05T12:41:00Z"}, EstadoVuelo.ATERRIZADO),
            ({"estimated_in": "2026-11-05T12:55:00Z"}, EstadoVuelo.DEMORADO),
            ({"estimated_in": "2026-11-05T12:54:00Z"}, EstadoVuelo.PROGRAMADO),
        ],
    )
    def test_estado(self, cambios, estado):
        assert FlightAwareFalso([vuelo(**cambios)]).consultar("LA123", INFORMADA).estado == estado

    def test_reintenta_y_se_recupera(self):
        consultor = FlightAwareFalso(http_error(503), urllib.error.URLError("sin red"), [vuelo()])
        assert consultor.consultar("LA123", INFORMADA) is not None
        assert len(consultor.pedidos) == 3

    def test_sin_datos_tras_los_reintentos(self):
        with pytest.raises(VuelosNoDisponibles):
            FlightAwareFalso(TimeoutError(), TimeoutError(), TimeoutError()).consultar("LA123", INFORMADA)

    def test_clave_invalida_no_reintenta(self):
        consultor = FlightAwareFalso(http_error(401))
        with pytest.raises(VuelosNoDisponibles):
            consultor.consultar("LA123", INFORMADA)
        assert len(consultor.pedidos) == 1

    def test_lejos_en_el_futuro_usa_el_itinerario(self):
        """/flights no acepta fechas a más de 2 días: para esas se consulta /schedules."""
        consultor = FlightAwareFalso(
            [
                {"ident_iata": "LA123", "scheduled_in": "2026-11-05T22:00:00Z"},
                {"ident_iata": "LA123", "scheduled_in": "2026-11-05T12:40:00Z"},
                {"ident_iata": "LA123", "scheduled_in": "2026-11-06T12:40:00Z"},  # otro día
            ],
            ahora=datetime(2026, 10, 20, 12, 0, tzinfo=SANTIAGO),
        )
        datos = consultor.consultar("LA 123", INFORMADA)
        assert datos.hora_programada == datetime(2026, 11, 5, 12, 40, tzinfo=ZoneInfo("UTC"))
        assert (datos.hora_estimada, datos.estado) == (None, EstadoVuelo.PROGRAMADO)
        ruta, parametros = consultor.pedidos[0]
        assert ruta.startswith("/schedules/2026-11-04T00:00:00")
        assert parametros == {"airline": "LA", "flight_number": "123", "destination": "SCL"}

    def test_itinerario_sin_ese_vuelo(self):
        lejos = datetime(2026, 10, 20, 12, 0, tzinfo=SANTIAGO)
        assert FlightAwareFalso([], ahora=lejos).consultar("LA123", INFORMADA) is None

    def test_arma_la_peticion(self, monkeypatch):
        capturada = {}

        def urlopen(peticion, timeout):
            capturada.update(url=peticion.full_url, clave=peticion.get_header("X-apikey"), timeout=timeout)
            return io.BytesIO(json.dumps({"flights": []}).encode())

        monkeypatch.setattr(vuelos.urllib.request, "urlopen", urlopen)
        ConsultorFlightAware("clave-sintetica", ahora=lambda: HOY).consultar("H2 456", INFORMADA)
        assert capturada["url"].startswith(
            "https://aeroapi.flightaware.com/aeroapi/flights/H2456?ident_type=designator"
        )
        assert capturada["clave"] == "clave-sintetica"
        assert capturada["timeout"] == 5.0


def test_elige_el_consultor_segun_la_clave(settings):
    settings.FLIGHTAWARE_API_KEY = ""
    assert isinstance(obtener_consultor_vuelos(), ConsultorVuelosDesarrollo)
    settings.FLIGHTAWARE_API_KEY = "clave-sintetica"
    assert isinstance(obtener_consultor_vuelos(), ConsultorFlightAware)
