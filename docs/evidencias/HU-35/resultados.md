# HU-35 · Cuenta de pasajero opcional — resultados

Rama `feat/HU-35-cuenta-pasajero`, 2026-11-10. CC-16 (#35). Datos sintéticos; WhatsApp con el notificador de desarrollo y el webhook sin firma (DEBUG).

| Caso | Esperado | Obtenido |
|---|---|---|
| Crear cuenta en el portal | Pendiente, usuario inactivo y WhatsApp «CONFIRMAR CUENTA» | OK (automática, web y manual) |
| Entrar sin confirmar | 401 `cuenta_sin_confirmar` | OK (automática) |
| Responder «CONFIRMAR CUENTA» | Activa, liga al pasajero (verificado) y muestra sus reservas de invitado | OK (automática y manual) |
| Confirmación vencida, «Confirmar» de una reserva, segunda cuenta del mismo teléfono | No confirma | OK (automática) |
| Datos inválidos, correo de otra cuenta, campo trampa | 400 / 400 / 201 sin crear | OK (automática y web) |
| Pedir con la cuenta | SOLICITADO sin verificación, con sus datos aunque vengan otros; actor PASAJERO con su usuario | OK (automática, web y manual: reserva 138) |
| Límite por teléfono | Cuarta solicitud en 15 min: 429 | OK (automática) |
| Historial y cancelación | Ve su historial; cancela en PENDIENTE_CONFIRMACION o SOLICITADO; con conductor 409 (RN-09); reservas ajenas 404 | OK (automática y web) |
| Recuperar la contraseña | 202 siempre; enlace por correo de un solo uso; la nueva sirve; enlace inválido 400 | OK (automática y web) |
| Bloqueo tras 5 intentos | `cuenta_bloqueada` | OK (automática) |
| Eliminar la cuenta | Sin credencial ni correo; pasajero y reservas quedan; no puede entrar; auditoría | OK (automática y web) |
| El invitado sigue igual | PENDIENTE_CONFIRMACION | OK (automática) |
| El panel sigue cerrado | 403 | OK (automática) |

## Límites conocidos

- USUARIO.email es único en todo el sistema: con el mismo correo no se puede tener cuenta en dos empresas.
- El WhatsApp de confirmación va como mensaje de sesión: fuera de la ventana de 24 h necesita una plantilla aprobada (PR-11).
- Sin probar contra Twilio ni SES reales.

## Capturas

- `portal-confirma-tu-cuenta-celular.png`
- `mis-reservas-escritorio.png`
