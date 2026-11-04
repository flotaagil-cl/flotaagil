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

## Ajuste del PO: navegar con la dirección escrita (`fix/HU-17-navegacion-texto`)

DC-30. Prueba manual contra el stack principal, sin clave de geocodificación, con el build de la app y la reserva sintética 129, recorrida hasta finalizar. Los botones se comprobaron capturando la URL que abren: sin teléfono no se abre la app real.

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| API sin clave de geocodificación | `navegar_con: DIRECCION` | OK (automática y manual) |
| API con clave | `navegar_con: COORDENADAS` | OK (automática) |
| Google Maps con dirección | `destination=<origen_dir o destino_dir>` | OK (automática y manual, en los dos tramos) |
| Waze con dirección | `q=<origen_dir o destino_dir>&navigate=yes`, sin `ll` | OK (automática y manual, en los dos tramos) |
| Espacios, tildes y `&` | Codificados | OK (automática) |
| Con coordenadas | Igual que antes, sin la dirección | OK (automática) |
| Backend anterior, sin el campo | Sigue con coordenadas | OK (automática) |
| Pantalla | Pasa `navegar_con` a los dos botones | OK (automática) |

**Límites:** no se comprobó en un teléfono cómo interpretan Google Maps y Waze esas direcciones (prueba F). Lo decide la clave vigente, no cómo se geocodificó cada viaje: una reserva creada antes de configurarla conserva sus puntos inventados (DC-30). El camino con coordenadas se probó solo de forma automática, porque el stack principal no tiene clave.

## Capturas

- `app-viaje-en-curso-celular.png`: viaje EN_CAMINO; navega a la recogida.
- `app-pasajero-a-bordo-celular.png`: pasajero a bordo; navega al destino.
- `app-navegar-por-direccion-celular.png`: ajuste del PO.
