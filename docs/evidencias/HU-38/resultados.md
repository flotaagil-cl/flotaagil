# HU-38 · Ingresar y crear cuenta — resultados

Ramas `feat/HU-38-ingresar` y `fix/ingreso-panel`, 2026-11-11. Web: `src/paginas/acceso.test.tsx`. Datos sintéticos; las capturas no tienen credenciales.

| Caso | Esperado | Obtenido |
|---|---|---|
| Ingreso del portal | `/solicitar/:slug/ingresar` con la marca de la empresa; mapa y panel inferior en el celular, panel con degradé en el computador | OK (`ingresar-portal-*.png`) |
| Crear cuenta | Nombre y apellido, correo, WhatsApp con +56, contraseña de 10+ caracteres y aviso de privacidad; mismo endpoint de HU-35 | OK (`crear-cuenta-*.png`) |
| Errores | Por campo, fuera de la etiqueta; 429 y otros como aviso general | OK |
| Comparación con el diseño | `docs/diseno/portal/web/01-ingresar.png` y `movil/01-ingresar.png`: títulos, panel con degradé, botón secundario, asa del panel móvil | OK, con las diferencias de abajo |

## Diferencias deliberadas con el diseño

- Borde de los campos más oscuro (#5F8F8B) para llegar a 3:1 (WCAG 1.4.11).
- Casilla «Acepto el aviso de privacidad» (no hay términos de uso todavía).
- El mapa del ingreso no muestra vehículos: serían datos inventados.
