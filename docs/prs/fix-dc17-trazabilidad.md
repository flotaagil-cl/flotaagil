# PR de la trazabilidad de DC-17

**Rama:** `fix/dc17-trazabilidad` (encadenada desde `feat/HU-24-calificacion`).

**Título:** `fix(backend): registrar la llegada manual y su distancia al origen`

## Cuerpo

Refs #19

### Qué hace

- Si se pulsa «Pasajero a bordo» sin que la geocerca haya marcado la llegada, EN_ZONA queda con `manual = true` y `distancia_m` en HISTORIAL_ESTADO (DC-20).
- La distancia se mide desde la última posición que el conductor envió después de salir. Si no envió ninguna queda NULL; una posición de antes de salir no cuenta.
- El panel lo muestra en el historial: «Indicado a mano, sin geocerca · a 320 m del origen».

### Pruebas

Las suites completas y una prueba manual: reserva con llegada manual vista en el panel.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
