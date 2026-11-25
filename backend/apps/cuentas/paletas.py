"""CC-27 (DC-84): catálogo fijo de paletas, sin colores libres. La única fuente es `paletas.json`: la web y la
app generan de ahí sus tokens, y los correos toman de aquí sus colores.
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paleta:
    clave: str
    nombre: str
    oscuro: str
    medio: str
    claro: str


_CATALOGO = json.loads((Path(__file__).parent / "paletas.json").read_text(encoding="utf-8"))

PREDETERMINADA: str = _CATALOGO["predeterminada"]
PALETAS: dict[str, Paleta] = {p["clave"]: Paleta(**p) for p in _CATALOGO["paletas"]}
OPCIONES = [(p.clave, p.nombre) for p in PALETAS.values()]


def paleta_de(clave: str | None) -> Paleta:
    """La paleta de esa clave; si ya no existe en el catálogo, la predeterminada."""
    return PALETAS.get(clave or "", PALETAS[PREDETERMINADA])
