# HU-44 · Mis viajes y cancelar — resultados

Rama `feat/HU-44-mis-viajes`, 2026-11-11. Backend: `apps/reservas/tests/test_tu_viaje.py` (cancelar con motivo). Web: `src/viajes/mis-viajes.test.tsx`. Datos sintéticos; las capturas usan un pasajero sintético cuya clave se invalidó al terminar.

| Caso | Esperado | Obtenido |
|---|---|---|
| Mis viajes | Próximos (ordenados por recogida) y anteriores (finalizados y cancelados), con insignia; cada uno abre «Tu viaje» | OK (`mis-viajes-*.png`) |
| Cancelar (RN-09) | Solo sin conductor: diálogo con motivo, «Sí, cancelar viaje» y «Volver»; Esc cierra sin cancelar | OK (`cancelar-viaje-*.png`) |
| Motivo | Queda en el motivo de cancelación del viaje | OK |
| Conductor ya aceptó | 409: «para cancelar, contacta a la central» | OK |
| Menú de la cuenta | «Mis viajes» y «Mi cuenta» (datos y eliminar la cuenta) | OK |

## Límites conocidos

- «Mi cuenta» abre la pantalla anterior (con eliminar la cuenta) hasta «Mi perfil» de HU-45.
- La lista trae la primera página de la API (las reservas más recientes).
