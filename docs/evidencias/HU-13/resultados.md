# HU-13 · Estado Disponible/No disponible del conductor — resultados de pruebas

Rama `feat/HU-13-turno`, 2026-11-03. Datos sintéticos (`datos_demo`).

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 535 pruebas en verde | 99 % total |
| Web (Vitest) | 439 pruebas en verde | 94,4 % total; `src/flota` 96,6 % |
| App (Vitest) | 29 pruebas en verde | 87 % sentencias en la lógica |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; `verificar-carga` ok (21 pantallas con lazy) | — |

## Casos de prueba

| CP | Qué se probó | Esperado | Obtenido |
|---|---|---|---|
| CP-03 | Disponible con un solo vehículo activo | Se declara ese vehículo | OK (automática) |
| CP-03 | Disponible con dos vehículos sin elegir (RN-05) | 409 `elegir_vehiculo`; en la app el botón queda desactivado hasta elegir | OK (backend real y automática) |
| CP-03 | Disponible eligiendo DMAE14 | Estado Disponible, vehículo DMAE14; el panel lo muestra sin recargar | OK: el panel se actualizó en 8,3 s y 11,0 s (refresco cada 10 s, PR-07) |
| CP-03 | Sin consentimiento (RN-18), licencia vencida, sin vehículos, vehículo ajeno o inactivo, vehículo en turno con otro conductor | 409 con `code` y mensaje | OK (automática) |
| CP-03 | Posición en turno | 201 | OK (backend real) |
| CP-04 | No disponible | Borra el vehículo declarado; el GPS se detiene; posiciones posteriores, 409 `fuera_de_turno` | OK (backend real) |
| CP-04 | Cambiar estando En viaje (RN-03) | 409 `en_viaje` | OK (automática) |
| CP-04 | Solo conductores | Despachador 403 | OK |

## Emulador

La sesión guardada se restauró tras reiniciar el emulador en frío: el refresh quedó en el almacenamiento cifrado. Antes de eso, el emulador (Android 17, API 37) empezó a quedar `offline` en adb en cada interacción, y siguió igual después de reiniciarlo. Por eso el selector de vehículo de la app no se pudo recorrer en el emulador. La regla está cubierta por las pruebas automáticas y por la API real. Queda en la guía del teléfono: [`docs/guia-prueba-app-android.md`](../../guia-prueba-app-android.md), prueba E.

## Capturas

- `panel-conductores-escritorio.png`: listado de conductores con su estado.
- `panel-conductor-celular.png`: ficha en 390 px con «Disponible · declaró DMAE14», actualizada sola tras el cambio hecho desde la app.
