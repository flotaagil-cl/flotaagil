# chore/app-base · Base de la app del conductor — resultados de pruebas

Rama `chore/app-base`, 2026-11-03. Datos sintéticos (`datos_demo` y cuentas `*.example`). Emulador Android 17 (API 37, `Medium_Phone_API_37.0`), app manejada por DevTools del WebView y GPS simulado con `adb emu geo fix`.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 519 pruebas en verde | 99 % total |
| App (Vitest) | 28 pruebas en verde | 87 % sentencias, 78 % ramas en sesión, API, cola, rastreador y muestreo |
| Web (Vitest) | 438 pruebas en verde (sin cambios de comportamiento; tipos regenerados) | — |
| Estático | ruff, bandit, ESLint y `tsc` (backend, web y app) sin hallazgos; OpenAPI validado; `npm ci` con npm 10 | — |

## Casos de prueba

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Login por el canal app (emulador) | Inicio con el estado del conductor | OK |
| Envío del GPS en turno (Disponible, emulador) | Una posición cada 30 s en `posicion_gps` | OK |
| **App en segundo plano y pantalla apagada 4 min con access de 1 min** (emulador) | Sin huecos; el access vence y se renueva sin cortar el envío | OK: 9 posiciones cada 30 s (16:50:02 → 16:54:04); 5 × `posiciones 401` → 5 × `refresh 200` → reintento 201; sesión intacta al volver |
| Viaje de 1 h con el access venciendo cada 15 min (automática) | 360 posiciones, 3 renovaciones, nada pendiente | OK |
| Varios 401 simultáneos (automática) | Un solo refresh (el backend rota el refresh) | OK |
| Refresh sin red en segundo plano (automática) | Se conserva el refresh, las posiciones esperan y llegan al volver la señal sin duplicar | OK |
| Respuesta perdida al enviar un lote (automática) | El reenvío no duplica (DC-15) | OK |
| Fuera de turno / sin consentimiento (automática y backend) | 409 y la cola se vacía; el GPS se detiene | OK |
| Contraseña temporal (emulador) | «Crea tu contraseña»; al cambiarla, consentimiento y luego Inicio | OK; `debe_cambiar_password = false` y consentimiento guardado en la base |
| Cerrar la app y volver a abrirla con la sesión guardada (emulador, reinstalación) | Restaura la sesión desde el refresh cifrado | OK |
| Logout (emulador, PR-02) | `POST /api/auth/app/logout/` 204, desaparece la notificación del GPS | OK |
| Lote inválido, precisión > 500 m, posiciones del futuro o de más de 30 días (backend) | 400 o descartadas | OK |

## Prueba en teléfono real

Pendiente: la hace Renato con [`docs/guia-prueba-app-android.md`](../../guia-prueba-app-android.md) (30 min con la pantalla apagada, sin señal, logout). El emulador no reproduce las restricciones de HyperOS.

## Capturas

- `app-inicio-en-turno.png`: Inicio en turno, registrando la ubicación.
- `app-cambio-password.png`: cambio obligatorio de la contraseña temporal.
- `app-consentimiento.png`: consentimiento informado (RN-18).
