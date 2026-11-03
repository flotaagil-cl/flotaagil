# Bitácora de avance

Una fila por HU o tarea de la cola. Estado: «En revisión» (rama subida, PR por abrir) o «Bloqueada» (con el motivo en pendientes).

| Fecha | HU | Rama | SP | Estado | Resumen | Pendientes |
|---|---|---|---|---|---|---|
| 2026-11-03 | HU-10 · Administrar conductores y vehículos | `feat/HU-10-flota` | 8 | En revisión | Vehículos y conductores con sus cuentas desde el panel, carga por CSV, contraseña temporal con cambio obligatorio y logout de la app (cierra PR-02 y PR-06). | Abrir el PR (Carlos). Alerta moderada de `npm audit` (minimatch, solo herramientas de desarrollo). |
| 2026-11-03 | chore/app-base · Base de la app del conductor | `chore/app-base` | — (tarea técnica) | En revisión | Login de la app con sesión segura (Keystore), cambio de contraseña temporal, consentimiento RN-18 y envío del GPS en turno que sobrevive al vencimiento del access en segundo plano (probado en emulador). | Prueba en teléfono real (guía en docs/guia-prueba-app-android.md). Intervalo nativo del GPS y batería (A1/A2 de la PoC). |
| 2026-11-03 | HU-13 · Estado Disponible/No disponible | `feat/HU-13-turno` | 8 | En revisión | Empezar y terminar el turno desde la app con selector de vehículo (RN-05), consentimiento (RN-18) y GPS que sigue al turno; el panel lo refleja en ≤ 11 s. | PR-07: WebSocket con HU-02. Recorrer el selector en teléfono real (prueba E de la guía; el emulador quedó inestable). |
| 2026-11-03 | HU-17 · Abrir Google Maps o Waze | `feat/HU-17-navegacion` | 3 | En revisión | Tarjeta del viaje en curso en la app con botones que abren Google Maps o Waze hacia la recogida o, con el pasajero a bordo, hacia el destino. | Probar en el teléfono que se abren las apps (prueba F). Los viajes llegan a ACEPTADO desde la app con HU-14/15. |
| 2026-11-03 | HU-26 · Registrar número de vuelo | `feat/HU-26-vuelos` | 5 | En revisión (parcial) | Consulta inicial a la API de vuelos en el panel y el portal: rechaza vuelos inexistentes, corrige la hora programada y deja marcado si quedó sin verificar; adaptador FlightAware listo. | PR-08: vuelos de salida (decisión del PO, cambio de VUELO). PR-09: clave de FlightAware (con costo). |
