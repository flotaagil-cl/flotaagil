"""Errores de la API con `code` estable para que el cliente distinga los casos sin leer el texto."""

from django.core.exceptions import PermissionDenied as PermisoDenegadoDjango
from django.http import Http404
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

# Excepciones de Django que DRF convierte en respuestas: su `detail` no trae código.
CODIGOS_DJANGO = ((Http404, "not_found"), (PermisoDenegadoDjango, "permission_denied"))


def error_con_codigo(exc, context):
    """Manejador de DRF que agrega `code` a los errores con solo `detail` (401, 403, 404, 405, 409, 415, 429).
    Los 400 de validación (errores por campo) quedan igual."""
    respuesta = exception_handler(exc, context)
    if respuesta is None or not isinstance(respuesta.data, dict) or set(respuesta.data) != {"detail"}:
        return respuesta
    if isinstance(exc, APIException):
        respuesta.data["code"] = getattr(respuesta.data["detail"], "code", exc.default_code)
    else:
        respuesta.data["code"] = next((c for tipo, c in CODIGOS_DJANGO if isinstance(exc, tipo)), "error")
    return respuesta
