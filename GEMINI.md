# GEMINI.md — contexto del agente para FlotaÁgil

Archivo versionado en la raíz del repositorio. Se carga al abrir cada sesión.

## Reglas del proyecto (obligatorias)

**Lee `CLAUDE.md` al iniciar cada sesión** (y `GEMINI.local.md` si existe en el equipo para los detalles locales de entorno). Todo lo que define `CLAUDE.md` es de cumplimiento obligatorio, en particular:

- **Arquitectura y stack:** Django 5.2 + DRF + GeoDjango, Channels/Daphne, Celery, PostgreSQL 16 + PostGIS, Redis; web en React + Vite; app del conductor en React + Capacitor (solo Android).
- **Dominio en español:** modelos y tablas según el diccionario de datos (singular: `Viaje`, `Conductor`); código y comentarios en español salvo términos técnicos estándar. Reglas de negocio RN-01…RN-18 y estados del viaje tal como están en `CLAUDE.md`. Valores supuestos van como parámetros configurables por empresa, nunca fijos.
- **Git:**
  - Nunca push directo a `main`.
  - Ramas `feat/…`, `fix/…`, `chore/…`, `docs/…`, `test/…`; una por HU o tarea.
  - Commits y título de PR en Conventional Commits en español con scope (`backend`, `web`, `app`, `infra`, `docs`, `ci`, `deps`).
  - PR con el check `ci` en verde y fusión *squash* (sin borrar la rama); `Closes #N` / `Refs #N` según corresponda.
- **Calidad:** Ruff y Bandit (backend), ESLint (web y app), pytest + coverage ≥ 70 % en módulos de negocio, Vitest en web y app. La definición de terminado de `CLAUDE.md` aplica a todo cambio.
- **Seguridad y datos:** nunca subir secretos (`.env` ignorado, ejemplos en `.env.example`); datos de prueba siempre sintéticos.
- **Proceso:** antes de crear o cambiar algo grande, explica el plan y espera confirmación. Si una decisión no está en el informe, pregunta en vez de suponer. Alcance congelado desde el 12/11/2026: lo nuevo va como solicitud de cambio (CC).

Si algo de este archivo choca con `CLAUDE.md`, manda `CLAUDE.md`.

## Flujo de trazabilidad y entrega (Definition of Done)

Todo cambio en el código, diseño o documentación del repositorio sigue estos 5 pasos obligatorios:

1. **Trazabilidad previa:** Antes de crear un issue nuevo o abrir una rama, identifica a qué Historia de Usuario (`HU-XX`) o Solicitud de Cambio (`CC-XX`) corresponde la tarea, manteniendo la convención del tablero `FlotaÁgil — Backlog`:
   - Consulta `"C:\Program Files\GitHub CLI\gh.exe" issue list --state open` y revisa `CLAUDE.md` y `docs/estado-para-informe.md` para identificar a qué `HU-XX` o `CC-XX` existente pertenece el módulo afectado.
   - Si ya existe un issue abierto para esa historia/cambio, enlaza el trabajo a ese número (`Refs #<N>` o `Closes #<N>`) sin duplicar tarjetas.
   - Si no existe y es una mejora sobre alcance vigente, crea el issue con el formato `<HU-XX o CC-XX> · <Título funcional>` (por ejemplo `CC-20 · Pulir UX/UI de Mapa en tiempo real`), agrégalo al proyecto `FlotaÁgil — Backlog` (`orgs/flotaagil-cl/projects/1`) y mueve su tarjeta a `En curso`.
   - Si agrega una funcionalidad nueva fuera del alcance aprobado, abre primero un issue con la plantilla de Solicitud de cambio (`RFC: CC-XX` correlativo) antes de implementar.
2. **Rama limpia:** Crea una rama nueva desde `main` actualizado (`git checkout main && git pull origin main && git checkout -b <tipo>/<descripcion>`).
3. **Implementación, documentación y pruebas:** Implementa los cambios, registra la Decisión de Cambio correlativa (`DC-XX`) en `docs/diccionario-cambios.md` cuando corresponda, y ejecuta las validaciones y pruebas puntuales en modo no interactivo (`npx vitest run ...`, `pytest <ruta_puntual>`, lint/typecheck según el área).
4. **Commit y PR:** Usa Conventional Commits en español con scope (con `Refs #<N>` en los commits de la rama), haz push (`git push -u origin <rama>`) y abre el PR hacia `main` con `Closes #<N>` (si termina el issue) o `Refs #<N>` (si es parcial). Verifica `gh pr view <PR> --json baseRefName,closingIssuesReferences`.
5. **CI y Fusión:** Espera `gh pr checks --watch` hasta que todos los checks (incluido `ci`) estén en verde, fusiona con `gh pr merge --squash` (**SIN** `--delete-branch`, respetando `CLAUDE.md`), vuelve a `main` (`git checkout main`) y ejecuta `git pull origin main`.
