# HU-31 · Historial de turnos y cierre de caja — resultados

Rama `feat/HU-31-turnos-caja`, 2026-11-10. CC-12 (#33). Datos sintéticos.

| Caso | Esperado | Obtenido |
|---|---|---|
| CP-36: rinde 48.000 de 48.000 | Diferencia 0, sin observación, en auditoría | OK (automática y web) |
| CP-36: rinde 45.000 | Exige observación; diferencia −3.000 | OK (automática y web) |
| CP-36: rinde 0 | Diferencia −48.000 con observación | OK (automática y web) |
| CP-36: turno sin efectivo | Registrado 0, diferencia 0 | OK (automática) |
| CP-36: segundo cierre | 409 `cierre_repetido` | OK (automática y web) |
| Turno abierto o con viaje en ejecución | 409 | OK (automática) |
| Solo administrador y su empresa | 403 / 404 | OK (automática y web) |
| Empezar, terminar, deshabilitar, cambiar de vehículo | Abre, cierra con su motivo, abre otro | OK (automática) |
| Un turno abierto por conductor | Índice único parcial | OK (automática) |
| Viaje aceptado guarda su turno; cierre forzado posterior queda en él | `viaje.turno` | OK (automática) |
| Cierre administrativo | No disponible, motivo en auditoría; 409 en viaje o sin turno | OK (automática) |
| Mi turno lee TURNO | Mismos campos que HU-18 | OK (automática) |
| Migración de DC-26 y su reversa | 9 turnos (7 abiertos), viajes enlazados; la reversa repone las columnas | OK (manual en la base de desarrollo) |
| Pantalla «Cierre de caja» | Lista y diálogo con diferencia | OK (manual: turno 17, registrado 1.000, rendido 500) |

## Límites conocidos

- Los turnos anteriores al último de cada conductor no existen: DC-26 no los guardaba.
- «Terminar turno» del administrador (CIERRE_ADMINISTRATIVO) existe en la API, pero no tiene botón en la ficha del conductor.
- La app no se entera al instante de un cierre administrativo: sin probar con la app abierta.
- Sin probar en teléfono: Mi turno tras cambiar de vehículo.

## Capturas

- `panel-turnos-por-cerrar-escritorio.png`
- `panel-cierre-con-diferencia-escritorio.png`
