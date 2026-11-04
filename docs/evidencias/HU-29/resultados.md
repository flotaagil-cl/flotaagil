# HU-29 · Fila virtual del aeropuerto — resultados de pruebas

Rama `feat/HU-29-fila`, 2026-11-04. Datos sintéticos, en un stack aislado. Las posiciones se enviaron por la API de la app: **no se ha probado con GPS real ni en el aeropuerto.**

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 769 pruebas en verde | 98 % total; `fila.py` 99 % |
| Web (Vitest) | 488 pruebas en verde | 94,7 % total |
| App (Vitest) | 72 pruebas en verde | 95,3 % sentencias en la lógica |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; `verificar-carga` ok | — |

## Casos de prueba

| Caso | Qué se probó | Esperado | Obtenido |
|---|---|---|---|
| CP-19 | Llega a la geocerca estando Disponible | Entra a la fila | OK (automática y manual) |
| CP-19 | Fuera de la zona, GPS impreciso, No disponible o con viaje | No entra | OK (automática; manual: fuera de la zona) |
| CP-19 | Posición atrasada de más de la tolerancia | No da un lugar viejo | OK (automática) |
| CP-19 | Geocerca de otra empresa (RN-13) | No cuenta | OK (automática) |
| CP-19 | Orden | El de ingreso a la geocerca (RN-16) | OK (automática y manual: lugares 1, 2 y 3) |
| CP-19 | El conductor ve su lugar | «Vas en el lugar 2 de 3» | OK (automática y manual) |
| CP-20 | Recogida en aeropuerto | Propone al primero aunque otro esté más cerca; ASIGNACION `FILA` | OK (automática y manual) |
| CP-20 | El despachador elige a otro (RN-02) | Queda `MANUAL`; el primero conserva su lugar | OK (automática) |
| CP-20 | Al ser asignado | Sale con motivo `ASIGNADO` y el resto avanza | OK (automática y manual: la app del segundo pasó a «Eres el primero» en 7 ms) |
| CP-20 | Si rechaza | Vuelve al final (DC-21) | OK (automática) |
| CP-20 | 11 min sin posiciones en la zona | Sale con motivo `FUERA_ZONA` | OK (automática y manual, con beat real) |
| CP-20 | 9 min fuera | Conserva su lugar | OK (automática) |
| CP-20 | Tolerancia configurada por empresa | Se respeta | OK (automática) |
| CP-20 | Pasa a No disponible | Sale con motivo `NO_DISPONIBLE` | OK (automática y manual) |

## Hallazgo corregido

La prueba en navegador encontró que, al salir de la fila, el aviso solo llegaba a quienes seguían en ella. Quien salía nunca se enteraba y su app seguía mostrando la tarjeta. Ahora también se le avisa, con su prueba automática.

## Capturas

- `app-lugar-en-fila-celular.png`: lugar en la fila en la app.
- `panel-primero-de-la-fila-escritorio.png`: el panel propone al primero de la fila.
