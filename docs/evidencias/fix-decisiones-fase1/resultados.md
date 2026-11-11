# Ajustes aprobados de la fase 1 — resultados

Rama `fix/decisiones-fase1` (encadenada desde `feat/HU-39-pedido`), 2026-11-11. Backend: `apps/reservas/tests/test_privacidad_cuenta.py` y `apps/portal/tests/test_pedido_tres_tipos.py`. Web: `src/paginas/acceso.test.tsx` y `src/pedido/pedido.test.tsx`. Datos sintéticos.

| Caso | Esperado | Obtenido |
|---|---|---|
| Crear cuenta sin la casilla | 400; no se crea | OK |
| Crear cuenta con la casilla | Fecha y versión del aviso en la cuenta (DC-44) | OK |
| Pedido | Sin aceptaciones: texto informativo; el PASAJERO lleva la aceptación de la cuenta | OK |
| Cuenta antigua | La sesión pide aceptar; no puede pedir (403) hasta aceptar una vez; queda en auditoría | OK |
| Versión nueva del aviso | Todas las cuentas aceptan otra vez | OK |
| Capacidad (DC-43 ajustada) | Máximo entre todos los vehículos; 4 sin vehículos | OK |
| Soporte | `SOPORTE_CORREO` vacío: sin enlace; con correo: «Soporte» en la barra y en el aviso del panel | OK |

## Pruebas que fallaron al cambiar el backend (49)

- Todas venían de datos de prueba sin el consentimiento: la fixture `con_cuenta` creaba la cuenta sin aceptación (403 `aceptar_privacidad`) y el alta por la API no enviaba la casilla (400 y fallas en cadena).
- Se arreglaron en un solo lugar: `CuentaPasajeroFactory` registra el consentimiento por defecto y `sin_consentimiento=True` crea una cuenta antigua (fixture `cuenta_antigua`).
- Las 3 de capacidad cambiaron por la regla ajustada (decisión del PO), no por un error.
- Ninguna mostró un error real.
