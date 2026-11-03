# PR de chore/app-base

**Rama:** `chore/app-base` (encadenada desde `feat/HU-10-flota`; incluye la PoC de H-3 por merge de `feat/H-3-poc-gps`).

**Título:** `feat(app): base de la app del conductor con sesión segura y envío del GPS`

## Cuerpo

Tarea técnica sin issue propio. Base para HU-13, HU-14, HU-16 y HU-17.

### Qué hace

- **Backend:** POSICION_GPS (única por conductor e instante, DC-15). `GET /api/app/perfil/`, `POST /api/app/consentimiento/` (RN-18) y `POST /api/app/posiciones/`: lote de hasta 100, idempotente, solo en turno y con consentimiento; descarta precisión > 500 m y fechas fuera de la retención (RN-15).
- **App:**
  - Login por el canal app.
  - Cambio obligatorio de la contraseña temporal (DC-14).
  - Consentimiento de ubicación e Inicio con el estado del GPS.
  - Logout en el servidor (PR-02).
- **Sesión:**
  - El refresh se guarda con `@aparajita/capacitor-secure-storage` 7.1.6: AES/GCM con una clave del Android Keystore. Es la línea para Capacitor 7 de un plugin mantenido.
  - El access vive solo en memoria.
  - La renovación es compartida y conserva el refresh si falla por red.
- **GPS:**
  - Una posición cada 10 s en viaje o 30 s en espera.
  - Cola en memoria con reintentos, que no se corta cuando vence el access.
- **Android:** `CapacitorHttp` (sin CORS), http sin cifrar solo en debug, y el ajuste del WebView de la PoC.

### Pruebas

- Backend: 519 pruebas (99 %).
- App: 28 pruebas (87 %).
- Web: 438 pruebas.
- Emulador: 4 min en segundo plano con la pantalla apagada y el access de 1 min. Sin huecos, con 5 renovaciones automáticas.
- Detalle: `docs/evidencias/app-base/resultados.md`.

### Pendiente

- Prueba en teléfono real: `docs/guia-prueba-app-android.md`.
- Intervalo nativo del GPS (A2 de la PoC) y consumo de batería (A1): HU-13 / HU-02.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
