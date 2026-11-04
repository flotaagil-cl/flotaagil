# chore/celery — resultados de pruebas

Rama `chore/celery`, 2026-11-03. Celery 5.5.3, Redis 7.2 como broker. **La medición usó servidores falsos de Twilio y AeroAPI, en un stack desechable: no se envió ningún WhatsApp real.**

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 727 pruebas en verde | 98 % total |
| Estático | ruff, bandit; OpenAPI sin diferencias | — |

## Medición: la respuesta al conductor ya no espera a Twilio

Mismo código y misma base, con Twilio tardando 3 s. «Sin worker» devuelve el envío a la petición, como antes de Celery. 5 viajes por modo.

| Acción del conductor | Con worker (mediana / máx.) | Sin worker (mediana / máx.) |
|---|---|---|
| Aceptar | **60 / 76 ms** | 3.069 / 3.186 ms |
| En camino | **45 / 53 ms** | 3.052 / 3.057 ms |
| Pasajero a bordo (sin aviso) | 50 / 56 ms | 54 / 69 ms |
| Finalizar | **52 / 62 ms** | 3.064 / 3.074 ms |

«Pasajero a bordo» no envía nada, y por eso sirve de control: mide lo mismo en ambos modos.

## Con el worker real

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Twilio responde 503 dos veces | La respuesta al conductor no espera; reintenta y se envía | Aceptar en 70 ms; «Retry in 2s» en el worker; mensajes en QUEUED a los 12 s |
| RN-04 por beat: sin respuesta del conductor | Vuelve a SOLICITADO y la asignación queda EXPIRADA | A los 58 s de pedir la asignación (se envía justo antes) |
| RN-06 por beat: solicitud vencida | CANCELADO | A los 62 s; beat la revisa cada 60 s |
| AeroAPI falla al crear la reserva | Se crea sin verificar, y la tarea reintenta y verifica | Creada en 80 ms; verificada a los 32 s («Retry in 30s») |

## Automáticas

| Qué se probó | Obtenido |
|---|---|
| Esperas de WhatsApp: 2, 4, 8, 16 y 32 s; agotadas, el mensaje queda en FAILED | OK |
| Error definitivo de Twilio (400): sin reintentos | OK |
| Esperas de vuelos: de 30 s a 16 min; agotadas, sigue sin verificar | OK |
| Transacción revertida: no encola | OK |
| Sin broker: la acción no se rompe y queda en el log | OK |
| La acción solo encola: Twilio no se llama en la petición | OK |
| Las pruebas no pueden llegar al broker real | OK |

## Incidente: las pruebas corrieron contra el worker de desarrollo

Al activar Celery, las primeras corridas de pytest mandaron unas 100 tareas al worker real, con IDs de la base de pruebas. Esas tareas se ejecutaron contra la base de desarrollo.

| Efecto en la base de desarrollo | Cantidad | Qué se hizo |
|---|---|---|
| Mensajes simulados a la reserva 68 (sintética, cancelada) | 2 (ids 34 y 35) | Borrados |
| Vuelos marcados como consultados (ids 4 a 7); solo cambió `ultima_consulta_en`, comprobado contra sus vecinos | 4 | Devueltos a su valor original |

**Ningún mensaje salió por Twilio:** no hay credenciales en `backend/.env` ni en el contenedor, y ninguna fila tiene un SID real de Twilio (`SM` más 32 caracteres). `SMmanual100` es una entrada de una prueba manual.

**Corrección:** `config/settings_pruebas.py` fija modo eager y broker en memoria, con `--ds` en `pyproject.toml`. El primer intento, desde `conftest.py`, no funcionó y se detectó al medirlo. Comprobado: el worker real recibió 0 tareas de envío o de vuelos durante una corrida de 383 pruebas.

## Decisiones

- **Consulta inicial de vuelo en la petición:** el formulario debe responder si el vuelo existe (HU-26). Hace un intento; si la API falla, reintenta la tarea `consultar_vuelo`.
- **Cliente `redis` de 6.4.0 a 5.2.1:** es el tope de `kombu[redis]` en Celery 5.5. El servidor sigue en 7.2.
- **Timeout de 60 s por barrido cada 5 s,** y no con una tarea por asignación: es idempotente y sobrevive a un reinicio. Por eso puede tardar unos segundos más de 60.
- **Entrega al menos una vez** (`acks_late`): si el worker muere justo tras enviar, el mensaje puede repetirse. Se prefirió a perderlo.

## Pendiente

- Probar contra Twilio y AeroAPI reales.
- Con `FLIGHTAWARE_API_KEY` puesta, `datos_demo` consultaría la API real y gastaría consultas.
- El compose de producción (HU de infraestructura) también debe llevar worker y un solo beat.
