"""HU-14 · Asignar un viaje y avisar al conductor (RN-01, RN-02, RN-03, RN-13)."""

from datetime import timedelta

import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.gis.geos import Point
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.aeropuerto.models import Vuelo
from apps.flota.models import ConductorVehiculo, EstadoConductor, PosicionGps
from apps.reservas.models import Actor, Asignacion, EstadoViaje, HistorialEstado, OrigenSugerencia, Sentido
from apps.reservas.tests.fabricas import ConductorFactory, VehiculoFactory, ViajeFactory
from config.asgi import application


def disponible(empresa, nombre="Pedro Soto", lat=None, **cambios):
    vehiculo = VehiculoFactory(empresa=empresa)
    conductor = ConductorFactory(
        usuario__empresa=empresa,
        usuario__nombre=nombre,
        estado=EstadoConductor.DISPONIBLE,
        vehiculo_activo=vehiculo,
        consentimiento_gps_en=timezone.now(),
        **cambios,
    )
    ConductorVehiculo.objects.create(conductor=conductor, vehiculo=vehiculo)
    if lat is not None:
        PosicionGps.objects.create(
            conductor=conductor,
            punto=Point(-70.66, lat, srid=4326),
            precision_m=5,
            registrada_en=timezone.now(),
        )
    return conductor


def asignar_url(viaje):
    return reverse("viaje-asignar", args=[viaje.pk])


@pytest.fixture
def api(cliente, despachador):
    cliente.force_authenticate(despachador)
    return cliente


@pytest.fixture
def solicitado(empresa):
    return ViajeFactory(empresa=empresa, estado=EstadoViaje.SOLICITADO, tarifa=18000)


@pytest.mark.django_db
class TestAsignar:
    def test_asigna_con_su_vehiculo_y_registra(self, api, despachador, empresa, solicitado):
        conductor = disponible(empresa)
        respuesta = api.post(asignar_url(solicitado), {"conductor": conductor.pk}, format="json")
        assert respuesta.status_code == 200, respuesta.json()
        assert respuesta.json()["estado"] == "ASIGNADO"
        assert respuesta.json()["conductor"]["id"] == conductor.pk
        assert respuesta.json()["vehiculo"]["patente"] == conductor.vehiculo_activo.patente
        asignacion = Asignacion.objects.get(viaje=solicitado)
        assert (
            asignacion.conductor,
            asignacion.despachador,
            asignacion.origen_sugerencia,
            asignacion.resultado,
        ) == (
            conductor,
            despachador,
            OrigenSugerencia.MANUAL,
            None,
        )
        cambio = HistorialEstado.objects.get(viaje=solicitado, estado_nuevo=EstadoViaje.ASIGNADO)
        assert (cambio.actor, cambio.usuario) == (Actor.DESPACHADOR, despachador)

    @pytest.mark.parametrize(
        ("cambios", "texto"),
        [
            (
                {"estado": EstadoConductor.NO_DISPONIBLE, "vehiculo_activo": None},
                "no está Disponible (RN-01)",
            ),
            ({"estado": EstadoConductor.EN_VIAJE}, "no está Disponible (RN-01)"),
        ],
    )
    def test_solo_disponibles(self, api, empresa, solicitado, cambios, texto):
        conductor = disponible(empresa)
        for campo, valor in cambios.items():
            setattr(conductor, campo, valor)
        conductor.save()
        respuesta = api.post(asignar_url(solicitado), {"conductor": conductor.pk}, format="json")
        assert respuesta.status_code == 409
        assert texto in respuesta.json()["detail"]

    def test_un_viaje_en_ejecucion_a_la_vez(self, api, empresa, solicitado):
        """RN-03."""
        conductor = disponible(empresa)
        ViajeFactory(empresa=empresa, conductor=conductor, estado=EstadoViaje.ACEPTADO)
        respuesta = api.post(asignar_url(solicitado), {"conductor": conductor.pk}, format="json")
        assert (respuesta.status_code, respuesta.json()["code"]) == (409, "asignacion_no_permitida")
        assert "RN-03" in respuesta.json()["detail"]

    @pytest.mark.parametrize("estado", [EstadoViaje.PENDIENTE_CONFIRMACION, EstadoViaje.ASIGNADO])
    def test_solo_reservas_solicitadas(self, api, empresa, estado):
        viaje = ViajeFactory(empresa=empresa, estado=estado)
        conductor = disponible(empresa)
        assert api.post(asignar_url(viaje), {"conductor": conductor.pk}, format="json").status_code == 409

    def test_conductor_de_otra_empresa(self, api, otra_empresa, solicitado):
        ajeno = disponible(otra_empresa)
        respuesta = api.post(asignar_url(solicitado), {"conductor": ajeno.pk}, format="json")
        assert respuesta.status_code == 400
        assert "conductor" in respuesta.json()

    def test_reserva_de_otra_empresa_404(self, api, otra_empresa, empresa):
        viaje = ViajeFactory(empresa=otra_empresa, estado=EstadoViaje.SOLICITADO)
        assert (
            api.post(asignar_url(viaje), {"conductor": disponible(empresa).pk}, format="json").status_code
            == 404
        )

    def test_el_conductor_no_puede_asignar(self, cliente, conductor, solicitado):
        cliente.force_authenticate(conductor)
        assert cliente.post(asignar_url(solicitado), {"conductor": 1}, format="json").status_code == 403


