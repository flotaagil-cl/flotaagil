# PR de fix/app-peticiones

**Rama:** `fix/app-peticiones` (encadenada desde `fix/dc17-trazabilidad`).

**Título:** `fix(app): tiempo límite en las peticiones y pantalla que se corrige sola`

## Cuerpo

Refs #19

### Qué hace

- **Tiempo límite de 10 s** en todas las peticiones de la app, con AbortController y un temporizador que no depende de que el fetch nativo respete la señal.
- **Recarga con reintento:** perfil y viaje activo se vuelven a pedir tras cada acción. Gana la última lectura y, si falla, reintenta sola con espera creciente hasta 30 s.
- **Canal en vivo:** el backend emite un evento en cada acción del viaje, y la app recarga al recibirlo y al reconectarse.
- **Pruebas de pantalla:** la app ahora monta pantallas en pruebas (`@testing-library/react` y `jsdom`, solo de desarrollo).

### Pruebas

Detalle en `docs/evidencias/fix-app-peticiones/resultados.md`. Sin el tiempo límite fallan 4 de los 7 casos de la App, incluido el de HU-16.

### Limitaciones

- La causa de la petición colgada en HU-16 sigue sin conocerse; se corrigió la consecuencia.
- Sin probar con CapacitorHttp en un teléfono.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
