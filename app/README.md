# app/

App del conductor de FlotaÁgil.

**Responsable:** Renato González.

- React 19 + Vite 6 + TypeScript + Capacitor 7 + `@capacitor-community/background-geolocation` 1.2.26.
- Solo Android 10+ (minSdk 29, targetSdk 35). appId `cl.flotaagil.conductor`.
- La ubicación se registra solo en turno y con consentimiento informado (RN-18). Meta: consumo < 50 MB por turno de 8 h.

## Qué hace (chore/app-base)

1. **Login** por el canal app (`/api/auth/app/token/`).
2. **Contraseña temporal (DC-14):** si el administrador generó una, la app pide crear una propia antes de seguir. Cualquier `403 cambio_password_requerido` del backend lleva a esa pantalla.
3. **Consentimiento de ubicación (RN-18):** una vez, registrado en el backend (`POST /api/app/consentimiento/`).
4. **Inicio:** estado del conductor, vehículo declarado y estado del GPS. Cambiar a Disponible o No disponible es HU-13.
5. **GPS en turno:** con estado Disponible (una posición cada 30 s) o En viaje (cada 10 s) y con consentimiento, el servicio en primer plano del plugin entrega posiciones y la app las envía a `POST /api/app/posiciones/`.

## Sesión

| Qué | Dónde | Por qué |
|---|---|---|
| Refresh | `@aparajita/capacitor-secure-storage` 7.1.6 | Cifra cada valor con AES/GCM usando una clave del **Android Keystore** que no sale del teléfono. Es la línea 7.x del plugin (la 8.x es para Capacitor 8) y se mantiene activamente: 7.1.6 es de octubre de 2025. |
| Access | Solo memoria | Vence a los 15 min; se pide con el refresh al abrir la app. |

- **Renovación compartida:** si varias peticiones reciben 401 a la vez (el envío del GPS y una pantalla), se hace un solo refresh. El backend rota el refresh, así que dos en paralelo cerrarían la sesión.
- **Sin red:** si el refresh falla por red (por ejemplo, con la app en segundo plano), se conserva y se reintenta. Solo un 401 del backend cierra la sesión.
- **Logout en el servidor** (`/api/auth/app/logout/`, PR-02): el refresh va a la lista negra. Sin red, se borra igual del teléfono.

## Envío del GPS

- Cola en memoria (no se guardan posiciones en el teléfono), hasta 2000 pendientes; se descartan las más antiguas.
- Un access vencido no corta el envío: se renueva y se repite la petición. Sin red o con 5xx, las posiciones esperan, con reintentos de espera creciente hasta 60 s.
- El reenvío de un lote que ya llegó no duplica: el backend identifica cada posición por conductor e instante (DC-15).
- `409 fuera_de_turno` o `409 sin_consentimiento`: vacía la cola y vuelve a leer el perfil, con lo que el GPS se detiene.
- Del PoC (H-3) se mantiene el ajuste de `MainActivity` que evita que el WebView se suspenda con la pantalla apagada.

## HTTP nativo y URL del backend

La app usa `CapacitorHttp` (fetch nativo), así que la API no necesita CORS para la app. La URL se fija al compilar con `VITE_API_URL` (ver `.env.example`):

- **Emulador:** `http://10.0.2.2:8000`.
- **Teléfono en la misma wifi que el PC:** `http://<IP del PC>:8000`.
- **Producción:** `https://…`.

Agrega el host a `DJANGO_ALLOWED_HOSTS` del backend. `http` sin cifrar solo se permite en los builds de depuración (`android/app/src/debug/AndroidManifest.xml`).

## Requisitos

- Node 22 LTS.
- JDK 21 (`JAVA_HOME` apuntando a él).
- Android Studio con SDK Platform 35, Build-Tools y Platform-Tools; `ANDROID_HOME` configurado.
- Teléfono Android 10+ con depuración USB, o el emulador.

## Comandos

```
npm ci
npm run lint
npm run typecheck
npm test                 # sesión, renovación, cola de envío y muestreo
npm run build
npx cap sync android
cd android && ./gradlew assembleDebug    # APK en android/app/build/outputs/apk/debug/
```

La prueba en un teléfono real (segundo plano y pantalla apagada) está en [`docs/guia-prueba-app-android.md`](../docs/guia-prueba-app-android.md).
