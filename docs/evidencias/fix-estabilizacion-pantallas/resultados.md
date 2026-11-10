# Pantallas pendientes (HU-31, HU-32, DC-35) — resultados

Rama `fix/estabilizacion-pantallas`, 2026-11-10. Decisiones del PO del 2026-11-10. Datos sintéticos.

| Caso | Esperado | Obtenido |
|---|---|---|
| Reserva de contingencia (despachador) | Formulario con folio, pasajero, horas reales, resultado, conductor, método y monto o motivo; abre la reserva creada | OK (web y manual: folio C-61299, reserva 139) |
| Validación y errores del servidor | Mensajes por campo; folio repetido en su campo | OK (web) |
| Conductores para el formulario | Todos los de la empresa, para administrador y despachador; el conductor no | OK (automática) |
| Conciliación por folio en Reportes | Folios, montos, «Sin turno» y total de viajes sin turno | OK (automática, web y manual) |
| «Terminar turno» en la ficha del conductor | Pide motivo y confirmación; queda No disponible y el turno con CIERRE_ADMINISTRATIVO; en viaje no se ofrece | OK (web y manual) |
| El administrador no crea convenios | Sin botón ni ruta en el panel; la API responde 405 | OK (automática y web) |
| Convenio sin cuenta | Historial: edita y desactiva; no se reactiva (409) ni ofrece restablecer | OK (automática y web) |

## Límites conocidos

- El formulario de contingencia no ofrece vuelo ni tarifa (la API acepta tarifa).

## Capturas

- `panel-reserva-contingencia-escritorio.png`
- `panel-conciliacion-contingencia-escritorio.png`
- `panel-terminar-turno-escritorio.png`
