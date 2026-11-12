# Informes del Proyecto de Título (generador)

Fuente de los dos informes y de la guía. Los PDF **se generan desde aquí**: no se editan a mano en Word,
porque el próximo build pisaría el cambio. Para corregir algo, se cambia el `.py` que lo contiene y se vuelve a generar.

## Estructura

```
generador/      scripts Python que arman los .docx y los convierten a PDF
  lib.py        motor: portada, títulos, tablas, figuras, índice y numeración de Tabla/Figura
  inf1.py       Informe 1 (formulación, plantilla Unidad 1) → out/Informe1_FlotaAgil_corregido.pdf
  build_es2.py  Informe 2 (ES2, plantilla Unidad 2: capítulos I a X) → out/Informe2_ES2_FlotaAgil.pdf
  sec0..sec4.py, sec_impl.py, annex.py   contenido por capítulo (los usa build_es2 y en parte inf1)
  data_*.py, datamodel.py               datos: backlog, casos de uso, pruebas, modelo de datos
  bpmn_*.py, uml_*.py, draw_er.py, gantt_*.py, infra_diagrams.py   generan las figuras en fig/
  template.docx  plantilla INACAP (portada, estilos, pie de página)
  fig/           figuras ya generadas (diagramas y capturas)
recursos/inf1img/   4 imágenes del Informe 1 original (AS-IS de aplicaciones, Ishikawa, poder-interés, Gantt base)
guia/               guía de estudio (HTML → PDF con Playwright) y sus fuentes tipográficas
entregables/        últimos PDF generados (12/11/2026)
PENDIENTES_REVISION.md   17 correcciones pendientes, por prioridad
```

## Requisitos

- Python 3.12 y `pip install -r requirements.txt`
- LibreOffice (para convertir .docx a PDF)
- Poppler (`pdfinfo` y `pdftotext`), para calcular las páginas del índice
- Para la guía: Node y `npm install playwright` (con Chromium)
- Graphviz (`dot`) solo si se regenera el modelo de datos (`draw_er.py`)

## Cómo generar

```bash
cd generador
python extraer_datos.py # 1) lee el repo y actualiza ../datos/datos.json (HU, SP, DC, entidades, pruebas)
python inf1.py          # 2) Informe 1 (dos pasadas para el índice); revisa antes de crear el PDF
python build_es2.py     # Informe 2
# PDF combinado (Poppler):
pdfunite out/Informe1_FlotaAgil_corregido.pdf out/Informe2_ES2_FlotaAgil.pdf out/Informes_1_y_2_FlotaAgil.pdf
cd ../guia && node r.js # guía
```

Si cambia un diagrama: ejecutar su script (por ejemplo `python bpmn_p1.py`) antes del build.

## Revisión automática

`inf1.py` y `build_es2.py` ejecutan `revisar.py` sobre el .docx antes de crear el PDF. Si encuentra errores,
**no genera el PDF** (se puede forzar con `--forzar`). Revisa:

- frases prohibidas o desactualizadas (menciones de IA, convenio por link, pedido sin cuenta, cifras viejas…),
  configurables en `revisar_reglas.json`, con las secciones donde sí se permiten (por ejemplo el registro de cambios);
- tablas o figuras sin resolver (`{T:…}`, `??`);
- cifras contra `datos/datos.json`: entidades, última DC, total de DC y total de pruebas;
- referencias de la lista que no se citan en el texto (aviso).

También se puede correr sola: `python revisar.py out/Informe2_ES2_FlotaAgil.docx`.
Cuando aparezca un error nuevo que se repita, agrégalo como regla en `revisar_reglas.json`.

## Datos

- `datos/datos.json`: lo genera `extraer_datos.py`; no se edita a mano.
- `datos/pruebas.json`: conteo real de pruebas; lo actualiza quien corre las suites completas.
- `../estado-para-informe.md`: una fila por HU terminada con lo que el informe necesita (lo mantiene Claude Code).

## Reglas del contenido

- No mencionar herramientas de IA en los entregables.
- Carlos figura como responsable de backend e infraestructura.
- Fechas según el calendario formal de 16 semanas (semana 1 = 10/08/2026).
- Datos de prueba siempre sintéticos; nada de credenciales ni datos personales reales.
