"""Rutas WebSocket.

El mapa del panel exige el Origin del panel (el navegador manda cookies a su origen); la app del conductor
solo usa el access como subprotocolo, sin cookies, y su WebView tiene otro origen.
"""

from channels.security.websocket import OriginValidator
from django.conf import settings
from django.urls import path

from .consumers import ConductorConsumer, MapaConsumer

websocket_urlpatterns = [
    path("ws/mapa/", OriginValidator(MapaConsumer.as_asgi(), settings.PANEL_ORIGENES)),
    path("ws/conductor/", ConductorConsumer.as_asgi()),
]
