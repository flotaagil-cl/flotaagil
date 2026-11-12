# Decisiones y estado a reflejar en los informes (12/11/2026)

Complementa `PENDIENTES_REVISION.md`. Leer ambos al retomar los informes.

## Estado real del código (corrige pendientes 2, 3 y 12)
- HU-31 a HU-44 **están en main** desde la migración. Sus issues (#36 a #51, salvo #41 y #43) están cerrados y en «Hecho» (plan-de-fusion.md, PR #65). Ya no corresponde decir "en revisión" ni "fusión pendiente".
- HU-45 (Mi perfil y eliminar cuenta) se adelantó al Sprint 4 por privacidad. Incluye la supresión de la cuenta con anonimización (DC-50) y la purga GPS a 30 días (DC-48). HU-46 a HU-49 quedan en la versión 1.1 (#52 a #56, sub-issues del #43).
- La anonimización (DC-50): telefono NULL, nombre «Pasajero eliminado», usuario inactivo con correo no utilizable, contenido de los mensajes vaciado. Viajes, pagos, historial y auditoría se conservan sin identificar a la persona. No se puede eliminar la cuenta con un viaje activo.
- Repositorio: flotaagil-cl/flotaagil (público), CI en verde, ruleset sin bypass, tablero con automatizaciones (Backlog, En revisión, Hecho, cierre automático).
- Cifras: correr `extraer_datos.py` (pruebas.json se actualiza al cerrar HU-45).
- Evidencias: `docs/estado-para-informe.md` tiene una fila por cada HU-31 a HU-44 (más HU-45) y las capturas están en docs/evidencias/HU-xx (script web/scripts/capturas.mjs).

## Cambios aprobados para después de la entrega (presentarlos como diseño, no construidos)
- **CC-19 · Chat interno y eliminación de WhatsApp (Twilio):**
  - Chat interno por WebSocket, en ambos sentidos: pasajero ↔ central (desde que pide hasta 24 h después del viaje), central ↔ conductor (todo el turno) y conductor ↔ pasajero (solo en EN_CAMINO y EN_ZONA; el conductor usa respuestas rápidas mientras maneja). La central responde como equipo y puede leer el chat conductor ↔ pasajero, con auditoría.
  - Verificación de la cuenta por correo (enlace de 24 h).
  - Avisos por notificación del navegador (Web Push) y por correo (Amazon SES), con una casilla para aceptar el correo de viajes. Los correos de la cuenta (activación y recuperación) se envían siempre.
  - Emergencias sin costo: botones «Llamar a la central» (tel:) y «Escribir a la central por WhatsApp» (wa.me, desde el WhatsApp propio del pasajero).
  - Se retira Twilio por completo: cambian HU-20, HU-21, HU-24, HU-30, RN-06 y RN-09; desaparece el riesgo de las plantillas de Meta; baja el costo variable (factibilidad económica).
  - Modelo: CONVERSACION y MENSAJE_CHAT; retención de 12 meses (RN-15); permisos por empresa (RN-13).
  - Riesgo aceptado: en iPhone, Web Push solo funciona con el portal agregado a la pantalla de inicio; si no, el aviso llega por correo.
- **CC-20 · Unificación visual del panel y la app** (sistema «Tiffany degradé»): versión 1.1.
- **CC-21 · Apariencia por empresa** (logo, nombre y colores): versión 1.1.
- **Llamadas internas (WebRTC):** evolución futura, sin CC todavía.
- **Biometría:** se descarta para el pasajero (desproporcionada). Para el conductor, una posible "selfie de turno" revisada por el despachador como evolución, sin datos biométricos.

## Plazo
- La entrega de los informes es el viernes 13/11/2026.
