# Contexto para retomar los informes en una sesión nueva

Pegar o adjuntar este archivo al iniciar. Así no hace falta releer conversaciones largas.

**Proyecto:** FlotaÁgil, Proyecto de Título TIHI84 (INACAP La Granja). Equipo: Renato González, Carlos Ortiz; PO simulado Juan Pérez.
**Entregables:** Informe 1 corregido (formulación, plantilla U1), Informe 2 (ES2, plantilla U2, capítulos I a X), PDF combinado y guía de estudio.

**Dónde está todo (repo `C:\Users\renaa\Documents\PROYECTO DE TITULO GIT`):**
- `docs/informes/` generador, figuras, reglas de revisión y PDF (`README.md` explica cómo regenerar)
- `docs/informes/PENDIENTES_REVISION.md` correcciones pendientes por prioridad
- `docs/estado-para-informe.md` qué se construyó por HU (fuente para el Anexo P y la trazabilidad)
- `docs/informes/datos/datos.json` cifras oficiales (correr `extraer_datos.py` primero)
- `CLAUDE.md` reglas del proyecto; `docs/diccionario-cambios.md` CC y DC; `docs/backlog/backlog.json` backlog

**Reglas de los informes:**
- No mencionar herramientas de IA.
- Carlos figura como responsable de backend e infraestructura.
- Fechas según el calendario formal (semana 1 = 10/08/2026; corte de la ES2 = semana 14).
- Nada de datos personales ni credenciales reales.
- El profe pidió: diferenciación más allá de digitalizar, normativa del transporte, privacidad del GPS, BPMN con verbos en infinitivo y un solo evento de término, sin RACI, un solo proveedor cloud (AWS).

**Forma de trabajo:**
1. `python extraer_datos.py`
2. Corregir en los `.py` (no en Word)
3. `python inf1.py` y `python build_es2.py`. La revisión automática debe quedar sin errores.
4. Revisar visualmente las páginas tocadas.
