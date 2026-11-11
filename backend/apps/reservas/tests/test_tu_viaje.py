"""HU-43: «Tu viaje». El pasajero ve solo SU viaje (404 si no es suyo), con conductor, vehículo y
patente desde que el conductor acepta, el vuelo y su avance sin datos del personal."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.aeropuerto.models import Vuelo
from apps.reservas.models import EstadoViaje, HistorialEstado, Pasajero, Viaje
from apps.reservas.tests.fabricas import ConductorFactory, PasajeroFactory, VehiculoFactory, ViajeFactory

E = EstadoViaje


@pytest.fixture
def mio(con_cuenta, empresa):
    """Un viaje del pasajero de la cuenta (teléfono +56900009101)."""
    pasajero = Pasajero.objects.get(empresa=empresa, telefono="+56900009101")
    return ViajeFactory(empresa=empresa, pasajero=pasajero, estado=E.SOLICITADO, pasajeros=2, maletas=1)


def url(viaje):
    return reverse("mi-cuenta-reserva", args=[viaje.pk])


@pytest.mark.django_db
class TestTuViaje:
    def test_ve_su_viaje_sin_conductor_todavia(self, con_cuenta, mio):
        datos = con_cuenta.get(url(mio)).json()
        assert datos["id"] == mio.pk
        assert (datos["estado"], datos["cancelable"], datos["pasajeros"], datos["maletas"]) == (
            "SOLICITADO",
            True,
            2,
            1,
        )
        assert (datos["conductor"], datos["vehiculo"], datos["vuelo"]) == (None, None, None)
        assert set(datos["origen"]) == {"lat", "lng"}

    def test_no_ve_viajes_ajenos(self, con_cuenta, empresa, otra_empresa):
        ajeno = ViajeFactory(empresa=empresa, pasajero=PasajeroFactory(empresa=empresa))
        de_otra = ViajeFactory(empresa=otra_empresa)
        assert con_cuenta.get(url(ajeno)).status_code == 404
        assert con_cuenta.get(url(de_otra)).status_code == 404

    @pytest.mark.parametrize("estado", [E.ASIGNADO, E.SOLICITADO])
    def test_sin_aceptar_no_muestra_al_conductor(self, con_cuenta, mio, empresa, estado):
        conductor = ConductorFactory(usuario__empresa=empresa)
        Viaje.objects.filter(pk=mio.pk).update(
            estado=estado, conductor=conductor, vehiculo=VehiculoFactory(empresa=empresa)
        )
        datos = con_cuenta.get(url(mio)).json()
        assert (datos["conductor"], datos["vehiculo"]) == (None, None)

    @pytest.mark.parametrize("estado", [E.ACEPTADO, E.EN_CAMINO, E.EN_ZONA, E.PASAJERO_A_BORDO, E.FINALIZADO])
    def test_desde_aceptado_muestra_conductor_vehiculo_y_patente(self, con_cuenta, mio, empresa, estado):
        conductor = ConductorFactory(usuario__empresa=empresa, usuario__nombre="Juan Rojas")
        vehiculo = VehiculoFactory(empresa=empresa, patente="KTRS42", marca_modelo="Toyota Corolla")
        Viaje.objects.filter(pk=mio.pk).update(estado=estado, conductor=conductor, vehiculo=vehiculo)
        datos = con_cuenta.get(url(mio)).json()
        assert datos["conductor"] == {"nombre": "Juan Rojas"}
        assert datos["vehiculo"] == {"marca_modelo": "Toyota Corolla", "patente": "KTRS42"}
        assert datos["cancelable"] is False

    def test_vuelo_y_pasos_sin_datos_del_personal(self, con_cuenta, mio, despachador):
        llegada = timezone.now() + timedelta(hours=3)
        Vuelo.objects.create(viaje=mio, numero="LA 845", fecha=llegada.date(), hora_programada=llegada)
        HistorialEstado.objects.create(
            viaje=mio,
            estado_anterior=E.SOLICITADO,
            estado_nuevo=E.ASIGNADO,
            actor="DESPACHADOR",
            usuario=despachador,
        )
        datos = con_cuenta.get(url(mio)).json()
        assert datos["vuelo"]["numero"] == "LA 845"
        assert datos["vuelo"]["estado_vuelo"]
        assert datos["pasos"][-1]["estado"] == "ASIGNADO"
        assert all(set(paso) == {"estado", "creado_en"} for paso in datos["pasos"])
        assert despachador.nombre not in str(datos)

    def test_otros_roles_no_entran(self, cliente, despachador, mio):
        cliente.force_authenticate(despachador)
        assert cliente.get(url(mio)).status_code == 403


@pytest.mark.django_db
class TestCancelarConMotivo:
    """HU-44: cancelar desde la cuenta solo sin conductor (RN-09), con un motivo opcional."""

    def test_con_motivo_queda_en_el_viaje(self, con_cuenta, mio):
        ruta = reverse("mi-cuenta-cancelar", args=[mio.pk])
        respuesta = con_cuenta.post(ruta, {"motivo": "VUELO_CANCELADO"}, format="json")
        assert respuesta.status_code == 200
        assert respuesta.json()["sentido"] == mio.sentido
        mio.refresh_from_db()
        assert mio.estado == E.CANCELADO
        assert mio.motivo_cancelacion == "Cancelada por el pasajero desde su cuenta: Mi vuelo se canceló."

    def test_sin_motivo_sigue_funcionando(self, con_cuenta, mio):
        assert con_cuenta.post(reverse("mi-cuenta-cancelar", args=[mio.pk])).status_code == 200
        mio.refresh_from_db()
        assert mio.motivo_cancelacion == "Cancelada por el pasajero desde su cuenta."

    def test_motivo_desconocido(self, con_cuenta, mio):
        ruta = reverse("mi-cuenta-cancelar", args=[mio.pk])
        assert con_cuenta.post(ruta, {"motivo": "OTRA_COSA"}, format="json").status_code == 400

    def test_con_conductor_no_se_cancela(self, con_cuenta, mio):
        Viaje.objects.filter(pk=mio.pk).update(estado=E.EN_CAMINO)
        respuesta = con_cuenta.post(
            reverse("mi-cuenta-cancelar", args=[mio.pk]), {"motivo": "OTRO"}, format="json"
        )
        assert respuesta.status_code == 409
