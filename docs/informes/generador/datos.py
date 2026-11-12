"""Cifras oficiales del proyecto para los textos de los informes (leídas de ../datos/datos.json).

Correr antes `python extraer_datos.py`. Así las cifras que cambian con cada historia (pruebas, DC, entidades)
no quedan escritas a mano en los .py.
"""
import json
import os

_RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "datos", "datos.json")
D = json.load(open(_RUTA, encoding="utf-8"))
P = D["pruebas"]


def miles(n):
    """1255 → '1.255'."""
    return f"{int(n):,}".replace(",", ".")


def pct(x):
    """97.9 → '97,9 %'."""
    return f"{x:.1f}".replace(".", ",") + " %"


PRUEBAS = miles(D["pruebas_total"])
PB, PW, PA = miles(P["backend"]["pruebas"]), miles(P["web"]["pruebas"]), miles(P["app"]["pruebas"])
CB, CW, CA = pct(P["backend"]["cobertura"]), pct(P["web"]["cobertura"]), pct(P["app"]["cobertura"])
DC_MAX = f"{D['dc_max']:02d}"
DC_TOTAL = D["dc_total"]
ENTIDADES = D["entidades"]
PRUEBAS_DETALLE = f"{PB} de backend, {PW} de web y {PA} de la app"
