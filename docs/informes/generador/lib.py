"""Constructor del informe sobre la plantilla oficial ES2."""
import copy
import re
import docx
from docx.shared import Pt, Cm, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
HDR_FILL = "1F3864"
ZEBRA = "F2F5F9"
BODY_COLOR = RGBColor(0x40, 0x40, 0x40)

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV"]


class Report:
    def __init__(self, template, cover):
        self.doc = docx.Document(template)
        self.body = self.doc.element.body
        self.fig_n = 0
        self.tab_n = 0
        self.refs = {}
        self.headings = []  # (nivel, texto)
        self.h1 = 0
        self.h2 = 0
        self.h3 = 0
        self.landscape = False
        self._bullet_num = self._make_bullet_numbering()
        self._fill_cover(cover)
        self._reset_body()

    # ------------------------------------------------------------------ portada
    def _fill_cover(self, c):
        el = list(self.body)[2]
        for p in el.iter(W + "p"):
            if p.find(".//" + W + "txbxContent") is not None:
                continue
            runs = [r for r in p.iter(W + "r") if r.find(W + "t") is not None]
            txt = "".join(r.find(W + "t").text or "" for r in runs)
            if txt.startswith("Asignatura"):
                self._append_run(p, runs[-1], c["carrera"], bold=False)
            elif txt.startswith("Sección"):
                self._append_run(p, runs[-1], c["seccion"], bold=False)
                self._append_run(p, runs[-1], "  ·  Sede: ", bold=True)
                self._append_run(p, runs[-1], c["sede"], bold=False)
            elif txt.startswith("Académico guía"):
                runs[-1].find(W + "t").text = " " + c["docente"]
            elif txt.startswith("Integrantes"):
                t = runs[-1].find(W + "t")
                t.text = " " + c["integrantes"]
                t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                self._unbold(runs[-1])
            elif txt.startswith("Fecha de entrega"):
                runs[-1].find(W + "t").text = "Fecha de entrega: "
                runs[-1].find(W + "t").set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                self._append_run(p, runs[-1], c["fecha"], bold=False)
                self._append_run(p, runs[-1], "  ·  " + c["version"], bold=False)
            elif txt.startswith("Nombre o título"):
                runs[0].find(W + "t").text = c["titulo"]
                for r in runs[1:]:
                    r.getparent().remove(r)

    def _unbold(self, r):
        rpr = r.find(W + "rPr")
        if rpr is not None:
            for tag in ("b", "bCs"):
                e = rpr.find(W + tag)
                if e is not None:
                    rpr.remove(e)

    def _append_run(self, p, model, text, bold=False, highlight=False):
        r = copy.deepcopy(model)
        t = r.find(W + "t")
        t.text = text
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        rpr = r.find(W + "rPr")
        if rpr is None:
            rpr = OxmlElement("w:rPr")
            r.insert(0, rpr)
        if not bold:
            for tag in ("b", "bCs"):
                e = rpr.find(W + tag)
                if e is not None:
                    rpr.remove(e)
        else:
            if rpr.find(W + "b") is None:
                rpr.append(OxmlElement("w:b"))
        if highlight:
            h = OxmlElement("w:highlight")
            h.set(qn("w:val"), "yellow")
            rpr.append(h)
        # insertar después del último run del párrafo
        last = [x for x in p if x.tag == W + "r"][-1]
        last.addnext(r)
        return r

    def _reset_body(self):
        kids = list(self.body)
        self.sectPr = kids[-1]
        for el in kids[5:-1]:
            self.body.remove(el)

    # ------------------------------------------------------------------ numeración viñetas
    def _make_bullet_numbering(self):
        numbering = self.doc.part.numbering_part.element
        abs_ids = [int(a.get(qn("w:abstractNumId"))) for a in numbering.findall(qn("w:abstractNum"))]
        num_ids = [int(n.get(qn("w:numId"))) for n in numbering.findall(qn("w:num"))]
        aid = max(abs_ids) + 1
        nid = max(num_ids) + 1
        a = OxmlElement("w:abstractNum")
        a.set(qn("w:abstractNumId"), str(aid))
        ml = OxmlElement("w:multiLevelType"); ml.set(qn("w:val"), "hybridMultilevel"); a.append(ml)
        for lvl, (sym, ind) in enumerate([("•", 567), ("–", 1000)]):
            l = OxmlElement("w:lvl"); l.set(qn("w:ilvl"), str(lvl))
            for tag, val in (("w:start", "1"), ("w:numFmt", "bullet"), ("w:lvlText", sym), ("w:lvlJc", "left")):
                e = OxmlElement(tag); e.set(qn("w:val"), val); l.append(e)
            ppr = OxmlElement("w:pPr"); ind_e = OxmlElement("w:ind")
            ind_e.set(qn("w:left"), str(ind)); ind_e.set(qn("w:hanging"), "283"); ppr.append(ind_e); l.append(ppr)
            rpr = OxmlElement("w:rPr"); f = OxmlElement("w:rFonts")
            f.set(qn("w:ascii"), "Calibri"); f.set(qn("w:hAnsi"), "Calibri"); rpr.append(f); l.append(rpr)
            a.append(l)
        first_num = numbering.find(qn("w:num"))
        first_num.addprevious(a)
        n = OxmlElement("w:num"); n.set(qn("w:numId"), str(nid))
        an = OxmlElement("w:abstractNumId"); an.set(qn("w:val"), str(aid)); n.append(an)
        numbering.append(n)
        return nid

    # ------------------------------------------------------------------ utilidades de párrafo
    def _new_p(self, style=None):
        p = self.doc.add_paragraph(style=style)
        if getattr(self, "_pb_next", False):
            p.paragraph_format.page_break_before = True
            self._pb_next = False
        return p

    def _drop_trailing_empty(self):
        prev = list(self.body)[-2] if len(self.body) > 1 else None
        if prev is not None and prev.tag == W + "p" and prev.find(W + "pPr/" + W + "sectPr") is None:
            has_text = "".join(t.text or "" for t in prev.iter(W + "t")).strip()
            if not has_text and prev.find(".//" + W + "drawing") is None and prev.find(".//" + W + "br") is None:
                nxt_tbl = True
                self.body.remove(prev)

    def _no_num(self, p, outline=None):
        ppr = p._p.get_or_add_pPr()
        numpr = OxmlElement("w:numPr")
        il = OxmlElement("w:ilvl"); il.set(qn("w:val"), "0")
        ni = OxmlElement("w:numId"); ni.set(qn("w:val"), "0")
        numpr.append(il); numpr.append(ni)
        ppr.insert(1 if ppr.find(qn("w:pStyle")) is not None else 0, numpr)
        if outline is not None:
            ol = OxmlElement("w:outlineLvl"); ol.set(qn("w:val"), str(outline))
            ppr.append(ol)

    def runs(self, p, text, size=None, color=None, italic=False, bold=False):
        """Admite **negrita**, *cursiva* y [[marcador amarillo]]."""
        parts = re.split(r"(\*\*.+?\*\*|\[\[.+?\]\]|(?<![\w*])\*[^*\s][^*]*?\*(?![\w*]))", text)
        for part in parts:
            if not part:
                continue
            b, it, hl = bold, italic, False
            if part.startswith("**") and part.endswith("**"):
                part = part[2:-2]; b = True
            elif part.startswith("[[") and part.endswith("]]"):
                part = part[2:-2]; hl = True
            elif part.startswith("*") and part.endswith("*") and len(part) > 2:
                part = part[1:-1]; it = True
            r = p.add_run(part)
            r.bold = b or None
            r.italic = it or None
            if size:
                r.font.size = Pt(size)
            if color:
                r.font.color.rgb = color
            if hl:
                rpr = r._r.get_or_add_rPr()
                h = OxmlElement("w:highlight"); h.set(qn("w:val"), "yellow"); rpr.append(h)
        return p

    def _spacing(self, p, before=0, after=6, line=1.15, keep_next=False):
        pf = p.paragraph_format
        pf.space_before = Pt(before)
        pf.space_after = Pt(after)
        pf.line_spacing = line
        if keep_next:
            pf.keep_with_next = True

    # ------------------------------------------------------------------ títulos
    def H1(self, text, page_break=True):
        self.h1 += 1; self.h2 = 0; self.h3 = 0
        label = f"{ROMAN[self.h1 - 1]}. {text}"
        if page_break and self.h1 > 1:
            self.page_break()
        p = self._new_p("Título1")
        self._no_num(p, outline=0)
        self.runs(p, label)
        self._spacing(p, before=6, after=10, keep_next=True)
        self.headings.append((1, label))
        return p

    def H2(self, text, numbered=True):
        self.h2 += 1; self.h3 = 0
        label = f"{self.h1}.{self.h2} {text}" if numbered else text
        p = self._new_p("Subtitulo1")
        self._no_num(p, outline=1)
        p.paragraph_format.left_indent = Cm(0)
        r = p.add_run(label); r.bold = True; r.font.size = Pt(12.5)
        self._spacing(p, before=12, after=6, keep_next=True)
        self.headings.append((2, label))
        return p

    def H3(self, text):
        self.h3 += 1
        label = f"{self.h1}.{self.h2}.{self.h3} {text}"
        p = self._new_p("Subtitulo2")
        self._no_num(p, outline=2)
        p.paragraph_format.left_indent = Cm(0)
        r = p.add_run(label); r.bold = True; r.italic = True; r.font.size = Pt(11.5)
        self._spacing(p, before=10, after=4, keep_next=True)
        self.headings.append((3, label))
        return p

    def H4(self, text):
        p = self._new_p("Estilo4")
        r = p.add_run(text); r.bold = True
        self._spacing(p, before=8, after=3, keep_next=True)
        return p

    # ------------------------------------------------------------------ cuerpo
    def P(self, text, after=6, keep_next=False, align=None, size=None, italic=False):
        p = self._new_p("Estilo4")
        self.runs(p, text, size=size, italic=italic)
        self._spacing(p, after=after, keep_next=keep_next)
        if align == "center":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        return p

    def bullets(self, items, level=0, after=2):
        for i, it in enumerate(items):
            p = self._new_p("Estilo4")
            ppr = p._p.get_or_add_pPr()
            numpr = OxmlElement("w:numPr")
            il = OxmlElement("w:ilvl"); il.set(qn("w:val"), str(level))
            ni = OxmlElement("w:numId"); ni.set(qn("w:val"), str(self._bullet_num))
            numpr.append(il); numpr.append(ni)
            ppr.insert(1, numpr)
            self.runs(p, it)
            self._spacing(p, after=after if i < len(items) - 1 else 6)
        return

    def page_break(self):
        prev = list(self.body)[-2] if len(self.body) > 1 else None
        if prev is not None and prev.tag == W + "p" and prev.find(W + "pPr/" + W + "sectPr") is not None:
            return
        self._drop_trailing_empty()
        self._pb_next = True

    # ------------------------------------------------------------------ secciones
    def _sect_break(self, landscape_next):
        """Cierra la sección actual con la orientación vigente; la siguiente usa landscape_next."""
        self._pb_next = False
        p = self._new_p("Estilo4")
        self._spacing(p, after=0)
        sp = copy.deepcopy(self.sectPr)
        cur_land = self.landscape
        first = not hasattr(self, "_n_sections")
        if not first:
            for tag in ("headerReference", "footerReference", "titlePg"):
                for e in sp.findall(W + tag):
                    sp.remove(e)
        self._n_sections = getattr(self, "_n_sections", 0) + 1
        self._orient(sp, cur_land)
        p._p.get_or_add_pPr().append(sp)
        self.landscape = landscape_next

    def _orient(self, sp, land):
        pg = sp.find(W + "pgSz")
        w, h = 12240, 15840
        if land:
            pg.set(qn("w:w"), str(h)); pg.set(qn("w:h"), str(w)); pg.set(qn("w:orient"), "landscape")
        else:
            pg.set(qn("w:w"), str(w)); pg.set(qn("w:h"), str(h))
            if pg.get(qn("w:orient")) is not None:
                del pg.attrib[qn("w:orient")]

    def landscape_on(self):
        self._sect_break(True)

    def landscape_off(self):
        self._sect_break(False)

    def finalize_sections(self):
        if hasattr(self, "_n_sections"):
            for tag in ("headerReference", "footerReference", "titlePg"):
                for e in self.sectPr.findall(W + tag):
                    self.sectPr.remove(e)
        self._orient(self.sectPr, self.landscape)

    @property
    def text_width(self):
        return Cm(22.9) if self.landscape else Cm(16.6)

    # ------------------------------------------------------------------ figuras y tablas
    def figure(self, path, key, caption, width_cm=None, source="Elaboración propia."):
        self.fig_n += 1
        self.refs["F:" + key] = str(self.fig_n)
        p = self._new_p("Estilo4")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        w = Cm(width_cm) if width_cm else self.text_width
        p.add_run().add_picture(path, width=w)
        self._spacing(p, before=4, after=2, keep_next=True)
        c = self._new_p("PIE DE FOTO")
        self.runs(c, f"**Figura {self.fig_n}.** *{caption}.* {source}", size=9)
        self._spacing(c, after=10)
        return p

    def table(self, key, caption, headers, rows, widths, font=8.5, source="Elaboración propia.", header_fill=HDR_FILL,
              first_col_bold=False, zebra=True, align_center_cols=()):
        self.tab_n += 1
        self.refs["T:" + key] = str(self.tab_n)
        cm = getattr(self, "cellremap", None)
        if cm:
            cols = [i for i, h in enumerate(headers) if h in ("Sección", "Respaldo", "Dónde", "Citado en")]
            if cols:
                rows = [tuple(cm(c) if i in cols and isinstance(c, str) else c for i, c in enumerate(row)) for row in rows]
        cap = self._new_p("PIE DE FOTO")
        cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
        self.runs(cap, f"**Tabla {self.tab_n}.** *{caption}*", size=9.5)
        self._spacing(cap, before=6, after=3, keep_next=True)
        t = self.doc.add_table(rows=1 + len(rows), cols=len(headers))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        self._table_borders(t)
        tw = sum(widths)
        scale = (self.text_width.cm) / tw if tw > self.text_width.cm else 1
        widths = [w * scale for w in widths]
        tbl = t._tbl
        tblPr = tbl.tblPr
        lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
        for i, h in enumerate(headers):
            c = t.rows[0].cells[i]
            self._cell(c, h, font, bold=True, color=RGBColor(255, 255, 255), fill=header_fill)
        trPr = t.rows[0]._tr.get_or_add_trPr()
        th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
        for ri, row in enumerate(rows):
            for ci, val in enumerate(row):
                c = t.rows[ri + 1].cells[ci]
                fill = ZEBRA if (zebra and ri % 2 == 1) else None
                self._cell(c, str(val), font, bold=(first_col_bold and ci == 0), fill=fill,
                           center=(ci in align_center_cols))
            cant = OxmlElement("w:cantSplit")
            t.rows[ri + 1]._tr.get_or_add_trPr().append(cant)
        if len(rows) <= 8:
            for row in t.rows[:-1]:
                for c in row.cells:
                    for q in c.paragraphs:
                        q.paragraph_format.keep_with_next = True
        for row in t.rows:
            for i, c in enumerate(row.cells):
                c.width = Cm(widths[i])
        grid = tbl.tblGrid
        for i, gc in enumerate(grid.findall(qn("w:gridCol"))):
            gc.set(qn("w:w"), str(int(widths[i] * 567)))
        if source:
            s = self._new_p("PIE DE FOTO")
            s.alignment = WD_ALIGN_PARAGRAPH.LEFT
            self.runs(s, f"*Fuente:* {source}", size=8.5)
            self._spacing(s, before=2, after=10)
        else:
            s = self._new_p("Estilo4"); self._spacing(s, after=6)
        return t

    def kv_table(self, key, caption, pairs, widths=(4.2, 12.4), font=8.5, source="Elaboración propia.", header=None):
        headers = header or ["Campo", "Detalle"]
        return self.table(key, caption, headers, pairs, list(widths), font=font, source=source, first_col_bold=True)

    def _cell(self, c, text, font, bold=False, color=None, fill=None, center=False):
        c.text = ""
        lines = text.split("\n")
        p = c.paragraphs[0]
        for li, line in enumerate(lines):
            if li > 0:
                p = c.add_paragraph()
            bullet = line.startswith("• ")
            self.runs(p, line, size=font, color=color, bold=bold)
            pf = p.paragraph_format
            pf.space_after = Pt(1); pf.space_before = Pt(0); pf.line_spacing = 1.0
            if bullet:
                pf.left_indent = Cm(0.3); pf.first_line_indent = Cm(-0.3)
            if center:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if fill:
            tcPr = c._tc.get_or_add_tcPr()
            shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill)
            tcPr.append(shd)
        tcPr = c._tc.get_or_add_tcPr()
        mar = OxmlElement("w:tcMar")
        for side, v in (("top", 30), ("bottom", 30), ("left", 70), ("right", 70)):
            e = OxmlElement(f"w:{side}"); e.set(qn("w:w"), str(v)); e.set(qn("w:type"), "dxa"); mar.append(e)
        tcPr.append(mar)

    def _table_borders(self, t):
        tblPr = t._tbl.tblPr
        b = OxmlElement("w:tblBorders")
        for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement(f"w:{side}")
            e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:space"), "0"); e.set(qn("w:color"), "A6AEB8")
            b.append(e)
        tblPr.append(b)

    # ------------------------------------------------------------------ índice
    def toc(self, entries):
        """entries: [(nivel, texto, pagina)]"""
        p = self._new_p("Estilo4")
        r = p.add_run("Contenido"); r.bold = True; r.font.size = Pt(14); r.font.color.rgb = RGBColor(0x40, 0x40, 0x40)
        self._spacing(p, after=10)
        first = True
        paras = []
        for lvl, text, page in entries:
            st = {1: "toc 1", 2: "toc 2", 3: "toc 3"}[lvl]
            q = self._new_p(st)
            if first:
                self._fld(q, "begin"); self._instr(q, ' TOC \\o "1-3" \\h \\z \\u '); self._fld(q, "separate")
                first = False
            rr = q.add_run(text)
            if lvl == 1:
                rr.bold = True
            q.add_run("\t" + str(page))
            pf = q.paragraph_format
            pf.space_after = Pt(2 if lvl > 1 else 4)
            tabs = pf.tab_stops
            from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER
            tabs.add_tab_stop(Cm(16.6), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
            if lvl == 3:
                pf.left_indent = Cm(1.0)
            paras.append(q)
        self._fld(paras[-1], "end")
        self.page_break()

    def _fld(self, p, kind):
        r = OxmlElement("w:r"); f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), kind); r.append(f)
        p._p.append(r)

    def _instr(self, p, text):
        r = OxmlElement("w:r"); i = OxmlElement("w:instrText"); i.set(qn("xml:space"), "preserve"); i.text = text; r.append(i)
        p._p.append(r)

    # ------------------------------------------------------------------ cierre
    def resolve_refs(self):
        pat = re.compile(r"(Tablas? |Figuras? )?\{([FT]):([\w\-]+)(\|n)?\}")

        def rep(m):
            num = self.refs.get(m.group(2) + ":" + m.group(3), "??" + m.group(3))
            if m.group(1):
                return m.group(1) + num
            if m.group(4):
                return num
            return ("Tabla " if m.group(2) == "T" else "Figura ") + num
        remap = getattr(self, "remap", None)
        for t in self.body.iter(W + "t"):
            if t.text and remap:
                t.text = remap(t.text)
            if t.text and "{" in t.text:
                t.text = pat.sub(rep, t.text)

    PPR_ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr", "suppressLineNumbers",
                 "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct", "topLinePunct", "autoSpaceDE",
                 "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents",
                 "suppressOverlap", "jc", "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle",
                 "rPr", "sectPr", "pPrChange"]
    TBLPR_ORDER = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize", "tblW", "jc",
                   "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription"]
    TCMAR_ORDER = ["top", "start", "left", "bottom", "end", "right"]

    def _reorder(self, el, order):
        kids = list(el)
        def k(e):
            n = e.tag.split("}")[1]
            return order.index(n) if n in order else len(order)
        kids_sorted = sorted(kids, key=k)
        if kids_sorted != kids:
            for e in kids:
                el.remove(e)
            for e in kids_sorted:
                el.append(e)

    def normalize(self):
        for e in self.body.iter(W + "pPr"):
            self._reorder(e, self.PPR_ORDER)
        for e in self.body.iter(W + "tblPr"):
            self._reorder(e, self.TBLPR_ORDER)
        for e in self.body.iter(W + "tcMar"):
            self._reorder(e, self.TCMAR_ORDER)
        numbering = self.doc.part.numbering_part.element
        cl = numbering.find(qn("w:numIdMacAtCleanup"))
        if cl is not None:
            numbering.remove(cl)
            numbering.append(cl)

    def save(self, path):
        self._drop_trailing_empty()
        self.normalize()
        self.finalize_sections()
        self.resolve_refs()
        self.doc.save(path)
