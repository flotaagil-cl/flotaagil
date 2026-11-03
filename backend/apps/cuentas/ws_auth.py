"""Autenticación de los WebSocket con el access JWT.

El navegador no puede poner encabezados en un WebSocket, y el token en la URL quedaría en los logs. Por eso el
cliente lo manda como subprotocolo: `new WebSocket(url, ["flotaagil", access])`, y el servidor acepta con el
subprotocolo «flotaagil». Mismas reglas que la API: cuenta activa, empresa activa y sin cambio de contraseña
pendiente (DC-14). `scope["token_exp"]` permite cerrar la conexión cuando el access vence.
"""

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken

from .models import Usuario

SUBPROTOCOLO = "flotaagil"


@database_sync_to_async
def _usuario(id_usuario):
    usuario = Usuario.objects.select_related("empresa").filter(pk=id_usuario).first()
    if usuario is None or not usuario.activo or not usuario.empresa.activa or usuario.debe_cambiar_password:
        return None
    return usuario


class JwtSubprotocoloMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope = dict(scope, user=AnonymousUser(), token_exp=None)
        subprotocolos = scope.get("subprotocols") or []
        if len(subprotocolos) >= 2 and subprotocolos[0] == SUBPROTOCOLO:
            try:
                token = AccessToken(subprotocolos[1])
            except TokenError:
                token = None
            if token is not None:
                usuario = await _usuario(token.get(api_settings.USER_ID_CLAIM))
                if usuario is not None:
                    scope["user"], scope["token_exp"] = usuario, int(token["exp"])
        return await self.app(scope, receive, send)
