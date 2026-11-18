# Credenciales externas

Qué hay que conseguir para pasar de los adaptadores de desarrollo a los servicios reales. No hay ninguna cuenta creada: mientras las variables estén vacías, todo funciona con los adaptadores de desarrollo.

| Servicio | Sin credenciales | Estado del código real |
|---|---|---|
| Web Push (VAPID) | Sin claves no se ofrecen los avisos en el navegador: van por correo a quien marcó la casilla | Listo, probado con un servicio de push simulado |
| FlightAware AeroAPI | Todo vuelo existe, salvo los que empiezan con `ZZ` | Listo, probado solo con respuestas simuladas |
| Google Maps (mapa) | Mapa esquemático | Listo, probado solo con un doble de la API |
| Google Geocoding (direcciones) | Coordenadas simuladas dentro de la zona | Listo, probado solo con respuestas simuladas |

Ninguno se ha probado todavía contra el servicio real. Los precios y límites de esta página pueden haber cambiado: confírmalos antes de contratar.

Las variables del backend van en `backend/.env` (no se sube al repositorio). Después de cambiarlas, reinicia: `docker compose -f infra/docker-compose.dev.yml up -d`.

## Web Push (VAPID)

WhatsApp (Twilio) se retiró con CC-19 (DC-63). Los avisos del viaje al pasajero con cuenta van por Web Push o, si no lo activó, por correo con su casilla.

**Cómo se obtiene:** no requiere cuenta. Se genera un par de claves P-256 (por ejemplo, con `cryptography` en el contenedor del backend) y se guardan en SSM Parameter Store.

**Variables en `backend/.env`**

```
WEBPUSH_VAPID_PUBLICA=<punto sin comprimir, base64url>
WEBPUSH_VAPID_PRIVADA=<escalar de 32 bytes, base64url>
WEBPUSH_CONTACTO=mailto:soporte@<dominio>
```

**Qué se activa:** en «Tu viaje», el botón «Activar avisos en este dispositivo». Solo se aceptan suscripciones de servicios de push conocidos (`WEBPUSH_SERVICIOS`) por https. Falta probarlo con un navegador real antes de producción.

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
| `web/.env` | `VITE_GOOGLE_MAPS_KEY` | Mapa de Google en la pantalla Mapa del panel |

`VITE_GOOGLE_MAPS_KEY` se fija al compilar: en desarrollo, reinicia Vite; en producción, vuelve a hacer el build. **Queda dentro del JavaScript que recibe el navegador**, y por eso la restricción por dominio es obligatoria. `web/.env` está ignorado: no la subas al repositorio.

Sin clave se muestra el mapa esquemático, sin cargar nada externo. Si Google rechaza la clave o el script no carga, el panel vuelve al esquemático y lo avisa.

**Falta probarlo con una clave real.** El adaptador usa `google.maps.Marker`, que Google marca como obsoleto en favor de `AdvancedMarkerElement`, aunque sigue disponible: la alternativa exige crear un Map ID en la consola. Si Google lo retira, hay que migrar ese adaptador.

## Fuentes

- [Twilio: sandbox de WhatsApp](https://www.twilio.com/docs/whatsapp/sandbox)
- [Twilio: parámetros de los webhooks](https://www.twilio.com/docs/messaging/guides/webhook-request)
- [Twilio: plantillas `twilio/quick-reply`](https://www.twilio.com/docs/content/twilio-quick-reply)
- [FlightAware: AeroAPI y precios](https://www.flightaware.com/commercial/aeroapi)
- [Google: seguridad de las claves](https://developers.google.com/maps/api-security-best-practices)
- [Google: preguntas frecuentes de facturación](https://developers.google.com/maps/faq)
