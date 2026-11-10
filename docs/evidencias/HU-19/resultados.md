# HU-19 · Formulario web de solicitud sin cuenta — resultados de pruebas

Evidencia tardía: la HU se construyó en el Sprint 1 (`feat/HU-19-portal`, `feat/HU-19-web`) y no tenía su `resultados.md`. Se probó el 2026-11-10 sobre `chore/estabilizacion-docs`. Stack de desarrollo con el notificador de WhatsApp de desarrollo (sin Twilio), datos sintéticos (teléfono +56911125449).

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 39 pruebas de `portal/tests/test_portal.py` en verde; suite completa: 1069 en verde | 98 % total |
| Web (Vitest) | 66 pruebas de `portal.test.tsx` y `telefono.test.ts` en verde | — |

## Casos de prueba

CP-07 y CP-09 según el backlog (CP-07 en HU-19 y HU-20). En HU-20, CP-09 cubre la idempotencia del webhook; aquí cubre el lado del portal: el límite de RN-06 y la expiración. El texto exacto del informe no está en el repositorio.

| CP | Qué se probó | Esperado | Obtenido |
|---|---|---|---|
| CP-07 | Enviar el formulario vacío en el celular | Un mensaje por campo y por aceptación | OK (manual y automática) |
| CP-07 | Solicitud completa urbana | PENDIENTE_CONFIRMACION, canal WEB, aceptación de privacidad y de WhatsApp guardadas, plantilla de verificación enviada | OK (manual: reserva 132; plantilla SALIENTE en SENT una vez arriba el worker) |
| CP-07 | Confirmación visual | Pantalla «Solicitud recibida» con el número y la hora límite | OK (manual) |
| CP-07 | Empresa inexistente | Página «no disponible» | OK (manual) |
| CP-07 | Campo trampa lleno | Responde como si nada y no crea la reserva | OK (automática) |
| CP-09 | Cuarta solicitud del mismo número en 15 min | Rechazada con el aviso «Ya enviaste varias solicitudes…»; quedan 3 | OK (manual: reservas 132 a 134) |
| CP-09 | El límite es por empresa | Otra empresa acepta el mismo número | OK (automática) |
| CP-09 | Sin respuesta en 15 min | CANCELADO, origen SISTEMA | OK (manual: reserva 132, con la hora corrida a 16 min antes y `expirar_pendientes`) |
| — | Límite por IP por minuto | 429 | OK (automática) |

## Observaciones

- La primera corrida del guion se cortó por un selector ambiguo (el campo «WhatsApp» y la casilla de avisos tienen la misma palabra) y no creó solicitudes del portal.
- La plantilla quedó en cola mientras el worker estuvo detenido y se envió al levantarlo: el portal no espera a Twilio.
- PR-04 (texto del aviso de privacidad) y PR-05 (portal en inglés) siguen abiertos.

## Capturas

- `portal-formulario-celular.png`: formulario vacío.
- `portal-validacion-celular.png`: mensajes de validación.
- `portal-confirmacion-celular.png`: solicitud recibida.
- `portal-limite-telefono-celular.png`: cuarta solicitud rechazada.
- `panel-solicitud-expirada-escritorio.png`: la reserva 132 expirada en el panel.
- `portal-empresa-inexistente-celular.png`: empresa inexistente.
