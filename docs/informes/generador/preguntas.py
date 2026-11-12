import docx
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

NAVY = "1F3864"
SECCIONES = [
    ("A. Críticas: pueden cambiar el capítulo VII o la nota", [
        ("¿Cuánto se ha construido realmente? ¿Hay código, qué historias están terminadas y cuántos SP por sprint?",
         "Tabla 48 (cap. VII) dice «Planificado» en los sprints 1 a 4 y el texto mantiene el plan de 16 semanas. Si la ES2 se entrega en la semana 14, el profe verá que los sprints 1 a 3 ya debían estar hechos. Hay que reportar el avance real o re-planificar fechas."),
        ("Si no hay código aún: ¿mantenemos las 16 semanas (y explicamos el atraso con medidas correctivas) o movemos las fechas de los sprints?",
         "Cap. VII completo, Figura 16 (Gantt), Tabla 47 y conclusiones. Hoy el informe dice que las fechas no cambian."),
        ("¿Se hizo la prueba de concepto del GPS en segundo plano (hito H-3)? ¿Con qué resultado y en qué teléfonos?",
         "Tabla 48 la muestra «reprogramada como primera tarea del Sprint 1». Si ya se hizo, conviene decirlo: es el riesgo más alto (R-01)."),
        ("¿Existen los prototipos de pantallas (E-06)? ¿En Figma? ¿Se mostraron al cliente?",
         "Tabla 48 dice que se validan en la Sprint Review 1. Si existen, se pueden agregar como anexo o figura."),
        ("Fecha exacta de entrega de la ES2.",
         "Portada (hoy dice «Noviembre de 2026») y fecha de actualización del cronograma."),
        ("¿El profe revisó el cronograma? ¿Cuándo y qué acordaron?",
         "Ítem 17.10 de la pauta. Hoy el informe dice que se valida en la retroalimentación de la semana 13."),
        ("¿Les parece bien que Juan Pérez figure como «integrante simulado» que hace de Product Owner? ¿Así lo planteó el profe?",
         "Tablas 12 y 13, 2.1.7. En la portada solo están ustedes dos."),
    ]),
    ("B. Entrevista del aeropuerto y aprobación de cambios", [
        ("Entrevista donde surgió el foco aeropuerto (EV-08): fecha, lugar o modalidad, participantes y duración.",
         "Anexo B, Tabla 53. Hoy solo dice «Diseño de la Unidad 2, posterior al 28/08/2026» y «administrador y equipo»."),
        ("¿Qué respaldo hay de esa entrevista (notas, correo, audio autorizado)?",
         "Anexo B. Saqué la fila «Respaldo» porque no sé si existe; si hay algo, se agrega."),
        ("¿Los hallazgos y acuerdos de la Tabla 53 reflejan lo que dijo el cliente? Los redacté a partir de lo que conversamos.",
         "Anexo B. Si algo no lo dijo el cliente, hay que corregirlo."),
        ("¿El cliente aprobó de verdad los cambios CC-01 (WhatsApp), CC-02 (aeropuerto) y CC-06 (99,0 %)? ¿Cuándo?",
         "Tabla 54 dice «PO + cliente». Si solo lo decidieron ustedes, cambiar a «PO»."),
    ]),
    ("C. Operación del cliente (supuestos que hoy son parámetros)", [
        ("¿La empresa opera 24/7? Si no, ¿qué horario?",
         "SLA (4.2), ventana de mantenimiento, guardia y Tabla 6."),
        ("Margen de recogida después de que aterriza el vuelo: ¿20 min nacional y 35 internacional está bien?",
         "RN-17, HU-27, P2.2."),
        ("¿Cuánto tiempo fuera de la zona del aeropuerto saca a un conductor de la fila? (supuse 10 min)",
         "RN-16, HU-29, P2.1, CP-20."),
        ("¿Cuánto espera el conductor al pasajero antes de declarar no presentación? (supuse 15 min)",
         "P3, CU-11, máquina de estados."),
        ("¿Dónde esperan exactamente los conductores en el aeropuerto (zona autorizada)? ¿Es solo el aeropuerto de Santiago?",
         "Polígono de la geocerca (Tabla 6)."),
        ("¿Qué porcentaje de los viajes son desde o hacia el aeropuerto? (supuse 30 % a 40 %)",
         "Costo de la API de vuelos (Anexo H)."),
        ("¿Qué parte de los pasajeros escribe primero por WhatsApp? (supuse la mitad)",
         "Costo de WhatsApp (≈ $104.000/mes, Tabla 14 y Anexo H)."),
        ("¿La tarifa promedio por viaje es cercana a $12.000? (la calculé del Informe 1: $2.196.000 ÷ 183)",
         "Beneficios económicos (2.1.9)."),
        ("¿Los conductores tienen contrato de trabajo con la empresa o son independientes?",
         "Normativa del GPS: si son dependientes aplica el Reglamento Interno y el Dictamen DT 148/2022; si no, solo el consentimiento (Ley 21.719)."),
        ("¿La empresa tiene un número de WhatsApp que se pueda pasar a la API y una cuenta de Meta Business con RUT para verificar?",
         "Riesgo R-12 y puesta en marcha (6.1.3)."),
        ("¿Todos los conductores usan Android 10 o superior? ¿Alguno usa iPhone?",
         "RNF-12; la app es solo Android."),
        ("¿El administrador puede asistir a una revisión cada dos semanas y a la UAT de la semana 16?",
         "Factibilidad implementativa (2.1.10) y SLA."),
    ]),
    ("D. Cuentas, dominio y precios", [
        ("¿Tienen cuenta AWS (créditos de estudiante o propia)? ¿Les sirve la región us-east-1?",
         "Infraestructura (3.6). En la matriz cloud puse «mayor familiaridad del equipo» con AWS: confirmar."),
        ("¿Está registrado el dominio flotaagil.cl? El informe usa app.flotaagil.cl y soporte@flotaagil.cl.",
         "Topología, SLA, puesta en marcha."),
        ("¿Ya crearon cuenta en Twilio (sandbox) y en AeroAPI?",
         "Factibilidad técnica (2.1.8)."),
        ("Plan Básico de $189.000: ¿es neto o con IVA? ¿Qué precio tiene Flota+? ¿Cuánto cuesta la implementación y la suscripción de soporte?",
         "Factibilidad económica: hoy solo se usa el Básico."),
        ("¿Les acomoda el tipo de cambio de $950 por dólar o prefieren otro?",
         "Todos los costos en pesos."),
    ]),
    ("E. Equipo y planificación", [
        ("¿Siguen pudiendo dedicar 25 horas semanales cada uno?",
         "Capacidad de 45 SP por sprint."),
        ("¿Están de acuerdo con el reparto de historias (89 SP cada uno)? Carlos: backend, integraciones e infraestructura; Renato: interfaz y app.",
         "Tabla 47 y Anexo A."),
        ("¿Es realista una guardia semanal rotativa con respuesta de 30 min durante la marcha blanca?",
         "Gestión de incidentes (6.3.3) y SLA."),
    ]),
    ("F. Decisiones que tomé yo y deben confirmar", [
        ("Eliminé HU-23 (contacto directo con el conductor) y bajé HU-04 de 13 a 8 SP para llegar a 178 SP.",
         "Backlog, Tabla 3, Anexo A."),
        ("WhatsApp vía Twilio, dejando la API directa de Meta como ahorro futuro (≈ $84.000/mes).",
         "Tabla 10 y factibilidad económica."),
        ("SLA de 99,0 % con crédito de 10 % bajo 99,0 % y 25 % bajo 97,0 % de la mensualidad.",
         "Tabla 31. Es una propuesta comercial; si no quieren ofrecer créditos, se quita."),
        ("Consultas de vuelos cada 30 min y cada 10 min en la última hora.",
         "HU-27, P2.2, costo de la API."),
        ("La APK se distribuye directamente (sin Google Play) mientras se tramita el permiso de ubicación en segundo plano.",
         "Riesgo R-14 y puesta en marcha."),
    ]),
]


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def borders(t):
    tblPr = t._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:space"), "0"); e.set(qn("w:color"), "A6AEB8")
        b.append(e)
    look = tblPr.find(qn("w:tblLook"))
    if look is not None:
        look.addprevious(b)
    else:
        tblPr.append(b)


