# Ingreso del panel y del portal — resultados

Rama `fix/ingreso-panel` (encadenada desde `feat/HU-40-cuenta-obligatoria`), 2026-11-11. Web: `src/paginas/acceso.test.tsx` y `src/cuentas-web/login-unico.test.tsx`. Datos sintéticos; las capturas no tienen credenciales.

| Caso | Esperado | Obtenido |
|---|---|---|
| `/login` | Ingreso del panel con la marca FlotaÁgil (`docs/diseno/panel/00-login.png`) | OK (`ingreso-panel-1440.png`) |
| Bajo 1024 px | Sin el panel con el degradé; formulario centrado, sin mapa ni panel deslizable | OK (`ingreso-panel-390.png`) |
| Olvidé mi contraseña (panel) | Pide una temporal al administrador; sin enlace a /recuperar | OK |
| Pasajeros y convenios en `/login` | Aviso: entrar desde el enlace de su empresa; si entran igual, llegan a su vista (HU-33 sin cambios) | OK |
| `/solicitar/:slug/ingresar` | Ingreso del portal con la marca de la empresa, mapa y panel inferior en el celular, crear cuenta y recuperar | OK |
| `/solicitar/:slug` | Lleva al ingreso del portal (HU-40) | OK |

## Límites conocidos

- El enlace «Soporte» de la barra del diseño no se agregó: falta definir el contacto de soporte.
- La mini vista del panel es una ilustración con datos de ejemplo, oculta a los lectores de pantalla.
