"""Autenticación JWT de la API con el bloqueo de cambio de contraseña pendiente (DC-14)."""

from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication


class CambioPasswordRequerido(PermissionDenied):
    default_detail = "Debes cambiar tu contraseña temporal antes de continuar."
    default_code = "cambio_password_requerido"


class AutenticacionJWT(JWTAuthentication):
    """Igual que la de simplejwt, pero si el usuario tiene una contraseña temporal sin cambiar, responde 403
    `cambio_password_requerido` en toda vista que no declare `permite_cambio_pendiente = True` (cambiar la
    contraseña y `yo`). El login, el refresh y el logout no usan esta autenticación, así que siguen
    disponibles."""

    def authenticate(self, request):
        resultado = super().authenticate(request)
        if resultado is not None and resultado[0].debe_cambiar_password:
            vista = (getattr(request, "parser_context", None) or {}).get("view")
            if not getattr(vista, "permite_cambio_pendiente", False):
                raise CambioPasswordRequerido()
        return resultado
