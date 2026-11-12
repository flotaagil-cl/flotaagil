# Pendientes de la revisión de los informes

Actualizado: 12/11/2026, tarde. Generadores en `docs/informes/generador/` (inf1.py = Informe 1, build_es2.py = Informe 2; guía en `docs/informes/guia/`).

## Estado: los 17 pendientes del 12/11 están resueltos

Ambos informes generan con la revisión automática en **0 errores y 0 avisos** (Informe 1: 60 páginas; Informe 2: 160 páginas; combinado: 220).

| # | Pendiente | Cómo quedó |
|---|---|---|
| 1 | Convenio por link y pasajero sin cuenta | BPMN P1 y P1.1 (Crear y habilitar la cuenta), contexto, CU-05/06/12/13, HU-11/19/20/25/34, RN-07, diccionario y máquina de estados (PENDIENTE_CONFIRMACION solo para reservas anteriores a CC-18). La regla del link admite la sección 1.3 (registro de cambios). |
| 2 | Pruebas antiguas en el Anexo P | Tabla del repositorio al corte: 445 archivos, 56.953 líneas, 2.116 pruebas (1.255 · 772 · 89), 202 commits en main. Evolución de pruebas cierra en HU-31 a HU-45. |
| 3 | Avance y cronograma sin CC-16–18 | Gantt con EF2 (HU-31, HU-32, CP-14) y cambios del cliente (HU-33 a HU-45) terminados; plan de fusión reemplazado por la migración (DC-49) e integración en main; Anexo N al día (Flotaagil-CL, ruleset sin excepciones). |
| 4 | Presupuesto $14.498.000 vs $14.047.000 | Explicado en ambos informes (AWS definido y cuotas de prueba conocidas). |
| 5 | Restos ES2 | Sin «22 entidades», «30 decisiones» ni ghcr.io/flotaagil/. |
| 6 | Capturas del trabajo nuevo | 7 figuras nuevas en el Anexo P (cierre de caja, convenio en revisión, usuarios, portal en escritorio y tres montajes del celular). |
| 7 | Matriz de metodología en el Informe 1 | Tabla 24 con los cinco criterios y el puntaje 4,65. |
| 8 | Ley 21.719 | «entra en vigencia el 1 de diciembre de 2026». |
| 9 | APA del Informe 1 | Ley 18.490 (BCN, 1986) referenciada; AWS 2026a/2026b e ISO 29119-3 citadas; PMI con abreviatura en la primera cita. |
| 10 | Medias páginas antes de tablas apaisadas | Normativa y capacidades diferenciadoras pasan a vertical. |
| 11 | Velocidad del Sprint 4 | Explicada en 7.1 (cambios absorbidos, reutilización, sin deuda). |
| 12 | Anexo P, Sprint 4 | Tabla HU-31 a HU-45 (126 SP en el sprint), CP-14 cerrado, defectos nuevos, DC-01 a DC-50, pendientes a producción al día (SES, PR-15). |
| 13 | DC-47 «un solo integrante» | Redacción neutra. |
| 14 | CP y trazabilidad HU-33–44 | CP-38 a CP-45 y trazabilidad hasta HU-45. |
| 15 | Trazabilidad del Informe 1 | OE-01 con filas; nota sobre CP-xx (ISO 29119-3) y subprocesos P1.1, P2.1 y P3.2. |
| 16 | Referencias sin cita en el ES2 | Griffith (2017), Mell y Grance (2011) y PMI (2021) citados. |
| 17 | Páginas casi vacías del ES2 | Leyenda huérfana del BPMN P1 y fuente suelta de la tabla de normas corregidas. |

## Agregado el 12/11 (pedido de Renato)

- **2.1.9 y Anexo J:** evaluación a tres años con VAN, TIR y PRI desde el cliente y desde FlotaÁgil; tasa 12 % con sensibilidad 8 % y 15 %; cartera 1 → 4 → 11 (justificada en el texto). Cifras en `generador/data_van.py` (`python data_van.py` las imprime). TIR del cliente meta: «No significativa (inversión inicial mínima)». CC-19 como proyección v1.1 con su desarrollo (150 h, $2.294.000) en el año 1. Conclusión: viable condicionado a CC-19 y a alcanzar 11 clientes.
- **Escenario con CC-19:** operación del cliente actual $163.650 → $60.650 (−63 %), $88 → $20 por reserva, ahorro ≈ $1.236.000 al año, margen Avanzado ≈ 18 % → ≈ 70 %; los planes ya no incluyen WhatsApp.
- **Guía de estudio:** datos al día y preguntas 16 y 17 (rentabilidad y CC-19).

## Por revisar a mano antes de entregar

- Leer de corrido 2.1.9 (pp. 15–19 del ES2) y el Anexo P (pp. 143–160).
- Montajes del celular en el Anexo P: quedan una figura por página por su tamaño.
