"""Lee el repositorio y deja las cifras oficiales del proyecto en docs/informes/datos/datos.json.

Uso (desde docs/informes/generador):  python extraer_datos.py
El informe y revisar.py usan este archivo para no escribir cifras a mano.

Fuentes:
- docs/backlog/backlog.json            historias y story points
- docs/diccionario-cambios.md          decisiones de cambio (DC-xx)
- backend/apps/*/models.py             entidades del modelo (clases models.Model y el usuario)
- docs/informes/datos/pruebas.json     conteo real de pruebas; lo actualiza quien corre las suites
                                       (ver la regla «Informes y evidencias» de CLAUDE.md)
"""
import datetime
import glob
import json
import os
import re

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
SALIDA = os.path.join(AQUI, "..", "datos", "datos.json")


def leer(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as f:
        return f.read()


def main():
    d = {"generado": datetime.datetime.now().isoformat(timespec="seconds")}

    bl = json.loads(leer("docs/backlog/backlog.json"))
    hs = bl["historias"] if isinstance(bl, dict) else bl
    d["hu_total"] = len(hs)
    d["sp_total"] = sum(int(h.get("sp") or 0) for h in hs)
    campo = next((k for k in ("estado", "status", "Estado") if hs and k in hs[0]), None)
    if campo:
        est = {}
        for h in hs:
            est[h[campo]] = est.get(h[campo], 0) + 1
        d["hu_por_estado"] = est

    dic = leer("docs/diccionario-cambios.md")
    dcs = sorted({int(x) for x in re.findall(r"^\|\s*DC-(\d+)", dic, re.M)})
    d["dc_total"] = len(dcs)
    d["dc_max"] = max(dcs) if dcs else None
    d["dc_faltantes"] = [n for n in range(1, (max(dcs) if dcs else 0) + 1) if n not in dcs]
    ccs = sorted({int(x) for x in re.findall(r"\bCC-(\d+)", dic + leer("docs/README.md"))})
    d["cc_max"] = max(ccs) if ccs else None

    clases = []
    for f in sorted(glob.glob(os.path.join(REPO, "backend", "apps", "*", "models.py"))):
        for m in re.finditer(r"^class (\w+)\(([^)]*)\):", open(f, encoding="utf-8").read(), re.M):
            nombre, bases = m.group(1), m.group(2)
            if "Manager" in nombre or "Manager" in bases:
                continue
            if "models.Model" in bases or "AbstractBaseUser" in bases or "AbstractUser" in bases:
                clases.append(nombre)
    d["entidades"] = len(clases)
    d["entidades_lista"] = clases

    pj = os.path.join(AQUI, "..", "datos", "pruebas.json")
    if os.path.exists(pj):
        p = json.load(open(pj, encoding="utf-8"))
        d["pruebas"] = p
        partes = [p.get(k, {}).get("pruebas") for k in ("backend", "web", "app")]
        d["pruebas_total"] = sum(x for x in partes if isinstance(x, int)) if all(isinstance(x, int) for x in partes) else None
    else:
        d["pruebas_total"] = None
        d["aviso"] = "Falta docs/informes/datos/pruebas.json: no se verifican los conteos de pruebas."

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in d.items() if k != "entidades_lista"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
