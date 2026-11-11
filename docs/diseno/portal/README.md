# Diseño del portal · Tiffany degradé

Referencia visual del portal web (pasajero y empresa en convenio). Las imágenes usan datos ficticios.
- `web/`: 1440 px de ancho (computador).
- `movil/`: 390 px de ancho (celular). Es la misma web responsiva, no una app.

## Colores (tokens)
| Token | Valor | Uso |
|---|---|---|
| --color-primario-900 | #0B4F5C | inicio de degradés, texto sobre claro |
| --color-primario-700 | #0C7F7D | pines del mapa, pestaña activa, íconos |
| --color-tiffany | #81D8D0 | insignias, fin del degradé destacado |
| --color-tiffany-50 | #E3F6F4 | inicio del degradé destacado |
| --fondo | #F2FBFA | fondo de página |
| --superficie | #FFFFFF | tarjetas, inputs, barra superior |
| --texto | #0F2A2E | texto principal |
| --texto-suave | #4F6A6C | texto secundario, placeholders |
| --borde | #CFE8E5 | bordes de inputs y tarjetas |
| --suave | #DDF3F1 | campos bloqueados, fondos de íconos |
| --mapa / --parque | #E1F0EE / #D3E6D8 | mapa de respaldo |
| --peligro | #B42318 | cancelar, eliminar cuenta |
| --exito | #1A7F45 | reglas cumplidas, verificado |

Degradés:
- `--grad-boton`: linear-gradient(90deg, #0B4F5C, #0C7F7D). Botón principal, texto blanco.
- `--grad-destacado`: linear-gradient(110deg, #E3F6F4, #81D8D0). Franja "Seguimos tu vuelo por ti" y avisos, texto oscuro.
- `--grad-hero`: linear-gradient(140deg, #0B4F5C 0%, #0C7F7D 65%, #2FA39C 100%). Panel lateral de ingreso y cabeceras móviles, texto blanco.

Insignias de estado (fondo / texto): info #81D8D0 / #0F2A2E · ok #D9F2E3 / #14532D · revisión #FDF0D5 / #7A4B00 · peligro #FDE3E1 / #8A1C12 · neutra #DDF3F1 / #4F6A6C.

## Tipografía
Plus Jakarta Sans 400, 500, 600, 700 y 800, autoalojada con @fontsource (sin CDN).
Título web: 38/44, peso 800, letter-spacing -0.8 px. Título móvil: 22 a 26, peso 800. Texto: 15. Etiquetas: 13, peso 600.

## Medidas
Inputs de 48 a 50 px de alto, radio 10. Botón principal de 54 px, radio 12. Tarjetas con radio 16. Panel hero con radio 24. Panel inferior móvil con radio 22. Toda zona táctil mide al menos 44 px.

## Pantallas
web y movil: ingresar, crear cuenta, pedir (desde el aeropuerto, al aeropuerto, en la ciudad), olvidaste tu contraseña, revisa tu correo, nueva contraseña, activa tu cuenta, primer ingreso, revisa tu pedido, pedido recibido, tu viaje, mis viajes, cancelar viaje, registro de empresa, empresa en revisión y mi perfil.
Solo web: 18 · convenio, pedir para el equipo.
Movil: además 03 · inicio, con las 3 opciones de viaje.
