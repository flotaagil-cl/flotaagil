# HU-11 · Administrar convenios con link y contraseña — resultados de pruebas

Rama `feat/HU-11-convenios`, 2026-11-04. Datos sintéticos, en un stack aislado. Las capturas muestran una contraseña y un token generados en esa base temporal, que ya no existe: no sirven para nada.

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Backend (pytest) | 866 pruebas en verde | 98 % total; `apps/convenios` sobre 97 % |
| Web (Vitest) | 520 pruebas en verde | 94,4 % total; `src/convenios` 83,8 % |
| App (Vitest) | 72 pruebas en verde (sin cambios en esta HU) | 95,3 % sentencias en la lógica |
| Estático | ruff, bandit, ESLint, `tsc`; OpenAPI validado; `verificar-carga` ok | — |

## Caso de prueba CP-22

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Crear | Token de 256 bits (43 caracteres) y contraseña generada | OK (automática y manual) |
| Contraseña | Solo con hash PBKDF2; se muestra una vez, nunca en la URL ni en la auditoría | OK (automática y manual: no vuelve tras cerrar ni al recargar) |
| Rotar | La nueva sirve, la anterior no; el token no cambia | OK (automática y manual) |
| RN-12 | Rotar, desactivar y activar quedan en auditoría, sin hashes | OK (automática y manual) |
| Desactivar (RN-08) | Pide confirmar; las reservas siguen ahí, sin cancelarse | OK (automática y manual: 1 reserva conservada) |
| Convenio inactivo (RN-08) | No admite reservas nuevas en el panel | OK (automática) |
| Reactivar | Mismo link, misma contraseña | OK (automática) |
| Listado | Volumen de reservas; sin el token | OK (automática y manual) |
| Validación | RUT con dígito verificador, nombre no vacío | OK (automática) |
| Otra empresa (RN-13) | 404, sin cambios | OK (automática) |
| Despachador | 403 en la API; «sin permiso» en el panel, sin consultar la API | OK (automática y manual) |

## Límites conocidos

- **El link todavía no abre nada:** la entrada del cliente con link y contraseña es HU-25, del Sprint 4. Hasta entonces, desactivar el convenio tampoco tiene un efecto visible en el link. Las validaciones de esta HU sobre estado y contraseña son las que usará HU-25.
- **No se puede rotar el token del link:** no está en los criterios. Si se filtra, hoy la salida es desactivar el convenio y crear otro.
- **Desactivar solo se prueba contra reservas nuevas en el panel:** el formulario del convenio llega con HU-25.

## Capturas

- `panel-contrasena-una-vez-escritorio.png`: contraseña recién creada.
- `panel-convenio-inactivo-escritorio.png`: convenio desactivado.
- `panel-listado-celular.png`: listado con el volumen de reservas.
