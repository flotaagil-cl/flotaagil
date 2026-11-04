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


class ConductorConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket de la app del conductor (HU-14): /ws/conductor/. Recibe los viajes asignados; al conectarse
    (o reconectarse) recibe el que esté esperando su respuesta, para no perderlo si la app estuvo sin red."""

    grupo = None

    async def connect(self):
        from apps.reservas.asignacion import grupo_conductor

        usuario = self.scope.get("user")
        if not getattr(usuario, "is_authenticated", False):
            await self.close(code=SIN_SESION)
            return
        conductor = await _conductor_de(usuario)
        if conductor is None:
            await self.close(code=SIN_PERMISO)
            return
        self.grupo = grupo_conductor(conductor.pk)
        await self.channel_layer.group_add(self.grupo, self.channel_name)
        await self.accept(subprotocol=SUBPROTOCOLO)
        pendiente = await _pendiente(conductor)
        if pendiente is not None:
            await self.send_json({"tipo": "asignado", "asignacion": pendiente})

    async def disconnect(self, code):
        if self.grupo:
            await self.channel_layer.group_discard(self.grupo, self.channel_name)

    async def _vigente(self) -> bool:
        if (self.scope.get("token_exp") or 0) <= time.time():
            await self.close(code=SIN_SESION)
            return False
        return True

    async def conductor_asignado(self, evento):
        if await self._vigente():
            await self.send_json({"tipo": "asignado", "asignacion": evento["asignacion"]})

    async def conductor_viaje(self, evento):
        """El viaje cambió sin que lo pidiera la app (EN_ZONA automático, cancelación): vuelve a leerlo."""
        if await self._vigente():
            await self.send_json({"tipo": "viaje", "viaje": evento["viaje"]})

    async def conductor_fila(self, evento):
        """Cambió la fila del aeropuerto: la app vuelve a leer su lugar (HU-29)."""
        if await self._vigente():
            await self.send_json({"tipo": "fila"})

    async def conductor_sin_asignacion(self, evento):
        """La asignación terminó (expiró, se canceló o se reasignó): la app cierra el aviso (HU-15)."""
        if await self._vigente():
            await self.send_json({"tipo": "sin_asignacion", "asignacion": evento["asignacion"]})

    async def receive_json(self, content, **kwargs):
        if content.get("tipo") == "ping" and await self._vigente():
            await self.send_json({"tipo": "pong"})


@database_sync_to_async
def _conductor_de(usuario):
    from .models import Conductor

    if usuario.rol != "CONDUCTOR":
        return None
    return Conductor.objects.filter(usuario=usuario).first()


@database_sync_to_async
def _pendiente(conductor):
    from apps.reservas.asignacion import asignacion_pendiente, datos_para_la_app

    asignacion = asignacion_pendiente(conductor)
    return datos_para_la_app(asignacion) if asignacion else None
