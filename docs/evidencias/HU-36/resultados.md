# HU-36 · Usuarios del panel — resultados

Rama `feat/HU-36-usuarios-panel`, 2026-11-10. CC-17 (#41). Datos sintéticos.

| Caso | Esperado | Obtenido |
|---|---|---|
| Listado | Solo administradores y despachadores de la empresa; sin conductores, convenios ni pasajeros | OK (automática y web) |
| Crear | Temporal mostrada una vez (no-store), vence a las 72 h, obliga a cambiarla; auditoría `CREAR` y `GENERAR_PASSWORD` sin la contraseña | OK (automática, web y manual) |
| Correo usado | 400 con el mensaje de correo único (PR-15) | OK (automática y web) |
| Rol fuera del panel | 400 | OK (automática) |
| Editar nombre y rol | Auditoría `EDITAR` con lo anterior; cambiar el rol cierra sus sesiones | OK (automática) |
| Propio rol / propia cuenta | 409 `propio_rol` / `propia_cuenta`; la pantalla no los ofrece | OK (automática y web) |
| Último administrador activo | 409 `ultimo_administrador` (un administrador inactivo no cuenta) | OK (automática y web) |
| Desactivar | La sesión abierta deja de servir al instante (401) y el refresh también; se puede reactivar | OK (automática y web) |
| Restablecer | Temporal nueva; levanta el bloqueo por intentos | OK (automática y web) |
| RN-13 y permisos | Otra empresa 404; despachador 403 | OK (automática y web) |

## Límites conocidos

- La temporal de la captura se invalidó en la base de desarrollo después de tomarla.

## Capturas

- `panel-usuarios-temporal-escritorio.png`
