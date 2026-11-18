"""HU-69 (DC-69 aprobada): ciudad de origen del vuelo y número opcional del vuelo de salida."""

from datetime import datetime, timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.aeropuerto import monitoreo
from apps.aeropuerto.models import EstadoVuelo, Vuelo
from apps.integraciones.tests.test_vuelos import INFORMADA, FlightAwareFalso, vuelo
from apps.integraciones.vuelos import DatosVuelo
from apps.reservas.models import Sentido, Viaje
from apps.reservas.tests.fabricas import ViajeFactory
from apps.reservas.tests.test_api import LISTA, reserva

pytestmark = pytest.mark.django_db


def en_horas(horas):
    return (timezone.now() + timedelta(hours=horas)).isoformat()


def llegada(empresa):
    hora = timezone.now() + timedelta(hours=2)
    viaje = ViajeFactory(empresa=empresa, sentido=Sentido.DESDE_AEROPUERTO, recogida_en=hora)
    return Vuelo.objects.create(viaje=viaje, numero="LA845", fecha=hora.date(), hora_programada=hora)


@pytest.fixture
def api(panel, despachador):
    panel.force_authenticate(despachador)
    return panel


class TestCiudadDeOrigen:
    def test_aeroapi_entrega_ciudad_y_aeropuerto(self):
        origen = {"code_icao": "SPJC", "city": "Lima", "name": "Jorge Chávez Intl"}
        datos = FlightAwareFalso([vuelo(origin=origen)]).consultar("LA123", INFORMADA)
        assert (datos.origen_ciudad, datos.origen_aeropuerto) == ("Lima", "Jorge Chávez Intl")
        sin = FlightAwareFalso([vuelo(origin={"code_icao": "SPJC", "city": ""})]).consultar(
            "LA123", INFORMADA
        )
        assert (sin.origen_ciudad, sin.origen_aeropuerto) == (None, None)

    def test_el_monitoreo_la_guarda_y_una_consulta_sin_ella_no_la_borra(self, empresa):
        v = llegada(empresa)
        base = (v.numero, v.hora_programada, v.hora_programada, EstadoVuelo.PROGRAMADO, "SPJC")
        monitoreo.aplicar(v.pk, DatosVuelo(*base, "Lima", "Aeropuerto Internacional Jorge Chávez"))
        v = monitoreo.aplicar(v.pk, DatosVuelo(*base))
        assert (v.origen_ciudad, v.origen_aeropuerto) == ("Lima", "Aeropuerto Internacional Jorge Chávez")

    @override_settings(DEBUG=True)
    @pytest.mark.parametrize(
        ("origen", "ciudad"), [("SPJC", "Lima"), ("SCFA", "Antofagasta"), ("ZZZZ", None)]
    )
    def test_el_simulador_da_la_ciudad_segun_el_codigo(self, empresa, origen, ciudad):
        v = llegada(empresa)
        call_command("simular_vuelo", v.viaje_id, "--eta-min", "0", "--origen", origen, stdout=StringIO())
        v.refresh_from_db()
        assert v.origen_ciudad == ciudad

    def test_el_listado_la_entrega(self, api, despachador):
        v = llegada(despachador.empresa)
        Vuelo.objects.filter(pk=v.pk).update(origen_icao="SPJC", origen_ciudad="Lima")
        fila = api.get(LISTA).json()["results"][0]
        assert (fila["vuelo"]["origen_ciudad"], fila["vuelo"]["origen_aeropuerto"]) == ("Lima", None)


class TestNumeroDeSalida:
    def test_el_panel_lo_guarda_normalizado(self, api):
        datos = reserva(sentido="HACIA_AEROPUERTO", vuelo_salida_numero=" la  601 ")
        respuesta = api.post(LISTA, datos, format="json")
        assert respuesta.status_code == 201, respuesta.data
        assert respuesta.data["vuelo_salida_numero"] == "LA 601"

    @pytest.mark.parametrize("numero", ["", None])
    def test_es_opcional(self, api, numero):
        respuesta = api.post(
            LISTA, reserva(sentido="HACIA_AEROPUERTO", vuelo_salida_numero=numero), format="json"
        )
        assert respuesta.status_code == 201 and respuesta.data["vuelo_salida_numero"] is None

    @pytest.mark.parametrize(
        ("sentido", "numero"),
        [("URBANO", "LA601"), ("DESDE_AEROPUERTO", "LA601"), ("HACIA_AEROPUERTO", "ABCDEF")],
    )
    def test_rechazos(self, api, sentido, numero):
        respuesta = api.post(LISTA, reserva(sentido=sentido, vuelo_salida_numero=numero), format="json")
        assert respuesta.status_code == 400 and "vuelo_salida_numero" in respuesta.data

    def test_editar_y_borrarlo_al_dejar_de_ir_al_aeropuerto(self, api, despachador):
        viaje = ViajeFactory(empresa=despachador.empresa, sentido=Sentido.HACIA_AEROPUERTO)
        url = reverse("viaje-detail", args=[viaje.pk])
        assert (
            api.patch(url, {"vuelo_salida_numero": "JA 30"}, format="json").data["vuelo_salida_numero"]
            == "JA 30"
        )
        assert api.patch(url, {"sentido": "URBANO"}, format="json").data["vuelo_salida_numero"] is None
        assert api.patch(url, {"vuelo_salida_numero": "JA30"}, format="json").status_code == 400

    def test_sin_numero_la_salida_sigue_igual(self, empresa):
        viaje = ViajeFactory(
            empresa=empresa,
            sentido=Sentido.HACIA_AEROPUERTO,
            vuelo_salida_en=datetime.fromisoformat(en_horas(5)),
            vuelo_salida_tipo="NACIONAL",
        )
        assert Viaje.objects.get(pk=viaje.pk).vuelo_salida_numero is None


