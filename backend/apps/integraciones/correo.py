"""HU-33: adaptador de correo (recuperar contraseña, aprobación de convenios).

Se elige con `CORREO_PROVEEDOR` (DC-34):
- `consola` (por defecto): el backend de consola de Django. El correo queda en el log del worker.
- `ses`: Amazon SES por su interfaz SMTP (`email-smtp.<región>.amazonaws.com`, puerto 587, STARTTLS), con el
  backend SMTP de Django: no agrega dependencias. Requiere `SES_SMTP_USUARIO` y `SES_SMTP_CLAVE` (credenciales
  SMTP de SES, distintas de las de IAM) y un remitente verificado en `CORREO_REMITENTE`. Sin credenciales.

El envío corre en el worker (`apps.cuentas.tareas.enviar_correo`), con reintento exponencial.
"""

import smtplib
from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

CID_LOGO = "logo-empresa"


class CorreoTransitorio(Exception):
    """Falla que puede resolverse reintentando (red, SMTP 4xx)."""


def _componer(destino, asunto, texto, html, logo) -> EmailMultiAlternatives:
    mensaje = EmailMultiAlternatives(asunto, texto, settings.DEFAULT_FROM_EMAIL, [destino])
    if html:
        mensaje.attach_alternative(html, "text/html")
    if html and logo:
        imagen = MIMEImage(logo, "png")
        imagen.add_header("Content-ID", f"<{CID_LOGO}>")
        imagen.add_header("Content-Disposition", "inline", filename="logo.png")
        mensaje.mixed_subtype = "related"  # el HTML y su imagen van juntos
        mensaje.attach(imagen)
    return mensaje


def enviar(destino: str, asunto: str, texto: str, html: str | None = None, logo: bytes | None = None) -> None:
    """`html` y `logo` (PNG referenciado como `cid:logo-empresa`) visten el correo (CC-27)."""
    try:
        _componer(destino, asunto, texto, html, logo).send(fail_silently=False)
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
