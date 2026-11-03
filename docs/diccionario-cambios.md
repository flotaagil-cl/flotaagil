# Cambios respecto del diccionario de datos (Anexo D)

Agregados y desvíos de la implementación respecto de [`diccionario-datos.md`](diccionario-datos.md), para actualizar el Anexo D del informe en la ES2. Cada entrada indica la decisión, su motivo y el estado de implementación. Cuando las ramas se fusionen, la columna «Estado» debe indicar el número del PR en vez del nombre de la rama.

| # | Fecha | Tipo | Tabla | Cambio | Motivo | Estado |
|---|---|---|---|---|---|---|
| DC-01 | 2026-10-29 | Agregado | EMPRESA | Columna `slug` | El portal público necesita identificar la empresa en la URL (`/solicitar/<slug>`) | Implementado (feat/backend-base) |
| DC-02 | 2026-10-29 | Agregado | CONFIGURACION_EMPRESA (nueva) | Tabla 1:1 con EMPRESA con los parámetros configurables | CLAUDE.md exige que los valores supuestos sean parámetros por empresa, no constantes en el código | Implementado (feat/backend-base) |
| DC-03 | 2026-10-29 | Desvío de dominio | HISTORIAL_ESTADO | `actor` agrega `ADMINISTRADOR` | El administrador también puede cambiar estados (p. ej., cancelar); registrarlo como DESPACHADOR falsearía el historial | Implementado (feat/HU-03-reservas) |
| DC-04 | 2026-10-29 | Agregado técnico | USUARIO | Columnas y tablas del sistema de autenticación de Django | Propias del framework; se usan solo para el admin de mantenimiento interno | Implementado (feat/backend-base) |
| DC-05 | 2026-10-29 | Decisión de diseño | VIAJE | Coordenadas obtenidas con un geocodificador detrás de un adaptador | `origen_geo` y `destino_geo` son NOT NULL y los formularios capturan direcciones en texto | Implementado (feat/HU-03-reservas) |
| DC-06 | 2026-10-29 | Precisión de uso | VUELO | Solo se crea para viajes `DESDE_AEROPUERTO`; `hora_programada` la informa el pasajero o el despachador | `hora_programada` es la hora de llegada que usan RN-17 y HU-27; HU-26 la valida o corrige | Implementado en el panel (feat/HU-03-reservas) y en el portal (feat/HU-19-portal) |
| DC-07 | 2026-10-29 | Supuesto | USUARIO | Duración del bloqueo tras 5 intentos fallidos: 15 min, configurable (`LOGIN_BLOQUEO_MIN`) | El Anexo D define el bloqueo al llegar a 5 intentos, pero no su duración | Implementado (feat/backend-base) |
| DC-08 | 2026-10-29 | Desvío de dominio | VIAJE | `origen_cancelacion` agrega `ADMINISTRADOR` | Igual que en DC-03: el administrador también cancela desde el panel; registrarlo como DESPACHADOR falsearía el origen | Implementado (feat/HU-03-reservas) |
| DC-09 | 2026-10-29 | Corrección de tipo | VIAJE, HISTORIAL_ESTADO | `estado`, `estado_anterior` y `estado_nuevo` pasan de VARCHAR(20) a VARCHAR(22) | `PENDIENTE_CONFIRMACION` tiene 22 caracteres y no cabe en VARCHAR(20) | Implementado (feat/HU-03-reservas) |
| DC-10 | 2026-10-29 | Agregado | CONFIGURACION_EMPRESA | `anticipacion_minima_min` SMALLINT NOT NULL, defecto 30 | Anticipación mínima de una solicitud del portal, configurable por empresa | Implementado (feat/HU-19-portal) |
| DC-11 | 2026-10-29 | Agregado | PASAJERO | `privacidad_aceptada_en` TIMESTAMPTZ NULL | Evidencia de la aceptación del aviso de privacidad (HU-19) | Implementado (feat/HU-19-portal) |
| DC-12 | 2026-10-29 | Supuesto | VUELO | Sin distinción nacional/internacional: la recogida calculada (RN-17) usa `margen_nacional_min` | El Anexo D no tiene columna que distinga el tipo de vuelo | Implementado (feat/HU-19-portal); revisar en HU-27 |
| DC-13 | 2026-11-03 | Agregado | AUDITORIA | `entidad` agrega `VEHICULO` y `CONDUCTOR` | HU-10 audita el alta, la edición y la desactivación de vehículos y los cambios de datos y vehículos de los conductores | Implementado (feat/HU-10-flota) |
| DC-14 | 2026-11-03 | Agregado | USUARIO | `debe_cambiar_password` BOOLEAN NOT NULL (defecto false) y `password_temporal_vence` TIMESTAMPTZ NULL | Contraseña temporal que genera el administrador para el conductor (HU-10): obliga a cambiarla y vence si no se usa | Implementado (feat/HU-10-flota) |
| DC-15 | 2026-11-03 | Agregado | POSICION_GPS | Restricción única (`conductor_id`, `registrada_en`) e índice (`conductor_id`, `registrada_en` desc) | La app reenvía un lote si no supo si llegó (red móvil, segundo plano): la restricción evita duplicados; el índice sirve a la última posición del conductor (HU-02) | Implementado (chore/app-base) |
| DC-16 | 2026-11-03 | Supuesto | CONFIGURACION_EMPRESA | `precision_geocerca_m` SMALLINT NOT NULL, defecto 50 | Precisión máxima de una posición para marcar EN_ZONA. El PoC H-3 (A7) observó posiciones de ±88 a ±1400 m al iniciar bajo techo, que marcarían una llegada falsa; configurable por empresa | Implementado (feat/HU-16-estados-pago) |
| DC-17 | 2026-11-03 | Supuesto | HISTORIAL_ESTADO | Sin cambio de columnas: EN_ZONA puede tener actor CONDUCTOR además de SISTEMA | Si la geocerca no marca la llegada (GPS impreciso), el conductor no queda bloqueado: «Pasajero a bordo» registra EN_ZONA con actor CONDUCTOR y luego PASAJERO_A_BORDO. El informe dice que EN_ZONA es automático: pendiente de aceptación del PO | Implementado (feat/HU-16-estados-pago) |
| DC-18 | 2026-11-03 | Supuesto | MENSAJE_WHATSAPP | Sin cambio de columnas: reglas de los avisos de HU-21 | «Conductor asignado» se avisa al aceptar, porque antes puede rechazar. «Tu vehículo te espera» solo con EN_ZONA automático. «Cancelar» sin citar un mensaje, con varias reservas en curso, no cancela ninguna. «No» suelto solo cancela durante la verificación | Implementado (feat/HU-21-avisos) |
| DC-19 | 2026-11-03 | Supuesto | CONFIGURACION_EMPRESA | `encuesta_vigencia_horas` SMALLINT NOT NULL, defecto 24 | Horas desde el fin del viaje en que un número suelto cuenta como respuesta a la encuesta; después es conversación. Configurable por empresa. Aprobado el 2026-11-03 | Implementado (feat/HU-24-calificacion) |

