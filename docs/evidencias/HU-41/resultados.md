# HU-41 · Recuperación, activación y primer ingreso — resultados

Rama `feat/HU-41-recuperacion`, 2026-11-11. Backend: `apps/reservas/tests/test_recuperacion_activacion.py` y `test_cuenta_pasajero.py`. Web: `src/cuentas-web/recuperar.test.tsx`, `src/paginas/primer-ingreso.test.tsx` y `src/paginas/acceso.test.tsx`. Datos sintéticos; las capturas no tienen credenciales válidas.

| Caso | Esperado | Obtenido |
|---|---|---|
| Recupera tu contraseña | Pide el enlace con la marca de la empresa (`?empresa=`); misma respuesta exista o no el correo | OK |
| Límite por correo | Hasta 3 envíos cada 15 min; el cuarto no se envía y responde igual 202 | OK |
| Revisa tu correo | Vence en 30 minutos, reenviar el enlace, volver a ingresar | OK |
| Crea una nueva contraseña | Reglas a la vista (10+ caracteres, no solo números, coinciden); enlace vencido con «Pedir un enlace nuevo» | OK |
| Personal del panel | No recibe enlace (pide una temporal al administrador) | OK |
| Activa tu cuenta | Pasos, «Esperando tu confirmación…» consultando el estado, reenviar y corregir el número | OK |
| Límite de reenvíos | 3 por cuenta cada 15 min (429); cuenta ya activa (409) | OK |
| Volver a activar | `/solicitar/:slug/activar` con correo y contraseña; desde el ingreso tras un intento fallido | OK |
| Primer ingreso | Diseño nuevo con reglas; marca de la empresa para pasajero y convenio, FlotaÁgil para el panel | OK |

## Límites conocidos

- El estado de la activación se consulta cada 8 s mientras la pantalla está abierta (no hay WebSocket para el portal).
- La pantalla de la contraseña no muestra la regla de contraseñas comunes: la valida el servidor y su mensaje aparece en el campo.
