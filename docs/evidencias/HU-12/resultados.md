# HU-12 · Auditoría de cambios en convenios — resultados de pruebas

Rama `feat/HU-12-auditoria-convenios`, 2026-11-04. Prueba manual contra el stack principal, con un convenio sintético nuevo. No se borró nada. El panel se sirvió desde un build con un servidor estático mínimo, sin un Vite adicional. Las capturas muestran solo la tarjeta de auditoría, sin el link ni la contraseña.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 935 pruebas en verde | 98 % total |
| Web (Vitest) | 539 pruebas en verde | 94,3 % total; `src/convenios` 84,7 % |
| App (Vitest) | 80 pruebas en verde (sin cambios en esta HU) | — |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; sin migraciones pendientes; `verificar-carga` ok | — |

## Caso de prueba CP-24

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Contenido | Usuario, acción y fecha, del más nuevo al más antiguo | OK (automática y manual: creación, cambio de contraseña, desactivación y activación) |
| Solo inserción (RN-12) | Modelo y trigger impiden cambiar o borrar | OK (automática, pruebas de `apps/auditoria`) |
| Consulta de solo lectura | POST, PATCH y DELETE: 405; sin botones en la tabla | OK (automática; manual: POST y DELETE) |
| Sin credenciales | Sin contraseña, hash, token ni datos previos | OK (automática; manual: la contraseña no aparece) |
| Por convenio | Solo los registros de ese convenio | OK (automática) |
| Actualización | Rotar o desactivar la refrescan sin recargar | OK (automática al rotar; manual al rotar y desactivar) |
| Paginación | 25 por página | OK (automática) |
| Otra empresa (RN-13) | 404 | OK (automática y manual) |
| Despachador | 403 | OK (automática y manual) |
| Celular (390 px) | Sin desborde horizontal | OK (manual) |

## Límites conocidos

- **Activar sin recargar no quedó comprobado en la prueba manual:** la espera del script coincidió con «Desactivación» y leyó la tabla antes de tiempo. Usa el mismo camino que desactivar, y el registro aparece tras recargar.
- **También se listan creación y edición de datos,** que ya estaban en la auditoría. RN-12 exige contraseña y estado.

## Capturas

- `panel-auditoria-escritorio.png` y `panel-auditoria-celular.png`: tarjeta de auditoría.
