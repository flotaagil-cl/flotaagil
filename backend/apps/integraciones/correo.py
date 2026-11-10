"""HU-33: adaptador de correo (recuperar contraseña, aprobación de convenios).

Se elige con `CORREO_PROVEEDOR` (DC-34):
- `consola` (por defecto): el backend de consola de Django. El correo queda en el log del worker.
- `ses`: Amazon SES por su interfaz SMTP (`email-smtp.<región>.amazonaws.com`, puerto 587, STARTTLS), con el
  backend SMTP de Django: no agrega dependencias. Requiere `SES_SMTP_USUARIO` y `SES_SMTP_CLAVE` (credenciales
  SMTP de SES, distintas de las de IAM) y un remitente verificado en `CORREO_REMITENTE`. Sin credenciales.

El envío corre en el worker (`apps.cuentas.tareas.enviar_correo`), con reintento exponencial.
"""

import smtplib

from django.conf import settings
from django.core.mail import send_mail


class CorreoTransitorio(Exception):
    """Falla que puede resolverse reintentando (red, SMTP 4xx)."""


def enviar(destino: str, asunto: str, texto: str) -> None:
    try:
        send_mail(asunto, texto, settings.DEFAULT_FROM_EMAIL, [destino], fail_silently=False)
    except (TimeoutError, smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, ConnectionError) as error:
        raise CorreoTransitorio(str(error)) from error
    except smtplib.SMTPResponseException as error:
        if 400 <= error.smtp_code < 500:
            raise CorreoTransitorio(str(error)) from error
        raise


def enmascarar(correo: str) -> str:
    """ana.perez@ejemplo.cl → a***@ejemplo.cl, para el log."""
    usuario, _, dominio = correo.partition("@")
    return f"{usuario[:1]}***@{dominio}"
