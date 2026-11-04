# fix/app-peticiones — resultados de pruebas

Rama `fix/app-peticiones`, 2026-11-03. Datos sintéticos, sin emulador. El tiempo límite no se ha probado con el fetch nativo de CapacitorHttp en un teléfono: por eso compite también contra un temporizador, y no depende solo de la señal de aborto.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| App (Vitest) | 71 pruebas en verde, 3 corridas seguidas | 95,3 % sentencias en la lógica |
| Backend (pytest) | Ver el PR | — |

## Casos de prueba

La App real está montada con sesión, API, tiempo límite y canal reales; solo son falsos la red y los plugins nativos.

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| **Caso de HU-16:** el backend registró el cambio, pero la lectura del viaje activo no responde | A los 9 s sigue el estado anterior; a los 12 s la pantalla se corrige sola | OK |
| Se pierde la respuesta de la acción, pero el servidor la registró | Muestra el estado real, sin error | OK |
| La acción no llegó al servidor | Avisa, sigue en el mismo paso y se puede repetir | OK |
| Tres lecturas seguidas colgadas | Insiste con espera creciente hasta lograrlo | OK |
| Evento del canal con una lectura colgada | Se corrige sin esperar el plazo | OK |
| Lectura atrasada | No vuelve al estado anterior | OK |
| Después de cada acción | Vuelve a pedir perfil y viaje activo | OK |
| Cuerpo de la respuesta a medias, o señal de aborto ignorada | Corta igual a los 10 s | OK |
| Evento del canal en cada acción (backend) | `en-camino`, `a-bordo` y `finalizar` lo emiten | OK |

**Comprobación de la prueba:** sin el tiempo límite fallan 4 de los 7 casos de la App, incluido el de HU-16.

## En un navegador real, contra el backend real (reserva 109)

| Qué se hizo | Obtenido |
|---|---|
| Retener de verdad la lectura del viaje activo y pulsar «Voy en camino» | Pantalla corregida a los **226 ms**, por el evento del canal |
| Pasar a bordo por la API, fuera de esa pantalla | La pantalla se enteró por el canal |
| Finalizar por la API, fuera de esa pantalla | La tarjeta del viaje desapareció sola |

## Lo que sigue sin saberse

No se encontró por qué esa petición no respondió en la prueba de HU-16. Lo corregido es la consecuencia: la pantalla ya no queda atrapada.

Si un **refresh** agota el tiempo después de que el servidor ya lo rotó, la app se queda con un refresh invalidado y pedirá iniciar sesión. Es poco probable, y ya podía pasar con un corte de red.

## Captura

- `app-corregida-sola-celular.png`
