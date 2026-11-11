# Plan de fusión: Sprints 1 a 4, cambios CC-12, CC-15 y CC-16, y ramas sueltas

Para Carlos. Son 5 PR encadenados hacia `main`, **en este orden**, y después 4 PR cortos de ramas que quedaron fuera de la cadena (ver «Ramas fuera de la cadena»).

| PR | Sprint | Rama de origen | Rama base | Issues que cierra |
|---|---|---|---|---|
| 1 | Sprint 1 | `feat/HU-20-whatsapp` | `main` | #9, #13, #16, #20, #22, #23, #27 |
| 2 | Sprint 2 | `feat/HU-24-calificacion` | `main` | #8, #17, #18, #19, #24, #25 |
| 3 | Sprint 3 | `fix/HU-27-origen-icao` | `main` | #10, #14, #28, #29, #30 |
| 4 | Sprint 4 | `docs/plan-fusion-sprint4` | `main` | #7, #11, #12, #15, #21, #26, #31 |
| 5 | Cambios CC-12, CC-15 a CC-18 y rediseño del portal (fases 1 a 3) | `feat/HU-44-mis-viajes` (punta de la cadena nueva) | `main` | #33 a #51 |

## Antes de empezar

- **Carlos solo usa la web.** Abre, revisa y fusiona ahí. El paso 5 requiere una terminal y **lo hace Claude desde el PC de Renato**, cuando Renato le avisa que se fusionó el PR.
- **No uses el botón «Update branch» en los PR 2, 3 y 4, ni abras uno antes de que Renato confirme el paso 5.** Generaría conflictos: las ramas están encadenadas y la fusión es *squash*.
- **Revisión:** desde DC-47 el ruleset no exige aprobaciones (sigue exigiendo el PR, *squash*, conversaciones resueltas y el check `ci`). La revisión del otro integrante se mantiene como acuerdo de trabajo: si tú abres el PR, lo revisa Renato.
- **Estos PR son grandes** (el 1 toca muchos archivos). Conviene revisar cada uno con su `docs/prs/HU-XX.md` y sus evidencias en `docs/evidencias/`.

## Por qué hay un paso fuera de la web

El ruleset solo permite *squash* y exige que la rama esté al día con `main`. Al fusionar el PR 1 con *squash*, la rama del PR 2 no tiene ese commit en su historial, y GitHub volvería a mostrar todo el Sprint 1 con conflictos.

`git merge -s ours` lo resuelve: registra `main` como antecesor sin cambiar el contenido de la rama. Es un push normal, sin reescribir historial y sin tocar el ruleset. El procedimiento completo se simuló en un clon local: en los tres pasos `main` queda idéntico a la rama de origen.

## Pasos

Repite 1 a 5 para cada PR, en orden.

| Paso | Quién | Qué |
|---|---|---|
| 1 | Carlos, en la web | **Abrir el PR** en https://github.com/flotaagil/flotaagil/compare. En «base» elige `main`; en «compare», la rama de origen. Copia el título y el cuerpo de abajo. |
| 2 | Carlos, en la web | **Esperar el CI:** `ci` debe quedar en verde. |
| 3 | Renato | **Revisar y aprobar.** |
| 4 | Carlos, en la web | **Fusionar** con «Squash and merge», y avisarle a Renato. |
| 5 | Claude, desde el PC de Renato | **Preparar la rama del PR siguiente,** cuando Renato avisa que se fusionó. Confirma cuando el siguiente PR se puede abrir. |

Tras el PR 5 el paso 5 ya no hace falta en la cadena. Las ramas fuera de la cadena usan su propio paso, descrito abajo.

### Lo que hace el paso 5

```sh
git fetch origin
git switch <rama del PR siguiente>
git pull
git merge -s ours --no-edit origin/main
git push
```

Después, Claude comprueba que la rama tenga el mismo contenido que antes y que `main` sea su antecesor.

### Si hay cambios durante la revisión

Un commit nuevo en la rama de un PR no llega solo a las siguientes, porque `merge -s ours` descarta el contenido que trae `main`. Avísale a Renato al pedir el paso 5: Claude lleva primero esos commits a la rama siguiente, con `git merge <rama del PR recién fusionado>`, y resuelve los conflictos si los hay.

## Riesgos conocidos

