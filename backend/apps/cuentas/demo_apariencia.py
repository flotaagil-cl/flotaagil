"""CC-27: apariencia de demostración. El logo es sintético (dibujado aquí), sin marcas reales."""

import io

from PIL import Image, ImageDraw, ImageFont

from apps.auditoria.models import Auditoria, Entidad

from . import logos
from .models import Empresa

# Empresa demo → paleta. Taxi Pacífico se queda con Tiffany y sin logo, para comparar.
APARIENCIA_DEMO = {"transportes-andes": "indigo"}


def logo_sintetico(texto: str = "ANDES DEMO") -> bytes:
    """Un cerro blanco dentro de un círculo y un nombre ficticio, sobre fondo transparente."""
    imagen = Image.new("RGBA", (900, 260), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    azul = (43, 42, 120, 255)
    dibujo.ellipse((20, 20, 240, 240), fill=azul)
    dibujo.polygon([(52, 180), (108, 92), (140, 134), (166, 104), (210, 180)], fill=(255, 255, 255, 255))
    dibujo.text((282, 130), texto, font=ImageFont.load_default(size=82), fill=azul, anchor="lm")
    salida = io.BytesIO()
    imagen.save(salida, format="PNG")
    return salida.getvalue()


def cargar(empresa: Empresa) -> None:
    """Solo si nadie ha tocado la apariencia: repetir datos_demo no pisa lo que eligió el administrador."""
    paleta = APARIENCIA_DEMO.get(empresa.slug)
    if paleta is None or empresa.logo or empresa.paleta != "tiffany":
        return
    if Auditoria.objects.filter(
        entidad=Entidad.EMPRESA, entidad_id=empresa.pk, accion="EDITAR_APARIENCIA"
    ).exists():
        return
    empresa.paleta = paleta
    empresa.logo = logos.guardar(empresa.pk, logos.procesar(logo_sintetico()))
    empresa.save(update_fields=["paleta", "logo"])
