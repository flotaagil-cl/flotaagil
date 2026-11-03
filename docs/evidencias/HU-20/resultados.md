# HU-20 · Verificación del pasajero por WhatsApp — resultados de pruebas

Rama `feat/HU-20-whatsapp`, 2026-11-03. Datos sintéticos. Sin credenciales de Twilio: el adaptador real se probó con un doble y el flujo completo con el notificador de desarrollo.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 586 pruebas en verde | 98 % total; `verificacion.py` 95 %, `whatsapp_views.py` 98 % |
| Web (Vitest) | 441 pruebas en verde (solo tipos regenerados) | — |
| App (Vitest) | 31 pruebas en verde | — |
| Estático | ruff, bandit, `tsc`; OpenAPI validado | — |

## Casos de prueba

| CP | Qué se probó | Esperado | Obtenido |
|---|---|---|---|
| CP-07 | Solicitud del portal | PENDIENTE_CONFIRMACION y plantilla de verificación registrada (SALIENTE, PLANTILLA) | OK (automática y manual) |
| CP-07 | Twilio (doble): plantilla con ContentSid, variables, From/To de WhatsApp y StatusCallback | Petición correcta; SID guardado | OK |
| CP-07 | Twilio caído o con 5xx/429 | 3 intentos con espera creciente; luego FAILED y la solicitud expira sola | OK |
| CP-07 | Credenciales inválidas (401) | Sin reintentos, FAILED | OK |
| CP-08 | Confirmar (botón o «Sí») | SOLICITADO por la máquina de estados, actor PASAJERO, `verificado_en`, respuesta al pasajero | OK (manual con `simular_whatsapp`: viaje 100) |
| CP-08 | Cancelar | CANCELADO, origen PASAJERO, motivo RN-06, respuesta al pasajero | OK (manual por el webhook: viaje 99) |
| CP-08 | Dos solicitudes pendientes del mismo número | Se responde la del mensaje respondido (`OriginalRepliedMessageSid`) | OK (automática); sin referencia, la más reciente (manual) |
| CP-09 | Mismo webhook dos veces | La segunda vez «repetido», sin efectos | OK (automática y manual) |
| CP-09 | Firma `X-Twilio-Signature` inválida o ausente | 403, sin cambios | OK |
| CP-09 | Sin token | Solo se acepta con DEBUG | OK |
| CP-09 | Respuesta después de expirar | «Ya no está vigente», sin cambios | OK |
| CP-09 | Estados de entrega desordenados | Solo avanzan (`sent` tardío no retrocede a `delivered`) | OK |
| — | Texto libre / número desconocido | Se guarda o se ignora, sin acciones | OK |
| — | Máximo 3 solicitudes por número cada 15 min y expiración a los 15 min (RN-06) | Ya existían (HU-19) | OK |

## Pendiente

- **PR-11:** cuenta de Twilio, número aprobado, plantilla aprobada y URL pública (con costo).
- **PR-10:** avisos de ubicación del vehículo al pasajero.
- Envío síncrono hasta que exista el worker de Celery.

## Capturas

- `panel-confirmada-por-whatsapp.png`: historial «Pendiente de confirmación → Solicitado · Pasajero».
- `panel-cancelada-por-whatsapp.png`: historial «Pendiente de confirmación → Cancelado · Pasajero».
