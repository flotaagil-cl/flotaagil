from data_backlog import HU, SPRINTS, RESP


def implementacion(r):
    r.H1("Plan de Implementación")
    r.P("Este capítulo define cómo se pone en marcha y se opera la solución una vez construida. Todo lo descrito está **propuesto**; su primera "
        "ejecución completa ocurre en las semanas 15 y 16 (despliegue, capacitación, marcha blanca y UAT). Hasta la fecha de corte el sistema "
        "corre en el ambiente local de desarrollo, con Docker Compose.")
    r.H2("Gestión de Disponibilidad")
    r.H3("Servicios TI, dependencias y análisis de fallas")
    svc = [
        ("Hosting de la aplicación (EC2 + Docker)", "SLA-01, 02, 03", "Crítico", "AWS us-east-1a"),
        ("API REST y canal WSS", "SLA-01, 02", "Crítico", "Gunicorn, Daphne, Redis, PostgreSQL"),
        ("Base de datos PostgreSQL + PostGIS", "SLA-01, 02, 03", "Crítico", "EBS, respaldos"),
        ("Tareas asíncronas (Celery)", "SLA-02 (avisos), SLA-01 (expiraciones)", "Alto", "Redis"),
        ("Mensajería WhatsApp", "SLA-02", "Alto", "Twilio, Meta"),
        ("Monitoreo de vuelos", "SLA-01 (recogidas en aeropuerto)", "Medio", "API de vuelos"),
        ("DNS y certificado TLS", "Todos", "Crítico", "Route 53, Let's Encrypt"),
    ]
    r.table("svc", "Servicios TI y su relación con los objetivos de disponibilidad", ["Servicio TI", "SLA que soporta", "Criticidad", "Depende de"], svc,
            [5.2, 4.4, 2.0, 5.0], font=8)
    fmea = [
        ("Instancia EC2", "Falla de hardware o del hipervisor", "Caída total", "StatusCheckFailed en CloudWatch; UptimeRobot", "Acción de recuperación automática de EC2; si no basta, relanzar desde snapshot (PO-02)"),
        ("Contenedor api o ws", "Error de memoria o excepción fatal", "Caída del panel o del tiempo real", "Health check de Docker; Sentry", "restart: unless-stopped; límites de memoria por contenedor"),
        ("PostgreSQL", "Disco lleno o corrupción", "Caída total o pérdida de datos", "Alarma de disco > 75 %; error en /health", "Purga de posiciones; restauración desde respaldo"),
        ("Redis", "Reinicio", "Pérdida de últimas posiciones (se reconstruyen en segundos)", "/health", "Datos efímeros; reconstrucción con el siguiente ping"),
        ("Despliegue", "Versión defectuosa o migración fallida", "Errores 5xx", "Prueba de humo (CP-34)", "Reversión a la imagen anterior (PO-03)"),
        ("Certificado TLS", "Expiración", "Navegadores bloquean el sitio", "Aviso de Certbot y de UptimeRobot a 14 días", "Renovación automática cada 60 días"),
        ("Twilio / Meta", "Indisponibilidad o plantilla rechazada", "Sin avisos ni verificación", "Tasa de fallos de entrega > 5 %", "Cola con reintentos; alerta; confirmación telefónica"),
        ("Conectividad del conductor", "Zona sin cobertura", "Posición desactualizada", "Antigüedad del dato > 60 s", "La app encola y reenvía; marca de no confiable"),
    ]
    r.table("fmea", "Análisis de fallas que afectan la disponibilidad", ["Componente", "Modo de falla", "Efecto", "Detección", "Medida"], fmea,
            [2.6, 3.0, 3.0, 3.4, 4.6], font=7.8)
    r.H3("Monitoreo, alertas y su atención")
    mon = [
        ("Disponibilidad externa", "UptimeRobot: /health y WSS cada 5 min", "2 fallas consecutivas", "Guardia (push y correo)", "P1"),
        ("Errores de aplicación", "Sentry", "Error nuevo o > 20 eventos en 10 min", "Correo del equipo", "P2"),
        ("CPU", "CloudWatch", "> 80 % durante 15 min", "SNS → correo", "P3"),
        ("Memoria", "Agente CloudWatch", "> 85 % durante 10 min", "SNS → correo", "P2"),
        ("Disco", "Agente CloudWatch", "> 75 %", "SNS → correo", "P3"),
        ("Estado de la instancia", "CloudWatch StatusCheckFailed", "1 falla", "Acción de recuperación + SNS", "P1"),
        ("Latencia de la API", "Middleware → logs", "p95 > 2 s en 15 min", "Correo", "P3"),
        ("Respaldo lógico cada 6 h", "Tarea pg_dump + verificación", "Falla, tamaño anómalo (±50 %) o más de 7 h sin un respaldo válido", "Correo", "P2"),
        ("Entregas de WhatsApp", "Estados del webhook", "> 5 % FAILED en 1 h", "Panel y correo", "P2"),
    ]
    r.table("mon", "Variables monitoreadas, umbrales y destinatarios", ["Variable", "Herramienta", "Umbral", "Destinatario", "Prioridad"], mon,
            [3.2, 4.0, 3.8, 3.4, 2.2], font=8)
    r.P("**Atención de alertas.** La guardia (rotación semanal entre Renato y Carlos) acusa recibo de la alerta, abre un registro de incidente, "
        "diagnostica con el procedimiento de 8.3 y, si en 30 minutos no restablece el servicio, escala al otro integrante e informa al administrador "
        "de la flota. **Mantenimiento preventivo (mensual, en la ventana):** parches de Ubuntu y actualización de imágenes base, revisión de "
        "Dependabot, verificación de restauración, limpieza de imágenes y registros antiguos, revisión de la vigencia del dominio y de las plantillas.")
    r.P("**Capacidad y crecimiento.** Se revisan mensualmente CPU, memoria, disco, conexiones WSS y filas de POSICION_GPS. Con más de 70 conductores, "
        "memoria sobre 80 % sostenida o un segundo cliente se escala a t4g.medium; con más de cuatro flotas se separa la base de datos en Amazon "
        "RDS. **Despliegues sin interrupción perceptible:** imágenes construidas y probadas en CI, migraciones compatibles hacia atrás (agregar "
        "antes de eliminar), reinicio contenedor por contenedor con *health check* y despliegues fuera de horas punta; los cambios que exigen corte "
        "van en la ventana mensual. **Redundancia:** no se implementa una segunda instancia (≈ USD 60/mes adicionales, ver 4.2); la alternativa "
        "viable es la recreación desde snapshot en otra zona y el modo de operación manual de contingencia (8.2).")
    r.P("**Medición del cumplimiento.** Disponibilidad = (minutos del mes − minutos no disponibles no programados) ÷ minutos del mes × 100, con los "
        "datos de UptimeRobot. Carlos Ortiz emite el informe mensual con incidentes, causa y acciones; se revisa con el administrador. **Recursos y "
        "costos para sostener el servicio:** ≈ USD 21/mes de AWS y EUR 10/mes de UptimeRobot (ver {T:costos}), más unas 4 horas mensuales del equipo "
        "en mantenimiento preventivo y la guardia.")

    r.H3("Puesta en marcha")
    r.P("**Requisitos previos:** dominio flotaagil.cl delegado a Route 53; cuenta AWS con MFA y presupuesto con alerta; cuenta de Twilio con "
        "remitente de WhatsApp aprobado y plantillas de utilidad aprobadas por Meta; clave de Google Maps restringida al dominio; credencial de la API "
        "de vuelos; APK firmada (versión 1.0.0); teléfonos de conductores con Android 10+ y permisos de ubicación; consentimiento informado de "
        "conductores y aviso de privacidad publicado; planillas de carga inicial revisadas por el cliente.")
    seq = [
        ("1", "Crear VPC, subred, Security Group, Elastic IP, rol IAM y parámetros SSM", "Carlos", "Semana 15, día 1", "Lista de verificación"),
        ("2", "Lanzar EC2 de producción y de staging, instalar Docker, configurar DLM, S3, respaldos cada 6 h y alarmas", "Carlos", "Semana 15, día 1", "Alarmas en estado OK"),
        ("3", "Desplegar la versión 1.0.0 con Docker Compose; emitir certificado TLS", "Carlos", "Semana 15, día 2", "SSL Labs ≥ A"),
        ("4", "Carga, estrés, seguridad y restauración en staging", "Carlos", "Semana 15, días 2–3", "CP-28 a CP-31 aprobados"),
        ("5", "Ejecutar migraciones y cargar datos maestros (conductores, vehículos, convenios, geocerca)", "Carlos + cliente", "Semana 15, día 3", "Reporte de carga sin rechazos"),
        ("6", "Prueba de humo y verificación de webhooks y plantillas", "Carlos", "Semana 15, día 3", "CP-34 aprobado"),
        ("7", "Capacitación de administrador, despachadores y conductores; instalación de la APK; revisión del SLA", "Renato", "Semana 15, días 4–5", "Lista de asistencia"),
        ("8", "Marcha blanca con un grupo de conductores, en paralelo a la planilla", "Equipo + cliente", "Semana 15, día 5, a semana 16, día 3", "Registro de defectos; primeros cierres de caja"),
        ("9", "UAT con el guion por rol", "Equipo; aprueba el cliente", "Semana 16, días 3–4", "Acta de UAT (E-11)"),
        ("10", "Corte: FlotaÁgil pasa a ser el registro oficial", "Cliente", "Semana 16, día 5", "Comunicado a conductores"),
    ]
    r.table("seq", "Secuencia de instalación, configuración y despliegue", ["Paso", "Actividad", "Responsable", "Cuándo", "Verificación"], seq,
            [1.0, 7.0, 2.6, 3.2, 2.8], font=8, align_center_cols=(0,))
    r.P("Respecto de la versión anterior, la instalación, las pruebas en staging, la carga de datos y la capacitación se adelantaron de la "
        "semana 16 a la 15, porque la construcción terminó antes de lo planificado. La semana 16 queda solo con el cierre de la marcha blanca, "
        "la UAT y el corte; la justificación de la carga de trabajo está en la sección 9.1.")
    r.P("**Carga inicial de datos:** conductores, vehículos y convenios desde las planillas del cliente mediante CSV con validación de RUT y patente; "
        "las reservas históricas no se migran (quedan en Excel como respaldo). **Verificaciones posteriores al despliegue:** /health, login por rol, "
        "WSS desde la app, reserva de prueba de punta a punta, mensaje de WhatsApp, primer respaldo de 6 h ejecutado y alarmas activas. **Criterios de "
        "aceptación de la puesta en marcha:** UAT firmada sin defectos críticos ni altos abiertos, 100 % de conductores de la marcha blanca operando "
        "con la app, respaldo restaurado con éxito en staging y SLA acordado. **Documentación:** manual de usuario por rol, guía rápida de una página "
        "para conductores, manual de operación (procedimientos PO-01 a PO-06 del Anexo L) y video corto de la app. **Reversión:** si el despliegue "
        "falla se vuelve a la imagen anterior (PO-03); si la puesta en marcha completa fracasa, el cliente continúa con la planilla, que se mantiene "
        "actualizada hasta el corte del paso 10.")

    r.H2("Gestión de Continuidad")
    r.P("La continuidad combina medidas **proactivas** (evitar o reducir el impacto de una interrupción) y **reactivas** (recuperar el servicio). "
        "Los objetivos son **RTO de 2 horas** y **RPO de 6 horas** para los servicios críticos. El RTO se justifica en el tiempo estimado para "
        "recrear la instancia desde un snapshot y verificarla (≈ 45–60 min, que el ensayo CP-30 mide), más el margen para el diagnóstico; dos horas es el "
        "máximo que la operación puede sostener con el modo manual de contingencia. El **RPO de 6 horas** resulta de la frecuencia de los respaldos: "
        "tanto el snapshot del volumen como el respaldo lógico (pg_dump) se toman **cada 6 horas**, alternados con tres horas de desfase "
        "({T:bk}). Así, cada mecanismo por separado cumple el RPO y, cuando ambos están disponibles, la pérdida máxima baja a 3 horas. La versión "
        "anterior prometía 6 horas con un pg_dump diario, lo que no se sostenía si el snapshot fallaba; se corrigió con CC-14. Lo que se pierde "
        "dentro de esa ventana se reconstruye con el procedimiento de retorno al servicio descrito más abajo.")
    esc = [
        ("E1 Caída de la instancia o de la zona", "SLA-01, 02, 03", "Despacho manual; pasajeros sin avisos", "1", "Recuperación automática; relanzar desde snapshot en otra zona"),
        ("E2 Corrupción o borrado de la base de datos", "Datos de viajes y pagos", "Pérdida de información", "1", "Restaurar el último respaldo válido"),
        ("E3 Despliegue defectuoso", "Servicios afectados por la versión", "Errores en funciones", "2", "Reversión de imagen (PO-03)"),
        ("E4 Credenciales comprometidas o ransomware", "Toda la plataforma", "Riesgo legal y de datos", "1", "Rotar secretos, aislar, restaurar desde respaldo limpio, notificar"),
        ("E5 Caída de Twilio/Meta", "SLA-02", "Sin verificación ni avisos", "3", "Cola y reintentos; confirmación telefónica"),
        ("E6 Caída de la API de vuelos", "Recogidas en aeropuerto", "Sin ajuste automático", "3", "Consulta manual en el sitio del aeropuerto"),
        ("E7 Sin Internet en la central", "Panel del despachador", "Despacho más lento", "2", "Panel desde teléfono con datos"),
        ("E8 Dominio o certificado vencido", "Acceso de usuarios", "Sitio inaccesible", "1", "Renovación automática y alertas"),
    ]
    r.table("esc", "Escenarios de interrupción, impacto y prioridad de recuperación", ["Escenario", "Servicios y activos", "Impacto", "Prioridad", "Respuesta"], esc,
            [3.8, 3.0, 3.2, 1.6, 5.0], font=7.8, align_center_cols=(3,))
    r.H3("Respaldos")
    bk = [
        ("Volumen EBS completo", "Snapshot (DLM)", "Cada 6 h: 03:00, 09:00, 15:00 y 21:00", "7 días (28 copias)", "Servicio regional de AWS; cifrado KMS"),
        ("Base de datos", "pg_dump comprimido", "Cada 6 h: 00:00, 06:00, 12:00 y 18:00", "Las de 6 h, 7 días; la de las 00:00, 30 días (≈ 50 copias, ≈ 6 GB)", "S3 privado, cifrado, versionado; acceso solo con el rol de la instancia y la cuenta raíz con MFA"),
        ("Configuración (compose, nginx, parámetros)", "Repositorio Git + SSM", "Cada cambio", "Historial completo", "GitHub (2FA, reglas de rama) y SSM"),
        ("Secretos", "SSM Parameter Store (SecureString)", "Cada cambio", "Versionado de SSM", "IAM; nunca en el repositorio"),
        ("APK firmada y llave de firma", "Archivo cifrado", "Cada versión", "Permanente", "Dos copias fuera de AWS (gestor de contraseñas del equipo)"),
    ]
    r.table("bk", "Información respaldada, frecuencia, ubicación y retención", ["Elemento", "Mecanismo", "Frecuencia", "Retención", "Ubicación y protección"], bk,
            [3.4, 2.6, 2.8, 2.4, 5.4], font=8)
    r.P("**Supervisión e integridad:** Carlos Ortiz revisa cada lunes el estado de snapshots y dumps; la tarea de respaldo verifica el código de "
        "salida y el tamaño, y una vez al mes se restaura el dump en staging y se ejecutan conteos de control (viajes, pagos y suma de montos del "
        "mes) contra producción. **Medidas preventivas:** parches mensuales, mínimo privilegio en IAM, MFA, secret scanning y Dependabot, Security "
        "Group restrictivo, límite de tasa en accesos públicos, alarmas de disco y certificado, y pruebas de humo en cada despliegue.")
    r.H3("Activación, recuperación y vuelta a la normalidad")
    r.P("**Alternativa temporal de operación:** el despachador usa la planilla de contingencia (plantilla con los mismos campos de la reserva) y "
        "asigna por teléfono; los conductores anotan los cobros en el formulario de papel de la guía rápida. Cada fila de la planilla lleva un "
        "**folio correlativo** (C-001, C-002…), que es la llave para volver a ingresarla. **Activación:** se declara contingencia cuando un servicio crítico lleva 30 minutos sin restablecerse o ante pérdida o "
        "compromiso de datos. **Declara y coordina:** Carlos Ortiz como líder; en su ausencia, Renato González. **Cadena de comunicación:** guardia → "
        "líder → administrador de la flota → despachadores → conductores (grupo de WhatsApp de la empresa); contactos en el manual de operación.")
    r.bullets([
        "**Diagnóstico y contención (0–30 min):** revisar UptimeRobot, CloudWatch y Sentry; identificar el escenario; si hay sospecha de compromiso, "
        "aislar la instancia (Security Group sin entrada) y rotar secretos.",
        "**Secuencia de recuperación:** 1) infraestructura (instancia o volumen desde snapshot), 2) PostgreSQL y verificación de integridad, 3) Redis, "
        "4) API y canal WSS, 5) Celery, 6) Nginx y certificado, 7) clientes (la app se reconecta sola).",
        "**Restauración de datos y configuración:** volumen desde el snapshot más reciente o, si está comprometido, instancia nueva + pg_restore del "
        "último dump válido + configuración desde Git y SSM (PO-02).",
        "**Validación:** prueba de humo, conteos de control, login por rol, asignación de prueba y revisión de la última reserva conocida.",
        "**Reanudación:** con la validación aprobada, el líder declara el fin de la contingencia y la operación vuelve de inmediato al sistema; "
        "los viajes de la planilla se ingresan con el procedimiento de retorno al servicio (PO-06).",
        "**Comunicación:** aviso al administrador al activar, cada 30 minutos y al cerrar; mensaje a conductores al volver a operar.",
        "**Registro y revisión posterior:** el incidente queda documentado (8.3); en 5 días hábiles se realiza una revisión sin culpables con causa "
        "raíz y acciones, que entran al backlog.",
    ])
    r.H3("Retorno al servicio: carga diferida de la contingencia")
    r.P("La EF2 observó que faltaba explicar cómo vuelven al sistema los viajes anotados en papel. Durante una caída se producen **dos vacíos** "
        "que hay que cerrar ({T:retorno}): lo operado a mano mientras el sistema no estuvo disponible y, si hubo que restaurar un respaldo, lo "
        "que el sistema había registrado después de ese respaldo. El procedimiento PO-06 (Anexo L) cierra ambos con una función específica, la "
        "**reserva de contingencia** (HU-32, CC-15).")
    r.table("retorno", "Línea de tiempo de una caída y cómo se recupera cada tramo", ["Tramo", "Qué ocurre con los datos", "Fuente para reconstruir", "Cómo vuelve al sistema"], [
        ("Antes del último respaldo válido", "Se conservan completos", "—", "Restauración (PO-02)"),
        ("Del último respaldo a la falla (máximo 6 h; 3 h con ambos mecanismos)", "Se pierden solo si hubo que restaurar un respaldo", "Mensajes de WhatsApp en Twilio, que conserva su propio historial; registros del conductor y cuaderno de respaldo de la central", "Reserva de contingencia con el folio «R» y las horas reales"),
        ("De la falla al restablecimiento (máximo 2 h)", "Operación manual", "Planilla de contingencia con folio y formulario de cobros del conductor", "Reserva de contingencia con el folio de la planilla"),
        ("Viajes que estaban en curso al fallar", "Quedan en un estado intermedio", "Conductor y planilla", "Cierre o anulación forzada (HU-05) con motivo, método de pago y monto"),
        ("Después del restablecimiento", "Operación normal", "—", "—"),
    ], [3.8, 3.6, 4.8, 4.4], font=7.8)
    r.bullets([
        "**Plazo y responsable:** el despachador de turno ingresa las filas dentro de las 24 horas siguientes al restablecimiento; el "
        "administrador revisa la conciliación.",
        "**Qué registra una reserva de contingencia:** folio, pasajero, origen y destino, hora real de recogida, conductor y vehículo, estado "
        "final (FINALIZADO con método y monto, o CANCELADO con motivo). Queda con canal CONTINGENCIA y la fecha de ingreso al sistema es distinta "
        "de la del servicio, por lo que siempre se distingue de una reserva normal.",
        "**Qué no hace:** no envía avisos ni encuesta al pasajero, porque el viaje ya ocurrió; no acepta un folio repetido; no reemplaza al "
        "cierre forzado para los viajes que ya existían en el sistema.",
        "**Conciliación:** un reporte compara los folios de la planilla con las reservas ingresadas y la suma de los montos. La contingencia se "
        "cierra cuando coinciden el número de folios y el total cobrado; el administrador lo firma y la planilla se archiva.",
        "**Caja:** los cobros de esos viajes entran al turno del conductor, de modo que el cierre de caja (HU-31) los incluye y la diferencia "
        "sigue siendo medible.",
        "**Indicadores:** los viajes de contingencia cuentan para KPI-01, KPI-05 y KPI-08, y se excluyen de KPI-02 y KPI-09, porque sus tiempos "
        "de asignación y de llegada no se midieron.",
        "**Trazabilidad:** cada ingreso queda en AUDITORIA con el usuario y la hora (acción RESERVA_CONTINGENCIA).",
    ])
    r.P("**Ejercicios:** simulacro de restauración y de carga diferida en staging en la semana 15 (CP-30 y CP-37), mensual durante la operación, "
        "y un ejercicio de mesa trimestral con el cliente sobre la contingencia manual. **Coherencia entre contingencia, restauración y retorno:** "
        "el RPO de 6 h coincide con la frecuencia de cada mecanismo de respaldo; el RTO de 2 h supera el tiempo estimado de recreación y acota "
        "el tramo que se opera a mano; la planilla con folio cubre ese tramo y la reserva de contingencia lo devuelve al sistema con trazabilidad; "
        "los recursos necesarios (DLM, S3, staging) ya están en el presupuesto; y el SLA de 99,0 % (7 h 12 min al mes) admite un incidente mayor "
        "al mes.")

    r.H2("Plan de Mantención")
    r.H3("Gestión de configuración")
    ci = [
        ("Código fuente (backend, web, app, infra)", "Repositorio flotaagil-cl/flotaagil (migrado con su historial completo); tags SemVer (v1.0.0)", "GitHub", "Carlos (backend, infra) · Renato (web, app)"),
        ("Dependencias", "requirements.lock, package-lock.json con versiones fijas", "Repositorio", "Ambos; Dependabot"),
        ("Imágenes Docker", "ghcr.io/flotaagil/*: etiqueta = versión + SHA del commit", "GitHub Container Registry", "Carlos"),
        ("Infraestructura", "Inventario y runbook versionados en /infra; IDs de recursos AWS", "Repositorio + AWS", "Carlos"),
        ("Esquema de base de datos", "Migraciones Django numeradas", "Repositorio", "Carlos"),
        ("Datos maestros y geocerca", "CSV de carga inicial y polígono GeoJSON versionados", "Repositorio (sin datos personales) / S3", "Carlos"),
        ("Configuración y secretos", "Parámetros SSM por ambiente (/flotaagil/prod/*)", "AWS SSM", "Carlos"),
        ("APK de la app", "versionName 1.0.0, versionCode incremental; llave de firma", "Releases de GitHub; llave fuera del repo", "Renato"),
        ("Plantillas de WhatsApp", "Nombre e identificador aprobado por Meta", "Twilio Console + /docs", "Carlos"),
        ("Documentos (informes, manuales, SLA)", "Versión en el nombre y en la portada", "Repositorio /docs", "Líder de proyecto"),
    ]
    r.table("ci", "Elementos de configuración controlados", ["Elemento", "Identificación y versión", "Ubicación", "Responsable"], ci, [4.0, 6.0, 3.6, 3.0], font=7.8)
    r.P("**Relaciones:** cada release del repositorio fija la combinación de imágenes, migraciones, versión mínima de la APK y plantillas que "
        "funcionan juntas, registrada en las notas de la release. **Líneas base:** v0.1 a v0.4 (una por sprint, que se etiquetan al fusionar "
        "su pull request) y v1.0.0 (producción, aprobada en la UAT). **Actualización:** todo cambio entra por pull "
        "request con CI en verde y la lista de chequeo de revisión (DC-47: mientras opere un solo integrante, la aprobación obligatoria se reemplaza por esa lista y se repone al volver el equipo completo); la fusión es *squash* a main y la release se etiqueta (configurado y probado en el "
        "Sprint 0, Anexo N). **Control de acceso:** "
        "organización de GitHub con 2FA obligatoria, reglas de rama que impiden *push* directo a main, secret scanning con push protection; SSM e "
        "IAM con mínimo privilegio. **Reconstrucción de una configuración conocida:** checkout del tag, imágenes del registro con esa etiqueta, "
        "parámetros SSM de esa versión y el respaldo correspondiente (PO-02).")
    r.H3("Gestión de cambios")
    r.P("**Canal:** *issue* de GitHub con la plantilla «Solicitud de cambio» (formulario RFC del Anexo L), que registra solicitante, motivo, "
        "elemento afectado, urgencia y beneficio esperado. **Clasificación:** *estándar* (preaprobados y de bajo riesgo, como actualizar una "
        "dependencia menor o rotar una contraseña), *normal* (funcionalidad o configuración) y *de emergencia* (restablecer un servicio caído o "
        "corregir una vulnerabilidad).")
    cam = [
        ("1. Solicitar", "Cualquier interesado", "Issue RFC completo"),
        ("2. Analizar impacto", "Líder de proyecto", "Efecto en alcance, tiempo (SP), costo, calidad y riesgos; elementos de configuración afectados"),
        ("3. Evaluar y decidir", "PO Juan Pérez (alcance y prioridad); líder (técnica); cliente si cambia el alcance comprometido o el SLA", "Aprobado si aporta valor, cabe en la capacidad o desplaza algo de menor prioridad y no rompe un SLA; rechazado o diferido en otro caso"),
        ("4. Programar", "PO en Sprint Planning; emergencias de inmediato", "Sprint asignado o ventana de mantenimiento"),
        ("5. Implementar y probar", "Developers", "Rama, pruebas automatizadas y casos afectados; staging"),
        ("6. Actualizar documentación", "Autor del cambio", "HU, diagramas, diccionario, manuales y Anexo D"),
        ("7. Comunicar", "Líder", "Aviso a usuarios afectados con fecha y efecto"),
        ("8. Liberar con plan de reversión", "Carlos", "Despliegue; reversión a la imagen y respaldo previos si falla la humo"),
        ("9. Cerrar", "Líder", "Resultado registrado en el issue y en el registro de cambios"),
    ]
    r.table("cam", "Procedimiento de gestión de cambios", ["Paso", "Responsable", "Criterio o registro"], cam, [3.4, 5.6, 7.6], font=8)
    r.P("Los cambios de emergencia se implementan primero y se documentan y aprueban en las 24 horas siguientes. Los cambios CC-01 a CC-11 de la segunda "
        "entrega, los cambios CC-12 a CC-15, originados en la EF2, y los cambios CC-16 a CC-18 de la semana 14 siguieron este procedimiento y su registro está en el Anexo D.")
    r.P("**Ejemplo de aplicación (CC-18, cuenta obligatoria para pedir).** 1) El cliente pidió dejar de recibir reservas de invitados por "
        "seguridad. 2) El análisis mostró impacto en alcance (HU-19, HU-20, RN-06 y el formulario público), en datos (CUENTA_PASAJERO) y en "
        "riesgos (baja el de reservas falsas). 3) El PO lo aprobó con la condición de no comprometer la UAT. 4) Se programaron HU-37 a HU-44 "
        "en el Sprint 4 y HU-45 a HU-49 en la versión 1.1. 5) Cada historia se construyó en su rama con pruebas. 6) Se registraron las "
        "decisiones DC-41 a DC-46 en el diccionario. 7) a 9) La liberación sigue el procedimiento normal en la fusión del Sprint 4. "
        "**Cambio de configuración del repositorio:** ante la restricción de la cuenta de GitHub de un integrante (R-15), el repositorio se migró "
        "a una organización nueva con su historial, ramas y etiquetas; se verificó que los commits coincidieran y que la integración continua "
        "volviera a ejecutarse, y el cambio se registra como decisión de proceso.")
    r.H3("Gestión de incidentes")
    r.P("**Canal de reporte:** WhatsApp de soporte o correo para usuarios; alertas automáticas de monitoreo. Todo incidente se registra como *issue* "
        "con la etiqueta «incidente» y la plantilla del Anexo L: identificador, fecha y hora de detección, quién reporta, servicio y componente "
        "afectados, descripción y evidencia, impacto, urgencia, prioridad, responsable, acciones, hora de restablecimiento, causa y cierre.")
    prio = [
        ("P1 Crítica", "Servicio crítico caído o pérdida o compromiso de datos", "30 min (07:00–24:00) · 60 min (00:00–07:00)", "2 h", "Inmediato al líder y al cliente"),
        ("P2 Alta", "Función principal degradada sin alternativa (p. ej., sin avisos de WhatsApp)", "1 h", "8 h", "Si no se resuelve en 4 h"),
        ("P3 Media", "Falla con alternativa (p. ej., reporte con error)", "4 h hábiles", "3 días hábiles", "Revisión en el sprint"),
        ("P4 Baja", "Consulta o defecto menor", "2 días hábiles", "Próximo sprint", "—"),
    ]
    r.table("prio", "Prioridades, tiempos objetivo y escalamiento", ["Prioridad", "Criterio", "Respuesta", "Restauración", "Escalamiento"], prio,
            [2.2, 5.6, 3.6, 2.2, 3.0], font=8)
    r.P("**Clasificación:** la prioridad resulta de cruzar impacto (alto: toda la operación; medio: un rol o función; bajo: un usuario) con urgencia "
        "(alta: impide trabajar ahora; media: hay alternativa; baja: puede esperar): alto-alta = P1; alto-media o medio-alta = P2; medio-media, "
        "alto-baja o bajo-alta = P3; resto = P4. **Responsable:** la guardia de la semana. **Diagnóstico:** reproducir, revisar Sentry, logs por "
        "identificador de correlación, métricas y cambios recientes; identificar el componente. **Escalamiento técnico:** guardia → otro developer → "
        "proveedor (AWS, Twilio, API de vuelos); **funcional:** administrador de la flota para decisiones de operación. **Comunicación:** al "
        "reportante al acusar recibo, en cada cambio de estado y al cerrar; en P1, también al cliente cada 30 minutos. **Solución temporal:** "
        "reinicio del contenedor, reversión de versión o modo manual de contingencia. **Validación:** el reportante o la prueba de humo confirman el "
        "restablecimiento. **Cierre:** con causa identificada, evidencia adjunta y, si corresponde, HU o tarea de corrección definitiva. "
        "**Incidentes repetitivos:** dos o más con el mismo síntoma en 30 días abren un registro de problema con análisis de causa raíz (cinco "
        "porqués) y una corrección priorizada en el backlog.")


