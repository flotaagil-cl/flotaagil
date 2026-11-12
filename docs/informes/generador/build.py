import subprocess, re, sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from lib import Report
import sec0, sec1, sec2, sec3, sec4, sec_impl, annex

COVER = dict(carrera="  ·  Ingeniería en Informática", seccion="2026/P TIHI84/V-IEI-N8-P1-C1/V", sede="La Granja",
             docente="Alan Gajardo Medina", integrantes="Renato González – Carlos Ortiz",
             fecha="Noviembre de 2026", version="Evaluación Sumativa 2 (ES2) · versión 3.0, corregida tras la EF2",
             titulo="FlotaÁgil: Plataforma SaaS para la Gestión de Flotas de Taxi Turismo")


def build(toc_entries, out):
    r = Report("template.docx", COVER)
    r.toc(toc_entries)
    sec1.intro(r)
    sec0.formulacion(r)
    sec1.tecnologias(r)
    sec2.arquitectura(r)
    sec3.kpi_sla(r)
    sec3.pruebas_normas(r)
    sec_impl.implementacion_real(r)
    sec4.implementacion(r)
    sec4.cronograma(r)
    sec4.conclusiones(r)
    sec4.referencias(r)
    annex.anexos(r)
    r.save(out)
    return r


def _soffice():
    """Ubica LibreOffice (Linux, macOS o Windows)."""
    import shutil
    for c in ("soffice", "libreoffice", r"C:\Program Files\LibreOffice\program\soffice.exe",
              "/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        p = shutil.which(c) or (c if os.path.exists(c) else None)
        if p:
            return p
    raise RuntimeError("No se encontró LibreOffice (soffice). Instálalo para convertir a PDF.")


def pdf(docx_path):
    subprocess.run([_soffice(), "--headless", "--convert-to", "pdf", "--outdir", os.path.dirname(docx_path) or ".", docx_path],
                   check=True, capture_output=True)
    return docx_path[:-5] + ".pdf"


def page_texts(pdf_path):
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True).stdout).group(1))
    out = []
    for i in range(1, n + 1):
        t = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), "-layout", pdf_path, "-"], capture_output=True, text=True).stdout
        out.append(re.sub(r"\s+", " ", t))
    return out


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    # pasada 1: obtener títulos
    r = build([(1, "x", 0)], "out/pass0.docx")
    heads = [(l, t) for l, t in r.headings if l <= 2]
    entries = [(l, t, 99) for l, t in heads]
    build(entries, "out/pass1.docx")
    pages = page_texts(pdf("out/pass1.docx"))
    toc_pages = [i for i, t in enumerate(pages) if t.count("....") > 8]
    start = (max(toc_pages) + 1) if toc_pages else 1
    res = []
    cur = start
    for l, t in heads:
        key = norm(t)[:45]
        found = None
        for i in range(cur, len(pages)):
            if key in pages[i]:
                found = i
                break
        if found is None:
            print("NO ENCONTRADO:", t)
            found = cur
        cur = found
        res.append((l, t, found + 1))
    build(res, "out/Proyecto_de_Titulo_FlotaAgil_ES2.docx")
    p = pdf("out/Proyecto_de_Titulo_FlotaAgil_ES2.docx")
    pages2 = page_texts(p)
    # verificación de que los números no cambiaron
    bad = []
    for l, t, pg in res:
        if norm(t)[:45] not in pages2[pg - 1]:
            bad.append((t, pg))
    print("páginas:", len(pages2), "TOC:", toc_pages, "desajustes:", bad[:10])
