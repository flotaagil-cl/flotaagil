# HU-39 · Inicio y pedido en tres tipos — resultados

Rama `feat/HU-39-pedido`, 2026-11-11. Backend: `apps/portal/tests/test_pedido_tres_tipos.py`. Web: `src/pedido/pedido.test.tsx`. Datos sintéticos; las capturas usan un pasajero sintético cuya clave se invalidó al terminar.

| Caso | Esperado | Obtenido |
|---|---|---|
| Inicio en el computador | `/pedir` con pestañas Desde el aeropuerto, Al aeropuerto y En la ciudad, marca de la empresa del pasajero | OK (`pedir-1440-*.png`) |
| Inicio en el celular | Tres opciones sobre el mapa; cada una abre su formulario con volver | OK (`pedir-390-*.png`) |
| Desde el aeropuerto | SCL fijo, vuelo con número y fecha, «Seguimos tu vuelo por ti», destino, pasajeros y maletas | OK |
| API de vuelos sin respuesta | El servidor pide la hora de llegada y el formulario la muestra | OK |
| Al aeropuerto | Hora y tipo del vuelo guardados en VIAJE; recogida sugerida 3 h (internacional) o 2 h (nacional), con «Cambiar» | OK |
| En la ciudad | «Lo antes posible» = ahora + 30 min (DC-10) o programado | OK |
| Capacidad (DC-43) | Pasajeros ≤ mayor capacidad activa al pedir; al asignar no se propone ni acepta un vehículo más chico | OK |
| Panel | El despachador ve pasajeros, maletas y vuelo de salida en la API de viajes | OK |
| Otros roles | `/pedir` lleva a su vista; el pasajero llega a `/pedir` al ingresar | OK |

## Límites conocidos

- El mapa es el de respaldo: sin geocodificar las direcciones antes de pedir, solo muestra el aeropuerto.
- La tarjeta de estimado del diseño (minutos, km, tarifa) y los vehículos cercanos no se muestran: no hay datos reales para eso todavía.
- «Al aeropuerto» lleva pasajeros y maletas aunque el diseño no los muestre, para aplicar DC-43; el número del vuelo de salida (opcional en el diseño) no se pide porque VIAJE solo guarda hora y tipo.
- El aviso de privacidad y los avisos por WhatsApp se aceptan al pedir con la cuenta, y la pantalla lo dice bajo el botón.
- La confirmación es provisoria: «Revisa tu pedido» y «Pedido recibido» llegan con HU-42. «Mis viajes» sigue con la pantalla anterior hasta HU-44.
