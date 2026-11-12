# FlotaÁgil

SaaS para gestionar flotas de taxi turismo: despacho de reservas, seguimiento GPS de conductores, verificación y avisos al pasajero por WhatsApp, recogidas en aeropuerto con monitoreo de vuelos y convenios corporativos. Proyecto de Título TIHI84, INACAP La Granja.

La fuente de verdad es el Informe 2 (ES2). Si algo de este archivo choca con el informe, se avisa antes de decidir.

## Equipo

| Persona | Rol | Área |
|---|---|---|
| Renato González (`RenatoGonzalez151`) | Developer | `web/` (panel y portal), `app/` (app del conductor) |
| Carlos Ortiz (`ceal2013`) | Scrum Master, líder, Developer | `backend/`, integraciones, `infra/` |
| Juan Pérez | Product Owner (integrante simulado) | Prioriza y acepta incrementos |

HU-02 y HU-29 se trabajan en pareja. Mientras Carlos no esté, Renato integra cada PR con el check `ci` en verde y la lista de chequeo de `docs/prs/lista-de-chequeo.md` (DC-47); cuando Carlos vuelva, se evalúa volver a exigir 1 aprobación.

## Stack (versiones del informe)

- **Backend:** Python 3.12, Django 5.2 LTS + DRF 3.16, GeoDjango, Channels 4 + Daphne (WebSocket), Celery 5.5 (worker y beat), simplejwt 5, Gunicorn 23.
- **Datos:** PostgreSQL 16 + PostGIS 3.4, Redis 7.2 (canales, caché de última posición, broker).
- **Web:** Node 22 LTS, TypeScript 5, React 19 + Vite 6. Panel (administrador, despachador) y portal (pasajero, convenios).
- **App del conductor:** React + Capacitor 7 + background-geolocation. Solo Android 10+ (API 29–35).
- **Pruebas:** pytest + pytest-django + coverage, Vitest, Playwright, k6, Bandit, Ruff, ESLint, OWASP ZAP.
- **Infra:** Docker Compose, Nginx + Certbot, AWS EC2 t4g.small (ARM64, us-east-1), EBS gp3, S3, DLM, Route 53, CloudWatch, SSM Parameter Store. Imágenes en `ghcr.io/flotaagil-cl/*`.
- **Externos:** Twilio WhatsApp Business API, FlightAware AeroAPI / AeroDataBox (detrás de un adaptador), Google Maps JS API, Sentry, UptimeRobot.

Todas las imágenes Docker deben tener variante ARM64.

## Estructura del repositorio

Repositorio: `Flotaagil-CL/flotaagil` desde el 11-11-2026 (DC-49). El anterior, `flotaagil/flotaagil`, queda solo de lectura.

```
backend/   Django (API REST, WebSocket, Celery)        responsable: Carlos
web/       React + Vite: panel y portal                  responsable: Renato
app/       React + Capacitor: app del conductor          responsable: Renato
infra/     docker-compose, nginx, runbook, inventario    responsable: Carlos
docs/      informes, decisiones, evidencias de pruebas   ambos
docs/diseno/  referencias de diseño (portal, panel, app)  ambos
.github/   CI, plantillas, Dependabot
```

## Dominio

**Roles:** administrador, despachador, conductor, pasajero (con cuenta para pedir en el portal, CC-18), supervisor de convenio (cuenta de la empresa cliente). Multiempresa: todo registro pertenece a una EMPRESA y un usuario solo ve los de la suya (RN-13).

**Entidades (Anexo D, mismos nombres):** EMPRESA, USUARIO, CONDUCTOR, VEHICULO, CONDUCTOR_VEHICULO, CONVENIO, PASAJERO, VIAJE, VUELO, ASIGNACION, HISTORIAL_ESTADO, PAGO_VIAJE, CALIFICACION, GEOCERCA, FILA_AEROPUERTO, POSICION_GPS, MENSAJE_WHATSAPP, AUDITORIA.

**Estados del viaje:** PENDIENTE_CONFIRMACION → SOLICITADO → ASIGNADO → ACEPTADO → EN_CAMINO → EN_ZONA (geocerca de 150 m, automático) → PASAJERO_A_BORDO → FINALIZADO. CANCELADO desde PENDIENTE_CONFIRMACION (expira a los 15 min), SOLICITADO, ACEPTADO, EN_CAMINO y EN_ZONA (no presentación a los 15 min). Desde PASAJERO_A_BORDO solo por anulación forzada (HU-05). ASIGNADO vuelve a SOLICITADO si el conductor rechaza o no responde en 60 s.

**Reglas de negocio:**
- RN-01 Solo se asigna a conductores Disponibles.
- RN-02 Ninguna asignación ni ajuste de recogida sin confirmación del despachador.
- RN-03 Un conductor tiene a lo más un viaje en ejecución.
- RN-04 Sin respuesta en 60 s la reserva vuelve a SOLICITADO.
- RN-05 Con más de un vehículo, el conductor declara cuál usa antes de quedar Disponible.
- RN-06 Reserva del portal no se confirma hasta que el pasajero responda por WhatsApp; expira a los 15 min. Desde CC-18 (DC-41) en el portal solo se pide con cuenta: el teléfono se verifica una vez al activarla y las reservas nacen en SOLICITADO; RN-06 queda para las reservas anteriores.
- RN-07 Reservas por link de convenio vigente omiten la verificación del teléfono.
- RN-08 Desactivar un convenio invalida su link sin afectar el historial.
- RN-09 El pasajero cancela por WhatsApp solo sin conductor asignado.
- RN-10 Ningún viaje se finaliza sin método de pago y monto.
- RN-11 Cierre o anulación forzada exige motivo y queda en auditoría.
- RN-12 Cambios de contraseña o estado de convenio generan auditoría inmutable.
- RN-13 Un usuario solo accede a registros de su empresa.
- RN-14 La calificación es opcional y no condiciona el cierre.
- RN-15 Retención: viajes 24 meses, mensajes 12 meses, posiciones GPS 30 días, eventos 90 días.
- RN-16 En aeropuerto se propone al primero de la fila virtual (orden de ingreso a la geocerca).
- RN-17 Nueva hora de recogida = ETA + margen (20 min nacional, 35 internacional, configurable).
- RN-18 La ubicación del conductor se registra solo en turno y con consentimiento informado.

