"""HU-71 (DC-72): sugerencias de direcciones con Photon (red simulada) y guardar con sus coordenadas."""

import io
import json
import urllib.error
import urllib.parse

import pytest
from django.urls import reverse

from apps.integraciones import sugerencias as s
from apps.reservas import servicios
from apps.reservas.models import Viaje
from apps.reservas.tests.test_api import LISTA, reserva

URL = reverse("sugerir-direcciones")
pytestmark = pytest.mark.django_db


def rasgo(
    nombre=None, calle=None, numero=None, ciudad="Providencia", pais="CL", lat=-33.43, lon=-70.61, **mas
):
    propiedades = {
        "name": nombre,
        "street": calle,
        "housenumber": numero,
        "city": ciudad,
        "countrycode": pais,
        **mas,
    }
    return {
        "properties": {k: v for k, v in propiedades.items() if v},
        "geometry": {"coordinates": [lon, lat]},
    }


@pytest.fixture(autouse=True)
def _sin_red_real(monkeypatch):
    """Ninguna prueba sale a internet: urlopen falla salvo que `red` lo reemplace."""

    def prohibido(*args, **kwargs):
        raise AssertionError("llamada real a la red")

    monkeypatch.setattr(s.urllib.request, "urlopen", prohibido)


class RedFalsa:
    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.pedidos = []

    def __call__(self, pedido, timeout):
        self.pedidos.append(pedido)
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return io.BytesIO(json.dumps(respuesta).encode())


@pytest.fixture
def red(monkeypatch, settings):
    settings.SUGERIDOR_DIRECCIONES = "photon"

    def preparar(*respuestas):
        falsa = RedFalsa(*respuestas)
        monkeypatch.setattr(s.urllib.request, "urlopen", falsa)
        return falsa

    return preparar


class TestPhoton:
    def test_consulta_con_nombres_locales_sesgo_y_user_agent(self, red):
        falsa = red({"features": [rasgo(calle="Avenida Providencia", numero="1234", district="Providencia")]})
        resultado = s.SugeridorPhoton().sugerir("providencia 1234", (-33.45, -70.66))
        assert resultado == [s.Sugerencia("Avenida Providencia 1234, Providencia", -33.43, -70.61)]
        pedido = falsa.pedidos[0]
        assert pedido.full_url.startswith("https://photon.komoot.io/api?")
        consulta = urllib.parse.parse_qs(urllib.parse.urlsplit(pedido.full_url).query)
        assert (consulta["lang"], consulta["lat"], consulta["lon"]) == (["default"], ["-33.45"], ["-70.66"])
        assert consulta["bbox"] == ["-76.0,-56.0,-66.0,-17.4"]
        assert (
            pedido.get_header("User-agent")
            == "FlotaAgil-pruebas (+https://github.com/flotaagil-cl/flotaagil)"
        )

    def test_solo_chile_sin_repetidos_y_hasta_cinco(self, red):
        rasgos = [
            rasgo(nombre="Mendoza", pais="AR", lat=-32.9, lon=-68.8),
            rasgo(nombre="Fuera del recuadro", lat=-10.0, lon=-70.0),
            rasgo(nombre="Sin texto", ciudad=None) | {"properties": {"countrycode": "CL"}},
            *[rasgo(calle="Los Leones", numero=str(100 + n), lat=-33.42 - n / 1000) for n in range(7)],
            rasgo(calle="Los Leones", numero="100"),
        ]
        falsa = red({"features": rasgos})
        resultado = s.SugeridorPhoton().sugerir("los leones", (-33.45, -70.66))
        assert [r.texto for r in resultado] == [f"Los Leones {100 + n}, Providencia" for n in range(5)]
        assert len(falsa.pedidos) == 1

    def test_nombre_y_calle_juntos(self, red):
        red({"features": [rasgo(nombre="Costanera Center", calle="Avenida Andrés Bello", numero="2425")]})
        [sugerencia] = s.SugeridorPhoton().sugerir("costanera", (-33.45, -70.66))
        assert sugerencia.texto == "Costanera Center, Avenida Andrés Bello 2425, Providencia"

    def test_cache_y_minimo_de_caracteres(self, red):
        falsa = red({"features": [rasgo(calle="Lira", numero="10")]})
        geo = s.SugeridorPhoton()
        assert geo.sugerir("li", (-33.45, -70.66)) == []
        assert geo.sugerir("lira 10", (-33.45, -70.66)) == geo.sugerir("  LIRA   10 ", (-33.45, -70.66))
        assert len(falsa.pedidos) == 1

    @pytest.mark.parametrize("falla", [urllib.error.URLError("caído"), TimeoutError()])
    def test_sin_servicio_lista_vacia_y_no_se_guarda(self, red, falla):
        falsa = red(falla, {"features": [rasgo(calle="Lira", numero="10")]})
        geo = s.SugeridorPhoton()
        assert geo.sugerir("lira 10", (-33.45, -70.66)) == []
        assert len(geo.sugerir("lira 10", (-33.45, -70.66))) == 1  # la siguiente vuelve a intentar
        assert len(falsa.pedidos) == 2


