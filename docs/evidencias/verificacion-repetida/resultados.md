# DC-31 · Verificación repetida del teléfono — resultados de pruebas

Rama `feat/HU-20-verificacion-repetida`, 2026-11-10. Cambio sobre HU-20 (#23) pedido por el PO según P1.1 del informe. Stack de desarrollo con el notificador de WhatsApp de desarrollo (sin Twilio), datos sintéticos.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 89 pruebas de `apps/portal` en verde (9 nuevas en `test_verificacion_repetida.py`) | `apps/portal` 93 %; `portal/servicios.py` 100 % |
| Web (Vitest) | 82 pruebas de `src/portal` en verde (1 nueva) | — |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; sin migraciones pendientes | — |

## Casos de prueba

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Teléfono verificado hace 10 días | SOLICITADO, historial «Solicitado · Pasajero», `expira_en` NULL y aviso «confirmó tu viaje» en vez de la plantilla | OK (automática; manual: reservas 135 y 137) |
| Verificado hace 91 días | PENDIENTE_CONFIRMACION y plantilla de verificación | OK (automática) |
| Vigencia configurada en 5 días, verificado hace 6 | PENDIENTE_CONFIRMACION | OK (automática) |
| Vigencia 0 | Siempre se verifica | OK (automática) |
| Pasajero existente sin verificar | PENDIENTE_CONFIRMACION | OK (automática) |
| Verificado en otra empresa | No cuenta: PENDIENTE_CONFIRMACION | OK (automática) |
| Cuarta solicitud del número verificado en 15 min | 429 `limite_telefono`; quedan 3 SOLICITADO | OK (automática) |
| Aceptaciones de privacidad y avisos | Se registran igual | OK (automática) |
| Campo trampa con número verificado | Responde PENDIENTE_CONFIRMACION sin crear nada ni enviar | OK (automática) |
| Número nuevo | Sigue pidiendo verificación | OK (manual: reserva 136) |
| Portal: confirmación sin plazo | «Tu número … ya está verificado: no necesitas confirmar por WhatsApp.» | OK (automática y manual) |

**Recorrido manual.** El +56911125449 (sintético) tenía la reserva 133 pendiente. Se confirmó con `simular_whatsapp 133 confirmar`, lo que dejó `verificado_en`. Su siguiente solicitud desde el portal quedó SOLICITADO y el worker envió el aviso de confirmación (SESION, SENT).

## No probado

- Contra Twilio real (PR-11). Fuera de la ventana de 24 h, el aviso de confirmación necesita su plantilla aprobada (`TWILIO_PLANTILLA_AVISO_CONFIRMACION`).

## Capturas

- `portal-telefono-verificado-celular.png`: confirmación sin plazo para el número verificado.
- `panel-solicitada-sin-verificar-escritorio.png`: la reserva 137 nace en Solicitado, con actor Pasajero.
- `portal-telefono-nuevo-celular.png`: un número nuevo sigue con el plazo para confirmar.
