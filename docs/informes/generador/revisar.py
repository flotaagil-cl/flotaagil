"""Revisión automática de un informe generado (.docx) antes de convertirlo a PDF.

Uso:  python revisar.py out/Informe2_ES2_FlotaAgil.docx [out/otro.docx ...]
Sale con código 1 si hay errores. Las reglas están en revisar_reglas.json y las
cifras de referencia en ../datos/datos.json (lo genera extraer_datos.py).
"""
import json
import os
import re
import sys

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph

AQUI = os.path.dirname(os.path.abspath(__file__))
H1, H2 = "Título1", "Subtitulo1"


def bloques(path):
    """Recorre el cuerpo en orden y entrega (capítulo, sección, texto) por párrafo o celda."""
    d = docx.Document(path)
    cap, sec = "", ""
    for el in d.element.body.iterchildren():
        tag = el.tag.split("}")[-1]
        if tag == "p":
            p = Paragraph(el, d)
            est = p.style.name if p.style is not None else ""
            if est.startswith("toc"):
                continue
            if est == H1:
                cap, sec = p.text.strip(), ""
            elif est == H2:
                sec = p.text.strip()
            if p.text.strip():
                yield cap, sec, p.text
        elif tag == "tbl":
            t = Table(el, d)
            for fila in t.rows:
                vistos = set()
                for celda in fila.cells:
                    if id(celda._tc) in vistos:
                        continue
                    vistos.add(id(celda._tc))
                    if celda.text.strip():
                        yield cap, sec, celda.text


def permitido(regla, cap, sec):
    for z in regla.get("permitido_en", []):
        if z.lower() in cap.lower() or z.lower() in sec.lower():
            return True
    return False


def num(s):
    return int(s.replace(".", ""))


def revisar(path, reglas=None, datos=None):
    reglas = reglas or json.load(open(os.path.join(AQUI, "revisar_reglas.json"), encoding="utf-8"))
    if datos is None:
        p = os.path.join(AQUI, "..", "datos", "datos.json")
        datos = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    errores, avisos = [], []
    citas, refs, cuerpo = [], [], []
    for cap, sec, txt in bloques(path):
        donde = (sec or cap)[:60]
        # 1) frases prohibidas o desactualizadas
        for r in reglas["frases"]:
            if re.search(r["patron"], txt, re.I) and not permitido(r, cap, sec):
                m = re.search(r["patron"], txt, re.I)
                frag = txt[max(0, m.start() - 50):m.end() + 50].replace("\n", " ")
                (errores if r.get("nivel", "error") == "error" else avisos).append(f"[{donde}] {r['motivo']}: «…{frag}…»")
        # 2) referencias internas sin resolver
        if re.search(r"\{[TF]:\w+|\?\?", txt):
            errores.append(f"[{donde}] referencia a tabla o figura sin resolver: «{txt[:80]}»")
        # 3) cifras contra datos.json
        for c in reglas.get("cifras", []):
            if c["clave"] not in datos or datos[c["clave"]] is None:
                continue
            for m in re.finditer(c["patron"], txt):
                if permitido(c, cap, sec):
                    continue
                if num(m.group(1)) != datos[c["clave"]]:
                    errores.append(f"[{donde}] {c['motivo']}: dice {m.group(1)}, el repo dice {datos[c['clave']]}")
        # 4) para el cruce de citas y referencias
        if "referencias" in cap.lower():
            refs.append(txt)
        else:
            cuerpo.append(txt)
            citas += re.findall(r"([A-ZÁÉÍÓÚ][\wÁÉÍÓÚáéíóúñ.&\- ]{1,70}?),? (\d{4})[a-z]?\)", txt)
    # 5) referencias que no se citan en el cuerpo
    texto = " ".join(cuerpo)
    for ref in refs:
        m = re.match(r"([^(]{2,90}?)\. \((\d{4})([a-z]?)\)", ref)
        if not m:
            continue
        autor, anio = m.group(1).split(",")[0].strip(), m.group(2)
        alias = reglas.get("alias_autor", {}).get(autor, autor)
        if not re.search(r"(" + alias + r")[^)]{0,90}?" + anio, texto):
            avisos.append(f"[Referencias] no se cita en el texto: {autor} ({anio}{m.group(3)})")
    return errores, avisos


def main(paths):
    total = 0
    for p in paths:
        e, a = revisar(p)
        print(f"\n== {os.path.basename(p)}: {len(e)} errores, {len(a)} avisos")
        for x in e:
            print("  ERROR ", x)
        for x in a:
            print("  aviso ", x)
        total += len(e)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
