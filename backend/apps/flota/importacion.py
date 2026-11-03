"""Carga inicial de vehículos y de conductores por CSV (HU-10).

Todo o nada: se valida cada fila con las mismas reglas del alta individual y solo se crea si ninguna tiene
errores. Sin `confirmar` solo se entrega el informe, para revisarlo antes de cargar.

Formato común: encabezado en la primera línea; mayúsculas y tildes no importan. Separador coma o punto y coma
(Excel en español guarda con punto y coma). Codificación UTF-8 (con o sin BOM) o Windows-1252. Hasta 500 filas
y 1 MB.

- Vehículos: `patente`, `marca_modelo`, `anio` y, opcional, `capacidad` (por defecto 4). También sirven «año»,
  «marca y modelo» y «marca/modelo».
- Conductores: `nombre`, `email`, `rut`, `telefono`, `licencia_clase` y `licencia_vence` (AAAA-MM-DD o
  DD-MM-AAAA). Sin contraseñas: las cuentas quedan sin contraseña utilizable y el administrador genera una
  temporal desde la ficha de cada conductor.
"""

import csv
import io
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.comun.validadores import normalizar_rut

from .serializers import ConductorCrearSerializer, VehiculoCrearSerializer, normalizar_patente

MAX_BYTES = 1024 * 1024
MAX_FILAS = 500


@dataclass(frozen=True)
class Formato:
    """Qué columnas lleva el archivo, cómo se valida cada fila y qué valores no se pueden repetir."""

    nombre_plural: str
    obligatorias: tuple[str, ...]
    opcionales: tuple[str, ...]
    serializer: type[serializers.Serializer]
    # Campo → función que normaliza el valor para detectar repetidos dentro del archivo.
    unicos: dict[str, Callable[[str], str]] = field(default_factory=dict)
    sinonimos: dict[str, str] = field(default_factory=dict)
    # Ajusta la fila antes de validarla (p. ej. fechas DD-MM-AAAA).
    preparar: Callable[[dict], dict] | None = None


def _columna(formato: Formato, encabezado: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", encabezado).encode("ascii", "ignore").decode()
    limpio = " ".join(sin_tildes.strip().lower().split())
    return formato.sinonimos.get(limpio, limpio.replace(" ", "_"))


def _error_archivo(mensaje: str) -> ValidationError:
    return ValidationError({"archivo": [mensaje]})


def _decodificar(contenido: bytes) -> str:
    try:
        return contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        return contenido.decode("cp1252", errors="replace")


def leer_filas(archivo, formato: Formato) -> list[tuple[int, dict]]:
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
    columnas = [_columna(formato, c) for c in encabezado]
    faltan = [c for c in formato.obligatorias if c not in columnas]
    if faltan:
        esperado = ", ".join(formato.obligatorias)
        opcional = f" y, opcional, {', '.join(formato.opcionales)}" if formato.opcionales else ""
        raise _error_archivo(
            f"Faltan columnas: {', '.join(faltan)}. El encabezado debe tener {esperado}{opcional}."
        )
    conocidas = set(formato.obligatorias + formato.opcionales)
    filas = []
    for valores in lector:
        if not any(v.strip() for v in valores):
            continue
        if len(filas) == MAX_FILAS:
            raise _error_archivo(
                f"El archivo tiene más de {MAX_FILAS} {formato.nombre_plural}. Divídelo en partes."
            )
        fila = {col: valor.strip() for col, valor in zip(columnas, valores, strict=False) if col in conocidas}
        filas.append((lector.line_num, fila))
    if not filas:
        raise _error_archivo(f"El archivo no tiene {formato.nombre_plural}: solo el encabezado.")
    return filas


def validar(filas: list[tuple[int, dict]], formato: Formato) -> tuple[list[dict], list[dict]]:
    """Devuelve (informe por fila, datos válidos listos para crear)."""
    informe, validos = [], []
    vistas: dict[str, dict[str, int]] = {campo: {} for campo in formato.unicos}
    for linea, fila in filas:
        datos = {k: v for k, v in fila.items() if v != ""}
        if formato.preparar:
            datos = formato.preparar(datos)
        entrada = formato.serializer(data=datos)
        errores = {} if entrada.is_valid() else {k: [str(e) for e in v] for k, v in entrada.errors.items()}
        for campo, normalizar in formato.unicos.items():
            valor = normalizar(fila.get(campo, ""))
            if not valor:
                continue
            if campo not in errores and valor in vistas[campo]:
                errores[campo] = [f"Repetido en el archivo (línea {vistas[campo][valor]})."]
            vistas[campo].setdefault(valor, linea)
        informe.append({"linea": linea, "datos": fila, "errores": errores})
        if not errores:
            validos.append(dict(entrada.validated_data))
    return informe, validos


_FECHA_CHILENA = re.compile(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$")


def fecha_iso(valor: str) -> str:
    """«31-12-2027» o «31/12/2027» → «2027-12-31». Lo demás queda igual para que lo valide el serializer."""
    coincidencia = _FECHA_CHILENA.match(valor.strip())
    if not coincidencia:
        return valor
    dia, mes, anio = coincidencia.groups()
    return f"{anio}-{int(mes):02d}-{int(dia):02d}"


VEHICULOS = Formato(
    nombre_plural="vehículos",
    obligatorias=("patente", "marca_modelo", "anio"),
    opcionales=("capacidad",),
    serializer=VehiculoCrearSerializer,
    unicos={"patente": normalizar_patente},
    sinonimos={
        "ano": "anio",
        "marca y modelo": "marca_modelo",
        "marca/modelo": "marca_modelo",
        "marca modelo": "marca_modelo",
        "modelo": "marca_modelo",
    },
)
CONDUCTORES = Formato(
    nombre_plural="conductores",
    obligatorias=("nombre", "email", "rut", "telefono", "licencia_clase", "licencia_vence"),
    opcionales=(),
    serializer=ConductorCrearSerializer,
    unicos={"email": lambda v: v.strip().lower(), "rut": normalizar_rut},
    sinonimos={
        "correo": "email",
        "correo electronico": "email",
        "telefono movil": "telefono",
        "celular": "telefono",
        "clase de licencia": "licencia_clase",
        "clase licencia": "licencia_clase",
        "vencimiento licencia": "licencia_vence",
        "vencimiento de la licencia": "licencia_vence",
    },
    preparar=lambda datos: {
        **datos,
        **({"licencia_vence": fecha_iso(datos["licencia_vence"])} if "licencia_vence" in datos else {}),
        **({"licencia_clase": datos["licencia_clase"].upper()} if "licencia_clase" in datos else {}),
    },
)
