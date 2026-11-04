# HU-30 · Chat de WhatsApp desde el panel — resultados de pruebas

Rama `feat/HU-30-chat-whatsapp`, 2026-11-04. Prueba manual contra el stack principal, con pasajeros sintéticos nuevos y las reservas 122 a 124, canceladas al terminar. No se borró nada. Los mensajes entrantes entraron por el mismo código del webhook, sin Twilio, y el envío usó el notificador de desarrollo. El panel se sirvió desde un build con un servidor estático mínimo, sin un Vite adicional. Hubo que reiniciar el worker una vez para que cargara la tarea nueva.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 988 pruebas en verde | 98 % total; `apps/reservas/conversaciones.py` 99 % |
| Web (Vitest) | 565 pruebas en verde | 94,4 % total |
| App (Vitest) | 80 pruebas en verde (sin cambios en esta HU) | — |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; sin migraciones pendientes; `verificar-carga` ok | — |

## Caso de prueba CP-27

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Bandeja | Por pasajero, la más reciente primero, con la reserva vinculada | OK (automática y manual) |
| Mensaje libre del pasajero | Aparece en su conversación | OK (automática y manual, por el código del webhook) |
| Ventana | 24 h desde el último mensaje del pasajero; un saliente no la abre | OK (automática en los bordes de 23:59 y 24:01) |
| Dentro de la ventana | Texto libre, sin plantilla | OK (automática y manual) |
| Fuera de la ventana | Campo deshabilitado con el aviso de PR-11; 409 en la API | OK (automática y manual) |
| Ventana cerrada al enviar | Aviso, y el texto no se pierde | OK (automática) |
| Registro | Queda con el autor y la reserva | OK (automática y manual) |
| Envío | Lo hace el worker; repetir la tarea no duplica | OK (automática; manual: pasa a Enviado, 1 mensaje) |
| Fallas | Rechazo de Twilio o sin broker: FAILED, visible como «No se pudo enviar» | OK (automática, con un doble de Twilio) |
| Texto inválido | Vacío o de más de 1024: 400 | OK (automática) |
| Otra empresa (RN-13) | 404 | OK (automática y manual) |
| Conductor | 403 | OK (automática) |
| Celular (390 px) | Sin desborde horizontal | OK (manual) |

## Límites conocidos

- **Sin plantillas fuera de la ventana:** pendiente PR-11, según la decisión del PO.
- **Sin probar contra Twilio real.**
- **El hilo muestra los últimos 200 mensajes.**
- **Mensajes nuevos con 5 a 15 s de demora:** se revisan por tiempo, sin WebSocket.
- **Un teléfono en dos empresas sin reserva identificable:** su mensaje queda en la primera. Viene de HU-20.

## Capturas

- `panel-bandeja-escritorio.png`: bandeja con los datos del stack.
- `panel-hilo-dentro-escritorio.png`: respuesta enviada.
- `panel-hilo-fuera-escritorio.png`: campo deshabilitado con el aviso.
- `panel-hilo-celular.png`: hilo en celular.
