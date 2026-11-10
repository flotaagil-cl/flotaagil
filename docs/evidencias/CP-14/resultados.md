# CP-14 · Asignación con dos peticiones simultáneas — resultados

Rama `test/CP-14-concurrencia-asignacion`, 2026-11-10. Solo backend: `reservas/tests/test_asignacion_concurrencia.py` (3 en verde, PostgreSQL). Mismo patrón determinista que `cuentas/tests/test_concurrencia.py`: una transacción «llave» toma la fila, las dos peticiones HTTP reales se lanzan en hilos y pg_stat_activity confirma que **las dos** esperan el bloqueo a la vez antes de soltarla.

| Caso | Esperado | Obtenido |
|---|---|---|
| Misma reserva a dos conductores (llave: fila del viaje) | Una 200 y una 409; una ASIGNACION; el viaje con el ganador | OK |
| Mismo conductor a dos reservas (llave: fila del conductor) | Una 200 y una 409 por RN-03; una ASIGNACION; la otra reserva sigue SOLICITADO | OK |
| Posiciones con el viaje bloqueado: el conductor se puede actualizar (como en una cancelación) | Sí | OK con el arreglo; **falla con el código anterior** |

## Orden de bloqueo revisado

| Camino | Orden | Resultado |
|---|---|---|
| `asignar` | viaje → conductor | Correcto |
| `responder` (aceptar o rechazar) | asignación → viaje → conductor | Correcto |
| `expirar_asignaciones` | asignación (`skip_locked`) → viaje | Correcto |
| `cancelar_viaje` | viaje → conductor | Correcto |
| Cierre o anulación forzada (HU-05) | viaje → conductor | Correcto |
| Finalizar y estados de la app (HU-16) | viaje → conductor | Correcto |
| Turno de la app, deshabilitar y cierre administrativo | solo conductor (los viajes se leen sin bloquear) | Correcto |
| Cierre de caja (HU-31) | solo turno | Correcto |
| **Recepción de posiciones** (`PosicionesView`) | **conductor (FOR UPDATE) → viaje** | **Invertido. Corregido** |

**El camino invertido.** `PosicionesView` tomaba la fila del conductor con `FOR UPDATE` para poner en serie los lotes. Dentro de esa transacción, la inserción en POSICION_GPS (FK a VIAJE) toma `KEY SHARE` del viaje, y `marcar_en_zona` lo bloquea con `FOR UPDATE`. Una cancelación o un cierre forzado del mismo viaje toma el viaje y luego actualiza el conductor: las dos peticiones podían esperarse mutuamente y PostgreSQL abortaba una con deadlock (500).

**Corrección.** Los lotes se ponen en serie con un bloqueo consultivo por conductor (`pg_advisory_xact_lock`), que no toma la fila del conductor, y `marcar_en_zona` corre después de esa transacción.

## Límites conocidos

- Las pruebas fuerzan el cruce con una llave; no miden cuántas peticiones por segundo soporta la asignación (eso es k6).
