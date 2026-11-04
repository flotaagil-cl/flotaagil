# HU-05 · Cierre o anulación forzada de viaje — resultados de pruebas

Rama `feat/HU-05-cierre-forzado`, 2026-11-04. Prueba manual contra el stack principal, con datos sintéticos nuevos (reservas 115 a 117 y conductores `hu05.*`). No se borró nada: al terminar, esos conductores quedaron No disponible y la reserva 117 cancelada, para que no aparezcan como candidatos ni pendientes.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 909 pruebas en verde | 98 % total; `apps/reservas/servicios.py` 99 %, `serializers.py` 97 % |
| Web (Vitest) | 532 pruebas en verde | 94,2 % total; `src/reservas` 99,6 % |
| App (Vitest) | 72 pruebas en verde (sin cambios en esta HU) | — |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; sin migraciones pendientes; `verificar-carga` ok | — |

## Reglas de la HU

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Cuándo | Solo con el pasajero a bordo; en otro estado, 409 sin cambios | OK (automática en 6 estados y manual en SOLICITADO y FINALIZADO). El botón solo aparece a bordo |
| Anular | Exige motivo; pasa a CANCELADO con el origen según el rol | OK (automática y manual: reserva 116, sin pago) |
| Cerrar | Exige motivo, método y monto (RN-10); pasa a FINALIZADO con su PAGO_VIAJE | OK (automática y manual: reserva 115, Tarjeta, $18.500) |
| Validación en el panel | Sin motivo o método no se envía; acepta «18.500» | OK (automática y manual) |
| Convenio como método | Solo en viajes de convenio | OK (automática; manual: no se ofrece sin convenio) |
| RN-11 | AUDITORIA con usuario, acción, motivo y estado previo; el cierre guarda también método y monto | OK (automática y manual, leído en la base) |
| Conductor | Vuelve a Disponible | OK (automática y manual) |
| Encuesta | El cierre forzado no la envía | OK (automática; manual: 0 mensajes de la reserva 115, 4 s después y con el worker activo) |
| Repetir | 409, sin segundo pago ni segunda auditoría | OK (automática; manual: 409) |
| Otra empresa (RN-13) | 404 | OK (automática y manual) |
| Rol conductor | 403 | OK (automática y manual) |
| Ficha | Muestra el motivo, el responsable y la fecha | OK (automática y manual) |
| Celular (390 px) | Sin desborde horizontal | OK (manual) |

## Cómo se hizo la prueba manual

- **El panel se sirvió desde un build (`vite build`), con un servidor estático mínimo y proxy al backend del 8000,** en vez de un Vite adicional. Es el mismo código, pero no el servidor de desarrollo.
- **Las reservas llegaron a «Pasajero a bordo» con la máquina de estados, desde el shell,** no recorriendo la app del conductor. Lo que se probó de punta a punta es el cierre forzado.

## Límites conocidos

- **Aviso a la app:** se comprobó con una prueba automática que se llama al aviso, no con una app abierta ni en un teléfono.
- **El pago no se ve en la ficha del panel:** queda en PAGO_VIAJE y en la auditoría. Ya estaba pendiente desde HU-16.
- **El campo de motivo se ve en letra monoespaciada,** igual que en el diálogo de cancelar: es un detalle anterior a esta HU.

## Capturas

- `panel-dialogo-validacion-escritorio.png`: errores al enviar vacío.
- `panel-dialogo-cerrar-escritorio.png`: cierre con método y monto.
- `panel-ficha-cierre-forzado-escritorio.png`: ficha con motivo y responsable.
- `panel-dialogo-anular-celular.png`: anulación, sin método ni monto.
- `panel-ficha-anulacion-forzada-celular.png`: ficha tras anular.
