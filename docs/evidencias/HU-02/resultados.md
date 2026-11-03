# HU-02 · Mapa en tiempo real de conductores — resultados de pruebas

Rama `feat/HU-02-mapa`, 2026-11-03. Datos sintéticos (`datos_demo`). Backend con Daphne y la capa de canales en Redis; panel con el proxy de Vite (`/ws`).

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 598 pruebas en verde (12 de WebSocket) | 99 % total |
| Web (Vitest) | 451 pruebas en verde | 94,5 % total; `src/mapa` 95,6 % |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; `verificar-carga` ok (22 pantallas con lazy; el mapa fuera del paquete inicial, del login y del portal) | — |

## Criterios de aceptación

| Criterio | Qué se probó | Obtenido |
|---|---|---|
| Mapa con marcadores móviles | Dos conductores enviando una posición por segundo durante 20 s con el mapa abierto | Los marcadores se movieron con cada posición (manual) |
| Al seleccionar muestra nombre, patente y estado | Clic en el conductor | Ficha con nombre, patente, estado, antigüedad y precisión (manual y automática) |
| Latencia p95 < 5 s | Diferencia entre la llegada al navegador y `registrada_en`, 40 posiciones | **p95 = 59 ms** (mín. 48 ms, mediana 52 ms, máx. 71 ms) en local. Falta medirla con 50 usuarios (k6, pruebas no funcionales) |
| Posiciones > 60 s no confiables | 65 s sin posiciones nuevas | «Posición de hace más de 60 s: no confiable», marcador gris con borde punteado (manual y automática). También se marca la precisión > 100 m (Anexo D) |

## Seguridad y aislamiento

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Sin token, token inválido o vencido | Cierre 4401 | OK |
| Conductor | Cierre 4403 | OK |
| Cuenta con contraseña temporal pendiente (DC-14) | 4401 | OK |
| Origin que no es del panel | Conexión rechazada | OK |
| Otra empresa (RN-13) | No recibe las posiciones | OK |
| Access que vence con la conexión abierta | Cierre 4401; el panel renueva y se reconecta | OK (backend y web) |
| Fin de turno o cuenta deshabilitada | El conductor sale del mapa | OK |

El token viaja como subprotocolo del WebSocket, no en la URL: no queda en los logs.

## Pendiente

- **PR-12:** clave de Google Maps JS (con costo). Mientras tanto, el mapa usa el adaptador de desarrollo.
- **PR-07:** pasar el listado de Conductores al canal WebSocket.
- Medir la latencia con carga (k6).

## Capturas

- `panel-mapa-escritorio.png`: mapa en vivo con la ficha del conductor seleccionado.
- `panel-mapa-no-confiable-celular.png`: posición marcada como no confiable, en 390 px.
