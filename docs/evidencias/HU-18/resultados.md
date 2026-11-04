# HU-18 · Mi turno: viajes completados — resultados de pruebas

Rama `feat/HU-18-mi-turno`, 2026-11-04. Prueba manual contra el stack principal, en el navegador con el Vite de `app/` que ya estaba activo, con datos sintéticos nuevos (conductores `hu18.*` y reservas 118 a 120). No se borró nada. Se aplicó la migración `flota.0004` a la base principal: solo agrega dos columnas nulas.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 928 pruebas en verde | 98 % total |
| App (Vitest) | 80 pruebas en verde | 95,3 % sentencias en la lógica; la pantalla se prueba con su propio archivo |
| Web (Vitest) | 532 pruebas en verde (solo cambian los tipos generados) | 94,2 % total |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; sin migraciones pendientes | — |

## Decisiones del PO

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Inicio y fin (DC-26) | «Empezar turno» guarda el inicio y limpia el fin; «Terminar turno» guarda el fin | OK (automática y manual) |
| Repetir la acción | No reinicia el turno ni mueve el fin | OK (automática) |
| Empezar rechazado | No registra un inicio | OK (automática) |
| Cuenta deshabilitada | Termina el turno | OK (automática) |
| En turno | Viajes FINALIZADOS del turno actual, sin los anteriores ni los de otro conductor | OK (automática y manual) |
| Fuera de turno | Los del último turno | OK (automática y manual) |
| Turno nuevo | Parte vacío | OK (automática y manual) |
| Otros estados | No aparecen | OK (automática, 6 estados) |
| Datos del viaje | Hora, origen, destino, monto y método | OK (automática y manual) |
| Totales | Por método de pago y total | OK (automática; manual: Efectivo 2 / $27.000, Tarjeta 1 / $9.500, total $36.500) |
| Cierre por la central (HU-05) | Marcado, y suma en los totales | OK (automática y manual: reserva 120) |
| Sin turnos | Lo dice | OK (automática y manual) |
| Sin conexión | Lo dice y permite reintentar | OK (automática) |
| Rol del panel / sin sesión | 403 / 401 | OK (automática; 403 también manual) |
| Celular (390 px) | Sin desborde horizontal | OK (manual) |

## Detalles

- **Hora de cada viaje:** la de su paso a FINALIZADO en HISTORIAL_ESTADO.
- **Fallo corregido en las pruebas:** la fecha salía como `4-11`, porque `es-CL` no rellena el día.
- **Primer intento de la prueba manual:** expiró esperando la pantalla de inicio, justo después de migrar. Causa no confirmada. Lo que muestran los registros del backend (hora UTC):
  - El script obtuvo sus tokens a las 16:41:15, pero el POST de login del navegador **nunca llegó al backend**. El siguiente es de las 16:42:11, ya del diagnóstico.
  - No fue la migración ni el backend: ya estaba migrado, y otro cliente recibió 200 en `/api/app/perfil/` a las 16:41:29.
  - Por lo tanto, se perdió entre la página y el proxy del Vite de `app/`. La pantalla no se capturó, así que no se sabe más.
  - No se reprodujo: funcionó la repetición, y después 3 de 3 logins justo tras un `migrate`, estos por el build de la app, porque ese Vite ya no estaba activo.
- **Hallazgo aparte, de esa misma prueba:** entre las 16:37:48 y las 16:41 UTC, `/api/app/perfil/` y `/ws/conductor/` fallaron en el stack principal para un cliente conectado, porque el modelo se editó antes de aplicar la migración: el código montado se recarga solo. En HU-25 volvió a pasar unos minutos, porque el primer `migrate` falló. Desde `fix/HU-25-declaracion` la migración se aplica en el mismo paso que la edición.

## Límites conocidos

- **Solo se guarda el último turno:** no hay historial de turnos anteriores (DC-26).
- **Conductores ya en turno al migrar:** tienen `turno_inicio` NULL y ven «Aún no tienes turnos registrados» hasta empezar uno nuevo. No se rellenó con un dato inventado.
- **Sin probar en un teléfono:** prueba H de `docs/guia-prueba-app-android.md`.

## Capturas

- `app-mi-turno-en-curso-celular.png`: turno en curso, con un viaje cerrado por la central y los totales.
- `app-mi-turno-terminado-celular.png`: último turno, fuera de turno.
