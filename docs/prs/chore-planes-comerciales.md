# PR de los planes del modelo comercial

**Rama:** `chore/planes-comerciales` (encadenada desde `chore/crear-empresa`). Es la punta de la cadena del PR 5.

**Título:** `fix(backend): planes del modelo comercial en EMPRESA (DC-39)`

## Cuerpo

- `EMPRESA.plan`: INICIAL, ESTANDAR o AVANZADO (CC-13 del informe), con valor por defecto ESTANDAR.
- Migración `cuentas.0010_planes_comerciales`: BASICO → ESTANDAR y FLOTA_PLUS → AVANZADO, con reversa (probada en la base de desarrollo).
- Nada del sistema dependía del plan: solo el admin interno, `datos_demo` y la validación de `crear_empresa`.
