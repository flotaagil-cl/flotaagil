# HU-32 · Reserva de contingencia — resultados

Rama `feat/HU-32-contingencia`, 2026-11-10. CC-15 (#34). Solo backend, validado con pruebas automáticas (`reservas/tests/test_contingencia.py`, 29 en verde). Datos sintéticos.

| Caso | Esperado | Obtenido |
|---|---|---|
| CP-37: finalizado con horas reales | FINALIZADO, pago con registro a la hora de término, historial PASAJERO_A_BORDO → FINALIZADO marcado contingencia | OK |
| CP-37: cancelado | CANCELADO con motivo y origen según el rol; sin pago | OK |
| CP-37: sin avisos ni encuesta | Ningún WhatsApp | OK |
| CP-37: auditoría | `RESERVA_CONTINGENCIA` con folio y usuario | OK |
| Folio repetido en la empresa / en otra empresa | 400 / se acepta | OK |
| Folio vacío, con espacios o de más de 20 caracteres | 400 | OK |
| Hora futura, más de 7 días, límite configurable | 400, 400, se acepta con 10 días | OK |
| Finalizado sin conductor, método o monto; cancelado sin motivo | 400 | OK |
| Conductor de otra empresa; método CONVENIO | 400 | OK |
| Turno que contiene la recogida real (cerrado o abierto) / sin turno | Se liga con su vehículo / queda sin turno | OK |
| Administrador y despachador sí, conductor no; el alta normal no acepta el canal | 201, 403, 400 | OK |
| Reporte `contingencia`: por folio, «Sin turno», total | OK | OK |
| La liquidación de HU-06 lo cuenta el día real del pago | OK | OK |

## Límites conocidos

- Sin formulario en el panel: se ingresa por `POST /api/viajes/contingencia/`. El reporte `contingencia` tampoco tiene pestaña en Reportes.
- El historial de un finalizado no reconstruye los estados intermedios (ASIGNADO a EN_ZONA).