def cronograma(r):
    r.H1("Ajustes del Cronograma")
    r.H2("Revisión de Carta Gantt o desarrollo de fases")
    r.P("La Carta Gantt se rehízo con el **avance real** al corte de la semana 14, como pidió la retroalimentación de la EF2. La Figura "
        "{F:gantt} compara, actividad por actividad, la línea base de la formulación (barra clara) con lo ejecutado (barra verde), lo que está "
        "en curso (barra naranja) y lo replanificado para las semanas que quedan (barra achurada). Se mantienen las 16 semanas, los hitos H-1 a H-6 y los "
        "entregables E-01 a E-13, y se marcan los hitos académicos: **EF2 en la semana 12** y **ES2 en la semana 14**.")
    r.figure("fig/gantt.png", "gantt", "Carta Gantt: línea base frente al avance real al corte de la semana 14", width_cm=16.6)
    r.P("**Lectura del avance.** Los Sprints 1, 2 y 3 se ejecutaron en las semanas de la línea base y completaron su alcance. La Carta Gantt "
        "de la EF2 todavía mostraba los Sprints 1 y 2 como planificados, porque no se había actualizado con el avance, y el informe de esa "
        "entrega detallaba solo el Sprint 0 y la prueba de concepto H-3. Esta versión corrige ambas cosas: el Gantt refleja lo ejecutado y el "
        "capítulo VII documenta cada sprint con sus historias, pruebas y defectos. El **Sprint 4** está en curso (semanas 14 y 15) y va "
        "adelantado: sus siete historias están construidas, porque reutilizan componentes de los sprints anteriores, y el tiempo restante se "
        "destina a las correcciones de la EF2, a la fusión y a preparar la puesta en marcha. Los hitos se cumplieron en su semana (H-1 en la 5, "
        "H-2 y H-3 en la 7, H-4 en la 11), salvo la prueba de la PoC H-3 en un teléfono real, que queda para la semana 14.")
    rows = []
    REAL = {"S1": "Terminado", "S2": "Terminado", "S3": "Terminado", "S4": "En curso: historias construidas y en revisión; se suman HU-31 y HU-32 (EF2) y HU-33 a HU-44 (CC-16 a CC-18)"}
    for s, (sem, obj) in SPRINTS.items():
        hs = [h for h in HU if h[6] == s]
        ren = [h[0] for h in hs if RESP.get(h[0]) == "Renato"]
        car = [h[0] for h in hs if RESP.get(h[0]) != "Renato"]
        rows.append((s.replace("S", "Sprint "), sem, REAL[s], obj, ", ".join(h[0] for h in hs), "Renato: " + ", ".join(ren) + "\nCarlos: " + ", ".join(car), str(sum(h[5] for h in hs))))
    r.table("sprints", "Sprints: línea base y ejecución real", ["Sprint", "Semanas", "Estado", "Objetivo e incremento", "Historias", "Responsables", "SP"], rows,
            [1.3, 1.5, 2.2, 4.6, 2.6, 3.4, 0.9], font=7.6)
    r.P("La responsabilidad por historia sigue los roles Scrum ({T:roles}): Renato lidera las historias centradas en interfaz y app y Carlos las de backend, "
        "integraciones e infraestructura, con 89 SP cada uno; las historias que cruzan ambas capas (HU-02 y HU-29) se trabajaron en pareja.")
    r.P("**Comparación entre lo planificado y el avance real.** La {T:avance} contrasta el plan de la formulación con el estado a la fecha de "
        "corte, distinguiendo lo terminado, lo modificado y lo pendiente; la {T:velocidad} resume el alcance comprometido y terminado de cada sprint.")
    av = [
        ("Fase 1 · Análisis y formulación (s1–5)", "E-01, E-02, E-03 · H-1", "Terminada; formulación entregada el 09/09/2026", "—"),
        ("Fase 2 · Diseño (s6–7)", "E-04, E-05, E-06 · H-2", "Terminada en la semana 7; E-06 reemplazado por pantallas funcionales", "Ajustada durante los sprints con CC-01 a CC-11 y tras la EF2 con CC-12 a CC-15"),
        ("Ecosistema de desarrollo (Sprint 0, s6–7)", "No planificado como tarea", "Terminado en la semana 7: organización y repositorio, protección de main, CI, Dependabot, secret scanning, 2FA y tablero (Anexo N)", "Actividad incorporada"),
        ("PoC de GPS en segundo plano (s7)", "Informe técnico · H-3", "Hecha en la semana 7: suspensión del WebView detectada y corregida (Anexo M)", "Falta la prueba en teléfono real (semana 14)"),
        ("Sprint 1 (s8–9)", "45 SP", "**Terminado** en la semana 9: HU-03, 10, 13, 17, 19, 20, 26 (45 SP), más la base del backend, del panel y de la app", "Entraron HU-17 y HU-26; salió HU-01"),
        ("Sprint 2 (s10–11)", "45 SP", "**Terminado** en la semana 11: HU-02, 14, 15, 16, 21, 24 (45 SP), más estado en vivo, DC-20, Celery y adaptador de Google Maps", "Se adelantó Celery, previsto para operación"),
        ("Sprint 3 (s12–13)", "44 SP (HU-04, 11, 12, 25)", "**Terminado** en la semana 13: HU-04, 11, 27, 28, 29 (42 SP)", "Entraron HU-27, 28 y 29; HU-12 y HU-25 pasaron al Sprint 4"),
        ("Sprint 4 (s14–15)", "45 SP (HU-05 a 09, 21 a 24)", "**En curso:** HU-01, 05, 06, 12, 18, 25, 30 (46 SP) construidas y en revisión; se suman y están construidas HU-31 y HU-32 (8 SP, EF2) y HU-33 a HU-44 (67 SP, CC-16 a CC-18); HU-45 a HU-49 (21 SP) pasan a la versión 1.1", "Reportes fusionados; entró HU-30; salieron HU-22 y HU-23; entran HU-31 y HU-32"),
        ("Puesta en marcha (s15)", "Dentro de la semana 16", "Planificada: despliegue en AWS, pruebas de carga, seguridad y recuperación en staging, carga de datos y capacitación", "Se adelanta de la semana 16 a la 15"),
        ("Fase 5 · UAT y producción (s16)", "E-11, E-12, E-13 · H-6", "Replanificada: capacitación e inicio de la marcha blanca en la semana 15; UAT y corte en la 16", "Se descarga la semana 16 (ver más abajo)"),
    ]
    r.table("avance", "Planificado frente a avance real", ["Actividad", "Plan (formulación)", "Estado al corte (semana 14)", "Ajuste"], av, [3.8, 3.2, 5.8, 3.8], font=7.8)
    r.table("velocidad", "Alcance comprometido y terminado por sprint", ["Sprint", "Comprometido", "Terminado", "Historias", "Desviación de alcance", "Tareas técnicas adicionales"], [
        ("Sprint 1", "45 SP", "45 SP", "7 de 7", "0 %", "Base del backend, panel y app del conductor"),
        ("Sprint 2", "45 SP", "45 SP", "6 de 6", "0 %", "Estado en vivo, DC-20, tiempo límite de la app, Celery, adaptador de Google Maps"),
        ("Sprint 3", "42 SP", "42 SP", "5 de 5", "0 %", "Vuelo nacional o internacional por código ICAO (DC-22)"),
        ("Sprint 4 (en curso)", "46 SP + 8 SP (EF2)", "46 SP construidos", "7 de 9", "—", "Señal de los vehículos, declaración del supervisor, navegación por dirección"),
        ("**Acumulado**", "**186 SP**", "**178 SP construidos (96 %)**", "**25 de 27**", "**0 % en los sprints cerrados**", "Todas en «En revisión»; fusión pendiente"),
    ], [2.2, 2.2, 3.0, 2.0, 2.4, 4.8], font=8)
    r.P("**Sobre la velocidad.** Los Sprints 1 a 3 completaron 45, 45 y 42 SP, en línea con la velocidad de 45 SP por sprint estimada en la "
        "formulación (R-02 no se materializó). «Terminado» significa construido, probado y con evidencia; la DoD se completa con la aprobación "
        "del pull request, que sigue pendiente por la restricción de la cuenta de GitHub (R-15) y es hoy el cuello de botella del flujo. Como "
        "lo que resta combina desarrollo, despliegue y capacitación, se planifica en **horas** ({T:carga}).")
    r.P("**Cambios absorbidos en la semana 14.** El cliente pidió en esta semana tres cambios (CC-16 a CC-18): un inicio de sesión único, "
        "convenios con cuenta propia y aprobación, administración de usuarios del panel y pedir siempre con cuenta, con el rediseño del portal. "
        "Se aprobaron con una condición del Product Owner: **no mover la UAT ni la semana 16**. Por eso se dividieron: HU-33 a HU-44 entraron al "
        "Sprint 4 porque reutilizan piezas ya construidas (el inicio de sesión y la renovación segura de la sesión, la verificación por WhatsApp de "
        "HU-20, los componentes del panel y el sistema visual) y se construyeron en ramas propias con sus pruebas; HU-45 a HU-49 (perfil y "
        "eliminación de la cuenta, convenios por equipo, personas frecuentes y estados del sistema) quedan para la versión 1.1, después de la "
        "UAT. Esta velocidad no se usa para proyectar los sprints siguientes: el plan de las semanas 15 y 16 se controla en horas y no suma "
        "historias nuevas.")

    r.H3("Plan de las semanas 14 a 16 y carga de la semana 16")
    r.P("La versión anterior concentraba en la semana 16 la capacitación, la marcha blanca, la corrección de errores y la UAT. El académico guía "
        "observó que esa carga no era creíble en una sola semana. Como las historias del Sprint 4 ya están construidas, el resto de ese sprint "
        "deja capacidad libre y el trabajo se redistribuyó entre las semanas 14, 15 y 16 ({T:carga}). La capacidad es de 50 horas por semana "
        "(dos integrantes a 25 h).")
    r.table("carga", "Plan y carga de trabajo de las semanas 14 a 16", ["Semana", "Actividades", "Horas estimadas", "Capacidad", "Resultado esperado"], [
        ("14 (9 al 15/11) · Sprint 4", "Entrega de la ES2 (4 h) · fusión de los cuatro PR con CI (6 h) · HU-31: TURNO y CIERRE_CAJA (9 h) · HU-32: reserva de contingencia (5 h) · CP-14 con simultaneidad (3 h) · credenciales de Twilio, vuelos y mapas (6 h) · guía de prueba en teléfono real (8 h) · corrección de hallazgos (6 h)", "47 h", "50 h", "main con los cuatro sprints; H-3 cerrada; CP-14, CP-36 y CP-37 ejecutados"),
        ("15 (16 al 22/11) · cierre del Sprint 4", "Revisión del Sprint 4 con el PO y el cliente (2 h) · infraestructura en AWS, producción y staging (8 h) · despliegue v1.0.0 y humo (4 h) · carga, estrés, seguridad y restauración en staging (10 h) · corrección de defectos (8 h) · carga de datos maestros (3 h) · capacitación de administrador, despachadores y conductores (6 h) · manuales y guía rápida (6 h) · inicio de la marcha blanca (2 h)", "49 h", "50 h", "Sprint 4 cerrado; CP-28 a CP-31 y CP-34 ejecutados; usuarios capacitados; SLA revisado; H-5"),
        ("16 (23 al 29/11)", "Acompañamiento de la marcha blanca, tres días (12 h) · usabilidad y consumo en teléfono (4 h) · UAT por rol, dos sesiones (6 h) · reserva para corregir lo que encuentren la marcha blanca y la UAT (16 h) · corte, acta y cierre documental (6 h)", "44 h", "50 h", "Acta de UAT firmada; corte; H-6"),
    ], [2.2, 8.6, 1.6, 1.4, 2.8], font=7.6)
    r.P("**Por qué la semana 16 ahora es factible.** 1) La capacitación, el despliegue y las pruebas no funcionales ya no están en ella: pasaron "
        "a la semana 15. 2) La corrección de errores finales tiene dos momentos y no uno: 8 horas en la semana 15, para lo que encuentren las "
        "pruebas en staging, y una reserva de 16 horas en la 16, para lo que encuentren la marcha blanca y la UAT. 3) La marcha blanca empieza "
        "el último día de la semana 15, con lo que acumula cuatro días de operación real antes de la UAT. 4) La semana 16 queda en 44 de 50 "
        "horas, con 6 de holgura. 5) Si un defecto crítico no cabe en la reserva, la UAT se firma con el alcance aprobado y la corrección entra "
        "como primera versión de mantención (v1.0.1) bajo el procedimiento de cambios de 8.3; el corte no se hace con defectos críticos o altos "
        "abiertos. **Condición externa:** la aprobación de las plantillas de WhatsApp por Meta (R-12) no depende del equipo; si no llega antes de "
        "la marcha blanca, esta se hace con el sandbox y los avisos fuera de la ventana de 24 horas quedan fuera de la UAT, declarados en el acta.")
    r.P("**Dependencias revisadas.** La fusión de los pull requests precede a HU-31 y HU-32, que se construyen sobre main; HU-31 depende de "
        "HU-18 (turno) y de HU-06 (liquidación); el despliegue depende de la fusión; las pruebas de carga dependen del staging; y la UAT depende "
        "de la capacitación. **Revisiones y validación:** revisión del académico guía en la EF2 (semana 12) y en la ES2 (semana 14), revisión "
        "del Sprint 4 con el Product Owner y el cliente en la semana 15, y aceptación del cliente en la UAT. Fecha de actualización del "
        "cronograma: semana 14.")
    r.P("**Causas e impacto de los ajustes.** En **alcance**, los cambios CC-01 a CC-05 agregaron 31 SP de aeropuerto y chat, compensados con 32 SP "
        "de fusiones, eliminaciones y reestimaciones (de 179 a 178 SP); las observaciones de la EF2 agregan 8 SP (HU-31 y HU-32), con lo que el "
        "backlog llega a 186 SP, que se absorben en el Sprint 4. En **fechas**, se mantienen las 16 semanas y los hitos; solo la prueba de la "
        "PoC H-3 en un teléfono real se desplaza a la semana 14, y la capacitación se adelanta a la 15. En **recursos**, se suman la cuenta de Twilio, la API de vuelos y unas horas de staging, cubiertas por el "
        "presupuesto. En **calidad**, se agregan los casos CP-07 a CP-11, CP-16, CP-17, CP-19 a CP-21, CP-27, CP-36 y CP-37, y se rediseña CP-14.")
    r.P("**Medidas correctivas ante retrasos.** El control pasa de story points a horas: al cierre de cada semana se compara lo ejecutado con la "
        "{T:carga}. Si la semana 14 no termina con los pull requests fusionados, se priorizan en este orden: 1) fusión y despliegue, que "
        "condicionan todo lo demás; 2) HU-31, que cierra la observación de mayor peso; 3) HU-32, cuyo procedimiento puede operar de forma "
        "provisoria ingresando los viajes como reservas normales con una nota; 4) las pruebas de usabilidad, que pueden hacerse durante la "
        "marcha blanca. **Factibilidad:** el plan es factible porque lo que resta suma 140 horas frente a 150 de capacidad, las 25 historias del "
        "backlog validado ya están construidas y lo nuevo es acotado (8 SP). **Relación con los objetivos:** los cuatro sprints entregaron los "
        "procesos P1, P2 y P3 (OE-02 y OE-03); el cierre del Sprint 4 completa P3.2 y la continuidad; y las semanas 15 y 16 validan la solución (OE-04).")
    r.P("**Seguimiento de riesgos.** La matriz completa, con el estado de cada riesgo a la fecha de corte, está en la {T:riesgos_full}. Los "
        "riesgos con exposición ≥ 12 se revisan cada semana; los que más preocupan para el cierre son R-12 (plantillas de Meta), porque "
        "condiciona la UAT y no depende del equipo, y R-01 (GPS en un teléfono real), porque todavía no se ha probado en la calle.")


