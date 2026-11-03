"""Carga inicial de vehículos por CSV (HU-10).

Todo o nada: se valida cada fila con las mismas reglas del alta individual y solo se crea si ninguna tiene
errores. Sin `confirmar` solo se entrega el informe, para revisarlo antes de cargar.

Formato: encabezado en la primera línea con `patente`, `marca_modelo`, `anio` y, opcional, `capacidad`
(por defecto 4). Se aceptan las variantes «año», «marca y modelo», «marca/modelo», mayúsculas y tildes.
Separador coma o punto y coma (Excel en español guarda con punto y coma). Codificación UTF-8 (con o sin BOM)
o Windows-1252.
"""

import csv
import io
import unicodedata

from rest_framework.exceptions import ValidationError

from .serializers import VehiculoCrearSerializer, normalizar_patente

MAX_BYTES = 1024 * 1024
MAX_FILAS = 500
OBLIGATORIAS = ("patente", "marca_modelo", "anio")
OPCIONALES = ("capacidad",)

SINONIMOS = {
    "ano": "anio",
    "marca y modelo": "marca_modelo",
    "marca/modelo": "marca_modelo",
    "marca modelo": "marca_modelo",
    "modelo": "marca_modelo",
}


def _columna(encabezado: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", encabezado).encode("ascii", "ignore").decode()
    limpio = " ".join(sin_tildes.strip().lower().split())
    return SINONIMOS.get(limpio, limpio.replace(" ", "_"))


def _error_archivo(mensaje: str) -> ValidationError:
    return ValidationError({"archivo": [mensaje]})


def _decodificar(contenido: bytes) -> str:
    try:
        return contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        return contenido.decode("cp1252", errors="replace")


def leer_filas(archivo) -> list[tuple[int, dict]]:
    """(línea, fila) con las columnas reconocidas. Lanza ValidationError si el archivo no sirve."""
    if archivo.size > MAX_BYTES:
        raise _error_archivo("El archivo supera 1 MB.")
    texto = _decodificar(archivo.read())
    primera = texto.split("\n", 1)[0]
    separador = ";" if primera.count(";") > primera.count(",") else ","
    lector = csv.reader(io.StringIO(texto), delimiter=separador)
    try:
        encabezado = next(lector)
    except StopIteration:
        raise _error_archivo("El archivo está vacío.") from None
    columnas = [_columna(c) for c in encabezado]
    faltan = [c for c in OBLIGATORIAS if c not in columnas]
    if faltan:
        raise _error_archivo(
            f"Faltan columnas: {', '.join(faltan)}. El encabezado debe tener patente, marca_modelo, anio "
            "y, opcional, capacidad."
        )
    conocidas = set(OBLIGATORIAS + OPCIONALES)
    filas = []
    for valores in lector:
        if not any(v.strip() for v in valores):
            continue
        if len(filas) == MAX_FILAS:
            raise _error_archivo(f"El archivo tiene más de {MAX_FILAS} vehículos. Divídelo en partes.")
        fila = {col: valor.strip() for col, valor in zip(columnas, valores, strict=False) if col in conocidas}
        filas.append((lector.line_num, fila))
    if not filas:
        raise _error_archivo("El archivo no tiene vehículos: solo el encabezado.")
    return filas


def validar(filas: list[tuple[int, dict]]) -> tuple[list[dict], list[dict]]:
    """Devuelve (informe por fila, datos válidos listos para crear)."""
    informe, validos, vistas = [], [], {}
    for linea, fila in filas:
        datos = {k: v for k, v in fila.items() if v != ""}
        entrada = VehiculoCrearSerializer(data=datos)
        errores = {} if entrada.is_valid() else {k: [str(e) for e in v] for k, v in entrada.errors.items()}
        patente = normalizar_patente(fila.get("patente", ""))
        if patente and "patente" not in errores and patente in vistas:
            errores["patente"] = [f"Repetida en el archivo (línea {vistas[patente]})."]
        if patente:
            vistas.setdefault(patente, linea)
        informe.append({"linea": linea, "datos": fila, "errores": errores})
        if not errores:
            validos.append(dict(entrada.validated_data))
    return informe, validos
