# feat/mapa-google — resultados de pruebas

Rama `feat/mapa-google`, 2026-11-03. **Sin clave real:** nunca se ha visto el mapa real de Google con marcadores. Hace falta una clave con facturación (`docs/credenciales-externas.md`).

## Totales

| Suite | Resultado | Cobertura |
|---|---|---|
| Web (Vitest) | 484 pruebas en verde | 94,6 % total; `MapaGoogle.tsx` 98,6 % |
| Estático | ESLint, `tsc`; `verificar-carga` ok | — |

## Casos de prueba

| Qué se probó | Esperado | Obtenido |
|---|---|---|
| Sin clave | Mapa esquemático; ningún script externo | OK (automática) |
| Build sin clave | El JavaScript no menciona a Google | OK: sin coincidencias en `dist/` |
| Con clave | Carga el script una vez, con la clave, en español y para Chile | OK (automática y en navegador, con doble) |
| Un marcador por conductor con posición | Etiqueta con patente, título con nombre, color por estado | OK (automática, con doble) |
| Posición nueva | Mueve el marcador, sin crear otro ni reencuadrar | OK (automática, con doble) |
| Conductor sale de turno | Pierde su marcador | OK (automática, con doble) |
| Clic en un marcador o elegir en la lista | Selecciona y lleva al conductor | OK (automática, con doble) |
| Script bloqueado por la red | Vuelve al esquemático con aviso | OK (automática y en navegador) |
| **Script real de Google con una clave sintética inválida** | Vuelve al esquemático con aviso | **OK: a los 330 ms** (en navegador) |

## Lo que falta

- En el navegador, el doble no mostró marcadores: esa prueba corrió en el puerto 5175, el WebSocket no conectó ahí y el mapa quedó en «Reconectando…». Los marcadores están probados con Vitest, no en un navegador.
- Con una clave real, comprobar el aspecto, las etiquetas sobre el círculo y el encuadre.
- Usa `google.maps.Marker`, marcado como obsoleto por Google pero disponible.

## Clave

Ninguna clave real se usó ni se versionó. `git grep` no encuentra claves con el formato de Google, `web/.env` está ignorado y `web/.env.example` la deja vacía. La única enviada fue la sintética `clave-sintetica`, al script público de Google, sin cuenta ni costo.

## Capturas

- `mapa-google-doble-escritorio.png`: con el doble de Google, no con el mapa real.
- `mapa-sin-google-celular.png`: script bloqueado.
- `mapa-clave-rechazada-escritorio.png`: clave rechazada por Google.
