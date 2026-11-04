# HU-04 · Sugerencia del conductor más apto — resultados de pruebas

Rama `feat/HU-04-sugerencia`, 2026-11-04. Datos sintéticos, en un stack aislado (base temporal), para no tocar el entorno de desarrollo.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 741 pruebas en verde | 98 % total; `asignacion.py` 97 % |
| Web (Vitest) | 486 pruebas en verde (ver nota) | 94,6 % total |
| App (Vitest) | 71 pruebas en verde (sin cambios en esta HU) | 95,3 % sentencias en la lógica |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; `verificar-carga` ok | — |

**Nota:** dos pruebas largas de formularios de la web (`cuentas.test.tsx`, `formulario-ui.test.tsx`) superaban el límite de 5 s con la máquina cargada, ajenas a esta HU. Es lo que explica el fallo intermitente registrado en HU-24. Se subió `testTimeout` a 20 s.

## Caso de prueba CP-18

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Diferencia de 1 km o más | Gana el más cercano, aunque acabe de terminar un viaje | OK (automática) |
| Diferencia de menos de 1 km | Gana quien lleva más tiempo sin viaje | OK (automática y manual) |
| Sin viajes terminados | Cuenta como quien lleva más tiempo | OK (automática) |
| Dos grupos de empate | Cada grupo se ordena por separado | OK (automática) |
| Solo se sugiere uno y el resto queda en el desplegable | Sugerido + desplegable | OK (automática y manual) |
| Posición antigua o imprecisa | No compite ni se sugiere | OK (automática y manual: «NO confiable» al final) |
| Nadie con posición confiable | No sugiere, lo explica y deja elegir | OK (automática) |
| Conductor con viaje en ejecución (RN-01, RN-03) | No aparece | OK (automática) |
| Consultar o abrir el diálogo (RN-02) | No asigna | OK (automática y manual) |
| Recogida en aeropuerto | No sugiere por distancia | OK (automática) |
| Elegir al sugerido | Queda `DISTANCIA` | OK (automática y manual) |
| Elegir a otro o sin sugerencia | Queda `MANUAL` | OK (automática) |

## Capturas

- `panel-sugerencia-escritorio.png` y `panel-sugerencia-celular.png`: sugerido y desplegable.
