# PR de la verificación repetida (DC-31)

**Rama:** `feat/HU-20-verificacion-repetida` (encadenada desde `chore/estabilizacion-docs`). Va dentro del PR 5 del plan de fusión.

**Título:** `feat(backend): no volver a verificar un teléfono verificado hace poco (DC-31)`

## Cuerpo

Refs #23

### Qué hace

- **DC-31:** `CONFIGURACION_EMPRESA.vigencia_verificacion_dias` (90 por defecto; 0 la desactiva).
- Si el pasajero de ese número en la empresa confirmó por WhatsApp dentro de la vigencia, la solicitud del portal nace en SOLICITADO, se envía el aviso de confirmación (HU-21) y `expira_en` llega NULL.
- Se mantiene el límite de 3 solicitudes por número cada 15 min.
- Portal: la confirmación dice que el número ya está verificado, sin plazo.

### Pruebas

- Backend: 9 pruebas nuevas; `portal/servicios.py` 100 %.
- Web: 1 prueba nueva.
- Manual con capturas: `docs/evidencias/verificacion-repetida/`.

### Migración

`cuentas.0007_vigencia_verificacion`.
