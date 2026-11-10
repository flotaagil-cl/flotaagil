"""Autenticación JWT.

- Panel web (administrador, despachador): el access va en la respuesta y el refresh en una cookie
  httpOnly (SameSite=Lax, Secure en producción) limitada a /api/auth/. Login, refresh y logout exigen
  un Origin (o Referer) de PANEL_ORIGENES y solo aceptan JSON. La sesión dura a lo más JWT_SESION_MAX
  desde el login.
- App del conductor: access y refresh en la respuesta; la app los guarda en el almacenamiento seguro
  del teléfono y envía Authorization: Bearer. Sin revisión de origen ni tope absoluto.

Un refresh rechazado responde 401 sin tocar la cookie: solo el logout la borra. Así una respuesta tardía
de otra pestaña nunca borra una cookie que ya se renovó.

Los errores de estas vistas llevan `code` además de `detail` (p. ej. `cuenta_bloqueada`), para que el cliente
no dependa del texto.
"""

import contextlib

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.comun.excepciones import error_con_codigo

from . import credenciales
from .autenticacion import (
    CANAL_APP,
    CANAL_PANEL,
    ROLES_APP,
    ROLES_WEB,
    SesionRechazada,
    autenticar,
    emitir_tokens,
    renovar,
    vida_cookie,
)
from .credenciales import cambiar_password
from .origen import OrigenPanelPermitido
from .serializers import (
    AccessSerializer,
    CambiarPasswordSerializer,
    ErrorSerializer,
    LoginSerializer,
    RefreshSerializer,
    SesionAppSerializer,
    SesionPanelSerializer,
    TokensSerializer,
    UsuarioSesionSerializer,
)

MENSAJES_SESION = {
    "sesion_invalida": "La sesión no es válida o expiró.",
    "sesion_expirada": "La sesión alcanzó su duración máxima. Inicia sesión de nuevo.",
}


def _sin_sesion(codigo: str) -> Response:
    return Response({"detail": MENSAJES_SESION[codigo], "code": codigo}, status=status.HTTP_401_UNAUTHORIZED)


def _poner_cookie(respuesta: Response, refresh: str, max_age: int) -> None:
    cookie = settings.JWT_COOKIE
    respuesta.set_cookie(
        cookie["nombre"],
        refresh,
        max_age=max_age,
        httponly=True,
        secure=cookie["secure"],
        samesite=cookie["samesite"],
        path=cookie["ruta"],
    )


def _borrar_cookie(respuesta: Response) -> None:
    cookie = settings.JWT_COOKIE
    respuesta.delete_cookie(cookie["nombre"], path=cookie["ruta"], samesite=cookie["samesite"])


# --- Documentación OpenAPI de las respuestas de error ---


def _error(descripcion: str) -> OpenApiResponse:
    return OpenApiResponse(ErrorSerializer, description=descripcion)


ERROR_ORIGEN = _error(
    "`origen_no_permitido`: falta el encabezado Origin (y el Referer) o no está en PANEL_ORIGENES."
)
ERROR_VALIDACION = OpenApiResponse(description="Datos inválidos: errores por campo.")
ERROR_THROTTLE = _error("`throttled`: demasiados intentos desde esta IP (THROTTLE_LOGIN).")
ERROR_JSON = _error("`unsupported_media_type`: el cuerpo debe ser application/json.")
COOKIE_PUESTA = OpenApiParameter(
    "Set-Cookie",
    str,
    OpenApiParameter.HEADER,
    response=[200],
    description="`refresh_panel=<refresh>; HttpOnly; SameSite=Lax; Path=/api/auth/; Max-Age=<segundos>` "
    "(Secure en producción). Max-Age no supera lo que le queda a la sesión.",
)
COOKIE_BORRADA = OpenApiParameter(
    "Set-Cookie",
    str,
    OpenApiParameter.HEADER,
    response=[204],
    description="Borra `refresh_panel` (Max-Age=0, Path=/api/auth/).",
)
NOTA_ORIGEN = (
    " Exige que el navegador envíe Origin (o, si falta, Referer) con un origen de PANEL_ORIGENES; "
    "el navegador lo pone solo."
)


