# HU-33 · Inicio de sesión web único — resultados

Rama `feat/HU-33-login-unico`, 2026-11-10. CC-16 (#35). Datos sintéticos (`pasajero.demo@transportes-andes.example`).

| Caso | Esperado | Obtenido |
|---|---|---|
| Administrador, despachador, convenio y pasajero en `/api/auth/token/` | 200 con la cookie del panel y el rol | OK (automática) |
| Conductor en el login web / roles web en la app | 403 `rol_no_permitido` / 403 | OK (automática y web) |
| Convenio y pasajero renuevan la sesión | 200 | OK (automática) |
| Convenio y pasajero contra el panel (reservas, conductores, vehículos, convenios, caja, indicadores) | 403 | OK (automática) |
| Bloqueo tras 5 intentos | También para los roles nuevos | OK (automática) |
| Destino tras el login | `/`, `/mi-convenio`, `/mis-reservas`; con `volver`, el destino pedido | OK (web y manual) |
| Marco del panel | Menú solo con su vista, sin alertas de vuelo; `/` lleva a su vista; el panel por URL dice «sin permiso» | OK (web) |
| Portal con cuatro opciones | Invitado (formulario), iniciar sesión, crear cuenta, registrar empresa | OK (web y manual) |
| Correo | Consola por defecto; SES por configuración; reintenta fallas transitorias y no las definitivas | OK (automática) |

## Límites conocidos

- «Crear cuenta» y «Registrar mi empresa» llevan a pantallas de HU-35 y HU-34.
- SES sin probar contra el servicio real: no hay credenciales.

## Capturas

- `portal-cuatro-opciones-celular.png`
- `login-unico-pasajero-escritorio.png`
