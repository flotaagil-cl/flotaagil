# HU-16 · Estados del viaje y pago — resultados de pruebas

Rama `feat/HU-16-estados-pago`, 2026-11-03. Datos sintéticos (`datos_demo`). La app se probó en el navegador con pantalla de teléfono, contra el backend real, sin emulador. Las posiciones se enviaron por la API de la app: **la geocerca no se ha probado con GPS real** (prueba G de la guía).

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 652 pruebas en verde | 98 % total; `ejecucion.py` 97 % |
| Web (Vitest) | 462 pruebas en verde | 94,4 % total |
| App (Vitest) | 51 pruebas en verde | 87,9 % sentencias en la lógica |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; `verificar-carga` ok | — |

La pantalla `AvanceViaje` de la app no tiene pruebas automáticas: la configuración de pruebas de la app no monta pantallas. Su lógica (`conductor/ejecucion.ts`) sí, y la pantalla se probó a mano.

## Casos de prueba

| Caso | Qué se probó | Esperado | Obtenido |
|---|---|---|---|
| CP-15 | Secuencia completa en la app | ACEPTADO → EN_CAMINO → EN_ZONA → PASAJERO_A_BORDO → FINALIZADO | OK (automática y manual: reserva 102) |
| CP-15 | Posición precisa a ~445 m del origen | Sigue EN_CAMINO | OK |
| CP-15 | Posición a ~111 m con ±88 m de precisión | Sigue EN_CAMINO (PoC H-3, A7) | OK |
| CP-15 | Posición a ~111 m con ±8 m | EN_ZONA con actor SISTEMA; la app lo muestra sin recargar | OK: la app lo mostró en 205 ms |
| CP-15 | Posición tomada antes de salir (lote atrasado) | No marca EN_ZONA | OK (automática) |
| CP-15 | Geocerca sin marcar y el pasajero ya subió (DC-17) | EN_ZONA con actor CONDUCTOR y luego PASAJERO_A_BORDO | OK (automática y manual: reserva 4) |
| CP-15 | Botón fuera de secuencia, otro conductor u otro rol | 409, 400 y 403; sin cambios | OK (automática) |
| CP-16 | Finalizar sin método, sin monto o con monto fuera de 0–500.000 (RN-10) | 400; el viaje sigue a bordo y sin pago | OK (automática; manual: en la app y por la API) |
| CP-16 | Finalizar con Tarjeta y $18.500 | PAGO_VIAJE registrado, FINALIZADO, conductor Disponible | OK (manual: reserva 102) |
| CP-16 | Método Convenio | Solo en viajes de convenio | OK (automática) |
| CP-16 | Finalizar dos veces | 409, un solo pago | OK (automática) |
| — | Cancelar desde el panel un viaje en curso | Conductor Disponible y la app se entera | OK (automática) |

Historial de la reserva 102: `… ACEPTADO (CONDUCTOR) → EN_CAMINO (CONDUCTOR) → EN_ZONA (SISTEMA) → PASAJERO_A_BORDO (CONDUCTOR) → FINALIZADO (CONDUCTOR)`.

## Hallazgos

- **Corregido:** el error de monto seguía visible después de corregir el valor. Se detectó en la captura; ahora se borra al escribir.
- **Corregido:** cancelar un viaje en curso dejaba al conductor En viaje para siempre.
- **Sin resolver, intermitente:** en 1 de 3 recorridos manuales la pantalla siguió mostrando «Aceptado» durante 30 s tras pulsar «Voy en camino».
  - El backend sí registró EN_CAMINO. En su registro aparece `GET /perfil/`, pero no `GET /viaje-activo/`, así que esa lectura no se completó.
  - No se encontró la causa. No se repitió en el recorrido siguiente, ni en 600 lecturas de esos dos endpoints (300 directas y 300 por el proxy de Vite), sin ningún cuelgue.
  - La app no ponía tiempo límite a sus peticiones, así que una lectura colgada no se reintentaba sola. **Corregido en `fix/app-peticiones`**: si la respuesta no llega, la pantalla se corrige sola. La causa de que esa petición no respondiera sigue sin conocerse.

## Capturas

- `app-en-zona-celular.png`: llegada marcada por la geocerca, con el botón siguiente.
- `app-pago-celular.png`: método y monto para finalizar.

El aviso «No se pudo iniciar el GPS» de las capturas se debe a que la app corre en el navegador, sin el plugin nativo.