class _VistaAuth(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get_exception_handler(self):
        return error_con_codigo

    def get_authenticate_header(self, request):
        # Sin autenticadores DRF respondería 403 a las credenciales inválidas; deben ser 401.
        return 'Bearer realm="api"'


class _VistaPanel(_VistaAuth):
    """Login, refresh y logout del panel: origen permitido (anti-CSRF) y solo JSON."""

    permission_classes = [OrigenPanelPermitido]
    parser_classes = [JSONParser]


class _ThrottleLogin:
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class LoginPanelView(_ThrottleLogin, _VistaPanel):
    @extend_schema(
        tags=["auth"],
        summary="Iniciar sesión en la web (panel, convenio o pasajero)",
        request=LoginSerializer,
        parameters=[COOKIE_PUESTA],
        responses={
            200: SesionPanelSerializer,
            400: ERROR_VALIDACION,
            401: _error("`credenciales_invalidas`, `cuenta_bloqueada` o `cuenta_deshabilitada`."),
            403: _error("`rol_no_permitido` (el conductor usa la app) u `origen_no_permitido`."),
            415: ERROR_JSON,
            429: ERROR_THROTTLE,
        },
        description="Deja el refresh en la cookie httpOnly «refresh_panel» y emite la sesión con su tope "
        "absoluto (JWT_SESION_MAX desde este login)." + NOTA_ORIGEN,
    )
    def post(self, request):
        datos = LoginSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        usuario = autenticar(datos.validated_data["email"], datos.validated_data["password"], ROLES_WEB)
        refresh = emitir_tokens(usuario, CANAL_PANEL)
        respuesta = Response(
            {"access": str(refresh.access_token), "usuario": UsuarioSesionSerializer(usuario).data}
        )
        _poner_cookie(respuesta, str(refresh), vida_cookie(refresh))
        return respuesta


class RefreshPanelView(_VistaPanel):
    @extend_schema(
        tags=["auth"],
        summary="Renovar el access del panel con la cookie de refresh",
        request=None,
        parameters=[COOKIE_PUESTA],
        responses={
            200: AccessSerializer,
            401: _error(
                "`sesion_invalida` o `sesion_expirada`. No trae Set-Cookie: la cookie no se toca. "
                "El cliente debe tratar ambos códigos igual (volver al login)."
            ),
            403: ERROR_ORIGEN,
        },
        description="Rota el refresh (el anterior queda en la lista negra). Los tokens nuevos no superan el "
        "tope de la sesión." + NOTA_ORIGEN,
    )
    def post(self, request):
        try:
            renovacion = renovar(request.COOKIES.get(settings.JWT_COOKIE["nombre"], ""), CANAL_PANEL)
        except SesionRechazada as rechazo:
            return _sin_sesion(rechazo.codigo)
        respuesta = Response({"access": renovacion.access})
        _poner_cookie(respuesta, renovacion.refresh, renovacion.max_age)
        return respuesta


class LogoutPanelView(_VistaPanel):
    @extend_schema(
        tags=["auth"],
        summary="Cerrar sesión del panel",
        request=None,
        parameters=[COOKIE_BORRADA],
        responses={204: None, 403: ERROR_ORIGEN},
        description="Deja el refresh de la cookie en la lista negra y borra la cookie. "
        "Responde 204 aunque no haya sesión." + NOTA_ORIGEN,
    )
    def post(self, request):
        refresh = request.COOKIES.get(settings.JWT_COOKIE["nombre"])
        if refresh:
            with contextlib.suppress(TokenError):
                RefreshToken(refresh).blacklist()
        respuesta = Response(status=status.HTTP_204_NO_CONTENT)
        _borrar_cookie(respuesta)
        return respuesta


class LoginAppView(_ThrottleLogin, _VistaAuth):
    @extend_schema(
        tags=["auth"],
        summary="Iniciar sesión en la app del conductor",
        request=LoginSerializer,
        responses={
            200: SesionAppSerializer,
            400: ERROR_VALIDACION,
            401: _error("`credenciales_invalidas`, `cuenta_bloqueada` o `cuenta_deshabilitada`."),
            403: _error("`rol_no_permitido` (solo conductores)."),
            429: ERROR_THROTTLE,
        },
    )
    def post(self, request):
        datos = LoginSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        usuario = autenticar(datos.validated_data["email"], datos.validated_data["password"], ROLES_APP)
        refresh = emitir_tokens(usuario, CANAL_APP)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "usuario": UsuarioSesionSerializer(usuario).data,
            }
        )


class RefreshAppView(_VistaAuth):
    @extend_schema(
        tags=["auth"],
        summary="Renovar los tokens de la app del conductor",
        request=RefreshSerializer,
        responses={
            200: TokensSerializer,
            400: ERROR_VALIDACION,
            401: _error(
                "`sesion_invalida`: el refresh no sirve (vencido, usado, de otro canal o usuario "
                "deshabilitado)."
            ),
        },
        description="Rota el refresh: el anterior queda en la lista negra.",
    )
    def post(self, request):
        datos = RefreshSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        try:
            renovacion = renovar(datos.validated_data["refresh"], CANAL_APP)
        except SesionRechazada as rechazo:
            return _sin_sesion(rechazo.codigo)
        return Response({"access": renovacion.access, "refresh": renovacion.refresh})


