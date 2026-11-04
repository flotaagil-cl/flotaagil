# Credenciales externas

Qué hay que conseguir para pasar de los adaptadores de desarrollo a los servicios reales. No hay ninguna cuenta creada: mientras las variables estén vacías, todo funciona con los adaptadores de desarrollo.

| Servicio | Sin credenciales | Estado del código real |
|---|---|---|
| Twilio (WhatsApp) | Registra los mensajes y las respuestas se simulan con `simular_whatsapp` | Listo, probado solo con un doble |
| FlightAware AeroAPI | Todo vuelo existe, salvo los que empiezan con `ZZ` | Listo, probado solo con respuestas simuladas |
| Google Maps (mapa) | Mapa esquemático | **Falta escribir el adaptador** |
| Google Geocoding (direcciones) | Coordenadas simuladas dentro de la zona | Listo, probado solo con respuestas simuladas |

Ninguno se ha probado todavía contra el servicio real. Los precios y límites de esta página pueden haber cambiado: confírmalos antes de contratar.

Las variables del backend van en `backend/.env` (no se sube al repositorio). Después de cambiarlas, reinicia: `docker compose -f infra/docker-compose.dev.yml up -d`.

## Twilio: sandbox de WhatsApp

**Cómo se obtiene**

1. Crea una cuenta en Twilio. El sandbox se activa solo desde la consola antigua: en la nueva no está disponible y, en las cuentas de prueba, aparece como «Try out WhatsApp».
2. En la página **Try WhatsApp**, acepta las condiciones y confirma.
3. Desde tu teléfono, envía `join <tu código>` al número del sandbox, **+1 415 523 8886**. El código aparece en la consola.
4. Copia el **Account SID** y el **Auth Token** del panel de la cuenta.
5. Expón el backend con una URL pública https, por ejemplo con un túnel hacia el puerto 8000, y agrega ese host a `DJANGO_ALLOWED_HOSTS`.
6. En **Sandbox settings > Sandbox configuration**, configura:
   - **When a message comes in:** `https://<url pública>/api/whatsapp/entrante/`
   - **Status callback URL:** `https://<url pública>/api/whatsapp/estado/`

**Variables en `backend/.env`** (la web no necesita ninguna)

```
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=+14155238886
WHATSAPP_URL_BASE=https://<url pública>
# Vacías en el sandbox:
TWILIO_PLANTILLA_VERIFICACION=
TWILIO_PLANTILLA_AVISO_CONFIRMACION=
TWILIO_PLANTILLA_AVISO_CONDUCTOR=
TWILIO_PLANTILLA_AVISO_EN_CAMINO=
TWILIO_PLANTILLA_AVISO_EN_ZONA=
TWILIO_PLANTILLA_AVISO_ENCUESTA=
```

`WHATSAPP_URL_BASE` debe ser exactamente la URL configurada en Twilio: con ella se valida la firma de cada webhook.

**Qué se activa**

- Con las cuatro primeras variables, las solicitudes del portal envían un WhatsApp real al pasajero, y también los avisos de estado del viaje.
- Con `TWILIO_AUTH_TOKEN`, los webhooks exigen la firma `X-Twilio-Signature`. Una llamada sin firma recibe 403.
- `simular_whatsapp` sigue disponible con `DEBUG` activo, pero sus respuestas al pasajero ahora se envían de verdad.

**Limitaciones del sandbox**

- No admite plantillas propias. Por eso, con `TWILIO_PLANTILLA_VERIFICACION` vacía, la verificación va como texto y el pasajero responde escribiendo «Confirmar» o «Cancelar», **sin botones**.
- Solo llega a números que enviaron el `join`. Los demás fallan con el error 63015.
- El mensaje de texto solo se entrega dentro de las 24 h siguientes al último mensaje del pasajero. El `join` abre esa ventana.
- La inscripción dura 3 días; después hay que volver a enviar el `join`.
- Envía como máximo un mensaje cada 3 segundos.
- Todos los usuarios del sandbox comparten el número.

**Para producción** hace falta un número de WhatsApp registrado y una plantilla de tipo `twilio/quick-reply` aprobada, con los botones Confirmar y Cancelar y cuatro variables: nombre, empresa, recogida y hora límite. Su identificador (`HX...`) va en `TWILIO_PLANTILLA_VERIFICACION`, y con eso se activan los botones. Queda sin probar si la plantilla entrega `ButtonPayload` con el valor esperado: el código acepta `confirmar` y `cancelar`, así que conviene definir esos identificadores en los botones.

