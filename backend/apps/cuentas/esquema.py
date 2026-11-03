"""Extensión de drf-spectacular para la autenticación propia (se registra en CuentasConfig.ready()).

Aparte de jwt.py para que el módulo de autenticación no dependa de la herramienta de documentación.
"""

from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme


class EsquemaAutenticacionJWT(SimpleJWTScheme):
    """La misma definición (jwtAuth, Bearer) que la autenticación de simplejwt."""

    target_class = "apps.cuentas.jwt.AutenticacionJWT"
