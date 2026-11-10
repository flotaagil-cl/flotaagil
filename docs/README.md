# docs/

Índice de la documentación de FlotaÁgil. La fuente de verdad es el Informe 2 (ES2).

| Ruta | Contenido |
|---|---|
| [`backlog/backlog.json`](backlog/backlog.json) | Product backlog: 30 HU + H-3 (210 SP); HU-31 a HU-35 por CC-12, CC-15 y CC-16 |
| [`diccionario-datos.md`](diccionario-datos.md) | Diccionario de datos (Anexo D del Informe 2): fuente de los modelos del backend |
| [`diccionario-cambios.md`](diccionario-cambios.md) | Agregados y desvíos respecto del Anexo D, para actualizar el informe |
| [`sprint0.md`](sprint0.md) | Instrucciones del Sprint 0 (ecosistema GitHub) |
| [`evidencias/`](evidencias/) | Evidencias de ejecución de casos de prueba (CP-xx) |

Se agregarán: informes, registro de decisiones, informe de la PoC de GPS (H-3), runbook y resultados de pruebas de carga y seguridad.

## Pendientes de configuración

- [ ] **Quitar el bypass temporal del ruleset «Proteger main»** (rol de administrador de la organización, modo «solo pull request») cuando Carlos Ortiz se sume al repositorio. Desde ese momento todo PR requiere la aprobación del otro integrante.
- [ ] Descomentar en `.github/CODEOWNERS` las líneas de Carlos para `backend/` e `infra/`.
- [ ] Activar en `.github/dependabot.yml` las entradas `pip`, `npm` y `docker` cuando existan los manifiestos.