class TestSalidaEnElPanel:
    """DC-70 (aprobada con cambio): hora y tipo de salida opcionales en el panel, como en el portal."""

    @pytest.mark.parametrize(
        ("tipo", "antelacion"),
        [
            ("NACIONAL", "antelacion_vuelo_nacional_min"),
            ("INTERNACIONAL", "antelacion_vuelo_internacional_min"),
        ],
    )
    def test_con_hora_calcula_cuando_debe_estar_en_el_aeropuerto(self, api, despachador, tipo, antelacion):
        despegue = timezone.now() + timedelta(hours=8)
        datos = reserva(
            sentido="HACIA_AEROPUERTO",
            vuelo_salida_numero="LA601",
            vuelo_salida_en=despegue.isoformat(),
            vuelo_salida_tipo=tipo,
        )
        respuesta = api.post(LISTA, datos, format="json")
        assert respuesta.status_code == 201, respuesta.data
        minutos = getattr(despachador.empresa.configuracion, antelacion)
        esperado = timezone.localtime(despegue - timedelta(minutes=minutos)).isoformat()
        assert respuesta.data["vuelo_salida_tipo"] == tipo
        assert respuesta.data["en_aeropuerto_a_las"] == esperado

    def test_sin_hora_queda_sin_hora_en_el_aeropuerto(self, api):
        respuesta = api.post(
            LISTA, reserva(sentido="HACIA_AEROPUERTO", vuelo_salida_numero="LA601"), format="json"
        )
        assert respuesta.status_code == 201
        assert (respuesta.data["vuelo_salida_en"], respuesta.data["en_aeropuerto_a_las"]) == (None, None)

    @pytest.mark.parametrize(
        ("cambios", "campo"),
        [
            ({"vuelo_salida_en": en_horas(8)}, "vuelo_salida_tipo"),
            ({"vuelo_salida_tipo": "NACIONAL"}, "vuelo_salida_en"),
            (
                {"sentido": "URBANO", "vuelo_salida_en": en_horas(8), "vuelo_salida_tipo": "NACIONAL"},
                "vuelo_salida_en",
            ),
        ],
    )
    def test_hora_y_tipo_van_juntos_y_solo_hacia_el_aeropuerto(self, api, cambios, campo):
        respuesta = api.post(LISTA, reserva(**{"sentido": "HACIA_AEROPUERTO", **cambios}), format="json")
        assert respuesta.status_code == 400 and campo in respuesta.data

    def test_editar_agrega_quita_y_borra_al_cambiar_de_sentido(self, api, despachador):
        viaje = ViajeFactory(empresa=despachador.empresa, sentido=Sentido.HACIA_AEROPUERTO)
        url = reverse("viaje-detail", args=[viaje.pk])
        hora = en_horas(8)
        datos = api.patch(url, {"vuelo_salida_en": hora, "vuelo_salida_tipo": "NACIONAL"}, format="json").data
        assert datos["en_aeropuerto_a_las"] is not None
        assert api.patch(url, {"vuelo_salida_tipo": None}, format="json").status_code == 400
        quitada = api.patch(url, {"vuelo_salida_en": None, "vuelo_salida_tipo": None}, format="json").data
        assert quitada["en_aeropuerto_a_las"] is None
        api.patch(url, {"vuelo_salida_en": hora, "vuelo_salida_tipo": "INTERNACIONAL"}, format="json")
        urbano = api.patch(url, {"sentido": "URBANO"}, format="json").data
        assert (urbano["vuelo_salida_en"], urbano["vuelo_salida_tipo"]) == (None, None)
