"""Generación dinámica de vuelos demo y consulta en vivo desde Vuelos de hoy (HU-27, HU-69)."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.aeropuerto.demo import PARRILLA_VUELOS_DEMO, asegurar_vuelos_demo_vigentes
from apps.aeropuerto.models import AlertaVuelo, EstadoVuelo, Vuelo
from apps.reservas.models import Viaje

URL_HOY = reverse("vuelos-de-hoy")
URL_CONSULTAR = reverse("vuelos-de-hoy-consultar")
pytestmark = pytest.mark.django_db


@pytest.fixture
def api(panel, despachador):
    panel.force_authenticate(despachador)
    return panel


class TestAsegurarVuelosDemo:
    def test_no_corre_si_debug_esta_apagado_o_hay_api_key(self, empresa, settings):
        settings.DEBUG = False
        settings.FLIGHTAWARE_API_KEY = ""
        assert asegurar_vuelos_demo_vigentes(empresa) == 0
        assert Vuelo.objects.count() == 0

        settings.DEBUG = True
        settings.FLIGHTAWARE_API_KEY = "clave-real-sintetica"
        assert asegurar_vuelos_demo_vigentes(empresa) == 0
        assert Vuelo.objects.count() == 0

    def test_genera_6_vuelos_por_3_dias_y_es_idempotente(self, empresa, settings):
        settings.DEBUG = True
        settings.FLIGHTAWARE_API_KEY = ""
        creados = asegurar_vuelos_demo_vigentes(empresa)
        assert creados == len(PARRILLA_VUELOS_DEMO) * 3 == 18
        assert Viaje.objects.filter(empresa=empresa).count() == 18

        hoy = timezone.localdate()
        for offset in range(3):
            dia = hoy + timedelta(days=offset)
            assert Vuelo.objects.filter(viaje__empresa=empresa, fecha=dia).count() == 6

        # Hoy incluye un aterrizado temprano, un demorado con propuesta y un internacional (KMIA).
        aterrizado_hoy = Vuelo.objects.get(viaje__empresa=empresa, fecha=hoy, numero="LA 305")
        assert aterrizado_hoy.estado_vuelo == EstadoVuelo.ATERRIZADO

        demorado = Vuelo.objects.get(viaje__empresa=empresa, fecha=hoy, numero="LA 450")
        assert demorado.estado_vuelo == EstadoVuelo.DEMORADO
        assert demorado.hora_estimada == demorado.hora_programada + timedelta(minutes=25)
        assert demorado.recogida_propuesta == demorado.hora_estimada + timedelta(
            minutes=empresa.configuracion.margen_nacional_min
        )
        assert AlertaVuelo.objects.filter(viaje=demorado.viaje).exists()

        internacional = Vuelo.objects.get(viaje__empresa=empresa, fecha=hoy, numero="LA 800")
        assert internacional.origen_icao == "KMIA"

        # Segunda ejecución: completamente idempotente.
        assert asegurar_vuelos_demo_vigentes(empresa) == 0
        assert Vuelo.objects.filter(viaje__empresa=empresa).count() == 18


class TestRangoYConsultaEnVivo:
    def test_filtra_por_hoy_manana_y_proximos_3_dias_en_desarrollo(self, api, settings):
        settings.DEBUG = True
        settings.FLIGHTAWARE_API_KEY = ""
        hoy = timezone.localdate()

        resp_hoy = api.get(URL_HOY)
        assert resp_hoy.status_code == 200
        assert resp_hoy.json()["fecha"] == hoy.isoformat()
        assert len(resp_hoy.json()["viajes"]) == 6

        resp_manana = api.get(URL_HOY, {"rango": "manana"})
        assert resp_manana.status_code == 200
        assert resp_manana.json()["fecha"] == (hoy + timedelta(days=1)).isoformat()
        assert len(resp_manana.json()["viajes"]) == 6

        resp_3 = api.get(URL_HOY, {"rango": "proximos_3_dias"})
        assert resp_3.status_code == 200
        assert len(resp_3.json()["viajes"]) == 18

        assert api.get(URL_HOY, {"rango": "otro"}).status_code == 400

    def test_consultar_ahora_ejecuta_el_adaptador_sobre_vuelos_activos(self, api, settings):
        settings.DEBUG = True
        settings.FLIGHTAWARE_API_KEY = ""
        resp = api.post(URL_CONSULTAR, {"rango": "hoy"}, format="json")
        assert resp.status_code == 200
        datos = resp.json()
        # De los 6 de hoy, LA 305 ya está ATERRIZADO (estado final) y los otros 5 se consultan.
        assert datos == {"consultados": 5, "actualizados": 5, "sin_datos": 0}
