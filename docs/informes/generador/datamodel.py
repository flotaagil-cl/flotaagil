"""Modelo lógico: fuente única para el diagrama (graphviz) y el diccionario de datos (anexo)."""

# (campo, tipo, nulo, clave, descripción, restricciones/dominio, defecto, sensible)
E = {}

E["EMPRESA"] = ("Organización propietaria de la flota que opera la plataforma (inquilino).", [
    ("id", "BIGINT", "No", "PK", "Identificador de la empresa", "Autoincremental", "—", ""),
    ("rut", "VARCHAR(12)", "No", "UK", "RUT de la empresa", "Formato 12345678-9; dígito verificador válido", "—", ""),
    ("razon_social", "VARCHAR(120)", "No", "", "Razón social", "Texto no vacío", "—", ""),
    ("slug", "VARCHAR(50)", "No", "UK", "Identificador en la URL del portal (DC-01)", "kebab-case; único", "—", ""),
    ("plan", "VARCHAR(12)", "No", "", "Plan de servicio contratado", "INICIAL | ESTANDAR | AVANZADO (CC-13; reemplaza BASICO | FLOTA_PLUS al implementar el modelo comercial)", "INICIAL", ""),
    ("activa", "BOOLEAN", "No", "", "Indica si la empresa opera", "true/false", "true", ""),
    ("creado_en", "TIMESTAMPTZ", "No", "", "Fecha de alta", "UTC", "now()", ""),
])
E["CONFIGURACION_EMPRESA"] = ("Parámetros de operación configurables por empresa (DC-02); relación 1:1 con EMPRESA.", [
    ("empresa_id", "BIGINT", "No", "PK, FK", "Empresa", "→ EMPRESA.id (1:1)", "—", ""),
    ("margen_nacional_min", "SMALLINT", "No", "", "Margen sobre la ETA, vuelos nacionales (RN-17)", "≥ 0", "20", ""),
    ("margen_internacional_min", "SMALLINT", "No", "", "Margen sobre la ETA, vuelos internacionales (RN-17)", "≥ 0", "35", ""),
    ("tolerancia_fila_min", "SMALLINT", "No", "", "Tiempo fuera de la geocerca antes de salir de la fila (RN-16)", "≥ 0", "10", ""),
    ("espera_no_presentacion_min", "SMALLINT", "No", "", "Espera en EN_ZONA antes de cancelar por no presentación", "≥ 0", "15", ""),
    ("expiracion_verificacion_min", "SMALLINT", "No", "", "Expiración de PENDIENTE_CONFIRMACION (RN-06)", "≥ 1", "15", ""),
    ("anticipacion_minima_min", "SMALLINT", "No", "", "Anticipación mínima de una solicitud del portal (DC-10)", "≥ 0", "30", ""),
    ("precision_geocerca_m", "SMALLINT", "No", "", "Precisión máxima de una posición para marcar EN_ZONA (DC-16)", "> 0", "50", ""),
    ("encuesta_vigencia_horas", "SMALLINT", "No", "", "Horas en que un número suelto cuenta como calificación (DC-19)", "> 0", "24", ""),
    ("consulta_vuelo_desde_min", "SMALLINT", "No", "", "Anticipación con que empieza el monitoreo del vuelo (DC-22)", "> 0", "180", ""),
    ("consulta_vuelo_cada_min", "SMALLINT", "No", "", "Frecuencia de consulta del vuelo (DC-22)", "> 0", "30", ""),
    ("consulta_vuelo_final_cada_min", "SMALLINT", "No", "", "Frecuencia de consulta en la ventana final (DC-22)", "> 0", "10", ""),
    ("consulta_vuelo_final_ventana_min", "SMALLINT", "No", "", "Duración de la ventana final antes de la llegada (DC-22)", "> 0", "60", ""),
    ("cambio_eta_min", "SMALLINT", "No", "", "Cambio mínimo de la ETA que genera una propuesta de recogida (DC-22)", "> 0", "15", ""),
    ("zona_lat_min … zona_lon_max", "NUMERIC(9,6) × 4", "No", "", "Rectángulo de la zona de operación", "Mínimo < máximo", "RM aproximada", ""),
])
E["USUARIO"] = ("Persona con acceso autenticado al sistema, diferenciada por rol.", [
    ("id", "BIGINT", "No", "PK", "Identificador del usuario", "Autoincremental", "—", ""),
    ("empresa_id", "BIGINT", "No", "FK", "Empresa a la que pertenece", "→ EMPRESA.id", "—", ""),
    ("nombre", "VARCHAR(80)", "No", "", "Nombre completo", "Texto no vacío", "—", "Personal"),
    ("email", "VARCHAR(120)", "No", "UK", "Correo de acceso", "Formato correo; único", "—", "Personal"),
    ("password_hash", "VARCHAR(128)", "No", "", "Hash de la contraseña", "PBKDF2-SHA256 con salt", "—", "Credencial"),
    ("rol", "VARCHAR(14)", "No", "", "Rol de acceso", "ADMINISTRADOR | DESPACHADOR | CONDUCTOR", "—", ""),
    ("activo", "BOOLEAN", "No", "", "Cuenta habilitada", "true/false", "true", ""),
    ("intentos_fallidos", "SMALLINT", "No", "", "Intentos fallidos consecutivos", "0–5; bloqueo al llegar a 5", "0", ""),
    ("bloqueado_hasta", "TIMESTAMPTZ", "Sí", "", "Fin del bloqueo temporal", "UTC; 15 min configurables (DC-07)", "NULL", ""),
    ("debe_cambiar_password", "BOOLEAN", "No", "", "Tiene una contraseña temporal que debe cambiar (DC-14)", "true/false; con true la API responde 403 salvo cambio de contraseña y logout", "false", ""),
    ("password_temporal_vence", "TIMESTAMPTZ", "Sí", "", "Vencimiento de la contraseña temporal (DC-14)", "UTC; 72 h desde que se genera", "NULL", ""),
])
E["CONDUCTOR"] = ("Datos operativos del usuario con rol conductor.", [
    ("id", "BIGINT", "No", "PK", "Identificador del conductor", "Autoincremental", "—", ""),
    ("usuario_id", "BIGINT", "No", "FK, UK", "Cuenta de acceso asociada", "→ USUARIO.id (1:1)", "—", ""),
    ("rut", "VARCHAR(12)", "No", "UK", "RUT del conductor", "Dígito verificador válido", "—", "Personal"),
    ("telefono", "VARCHAR(16)", "No", "", "Teléfono de contacto", "E.164 (+569XXXXXXXX)", "—", "Personal"),
    ("licencia_clase", "VARCHAR(4)", "No", "", "Clase de licencia", "A1 | A2 | A3", "—", ""),
    ("licencia_vence", "DATE", "No", "", "Vencimiento de la licencia", "Fecha futura al alta", "—", ""),
    ("estado", "VARCHAR(14)", "No", "", "Estado operativo", "DISPONIBLE | NO_DISPONIBLE | EN_VIAJE", "NO_DISPONIBLE", ""),
    ("vehiculo_activo_id", "BIGINT", "Sí", "FK", "Vehículo declarado para el turno", "→ VEHICULO.id; obligatorio si DISPONIBLE (RN-05)", "NULL", ""),
    ("consentimiento_gps_en", "TIMESTAMPTZ", "Sí", "", "Aceptación informada del tratamiento de ubicación", "Requerido para iniciar turno", "NULL", ""),
    ("turno_inicio, turno_fin", "TIMESTAMPTZ × 2", "Sí", "", "Inicio y término del último turno (DC-26)", "Transitorio: implementado en HU-18; se migra a TURNO, que conserva el historial (CC-12)", "NULL", ""),
])
E["TURNO"] = ("Jornada de un conductor con un vehículo, desde «Empezar turno» hasta «Terminar turno» (CC-12). Conserva el historial que CONDUCTOR.estado sobrescribe.", [
    ("id", "BIGINT", "No", "PK", "Identificador del turno", "Autoincremental", "—", ""),
    ("conductor_id", "BIGINT", "No", "FK", "Conductor que trabaja el turno", "→ CONDUCTOR.id; a lo más un turno abierto por conductor (índice único parcial con hora_termino IS NULL)", "—", ""),
    ("vehiculo_id", "BIGINT", "No", "FK", "Vehículo declarado para el turno (RN-05)", "→ VEHICULO.id", "—", ""),
    ("hora_inicio", "TIMESTAMPTZ", "No", "", "Momento en que el conductor empieza el turno", "UTC", "now()", ""),
    ("hora_termino", "TIMESTAMPTZ", "Sí", "", "Momento en que termina el turno", "UTC; ≥ hora_inicio; NULL mientras está en curso", "NULL", ""),
    ("motivo_termino", "VARCHAR(20)", "Sí", "", "Cómo terminó el turno", "CONDUCTOR | CUENTA_DESHABILITADA | CIERRE_ADMINISTRATIVO; obligatorio si hay hora_termino", "NULL", ""),
])
E["CIERRE_CAJA"] = ("Cuadratura de la caja de un turno: lo registrado por el sistema frente a lo rendido por el conductor (CC-12, proceso P3.2).", [
    ("id", "BIGINT", "No", "PK", "Identificador del cierre", "Autoincremental", "—", ""),
    ("turno_id", "BIGINT", "No", "FK, UK", "Turno que se cuadra", "→ TURNO.id (1:0..1); solo turnos terminados", "—", ""),
    ("monto_registrado", "INTEGER", "No", "", "Efectivo registrado por el sistema en el turno (CLP)", "≥ 0; suma de PAGO_VIAJE con método EFECTIVO de los viajes del turno, fijada al cerrar", "—", ""),
    ("monto_rendido", "INTEGER", "No", "", "Efectivo que entrega el conductor (CLP)", "≥ 0", "—", ""),
    ("diferencia", "INTEGER", "No", "", "Diferencia de la cuadratura (CLP)", "= monto_rendido − monto_registrado; negativo = faltante, positivo = sobrante", "—", ""),
    ("observacion", "VARCHAR(200)", "Sí", "", "Explicación de la diferencia", "Obligatoria si diferencia ≠ 0 (RN-19)", "NULL", ""),
    ("responsable_id", "BIGINT", "No", "FK", "Usuario que realiza el cuadre", "→ USUARIO.id; rol ADMINISTRADOR", "—", ""),
    ("fecha_cierre", "TIMESTAMPTZ", "No", "", "Momento del cierre", "UTC; ≥ TURNO.hora_termino", "now()", ""),
])
E["VEHICULO"] = ("Móvil de la flota habilitado para el servicio.", [
    ("id", "BIGINT", "No", "PK", "Identificador del vehículo", "Autoincremental", "—", ""),
    ("empresa_id", "BIGINT", "No", "FK", "Empresa propietaria", "→ EMPRESA.id", "—", ""),
    ("patente", "VARCHAR(8)", "No", "UK", "Placa patente", "Formato chileno (AB1234 o ABCD12)", "—", ""),
    ("marca_modelo", "VARCHAR(60)", "No", "", "Marca y modelo", "Texto no vacío", "—", ""),
    ("anio", "SMALLINT", "No", "", "Año de fabricación", "≥ año actual − 12 (antigüedad máx. del servicio)", "—", ""),
    ("capacidad", "SMALLINT", "No", "", "Número de pasajeros", "1–7", "4", ""),
    ("activo", "BOOLEAN", "No", "", "Vehículo habilitado", "true/false", "true", ""),
])
E["CONDUCTOR_VEHICULO"] = ("Resuelve la relación N:M entre conductores y vehículos.", [
    ("conductor_id", "BIGINT", "No", "PK, FK", "Conductor", "→ CONDUCTOR.id", "—", ""),
    ("vehiculo_id", "BIGINT", "No", "PK, FK", "Vehículo", "→ VEHICULO.id", "—", ""),
    ("desde", "DATE", "No", "", "Inicio de la asociación", "—", "current_date", ""),
])
E["CONVENIO"] = ("Acuerdo comercial con una empresa cliente que habilita reservas corporativas.", [
    ("id", "BIGINT", "No", "PK", "Identificador del convenio", "Autoincremental", "—", ""),
    ("empresa_id", "BIGINT", "No", "FK", "Empresa de taxi que otorga el convenio", "→ EMPRESA.id", "—", ""),
    ("cliente_nombre", "VARCHAR(120)", "No", "", "Nombre de la empresa cliente", "Texto no vacío", "—", ""),
    ("cliente_rut", "VARCHAR(12)", "No", "", "RUT de la empresa cliente", "Dígito verificador válido", "—", ""),
    ("token_link", "CHAR(43)", "No", "UK", "Token del link único", "Aleatorio de 256 bits (base64url)", "—", "Credencial"),
    ("password_hash", "VARCHAR(128)", "No", "", "Hash de la contraseña del convenio", "PBKDF2-SHA256", "—", "Credencial"),
    ("activo", "BOOLEAN", "No", "", "Vigencia del convenio", "false invalida el link (RN-08)", "true", ""),
    ("intentos_fallidos", "SMALLINT", "No", "", "Intentos fallidos consecutivos en el link (DC-27)", "0–5; bloqueo al llegar a 5", "0", ""),
    ("bloqueado_hasta", "TIMESTAMPTZ", "Sí", "", "Fin del bloqueo del link (DC-27)", "UTC; 15 min configurables; rotar la contraseña lo levanta", "NULL", ""),
])
E["PASAJERO"] = ("Solicitante del traslado, particular o beneficiario de un convenio.", [
    ("id", "BIGINT", "No", "PK", "Identificador del pasajero", "Autoincremental", "—", ""),
    ("empresa_id", "BIGINT", "No", "FK", "Empresa que lo atiende", "→ EMPRESA.id", "—", ""),
    ("nombre", "VARCHAR(80)", "No", "", "Nombre declarado", "Texto no vacío", "—", "Personal"),
    ("telefono", "VARCHAR(16)", "No", "UK (empresa)", "Número de WhatsApp", "E.164; único por empresa", "—", "Personal"),
    ("verificado_en", "TIMESTAMPTZ", "Sí", "", "Fecha de verificación por WhatsApp", "UTC", "NULL", ""),
    ("opt_in_en", "TIMESTAMPTZ", "Sí", "", "Aceptación de avisos por WhatsApp", "Requerido antes de enviar plantillas", "NULL", ""),
    ("privacidad_aceptada_en", "TIMESTAMPTZ", "Sí", "", "Aceptación del aviso de privacidad (DC-11)", "UTC", "NULL", ""),
])
E["VIAJE"] = ("Unidad central del negocio: un traslado desde su solicitud hasta su cierre.", [
    ("id", "BIGINT", "No", "PK", "Identificador del viaje", "Autoincremental", "—", ""),
    ("empresa_id", "BIGINT", "No", "FK", "Empresa", "→ EMPRESA.id", "—", ""),
    ("pasajero_id", "BIGINT", "No", "FK", "Pasajero", "→ PASAJERO.id", "—", ""),
    ("convenio_id", "BIGINT", "Sí", "FK", "Convenio, si es corporativo", "→ CONVENIO.id", "NULL", ""),
    ("conductor_id", "BIGINT", "Sí", "FK", "Conductor asignado", "→ CONDUCTOR.id", "NULL", ""),
    ("vehiculo_id", "BIGINT", "Sí", "FK", "Vehículo usado", "→ VEHICULO.id", "NULL", ""),
    ("canal", "VARCHAR(12)", "No", "", "Canal de ingreso", "WEB | WHATSAPP | TELEFONO | CONVENIO | CONTINGENCIA (CC-15: reserva ingresada después de una caída)", "—", ""),
    ("sentido", "VARCHAR(16)", "No", "", "Tipo de trayecto", "DESDE_AEROPUERTO | HACIA_AEROPUERTO | URBANO", "URBANO", ""),
    ("origen_dir", "VARCHAR(200)", "No", "", "Dirección de recogida", "Texto no vacío", "—", "Personal"),
    ("origen_geo", "GEOGRAPHY(Point,4326)", "No", "", "Coordenadas de recogida", "Dentro de la RM", "—", "Ubicación"),
    ("destino_dir", "VARCHAR(200)", "No", "", "Dirección de destino", "Texto no vacío", "—", "Personal"),
    ("destino_geo", "GEOGRAPHY(Point,4326)", "No", "", "Coordenadas de destino", "—", "—", "Ubicación"),
    ("recogida_en", "TIMESTAMPTZ", "No", "", "Hora de recogida vigente", "Ajustable por P2.2", "—", ""),
    ("estado", "VARCHAR(22)", "No", "", "Estado del viaje (Anexo H; largo según DC-09)", "Ver máquina de estados", "PENDIENTE_CONFIRMACION", ""),
    ("tarifa", "INTEGER", "Sí", "", "Tarifa acordada (CLP)", "≥ 0; definida por el cliente", "NULL", ""),
    ("motivo_cancelacion", "VARCHAR(200)", "Sí", "", "Motivo de cancelación", "Obligatorio si CANCELADO", "NULL", ""),
    ("origen_cancelacion", "VARCHAR(14)", "Sí", "", "Quién canceló", "PASAJERO | DESPACHADOR | ADMINISTRADOR | SUPERVISOR | SISTEMA (DC-08)", "NULL", ""),
    ("autorizacion_avisos_en", "TIMESTAMPTZ", "Sí", "", "Momento en que el supervisor del convenio declaró que el pasajero autorizó los avisos (DC-27)", "UTC; solo reservas por link de convenio", "NULL", ""),
    ("autorizacion_avisos_supervisor", "VARCHAR(80)", "Sí", "", "Nombre que escribió el supervisor al declarar (DC-27)", "Texto; el supervisor no tiene cuenta", "NULL", "Personal"),
    ("folio_contingencia", "VARCHAR(12)", "Sí", "UK (empresa)", "Folio de la planilla de contingencia (CC-15)", "Obligatorio y único por empresa si canal = CONTINGENCIA", "NULL", ""),
    ("creado_en", "TIMESTAMPTZ", "No", "", "Fecha de ingreso al sistema", "UTC; en una reserva de contingencia es posterior a recogida_en", "now()", ""),
])
E["VUELO"] = ("Vuelo asociado a un viaje desde o hacia el aeropuerto.", [
    ("id", "BIGINT", "No", "PK", "Identificador", "Autoincremental", "—", ""),
    ("viaje_id", "BIGINT", "No", "FK, UK", "Viaje asociado", "→ VIAJE.id (1:0..1)", "—", ""),
    ("numero", "VARCHAR(8)", "No", "", "Código IATA del vuelo", "Formato LA123 / H2 456", "—", ""),
    ("fecha", "DATE", "No", "", "Fecha programada", "—", "—", ""),
    ("hora_programada", "TIMESTAMPTZ", "No", "", "Hora programada de llegada", "UTC", "—", ""),
    ("hora_estimada", "TIMESTAMPTZ", "Sí", "", "Última ETA informada", "UTC", "NULL", ""),
    ("estado_vuelo", "VARCHAR(12)", "No", "", "Estado informado", "PROGRAMADO | DEMORADO | ATERRIZADO | CANCELADO | DESVIADO", "PROGRAMADO", ""),
    ("ultima_consulta_en", "TIMESTAMPTZ", "Sí", "", "Última consulta a la API", "UTC", "NULL", ""),
    ("origen_icao", "VARCHAR(4)", "Sí", "", "Código ICAO del aeropuerto de origen (DC-22)", "Nacional si empieza con SC; sin dato se usa el margen nacional", "NULL", ""),
    ("eta_referencia", "TIMESTAMPTZ", "Sí", "", "ETA con la que se calculó la última propuesta (DC-22)", "UTC", "NULL", ""),
    ("recogida_propuesta", "TIMESTAMPTZ", "Sí", "", "Hora de recogida propuesta, pendiente de confirmar (DC-22, RN-02)", "= ETA + margen (RN-17)", "NULL", ""),
    ("propuesta_en", "TIMESTAMPTZ", "Sí", "", "Momento en que se generó la propuesta (DC-22)", "UTC", "NULL", ""),
])
E["ALERTA_VUELO"] = ("Alertas de demora, cancelación o desvío de un vuelo y su atención (DC-23).", [
    ("id", "BIGINT", "No", "PK", "Identificador", "Autoincremental", "—", ""),
    ("empresa_id", "BIGINT", "No", "FK", "Empresa", "→ EMPRESA.id", "—", ""),
    ("viaje_id", "BIGINT", "No", "FK", "Reserva afectada", "→ VIAJE.id", "—", ""),
    ("numero_vuelo", "VARCHAR(8)", "No", "", "Vuelo que originó la alerta", "Se conserva aunque se edite el vuelo", "—", ""),
    ("tipo", "VARCHAR(16)", "No", "", "Tipo de alerta", "ETA_CAMBIADA | VUELO_CANCELADO | VUELO_DESVIADO | SIN_DATOS", "—", ""),
    ("detalle", "VARCHAR(200)", "No", "", "Texto que ve el despachador", "Texto no vacío", "—", ""),
    ("eta", "TIMESTAMPTZ", "Sí", "", "ETA informada al generar la alerta", "UTC", "NULL", ""),
    ("creada_en", "TIMESTAMPTZ", "No", "", "Momento de la alerta", "UTC", "now()", ""),
    ("atendida_en", "TIMESTAMPTZ", "Sí", "", "Momento en que se atendió", "NULL mientras la reserva sigue marcada", "NULL", ""),
    ("atendida_por", "BIGINT", "Sí", "FK", "Usuario que la atendió", "→ USUARIO.id; NULL si la resolvió el sistema", "NULL", ""),
])
E["ASIGNACION"] = ("Cada intento de asignación con su respuesta, base del KPI de rechazo.", [
    ("id", "BIGINT", "No", "PK", "Identificador", "Autoincremental", "—", ""),
    ("viaje_id", "BIGINT", "No", "FK", "Viaje", "→ VIAJE.id", "—", ""),
    ("conductor_id", "BIGINT", "No", "FK", "Conductor notificado", "→ CONDUCTOR.id", "—", ""),
    ("despachador_id", "BIGINT", "No", "FK", "Usuario que confirmó", "→ USUARIO.id (RN-02)", "—", ""),
    ("origen_sugerencia", "VARCHAR(10)", "No", "", "Fuente del candidato", "FILA | DISTANCIA | MANUAL", "—", ""),
    ("enviada_en", "TIMESTAMPTZ", "No", "", "Envío de la notificación", "UTC", "now()", ""),
    ("respondida_en", "TIMESTAMPTZ", "Sí", "", "Respuesta del conductor", "≤ enviada_en + 60 s", "NULL", ""),
    ("resultado", "VARCHAR(10)", "Sí", "", "Resultado", "ACEPTADA | RECHAZADA | EXPIRADA", "NULL", ""),
])
E["HISTORIAL_ESTADO"] = ("Registro de solo inserción de cada transición del viaje.", [
    ("id", "BIGINT", "No", "PK", "Identificador", "Autoincremental", "—", ""),
    ("viaje_id", "BIGINT", "No", "FK", "Viaje", "→ VIAJE.id", "—", ""),
    ("estado_anterior", "VARCHAR(22)", "Sí", "", "Estado previo", "Dominio de VIAJE.estado", "NULL", ""),
    ("estado_nuevo", "VARCHAR(22)", "No", "", "Estado resultante", "Transición válida (Anexo H)", "—", ""),
    ("actor", "VARCHAR(14)", "No", "", "Tipo de actor", "CONDUCTOR | DESPACHADOR | ADMINISTRADOR | PASAJERO | SISTEMA (DC-03); EN_ZONA admite CONDUCTOR (DC-17)", "—", ""),
    ("usuario_id", "BIGINT", "Sí", "FK", "Usuario responsable", "→ USUARIO.id", "NULL", ""),
    ("manual", "BOOLEAN", "No", "", "Llegada indicada por el conductor sin geocerca (DC-20)", "true/false", "false", ""),
    ("distancia_m", "INTEGER", "Sí", "", "Metros entre el origen y la última posición del conductor (DC-20)", "≥ 0; NULL si no envió posiciones", "NULL", ""),
    ("creado_en", "TIMESTAMPTZ", "No", "", "Momento de la transición", "UTC", "now()", ""),
])
E["PAGO_VIAJE"] = ("Registro del cobro de un viaje finalizado.", [
    ("id", "BIGINT", "No", "PK", "Identificador", "Autoincremental", "—", ""),
    ("viaje_id", "BIGINT", "No", "FK, UK", "Viaje cobrado", "→ VIAJE.id (1:0..1)", "—", ""),
    ("metodo", "VARCHAR(14)", "No", "", "Método de pago", "EFECTIVO | TARJETA | TRANSFERENCIA | CONVENIO", "—", ""),
    ("monto", "INTEGER", "No", "", "Monto cobrado (CLP)", "0–500.000", "—", ""),
    ("registrado_en", "TIMESTAMPTZ", "No", "", "Momento del registro", "UTC", "now()", ""),
    ("corregido_por", "BIGINT", "Sí", "FK", "Administrador que corrigió", "→ USUARIO.id; genera AUDITORIA", "NULL", ""),
])
E["CALIFICACION"] = ("Evaluación opcional del servicio por el pasajero (RN-14).", [
    ("id", "BIGINT", "No", "PK", "Identificador", "Autoincremental", "—", ""),
    ("viaje_id", "BIGINT", "No", "FK, UK", "Viaje calificado", "→ VIAJE.id", "—", ""),
    ("puntaje", "SMALLINT", "No", "", "Nota del servicio", "1–5", "—", ""),
    ("creado_en", "TIMESTAMPTZ", "No", "", "Fecha", "UTC", "now()", ""),
])
E["GEOCERCA"] = ("Polígono que delimita una zona operativa, como el aeropuerto.", [
    ("id", "BIGINT", "No", "PK", "Identificador", "Autoincremental", "—", ""),
    ("empresa_id", "BIGINT", "No", "FK", "Empresa", "→ EMPRESA.id", "—", ""),
    ("nombre", "VARCHAR(60)", "No", "", "Nombre de la zona", "Texto no vacío", "—", ""),
    ("poligono", "GEOGRAPHY(Polygon,4326)", "No", "", "Límite geográfico", "Polígono válido (ST_IsValid)", "—", ""),
])
E["FILA_AEROPUERTO"] = ("Turnos de la fila virtual: ingreso, posición y salida de cada conductor.", [
    ("id", "BIGINT", "No", "PK", "Identificador", "Autoincremental", "—", ""),
    ("geocerca_id", "BIGINT", "No", "FK", "Zona de la fila", "→ GEOCERCA.id", "—", ""),
    ("conductor_id", "BIGINT", "No", "FK", "Conductor en la fila", "→ CONDUCTOR.id; una entrada abierta por conductor", "—", ""),
    ("ingreso_en", "TIMESTAMPTZ", "No", "", "Ingreso a la geocerca", "Define el orden FIFO (RN-16)", "now()", ""),
    ("salida_en", "TIMESTAMPTZ", "Sí", "", "Salida de la fila", "NULL mientras está en la fila", "NULL", ""),
    ("motivo_salida", "VARCHAR(14)", "Sí", "", "Motivo de salida", "ASIGNADO | FUERA_ZONA | NO_DISPONIBLE", "NULL", ""),
])
E["POSICION_GPS"] = ("Ubicaciones enviadas por la app durante el turno (RNF-09).", [
    ("id", "BIGINT", "No", "PK", "Identificador", "Secuencia", "—", ""),
    ("conductor_id", "BIGINT", "No", "FK", "Conductor emisor", "→ CONDUCTOR.id", "—", ""),
    ("viaje_id", "BIGINT", "Sí", "FK", "Viaje en curso, si existe", "→ VIAJE.id", "NULL", ""),
    ("punto", "GEOGRAPHY(Point,4326)", "No", "", "Posición", "Índice GiST", "—", "Ubicación"),
    ("precision_m", "SMALLINT", "Sí", "", "Precisión informada (m)", "0–500; > 100 se marca no confiable", "NULL", ""),
    ("registrada_en", "TIMESTAMPTZ", "No", "UK (conductor)", "Momento de captura", "Retención 30 días; único por conductor e instante (DC-15)", "—", ""),
])
E["MENSAJE_WHATSAPP"] = ("Mensajes entrantes y salientes del canal WhatsApp, incluido el chat del panel.", [
    ("id", "BIGINT", "No", "PK", "Identificador", "Autoincremental", "—", ""),
    ("pasajero_id", "BIGINT", "No", "FK", "Interlocutor", "→ PASAJERO.id", "—", ""),
    ("viaje_id", "BIGINT", "Sí", "FK", "Viaje relacionado", "→ VIAJE.id", "NULL", ""),
    ("direccion", "VARCHAR(8)", "No", "", "Sentido", "ENTRANTE | SALIENTE", "—", ""),
    ("tipo", "VARCHAR(10)", "No", "", "Tipo de mensaje", "PLANTILLA | SESION", "—", ""),
    ("cuerpo", "TEXT", "No", "", "Contenido", "≤ 1.024 caracteres", "—", "Personal"),
    ("proveedor_sid", "VARCHAR(40)", "Sí", "UK", "Identificador en Twilio", "Idempotencia de webhooks", "NULL", ""),
    ("estado_entrega", "VARCHAR(12)", "No", "", "Estado de entrega", "QUEUED | SENT | DELIVERED | READ | FAILED", "QUEUED", ""),
    ("usuario_id", "BIGINT", "Sí", "FK", "Despachador que respondió", "→ USUARIO.id", "NULL", ""),
    ("creado_en", "TIMESTAMPTZ", "No", "", "Fecha", "UTC", "now()", ""),
])
E["AUDITORIA"] = ("Registro inmutable (solo inserción) de acciones sensibles.", [
    ("id", "BIGINT", "No", "PK", "Identificador", "Autoincremental", "—", ""),
    ("empresa_id", "BIGINT", "No", "FK", "Empresa", "→ EMPRESA.id", "—", ""),
    ("usuario_id", "BIGINT", "Sí", "FK", "Usuario que actuó", "→ USUARIO.id; NULL solo en eventos sin usuario autenticado, como BLOQUEO_LINK (DC-27)", "NULL", ""),
    ("entidad", "VARCHAR(30)", "No", "", "Entidad afectada", "CONVENIO | VIAJE | PAGO_VIAJE | USUARIO | VEHICULO | CONDUCTOR (DC-13) | CIERRE_CAJA (CC-12)", "—", ""),
    ("entidad_id", "BIGINT", "No", "", "Registro afectado", "—", "—", ""),
    ("accion", "VARCHAR(30)", "No", "", "Acción realizada", "Ej.: CAMBIAR_PASSWORD, CIERRE_FORZADO, ANULACION_FORZADA (DC-25), AJUSTE_RECOGIDA, BLOQUEO_LINK, DESBLOQUEO_LINK (DC-27), CIERRE_CAJA, RESERVA_CONTINGENCIA", "—", ""),
    ("motivo", "VARCHAR(200)", "Sí", "", "Motivo declarado", "Obligatorio en cierres forzados (RN-11)", "NULL", ""),
    ("datos_previos", "JSONB", "Sí", "", "Valores anteriores", "Sin contraseñas ni hashes", "NULL", ""),
    ("creado_en", "TIMESTAMPTZ", "No", "", "Fecha", "UTC", "now()", ""),
])

