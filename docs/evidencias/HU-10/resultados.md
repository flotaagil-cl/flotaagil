# HU-10 · Administrar conductores y vehículos — resultados de pruebas

Rama `feat/HU-10-flota`, 2026-11-03. Datos sintéticos (`datos_demo` y cuentas `*.example`).

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 504 pruebas en verde | 98,5 % total |
| Web (Vitest) | 438 pruebas en verde | 94,4 % total; `src/flota` 96,6 % |
| Estático | ruff, bandit, ESLint y `tsc` sin hallazgos; OpenAPI validado; `gen:api` sin diferencias | — |
| Build | `verificar-carga` ok: 21 pantallas con lazy; flota fuera del paquete inicial, del login y del portal | — |

## Casos de prueba

| CP | Qué se probó | Esperado | Obtenido |
|---|---|---|---|
| CP-01 | Registrar un vehículo con la patente escrita «gh-jk 20» | Se guarda «GHJK20» y abre la ficha | OK (automática y manual) |
| CP-01 | Patente repetida, año fuera de la antigüedad máxima (12 años), capacidad 8 | 400 en el campo, sin crear | OK |
| CP-01 | Desactivar un vehículo declarado por un conductor Disponible | 409 `flota_en_uso` con el nombre del conductor | OK (manual: DMAA10) |
| CP-01 | CSV con una línea válida, una patente ya registrada y una inválida | Informe por línea, sin botón «Cargar», nada creado | OK |
| CP-01 | CSV válido de Excel (punto y coma, Windows-1252) | Crea todos | OK |
| CP-02 | Alta de un conductor | Cuenta CONDUCTOR sin contraseña utilizable, estado «Sin contraseña» | OK |
| CP-02 | Generar la contraseña temporal | 14 caracteres sin ambiguos, se muestra una vez, «Copiar» funciona, no queda en la página ni en el almacenamiento del navegador | OK (manual) |
| CP-02 | Login de la app con la temporal | 200 con `debe_cambiar_password: true` | OK |
| CP-02 | Otros endpoints con la temporal pendiente (`/api/viajes/`, `/api/vehiculos/`, `/api/conductores/`) | 403 `cambio_password_requerido` | OK |
| CP-02 | Endpoints permitidos con la temporal pendiente | `yo` 200, refresh 200, cambiar contraseña 200, logout 204 | OK |
| CP-02 | Cambiar la contraseña | Tokens nuevos; refresh anterior 401; la temporal ya no sirve | OK |
| CP-02 | Temporal vencida (72 h) | 401 `password_temporal_vencida` | OK (automática) |
| CP-02 | Deshabilitar | Sesiones cerradas, No disponible, login 401 `cuenta_deshabilitada`, auditoría | OK |
| CP-02 | Deshabilitar o restablecer en viaje | 409 `conductor_en_viaje` | OK (automática) |
| CP-02 | Logout de la app (PR-02) | 204 y el refresh queda inválido | OK |
| CP-02 | Editar RUT inválido / repetido; asociar y quitar vehículos; quitar el declarado en turno | 400 en el campo / N:M / 409 | OK |
| — | Aislamiento por empresa (RN-13) y permisos | Despachador 403 y «Sin permiso» en el panel; lo de otra empresa 404 | OK |

## La contraseña temporal no se filtra

| Dónde se buscó | Resultado |
|---|---|
| Respuesta al administrador que la generó (`POST /api/conductores/{id}/password/`, `Cache-Control: no-store`) | Única aparición |
| Detalle y listado del conductor | No aparece (prueba automática) |
| Tabla `auditoria` (`datos_previos` y `motivo`) | 0 filas (prueba automática y búsqueda en la base) |
| Tabla `usuario` (solo hash PBKDF2) | 0 filas con el texto |
| Logs del backend y del servidor de desarrollo | 0 apariciones (`caplog` en la prueba automática y `docker compose logs`) |
| `localStorage` y `sessionStorage` del panel | No aparece |

## Manejador de errores con `code` en toda la API

Antes solo autenticación y portal agregaban `code`. Ahora todo error con solo `detail` lo trae: 401 `not_authenticated`, 403 `permission_denied` o `cambio_password_requerido`, 404 `not_found` (también el `Http404` de Django), 405 `method_not_allowed`, 409 `conflicto_estado` / `flota_en_uso` / `conductor_en_viaje`, 429 `throttled`. Los 400 de validación (errores por campo) no cambian. En la web, el aplanador de errores ignora ese `code` para no mostrarlo como mensaje; la suite web completa (438 pruebas) pasa.

## Capturas

- `conductor-password-temporal-escritorio.png`: diálogo de la contraseña temporal (cuenta sintética; esa temporal ya se cambió durante la prueba y no sirve).
- `conductores-escritorio.png`: listado con el estado de las cuentas.
- `conductor-ficha-celular.png`: ficha en 390 px, sin scroll horizontal.
