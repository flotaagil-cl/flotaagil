"""ASGI: HTTP (Django) y WebSocket (Channels, HU-02).

Los WebSocket exigen un Origin de PANEL_ORIGENES (contra el secuestro entre sitios) y el access JWT como
subprotocolo (apps/cuentas/ws_auth.py).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
aplicacion_http = get_asgi_application()

# Después de cargar Django: estos módulos usan los modelos.
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import OriginValidator  # noqa: E402
from django.conf import settings  # noqa: E402

from apps.cuentas.ws_auth import JwtSubprotocoloMiddleware  # noqa: E402
from apps.flota.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": aplicacion_http,
        "websocket": OriginValidator(
            JwtSubprotocoloMiddleware(URLRouter(websocket_urlpatterns)), settings.PANEL_ORIGENES
        ),
    }
)
