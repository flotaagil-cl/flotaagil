"""HU-70 (DC-71): geocodificación con Nominatim, solo para desarrollo y pruebas. Sin red: urlopen simulado."""

import io
import json
import urllib.error
import urllib.parse

import pytest
from django.core.cache import cache

from apps.integraciones import geocodificador as g

RM = g.Zona(-33.70, -33.20, -70.95, -70.40)
LIMA = [{"lat": "-33.4372", "lon": "-70.6506", "display_name": "Plaza de Armas, Santiago, Chile"}]

pytestmark = pytest.mark.django_db


class RedFalsa:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.pedidos = []

    def __call__(self, pedido, timeout):
        self.pedidos.append(pedido)
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return io.BytesIO(json.dumps(respuesta).encode())


class Reloj:
    """Reloj y sueño simulados: dormir avanza el reloj y, al pasar 1 s, vence el candado de Redis."""

    def __init__(self):
        self.ahora = 0.0
        self.esperas = []

    def dormir(self, segundos):
        self.esperas.append(segundos)
        self.ahora += segundos
        if sum(self.esperas) >= 1:
            cache.delete(g.GeocodificadorNominatim.CANDADO)

    def __call__(self):
        return self.ahora


@pytest.fixture
def red(monkeypatch):
    def preparar(*respuestas):
        falsa = RedFalsa(respuestas)
        monkeypatch.setattr(g.urllib.request, "urlopen", falsa)
        return falsa

    return preparar


@pytest.fixture
def reloj():
    return Reloj()


def nominatim(reloj, **opciones):
    return g.GeocodificadorNominatim(dormir=reloj.dormir, reloj=reloj, **opciones)


def test_consulta_en_chile_con_sesgo_a_la_zona_y_user_agent(red, reloj):
    falsa = red(LIMA)
    assert nominatim(reloj).geocodificar("Plaza de Armas, Santiago", RM) == g.Coordenadas(-33.4372, -70.6506)
    pedido = falsa.pedidos[0]
    assert pedido.full_url.startswith("https://nominatim.openstreetmap.org/search?")
    consulta = urllib.parse.parse_qs(urllib.parse.urlsplit(pedido.full_url).query)
    assert consulta["countrycodes"] == ["cl"]
    assert consulta["viewbox"] == ["-70.95,-33.2,-70.4,-33.7"]
    assert consulta["format"] == ["jsonv2"] and consulta["limit"] == ["1"]
    assert pedido.get_header("User-agent") == "FlotaAgil-pruebas (+https://github.com/flotaagil-cl/flotaagil)"


def test_la_cache_evita_repetir_la_consulta(red, reloj):
    falsa = red(LIMA)
    geo = nominatim(reloj)
    primera = geo.geocodificar("Plaza de Armas, Santiago", RM)
    # Misma dirección con otras mayúsculas y espacios: sale de la caché, sin otra solicitud.
    assert geo.geocodificar("  plaza de armas,   SANTIAGO ", RM) == primera
    assert len(falsa.pedidos) == 1


def test_una_solicitud_por_segundo_con_candado_en_redis(red, reloj):
    falsa = red(LIMA, LIMA)
    geo = nominatim(reloj)
    geo.geocodificar("Plaza de Armas, Santiago", RM)
    assert reloj.esperas == []  # la primera no espera
    geo.geocodificar("Av. Providencia 1234", RM)  # el candado sigue tomado: espera hasta que vence (1 s)
    assert len(falsa.pedidos) == 2 and sum(reloj.esperas) >= 1


def test_si_el_candado_no_se_libera_avisa_que_no_esta_disponible(red, reloj):
    red()
    cache.add(g.GeocodificadorNominatim.CANDADO, 1, timeout=60)
    geo = g.GeocodificadorNominatim(dormir=lambda s: None, reloj=iter(range(100)).__next__)
    with pytest.raises(g.GeocodificacionError, match="no está disponible"):
        geo.geocodificar("Av. Providencia 1234", RM)


def test_sin_resultados_no_encontrada_y_tambien_se_recuerda(red, reloj):
    falsa = red([])
    geo = nominatim(reloj)
    for _ in range(2):
        with pytest.raises(g.GeocodificacionError, match="No se encontró"):
            geo.geocodificar("Calle que no existe 999", RM)
    assert len(falsa.pedidos) == 1


def test_reintenta_errores_de_red_y_agota_los_intentos(red, reloj):
    falsa = red(urllib.error.URLError("caído"), TimeoutError(), LIMA)
    assert nominatim(reloj).geocodificar("Plaza de Armas, Santiago", RM).lat == -33.4372
    assert len(falsa.pedidos) == 3
    cache.clear()
    red(TimeoutError(), urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None), TimeoutError())
    with pytest.raises(g.GeocodificacionError, match="no está disponible"):
        nominatim(Reloj()).geocodificar("Av. Providencia 1234", RM)


def test_direccion_vacia(red, reloj):
    red()
    with pytest.raises(g.GeocodificacionError, match="vacía"):
        nominatim(reloj).geocodificar("   ", RM)


@pytest.mark.parametrize(
    ("geocodificador", "clave", "debug", "esperado"),
    [
        ("", "", True, g.GeocodificadorNominatim),  # desarrollo sin clave: Nominatim
        ("", "", False, g.GeocodificadorDesarrollo),  # producción sin clave: el de desarrollo, como hoy
        ("", "clave", True, g.GeocodificadorGoogle),  # con clave: Google
        ("nominatim", "clave", False, g.GeocodificadorNominatim),
        ("desarrollo", "clave", True, g.GeocodificadorDesarrollo),
        ("google", "", True, g.GeocodificadorDesarrollo),  # Google sin clave no puede: el de desarrollo
        ("GOOGLE", "clave", False, g.GeocodificadorGoogle),
    ],
)
def test_eleccion_del_proveedor(settings, geocodificador, clave, debug, esperado):
    settings.GEOCODIFICADOR, settings.GOOGLE_GEOCODING_API_KEY, settings.DEBUG = geocodificador, clave, debug
    assert isinstance(g.obtener_geocodificador(), esperado)


def test_nominatim_da_coordenadas_reales_para_navegar(settings):
    settings.GEOCODIFICADOR = "nominatim"
    assert g.coordenadas_reales() is True
