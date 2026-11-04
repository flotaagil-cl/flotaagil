"""Viaje en curso del conductor para navegar con Google Maps o Waze (HU-17)."""

import pytest
from django.contrib.gis.geos import Point
from django.urls import reverse

from apps.aeropuerto.models import Vuelo
from apps.reservas.models import EstadoViaje
from apps.reservas.tests.fabricas import ConductorFactory, ViajeFactory

URL = reverse("app-viaje-activo")
ORIGEN = Point(-70.7858, -33.3930, srid=4326)  # aeropuerto (aprox.)
DESTINO = Point(-70.6100, -33.4260, srid=4326)


@pytest.fixture
def chofer(empresa):
    return ConductorFactory(usuario__empresa=empresa)


@pytest.fixture
def app(cliente, chofer):
    cliente.force_authenticate(chofer.usuario)
    return cliente


def viaje(chofer, estado, **cambios):
    return ViajeFactory(
        empresa=chofer.usuario.empresa,
        conductor=chofer,
        estado=estado,
        origen_dir="Aeropuerto SCL",
        origen_geo=ORIGEN,
        destino_dir="Av. Providencia 1234",
        destino_geo=DESTINO,
        **cambios,
    )


@pytest.mark.django_db
class TestViajeActivo:
    def test_sin_viaje(self, app, chofer):
        viaje(chofer, EstadoViaje.FINALIZADO)
        viaje(chofer, EstadoViaje.ASIGNADO)  # aún no lo acepta
        assert app.get(URL).json() == {"viaje": None}

    @pytest.mark.parametrize("estado", [EstadoViaje.ACEPTADO, EstadoViaje.EN_CAMINO, EstadoViaje.EN_ZONA])
    def test_antes_de_subir_navega_al_origen(self, app, chofer, estado):
        v = viaje(chofer, estado)
        Vuelo.objects.create(
            viaje=v, numero="LA123", fecha=v.recogida_en.date(), hora_programada=v.recogida_en
        )
        datos = app.get(URL).json()["viaje"]
        assert datos["hacia"] == {"direccion": "Aeropuerto SCL", "lat": -33.393, "lon": -70.7858}
        assert datos["vuelo"] == "LA123"
        assert datos["estado"] == estado

    def test_con_el_pasajero_a_bordo_navega_al_destino(self, app, chofer):
        viaje(chofer, EstadoViaje.PASAJERO_A_BORDO)
        datos = app.get(URL).json()["viaje"]
        assert datos["hacia"]["direccion"] == "Av. Providencia 1234"
        assert datos["vuelo"] is None

    def test_solo_los_viajes_propios(self, app, empresa):
        otro = ConductorFactory(usuario__empresa=empresa)
        viaje(otro, EstadoViaje.EN_CAMINO)
        assert app.get(URL).json() == {"viaje": None}

    def test_solo_conductores(self, cliente, despachador):
        cliente.force_authenticate(despachador)
        assert cliente.get(URL).status_code == 403


@pytest.mark.django_db
class TestNavegarCon:
    """DC-30."""

    def test_con_el_geocodificador_de_desarrollo_navega_con_la_direccion(self, app, chofer, settings):
        settings.GOOGLE_GEOCODING_API_KEY = ""
        viaje(chofer, EstadoViaje.ACEPTADO)
        assert app.get(URL).json()["viaje"]["navegar_con"] == "DIRECCION"

    def test_con_el_geocodificador_real_navega_con_las_coordenadas(self, app, chofer, settings):
        settings.GOOGLE_GEOCODING_API_KEY = "clave-sintetica"
        viaje(chofer, EstadoViaje.ACEPTADO)
        assert app.get(URL).json()["viaje"]["navegar_con"] == "COORDENADAS"

    def test_la_direccion_y_las_coordenadas_siguen_disponibles(self, app, chofer, settings):
        settings.GOOGLE_GEOCODING_API_KEY = ""
        viaje(chofer, EstadoViaje.ACEPTADO)
        hacia = app.get(URL).json()["viaje"]["hacia"]
        assert hacia == {"direccion": "Aeropuerto SCL", "lat": -33.393, "lon": -70.7858}
