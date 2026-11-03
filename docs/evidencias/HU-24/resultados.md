# HU-24 · Calificación del servicio (1 a 5) — resultados de pruebas

Rama `feat/HU-24-calificacion`, 2026-11-03. Datos sintéticos. **Probado con el notificador de desarrollo y con un doble de Twilio: no se ha enviado ningún WhatsApp real.**

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 705 pruebas en verde | 98 % total; `verificacion.py` 97 % |
| Web (Vitest) | 464 pruebas en verde (ver nota) | 94,4 % total |
| App (Vitest) | 51 pruebas en verde (sin cambios en esta HU) | 87,9 % sentencias en la lógica |
| Estático | ruff, bandit, ESLint; OpenAPI validado; `verificar-carga` ok | — |

**Nota:** en una corrida falló 1 prueba de la web, ajena a esta HU: `formulario-ui.test.tsx`, «9 dígitos que empiezan con 9…». Pasó en 3 corridas aisladas y en la suite completa siguiente. Es intermitente; no se buscó la causa.

## Casos de prueba

El backlog no asigna CP a esta HU.

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Finalizar un viaje | Encuesta de 1 a 5, marcada como opcional | OK (automática y manual: reserva 107) |
| Twilio caído al enviar la encuesta (RN-14) | El viaje igual queda FINALIZADO y con pago | OK (automática) |
| Finalizar rechazado | Sin encuesta | OK (automática) |
| Responder del 1 al 5 | CALIFICACION asociada al viaje y a su conductor | OK (automática; manual: «4») |
| «0», «6», «45», «5 minutos», «gracias» o vacío | No califica; es conversación | OK (automática; manual: «gracias») |
| Segunda respuesta | Vale la primera | OK (automática; manual: «1» no cambió el «4») |
| Mismo webhook dos veces | Una sola calificación | OK (automática) |
| Responder fuera de plazo (DC-19) | No califica | OK (automática) |
| Plazo configurado por empresa | Se respeta | OK (automática) |
| Dos viajes sin calificar y sin citar | Va al último | OK (automática) |
| Citar un viaje fuera de plazo | No cae en otro viaje | OK (automática) |
| Número con un viaje en curso o una solicitud pendiente | No califica ni cambia el estado | OK (automática; manual: «5» en EN_CAMINO) |
| Puntaje fuera de rango en la base | Rechazado por restricción | OK (automática) |
| Ficha del panel | Muestra «4 de 5»; sin calificación no muestra la fila | OK (automática y manual) |

## Criterio parcial

«Visible en HU-06»: HU-06 es del Sprint 4. Por ahora la nota se ve en la ficha del viaje y queda asociada al conductor por el viaje. El promedio por conductor se hará en HU-06. **Aceptado como parcial** el 2026-11-03.

## Capturas

- `panel-calificacion-escritorio.png` y `panel-calificacion-celular.png`: ficha de la reserva 107 con la calificación.
