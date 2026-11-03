# HU-21 · Avisos de estado y cancelación por WhatsApp — resultados de pruebas

Rama `feat/HU-21-avisos`, 2026-11-03. Datos sintéticos. **Probado con el notificador de desarrollo y con un doble de Twilio: no se ha enviado ningún WhatsApp real** (PR-11, `docs/credenciales-externas.md`).

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 679 pruebas en verde | 98 % total; `verificacion.py` 96 % |
| Web (Vitest) | 462 pruebas en verde | 94,4 % total (sin cambios en esta HU) |
| App (Vitest) | 51 pruebas en verde | 87,9 % sentencias en la lógica (sin cambios en esta HU) |
| Estático | ruff, bandit; OpenAPI sin diferencias | — |

## Casos de prueba

| Caso | Qué se probó | Esperado | Obtenido |
|---|---|---|---|
| CP-16 | Reserva creada en el panel | Aviso de confirmación, con la opción de responder Cancelar | OK (automática y manual: 105 y 106) |
| CP-16 | Conductor asignado | Sin aviso al asignar; con nombre, vehículo y patente al aceptar | OK (automática y manual: 106) |
| CP-16 | El conductor rechaza | Sin aviso | OK (automática) |
| CP-16 | En camino | Aviso con el conductor y el punto de recogida | OK (automática y manual: 106) |
| CP-16 | EN_ZONA por geocerca | «Tu vehículo te espera» con la patente | OK (automática y manual: 106) |
| CP-16 | EN_ZONA indicado por el conductor (DC-17) | Sin aviso: el pasajero ya subió | OK (automática) |
| CP-17 | Cancelar sin conductor (RN-09) | CANCELADO, actor PASAJERO, origen PASAJERO | OK (automática y manual: 105) |
| CP-17 | Cancelar en ASIGNADO, ACEPTADO, EN_CAMINO, EN_ZONA o a bordo (RN-09) | Sin cambios; responde que tiene conductor | OK (automática; manual: 106 en ASIGNADO) |
| CP-17 | Lo asignan justo al cancelar | Responde que tiene conductor | OK (automática) |
| CP-17 | «No» suelto en un viaje ya confirmado | Sin cambios; es conversación | OK (automática) |
| CP-17 | Dos reservas y «Cancelar» sin citar un mensaje | No cancela ninguna y pide citar el mensaje | OK (automática) |
| CP-17 | Dos reservas y «Cancelar» citando un mensaje | Cancela solo la citada | OK (automática) |
| — | Twilio caído o error inesperado al avisar | El estado se conserva y el mensaje queda en FAILED | OK (automática) |
| — | Plantilla configurada o sin plantilla | ContentSid o texto | OK (automática) |
| — | Datos de demostración | No envían avisos | OK (automática) |
| — | Teléfono en el log | Enmascarado | OK (automática y manual) |

## Conversación de la reserva 106 (manual)

```
SALIENTE  Hola Prueba, Transportes Andes Demo SpA confirmó tu viaje para el 04-11 22:30. Te avisaremos por aquí cuando tengas conductor. Si necesitas anularlo antes, responde Cancelar.
ENTRANTE  Cancelar
SALIENTE  Tu viaje ya tiene conductor asignado, así que no se puede cancelar por aquí. Comunícate con la central.
SALIENTE  Hola Prueba, tu conductor es Muriel Moreno, en Kia Rio, patente DMAD13.
SALIENTE  Muriel Moreno va en camino a recogerte en Plaza de Armas, Santiago.
SALIENTE  Tu vehículo te espera en Plaza de Armas, Santiago. Patente DMAD13.
```

## Hallazgo corregido

Una prueba encontró que un error inesperado al enviar un aviso rompía la respuesta de la API: al registrar el fallo, Django pide el nombre de la función, y un `functools.partial` no lo tiene.

## Límites conocidos

- **Fuera de la ventana de 24 h el texto no llega.** Una reserva hecha por teléfono, con un pasajero que nunca ha escrito, solo recibe avisos con plantillas aprobadas. Sin ellas el mensaje queda en FAILED.
- **El envío es síncrono.** Si Twilio no responde, la respuesta al conductor puede tardar unos 16 s (3 intentos de 5 s, más esperas). Se resuelve al pasar el envío a Celery (PR-11).
- La cancelación por el pasajero aparece en la ficha, pero no se avisa al despachador con una alerta.

## Capturas

- `panel-cancelada-por-whatsapp-escritorio.png` y `panel-cancelada-por-whatsapp-celular.png`: ficha de la reserva 105, cancelada por el pasajero.

Los avisos no tienen pantalla propia: la evidencia es la conversación de arriba, leída de MENSAJE_WHATSAPP.
