# HU-28 · Alertas de demora, cancelación o desvío — resultados de pruebas

Rama `feat/HU-28-alertas`, 2026-11-04. Datos sintéticos, en un stack aislado, con `simular_vuelo`. **Sin probar contra FlightAware real.**

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 840 pruebas en verde | 98 % total |
| Web (Vitest) | 503 pruebas en verde | 94,9 % total; `src/alertas` 100 % sentencias |
| App (Vitest) | 72 pruebas en verde (sin cambios en esta HU) | 95,3 % sentencias en la lógica |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; `verificar-carga` ok | — |

## Caso de prueba CP-21

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| ETA cambia 15 min o más | Alerta | OK (automática y manual: visible a los 10,9 s) |
| ETA cambia menos, o bajo el umbral de la empresa | Sin alerta | OK (automática) |
| Vuelo cancelado o desviado | Una alerta | OK (automática y manual) |
| API caída tras los reintentos, o vuelo que no aparece | Alerta «sin datos» | OK (automática) |
| Fallo que se recupera con un reintento | Sin alerta | OK (automática) |
| La API vuelve | «Sin datos» se resuelve sola | OK (automática) |
| Alerta sin atender y la ETA sigue cambiando | Se actualiza, no se acumula | OK (automática) |
| Atendida, con la misma ETA | No se repite | OK (automática) |
| Atendida y la ETA se mueve 15 min más | Avisa de nuevo | OK (automática) |
| Alerta visual | En cualquier pantalla, con enlace a la reserva | OK (automática y manual) |
| Alerta sonora | Suena solo con alertas nuevas; lo que ya estaba al abrir, no | OK (automática y manual: 2 tonos pedidos por alerta) |
| Registro | Tipo, detalle, quién y cuándo | OK (automática y manual) |
| Marca en la reserva | En el listado y la ficha, hasta atenderla | OK (automática y manual) |
| Confirmar o descartar la nueva hora | También atiende la alerta del cambio | OK (automática) |
| Otra empresa (RN-13) | No la ve ni la atiende | OK (automática) |
| Conductor | 403 y sin la zona de alertas | OK (automática) |
| Listado de reservas | Sin una consulta por fila | OK (automática) |

## Límites conocidos

- **El sonido no se oyó:** el navegador de prueba no tiene altavoz. Se comprobó que el panel pide los tonos. Prueba pendiente en un equipo real.
- **El navegador puede bloquear el audio** hasta la primera interacción con la página. La alerta visual queda igual.
- **Revisión cada 15 s,** no un canal en vivo: el vuelo se consulta como mucho cada 10 min, y evita un WebSocket más en todas las pantallas.

## Capturas

- `panel-alerta-escritorio.png`: alerta sobre el listado, con la reserva marcada.
- `panel-alerta-ficha-celular.png`: ficha de la reserva.
