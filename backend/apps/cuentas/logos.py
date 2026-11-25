"""CC-27 (DC-83): procesamiento y almacenamiento del logo de la empresa.

Se verifica que el contenido sea una imagen (no basta la extensión), se descartan los metadatos, se corrige
la orientación y se recortan los márgenes vacíos. De ese original se generan versiones PNG de proporción fija.
Todo se guarda con `default_storage`: disco local en desarrollo y S3 en el despliegue solo con variables de
entorno.
"""

import io
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageChops, ImageOps, UnidentifiedImageError

MAXIMO_BYTES = 2 * 1024 * 1024
ANCHO_MINIMO = 256
# Contra las imágenes pequeñas en bytes y enormes en píxeles: se rechazan antes de descomprimirlas.
MAXIMO_PIXELES = 40_000_000
FORMATOS = ("PNG", "JPEG", "WEBP")
LADO_MAXIMO_ORIGINAL = 2048
# Tolerancia para considerar «blanco» un margen de un JPG comprimido.
TOLERANCIA_BLANCO = 12

# Versiones de proporción fija (ancho, alto): el logo se ajusta dentro y se centra sobre fondo transparente.
VARIANTES = {
    "panel": (480, 160),
    "portal": (600, 200),
    "app": (480, 160),
    "correo": (360, 120),
    "icono": (128, 128),
}
ARCHIVOS = ("original", *VARIANTES)


class LogoInvalido(Exception):
    """El archivo no sirve como logo; el mensaje se muestra tal cual al administrador."""


def _abrir(contenido: bytes) -> Image.Image:
    try:
        imagen = Image.open(io.BytesIO(contenido))
        if imagen.format not in FORMATOS:
            raise LogoInvalido("El logo debe ser una imagen PNG, JPG o WebP.")
        ancho, alto = imagen.size
        if ancho * alto > MAXIMO_PIXELES:
            raise LogoInvalido("La imagen tiene demasiados píxeles. Súbela más pequeña.")
        imagen.load()  # falla si el archivo está truncado o corrupto
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError) as error:
        raise LogoInvalido("El archivo no es una imagen válida (PNG, JPG o WebP).") from error
    return imagen


def _sin_margenes(imagen: Image.Image) -> Image.Image:
    """Recorta los bordes transparentes y, en imágenes opacas con fondo blanco, los bordes blancos."""
    alfa = imagen.getchannel("A")
    caja = alfa.point(lambda a: 255 if a > 8 else 0).getbbox()
    if caja is None:
        raise LogoInvalido("La imagen está vacía.")
    imagen = imagen.crop(caja)
    esquinas = [(0, 0), (imagen.width - 1, 0), (0, imagen.height - 1), (imagen.width - 1, imagen.height - 1)]
    if all(_es_blanco(imagen.getpixel(p)) for p in esquinas):
        blanco = Image.new("RGB", imagen.size, (255, 255, 255))
        diferencia = ImageChops.difference(imagen.convert("RGB"), blanco).convert("L")
        caja = diferencia.point(lambda v: 255 if v > TOLERANCIA_BLANCO else 0).getbbox()
        if caja is None:
            raise LogoInvalido("La imagen está vacía.")
        imagen = imagen.crop(caja)
    return imagen


def _es_blanco(pixel) -> bool:
    r, g, b, a = pixel
    return a == 255 and min(r, g, b) >= 255 - TOLERANCIA_BLANCO


def _png(imagen: Image.Image) -> bytes:
    imagen.info.clear()  # sin EXIF, perfiles ni comentarios
    salida = io.BytesIO()
    imagen.save(salida, format="PNG", optimize=True)
    return salida.getvalue()


def _ajustar(imagen: Image.Image, ancho: int, alto: int) -> Image.Image:
    escalada = ImageOps.contain(imagen, (ancho, alto), Image.Resampling.LANCZOS)
    lienzo = Image.new("RGBA", (ancho, alto), (255, 255, 255, 0))
    lienzo.paste(escalada, ((ancho - escalada.width) // 2, (alto - escalada.height) // 2), escalada)
    return lienzo


def procesar(contenido: bytes) -> dict[str, bytes]:
    """Los archivos PNG del logo (original procesado y versiones). Lanza LogoInvalido."""
    if len(contenido) > MAXIMO_BYTES:
        raise LogoInvalido("El logo pesa más de 2 MB.")
    imagen = ImageOps.exif_transpose(_abrir(contenido)).convert("RGBA")
    if imagen.width < ANCHO_MINIMO:
        raise LogoInvalido(
            f"El logo debe medir al menos {ANCHO_MINIMO} px de ancho (mide {imagen.width} px)."
        )
    imagen = _sin_margenes(imagen)
    imagen.thumbnail((LADO_MAXIMO_ORIGINAL, LADO_MAXIMO_ORIGINAL), Image.Resampling.LANCZOS)
    archivos = {nombre: _png(_ajustar(imagen, *medidas)) for nombre, medidas in VARIANTES.items()}
    archivos["original"] = _png(imagen)
    return archivos


def ruta(carpeta: str, nombre: str) -> str:
    return f"{carpeta}/{nombre}.png"


def guardar(empresa_id: int, archivos: dict[str, bytes]) -> str:
    """Guarda una versión nueva y devuelve su carpeta; el nombre aleatorio evita ver la anterior en caché."""
    carpeta = f"logos/{empresa_id}/{uuid.uuid4().hex}"
    try:
        for nombre, contenido in archivos.items():
            default_storage.save(ruta(carpeta, nombre), ContentFile(contenido))
    except Exception:
        borrar(carpeta)
        raise
    return carpeta


def borrar(carpeta: str | None) -> None:
    if carpeta:
        for nombre in ARCHIVOS:
            default_storage.delete(ruta(carpeta, nombre))
