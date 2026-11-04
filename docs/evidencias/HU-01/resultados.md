# HU-01 · Panel de indicadores de reservas y vehículos — resultados de pruebas

Rama `feat/HU-01-indicadores`, 2026-11-04. Prueba manual contra el stack principal, con una reserva sintética nueva (125, cancelada en la misma prueba) y un conductor sintético `hu18.*` que empezó y terminó su turno. No se borró nada. El panel se sirvió desde un build con un servidor estático mínimo, sin un Vite adicional. Se reiniciaron `worker` y `beat` para que sus cambios de estado también avisen.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 1006 pruebas en verde | 98 % total; `apps/reservas/indicadores.py` 100 % |
| Web (Vitest) | 572 pruebas en verde | 94,2 % total; `src/paginas` 91,3 % |
| App (Vitest) | 80 pruebas en verde (sin cambios en esta HU) | — |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; sin migraciones pendientes; `verificar-carga` ok | — |

## Criterios

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Reservas del día | Por estado, con todos los estados, según la fecha de recogida en hora de Chile | OK (automática y manual) |
| Vehículos | En línea y fuera de línea, sin contar inactivos ni cuentas deshabilitadas (DC-28) | OK (automática y manual) |
| Sin recargar | Reserva creada y cancelada, turno empezado y terminado | OK (manual: 10 a 68 ms, cero navegaciones) |
| Qué avisa | Crear y cancelar reservas, turno y desactivar vehículos; una posición GPS no | OK (automática, con el WebSocket real) |
| Conexión perdida | Lo dice, conserva los datos y se reconecta; 4401 renueva el access | OK (automática) |
| Al salir de Inicio | Cierra la conexión | OK (automática) |
| Enlaces | Al listado filtrado por fecha y estado | OK (automática y manual) |
| Otra empresa (RN-13) | No cuenta ni avisa | OK (automática) |
| WebSocket | Sin token 4401; conductor 4403; origen ajeno no conecta | OK (automática) |
| Conductor en la API | 403 | OK (automática y manual) |
| Celular (390 px) | Sin desborde horizontal | OK (manual) |

## Límites conocidos

- **DC-28 está por aprobar:** qué significa «en línea» y que también lo vea el despachador.
- **Latencia medida en local,** con un solo panel y sin carga.
- **La confirmación de una nueva hora de recogida (HU-27) no avisa:** se ve en la revisión de cada minuto.

## Capturas

- `panel-indicadores-escritorio.png`: estado inicial.
- `panel-indicadores-en-vivo-escritorio.png`: tras los cambios, sin recargar.
- `panel-indicadores-celular.png`: como administrador.