def conclusiones(r):
    r.H1("Conclusiones")
    r.P("El proyecto transformó un problema operativo medido (12,1 % de reservas perdidas, 8 min 40 s por asignación y $34.500 diarios de "
        "descuadre) en un producto que funciona de punta a punta. Al corte de la semana 14 están construidas y probadas las 25 historias del "
        "backlog validado, las dos originadas en la EF2 y las doce de los cambios CC-16 a CC-18, con los Sprints 1 a 3 terminados y el Sprint 4 en curso: un pasajero con cuenta pide un viaje desde el portal, un convenio lo hace con su propia cuenta o lo registra el despachador; se confirma "
        "por WhatsApp; el vuelo se valida y se monitorea; el despachador asigna con una sugerencia, que en el aeropuerto es el primero de la "
        "fila virtual; el conductor acepta en 60 segundos; la llegada se marca por geocerca; el pago queda registrado al finalizar; y el "
        "administrador dispone de reportes, auditoría e indicadores. Las tres causas raíz del diagnóstico —sin fuente única de datos, sin "
        "trazabilidad de la flota y sin registro del cobro— tienen una respuesta construida.")
    r.P("La retroalimentación de la EF2 mejoró el proyecto más allá del documento. Al exigir que la factibilidad, el modelo de datos y los "
        "indicadores conversaran entre sí, dejó a la vista tres cosas que no estaban resueltas: que el beneficio del cliente se había calculado "
        "sobre el ingreso bruto; que el modelo no guardaba la historia de los turnos ni lo rendido en caja, por lo que el indicador de "
        "cuadratura no se podía medir; y que no se había definido cómo vuelve al sistema lo operado a mano durante una caída. Las tres se "
        "corrigieron con cambios concretos y trazables: el cálculo con margen neto y punto de equilibrio, las entidades TURNO y CIERRE_CAJA "
        "con la historia HU-31, y la reserva de contingencia con la historia HU-32.")
    r.P("La factibilidad económica quedó más exigente y más creíble. Con un margen supuesto de 25 % por viaje y las metas de los KPI, el "
        "cliente actual obtiene unos $432.500 netos al mes y recupera la licencia en poco más de un mes; el plan se paga con solo recuperar 67 "
        "de las 183 reservas que hoy pierde. El cambio a una licencia perpetua de uso más un plan de servicio mensual resuelve además un "
        "problema de fondo del modelo anterior: permite vender el producto a varias flotas sin ceder el código. Para FlotaÁgil la operación se "
        "sostiene desde el primer cliente ($35.350 mensuales), con un margen estrecho mientras la mensajería pase por un intermediario.")
    r.P("La arquitectura elegida (Django con PostGIS, Channels y Celery; React en el panel, el portal y la app con Capacitor) permitió "
        "completar el alcance de los cuatro sprints y absorber tres cambios del cliente en la última semana sin mover la UAT, y la separación por empresa definida desde el inicio se verificó en cada historia. Las 47 "
        "decisiones de cambio registradas muestran que el diseño necesitó precisiones, no rediseños. La calidad se trató como parte de cada "
        "historia: las 2.075 pruebas automáticas al corte (1.221 de backend, 765 de web y 89 de la app) y las pruebas manuales contra el backend real encontraron 13 "
        "defectos antes de que llegaran a un usuario.")
    r.P("Se distingue con claridad lo demostrado de lo esperado. Está demostrado el funcionamiento con datos sintéticos, servicios externos "
        "simulados, un emulador Android y un ambiente local. **No está demostrado todavía** con WhatsApp real (cuenta, número y plantillas "
        "aprobadas por Meta), con la API de vuelos y Google Maps con claves reales, con el GPS de un teléfono en la calle, ni bajo carga en "
        "AWS; y las historias siguen en revisión, sin fusionar, a la espera de que la integración continua del repositorio migrado quede en verde. Los beneficios, los KPI y los SLA son **proyectados** hasta la marcha blanca, y el margen por viaje es un supuesto que "
        "debe confirmar el cliente. En el cronograma, los hitos se cumplieron en su semana, salvo la prueba de la PoC en un teléfono real.")
    r.P("Como aprendizaje, el foco aeropuerto mostró que una conversación más con el cliente puede cambiar el producto más que cualquier "
        "decisión técnica, y la EF2, que la coherencia entre artefactos no es un asunto de forma: un indicador que el modelo de datos no puede "
        "calcular es un indicador que no existe. También se confirmó que registrar las decisiones y la evidencia de cada historia en el "
        "repositorio hace que el avance sea verificable, y que conviene despejar el riesgo técnico mayor antes de construir.")
    r.P("Los próximos pasos son cerrar el Sprint 4: fusionar los pull requests con la integración continua en verde y ejecutar CP-14 contra la base real; tramitar las plantillas de Meta "
        "y las claves de los servicios externos; ejecutar la guía de prueba en un teléfono real; desplegar en AWS y ejecutar las pruebas de "
        "carga, seguridad y recuperación; capacitar a los usuarios; y cerrar con la marcha blanca y la UAT de la semana 16. Quedan como líneas "
        "de evolución, en este orden: la migración de la mensajería a la Cloud API de Meta, que es una mejora de código (un adaptador nuevo) y "
        "de negocio (baja el costo variable de ≈ $88 a ≈ $32 por reserva); las historias HU-45 a HU-49 de la versión 1.1; la predicción de demanda por franja horaria con el historial de viajes y las llegadas de vuelos programadas; roles y permisos más "
        "finos; el aviso por push con la app cerrada; el portal en inglés para turistas; la operación multiempresa completa y la alta "
        "disponibilidad; y la integración de pagos electrónicos con emisión de documentos tributarios.")


