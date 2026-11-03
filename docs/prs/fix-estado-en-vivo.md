# PR de fix/estado-en-vivo

**Rama:** `fix/estado-en-vivo` (encadenada desde `feat/HU-14-asignacion`; `feat/HU-15-respuesta` la incluye por merge).

**Título:** `fix(web): estado del conductor en vivo por el canal del mapa`

## Cuerpo

Refs #16

### Qué hace

- **PR-07:** el listado y la ficha de Conductores reciben los cambios de estado por el canal en vivo de HU-02 (`/ws/mapa/`). Se quita el refresco cada 10 s.
- Solo recargan los datos cuando cambia quién está en turno, su estado o su vehículo. Las posiciones no provocan recargas.
- Si la conexión se corta, el listado lo avisa. Al volver llega la foto completa y se recupera el cambio perdido.
- **Compose:** `programador` usa la misma imagen que `backend`. Con imágenes separadas, reconstruir solo el backend dejaba a `programador` sin `daphne`: se caía al arrancar y la expiración de solicitudes (RN-06) no corría.

### Pruebas

- Web: pruebas nuevas en `src/flota/turno.test.tsx`.
- Contra el backend real, con 4 cambios de turno: el panel los mostró en 86, 97, 151 y 1386 ms (antes, entre 8 y 11 s).
- 5 posiciones seguidas y 13 s sin cambios: ninguna recarga del listado.

### Para revisar

- Un cambio de estado se refleja por el canal, pero deshabilitar la cuenta de un conductor que ya está fuera de turno no cambia nada en el mapa. Por eso, en otra sesión del panel esa cuenta se ve actualizada solo al recargar la pantalla.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
