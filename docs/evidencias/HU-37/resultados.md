# HU-37 · Sistema visual del portal — resultados

Rama `feat/HU-37-sistema-visual`, 2026-11-10. Web: `src/diseno/diseno.test.tsx` y `src/diseno/tokens.test.ts` (57 en verde, cobertura 97,6 % en `src/diseno`). Datos sintéticos.

| Caso | Esperado | Obtenido |
|---|---|---|
| Tokens | Valores del diseño (`docs/diseño/portal/diseno-portal/README.md`) bajo `.tema-portal`; el panel no cambia | OK |
| Contraste AA | Texto ≥ 4,5:1 (texto, secundario, insignias, botones); bordes de campos y foco ≥ 3:1 | OK (21 pares) |
| Colores solo como tokens | Ningún hex, `rgb()` ni `hsl()` fuera de `tokens.css` | OK |
| Fuente | Plus Jakarta Sans 400–800 desde `@fontsource/plus-jakarta-sans` 5.3.0 (subconjunto latino), sin CDN | OK |
| Campo | Etiqueta asociada; error y ayuda fuera de la etiqueta, con `aria-describedby` | OK |
| Contador | Botones de 44 px con nombre, mínimo y máximo, valor anunciado | OK |
| Pestañas | Patrón ARIA: flechas, Inicio y Fin | OK |
| Diálogo | `aria-modal`, foco adentro, Tab no sale, Esc y tocar fuera cierran, el foco vuelve | OK |
| Línea de tiempo | Paso en curso con `aria-current="step"` y estado en texto | OK |
| Marco | Marca, navegación, «Saltar al contenido», menú de la cuenta (en el celular reemplaza la navegación) | OK |
| Mapa | `<Mapa>` dibuja el de respaldo (SVG, sin servicios externos); `<ProveedorMapa>` lo reemplaza sin tocar las pantallas | OK |

## Decisiones

- `--borde-campo` (#5F8F8B) para el borde de los campos: el `--borde` del diseño (#CFE8E5) no llega a 3:1 (WCAG 1.4.11) y queda solo para tarjetas.
- El portal es solo claro (`color-scheme: light`), como el diseño.
- Color por empresa preparado: `MarcoPortal` acepta `colores` con los tres tokens de marca; no se usa todavía.

## Límites conocidos

- Las capturas a 390 y 1440 px van con las pantallas que usan estos componentes (HU-38 y HU-39).
- El extremo claro del degradé hero (#2FA39C) no llega a 4,5:1 con texto blanco: solo lleva texto grande o va bajo la parte oscura.
