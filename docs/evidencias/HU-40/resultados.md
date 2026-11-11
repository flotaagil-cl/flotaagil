# HU-40 · Cuenta obligatoria para pedir (CC-18) — resultados

Rama `feat/HU-40-cuenta-obligatoria`, 2026-11-11. Backend: `apps/portal/tests/test_portal.py` y las pruebas reubicadas de vuelo y WhatsApp. Web: `src/portal/portal.test.tsx`. Datos sintéticos.

| Caso | Esperado | Obtenido |
|---|---|---|
| `POST /api/portal/{slug}/solicitudes/` | 404: el pedido como invitado ya no existe | OK |
| Pedido web sin sesión | 401 | OK |
| Pedido con cuenta | SOLICITADO, sin verificación por reserva, sin declaración de convenio | OK |
| Anticipación, vuelo, recogida (RN-17) y límite por teléfono | Mismas reglas, ahora probadas en `/api/mi-cuenta/solicitudes/` | OK |
| `/solicitar/:slug` | Lleva a `/login?empresa=<slug>` | OK |
| Formulario del viaje | Sigue probado (lo usan la cuenta y el convenio), con un arnés de prueba | OK |
| `datos_demo` | Sin `--pendientes` | OK |

## Límites conocidos

- Las reservas en PENDIENTE_CONFIRMACION anteriores siguen expirando; la carga demo de reservas conserva algunas en ese estado para el panel.
- `CLAUDE.md` todavía describe al pasajero «sin cuenta»: se actualiza al fusionar (DC-41).
