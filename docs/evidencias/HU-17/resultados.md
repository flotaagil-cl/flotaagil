# HU-17 · Abrir Google Maps o Waze — resultados de pruebas

Rama `feat/HU-17-navegacion`, 2026-11-03. Datos sintéticos (`datos_demo`).

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 542 pruebas en verde | 99 % total |
| App (Vitest) | 31 pruebas en verde | 87,7 % sentencias en la lógica (incluye `navegacion.ts`) |
| Web (Vitest) | 439 pruebas en verde (solo tipos regenerados) | — |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado | — |

## Casos de prueba

HU-17 no tiene CP asignado en el backlog; estos son los casos de la HU.

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Conductor sin viaje aceptado (solo ASIGNADO o FINALIZADO) | No se muestra la tarjeta (`viaje: null`) | OK (automática) |
| Viaje ACEPTADO, EN_CAMINO o EN_ZONA | Navega al punto de recogida | OK (automática y en el navegador con `conductor2`, viaje EN_CAMINO) |
| Pasajero a bordo | Navega al destino | OK (automática y en el navegador con `conductor1@taxi-pacifico`) |
| Botón Google Maps | `https://www.google.com/maps/dir/?api=1&destination=<lat>,<lon>&travelmode=driving` | OK |
| Botón Waze | `https://waze.com/ul?ll=<lat>,<lon>&navigate=yes` | OK |
| Viajes de otro conductor | No aparecen | OK |
| Solo conductores | Despachador 403 | OK |
| Celular (390 px) | Sin scroll horizontal; botones de 44 px o más | OK |

En el teléfono, los enlaces universales abren la app de Google Maps o de Waze si está instalada. Verificarlo en el Android real: [`docs/guia-prueba-app-android.md`](../../guia-prueba-app-android.md), prueba F.

## Capturas

- `app-viaje-en-curso-celular.png`: viaje EN_CAMINO; navega a la recogida.
- `app-pasajero-a-bordo-celular.png`: pasajero a bordo; navega al destino.
