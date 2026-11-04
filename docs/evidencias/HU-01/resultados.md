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

## Ajuste del PO: con señal y sin señal (`fix/HU-01-senal`)

DC-28 aprobado, separando «en línea con señal» de «en línea sin señal» (sin posición hace más de 60 s, o sin ninguna), el criterio de HU-02. Suites en esta rama: backend 1053 (98 % de líneas), web 588 (94,4 %).

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Límite | Con señal hasta 60 s desde la última posición; configurable | OK (automática en 5, 59, 61 y 3600 s) |
| Sin ninguna posición | Sin señal | OK (automática y manual) |
| Turno sin posición reciente | Pasa a «sin señal» | OK (manual: 0,1 s) |
| Llega una posición | Pasa a «con señal», avisando por WebSocket | OK (automática y manual: 0,1 s) |
| Dejan de llegar | Pasa a «sin señal», en la revisión de cada 15 s | OK (manual: 61 s) |
| Posición con señal vigente | No avisa | OK (automática) |
| Access vencido en el WebSocket | Cierra con 4401 | OK (automática) |

## Límites conocidos

- **Perder la señal tarda hasta 75 s en verse:** 60 s del criterio más hasta 15 s de revisión, porque no llegar posiciones no genera ningún evento.
- **Solo cuenta la antigüedad:** una posición imprecisa da «con señal», aunque el mapa la marque como no confiable. Es lo que pidió el PO.
- **Latencia medida en local,** con un solo panel y sin carga.
- **La confirmación de una nueva hora de recogida (HU-27) no avisa:** se ve en la revisión periódica.

## Capturas

- `panel-indicadores-escritorio.png`: estado inicial.
- `panel-indicadores-en-vivo-escritorio.png`: tras los cambios, sin recargar.
- `panel-indicadores-celular.png`: como administrador.
- `panel-sin-senal-escritorio.png` y `panel-con-senal-escritorio.png`: ajuste del PO.
