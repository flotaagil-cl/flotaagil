# Guía: probar la app del conductor en tu Android

Qué valida esta guía, y que el emulador no puede validar del todo:

- El GPS sigue registrando y enviando con la app en segundo plano y la pantalla apagada.
- La sesión se renueva sola mientras tanto.
- La contraseña temporal y el logout funcionan en el teléfono.

Tiempo: unos 40 minutos, la mayor parte esperando con la pantalla apagada.

## 1. Preparar el backend en el PC

1. Conecta el PC y el teléfono a la **misma wifi**. Anota la IP del PC (`ipconfig`, «Dirección IPv4», p. ej. `192.168.1.20`).
2. En `backend/.env`:
   - Agrega esa IP a `DJANGO_ALLOWED_HOSTS`: `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.20`.
   - Para que la renovación ocurra varias veces durante la prueba, baja la vida del access: `JWT_ACCESS_MIN=2`. Vuelve a 15 al terminar.
3. Levanta el backend: `docker compose -f infra/docker-compose.dev.yml up -d backend`.
4. Si Windows pregunta por el firewall al abrir el puerto 8000, permite la red privada.
5. Comprueba la conexión desde el navegador del teléfono: `http://192.168.1.20:8000/api/salud/` debe mostrar `{"estado": "ok"}`.

## 2. Compilar e instalar la app

```
cd app
echo VITE_API_URL=http://192.168.1.20:8000 > .env
npm ci
npm run build
npx cap sync android
cd android
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

(Con el teléfono conectado por USB y la depuración USB activa. También puedes abrir `app/android` en Android Studio y usar Run.)

## 3. Configurar el teléfono (Xiaomi / HyperOS)

Es la configuración recomendada de la PoC H-3 (`docs/poc-gps.md`):

- **Ajustes > Apps > FlotaÁgil Conductor > Ahorro de batería:** «Sin restricciones».
- **Inicio automático:** activado.
- **En recientes:** mantén presionada la app y ponle el **candado**.
- **Permisos:** ubicación «Mientras se usa la app» con **ubicación precisa** activada, y notificaciones permitidas.

## 4. Prueba A: contraseña temporal y consentimiento

1. En el panel (`http://localhost:5173`), como `admin@transportes-andes.example`, abre **Conductores > Nuevo conductor** y crea uno con datos inventados.
2. En su ficha, **Generar contraseña temporal** y copia la contraseña.
3. En el teléfono, ingresa con ese correo y la temporal. **Esperado:** la pantalla «Crea tu contraseña».
4. Crea la contraseña nueva (10 o más caracteres). **Esperado:** pasa a «Uso de tu ubicación».
5. Pulsa **Acepto**. **Esperado:** Inicio con «Estado: No disponible» y «No se registra: estás No disponible».
6. Cierra sesión y vuelve a ingresar con la contraseña nueva. **Esperado:** entra directo a Inicio, sin pedir el consentimiento otra vez.

## 5. Prueba B: GPS en segundo plano con la pantalla apagada (la importante)

1. Ingresa en el teléfono como `conductor1@transportes-andes.example` (contraseña: `DATOS_DEMO_PASSWORD` del `.env`). Si quedó en turno de una prueba anterior, pulsa «Terminar turno».
2. Ese conductor tiene dos vehículos: elige **DMAE14** y pulsa **Empezar turno (Disponible)** (HU-13). **Esperado:** Android pide permiso de ubicación (acepta «Mientras se usa la app» y «precisa»); aparece la notificación fija «FlotaÁgil: en turno» y en Inicio «Registrando tu ubicación (cada 30 s)».
3. Anota la hora. Pulsa Inicio, **apaga la pantalla** y deja el teléfono **30 minutos** sin tocarlo (sin cable, si puedes). Si puedes, camina o anda en auto un rato: así las posiciones cambian.
4. Mientras tanto, en el PC, revisa que lleguen posiciones:

   ```
   docker compose -f infra/docker-compose.dev.yml exec db psql -U flotaagil -d flotaagil -c "select count(*), max(registrada_en) from posicion_gps where conductor_id=(select c.id from conductor c join usuario u on u.id=c.usuario_id where u.email='conductor1@transportes-andes.example') and registrada_en > now() - interval '35 minutes';"
   ```

   **Esperado:** cerca de 60 posiciones en 30 min (una cada 30 s), y `max(registrada_en)` de hace menos de 1 minuto.
5. Revisa que la sesión se renovó en segundo plano:

   ```
   docker compose -f infra/docker-compose.dev.yml logs --since 35m backend | findstr "app/refresh"
   ```

   **Esperado:** con `JWT_ACCESS_MIN=2`, alrededor de 15 líneas `"POST /api/auth/app/refresh/ HTTP/1.1" 200` y ningún 401.
6. Enciende la pantalla y abre la app. **Esperado:** sigue en Inicio y muestra «Último envío» de hace segundos, sin pedir ingresar.

**Huecos:** para ver si hubo pausas de más de 60 s:

```
docker compose -f infra/docker-compose.dev.yml exec db psql -U flotaagil -d flotaagil -c "select registrada_en, registrada_en - lag(registrada_en) over (order by registrada_en) as hueco from posicion_gps where registrada_en > now() - interval '35 minutes' order by hueco desc nulls last limit 5;"
```

**Esperado:** el hueco mayor es de unos 30 s (en espera), sin pasar de 60 s.

## 5b. Prueba E: turno desde la app y el panel (HU-13)

1. Con el panel abierto en el PC en **Conductores**, en el teléfono pulsa **Terminar turno (No disponible)**. **Esperado:** desaparece la notificación del GPS; en el panel, sin recargar, el conductor pasa a «No disponible» en 10 s o menos.
2. Pulsa **Empezar turno** sin elegir vehículo. **Esperado:** el botón está desactivado hasta elegir uno (RN-05).
3. Elige DMAA10 y empieza el turno. **Esperado:** en el panel, «Disponible» y en la ficha «declaró DMAA10».
4. Desde el panel (Vehículos > DMAA10) intenta **Desactivar**. **Esperado:** 409 «está declarado por … en turno».

## 6. Prueba C: sin señal y vuelta

1. Con la app en turno, activa el **modo avión** 3 minutos y luego desactívalo.
2. **Esperado:** en Inicio aparece «Sin conexión: N posiciones esperan» y luego se vacía. En la base, las posiciones de esos 3 minutos aparecen igual, cada una una sola vez.

## 7. Prueba D: logout

1. Pulsa **Cerrar sesión** (dos veces: la segunda confirma). **Esperado:** desaparece la notificación del GPS y vuelve al login.
2. **Esperado** en los logs del backend: `"POST /api/auth/app/logout/ HTTP/1.1" 204`.

## 8. Al terminar

- Devuelve `JWT_ACCESS_MIN=15` en `backend/.env` y reinicia el backend.
- Anota los resultados en `docs/evidencias/app-base/resultados.md`, en la sección «Prueba en teléfono real»: modelo, versión de Android, posiciones recibidas, hueco máximo, renovaciones y batería consumida.
