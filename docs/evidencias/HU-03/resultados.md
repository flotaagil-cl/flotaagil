# HU-03 · Ingresar, editar y cancelar reservas — resultados de pruebas

Evidencia tardía: la HU se construyó en el Sprint 1 (`feat/HU-03-reservas`, `feat/HU-03-web`) y no tenía su `resultados.md`. Se probó el 2026-11-10 sobre `chore/estabilizacion-docs`, que contiene todo el Sprint 4. Stack de desarrollo, datos sintéticos (pasajeros «Prueba Sintética», teléfonos +5691111xxxx).

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 153 pruebas de la HU en verde (`reservas/tests/test_api.py`, `test_estados.py`); suite completa: 1069 en verde | 98 % total |
| Web (Vitest) | 145 pruebas de `src/reservas` en verde (incluye las de HU-05, HU-14 y HU-27 que viven ahí) | — |

## Casos de prueba

Las definiciones de CP-05 y CP-06 se tomaron del backlog (HU-03: CP-05 y CP-06); el texto exacto del informe no está en el repositorio.

| CP | Qué se probó | Esperado | Obtenido |
|---|---|---|---|
| CP-05 | Guardar el formulario vacío | Un mensaje por campo obligatorio, sin crear nada | OK (manual y automática) |
| CP-05 | Alta con pasajero, canal Teléfono, origen, destino y recogida | Reserva en SOLICITADO, con historial «Solicitado · Despachador» | OK (manual: reserva 131) |
| CP-05 | Teléfono fuera de E.164, origen fuera de la zona, recogida pasada, vuelo en un viaje urbano | 400 con el campo | OK (automática) |
| CP-06 | Editar el destino en SOLICITADO | Cambia y se regeocodifica | OK (manual: «Costanera Center, Providencia») |
| CP-06 | Editar después del despacho (ASIGNADO a CANCELADO) | 409, sin cambios | OK (automática; manual: la reserva cancelada muestra «ya no se puede editar») |
| CP-06 | Cancelar sin motivo | El diálogo lo exige | OK (manual y automática) |
| CP-06 | Cancelar con motivo | CANCELADO, origen DESPACHADOR, historial y AUDITORIA `CANCELACION` | OK (manual: reserva 131) |
| CP-06 | Cancelar en ASIGNADO, PASAJERO_A_BORDO o FINALIZADO | 409 | OK (automática) |
| — | Reserva de otra empresa (RN-13) | 404 al ver, editar o cancelar | OK (automática) |

## Observaciones

- La primera corrida del guion creó y canceló también la reserva 130, idéntica a la 131.
- PR-03 sigue abierto: el teléfono del pasajero no se corrige desde la edición.

## Capturas

- `panel-nueva-validacion-escritorio.png`: formulario vacío con los mensajes de cada campo.
- `panel-reserva-creada-escritorio.png`: reserva 131 en Solicitado.
- `panel-reserva-editada-escritorio.png`: destino editado.
- `panel-cancelar-sin-motivo-escritorio.png`: el diálogo exige el motivo.
- `panel-reserva-cancelada-escritorio.png`: reserva cancelada con motivo e historial.
- `panel-editar-cancelada-escritorio.png`: la reserva cancelada ya no se edita.
