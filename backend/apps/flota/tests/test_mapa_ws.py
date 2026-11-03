"""HU-02 · Mapa en tiempo real por WebSocket (/ws/mapa/): autenticación, aislamiento y actualizaciones.

Cada prueba es un escenario asíncrono completo (un solo bucle de eventos para la conexión); lo que toca la
base o la API corre con database_sync_to_async.
"""

import asyncio
from datetime import timedelta

import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.cuentas.tests.fabricas import UsuarioFactory
from apps.flota.models import ConductorVehiculo, EstadoConductor
from apps.reservas.tests.fabricas import ConductorFactory, VehiculoFactory
from config.asgi import application

ORIGEN = (b"origin", b"http://localhost:5173")

pytestmark = pytest.mark.django_db(transaction=True)


def access(usuario, vence_en=None):
    token = AccessToken.for_user(usuario)
    if vence_en is not None:
        token.set_exp(lifetime=vence_en)
    return str(token)


def comunicador(token=None, origen=ORIGEN):
    subprotocolos = ["flotaagil", token] if token else []
    return WebsocketCommunicator(
        application, "/ws/mapa/", headers=[origen] if origen else [], subprotocols=subprotocolos
    )


def escenario(funcion):
    """Ejecuta la corrutina de la prueba en un solo bucle de eventos."""
    return async_to_sync(funcion)()


@pytest.fixture
def en_turno(empresa):
    vehiculo = VehiculoFactory(empresa=empresa, patente="BCDF10")
    conductor = ConductorFactory(
        usuario__empresa=empresa,
        usuario__nombre="Pedro Soto",
        estado=EstadoConductor.DISPONIBLE,
        vehiculo_activo=vehiculo,
        consentimiento_gps_en=timezone.now(),
    )
    ConductorVehiculo.objects.create(conductor=conductor, vehiculo=vehiculo)
    return conductor


@database_sync_to_async
def enviar_posicion(conductor, lat=-33.45):
    cliente = APIClient()
    cliente.force_authenticate(conductor.usuario)
    registrada = (timezone.now() - timedelta(seconds=1)).isoformat()
    datos = {"posiciones": [{"lat": lat, "lon": -70.66, "precision_m": 7, "registrada_en": registrada}]}
    assert cliente.post(reverse("app-posiciones"), datos, format="json").status_code == 201


@database_sync_to_async
def post_como(usuario, ruta, datos=None):
    cliente = APIClient()
    cliente.force_authenticate(usuario)
    return cliente.post(ruta, datos or {}, format="json").status_code


class TestConexion:
    def test_sin_token_cierra_4401(self):
        async def prueba():
            return await comunicador().connect()

        assert escenario(prueba) == (False, 4401)

    def test_token_invalido(self):
        async def prueba():
            return await comunicador("no-es-un-jwt").connect()

        assert escenario(prueba) == (False, 4401)

    def test_access_vencido(self, despachador):
        token = access(despachador, vence_en=timedelta(seconds=-1))

        async def prueba():
            return await comunicador(token).connect()

        assert escenario(prueba) == (False, 4401)

    def test_origen_no_permitido(self, despachador):
        token = access(despachador)

        async def prueba():
            conectado, _ = await comunicador(
                token, origen=(b"origin", b"https://malicioso.example")
            ).connect()
            return conectado

        assert escenario(prueba) is False

    def test_conductor_sin_permiso(self, conductor):
        token = access(conductor)

        async def prueba():
            return await comunicador(token).connect()

        assert escenario(prueba) == (False, 4403)

    def test_cuenta_con_cambio_pendiente(self, despachador):
        despachador.debe_cambiar_password = True
        despachador.save()
        token = access(despachador)

        async def prueba():
            return await comunicador(token).connect()

        assert escenario(prueba) == (False, 4401)

    def test_acepta_con_el_subprotocolo_y_manda_la_foto_inicial(self, despachador, en_turno, empresa):
        ConductorFactory(usuario__empresa=empresa, estado=EstadoConductor.NO_DISPONIBLE)  # fuera de turno
        token = access(despachador)

        async def prueba():
            await enviar_posicion(en_turno)
            com = comunicador(token)
            conectado = await com.connect()
            inicial = await com.receive_json_from(timeout=2)
            await com.disconnect()
            return conectado, inicial

        conectado, inicial = escenario(prueba)
        assert conectado == (True, "flotaagil")
        assert inicial["tipo"] == "inicial"
        assert [c["nombre"] for c in inicial["conductores"]] == ["Pedro Soto"]
        conductor = inicial["conductores"][0]
        assert (conductor["patente"], conductor["estado"]) == ("BCDF10", "DISPONIBLE")
        assert conductor["posicion"]["lat"] == pytest.approx(-33.45)


