"""HU-61 (CC-19): /ws/chat/. Autenticación por subprotocolo y eventos en vivo para cada destinatario."""

import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.urls import reverse
from rest_framework.test import APIClient

from apps.cuentas.tests.fabricas import UsuarioFactory
from apps.flota.tests.test_mapa_ws import access
from apps.reservas.tests.fabricas import ConductorFactory
from config.asgi import application

pytestmark = pytest.mark.django_db(transaction=True)


def comunicador(token=None):
    return WebsocketCommunicator(application, "/ws/chat/", subprotocols=["flotaagil", token] if token else [])


@database_sync_to_async
def escribir_como(usuario, texto):
    cliente = APIClient()
    cliente.force_authenticate(usuario)
    central = cliente.get(reverse("chat-conversaciones")).data[0]["id"]
    respuesta = cliente.post(reverse("chat-mensajes", args=[central]), {"texto": texto}, format="json")
    assert respuesta.status_code == 201
    return central, respuesta.data["id"]


@database_sync_to_async
def marcar(usuario, central, hasta):
    cliente = APIClient()
    cliente.force_authenticate(usuario)
    assert cliente.post(reverse("chat-leido", args=[central]), {"hasta": hasta}).status_code == 204


def test_sin_sesion_y_rol_sin_chat(empresa):
    pasajero = UsuarioFactory(empresa=empresa, rol="PASAJERO")

    async def escenario():
        for token, codigo in ((None, 4401), ("no-es-un-token", 4401), (access(pasajero), 4403)):
            ws = comunicador(token)
            conectado, cierre = await ws.connect()
            assert (conectado, cierre) == (False, codigo)

    async_to_sync(escenario)()


def test_mensaje_y_leido_en_vivo(empresa, despachador):
    chofer = ConductorFactory(usuario__empresa=empresa, usuario__nombre="Pedro Soto")

    async def escenario():
        del_conductor = comunicador(access(chofer.usuario))
        del_equipo = comunicador(access(despachador))
        assert (await del_conductor.connect())[0] and (await del_equipo.connect())[0]
        assert await del_conductor.receive_json_from() == {"tipo": "inicial"}
        assert await del_equipo.receive_json_from() == {"tipo": "inicial"}
        central, mensaje = await escribir_como(despachador, "Te espera el pasajero")
        recibido = await del_conductor.receive_json_from()
        assert recibido["tipo"] == "mensaje"
        assert (recibido["mensaje"]["autor"], recibido["mensaje"]["propio"]) == ("Central", False)
        propio = await del_equipo.receive_json_from()
        assert (propio["mensaje"]["autor"], propio["mensaje"]["propio"]) == (despachador.nombre, True)
        await marcar(chofer.usuario, central, mensaje)
        assert await del_equipo.receive_json_from() == {"tipo": "leido", "conversacion": central}
        await del_conductor.send_json_to({"tipo": "ping"})
        assert await del_conductor.receive_json_from() == {"tipo": "pong"}
        await del_conductor.disconnect()
        await del_equipo.disconnect()

    async_to_sync(escenario)()


def test_access_vencido_cierra(empresa, despachador):
    from datetime import timedelta

    chofer = ConductorFactory(usuario__empresa=empresa)

    async def escenario():
        ws = comunicador(access(chofer.usuario, vence_en=timedelta(seconds=1)))
        assert (await ws.connect())[0]
        await ws.receive_json_from()
        import asyncio

        await asyncio.sleep(1.2)
        await escribir_como(despachador, "Hola")
        assert (await ws.receive_output())["type"] == "websocket.close"

    async_to_sync(escenario)()
