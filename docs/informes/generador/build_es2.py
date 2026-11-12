"""Informe 2 (ES2) según la plantilla oficial: I a X. Formulación en el Informe 1; desarrollo por sprint en el Anexo P."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from lib import Report
import sec0, sec1, sec2, sec3, sec4, sec_impl, annex
from build import pdf, page_texts, norm

COVER = dict(carrera="  ·  Ingeniería en Informática", seccion="2026/P TIHI84/V-IEI-N8-P1-C1/V", sede="La Granja",
             docente="Alan Gajardo Medina", integrantes="Renato González – Carlos Ortiz",
             fecha="Noviembre de 2026", version="Informe 2 · Evaluación Sumativa 2 (ES2) · versión final",
             titulo="FlotaÁgil: Plataforma SaaS para la Gestión de Flotas de Taxi Turismo")

# ---------------------------------------------------------------- renumeración de referencias
CH = {1: "1", 3: "2", 4: "3", 5: "4", 6: "5", 8: "6", 9: "7"}
INF1 = {"2.1": "2.1", "2.2": "2.1", "2.3": "3.1", "2.4": "4.2", "2.5": "5.1", "2.6": "6.1"}
ROM = {"II": "Informe 1", "III": "II", "IV": "III", "V": "IV", "VI": "V", "VII": "Anexo P", "VIII": "VI", "IX": "VII",
       "X": "VIII", "XI": "IX", "XII": "X"}


SENT = "\u2063"


def mapnum(x, cell=False):
    """'4.1' → ('sec','3.1'); '7.7' → ('anx','Anexo P'); '2.4' → ('inf1','4.2')."""
    p = x.split(".")
    d = int(p[0])
    if d == 1:
        sub = {"3": "2", "4": "3"}.get(p[1], p[1]) if len(p) > 1 else ""
        return ("sec", "1." + sub)
    if d in CH:
        return ("sec", CH[d] + ("." + ".".join(p[1:]) if len(p) > 1 else ""))
    if d == 7:
        return ("anx", "Anexo P")
    if d == 2:
        if x.startswith("2.3"):
            return ("anx", "Anexo O") if cell else ("inf1", "3.1")
        return ("inf1", INF1.get(".".join(p[:2]), "2.1"))
    return ("sec", x)


NUM = r"\d\.\d(?:\.\d)?"


def remap_text(t):
    if SENT in t:
        return t.replace(SENT, "")
    def sec(m):
        art, x = m.group(1) or "", m.group(2)
        k, v = mapnum(x)
        if k == "sec":
            return f"{art}sección {v}"
        if k == "anx":
            a = {"la ": "el ", "en la ": "en el ", "de la ": "del ", "a la ": "al "}.get(art, art)
            return f"{a}{v}"
        return f"{art}sección {v} del Informe 1"
    t = re.sub(r"((?:en |de |a )?la )?secci[oó]n (" + NUM + r")(?![\d])", sec, t)

    def cap(m):
        v = ROM.get(m.group(1), m.group(1))
        return v if v.startswith(("Anexo", "Informe")) else "capítulo " + v
    t = re.sub(r"cap[ií]tulo ([IVX]+)\b", cap, t)

    def par(m):
        k, v = mapnum(m.group(1))
        return "(" + (v if k != "inf1" else f"Informe 1, sección {v}") + ")"
    t = re.sub(r"\((" + NUM + r")\)", par, t)
    t = re.sub(r"\ben ((?:4|5|6|8|9)\.\d)\b(?=[ ,.;:)])", lambda m: "en " + mapnum(m.group(1))[1], t)
    t = re.sub(r"\bde ((?:4|5|6|8|9)\.\d)\b(?=[ ,.;:)])", lambda m: "de " + mapnum(m.group(1))[1], t)
    return t


def remap_cell(c):
    parts = [p.strip() for p in re.split(r",\s*", c)]
    out = []
    for p in parts:
        m = re.fullmatch(r"(" + NUM + r")(?:[–-](" + NUM + r"))?", p)
        if m:
            k, v = mapnum(m.group(1), cell=True)
            v = v if k != "inf1" else f"Informe 1 ({v})"
            if m.group(2):
                k2, v2 = mapnum(m.group(2))
                v = f"{v}–{v2}" if k == k2 == "sec" else v
            out.append(v)
        elif p in ROM:
            out.append(ROM[p])
        else:
            out.append(p)
    res = []
    for o in out:
        if o not in res:
            res.append(o)
    return SENT + ", ".join(res)


# ---------------------------------------------------------------- anexos O y P
def anexo_O(r):
    annex.AH(r, "Anexo O. Requerimientos, reglas de negocio, parámetros y riesgos vigentes")
    r.P(SENT + "Se reproducen aquí, para la consulta de este informe, los requerimientos y la matriz de riesgos vigentes; su origen y su "
        "justificación están en el Informe 1 (levantamiento, capítulo III, y metodología, capítulo VI).")
    h3 = r.H3
    r.H3 = lambda text: r.H4("O. " + text)
    sec1.requerimientos(r)
    r.H4("O. Matriz de riesgos y estado al corte de la semana 14")
    sec0.riesgos(r, heading=False)
    r.H3 = h3


def anexo_P(r):
    annex.AH(r, "Anexo P. Desarrollo e implementación de la solución")
    h1, h2 = r.H1, r.H2
    cnt = {"n": 0}
    r.H1 = lambda text, page_break=True: None

    def h2p(text, numbered=True):
        cnt["n"] += 1
        return r.H4(f"P.{cnt['n']} {text}")
    r.H2 = h2p
    sec_impl.implementacion_real(r)
    r.H1, r.H2 = h1, h2


def build(toc_entries, out):
    r = Report("template.docx", COVER)
    r.remap = remap_text
    r.cellremap = remap_cell
    r.toc(toc_entries)
    sec1.intro(r)
    sec1.tecnologias(r)
    sec2.arquitectura(r)
    sec3.kpi_sla(r)
    sec3.pruebas_normas(r)
    sec4.implementacion(r)
    sec4.cronograma(r)
    sec4.conclusiones(r)
    sec4.referencias(r)
    annex.anexos(r)
    r.landscape_off() if r.landscape else None
    anexo_O(r)
    anexo_P(r)
    r.save(out)
    return r


def run(name):
    os.makedirs("out", exist_ok=True)
    r = build([(1, "x", 0)], "out/_e2_pass0.docx")
    heads = [(l, t) for l, t in r.headings if l <= 2]
    build([(l, t, 99) for l, t in heads], "out/_e2_pass1.docx")
    pages = page_texts(pdf("out/_e2_pass1.docx"))
    toc_pages = [i for i, t in enumerate(pages) if t.count("....") > 8]
    cur = (max(toc_pages) + 1) if toc_pages else 1
    res = []
    for l, t in heads:
        key = norm(t)[:45]
        found = next((i for i in range(cur, len(pages)) if key in pages[i]), None)
        if found is None:
            print("NO ENCONTRADO:", t); found = cur
        cur = found
        res.append((l, t, found + 1))
    build(res, f"out/{name}.docx")
    import revisar
    errores = revisar.main([f"out/{name}.docx"])
    if errores and "--forzar" not in sys.argv:
        print("\nRevisión con errores: no se genera el PDF. Corrige o usa --forzar.")
        sys.exit(1)
    p = pdf(f"out/{name}.docx")
    pages2 = page_texts(p)
    bad = [(t, pg) for l, t, pg in res if norm(t)[:45] not in pages2[pg - 1]]
    print("páginas:", len(pages2), "desajustes:", bad[:10])
    return p


if __name__ == "__main__":
    run("Informe2_ES2_FlotaAgil")