class TestActualizaciones:
    def test_posicion_nueva_llega_al_mapa_de_su_empresa(self, despachador, en_turno, otra_empresa):
        propio = access(despachador)
        ajeno = access(UsuarioFactory(empresa=otra_empresa, rol="DESPACHADOR"))

        async def prueba():
            com, otro = comunicador(propio), comunicador(ajeno)
            await com.connect()
            await otro.connect()
            await com.receive_json_from(timeout=2)
            await otro.receive_json_from(timeout=2)
            await enviar_posicion(en_turno, lat=-33.40)
            mensaje = await com.receive_json_from(timeout=2)
            silencio = await otro.receive_nothing(timeout=0.3)
            await com.disconnect()
            await otro.disconnect()
            return mensaje, silencio

        mensaje, silencio = escenario(prueba)
        assert mensaje["tipo"] == "conductor"
        assert mensaje["conductor"]["posicion"]["lat"] == pytest.approx(-33.40)
        assert silencio is True  # RN-13: otra empresa no lo ve

    def test_terminar_y_empezar_turno(self, administrador, en_turno):
        token = access(administrador)

        async def prueba():
            com = comunicador(token)
            await com.connect()
            await com.receive_json_from(timeout=2)
            await post_como(en_turno.usuario, reverse("app-turno"), {"estado": "NO_DISPONIBLE"})
            fuera = await com.receive_json_from(timeout=2)
            await post_como(en_turno.usuario, reverse("app-turno"), {"estado": "DISPONIBLE"})
            dentro = await com.receive_json_from(timeout=2)
            await com.disconnect()
            return fuera, dentro

        fuera, dentro = escenario(prueba)
        assert fuera == {"tipo": "fuera", "id": en_turno.pk}
        assert (dentro["tipo"], dentro["conductor"]["estado"]) == ("conductor", "DISPONIBLE")

    def test_deshabilitar_la_cuenta_lo_saca_del_mapa(self, administrador, en_turno):
        token = access(administrador)

        async def prueba():
            com = comunicador(token)
            await com.connect()
            await com.receive_json_from(timeout=2)
            await post_como(administrador, reverse("conductor-deshabilitar", args=[en_turno.pk]))
            mensaje = await com.receive_json_from(timeout=2)
            await com.disconnect()
            return mensaje

        assert escenario(prueba) == {"tipo": "fuera", "id": en_turno.pk}

    def test_cierra_si_el_access_vence_con_la_conexion_abierta(self, despachador, en_turno):
        token = access(despachador, vence_en=timedelta(seconds=2))

        async def prueba():
            com = comunicador(token)
            await com.connect()
            await com.receive_json_from(timeout=2)
            await asyncio.sleep(2.2)
            await enviar_posicion(en_turno)
            salida = await com.receive_output(timeout=2)
            await com.disconnect()
            return salida

        assert escenario(prueba) == {"type": "websocket.close", "code": 4401}

    def test_ping(self, despachador):
        token = access(despachador)

        async def prueba():
            com = comunicador(token)
            await com.connect()
            await com.receive_json_from(timeout=2)
            await com.send_json_to({"tipo": "ping"})
            respuesta = await com.receive_json_from(timeout=2)
            await com.disconnect()
            return respuesta

        assert escenario(prueba) == {"tipo": "pong"}
