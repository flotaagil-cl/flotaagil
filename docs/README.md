# docs/

Índice de la documentación de FlotaÁgil. La fuente de verdad es el Informe 2 (ES2).

| Ruta | Contenido |
|---|---|
| [`backlog/backlog.json`](backlog/backlog.json) | Product backlog: 44 HU + H-3 (274 SP); HU-31 a HU-36 por CC-12, CC-15, CC-16 y CC-17; HU-37 a HU-49 por el rediseño del portal (HU-40 por CC-18) |
| [`diccionario-datos.md`](diccionario-datos.md) | Diccionario de datos (Anexo D del Informe 2): fuente de los modelos del backend |
| [`diccionario-cambios.md`](diccionario-cambios.md) | Agregados y desvíos respecto del Anexo D, para actualizar el informe |
| [`sprint0.md`](sprint0.md) | Instrucciones del Sprint 0 (ecosistema GitHub) |
| [`evidencias/`](evidencias/) | Evidencias de ejecución de casos de prueba (CP-xx) |

Se agregarán: informes, registro de decisiones, informe de la PoC de GPS (H-3), runbook y resultados de pruebas de carga y seguridad.

## Alta de un cliente nuevo

Procedimiento para dar de alta a una empresa de taxis (DC-38). Se ejecuta en el servidor, dentro del contenedor del backend; funciona en producción porque no exige `DEBUG`:

```sh
docker compose exec backend python manage.py crear_empresa \
  --rut 76543210-3 \
  --razon-social "Taxis Ejemplo SpA" \
  --slug taxis-ejemplo \
  --plan ESTANDAR \
  --admin-email admin@taxis-ejemplo.cl \
  --admin-nombre "Nombre Apellido" \
  --geocerca-scl
```

- Crea la EMPRESA, su CONFIGURACION_EMPRESA con los valores por defecto y su primer ADMINISTRADOR.
- `--plan`: uno de los planes del modelo comercial (`INICIAL`, `ESTANDAR` o `AVANZADO`).
- `--geocerca-scl` (opcional) agrega la geocerca aproximada del aeropuerto SCL (DC-21); la empresa debe ajustarla en el admin.
- Valida el RUT con su dígito verificador, el slug en kebab-case y el correo. Si el RUT, el slug o el correo ya existen, no crea nada.
- Imprime **una sola vez** la contraseña temporal del administrador (vence a las 72 h y obliga a cambiarla). Entrégasela por un canal seguro; si se pierde, otro administrador la restablece en «Usuarios» o se vuelve a generar desde el admin interno.
- El portal queda en `/solicitar/<slug>`. Desde ahí el administrador crea los demás usuarios del panel (HU-36) y los conductores (HU-10).

## Pendientes de configuración

- [ ] **Cuando Carlos Ortiz se sume al repositorio:** evaluar volver a exigir 1 aprobación en el ruleset «Proteger main». Desde DC-49 el ruleset no tiene bypass. Mientras tanto, Renato integra cada PR con el check `ci` y la lista de chequeo de [`prs/lista-de-chequeo.md`](prs/lista-de-chequeo.md) (DC-47).
- [ ] Descomentar en `.github/CODEOWNERS` las líneas de Carlos para `backend/` e `infra/`.
- [ ] Activar en `.github/dependabot.yml` las entradas `pip`, `npm` y `docker` cuando existan los manifiestos.

CI verificado en el repositorio nuevo, 11-11-2026.
