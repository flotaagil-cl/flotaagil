# HU-34 · Autoregistro de convenios con aprobación — resultados

Rama `feat/HU-34-autoregistro-convenios`, 2026-11-10. CC-16 (#35). Datos sintéticos.

| Caso | Esperado | Obtenido |
|---|---|---|
| Registro en el portal | Convenio EN_REVISION y cuenta de rol CONVENIO, en auditoría (`REGISTRO`) | OK (automática, web y manual: convenio 15) |
| RUT, correo, teléfono, dirección o contraseña inválidos; correo ya usado | 400 en su campo, sin crear nada | OK (automática y web) |
| Campo trampa / límite por IP / empresa inexistente | 201 sin crear / 429 / 404 | OK (automática) |
| Aprobar | APROBADO, revisado por, auditoría y correo al encargado | OK (automática y web) |
| Rechazar | Exige motivo; RECHAZADO, auditoría y correo con el motivo | OK (automática y web) |
| Aprobar o rechazar fuera de revisión | 409 | OK (automática) |
| Desactivar (RN-08) | La sesión abierta deja de servir (401), no puede volver a entrar y su historial no cambia; reactivar devuelve el acceso | OK (automática y web) |
| Restablecer contraseña | Temporal DC-14 mostrada una vez, sin quedar en la auditoría; 409 sin cuenta | OK (automática y web) |
| Cuenta en revisión o rechazada | Entra, ve su estado o el motivo, no reserva (409) | OK (automática y web) |
| Cuenta aprobada | Reserva SOLICITADO sin verificación (RN-07), con la declaración ligada a su usuario; ve solo sus reservas | OK (automática y web) |
| El panel no reserva con un convenio inactivo | 400 | OK (automática) |
| Link anterior `/api/convenio/<token>/` | 404 | OK (automática) |
| Migración | Convenios existentes APROBADO o INACTIVO, sin cuenta | OK (manual en la base de desarrollo: 14 convenios) |

## Límites conocidos

- La migración no tiene reversa: los tokens y las contraseñas del link no se pueden recuperar.
- La ficha del administrador edita razón social y RUT; dirección y encargado se editan por la API.
- Los correos no se probaron contra SES (DC-34).

## Capturas

- `portal-registro-empresa-celular.png`
- `panel-convenio-en-revision-escritorio.png`
