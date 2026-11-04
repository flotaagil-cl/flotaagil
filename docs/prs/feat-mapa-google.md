# PR de feat/mapa-google

**Rama:** `feat/mapa-google` (encadenada desde `chore/celery`).

**Título:** `feat(web): adaptador de Google Maps para el mapa del panel`

## Cuerpo

Refs #8

### Qué hace

- `MapaGoogle`: mismas propiedades que `MapaEsquematico`. Crea, mueve y quita marcadores sin redibujar, y encuadra una sola vez, para no mover la vista de quien mira.
- Con `VITE_GOOGLE_MAPS_KEY` carga Google Maps JS solo al abrir el mapa. Sin clave no carga nada externo.
- Si la clave se rechaza o el script no carga, vuelve al esquemático con un aviso.
- La clave no se versiona: `web/.env` está ignorado y `web/.env.example` la deja vacía.

### Limitaciones

- **Sin probar con una clave real.** Las pruebas usan un doble de la API, también en el navegador. El aspecto del mapa real está por verse.
- Usa `google.maps.Marker`, marcado como obsoleto por Google pero disponible. La alternativa exige un Map ID.
- Con clave, esta queda en el JavaScript servido: la restricción por dominio es obligatoria.

### Pruebas

Detalle en `docs/evidencias/feat-mapa-google/resultados.md`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
