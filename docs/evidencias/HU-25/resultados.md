# HU-25 · Acceso de convenio con link protegido — resultados de pruebas

Rama `feat/HU-25-acceso-convenio`, 2026-11-04. Prueba manual contra el stack principal, con convenios sintéticos nuevos y la reserva 121, cancelada al terminar. No se borró nada. Se aplicaron las migraciones `convenios.0002` y `auditoria.0004` a la base principal. El panel se sirvió desde un build con un servidor estático mínimo, sin un Vite adicional. Las capturas no muestran el token ni la contraseña.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 967 pruebas en verde | 98 % total; `apps/portal` 99 % |
| Web (Vitest) | 552 pruebas en verde | 94,4 % total; `src/portal` 96,1 % |
| App (Vitest) | 80 pruebas en verde (sin cambios en esta HU) | — |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; sin migraciones pendientes; `verificar-carga` ok | — |

## Caso de prueba CP-26

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Sin sesión | Pide contraseña, sin revelar el cliente ni mostrar el formulario | OK (automática y manual) |
| Contraseña incorrecta | Rechazada, sin sesión | OK (automática y manual) |
| Bloqueo | Al quinto intento, 15 min por convenio, también con la correcta | OK (automática y manual: 14,9 min restantes) |
| Bloqueo configurable | Lo fija `CONVENIO_BLOQUEO_MIN` | OK (automática) |
| Bloqueo vencido | Parte de cero | OK (automática) |
| AUDITORIA | `BLOQUEO_LINK` sin usuario, con la empresa; se ve en la ficha del convenio; sin la contraseña probada | OK (automática y manual) |
| Otro convenio | No se bloquea | OK (automática) |
| Cookie | httpOnly, SameSite=Strict, ruta `/api/convenio/`, 2 h; invisible para JavaScript | OK (automática y manual) |
| Inactividad | Vence a las 2 h sin uso; con uso a la 1,5 h sigue viva a las 3 h | OK (automática, con el reloj controlado) |
| Sesión inválida | Alterada, de otro convenio o tras rotar: 401 | OK (automática) |
| Recargar la página | La sesión sigue | OK (manual) |
| RN-07 | SOLICITADO, canal CONVENIO, con el convenio; sin verificación; no expira por RN-06 | OK (automática y manual: reserva 121) |
| Aviso | Llega el de confirmación, como en el panel | OK (automática y manual: un mensaje con simulación, sin Twilio real) |
| Método Convenio | La app lo admite al finalizar | OK (automática) |
| RN-08 | Desactivar da 404 al instante, con sesión abierta, sin tocar las reservas | OK (automática y manual) |
| Origen ajeno | 403 | OK (automática y manual) |
| Salir | Borra la cookie y vuelve a la contraseña | OK (automática) |
| Celular (390 px) | Sin desborde horizontal | OK (manual) |

## Ajustes del PO (`fix/HU-25-declaracion`)

Prueba manual con convenios sintéticos nuevos y las reservas 127 y 128, canceladas al terminar. Se aplicó `reservas.0009` a la base principal. Suites en esta rama: backend 1063 (98 % de líneas), web 591 (94,4 %).

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Casilla «Declaro que el pasajero autorizó recibir avisos por WhatsApp» | Obligatoria en el formulario y en la API | OK (automática y manual) |
| Nombre del supervisor | Obligatorio, hasta 80 caracteres | OK (automática y manual) |
| Registro | VIAJE guarda la fecha y el supervisor | OK (automática y manual: reserva 128) |
| Portal público | No pide ni guarda la declaración | OK (automática) |
| Rotar con el link bloqueado | Levanta el bloqueo y registra `DESBLOQUEO_LINK` con el administrador | OK (automática y manual) |
| Rotar sin bloqueo vigente | No registra desbloqueo | OK (automática) |

El supervisor no tiene cuenta, así que «supervisor» es el nombre que escribe en el formulario: no está verificado. Lo respalda que entró con la contraseña del convenio.

## Fallos corregidos en las pruebas

- **Salir no funcionaba:** el 204 sin cuerpo se trataba como error.
- **`verificar-carga`:** ahora vigila también la ruta del link, que no debe cargar nada del panel ni de la sesión.

## Límites conocidos

- **Salir no revoca la sesión en el servidor:** una copia de la cookie sirve hasta que venza o se rote la contraseña.
- **Sesión vencida al enviar:** vuelve a pedir la contraseña y el formulario se pierde.
- **Sin probar contra Twilio real.**
- **El token va en la URL:** puede quedar en el historial del navegador y en los registros del servidor. Por eso también se exige la contraseña.

## Capturas

- `convenio-contrasena-celular.png`, `convenio-formulario-celular.png`, `convenio-confirmacion-celular.png`.
- `convenio-no-disponible-celular.png`: convenio desactivado con la sesión abierta.
- `convenio-bloqueado-escritorio.png`: bloqueo tras 5 intentos.
- `convenio-declaracion-celular.png`: casilla y nombre del supervisor.
- `panel-auditoria-desbloqueo-escritorio.png`: bloqueo y desbloqueo en la auditoría.