# relaciones: (padre, hijo, cardinalidad hijo, obligatoria_en_hijo)
REL = [
    ("EMPRESA", "CONFIGURACION_EMPRESA", "1:1"), ("EMPRESA", "USUARIO", "1:N"), ("EMPRESA", "VEHICULO", "1:N"), ("EMPRESA", "CONVENIO", "1:N"),
    ("EMPRESA", "PASAJERO", "1:N"), ("EMPRESA", "GEOCERCA", "1:N"),
    ("USUARIO", "CONDUCTOR", "1:0..1"),
    ("CONDUCTOR", "CONDUCTOR_VEHICULO", "1:N"), ("VEHICULO", "CONDUCTOR_VEHICULO", "1:N"),
    ("PASAJERO", "VIAJE", "1:N"), ("CONVENIO", "VIAJE", "0..1:N"), ("CONDUCTOR", "VIAJE", "0..1:N"),
    ("VIAJE", "VUELO", "1:0..1"), ("VIAJE", "ALERTA_VUELO", "1:N"), ("EMPRESA", "ALERTA_VUELO", "1:N"), ("VIAJE", "ASIGNACION", "1:N"), ("CONDUCTOR", "ASIGNACION", "1:N"),
    ("VIAJE", "HISTORIAL_ESTADO", "1:N"), ("VIAJE", "PAGO_VIAJE", "1:0..1"), ("VIAJE", "CALIFICACION", "1:0..1"),
    ("GEOCERCA", "FILA_AEROPUERTO", "1:N"), ("CONDUCTOR", "FILA_AEROPUERTO", "1:N"),
    ("CONDUCTOR", "POSICION_GPS", "1:N"), ("PASAJERO", "MENSAJE_WHATSAPP", "1:N"),
    ("VIAJE", "MENSAJE_WHATSAPP", "0..1:N"), ("USUARIO", "AUDITORIA", "0..1:N"),
    ("CONDUCTOR", "TURNO", "1:N"), ("VEHICULO", "TURNO", "1:N"), ("TURNO", "CIERRE_CAJA", "1:0..1"), ("USUARIO", "CIERRE_CAJA", "1:N"),
]

