# HU-15 · Aceptar o rechazar viaje en 60 s — resultados de pruebas

Rama `feat/HU-15-respuesta`, 2026-11-03. Datos sintéticos (`datos_demo`). La app se probó en el navegador con pantalla de teléfono, contra el backend real, sin emulador.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 624 pruebas en verde | 98 % total; `asignacion.py` 96 % |
| Web (Vitest) | 462 pruebas en verde | 94,4 % total |
| App (Vitest) | 37 pruebas en verde | 87,7 % sentencias en la lógica |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; `verificar-carga` ok | — |

La pantalla `Responder` de la app no tiene pruebas automáticas: la configuración de pruebas de la app no monta pantallas. Se probó solo a mano.

## Casos de prueba

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Aceptar dentro de los 60 s | Viaje ACEPTADO, conductor En viaje, ASIGNACION `ACEPTADA` con `respondida_en`; la app muestra el viaje en curso | OK (automática y manual: reserva 102) |
| Rechazar | Reserva a SOLICITADO sin conductor ni vehículo, ASIGNACION `RECHAZADA`, actor CONDUCTOR | OK (automática y manual: reserva 104) |
| Sin respuesta en 60 s (RN-04) | ASIGNACION `EXPIRADA`, reserva a SOLICITADO, actor SISTEMA | OK: volvió a SOLICITADO a los **64 s** (manual: reserva 104) y automática |
| Responder después de los 60 s | 409 `asignacion_no_permitida` | OK (automática) |
| Responder dos veces, o un conductor que no es el asignado | 409 / 400, sin cambios | OK (automática) |
| Reasignar tras un rechazo | Nueva ASIGNACION sobre la misma reserva | OK (automática y manual) |
| Expiración repetida | Una segunda pasada no hace nada; una respondida no expira | OK (automática) |
| Aviso a la app | `sin_asignacion` cierra el aviso al rechazar o expirar | OK (automática y manual) |
| Dos despachadores a la vez | La reserva se relee con bloqueo antes de asignar | Implementado; sin prueba de concurrencia |

Historial de la reserva 104 en la prueba manual: `—→SOLICITADO (DESPACHADOR)`, `SOLICITADO→ASIGNADO (DESPACHADOR)`, `ASIGNADO→SOLICITADO (CONDUCTOR)`, `SOLICITADO→ASIGNADO (DESPACHADOR)`, `ASIGNADO→SOLICITADO (SISTEMA)`.

## Notas

- La expiración corre cada 5 s en el servicio `asignaciones` del compose, mientras no exista Celery beat. Por eso puede tardar hasta unos segundos más de 60 s.
- Esta rama incluye `fix/estado-en-vivo` por merge, y dos ajustes de adaptadores (FlightAware y sandbox de Twilio).

## Capturas

- `app-aceptar-o-rechazar-celular.png`: aviso con los botones y la cuenta regresiva.
- `app-viaje-aceptado-celular.png`: viaje en curso después de aceptar.
