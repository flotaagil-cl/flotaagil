# HU-43 · Tu viaje — resultados

Rama `feat/HU-43-tu-viaje`, 2026-11-11. Backend: `apps/reservas/tests/test_tu_viaje.py`. Web: `src/viajes/tu-viaje.test.tsx`. Datos sintéticos; las capturas usan un pasajero sintético cuya clave se invalidó al terminar.

| Caso | Esperado | Obtenido |
|---|---|---|
| Solo su viaje | Un viaje ajeno o de otra empresa responde 404; otros roles 403 | OK |
| Sin conductor | «Estamos buscando tu conductor»; ni nombre, ni vehículo, ni patente (también en ASIGNADO) | OK |
| Con conductor (desde ACEPTADO) | Nombre, vehículo, patente y aviso por WhatsApp | OK (`tu-viaje-*.png`) |
| Vuelo | Número, estado (a tiempo, atrasado…) y hora estimada de llegada | OK |
| Avance | Línea de tiempo con el paso en curso marcado; textos de aeropuerto o ciudad | OK |
| Sin datos del personal | El historial solo trae estado y hora | OK |
| Cancelar | Fuera de los estados cancelables: «Para cancelar, contacta a la central.» | OK |
| Actualización | El estado se vuelve a consultar cada 20 s | OK |

## Límites conocidos

- Sin tiempo estimado de llegada del conductor («Llega en 12 min» del diseño): no hay ETA del conductor para el portal todavía.
- El vehículo no tiene color en el dominio; se muestra marca y modelo.
