"""CC-27 (HU-80) y CC-21: los correos llevan la marca de la empresa (logo o iniciales, colores y nombre).

El texto plano sigue siendo el contenido del correo; este HTML solo lo viste. El logo viaja dentro del correo
(adjunto con `cid:`), así se ve sin depender de una URL pública. Estilos en línea y una tabla, que es lo que
entienden los clientes de correo.
"""

import logging
import re

from django.core.files.storage import default_storage
from django.utils.html import escape

from apps.integraciones.correo import CID_LOGO

from . import logos
from .paletas import paleta_de

logger = logging.getLogger(__name__)

TEXTO = "#0f2a2e"  # --texto de tokens.css: no cambia con la paleta
_ENLACE = re.compile(r"(https?://[^\s<>\"]*[^\s<>\".,;:)])")


def leer_logo(empresa) -> bytes | None:
    """PNG de la variante «correo». Sin logo legible, el correo sale con las iniciales o FlotaÁgil."""
    if not empresa.logo:
        return None
    try:
        with default_storage.open(logos.ruta(empresa.logo, "correo"), "rb") as archivo:
            return archivo.read()
    except Exception:  # el almacenamiento (disco o S3) no puede impedir que salga el correo
        logger.warning("No se pudo leer el logo de la empresa %s para el correo.", empresa.pk, exc_info=True)
        return None


def _linea(linea: str, color: str) -> str:
    # Los trozos impares de split() son los enlaces capturados.
    return "".join(
        f'<a href="{escape(trozo)}" style="color:{color};word-break:break-all;">{escape(trozo)}</a>'
        if posicion % 2
        else escape(trozo)
        for posicion, trozo in enumerate(_ENLACE.split(linea))
    )


def _parrafos(texto: str, color: str) -> str:
    parrafos = []
    for parrafo in re.split(r"\n\s*\n", texto.strip()):
        lineas = "<br>".join(_linea(linea, color) for linea in parrafo.split("\n"))
        parrafos.append(f'<p style="margin:0 0 16px;">{lineas}</p>')
    return "".join(parrafos)


def html_del_correo(empresa, texto: str, con_logo: bool) -> str:
    paleta = paleta_de(empresa.paleta)
    nombre = escape(empresa.nombre_visible)
    if con_logo:
        marca = (
            f'<img src="cid:{CID_LOGO}" alt="Logo de {nombre}" width="180" height="60" '
            'style="display:block;border:0;">'
        )
    else:
        estilo = f"display:block;padding:6px 8px;font-size:18px;font-weight:bold;color:{paleta.oscuro};"
        marca = f'<span style="{estilo}">{escape(empresa.iniciales or "FlotaÁgil")}</span>'
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        f'<body style="margin:0;padding:0;background:{paleta.claro};">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{paleta.claro}">'
        '<tr><td align="center" style="padding:24px 12px;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="max-width:560px;background:#ffffff;border-radius:12px;overflow:hidden;'
        'font-family:Arial,Helvetica,sans-serif;">'
        f'<tr><td bgcolor="{paleta.oscuro}" style="padding:20px 24px;background-color:{paleta.oscuro};'
        f'background-image:linear-gradient(90deg,{paleta.oscuro},{paleta.medio});">'
        # El logo va sobre una base blanca redondeada: un JPG con fondo blanco no se ve como un cuadro.
        '<div style="display:inline-block;padding:8px;background:#ffffff;border-radius:10px;">'
        f"{marca}</div>"
        f'<div style="margin-top:12px;color:#ffffff;font-size:16px;font-weight:bold;">{nombre}</div>'
        "</td></tr>"
        f'<tr><td style="padding:24px;color:{TEXTO};font-size:15px;line-height:1.5;">'
        f"{_parrafos(texto, paleta.oscuro)}</td></tr>"
        f'<tr><td style="padding:0 24px 20px;color:{TEXTO};font-size:12px;">Operado con FlotaÁgil</td></tr>'
        "</table></td></tr></table></body></html>"
    )