## DC-01 · EMPRESA.slug

| Columna | Tipo | Nulo | Clave | Descripción | Dominio / restricción | Defecto | Clasificación |
|---|---|---|---|---|---|---|---|
| slug | VARCHAR(50) | No | UK | Identificador de la empresa en la URL del portal | kebab-case: `^[a-z0-9]+(-[a-z0-9]+)*$`; único | — |  |

## DC-02 · CONFIGURACION_EMPRESA

| Columna | Tipo | Nulo | Clave | Descripción | Dominio / restricción | Defecto | Clasificación |
|---|---|---|---|---|---|---|---|
| empresa_id | BIGINT | No | PK, FK | Empresa | → EMPRESA.id (1:1) | — |  |
| margen_nacional_min | SMALLINT | No |  | Margen sobre la ETA para vuelos nacionales (RN-17) | ≥ 0 | 20 |  |
| margen_internacional_min | SMALLINT | No |  | Margen sobre la ETA para vuelos internacionales (RN-17) | ≥ 0 | 35 |  |
| tolerancia_fila_min | SMALLINT | No |  | Tiempo fuera de la geocerca antes de salir de la fila (HU-29) | ≥ 0 | 10 |  |
| espera_no_presentacion_min | SMALLINT | No |  | Espera en EN_ZONA antes de cancelar por no presentación | ≥ 0 | 15 |  |
| expiracion_verificacion_min | SMALLINT | No |  | Expiración de PENDIENTE_CONFIRMACION (RN-06) | ≥ 1 | 15 |  |
| zona_lat_min | NUMERIC(9,6) | No |  | Latitud mínima de la zona de operación | −90 a 90; < `zona_lat_max` | −34.300000 |  |
| zona_lat_max | NUMERIC(9,6) | No |  | Latitud máxima de la zona de operación | −90 a 90 | −32.920000 |  |
| zona_lon_min | NUMERIC(9,6) | No |  | Longitud mínima de la zona de operación | −180 a 180; < `zona_lon_max` | −71.720000 |  |
| zona_lon_max | NUMERIC(9,6) | No |  | Longitud máxima de la zona de operación | −180 a 180 | −69.770000 |  |

