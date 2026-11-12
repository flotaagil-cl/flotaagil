# HU vigentes: (id, épica, historia, criterios, prioridad, SP, sprint, estado_cambio)
HU = [
    ("HU-01", "Gestión y despacho", "Como administrador, quiero visualizar un panel con indicadores de reservas y vehículos activos, para conocer el estado de mi operación.",
     "Muestra reservas del día por estado y vehículos en línea/fuera de línea. Actualización por WebSocket sin recargar.", "Media", 5, "S4", "Sin cambios (reubicada a S4)"),
    ("HU-02", "Gestión y despacho", "Como despachador, quiero ver en un mapa la ubicación en tiempo real de los conductores conectados, para asignar servicios eficientemente.",
     "Mapa con marcadores móviles; al seleccionar uno muestra nombre, patente y estado. Latencia p95 < 5 s. Posiciones > 60 s se marcan como no confiables.", "Alta", 13, "S2", "Sin cambios"),
    ("HU-03", "Gestión y despacho", "Como despachador, quiero ingresar, editar y cancelar reservas, para mantener un registro único de solicitudes propias, del portal y de convenios.",
     "Formulario validado; edición antes del despacho; cancelación con motivo. Incluye sentido del trayecto (desde/hacia aeropuerto, urbano) y número de vuelo opcional.", "Alta", 8, "S1", "Modificada (sentido y vuelo)"),
    ("HU-04", "Gestión y despacho", "Como despachador, quiero recibir la sugerencia del conductor más apto al asignar una reserva urbana, confirmando siempre de forma manual.",
     "Ordena por distancia (PostGIS) y, ante diferencias < 1 km, por tiempo desde el último viaje. Desplegable con el resto de disponibles. Nunca asigna sin confirmación (RN-02). Para recogidas en aeropuerto delega en HU-29.", "Alta", 8, "S3", "Modificada (regla de sugerencia; 13→8 SP)"),
    ("HU-05", "Gestión y despacho", "Como despachador, quiero forzar el cierre o la anulación de un viaje en curso, para resolver casos en que el conductor pierde conexión.",
     "Botón en el panel; exige motivo; queda en AUDITORIA con el usuario responsable (RN-11).", "Alta", 5, "S4", "Sin cambios"),
    ("HU-06", "Gestión y despacho", "Como administrador, quiero generar reportes operativos (liquidación diaria por conductor, facturación por convenio, cancelaciones e historial), para controlar la recaudación y facturar.",
     "Filtros por fecha, conductor y convenio; desglose por método de pago; tasa de cancelación por origen; exportación CSV; totales del período.", "Media", 8, "S4", "Fusiona HU-06, 07, 08 y 09 (23→8 SP)"),
    ("HU-10", "Gestión y despacho", "Como administrador, quiero registrar y administrar conductores y vehículos, para mantener actualizada mi base de datos.",
     "CRUD de conductores con credenciales; CRUD de vehículos; asociación N:M conductor-vehículo; carga inicial por CSV.", "Alta", 8, "S1", "Modificada (carga CSV)"),
    ("HU-11", "Convenios", "Como administrador, quiero crear, editar y activar/desactivar convenios con link único y contraseña, para habilitar la reserva digital de clientes corporativos.",
     "Genera token aleatorio de 256 bits; define y rota la contraseña; desactivar no borra historial (RN-08); listado con volumen de reservas.", "Alta", 13, "S3", "Sin cambios"),
    ("HU-12", "Convenios", "Como administrador, quiero que quede registrado quién y cuándo modificó la contraseña o el estado de un convenio, para tener trazabilidad ante disputas.",
     "Registro de solo inserción con usuario, acción y fecha; consultable desde el panel (RN-12).", "Media", 5, "S4", "Sin cambios"),
    ("HU-13", "Operación en ruta", "Como conductor, quiero cambiar mi estado a Disponible o No Disponible indicando el vehículo que usaré, para operar con información correcta.",
     "Selector de vehículo si tiene más de uno (RN-05); exige consentimiento informado de ubicación al iniciar el turno; sincronización inmediata con el panel.", "Alta", 8, "S1", "Modificada (consentimiento GPS)"),
    ("HU-14", "Operación en ruta", "Como conductor, quiero recibir una notificación clara cuando se me asigne un viaje, viendo origen, destino, pasajero y tarifa.",
     "Alerta sonora y visual; muestra datos del viaje y, si aplica, número y ETA del vuelo.", "Alta", 8, "S2", "Modificada (datos de vuelo)"),
    ("HU-15", "Operación en ruta", "Como conductor, quiero contar con 60 segundos para aceptar o rechazar un viaje asignado, para que la central pueda reasignarlo si no respondo.",
     "Botones Aceptar/Rechazar; sin respuesta en 60 s o rechazo, la reserva vuelve a SOLICITADO (RN-04) y se registra en ASIGNACION.", "Alta", 8, "S2", "Sin cambios"),
    ("HU-16", "Operación en ruta", "Como conductor, quiero actualizar el estado del viaje y registrar método de pago y monto al finalizar, para respaldar la cuadratura.",
     "Botones secuenciales EN_CAMINO → PASAJERO_A_BORDO → FINALIZADO; EN_ZONA se marca automáticamente por geocerca de 150 m; pago y monto obligatorios (RN-10).", "Alta", 8, "S2", "Modificada (estado EN_ZONA)"),
    ("HU-17", "Operación en ruta", "Como conductor, quiero un botón que abra Google Maps o Waze con las coordenadas del viaje, para no digitar direcciones.",
     "Botón visible durante el viaje activo que abre la aplicación externa con coordenadas cargadas.", "Media", 3, "S1", "Sin cambios (reubicada a S1)"),
    ("HU-18", "Operación en ruta", "Como conductor, quiero ver los viajes completados en mi turno, para respaldar mis servicios.",
     "Pantalla Mi Turno con hora, origen, destino, monto y método de pago.", "Baja", 5, "S4", "Sin cambios"),
    ("HU-19", "Módulo pasajero", "Como pasajero, quiero solicitar un viaje desde un formulario web sin crear cuenta, indicando nombre, WhatsApp, origen, destino y vuelo si corresponde.",
     "Formulario público validado; aviso de privacidad y aceptación de avisos por WhatsApp; confirmación visual de solicitud recibida.", "Alta", 8, "S1", "Modificada (vuelo, aviso de privacidad)"),
    ("HU-20", "Módulo pasajero", "Como sistema, quiero verificar el número del pasajero por WhatsApp antes de confirmar la solicitud, para evitar reservas falsas.",
     "Plantilla con botón Confirmar/Cancelar; la reserva queda en PENDIENTE_CONFIRMACION y expira a los 15 minutos; máximo 3 envíos por número cada 15 minutos (RN-06).", "Alta", 5, "S1", "Modificada (SMS OTP → WhatsApp; 8→5 SP)"),
    ("HU-21", "Módulo pasajero", "Como pasajero, quiero recibir por WhatsApp los avisos de estado de mi viaje y poder cancelarlo respondiendo, para no llamar a la central.",
     "Avisos: confirmación, conductor asignado, en camino, «tu vehículo te espera» (EN_ZONA). Cancelación por respuesta solo sin conductor asignado (RN-09).", "Media", 5, "S2", "Modificada (SMS → WhatsApp; 8→5 SP)"),
    ("HU-24", "Módulo pasajero", "Como pasajero, quiero calificar el servicio de 1 a 5 al finalizar, para dejar retroalimentación.",
     "Encuesta por WhatsApp al finalizar; opcional (RN-14); asociada al conductor y visible en HU-06.", "Baja", 3, "S2", "Modificada (canal WhatsApp)"),
    ("HU-25", "Convenios", "Como supervisor de una empresa con convenio, quiero acceder a un link protegido con contraseña para solicitar viajes a nombre de mi empresa.",
     "El link pide contraseña y lleva al formulario; la reserva queda etiquetada con el convenio y omite la verificación (RN-07). Bloqueo tras 5 intentos fallidos.", "Alta", 13, "S4", "Sin cambios"),
    ("HU-26", "Aeropuerto", "Como despachador, quiero registrar el número de vuelo asociado a una reserva desde o hacia el aeropuerto, para que el sistema lo monitoree.",
     "Valida formato IATA; consulta inicial a la API de vuelos para confirmar que existe en la fecha; guarda hora programada.", "Alta", 5, "S1", "Nueva (CC-02)"),
    ("HU-27", "Aeropuerto", "Como despachador, quiero que el sistema monitoree el vuelo y proponga ajustar la hora de recogida, para no llegar ni antes ni después del pasajero.",
     "Consultas desde 3 h antes (cada 30 min; cada 10 min en la última hora); si la ETA cambia ≥ 15 min propone nueva hora (ETA + margen configurable) y el despachador la confirma.", "Alta", 8, "S3", "Nueva (CC-02)"),
    ("HU-28", "Aeropuerto", "Como despachador o administrador, quiero recibir alertas por demoras, cancelaciones o desvíos de vuelos, para reaccionar a tiempo.",
     "Alerta visual y sonora en el panel; registro de la alerta; marca la reserva afectada.", "Media", 5, "S3", "Nueva (CC-02)"),
    ("HU-29", "Aeropuerto", "Como despachador, quiero que los conductores que esperan en el aeropuerto formen una fila virtual por orden de llegada, para asignar los viajes desde el aeropuerto con justicia.",
     "Ingreso a la fila al entrar a la geocerca estando DISPONIBLE; salida tras 10 min fuera de la zona, al pasar a NO_DISPONIBLE o al ser asignado; el conductor ve su posición (RN-16).", "Alta", 8, "S3", "Nueva (CC-02)"),
    ("HU-30", "Módulo pasajero", "Como despachador, quiero atender desde el panel la conversación de WhatsApp de cada pasajero, para resolver dudas en el mismo hilo de su reserva.",
     "Bandeja de conversaciones por pasajero con la reserva vinculada; respuesta dentro de la ventana de 24 h; fuera de ella, solo plantillas aprobadas.", "Media", 5, "S4", "Nueva (reemplaza HU-22 y HU-23)"),
]
RETIRADAS = [
    ("HU-07", "Reporte de liquidación diaria", "Fusionada en HU-06", 8),
    ("HU-08", "Reporte mensual por convenio", "Fusionada en HU-06", 5),
    ("HU-09", "Tasa de cancelaciones", "Fusionada en HU-06", 5),
    ("HU-22", "Contacto con despachador vía wa.me", "Eliminada: reemplazada por HU-30", 3),
    ("HU-23", "Contacto directo con conductor vía wa.me", "Eliminada: el contacto pasa por el hilo de la central (HU-30); evita exponer el teléfono personal del conductor", 3),
]
# Historias incorporadas tras la EF2 (CC-12 y CC-15): no forman parte de los 178 SP de los cuatro sprints.
NUEVAS = [
    ("HU-31", "Gestión y despacho", "Como administrador, quiero cerrar la caja de cada turno comparando lo registrado por el sistema con lo que rinde el conductor, para dejar constancia de la diferencia y de quién la aprobó.",
     "Cada turno queda en TURNO con conductor, vehículo, inicio y término. Al cerrar, el panel muestra el efectivo registrado en el turno; el administrador ingresa el monto rendido; el sistema calcula la diferencia y exige una observación si no es cero (RN-19). El cierre queda en CIERRE_CAJA con responsable y fecha, y en AUDITORIA. Un turno se cierra una sola vez.",
     "Alta", 5, "S4", "Nueva (CC-12, observación de la EF2)"),
    ("HU-32", "Gestión y despacho", "Como despachador, quiero ingresar al sistema los viajes anotados en la planilla de contingencia cuando el servicio vuelve, para que el registro quede completo y cuadre con la caja.",
     "Formulario «Reserva de contingencia» con folio de la planilla, horas reales, conductor, estado final y pago. Queda con canal CONTINGENCIA, no envía avisos al pasajero y registra en AUDITORIA quién la ingresó y cuándo (RN-20). Rechaza folios repetidos. Reporte de conciliación por folio.",
     "Media", 3, "S4", "Nueva (CC-15, observación de la EF2)"),
]
RESP = {h: "Renato" for h in ["HU-01","HU-02","HU-11","HU-13","HU-14","HU-16","HU-17","HU-18","HU-19","HU-25","HU-28"]}
SPRINTS = {
    "S1": ("Semanas 8–9", "Base del sistema: modelo de datos, autenticación, flota, reservas, portal con verificación por WhatsApp y registro de vuelo."),
    "S2": ("Semanas 10–11", "Tiempo real y ciclo completo del conductor: mapa, asignación con 60 s, estados del viaje, cobro y avisos al pasajero."),
    "S3": ("Semanas 12–13", "Despacho asistido y aeropuerto: sugerencia por distancia y turno, fila virtual, monitoreo de vuelos y convenios."),
    "S4": ("Semanas 14–15", "Control y cierre: reportes, auditoría, acceso de convenios, chat del panel, cierre forzado y panel de indicadores."),
}

assert sum(h[5] for h in HU) == 178, sum(h[5] for h in HU)
if __name__ == "__main__":
    for s in SPRINTS:
        print(s, sum(h[5] for h in HU if h[6] == s))
