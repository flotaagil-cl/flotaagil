# Bitácora de avance

Una fila por HU o tarea de la cola. Estado: «En revisión» (rama subida, PR por abrir) o «Bloqueada» (con el motivo en pendientes).

| Fecha | HU | Rama | SP | Estado | Resumen | Pendientes |
|---|---|---|---|---|---|---|
| 2026-11-03 | HU-10 · Administrar conductores y vehículos | `feat/HU-10-flota` | 8 | En revisión | Vehículos y conductores con sus cuentas desde el panel, carga por CSV, contraseña temporal con cambio obligatorio y logout de la app (cierra PR-02 y PR-06). | Abrir el PR (Carlos). Alerta moderada de `npm audit` (minimatch, solo herramientas de desarrollo). |
| 2026-11-03 | chore/app-base · Base de la app del conductor | `chore/app-base` | — (tarea técnica) | En revisión | Login de la app con sesión segura (Keystore), cambio de contraseña temporal, consentimiento RN-18 y envío del GPS en turno que sobrevive al vencimiento del access en segundo plano (probado en emulador). | Prueba en teléfono real (guía en docs/guia-prueba-app-android.md). Intervalo nativo del GPS y batería (A1/A2 de la PoC). |