Relación: EMPRESA 1:1 CONFIGURACION_EMPRESA. Se crea junto con la empresa con los valores por defecto.

La zona de operación es un rectángulo (lat/lon mínimos y máximos) que valida «Dentro de la RM» en `VIAJE.origen_geo` y acota las coordenadas del geocodificador de desarrollo. Los valores por defecto son un rectángulo **aproximado** que contiene la Región Metropolitana; cada empresa puede ajustarlo.

**Limitación.** Es un rectángulo envolvente, no el límite real de la región: también incluye zonas de regiones vecinas, por ejemplo Valparaíso y San Antonio (Región de Valparaíso) y Rancagua (Región de O'Higgins). Un origen en esas zonas pasa la validación. El polígono real de la RM (p. ej. como GEOCERCA) queda para más adelante.

## DC-03 · HISTORIAL_ESTADO.actor

Dominio: `CONDUCTOR | DESPACHADOR | ADMINISTRADOR | PASAJERO | SISTEMA` (se agrega `ADMINISTRADOR`). `usuario_id` sigue identificando al usuario responsable cuando el actor tiene cuenta.

## DC-04 · Columnas técnicas de Django en USUARIO

USUARIO se implementa sobre el modelo de autenticación de Django. Además de las columnas del Anexo D, el framework agrega:

| Elemento | Tipo | Uso |
|---|---|---|
| `last_login` | TIMESTAMPTZ, nulo | Último inicio de sesión |
| `is_superuser` | BOOLEAN | Acceso total al admin de mantenimiento |
| `is_staff` | BOOLEAN | Acceso al admin de mantenimiento |
| `usuario_groups`, `usuario_user_permissions` | Tablas intermedias | Grupos y permisos del framework |

Correspondencias: `password_hash` es la columna `password` de Django (PBKDF2-SHA256 con salt, mismo formato); `activo` reemplaza a `is_active`. El admin de Django se usa solo para mantenimiento interno; los usuarios del sistema operan desde el panel web.

## DC-05 · Geocodificador

No agrega columnas. `origen_geo` y `destino_geo` siguen NOT NULL. Las direcciones en texto se convierten en coordenadas mediante un adaptador con dos implementaciones:

- **Desarrollo:** coordenadas aproximadas y determinísticas por texto (la misma dirección da siempre el mismo punto) dentro del límite de la Región Metropolitana.
- **Google Geocoding:** se activa cuando existe la API key en la configuración del entorno.

La restricción «Dentro de la RM» de `VIAJE.origen_geo` se valida contra la zona de operación de la empresa (`CONFIGURACION_EMPRESA.zona_*`, ver DC-02), por defecto un rectángulo aproximado de la RM.

## DC-06 · VUELO

- Se crea solo para viajes con `sentido = DESDE_AEROPUERTO` (vuelos de llegada). Para `HACIA_AEROPUERTO` no se crea VUELO.
- `hora_programada` la informa quien ingresa la reserva (portal o despachador); `fecha` es la fecha local de esa hora. HU-26 la valida contra la API de vuelos y la corrige.

## DC-08 · VIAJE.origen_cancelacion

Dominio: `PASAJERO | DESPACHADOR | ADMINISTRADOR | SUPERVISOR | SISTEMA` (se agrega `ADMINISTRADOR`). En una cancelación desde el panel, el origen corresponde al rol de quien cancela; el usuario exacto queda además en HISTORIAL_ESTADO y AUDITORIA.

## DC-09 · Largo de los estados del viaje

`VIAJE.estado`, `HISTORIAL_ESTADO.estado_anterior` y `HISTORIAL_ESTADO.estado_nuevo` son VARCHAR(22): el valor `PENDIENTE_CONFIRMACION` tiene 22 caracteres. Hay que corregir el Anexo D (dice VARCHAR(20)).

## DC-13 · AUDITORIA en la administración de flota

Dominio de `entidad`: `CONVENIO | VIAJE | PAGO_VIAJE | USUARIO | VEHICULO | CONDUCTOR`. Acciones registradas (las de USUARIO cumplen RN-12):

| Entidad | Acción | `datos_previos` |
|---|---|---|
| VEHICULO | `CREAR` (alta individual o por CSV) | — |
| CONDUCTOR | `CREAR` (alta individual o por CSV) | — |
| VEHICULO | `EDITAR`, `ACTIVAR`, `DESACTIVAR` | Valores anteriores de los campos cambiados |
| CONDUCTOR | `EDITAR` | Valores anteriores de nombre, RUT, teléfono o licencia |
| CONDUCTOR | `ASOCIAR_VEHICULO`, `DESASOCIAR_VEHICULO` | `vehiculo_id` y `patente` del vehículo |
| USUARIO | `GENERAR_PASSWORD`, `RESTABLECER_PASSWORD`, `CAMBIAR_PASSWORD` | — (la contraseña nunca se guarda en la auditoría) |
| USUARIO | `DESHABILITAR`, `HABILITAR` | `activo` y, al deshabilitar, el `estado` previo del conductor |

Reglas de uso (no cambian columnas): la patente no se edita (otra patente es otro vehículo); un vehículo no se borra, se desactiva; no se desactiva ni se quita a un conductor el vehículo que tiene declarado en turno (DISPONIBLE o EN_VIAJE, RN-05) ni uno con un viaje entre ASIGNADO y PASAJERO_A_BORDO; si el conductor está NO_DISPONIBLE, su `vehiculo_activo` se vacía. La licencia que se edita debe quedar vigente (fecha futura), igual que en el alta.

## DC-14 · Contraseña temporal en USUARIO

| Columna | Tipo | Nulo | Clave | Descripción | Dominio / restricción | Defecto | Clasificación |
|---|---|---|---|---|---|---|---|
| debe_cambiar_password | BOOLEAN | No |  | El usuario tiene una contraseña temporal que debe cambiar | true/false | false |  |
| password_temporal_vence | TIMESTAMPTZ | Sí |  | Vencimiento de la temporal si no se usa | UTC; `PASSWORD_TEMPORAL_HORAS` (72) desde que se genera | NULL |  |

Reglas: la cuenta nueva de un conductor queda sin contraseña utilizable; el administrador genera la temporal (14 caracteres sin 0/O/o ni 1/l/I/i, solo se guarda el hash PBKDF2, se muestra una vez). Mientras `debe_cambiar_password` esté activo la API responde 403 `cambio_password_requerido` en todo salvo cambiar la contraseña, `yo` y el logout (el login y el refresh no se bloquean). Una temporal vencida responde 401 `password_temporal_vencida` en el login. Generar, restablecer y deshabilitar cierran todas las sesiones del usuario (sus refresh van a la lista negra).

## Pendientes por revisar

| # | Tema | Detalle |
|---|---|---|
| PR-01 | RN-15 y AUDITORIA | RN-15 fija la retención de «eventos 90 días». Si AUDITORIA cuenta como evento, su purga choca con RN-12 (auditoría inmutable) y con el trigger `auditoria_sin_cambios`, que impide borrar filas. Definir si AUDITORIA queda fuera de RN-15 (retención indefinida o propia) o si la purga se hace con un procedimiento controlado que desactive el trigger y deje constancia. Mientras no se decida, AUDITORIA no se purga. |
| PR-02 | Logout de la app del conductor | **Cerrado** en feat/HU-10-flota: `POST /api/auth/app/logout/` deja el refresh en la lista negra (204 siempre). |
| PR-03 | Teléfono del pasajero al editar (HU-03) | El PATCH de `/api/viajes/{id}/` no acepta `pasajero`, así que el panel no puede corregir el teléfono: se muestra en solo lectura. Un teléfono mal ingresado manda los avisos de WhatsApp a otra persona. Evaluar el cambio en el backend (p. ej. permitir corregir el pasajero mientras la reserva sea editable, con auditoría). |
| PR-04 | Texto del aviso de privacidad (HU-19) | No hay un texto aprobado. El portal muestra un borrador (`web/src/portal/Privacidad.tsx`) con la franja «Texto provisional, pendiente de aprobación», junto a la aceptación y en `/solicitar/{slug}/privacidad`. Falta: texto final validado (responsable, datos, finalidad, encargados, plazos de RN-15, derechos y normativa citada) y quitar la franja. |
| PR-05 | Portal en inglés (HU-19) | El portal está solo en español, pero muchos pasajeros que piden desde el aeropuerto son turistas. Requiere su propia HU (textos, mensajes del backend y de WhatsApp, selector de idioma). |
| PR-06 | Alta y baja de conductores con credenciales (HU-10) | **Cerrado** en feat/HU-10-flota con las decisiones del 2026-11-03: contraseña temporal generada (DC-14), deshabilitar y restablecer revocan las sesiones y responden 409 en viaje, CSV de conductores sin contraseñas. |
| PR-07 | Sincronización del estado del conductor con el panel (HU-13) | **Cerrado** en fix/estado-en-vivo: el listado y la ficha de Conductores reciben los cambios por el canal en vivo de HU-02 (`/ws/mapa/`), sin refresco por tiempo (medido: 86 a 1386 ms). |
| PR-08 | Vuelos de salida (HU-26) | **Pospuesto, fuera del MVP** (decisión del 2026-11-03). VUELO sigue solo para llegadas (DC-06): `hora_programada` es la llegada que usan RN-17 y HU-27. Registrar salidas cambiaría el significado de la columna, así que el panel y el portal aceptan vuelo solo desde el aeropuerto. |
| PR-09 | Credenciales de FlightAware AeroAPI (HU-26) | Pasos en `docs/credenciales-externas.md`. El adaptador `ConsultorFlightAware` está listo y probado con respuestas simuladas: `/flights/{ident}` hasta 2 días adelante y `/schedules` para fechas más lejanas. Sin clave se usa el consultor de desarrollo. Probar con la clave real antes de producción. |
| PR-10 | Avisos de ubicación del vehículo al pasajero (HU-20) | Quedan fuera de HU-20 por decisión del 2026-11-03 («tu vehículo está en tal punto»). Se evalúan con HU-21 (avisos de estado) o como solicitud de cambio. |
| PR-11 | Credenciales de Twilio WhatsApp (HU-20) | Pasos en `docs/credenciales-externas.md`. El adaptador `NotificadorTwilio` y los webhooks firmados están listos y probados con un doble. Con el sandbox la verificación va como texto (no admite plantillas propias); los botones requieren un número registrado y una plantilla aprobada. Los avisos de HU-21 necesitan plantillas aprobadas para llegar fuera de la ventana de 24 h. El envío es síncrono con 3 reintentos (hasta unos 16 s con Twilio caído); pasarlo a Celery cuando exista el worker. |
| PR-12 | Google Maps JS API en el mapa (HU-02) | El informe pide Google Maps JS API; requiere clave con costo (`VITE_GOOGLE_MAPS_KEY`, pasos en `docs/credenciales-externas.md`). Mientras no exista, el mapa usa el adaptador de desarrollo `MapaEsquematico`. Falta escribir el adaptador de Google Maps con las mismas propiedades: la clave por sí sola no activa nada. |
| PR-13 | Aviso de viaje con la app cerrada (HU-14) | Con la app abierta o en segundo plano, el aviso llega por el WebSocket y una notificación local. Si el conductor cerró la app, no llega nada (decisión de H-3: no se exige registrar con la app cerrada). Push por Firebase Cloud Messaging lo resolvería, pero requiere crear el proyecto de Firebase (cuenta) y el `google-services.json`. Mientras tanto, el despachador ve que el conductor no responde y la asignación vence a los 60 s (HU-15). |
