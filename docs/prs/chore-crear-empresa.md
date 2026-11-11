# PR de alta de empresa

**Rama:** `chore/crear-empresa` (encadenada desde `feat/HU-36-usuarios-panel`). Va dentro del PR 5 del plan de fusión.

**Título:** `chore(backend): comando crear_empresa para dar de alta clientes`

## Cuerpo

- `python manage.py crear_empresa --rut --razon-social --slug --plan --admin-email --admin-nombre [--geocerca-scl]`.
- Crea la empresa, su configuración por defecto y su primer administrador con temporal impresa una vez. Funciona en producción.
- Valida RUT, slug y correo; si algo ya existe, no crea nada.
- Procedimiento documentado en `docs/README.md`. Decisión: DC-38.
