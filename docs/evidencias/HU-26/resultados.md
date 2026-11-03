# HU-26 · Registrar número de vuelo — resultados de pruebas

Rama `feat/HU-26-vuelos`, 2026-11-03. Datos sintéticos (`datos_demo`). Sin clave de FlightAware: el consultor de desarrollo hace de API; el adaptador real se probó con respuestas simuladas.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 564 pruebas en verde | 99 % total |
| Web (Vitest) | 441 pruebas en verde | 94,4 % total |
| App (Vitest) | 31 pruebas en verde | — |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; `verificar-carga` ok | — |

## CP-11

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Formato IATA (`LA123`, `H2 456`; rechaza otros) | 400 en el campo | OK (ya existía desde HU-03) |
| Vuelo inexistente en el panel (manual: `ZZ 999`) | «No encontramos el vuelo ZZ 999 con llegada a SCL el 20-11-2026…» en el campo, con foco | OK |
| Vuelo existente (manual: `LA 845`) | Se crea; la ficha dice «Verificado con la API de vuelos» | OK |
| La API informa otra hora programada | Se guarda la de la API, más la estimada y el estado (DC-06) | OK (automática) |
| La API no responde | Se guarda como se informó, «Sin verificar» | OK (automática) |
| Editar con otro vuelo / editar otro campo | Vuelve a verificar / no vuelve a consultar | OK (automática) |
| Portal: recogida sin hora | Llegada confirmada + margen nacional (RN-17) | OK (automática) |
| Portal: vuelo inexistente | 400 en el campo, sin crear la reserva | OK (automática) |
| FlightAware: elige la llegada a SCL del día más cercana a la informada; estados programado, demorado (≥ 15 min), aterrizado, cancelado y desviado; reintentos ante 429/5xx/red; 401 sin reintentar; 404 = no existe; arma la URL con `x-apikey` | — | OK (respuestas simuladas) |

## Pendiente

- **PR-08:** registrar vuelos de salida (viajes hacia el aeropuerto). Requiere decidir el cambio de VUELO.
- **PR-09:** la clave de FlightAware AeroAPI tiene costo. Probar con la clave real antes de producción.

## Capturas

- `panel-vuelo-inexistente.png`: error en el número de vuelo.
- `panel-vuelo-verificado.png`: ficha de la reserva con el vuelo verificado.
