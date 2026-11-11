# PR del primer ingreso

**Rama:** `fix/primer-ingreso` (encadenada desde `chore/planes-comerciales`). Va dentro del PR 5 del plan de fusión.

**Título:** `fix(web): cambiar la contraseña temporal en el primer ingreso (DC-40)`

## Cuerpo

Refs #42

- La guarda de rutas lleva a `/primer-ingreso` a quien entra con contraseña temporal (DC-14), en cualquier rol web.
- Al cambiarla vuelve a iniciar sesión y sigue a su vista.
- Corrige que los usuarios de HU-36, el administrador de `crear_empresa` y los convenios restablecidos no podían entrar.
