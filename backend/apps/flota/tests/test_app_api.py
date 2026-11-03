"""API de la app del conductor: perfil, consentimiento (RN-18) y posiciones GPS."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.flota.models import ConductorVehiculo, EstadoConductor, PosicionGps
from apps.reservas.models import EstadoViaje
from apps.reservas.tests.fabricas import ConductorFactory, VehiculoFactory, ViajeFactory

PERFIL = reverse("app-perfil")
CONSENTIMIENTO = reverse("app-consentimiento")
POSICIONES = reverse("app-posiciones")


def posicion(segundos_atras=10, **cambios):
    return {
        "lat": -33.45,
        "lon": -70.66,
        "precision_m": 8.4,
        "registrada_en": (timezone.now() - timedelta(seconds=segundos_atras)).isoformat(),
    } | cambios


@pytest.fixture
def chofer(empresa):
    vehiculo = VehiculoFactory(empresa=empresa, patente="BCDF10")
    conductor = ConductorFactory(
        usuario__empresa=empresa,
        estado=EstadoConductor.DISPONIBLE,
        vehiculo_activo=vehiculo,
        consentimiento_gps_en=timezone.now(),
    )
    ConductorVehiculo.objects.create(conductor=conductor, vehiculo=vehiculo)
    return conductor


@pytest.fixture
def app(cliente, chofer):
    cliente.force_authenticate(chofer.usuario)
    return cliente


@pytest.mark.django_db
class TestPermisos:
    @pytest.mark.parametrize("url", [PERFIL, CONSENTIMIENTO, POSICIONES])
    def test_solo_conductores(self, cliente, despachador, url):
        assert cliente.get(url).status_code == 401
        cliente.force_authenticate(despachador)
        assert cliente.post(url, {}, format="json").status_code == 403


@pytest.mark.django_db
class TestPerfil:
    def test_muestra_solo_vehiculos_activos(self, app, chofer, empresa):
        inactivo = VehiculoFactory(empresa=empresa, activo=False)
        ConductorVehiculo.objects.create(conductor=chofer, vehiculo=inactivo)
        datos = app.get(PERFIL).json()
        assert datos["estado"] == "DISPONIBLE"
        assert datos["vehiculo_activo"]["patente"] == "BCDF10"
        assert [v["patente"] for v in datos["vehiculos"]] == ["BCDF10"]


@pytest.mark.django_db
class TestConsentimiento:
    def test_acepta_una_vez(self, cliente, empresa):
        conductor = ConductorFactory(usuario__empresa=empresa)
        cliente.force_authenticate(conductor.usuario)
        primera = cliente.post(CONSENTIMIENTO).json()["consentimiento_gps_en"]
        assert primera is not None
        assert cliente.post(CONSENTIMIENTO).json()["consentimiento_gps_en"] == primera


@pytest.mark.django_db
class TestPosiciones:
    def test_guarda_el_lote(self, app, chofer):
        respuesta = app.post(POSICIONES, {"posiciones": [posicion(20), posicion(10)]}, format="json")
        assert respuesta.status_code == 201
        assert respuesta.json() == {"recibidas": 2, "repetidas": 0, "descartadas": 0}
        guardada = PosicionGps.objects.filter(conductor=chofer).latest("registrada_en")
        assert (round(guardada.punto.y, 2), round(guardada.punto.x, 2), guardada.precision_m) == (
            -33.45,
            -70.66,
            8,
        )
        assert guardada.confiable is True
        assert guardada.viaje is None

    def test_reenviar_no_duplica(self, app):
        lote = {"posiciones": [posicion(20), posicion(10)]}
        app.post(POSICIONES, lote, format="json")
        assert app.post(POSICIONES, lote, format="json").json() == {
            "recibidas": 0,
            "repetidas": 2,
            "descartadas": 0,
        }
        assert PosicionGps.objects.count() == 2

    def test_descarta_imprecisas_futuras_y_viejas(self, app):
        lote = [
            posicion(precision_m=900),
            posicion(-600),
            posicion(31 * 86400),
            posicion(5, precision_m=None),
        ]
        assert app.post(POSICIONES, {"posiciones": lote}, format="json").json() == {
            "recibidas": 1,
            "repetidas": 0,
            "descartadas": 3,
        }
        assert PosicionGps.objects.get().confiable is False

    def test_se_asocia_al_viaje_en_curso(self, app, chofer, empresa):
        viaje = ViajeFactory(empresa=empresa, conductor=chofer, estado=EstadoViaje.EN_CAMINO)
        ViajeFactory(empresa=empresa, conductor=chofer, estado=EstadoViaje.FINALIZADO)
        app.post(POSICIONES, {"posiciones": [posicion()]}, format="json")
        assert PosicionGps.objects.get().viaje == viaje

    def test_fuera_de_turno(self, app, chofer):
        chofer.estado = EstadoConductor.NO_DISPONIBLE
        chofer.save()
        respuesta = app.post(POSICIONES, {"posiciones": [posicion()]}, format="json")
        assert (respuesta.status_code, respuesta.json()["code"]) == (409, "fuera_de_turno")

    def test_sin_consentimiento(self, app, chofer):
        chofer.consentimiento_gps_en = None
        chofer.save()
        respuesta = app.post(POSICIONES, {"posiciones": [posicion()]}, format="json")
        assert (respuesta.status_code, respuesta.json()["code"]) == (409, "sin_consentimiento")
        assert not PosicionGps.objects.exists()

    @pytest.mark.parametrize(
        "lote",
        [{"posiciones": []}, {"posiciones": [posicion(lat=95)]}, {"posiciones": [posicion()] * 101}, {}],
    )
    def test_lote_invalido(self, app, lote):
        assert app.post(POSICIONES, lote, format="json").status_code == 400