d = docx.Document()
sec = d.sections[0]
sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)
for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, m, Cm(2.0))
st = d.styles["Normal"]
st.font.name = "Calibri"; st.font.size = Pt(10.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")

p = d.add_paragraph(); r = p.add_run("FlotaÁgil · Informe 2 (ES2)"); r.bold = True; r.font.size = Pt(16); r.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
p = d.add_paragraph(); r = p.add_run("Preguntas pendientes para cerrar el informe"); r.font.size = Pt(13); r.font.color.rgb = RGBColor(0x40, 0x40, 0x40)
p = d.add_paragraph("Cada pregunta indica dónde impacta en el informe. La columna «Respuesta» es para completarla entre Renato y Carlos. "
                    "Las del grupo A conviene resolverlas antes de entregar; el resto ya está cubierto en el informe con un supuesto razonable, "
                    "pero si la respuesta real es distinta hay que ajustar el texto indicado.")
p.paragraph_format.space_after = Pt(10)

n = 0
W = [Cm(0.9), Cm(6.6), Cm(5.6), Cm(4.4)]
for title, qs in SECCIONES:
    h = d.add_paragraph(); r = h.add_run(title); r.bold = True; r.font.size = Pt(12); r.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
    h.paragraph_format.space_before = Pt(12); h.paragraph_format.space_after = Pt(4); h.paragraph_format.keep_with_next = True
    t = d.add_table(rows=1, cols=4)
    borders(t)
    for i, txt in enumerate(["N°", "Pregunta", "Dónde impacta en el informe", "Respuesta"]):
        c = t.rows[0].cells[i]; c.text = ""
        rr = c.paragraphs[0].add_run(txt); rr.bold = True; rr.font.size = Pt(9.5); rr.font.color.rgb = RGBColor(255, 255, 255)
        shade(c, NAVY)
    trPr = t.rows[0]._tr.get_or_add_trPr(); th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    for q, imp in qs:
        n += 1
        row = t.add_row().cells
        for i, txt in enumerate([str(n), q, imp, ""]):
            row[i].text = ""
            rr = row[i].paragraphs[0].add_run(txt); rr.font.size = Pt(9.5)
            if i == 0:
                rr.bold = True
        cant = OxmlElement("w:cantSplit"); t.rows[-1]._tr.get_or_add_trPr().append(cant)
    for row in t.rows:
        for i, c in enumerate(row.cells):
            c.width = W[i]
    for i, gc in enumerate(t._tbl.tblGrid.findall(qn("w:gridCol"))):
        gc.set(qn("w:w"), str(int(W[i].cm * 567)))

z = d.settings.element.find(qn("w:zoom"))
if z is not None:
    z.set(qn("w:percent"), "100")
d.save("out/Preguntas_pendientes_Informe2_FlotaAgil.docx")
print(n, "preguntas")