- **El CI nunca ha corrido en estas ramas:** solo se activa con un PR. Las suites se corrieron en local al cerrar cada HU. El PR 1 será la primera ejecución real.
- **Dos fallos posibles en los PR 1 y 2**, corregidos recién en el Sprint 3:
  - Una prueba de flota falla entre las 21:00 y las 24:00 de Chile, porque la fecha salía de la base en UTC. Si pasa, vuelve a correr el CI después de esa hora.
  - Dos pruebas largas de formularios de la web pueden superar los 5 s en una máquina lenta. Vuelve a correr el CI.
- **Tras fusionar el PR 2 o el 3:** quien tenga el entorno levantado debe correr `docker compose -f infra/docker-compose.dev.yml build backend`, `up -d --remove-orphans` y las migraciones. El PR 3 trae Celery y quita los servicios `programador` y `asignaciones`.
- **Tras fusionar el PR 4:** migraciones y reinicio de `worker` y `beat`. Trae cuatro migraciones y la tarea `enviar_chat`.
- **Los PR abiertos** de Dependabot (#1 a #4) y #32 no son parte de este plan. Dependabot propondrá subir `redis` a más de 5.2.1: no se debe aceptar sin subir también Celery.

Según CLAUDE.md, después de cada PR corresponde la línea base del sprint (`v0.1`, `v0.2`, `v0.3`, `v0.4`). El PR 5 no tiene línea base asignada: los cambios CC-12, CC-15 y CC-16 no tienen sprint definido.

## Ramas fuera de la cadena

Cuatro ramas salieron de `main` en el Sprint 0 y no están en ninguna de las cinco ramas de origen: si no se abre su PR, no llegan a `main`. Se simuló su fusión (`git merge-tree`) contra la punta de la cadena nueva: **ninguna tiene conflictos**.

| Orden | Rama | Qué trae | PR | Cierra |
|---|---|---|---|---|
| 6 | `chore/sprint0-script` | `docs/sprint0_github.py` (script del Sprint 0) y una línea en los README | #32, ya abierto | — |
| 7 | `docs/agregar-carlos` | CODEOWNERS con `@ceal2013` en `backend/` e `infra/`; la línea de Carlos en `CLAUDE.md` | Por abrir | — |
| 8 | `docs/flujo-tablero` | La regla del flujo del tablero en `CLAUDE.md` (Closes en el PR que termina la HU, Refs en los parciales) | Por abrir | — |
| 9 | `docs/backlog-sprint1` | Criterios detallados de HU-03 y HU-19, avance de HU-26 y `docs/backlog/pendientes.md`, `llevar-a-github.sh` | Por abrir | — |

**Cuándo:** después del PR 5, una por una, en este orden. Son solo documentación y no cambian el comportamiento.

**Cómo** (para cada una):

| Paso | Quién | Qué |
|---|---|---|
| 1 | Claude, desde el PC de Renato | Actualizar la rama con `main` con un merge normal (**no** `-s ours`: estas ramas no están en `main` y su contenido debe llegar). Comprobar que no haya conflictos y subirla. |
| 2 | Carlos, en la web | Abrir el PR (o usar #32) con base `main`, esperar el CI y pedir revisión a Renato. |
| 3 | Carlos, en la web | Fusionar con «Squash and merge». |

```sh
git fetch origin
git switch <rama>
git pull
git merge --no-edit origin/main
git push
```

**`CLAUDE.md` y Carlos:** `chore/estabilizacion-docs` (PR 5) ya cambia la fila de Carlos al mismo texto que `docs/agregar-carlos` (`ceal2013`). Un cambio idéntico en ambos lados no produce conflicto, y el PR 7 queda solo con CODEOWNERS. Si al revisarlo Carlos usa otro usuario, se corrige en el PR 7.

**`docs/backlog-sprint1`:** fue un borrador del backlog del Sprint 1. Al revisarlo, decidir si sus criterios detallados de HU-03 y HU-19 reemplazan los del backlog actual (que ya tiene HU-31 a HU-35) o si la rama se cierra sin fusionar.

---

## PR 1: Sprint 1

**Rama de origen:** `feat/HU-20-whatsapp` · **Rama base:** `main`

**Título:** `feat: incremento del Sprint 1 (reservas, flota, app del conductor, portal y WhatsApp)`

**Cuerpo:**

```markdown
Incremento del Sprint 1.

Closes #9
Closes #13
Closes #16
Closes #20
Closes #22
Closes #23
Closes #27
Refs #6

### Qué incluye

- HU-03: ingresar, editar y cancelar reservas.
- HU-10: administrar conductores y vehículos.
- HU-13: estado Disponible/No disponible del conductor.
- HU-17: abrir Google Maps o Waze.
- HU-19: formulario web de solicitud sin cuenta.
- HU-20: verificación del pasajero por WhatsApp.
- HU-26: registrar número de vuelo. Los vuelos de salida quedan fuera del MVP (PR-08).
- Base del panel, del backend y de la app del conductor.

H-3 (GPS en segundo plano) sigue abierta hasta la prueba en teléfono: por eso `Refs #6` y no `Closes`.

### Cómo revisarlo

Detalle por historia en `docs/prs/HU-XX.md`, y resultados en `docs/evidencias/HU-XX/`. Bitácora en `docs/avance.md`.

### Sin probar contra el servicio real

Twilio y FlightAware se probaron con dobles.
```

---

## PR 2: Sprint 2

**Rama de origen:** `feat/HU-24-calificacion` · **Rama base:** `main`

**Antes de abrirlo:** paso 5, con esta rama.

**Título:** `feat: incremento del Sprint 2 (mapa en vivo, asignación, ejecución del viaje y avisos)`

**Cuerpo:**

```markdown
Incremento del Sprint 2.

Closes #8
Closes #17
Closes #18
Closes #19
Closes #24
Closes #25

### Qué incluye

- HU-02: mapa en tiempo real de conductores.
- HU-14: notificación de viaje asignado.
- HU-15: aceptar o rechazar viaje en 60 s.
- HU-16: estados del viaje y registro de pago.
- HU-21: avisos de estado y cancelación por WhatsApp.
- HU-24: calificación del servicio. «Visible en HU-06» aceptado como parcial por el PO.
- PR-07: el estado del conductor llega al panel por el canal en vivo.

### Cómo revisarlo

Detalle por historia en `docs/prs/HU-XX.md`, y resultados en `docs/evidencias/HU-XX/`.

### Para revisar

- El commit `27588c6` dice HU-14 y `Refs #17`, pero contiene código de HU-15. La fusión squash lo absorbe.
- En esta rama el envío de WhatsApp todavía es síncrono: pasa a Celery en el PR del Sprint 3.

### Sin probar contra el servicio real

Twilio se probó con un doble. Geocerca y notificaciones, sin GPS real ni teléfono.
```

---

## PR 3: Sprint 3

**Rama de origen:** `fix/HU-27-origen-icao` · **Rama base:** `main`

**Antes de abrirlo:** paso 5, con esta rama.

**Título:** `feat: incremento del Sprint 3 (sugerencia, fila del aeropuerto, monitoreo de vuelos y convenios)`

**Cuerpo:**

```markdown
Incremento del Sprint 3.

Closes #10
Closes #14
Closes #28
Closes #29
Closes #30
Refs #8
Refs #19

### Qué incluye

- HU-04: sugerencia del conductor más apto.
- HU-11: administrar convenios con link y contraseña.
- HU-27: monitoreo de vuelo y ajuste de recogida.
- HU-28: alertas de demora, cancelación o desvío.
- HU-29: fila virtual del aeropuerto.

### También incluye

- `fix/dc17-trazabilidad` (`Refs #19`): la llegada manual queda marcada, con su distancia al origen.
- `fix/app-peticiones` (`Refs #19`): tiempo límite de 10 s en la app y pantalla que se corrige sola.
- `chore/celery`: worker y beat, con WhatsApp, vuelos y expiraciones como tareas con reintento.
- `feat/mapa-google` (`Refs #8`): adaptador de Google Maps con `VITE_GOOGLE_MAPS_KEY`.
- `fix/HU-27-origen-icao`: vuelo nacional si el ICAO del origen empieza con SC.

### Decisiones del PO

DC-16 a DC-24 aprobadas. El aviso al pasajero por cambio de hora queda como PR-14.

### Cómo revisarlo

Detalle en `docs/prs/` y resultados en `docs/evidencias/`.

### Para revisar

- Tras fusionar: reconstruir la imagen y `up -d --remove-orphans`, porque desaparecen `programador` y `asignaciones`.
- El cliente `redis` baja de 6.4.0 a 5.2.1, por el tope de Celery 5.5.
- El commit de Celery dice `Refs #8` por error: no tiene relación con esa HU.
- El link de convenio no abre nada hasta HU-25 (Sprint 4).

### Sin probar contra el servicio real

Twilio, FlightAware y Google Maps con dobles; geocerca y fila sin GPS real.
```

---

## PR 4: Sprint 4

**Rama de origen:** `docs/plan-fusion-sprint4` · **Rama base:** `main`

Es la punta de la cadena e incluye todo lo anterior: `feat/HU-05-cierre-forzado`, `feat/HU-18-mi-turno`, `feat/HU-12-auditoria-convenios`, `feat/HU-25-acceso-convenio`, `feat/HU-30-chat-whatsapp`, `feat/HU-01-indicadores`, `feat/HU-06-reportes`, `fix/HU-01-senal`, `fix/HU-25-declaracion` y `fix/HU-17-navegacion-texto`. No hay que abrir un PR por cada una.

**Antes de abrirlo:** paso 5, con esta rama.

**Título:** `feat: incremento del Sprint 4 (cierre forzado, Mi turno, acceso de convenio, chat, indicadores y reportes)`

**Cuerpo:**

```markdown
Incremento del Sprint 4.

Closes #7
Closes #11
Closes #12
Closes #15
Closes #21
Closes #26
Closes #31
Refs #20
Refs #25

### Qué incluye

- HU-01: panel de indicadores de reservas y vehículos.
- HU-05: cierre o anulación forzada de viaje.
- HU-06: reportes operativos y exportación CSV.
- HU-12: auditoría de cambios en convenios.
- HU-18: Mi turno, viajes completados.
- HU-25: acceso de convenio con link protegido.
- HU-30: chat de WhatsApp desde el panel.

### También incluye

- `fix/HU-01-senal` (`Refs #7`): vehículos en línea con señal y sin señal.
- `fix/HU-25-declaracion` (`Refs #26`): declaración del supervisor, guardada con fecha y nombre, y desbloqueo en auditoría.
- `fix/HU-17-navegacion-texto` (`Refs #20`): con el geocodificador de desarrollo, Google Maps y Waze navegan con la dirección escrita.

### Decisiones del PO

DC-25 a DC-30 aprobadas o tomadas por el PO. **Para confirmar:** en DC-27, «supervisor» es el nombre que escribe en el formulario, porque no tiene cuenta.

### Cómo revisarlo

Detalle en `docs/prs/HU-XX.md` y resultados en `docs/evidencias/HU-XX/`.

### Para revisar

- Migraciones: `flota.0004`, `convenios.0002`, `auditoria.0004` (`usuario_id` pasa a NULL) y `reservas.0009`.
- Tras fusionar: migrar y reiniciar `worker` y `beat`.
- Nginx debe reenviar `/ws/indicadores/`, igual que `/ws/mapa/`.

### Sin probar contra el servicio real

Twilio con un doble y el notificador de desarrollo. Mi turno y la navegación con la dirección escrita, sin probar en un teléfono.
```

---

## PR 5: cambios CC-12, CC-15 a CC-18 y rediseño del portal (fases 1 a 3)

**Rama de origen:** `feat/HU-44-mis-viajes` · **Rama base:** `main`

Es la punta de la cadena nueva: `chore/estabilizacion-docs` → `feat/HU-20-verificacion-repetida` → `feat/HU-31-turnos-caja` → `feat/HU-32-contingencia` → `test/CP-14-concurrencia-asignacion` → `feat/HU-33-login-unico` → `feat/HU-34-autoregistro-convenios` → `feat/HU-35-cuenta-pasajero` → `fix/estabilizacion-pantallas` → `feat/HU-36-usuarios-panel` → `chore/crear-empresa` → `chore/planes-comerciales` → `fix/primer-ingreso` → `feat/HU-37-sistema-visual` → `feat/HU-38-ingresar` → `feat/HU-40-cuenta-obligatoria` → `fix/ingreso-panel` → `feat/HU-39-pedido` → `fix/decisiones-fase1` → `feat/HU-41-recuperacion` → `feat/HU-42-revisa-pedido` → `feat/HU-43-tu-viaje` → `feat/HU-44-mis-viajes`.

**Antes de abrirlo:** paso 5, con esta rama.

**Título:** `feat: turnos y caja, contingencia, cuentas web, usuarios del panel y portal nuevo (CC-12, CC-15 a CC-18)`

**Cuerpo:**

```markdown
Cambios aprobados por el PO en CC-12, CC-15, CC-16, CC-17 y CC-18, y la fase 1 del rediseño del portal.

Closes #36
Closes #37
Closes #38
Closes #39
Closes #40
Closes #33
Closes #34
Closes #35
Closes #41
Closes #42
Closes #44
Closes #45
Closes #46
Closes #47
Closes #48
Closes #49
Closes #50
Closes #51
Refs #43
Refs #9
Refs #18
Refs #22
Refs #23

### Qué incluye

- Preliminares: evidencias de HU-03 y HU-19; el login bloquea la fila del usuario al contar intentos fallidos.
- DC-31: un teléfono verificado en los últimos 90 días no se vuelve a verificar.
- HU-31: historial de turnos y cierre de caja.
- HU-32: reservas de contingencia con folio.
- CP-14: asignación con dos peticiones simultáneas; se corrigió el orden de bloqueo al recibir posiciones.
- HU-33: inicio de sesión web único por rol y adaptador de correo.
- HU-34: autoregistro de convenios con aprobación; se retira el link con token de HU-11 y HU-25.
- HU-35: cuenta de pasajero opcional.
- Pantallas pendientes: formulario de contingencia y conciliación por folio, «Terminar turno» del administrador y sin creación de convenios por el administrador (decisión del PO sobre DC-35).
- HU-36: usuarios del panel para el administrador.
- Alta de clientes con `python manage.py crear_empresa` (procedimiento en `docs/README.md`).
- Planes del modelo comercial: INICIAL, ESTANDAR y AVANZADO.
- Primer ingreso con contraseña temporal en la web (DC-40).
- HU-37: sistema visual del portal (tokens, Plus Jakarta Sans autoalojada, componentes y mapa de respaldo).
- HU-38: ingresar y crear cuenta con el diseño nuevo. `/login` es el ingreso del panel con la marca FlotaÁgil; el del portal, con la marca de la empresa, es `/solicitar/:slug/ingresar`.
- HU-40 (CC-18): cuenta obligatoria para pedir; se retira el pedido como invitado (DC-41).
- HU-39: inicio y pedido del pasajero en tres tipos (`/pedir`), con pasajeros, maletas y vuelo de salida (DC-42) y la capacidad al pedir y al asignar (DC-43).
- Ajustes del PO: consentimiento único al crear la cuenta con fecha y versión (DC-44), capacidad con toda la flota y 4 sin vehículos (DC-43), soporte del panel por `SOPORTE_CORREO` y `CLAUDE.md` al día.
- HU-41: recuperación con enlace de 30 min y límite por correo; activa tu cuenta con reenvío y corrección del número; primer ingreso con el diseño nuevo (DC-45).
- HU-42 a HU-44: revisa tu pedido, pedido recibido, tu viaje y mis viajes; cancelar según RN-09 con motivo (DC-46).

### Cómo revisarlo

Detalle en `docs/prs/` y resultados en `docs/evidencias/`. Decisiones DC-31 a DC-46 (DC-36 provisorio hasta la plantilla de Meta) y PR-15 en `docs/diccionario-cambios.md`.

### Para revisar

- Migraciones: `cuentas.0007` a `0010` (la `0010` pasa BASICO a ESTANDAR y FLOTA_PLUS a AVANZADO), `flota.0005` y `0006` (pasa el último turno de DC-26 a TURNO), `auditoria.0005`, `reservas.0010` a `0013` y `convenios.0003`, que **no tiene reversa** (retira los tokens y las contraseñas de los links).
- Tras fusionar: migrar y reiniciar `worker` y `beat`. Nuevas variables en `.env.example`: `CORREO_*`, `SES_SMTP_*`, `WEB_URL_BASE` y `RECUPERAR_PASSWORD_HORAS`.
- Los links de convenio anteriores dejan de funcionar: las empresas deben registrarse en el portal. Los convenios sin cuenta quedan como historial.
- El administrador ya no crea convenios: `POST /api/convenios/` responde 405.
- Migraciones del rediseño: `cuentas.0011` y `reservas.0014` (pasajeros, maletas, vuelo de salida y antelaciones), reversibles.
- `POST /api/portal/{slug}/solicitudes/` ya no existe (CC-18): `/solicitar/:slug` lleva al ingreso de la empresa. Avisar a las empresas que compartieron ese enlace.
- El pasajero llega a `/pedir` al ingresar. `datos_demo` ya no tiene `--pendientes`.
- Migraciones `reservas.0015` (consentimiento, DC-44) y `reservas.0016` (reenvío de la activación, DC-45), reversibles.
- Variables nuevas en `.env.example`: `AVISO_PRIVACIDAD_VERSION`, `SOPORTE_CORREO`, `RECUPERAR_PASSWORD_MINUTOS` (reemplaza a `RECUPERAR_PASSWORD_HORAS`), `RECUPERAR_MAX_ENVIOS`, `RECUPERAR_VENTANA_MIN` y `ACTIVACION_MAX_REENVIOS`.
- Las cuentas de pasajero anteriores a DC-44 aceptan el aviso de privacidad la primera vez que ingresen.

### Sin probar contra el servicio real

Twilio y Amazon SES con dobles y backends de desarrollo.
```
