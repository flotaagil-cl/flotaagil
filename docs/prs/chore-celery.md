# PR de chore/celery

**Rama:** `chore/celery` (encadenada desde `fix/app-peticiones`).

**Título:** `chore(backend): pasar WhatsApp, vuelos y expiraciones a Celery`

## Cuerpo

Sin issue propio: tarea técnica pedida por el equipo. El `Refs #8` del commit de código es un error mío; no tiene relación con esa HU.

### Qué hace

- **Compose:** `worker` y `beat` reemplazan a `programador` y `asignaciones`.
- **WhatsApp:** verificación, avisos y respuestas salen del worker, con reintentos a 2, 4, 8, 16 y 32 s. Agotados, el mensaje queda en FAILED.
- **RN-06 y RN-04:** tareas periódicas de beat, cada 60 s y cada 5 s.
- **Vuelos:** la consulta inicial sigue en la petición con un intento, porque el formulario debe responder si el vuelo existe. Si la API falla, reintenta la tarea, de 30 s a 16 min.

### Medición, con Twilio tardando 3 s

| Acción | Con worker | Sin worker |
|---|---|---|
| Aceptar | 60 ms | 3.069 ms |
| En camino | 45 ms | 3.052 ms |
| Finalizar | 52 ms | 3.064 ms |

### Para revisar

- **Tras fusionar:** `docker compose build backend` y `up -d --remove-orphans`. La imagen tiene dependencias nuevas y los servicios antiguos desaparecen.
- **`redis` baja de 6.4.0 a 5.2.1:** tope de `kombu[redis]` en Celery 5.5. Dependabot propondrá subirlo: no debe aceptarse sin subir también Celery.
- **Incidente:** las primeras corridas de pytest llegaron al worker real y dejaron 2 mensajes y 4 vuelos modificados en la base de desarrollo local. Limpiado y corregido con `config/settings_pruebas.py`. Quien tenga el worker corriendo con la versión anterior no se ve afectado: el aislamiento va con esta rama.

### Pruebas

727 pruebas en verde. Detalle en `docs/evidencias/chore-celery/resultados.md`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
