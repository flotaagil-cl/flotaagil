# HU-14 · Notificación de viaje asignado — resultados de pruebas

Rama `feat/HU-14-asignacion`, 2026-11-03. Datos sintéticos (`datos_demo`). La app se probó en el navegador con pantalla de teléfono, contra el backend real. El sonido, la vibración y la notificación del sistema solo se pueden ver en Android.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 611 pruebas en verde | 98 % total; `asignacion.py` 95 % |
| Web (Vitest) | 455 pruebas en verde | 94,3 % total |
| App (Vitest) | 37 pruebas en verde | 87,7 % sentencias en la lógica |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; `verificar-carga` ok | — |

## Casos de prueba

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| El despachador asigna desde el panel (RN-02) | SOLICITADO → ASIGNADO por la máquina de estados, con conductor y vehículo; queda la ASIGNACION (origen MANUAL) | OK (automática y manual) |
| Conductor no Disponible o sin vehículo (RN-01, RN-05) | 409 con el motivo | OK (automática) |
| Conductor con otro viaje en ejecución (RN-03) | 409; no aparece entre los candidatos | OK (automática; manual: en `datos_demo` los disponibles ya tenían viaje, ver captura) |
| Reserva no solicitada o reasignar la misma | 409 | OK (manual: «esta está en ASIGNADO») |
| Conductor o reserva de otra empresa (RN-13) | 400 / 404 | OK (automática) |
| Candidatos | Disponibles sin viaje, el más cercano al origen primero, «sin posición reciente» al final | OK (automática) |
| La app recibe el viaje (alerta visual) | Aviso con origen, destino, pasajero, tarifa, vuelo con hora de llegada y ETA, y cuenta regresiva de 60 s | OK: llegó **362 ms** después de asignar |
| Reconexión de la app | Al reconectarse vuelve a recibir la asignación pendiente, sin repetir la alerta | OK (automática y manual) |
| WebSocket de la app | Solo conductores (4403); sin token 4401; ante 4401 renueva y se reconecta | OK (automática) |
| Alerta sonora y vibración | Tres pitidos y vibración al llegar el viaje; notificación del sistema si la app está en segundo plano | Implementado; probar en Android (guía, prueba G) |

## Pendiente

- Probar en el teléfono el sonido, la vibración y la notificación con la app en segundo plano.
- Solo en el navegador, no en Android: al recargar la app de desarrollo se pierde la sesión. Hay que revisar el almacenamiento web del plugin. No afecta al teléfono: en el emulador la sesión se recuperó tras reiniciarlo.
- Con la app cerrada no llega el aviso. Hace falta push por Firebase, que necesita crear una cuenta; queda para evaluar (PR-13).
- Aceptar, rechazar y la expiración a los 60 s: HU-15.

## Capturas

- `app-viaje-asignado-celular.png`: aviso de viaje asignado en la app.
- `panel-asignar-conductor.png`: diálogo «Asignar conductor» del panel. Aparece sin candidatos porque en `datos_demo` los conductores disponibles ya tenían un viaje (RN-03).
