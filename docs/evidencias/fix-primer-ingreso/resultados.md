# Primer ingreso con contraseña temporal (DC-40) — resultados

Rama `fix/primer-ingreso`, 2026-11-10. Web: `src/paginas/primer-ingreso.test.tsx` (4 en verde). Datos sintéticos.

| Caso | Esperado | Obtenido |
|---|---|---|
| Ingresa con temporal | Va a «Crea tu contraseña»; al guardarla vuelve a iniciar sesión y llega a su vista | OK |
| Intenta ir a otra pantalla | La guarda lo devuelve al primer ingreso | OK |
| Validación | Temporal obligatoria, mínimo 10 caracteres, coincidencia y distinta de la temporal | OK |
| Temporal equivocada | Error del servidor en el campo | OK |
| Sin temporal | `/primer-ingreso` lleva a su vista | OK |

## Límites conocidos

- Usa el estilo del login actual; el diseño nuevo llega con HU-41.