@pytest.mark.django_db
class TestCandidatos:
    def test_disponibles_sin_viaje_los_mas_cercanos_primero(self, api, empresa, solicitado):
        # El origen de la fábrica es el centro de Santiago (-33.4489).
        lejos = disponible(empresa, "Lejos", lat=-33.60)
        cerca = disponible(empresa, "Cerca", lat=-33.45)
        sin_posicion = disponible(empresa, "Sin posición")
        ocupado = disponible(empresa, "Ocupado", lat=-33.4489)
        ViajeFactory(empresa=empresa, conductor=ocupado, estado=EstadoViaje.EN_CAMINO)
        disponible(empresa, "No disponible").__class__.objects.filter(usuario__nombre="No disponible").update(
            estado=EstadoConductor.NO_DISPONIBLE, vehiculo_activo=None
        )
        filas = api.get(reverse("viaje-candidatos", args=[solicitado.pk])).json()
        assert [f["nombre"] for f in filas] == ["Cerca", "Lejos", "Sin posición"]
        assert filas[0]["distancia_m"] < 1000 < filas[1]["distancia_m"]
        assert filas[2]["distancia_m"] is None
        assert {cerca.pk, lejos.pk, sin_posicion.pk} == {f["id"] for f in filas}


def access(usuario):
    return str(AccessToken.for_user(usuario))


@pytest.mark.django_db(transaction=True)
class TestAvisoAlConductor:
    def test_recibe_el_viaje_con_vuelo_y_al_reconectar_lo_vuelve_a_recibir(self, empresa, despachador):
        conductor = disponible(empresa)
        viaje = ViajeFactory(
            empresa=empresa, estado=EstadoViaje.SOLICITADO, tarifa=25000, sentido=Sentido.DESDE_AEROPUERTO
        )
        llegada = timezone.now() + timedelta(hours=1)
        Vuelo.objects.create(
            viaje=viaje,
            numero="LA 845",
            fecha=llegada.date(),
            hora_programada=llegada,
            hora_estimada=llegada + timedelta(minutes=20),
        )
        token = access(conductor.usuario)

        @database_sync_to_async
        def asignar():
            cliente = APIClient()
            cliente.force_authenticate(despachador)
            return cliente.post(asignar_url(viaje), {"conductor": conductor.pk}, format="json").status_code

        async def prueba():
            com = WebsocketCommunicator(application, "/ws/conductor/", subprotocols=["flotaagil", token])
            conectado = await com.connect()
            assert await com.receive_nothing(timeout=0.2)
            assert await asignar() == 200
            aviso = await com.receive_json_from(timeout=2)
            await com.disconnect()
            otra = WebsocketCommunicator(application, "/ws/conductor/", subprotocols=["flotaagil", token])
            await otra.connect()
            de_nuevo = await otra.receive_json_from(timeout=2)
            await otra.disconnect()
            return conectado, aviso, de_nuevo

        conectado, aviso, de_nuevo = async_to_sync(prueba)()
        assert conectado == (True, "flotaagil")
        datos = aviso["asignacion"]
        assert aviso["tipo"] == "asignado"
        assert (datos["viaje"], datos["tarifa"], datos["vuelo"]["numero"]) == (viaje.pk, 25000, "LA 845")
        assert datos["vuelo"]["hora_estimada"] is not None
        assert {"origen", "destino", "pasajero", "recogida_en", "vence_en"} <= set(datos)
        assert de_nuevo == aviso  # reconexión: no se pierde

    def test_solo_conductores(self, despachador):
        token = access(despachador)

        async def prueba():
            com = WebsocketCommunicator(application, "/ws/conductor/", subprotocols=["flotaagil", token])
            return await com.connect()

        assert async_to_sync(prueba)() == (False, 4403)

    def test_sin_token(self):
        async def prueba():
            return await WebsocketCommunicator(application, "/ws/conductor/").connect()

        assert async_to_sync(prueba)() == (False, 4401)