**En producción, todo aviso iniciado por la empresa fuera de la ventana de 24 h requiere una plantilla aprobada por Meta.** Esa ventana se abre con el último mensaje del pasajero, así que la regla alcanza a la verificación, a los cuatro avisos de estado y a la encuesta. Sin plantilla van como texto y fallan si el pasajero no ha escrito hace poco, como en una reserva por teléfono. Hay que tramitar una plantilla por tipo, y su aprobación queda en manos de Meta, así que conviene contar con ese plazo antes de salir a producción. Las variables son:

| Variable de `backend/.env` | Variables de la plantilla |
|---|---|
| `TWILIO_PLANTILLA_AVISO_CONFIRMACION` | nombre, empresa, recogida |
| `TWILIO_PLANTILLA_AVISO_CONDUCTOR` | nombre, conductor, vehículo, patente |
| `TWILIO_PLANTILLA_AVISO_EN_CAMINO` | conductor, punto de recogida |
| `TWILIO_PLANTILLA_AVISO_EN_ZONA` | punto de recogida, patente |
| `TWILIO_PLANTILLA_AVISO_ENCUESTA` | nombre, conductor |

## FlightAware AeroAPI

**Cómo se obtiene**

1. Crea una cuenta en FlightAware y entra a [AeroAPI](https://www.flightaware.com/commercial/aeroapi).
2. En el nivel **Personal**, pulsa **Get Started**.
3. Copia la clave desde la pestaña **My AeroAPI**.

**Costo:** el nivel Personal cobra por consulta, sin mínimo mensual, con hasta 5 USD gratis al mes. La página oficial lista `GET /flights/{ident}` a 0,005 USD por conjunto de resultados y un límite de 10 por minuto. No confirmé el precio de `/schedules` ni si el nivel Personal lo incluye: revísalo, porque el adaptador lo usa para vuelos a más de 2 días.

**Variables en `backend/.env`** (la web no necesita ninguna)

```
FLIGHTAWARE_API_KEY=...
AEROPUERTO_IATA=SCL
```

**Qué se activa**

- Al registrar un vuelo en el panel o en el portal se consulta la API real, según la fecha:
  - **Hasta 2 días adelante:** `/flights/{ident}`, con estado y ETA.
  - **Más lejos:** `/schedules`, solo con la hora programada.
- Un vuelo sin llegada a SCL ese día se rechaza; uno que existe guarda la hora programada de la API. Si la API no responde, se guarda «sin verificar».
- Los vuelos `ZZ` dejan de ser el caso de prueba.

**Antes de producción:** prueba una llegada conocida a SCL, un vuelo inexistente y un corte de red. Revisa también el límite de 10 consultas por minuto cuando se construya el monitoreo de HU-27.

## Google Maps

**Cómo se obtiene** (sirve para las dos claves)

1. Crea un proyecto en [Google Cloud Console](https://console.cloud.google.com/) y **asócialo a una cuenta de facturación**. Sin ella, las APIs quedan limitadas a 1 petición al día.
2. Activa la API que corresponda y crea una clave para cada uso:
   - **Mapa (web):** Maps JavaScript API. Restringe la clave por **HTTP referrers** a las URL del panel (`http://localhost:5173/*` en desarrollo) y por API a Maps JavaScript API. Esta clave queda visible en el navegador, así que la restricción es obligatoria.
   - **Direcciones (backend):** Geocoding API. Usa otra clave, restringida a esa API.

No confirmé los precios ni el crédito mensual: revisa la página de precios de Google Maps Platform.

**Variables**

| Dónde | Variable | Qué activa |
|---|---|---|
| `backend/.env` | `GOOGLE_GEOCODING_API_KEY` | Direcciones reales en el panel y el portal, **ya funciona al ponerla** |
| `web/.env` | `VITE_GOOGLE_MAPS_KEY` | **Hoy no activa nada** |

`VITE_GOOGLE_MAPS_KEY` se fija al compilar, así que hay que volver a hacer el build. El mapa sigue siendo el esquemático hasta escribir el adaptador de Google Maps con las mismas propiedades de `MapaEsquematico` (PR-12). Es trabajo pendiente: hace falta una clave para poder probarlo.

## Fuentes

- [Twilio: sandbox de WhatsApp](https://www.twilio.com/docs/whatsapp/sandbox)
- [Twilio: parámetros de los webhooks](https://www.twilio.com/docs/messaging/guides/webhook-request)
- [Twilio: plantillas `twilio/quick-reply`](https://www.twilio.com/docs/content/twilio-quick-reply)
- [FlightAware: AeroAPI y precios](https://www.flightaware.com/commercial/aeroapi)
- [Google: seguridad de las claves](https://developers.google.com/maps/api-security-best-practices)
- [Google: preguntas frecuentes de facturación](https://developers.google.com/maps/faq)
