# HU-42 · Revisa tu pedido y pedido recibido — resultados

Rama `feat/HU-42-revisa-pedido`, 2026-11-11. Web: `src/pedido/pedido.test.tsx`. Backend: `apps/portal/tests/test_portal.py`. Datos sintéticos; las capturas usan un pasajero sintético cuya clave se invalidó al terminar.

| Caso | Esperado | Obtenido |
|---|---|---|
| Revisa tu pedido | Resumen por tipo (vuelo, llegada, salida, recogida, origen, destino, pasajeros y maletas) y el nombre y WhatsApp de la cuenta; nada se envía hasta confirmar | OK (`revisa-tu-pedido-*.png`) |
| Editar datos | Vuelve al formulario con lo escrito | OK |
| Error del servidor | Vuelve al formulario con el error en su campo (p. ej. la hora de llegada si la API de vuelos no respondió) | OK |
| Límite y red | 429 y falla de red se explican sin perder el pedido | OK |
| Pedido recibido | «¡Listo! Recibimos tu pedido», N.º de reserva, «Ver mi viaje» y «Volver al inicio» | OK (`pedido-recibido-*.png`) |

## Límites conocidos

- El N.º de reserva es el número del viaje (el diseño usa un formato «FA-…» que no está definido en el dominio).
- El resumen no muestra el origen del vuelo («Lima → Santiago»): se conoce después de consultar la API.
