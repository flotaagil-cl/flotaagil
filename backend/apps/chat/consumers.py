"""WebSocket del chat (CC-19): /ws/chat/. Cada usuario recibe en su grupo los eventos de sus conversaciones.

Eventos: `mensaje` (ya armado para quien lo recibe), `leido` y `conversaciones` (volver a pedir la lista).
Lo usan el panel y la app; el access va como subprotocolo, sin cookies, así que no se exige Origin.
"""

import time

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.cuentas.ws_auth import SUBPROTOCOLO
from apps.flota.consumers import SIN_PERMISO, SIN_SESION

from .permisos import ROLES_PERSONAL
from .servicios import grupo_usuario


class ChatConsumer(AsyncJsonWebsocketConsumer):
    grupo = None

    async def connect(self):
        usuario = self.scope.get("user")
        if not getattr(usuario, "is_authenticated", False):
            await self.close(code=SIN_SESION)
            return
        if usuario.rol not in ROLES_PERSONAL:
            await self.close(code=SIN_PERMISO)
            return
        self.grupo = grupo_usuario(usuario.pk)
        await self.channel_layer.group_add(self.grupo, self.channel_name)
        await self.accept(subprotocol=SUBPROTOCOLO)
        await self.send_json({"tipo": "inicial"})  # Al reconectarse se vuelven a pedir los no leídos.

    async def disconnect(self, code):
        if self.grupo:
            await self.channel_layer.group_discard(self.grupo, self.channel_name)

    async def _vigente(self) -> bool:
        if (self.scope.get("token_exp") or 0) <= time.time():
            await self.close(code=SIN_SESION)
            return False
        return True

    async def chat_evento(self, evento):
        if await self._vigente():
            await self.send_json(evento["datos"])

    async def receive_json(self, content, **kwargs):
        if content.get("tipo") == "ping" and await self._vigente():
            await self.send_json({"tipo": "pong"})
