"""WebSocket del mapa en tiempo real (HU-02): /ws/mapa/. Solo administrador y despachador, solo su empresa."""

import time

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.cuentas.autenticacion import ROLES_PANEL
from apps.cuentas.ws_auth import SUBPROTOCOLO

from .tiempo_real import conductores_del_mapa, grupo_mapa

# Códigos de cierre propios (4000-4999): ante 4401 el cliente renueva el access y se reconecta.
SIN_SESION = 4401
SIN_PERMISO = 4403


class MapaConsumer(AsyncJsonWebsocketConsumer):
    grupo = None

    async def connect(self):
        usuario = self.scope.get("user")
        if not getattr(usuario, "is_authenticated", False):
            await self.close(code=SIN_SESION)
            return
        if usuario.rol not in ROLES_PANEL:
            await self.close(code=SIN_PERMISO)
            return
        self.grupo = grupo_mapa(usuario.empresa_id)
        await self.channel_layer.group_add(self.grupo, self.channel_name)
        await self.accept(subprotocol=SUBPROTOCOLO)
        conductores = await database_sync_to_async(conductores_del_mapa)(usuario.empresa_id)
        await self.send_json({"tipo": "inicial", "conductores": conductores})

    async def disconnect(self, code):
        if self.grupo:
            await self.channel_layer.group_discard(self.grupo, self.channel_name)

    async def _vigente(self) -> bool:
        """Con el access vencido se cierra la conexión: el cliente renueva y se reconecta."""
        if (self.scope.get("token_exp") or 0) <= time.time():
            await self.close(code=SIN_SESION)
            return False
        return True

    async def mapa_conductor(self, evento):
        if await self._vigente():
            await self.send_json({"tipo": "conductor", "conductor": evento["conductor"]})

    async def mapa_fuera(self, evento):
        if await self._vigente():
            await self.send_json({"tipo": "fuera", "id": evento["id"]})

    async def receive_json(self, content, **kwargs):
        if content.get("tipo") == "ping" and await self._vigente():
            await self.send_json({"tipo": "pong"})
