# HU-27 · Monitoreo de vuelo y ajuste de recogida — resultados de pruebas

Rama `feat/HU-27-monitoreo`, 2026-11-04. Datos sintéticos, en un stack aislado con una AeroAPI falsa. **Sin probar contra FlightAware real.**

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 818 pruebas en verde | 98 % total; `monitoreo.py` 98 % |
| Web (Vitest) | 493 pruebas en verde | 94,7 % total |
| App (Vitest) | 72 pruebas en verde (sin cambios en esta HU) | 95,3 % sentencias en la lógica |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; `verificar-carga` ok | — |

## Caso de prueba CP-21

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Más de 3 h antes de la llegada | No consulta | OK (automática) |
| Desde 3 h antes | Consulta cada 30 min | OK (automática: 29 min no, 30 sí) |
| Última hora | Cada 10 min | OK (automática: 9 min no, 10 sí) |
| Valores por empresa | Se respetan | OK (automática) |
| Vuelo aterrizado, cancelado o desviado; viaje cerrado o pendiente | No consulta | OK (automática) |
| Límite de la API por minuto | Respeta el límite y prioriza al más atrasado | OK (automática) |
| ETA cambia 14 min | No propone | OK (automática) |
| ETA cambia 15 min, más o menos | Propone | OK (automática) |
| Vuelo nacional | ETA + 20 min (RN-17) | OK (automática) |
| Vuelo internacional | ETA + 35 min (RN-17) | OK (automática) |
| Origen desconocido | Margen nacional (DC-12) | OK (automática) |
| Antes de confirmar (RN-02) | La recogida no cambia | OK (automática y manual) |
| Confirmar | Cambia la recogida, queda en auditoría | OK (automática y manual: `AJUSTE_RECOGIDA`) |
| Descartar | Mantiene la recogida, queda en auditoría; esa ETA no se vuelve a proponer | OK (automática) |
| La propuesta cambió mientras se miraba | 409, no aplica lo que no se vio | OK (automática) |
| Otra empresa (RN-13) | 404 | OK (automática) |
| Dos barridos seguidos | No duplican la consulta | OK (automática) |
| API caída | Reintenta a los 30, 60 y 120 s | OK (automática; manual: `Retry in 30s`) |

## Con beat real (reserva 31)

Con la AeroAPI falsa fallando dos veces: la propuesta apareció en el panel **a los 53 s**, con la recogida sin cambios. Al confirmar quedó en auditoría con el usuario, la hora anterior y la ETA.

## Límites conocidos

- **El pasajero no recibe aviso del cambio de hora:** no está en los criterios. El conductor con viaje sí se entera.
- **Lista de aeropuertos de Chile fija en el código:** si falta uno, ese vuelo usaría el margen internacional.
- **El panel refresca la ficha cada 30 s.** La alerta en vivo llega con HU-28.

## Capturas

- `panel-propuesta-escritorio.png` y `panel-propuesta-celular.png`: propuesta por confirmar.