Los valores marcados como supuestos (márgenes, 10 min fuera de geocerca, 15 min de no presentación, polígono del aeropuerto) van como **parámetros configurables por empresa**, nunca fijos en el código.

**Portal (rediseño, HU-37 en adelante):** el pasajero pide con cuenta (CC-18) y acepta el aviso de privacidad una sola vez al crearla (DC-44). La referencia visual está en `docs/diseno/` (README y capturas a 390 y 1440 px); los colores van solo como tokens de `web/src/diseno/tokens.css`.

**No funcionales clave:** latencia GPS p95 < 5 s; API p95 < 2 s con 50 usuarios; TLS 1.2+ con HSTS; contraseñas PBKDF2-SHA256; cobertura ≥ 70 % en módulos de negocio; toda transición de estado y acción sensible auditada; integraciones con reintento exponencial y webhooks idempotentes; consumo de la app < 50 MB por turno de 8 h.

## Forma de trabajo

- **Scrum**, sprints de 2 semanas, tablero en GitHub Projects «FlotaÁgil — Backlog». Backlog completo en `docs/backlog/backlog.json` (44 HU, 274 SP).
- **Nunca push directo a `main`.** Todo entra por PR con el check `ci` en verde y fusión *squash* (historial lineal); el ruleset «Proteger main» no se modifica. Hoy no exige aprobaciones (DC-47): Renato integra con la lista de chequeo de `docs/prs/lista-de-chequeo.md`. Las ramas fusionadas no se borran (el informe cita sus hashes).
- **Ramas:** `feat/HU-03-reservas`, `fix/HU-16-monto-pago`, `chore/…`, `docs/…`, `test/…`. Una rama por HU o tarea.
- **Commits y título del PR:** Conventional Commits en español con scope del área: `feat(backend): crear modelo VIAJE`, `fix(app): …`. El PR referencia el issue: `Closes #12` si termina la HU, `Refs #12` si es parcial.
- **Flujo del tablero** («FlotaÁgil — Backlog», `orgs/flotaagil-cl/projects/1`):
  - Al crear la rama de una HU o tarea, su tarjeta pasa a **En curso**.
  - Cada commit de esa rama lleva `Refs #N` con el número del issue (no el código de la HU).
  - El PR que termina la HU usa `Closes #N` y la tarjeta pasa a **En revisión**; al fusionarlo, a **Hecho**. Los PR parciales (por ejemplo, el backend de una HU) usan `Refs #N` y no mueven la tarjeta. Las tareas técnicas sin issue no llevan ninguno de los dos.
  - Si los workflows del tablero no mueven la tarjeta, se mueve a mano y se confirma leyendo el tablero. Nadie cierra issues a mano: los cierra el `Closes #N` al fusionar en `main`.
  - Los keywords de cierre solo actúan en PR cuya base es `main`; antes de fusionar, verificar con `gh pr view <N> --json baseRefName,closingIssuesReferences`.
  - En la fusión *squash*, el mensaje lleva la lista de HU, DC y CC y los `Closes #N` o `Refs #N` del PR.
- **Versiones:** SemVer. Línea base `v0.1`–`v0.4` al cierre de cada sprint y `v1.0.0` en producción.
- **Definición de terminado** (revisar contra la DoD del Informe 1): criterios de aceptación cumplidos, pruebas automatizadas de la HU en verde, cobertura ≥ 70 % en lo tocado, PR revisado, sin secretos ni datos personales, documentación actualizada si hubo cambio (Anexo B).
- **Cambios de alcance:** issue con plantilla «Solicitud de cambio». No se agrega funcionalidad fuera del backlog sin ese issue.

## Reglas para Claude

- Antes de crear o cambiar algo grande, explica el plan y espera confirmación.
- No inventes datos del cliente. Datos de prueba siempre sintéticos.
- Nunca subas secretos: `.env` está ignorado; usa `.env.example` con valores de ejemplo.
- Nombres de modelos y tablas según el diccionario de datos (español, singular: `Viaje`, `Conductor`). Código y comentarios en español salvo términos técnicos estándar.
- Si una decisión no está en el informe, pregúntala en vez de suponer.

## Informes y evidencias

- Los informes (Informe 1, Informe 2 y la guía) se generan desde `docs/informes/` (ver su README). No se editan el PDF ni el Word a mano.
- Al cerrar cada HU o tarea, agrega una fila a `docs/estado-para-informe.md`: qué se construyó, cómo se verificó, pruebas agregadas, CC/DC y rutas de las capturas.
- Cada vez que corras las suites completas, actualiza `docs/informes/datos/pruebas.json` (fecha, rama, número de pruebas en verde y cobertura de backend, web y app).
- Capturas de evidencia en `docs/evidencias/HU-xx/`, a 390 y 1440 px, con datos sintéticos; preferir el script de Playwright del proyecto.
- Al terminar, corre `cd docs/informes/generador && python extraer_datos.py` para refrescar las cifras.
- **Alcance congelado desde el 12/11/2026:** todo cambio de alcance nuevo se registra como solicitud de cambio (CC) y queda para la versión 1.1. No se construye antes de la entrega salvo que Renato lo autorice de forma explícita.

