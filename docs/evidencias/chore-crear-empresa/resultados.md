# Alta de empresa (`crear_empresa`) — resultados

Rama `chore/crear-empresa`, 2026-11-10. Tarea técnica (2 SP), sin pantallas: validada con `cuentas/tests/test_crear_empresa.py` (10 en verde). Datos sintéticos.

| Caso | Esperado | Obtenido |
|---|---|---|
| Alta con `DEBUG=False` | Empresa, configuración por defecto y administrador con temporal (vence a las 72 h, obliga a cambiarla); la temporal sale una vez y no queda en la auditoría | OK |
| `--geocerca-scl` | Geocerca del aeropuerto SCL | OK |
| RUT con dígito verificador malo, slug fuera de kebab-case, correo inválido, razón social vacía | Falla sin crear nada | OK |
| RUT, slug o correo ya existentes | Falla sin crear nada | OK |
| Plan fuera del dominio | Falla | OK |
| Auditoría | `ALTA_EMPRESA`, sin usuario, con la empresa | OK |

## Límites conocidos

- La geocerca de SCL es el rectángulo aproximado de DC-21.
