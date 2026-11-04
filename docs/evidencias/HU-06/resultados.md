# HU-06 · Reportes operativos y exportación CSV — resultados de pruebas

Rama `feat/HU-06-reportes`, 2026-11-04. Prueba manual contra el stack principal, con los datos sintéticos de las HU anteriores y la reserva 126, de convenio, recorrida por el flujo real hasta finalizar. No se borró nada. El panel se sirvió desde un build con un servidor estático mínimo, sin un Vite adicional.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 1043 pruebas en verde | 98 % total; `apps/reservas/reportes.py` 99 % |
| Web (Vitest) | 588 pruebas en verde | 94,4 % total |
| App (Vitest) | 80 pruebas en verde (sin cambios en esta HU) | — |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; sin migraciones pendientes; `verificar-carga` ok | — |

## Caso de prueba CP-25

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Liquidación | Por día y conductor, con desglose por método y totales del período | OK (automática y manual) |
| Cierres forzados | Incluidos, identificados con cantidad y monto | OK (automática y manual: 2 cierres, $30.500 de $75.000) |
| Facturación | Por convenio, con desglose | OK (automática y manual: reserva 126, $20.000) |
| Cancelaciones | Tasa por origen, sin dividir por cero | OK (automática y manual: 10 de 19, 52,6 %) |
| Historial | Pago, cierre o anulación forzada y calificación (HU-24), paginado con totales del período | OK (automática y manual) |
| Filtros | Fecha, conductor y convenio, en la URL | OK (automática y manual) |
| Fechas invertidas | Se explica, sin consultar ni exportar | OK (automática y manual); 400 en la API |
| CSV | Mismos filtros, columnas y totales; historial sin paginar; abre en Excel con acentos | OK (automática); manual: descarga con BOM y filas correctas, sin abrirlo en Excel |
| Fórmulas en el CSV | Un dato como `=HYPERLINK(...)` queda como texto | OK (automática) |
| Otra empresa (RN-13) | No aparece, ni con sus filtros | OK (automática y manual) |
| Despachador | 403 en la API; «sin permiso» en el panel, sin consultar | OK (automática; 403 también manual) |
| Celular (390 px) | Sin desborde horizontal | OK (manual) |

## Fallo corregido en la prueba manual

Al cambiar de reporte se veían un instante los datos del anterior bajo el título nuevo. Ahora solo se conservan dentro del mismo reporte. La prueba automática que lo cubre falla si se reintroduce el error.

## Límites conocidos

- **El CSV se arma completo en memoria.**
- **Sin abrir el archivo en Excel:** se comprobaron el formato y la codificación.

## Capturas

- `panel-liquidacion-escritorio.png` y `panel-liquidacion-celular.png`.
- `panel-facturacion-escritorio.png`, `panel-cancelaciones-escritorio.png`, `panel-historial-escritorio.png`.
- `ejemplo-liquidacion.csv`: archivo descargado, con datos sintéticos.
