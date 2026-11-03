"""Turno del conductor (HU-13).

CP-03: quedar Disponible con su vehículo (RN-05, RN-18). CP-04: No disponible y estados que no se cambian.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.flota.models import ConductorVehiculo, EstadoConductor
from apps.reservas.tests.fabricas import ConductorFactory, VehiculoFactory

TURNO = reverse("app-turno")
D, ND = EstadoConductor.DISPONIBLE, EstadoConductor.NO_DISPONIBLE


@pytest.fixture
def chofer(empresa):
    return ConductorFactory(usuario__empresa=empresa, consentimiento_gps_en=timezone.now())


@pytest.fixture
def app(cliente, chofer):
    cliente.force_authenticate(chofer.usuario)
    return cliente


def asociar(conductor, **kwargs):
    vehiculo = VehiculoFactory(empresa=conductor.usuario.empresa, **kwargs)
    ConductorVehiculo.objects.create(conductor=conductor, vehiculo=vehiculo)
    return vehiculo


def codigo(respuesta):
    return respuesta.status_code, respuesta.json().get("code")


@pytest.mark.django_db
class TestDisponible:
    def test_con_un_solo_vehiculo_lo_declara_solo(self, app, chofer):
        vehiculo = asociar(chofer)
        datos = app.post(TURNO, {"estado": "DISPONIBLE"}, format="json").json()
        assert (datos["estado"], datos["vehiculo_activo"]["id"]) == ("DISPONIBLE", vehiculo.pk)

    def test_con_varios_hay_que_elegir(self, app, chofer):
        """RN-05."""
        asociar(chofer)
        segundo = asociar(chofer)
        assert codigo(app.post(TURNO, {"estado": "DISPONIBLE"}, format="json")) == (409, "elegir_vehiculo")
        datos = app.post(TURNO, {"estado": "DISPONIBLE", "vehiculo": segundo.pk}, format="json").json()
        assert datos["vehiculo_activo"]["id"] == segundo.pk

    def test_los_inactivos_no_cuentan(self, app, chofer):
        asociar(chofer, activo=False)
        activo = asociar(chofer)
        assert (
            app.post(TURNO, {"estado": "DISPONIBLE"}, format="json").json()["vehiculo_activo"]["id"]
            == activo.pk
        )

    def test_vehiculo_ajeno_o_inactivo(self, app, chofer, otra_empresa):
        asociar(chofer)
        inactivo = asociar(chofer, activo=False)
        ajeno = VehiculoFactory(empresa=otra_empresa)
        for vehiculo in (inactivo, ajeno):
            respuesta = app.post(TURNO, {"estado": "DISPONIBLE", "vehiculo": vehiculo.pk}, format="json")
            assert codigo(respuesta) == (409, "vehiculo_no_disponible")

    def test_sin_vehiculo(self, app):
        assert codigo(app.post(TURNO, {"estado": "DISPONIBLE"}, format="json")) == (409, "sin_vehiculo")

    def test_sin_consentimiento(self, app, chofer):
        """RN-18."""
        asociar(chofer)
        chofer.consentimiento_gps_en = None
        chofer.save()
        assert codigo(app.post(TURNO, {"estado": "DISPONIBLE"}, format="json")) == (409, "sin_consentimiento")
        chofer.refresh_from_db()
        assert chofer.estado == ND

    def test_licencia_vencida(self, app, chofer):
        asociar(chofer)
        chofer.licencia_vence = timezone.localdate() - timedelta(days=1)
        chofer.save()
        assert codigo(app.post(TURNO, {"estado": "DISPONIBLE"}, format="json")) == (409, "licencia_vencida")

    def test_vehiculo_en_turno_con_otro_conductor(self, app, chofer, empresa):
        vehiculo = asociar(chofer)
        otro = ConductorFactory(usuario__empresa=empresa, estado=D, vehiculo_activo=vehiculo)
        ConductorVehiculo.objects.create(conductor=otro, vehiculo=vehiculo)
        respuesta = app.post(TURNO, {"estado": "DISPONIBLE"}, format="json")
        assert codigo(respuesta) == (409, "vehiculo_ocupado")
        assert vehiculo.patente in respuesta.json()["detail"]

    def test_cambiar_de_vehiculo_estando_disponible(self, app, chofer):
        primero = asociar(chofer)
        segundo = asociar(chofer)
        app.post(TURNO, {"estado": "DISPONIBLE", "vehiculo": primero.pk}, format="json")
        datos = app.post(TURNO, {"estado": "DISPONIBLE", "vehiculo": segundo.pk}, format="json").json()
        assert datos["vehiculo_activo"]["id"] == segundo.pk


@pytest.mark.django_db
class TestNoDisponible:
    def test_borra_el_vehiculo_declarado(self, app, chofer):
        asociar(chofer)
        app.post(TURNO, {"estado": "DISPONIBLE"}, format="json")
        datos = app.post(TURNO, {"estado": "NO_DISPONIBLE"}, format="json").json()
        assert (datos["estado"], datos["vehiculo_activo"]) == ("NO_DISPONIBLE", None)

    def test_no_disponible_sin_consentimiento_si_se_puede(self, app, chofer):
        chofer.consentimiento_gps_en = None
        chofer.save()
        assert app.post(TURNO, {"estado": "NO_DISPONIBLE"}, format="json").status_code == 200

    def test_en_viaje_no_cambia(self, app, chofer):
        """RN-03: el estado cambia al terminar el viaje."""
        chofer.vehiculo_activo, chofer.estado = asociar(chofer), EstadoConductor.EN_VIAJE
        chofer.save()
        for estado in ("NO_DISPONIBLE", "DISPONIBLE"):
            assert codigo(app.post(TURNO, {"estado": estado}, format="json")) == (409, "en_viaje")

    @pytest.mark.parametrize("cuerpo", [{}, {"estado": "EN_VIAJE"}, {"estado": "OTRO"}])
    def test_estado_invalido(self, app, cuerpo):
        assert app.post(TURNO, cuerpo, format="json").status_code == 400

    def test_solo_conductores(self, cliente, despachador):
        cliente.force_authenticate(despachador)
        assert cliente.post(TURNO, {"estado": "DISPONIBLE"}, format="json").status_code == 403