class YoView(APIView):
    # Con la temporal pendiente la app la consulta para saber que debe pedir el cambio (DC-14).
    permite_cambio_pendiente = True

    @extend_schema(
        tags=["auth"],
        summary="Usuario de la sesión actual",
        responses={
            200: UsuarioSesionSerializer,
            401: OpenApiResponse(description="Falta el access o no es válido (`token_not_valid`)."),
        },
    )
    def get(self, request):
        return Response(UsuarioSesionSerializer(request.user).data)


class LogoutAppView(_VistaAuth):
    @extend_schema(
        tags=["auth"],
        summary="Cerrar sesión en la app del conductor",
        request=RefreshSerializer,
        responses={204: None},
        description="Deja el refresh en la lista negra. Responde 204 aunque el refresh no sirva (vencido, ya "
        "usado o de otro canal): para la app la sesión queda cerrada igual.",
    )
    def post(self, request):
        datos = RefreshSerializer(data=request.data)
        if datos.is_valid():
            with contextlib.suppress(TokenError):
                token = RefreshToken(datos.validated_data["refresh"])
                if token.get("canal") == CANAL_APP:
                    token.blacklist()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CambiarPasswordView(APIView):
    """Disponible aunque el usuario tenga una contraseña temporal pendiente (DC-14)."""

    permite_cambio_pendiente = True
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(
        tags=["auth"],
        summary="Cambiar la propia contraseña",
        request=CambiarPasswordSerializer,
        responses={
            200: OpenApiResponse(
                TokensSerializer,
                description="App: tokens nuevos. Panel: solo `access` y el refresh en la cookie.",
            ),
            400: ERROR_VALIDACION,
            401: OpenApiResponse(description="Falta el access o no es válido."),
            429: ERROR_THROTTLE,
        },
        description="Exige la contraseña actual. Cierra todas las sesiones del usuario (panel y app) y "
        "entrega "
        "una nueva en el mismo canal del access usado. Quita la obligación de cambiar la temporal.",
    )
    def post(self, request):
        datos = CambiarPasswordSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        cambiar_password(
            request.user,
            actual=datos.validated_data["password_actual"],
            nueva=datos.validated_data["password_nueva"],
        )
        request.user.refresh_from_db()
        canal = request.auth.get("canal") if request.auth is not None else None
        refresh = emitir_tokens(request.user, CANAL_PANEL if canal == CANAL_PANEL else CANAL_APP)
        if canal == CANAL_PANEL:
            respuesta = Response({"access": str(refresh.access_token)})
            _poner_cookie(respuesta, str(refresh), vida_cookie(refresh))
            return respuesta
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


class RecuperarSerializer(serializers.Serializer):
    email = serializers.EmailField()


class RecuperarView(_ThrottleLogin, _VistaAuth):
    @extend_schema(
        tags=["auth"],
        summary="Pedir el enlace para recuperar la contraseña (pasajero o convenio)",
        request=RecuperarSerializer,
        responses={202: None, 429: ERROR_THROTTLE},
        description="HU-35: responde 202 siempre, exista o no la cuenta. El enlace vence y sirve una vez.",
    )
    def post(self, request):
        entrada = RecuperarSerializer(data=request.data)
        if entrada.is_valid():
            credenciales.pedir_recuperacion(entrada.validated_data["email"])
        return Response(status=status.HTTP_202_ACCEPTED)


class RecuperarConfirmarView(_ThrottleLogin, _VistaAuth):
    @extend_schema(
        tags=["auth"],
        summary="Elegir la contraseña nueva con el enlace del correo",
        request=inline_serializer(
            "RecuperarConfirmar",
            {
                "uid": serializers.CharField(),
                "token": serializers.CharField(),
                "password": serializers.CharField(),
            },
        ),
        responses={204: None, 400: ERROR_VALIDACION, 429: ERROR_THROTTLE},
        description="Cierra todas las sesiones y levanta el bloqueo por intentos. Queda en auditoría.",
    )
    def post(self, request):
        uid, token, password = (str(request.data.get(c, "")) for c in ("uid", "token", "password"))
        credenciales.confirmar_recuperacion(uid, token, password)
        return Response(status=status.HTTP_204_NO_CONTENT)