REFS = [
    "Griffith, C. (2017). *Mobile app development with Ionic: Revised edition*. O'Reilly Media.",
    "Mell, P., & Grance, T. (2011). *The NIST definition of cloud computing* (Special Publication 800-145). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-145",
    "Project Management Institute. (2021). *A guide to the project management body of knowledge (PMBOK guide)* (7.ª ed.). Project Management Institute.",
    "Amazon Web Services. (2026a). *Amazon EC2 on-demand pricing*. https://aws.amazon.com/ec2/pricing/on-demand/",
    "Amazon Web Services. (2026b). *Amazon EC2 service level agreement*. https://aws.amazon.com/compute/sla/",
    "AeroDataBox. (2026). *AeroDataBox API: Flight status and airport data*. https://aerodatabox.com/",
    "Amazon Web Services. (2026c). *Amazon EBS snapshots and Data Lifecycle Manager*. https://docs.aws.amazon.com/ebs/latest/userguide/snapshot-lifecycle.html",
    "Axelos. (2019). *ITIL foundation: ITIL 4 edition*. TSO.",
    "Bass, L., Clements, P., & Kazman, R. (2021). *Software architecture in practice* (4.ª ed.). Addison-Wesley.",
    "Biblioteca del Congreso Nacional de Chile. (1970). *Ley N° 17.336 sobre propiedad intelectual*. https://www.bcn.cl/leychile/navegar?idNorma=28933",
    "Biblioteca del Congreso Nacional de Chile. (1992). *Decreto 212: Reglamento de los servicios nacionales de transporte público de pasajeros*. https://www.bcn.cl/leychile/navegar?idNorma=11683",
    "Biblioteca del Congreso Nacional de Chile. (1999). *Ley N° 19.628 sobre protección de la vida privada*. https://www.bcn.cl/leychile/navegar?idNorma=141599",
    "Biblioteca del Congreso Nacional de Chile. (2023). *Ley N° 21.553 que regula a las empresas de aplicación de transporte y a los conductores que prestan servicios a través de ellas*. https://www.bcn.cl/leychile/navegar?i=1191380",
    "Biblioteca del Congreso Nacional de Chile. (2024). *Ley N° 21.719 que regula la protección y el tratamiento de los datos personales y crea la Agencia de Protección de Datos Personales*. https://www.bcn.cl/leychile/navegar?idLey=21719",
    "DigitalOcean. (2026). *Droplet pricing*. https://www.digitalocean.com/pricing/droplets",
    "Django Software Foundation. (2025). *Django documentation (versión 5.2)*. https://docs.djangoproject.com/en/5.2/",
    "Dirección del Trabajo. (2022). *Dictamen Ord. N° 148: Geolocalización como medida de control*. https://www.dt.gob.cl/legislacion/1624/w3-propertyvalue-182333.html",
    "Fette, I., & Melnikov, A. (2011). *The WebSocket protocol* (RFC 6455). Internet Engineering Task Force. https://doi.org/10.17487/RFC6455",
    "FlightAware. (2026). *AeroAPI: Flight tracking and flight status API*. https://www.flightaware.com/commercial/aeroapi/",
    "Google. (2026). *Google Maps Platform pricing*. https://mapsplatform.google.com/pricing/",
    "Google Cloud. (2026). *Compute Engine pricing*. https://cloud.google.com/compute/all-pricing",
    "International Organization for Standardization. (2013). *ISO/IEC 19510:2013 Information technology — Object Management Group Business Process Model and Notation*. ISO.",
    "International Organization for Standardization. (2021). *ISO/IEC/IEEE 29119-3:2021 Software and systems engineering — Software testing — Part 3: Test documentation*. ISO.",
    "International Organization for Standardization. (2022). *ISO/IEC 27001:2022 Information security, cybersecurity and privacy protection — Information security management systems — Requirements*. ISO.",
    "International Organization for Standardization. (2023). *ISO/IEC 25010:2023 Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — Product quality model*. ISO.",
    "Meta Platforms. (2025). *Pricing on the WhatsApp Business Platform*. https://developers.facebook.com/docs/whatsapp/pricing",
    "Microsoft. (2026). *Linux virtual machines pricing*. https://azure.microsoft.com/pricing/details/virtual-machines/linux/",
    "Obe, R., & Hsu, L. (2021). *PostGIS in action* (3.ª ed.). Manning Publications.",
    "Object Management Group. (2017). *Unified Modeling Language (UML), versión 2.5.1*. https://www.omg.org/spec/UML/2.5.1",
    "OWASP Foundation. (2021a). *Application Security Verification Standard 4.0.3*. https://owasp.org/www-project-application-security-verification-standard/",
    "OWASP Foundation. (2021b). *OWASP Top 10: 2021*. https://owasp.org/Top10/",
    "Pressman, R. S., & Maxim, B. R. (2020). *Software engineering: A practitioner's approach* (9.ª ed.). McGraw-Hill Education.",
    "Richards, M., & Ford, N. (2020). *Fundamentals of software architecture: An engineering approach*. O'Reilly Media.",
    "Schwaber, K., & Sutherland, J. (2020). *The Scrum guide*. https://scrumguides.org/",
    "Sommerville, I. (2016). *Software engineering* (10.ª ed.). Pearson Education.",
    "Twilio. (2026a). *WhatsApp Business API pricing*. https://www.twilio.com/en-us/whatsapp/pricing",
    "Twilio. (2026b). *SMS pricing for Chile*. https://www.twilio.com/sms/pricing/cl",
    "UptimeRobot. (2026). *Pricing*. https://uptimerobot.com/pricing/",
    "World Wide Web Consortium. (2018). *Web Content Accessibility Guidelines (WCAG) 2.1*. https://www.w3.org/TR/WCAG21/",
]


def referencias(r):
    from docx.shared import Cm, Pt
    r.H1("Referencias bibliográficas")
    import re, unicodedata
    def k(x):
        x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode()
        return re.sub(r"[^\w\s]", "", x).lower()
    for ref in sorted(REFS, key=k):
        p = r._new_p("Estilo4")
        r.runs(p, ref)
        pf = p.paragraph_format
        pf.left_indent = Cm(1.27)
        pf.first_line_indent = Cm(-1.27)
        pf.line_spacing = 2.0
        pf.space_after = Pt(0)
        p.alignment = 0