# ---------------------------------------------------------------- semana 14: CC-16, CC-17 y CC-18 (DC-34 a DC-46)
def _set(ent, cols_out=(), add=(), after=None, replace=None):
    desc, cols = E[ent]
    cols = [c for c in cols if c[0] not in cols_out]
    if replace:
        cols = [replace.get(c[0], c) for c in cols]
    if after:
        i = [c[0] for c in cols].index(after) + 1
        cols = cols[:i] + list(add) + cols[i:]
    else:
        cols = cols + list(add)
    E[ent] = (desc, cols)


_u = E["USUARIO"][1]
E["USUARIO"] = (E["USUARIO"][0], [(c[0], c[1], c[2], c[3], c[4], c[5].replace("DESPACHADOR | CONDUCTOR", "DESPACHADOR | CONDUCTOR | CONVENIO | PASAJERO (DC-34)"), c[6], c[7]) if c[0] == "rol" else c for c in _u])
E["CONVENIO"] = ("Acuerdo comercial con una empresa cliente; desde CC-16 la empresa cliente se registra en el portal y el administrador la aprueba (DC-35).", [
    c for c in E["CONVENIO"][1] if c[0] not in ("token_link", "password_hash", "activo", "intentos_fallidos", "bloqueado_hasta")] + [
    ("estado", "VARCHAR(12)", "No", "", "Estado del convenio (DC-35)", "EN_REVISION | APROBADO | RECHAZADO | INACTIVO; INACTIVO deshabilita la cuenta (RN-08)", "EN_REVISION", ""),
    ("encargado_nombre", "VARCHAR(80)", "No", "", "Encargado de la empresa cliente", "Texto no vacío", "—", "Personal"),
    ("encargado_telefono", "VARCHAR(16)", "No", "", "Teléfono del encargado", "E.164", "—", "Personal"),
    ("motivo_rechazo", "VARCHAR(200)", "Sí", "", "Motivo del rechazo", "Obligatorio si RECHAZADO", "NULL", ""),
    ("revisado_por", "BIGINT", "Sí", "FK", "Administrador que aprobó o rechazó", "→ USUARIO.id", "NULL", ""),
    ("revisado_en", "TIMESTAMPTZ", "Sí", "", "Momento de la revisión", "UTC", "NULL", ""),
    ("usuario_id", "BIGINT", "Sí", "FK, UK", "Cuenta de la empresa cliente (rol CONVENIO)", "→ USUARIO.id (1:0..1)", "NULL", ""),
    ("creado_en", "TIMESTAMPTZ", "No", "", "Fecha de registro", "UTC", "now()", ""),
])
_set("VIAJE", add=[
    ("pasajeros", "SMALLINT", "No", "", "Personas que viajan, incluido el titular (DC-42)", "1–7; ≤ mayor capacidad de la flota (DC-43)", "1", ""),
    ("maletas", "SMALLINT", "No", "", "Equipaje declarado (DC-42)", "0–20", "0", ""),
    ("vuelo_salida_en", "TIMESTAMPTZ", "Sí", "", "Hora del vuelo de salida, en viajes hacia el aeropuerto (DC-42)", "UTC; solo se guarda, sin monitoreo", "NULL", ""),
    ("vuelo_salida_tipo", "VARCHAR(13)", "Sí", "", "Tipo del vuelo de salida (DC-42)", "NACIONAL | INTERNACIONAL; define la antelación sugerida", "NULL", ""),
], after="recogida_en", cols_out=("autorizacion_avisos_supervisor",))
_set("VIAJE", add=[("autorizacion_avisos_por", "BIGINT", "Sí", "FK", "Usuario del convenio que declaró la autorización de avisos (DC-35)", "→ USUARIO.id", "NULL", "")], after="autorizacion_avisos_en")
E["CUENTA_PASAJERO"] = ("Cuenta con la que el pasajero pide en el portal (CC-18): se activa al confirmar su teléfono por WhatsApp (DC-36, DC-44, DC-45).", [
    ("usuario_id", "BIGINT", "No", "PK, FK", "Usuario de rol PASAJERO", "→ USUARIO.id (1:0..1)", "—", ""),
    ("empresa_id", "BIGINT", "No", "FK", "Empresa en la que se creó la cuenta", "→ EMPRESA.id", "—", ""),
    ("nombre", "VARCHAR(80)", "No", "", "Nombre del titular", "Texto no vacío", "—", "Personal"),
    ("telefono", "VARCHAR(16)", "No", "", "WhatsApp del titular", "E.164; único por empresa entre las cuentas confirmadas", "—", "Personal"),
    ("pasajero_id", "BIGINT", "Sí", "FK, UK", "Pasajero ligado al confirmar", "→ PASAJERO.id; NULL hasta confirmar", "NULL", ""),
    ("confirmada_en", "TIMESTAMPTZ", "Sí", "", "Confirmación del teléfono por WhatsApp", "UTC; sin confirmar no puede pedir", "NULL", ""),
    ("reenviada_en", "TIMESTAMPTZ", "Sí", "", "Último reenvío del mensaje de activación (DC-45)", "UTC", "NULL", ""),
    ("privacidad_aceptada_en", "TIMESTAMPTZ", "Sí", "", "Aceptación del aviso de privacidad y de los avisos por WhatsApp (DC-44)", "UTC; una vez por versión del aviso", "NULL", ""),
    ("privacidad_version", "VARCHAR(10)", "Sí", "", "Versión del aviso aceptada (DC-44)", "Si cambia la versión, se vuelve a aceptar", "NULL", ""),
    ("creada_en", "TIMESTAMPTZ", "No", "", "Fecha de creación", "UTC", "now()", ""),
])
REL += [("USUARIO", "CUENTA_PASAJERO", "1:0..1"), ("PASAJERO", "CUENTA_PASAJERO", "1:0..1"), ("USUARIO", "CONVENIO", "1:0..1")]