class TestEndpoint:
    def test_sin_sesion_con_el_slug_usa_la_zona_de_la_empresa(self, red, cliente, empresa):
        falsa = red({"features": [rasgo(calle="Lira", numero="10")]})
        respuesta = cliente.get(URL, {"q": "lira 10", "empresa": empresa.slug})
        assert respuesta.status_code == 200
        assert respuesta.json() == {
            "disponible": True,
            "sugerencias": [{"texto": "Lira 10, Providencia", "lat": -33.43, "lon": -70.61}],
        }
        consulta = urllib.parse.parse_qs(urllib.parse.urlsplit(falsa.pedidos[0].full_url).query)
        zona = empresa.configuracion
        assert float(consulta["lat"][0]) == pytest.approx(
            (float(zona.zona_lat_min) + float(zona.zona_lat_max)) / 2
        )

    def test_con_sesion_del_panel(self, red, panel, despachador):
        red({"features": []})
        panel.force_authenticate(despachador)
        assert panel.get(URL, {"q": "lira"}).json() == {"disponible": True, "sugerencias": []}

    def test_en_ninguno_no_consulta(self, cliente, settings):
        settings.SUGERIDOR_DIRECCIONES = "ninguno"
        assert cliente.get(URL, {"q": "lira 10"}).json() == {"disponible": False, "sugerencias": []}

    @pytest.mark.parametrize(
        ("valor", "debug", "esperado"),
        [
            ("", True, "photon"),
            ("", False, "ninguno"),
            ("NINGUNO", True, "ninguno"),
            ("photon", False, "photon"),
        ],
    )
    def test_proveedor_por_configuracion(self, settings, valor, debug, esperado):
        settings.SUGERIDOR_DIRECCIONES, settings.DEBUG = valor, debug
        assert s.proveedor_de_sugerencias() == esperado

    def test_limite_por_ip_y_por_usuario(self, red, cliente, panel, despachador, monkeypatch):
        monkeypatch.setattr(s.SugerenciasThrottle, "THROTTLE_RATES", {"sugerencias": "3/min"})
        red(*[{"features": []}] * 10)
        codigos = [cliente.get(URL, {"q": f"calle {n}"}).status_code for n in range(4)]
        assert codigos == [200, 200, 200, 429]
        # Con sesión cuenta por usuario, no por la IP agotada.
        panel.force_authenticate(despachador)
        assert panel.get(URL, {"q": "otra calle"}).status_code == 200


class TestGuardarConCoordenadas:
    @pytest.fixture
    def sin_geocodificar(self, monkeypatch):
        class Prohibido:
            def geocodificar(self, direccion, zona):
                raise AssertionError("no debió geocodificar")

        monkeypatch.setattr(servicios, "obtener_geocodificador", Prohibido)

    def test_el_panel_usa_las_coordenadas_sin_geocodificar(self, panel, despachador, sin_geocodificar):
        panel.force_authenticate(despachador)
        datos = reserva(
            origen_coordenadas={"lat": -33.4255, "lon": -70.6105},
            destino_coordenadas={"lat": -33.4372, "lon": -70.6506},
        )
        respuesta = panel.post(LISTA, datos, format="json")
        assert respuesta.status_code == 201, respuesta.data
        viaje = Viaje.objects.get(pk=respuesta.data["id"])
        assert (viaje.origen_geo.y, viaje.origen_geo.x) == (-33.4255, -70.6105)
        assert (viaje.destino_geo.y, viaje.destino_geo.x) == (-33.4372, -70.6506)

    def test_fuera_de_chile_se_rechaza(self, panel, despachador):
        panel.force_authenticate(despachador)
        datos = reserva(destino_coordenadas={"lat": -34.6, "lon": -58.38})  # Buenos Aires
        respuesta = panel.post(LISTA, datos, format="json")
        assert respuesta.status_code == 400 and "destino_coordenadas" in respuesta.data

    def test_al_editar_con_el_mismo_texto_y_otra_ubicacion(self, panel, despachador, sin_geocodificar):
        from apps.reservas.tests.fabricas import ViajeFactory

        panel.force_authenticate(despachador)
        viaje = ViajeFactory(empresa=despachador.empresa, destino_dir="Lira 10")
        url = reverse("viaje-detail", args=[viaje.pk])
        datos = {"destino_dir": "Lira 10", "destino_coordenadas": {"lat": -33.45, "lon": -70.64}}
        assert panel.patch(url, datos, format="json").status_code == 200
        viaje.refresh_from_db()
        assert (viaje.destino_geo.y, viaje.destino_geo.x) == (-33.45, -70.64)
