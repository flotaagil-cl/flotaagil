# Plan de fusión: Sprints 1 a 4

Para Carlos. Son 4 PR hacia `main`, uno por sprint, **en este orden**.

| PR | Sprint | Rama de origen | Rama base | Issues que cierra |
|---|---|---|---|---|
| 1 | Sprint 1 | `feat/HU-20-whatsapp` | `main` | #9, #13, #16, #20, #22, #23, #27 |
| 2 | Sprint 2 | `feat/HU-24-calificacion` | `main` | #8, #17, #18, #19, #24, #25 |
| 3 | Sprint 3 | `fix/HU-27-origen-icao` | `main` | #10, #14, #28, #29, #30 |
| 4 | Sprint 4 | `feat/HU-06-reportes` | `main` | #7, #11, #12, #15, #21, #26, #31 |

## Antes de empezar

- **Carlos solo usa la web.** Abre, revisa y fusiona ahí. El paso 5 requiere una terminal y **lo hace Claude desde el PC de Renato**, cuando Renato le avisa que se fusionó el PR.
- **No uses el botón «Update branch» en los PR 2, 3 y 4, ni abras uno antes de que Renato confirme el paso 5.** Generaría conflictos: las ramas están encadenadas y la fusión es *squash*.
- **Revisión:** el ruleset exige una aprobación. Si tú abres el PR, lo aprueba Renato.
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

Tras el PR 4 el paso 5 ya no hace falta.

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
- **Tras fusionar el PR 4:** migraciones y reinicio de `worker` y `beat`. Trae tres migraciones y la tarea `enviar_chat`.
- **Los PR abiertos** de Dependabot (#1 a #4) y #32 no son parte de este plan. Dependabot propondrá subir `redis` a más de 5.2.1: no se debe aceptar sin subir también Celery.

Según CLAUDE.md, después de cada PR corresponde la línea base del sprint (`v0.1`, `v0.2`, `v0.3`, `v0.4`).

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

**Rama de origen:** `feat/HU-06-reportes` · **Rama base:** `main`

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
Refs #25

### Qué incluye

- HU-01: panel de indicadores de reservas y vehículos.
- HU-05: cierre o anulación forzada de viaje.
- HU-06: reportes operativos y exportación CSV.
- HU-12: auditoría de cambios en convenios.
- HU-18: Mi turno, viajes completados.
- HU-25: acceso de convenio con link protegido.
- HU-30: chat de WhatsApp desde el panel.

### Decisiones

DC-25 a DC-27 siguen las decisiones del PO. **DC-28 y DC-29 están pendientes de aprobación:** qué es «en línea», quién ve los indicadores, sin comisiones en la liquidación y qué fecha usa cada reporte.

### Cómo revisarlo

Detalle en `docs/prs/HU-XX.md` y resultados en `docs/evidencias/HU-XX/`.

### Para revisar

- Migraciones: `flota.0004`, `convenios.0002` y `auditoria.0004` (`usuario_id` pasa a NULL).
- Tras fusionar: migrar y reiniciar `worker` y `beat`.
- Nginx debe reenviar `/ws/indicadores/`, igual que `/ws/mapa/`.
- HU-25: confirmar que el supervisor acepta los avisos en nombre del pasajero.

### Sin probar contra el servicio real

Twilio con un doble y el notificador de desarrollo. Mi turno, sin probar en un teléfono.
```
