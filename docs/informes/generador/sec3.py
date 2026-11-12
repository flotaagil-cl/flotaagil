from data_tests import CP
from datos import PRUEBAS

KPI = [
    # id, nombre, objetivo, que mide/relevancia, formula, variables/unidad, fuente, metodo, base, meta, plazo, frecuencia, responsable, umbrales, accion
    ("KPI-01", "Tasa de cumplimiento de reservas", "OE-02 / P1–P3", "Reservas confirmadas que terminan en viaje; mide directamente la pérdida de reservas, causa del 12,1 % de pérdida",
     "(reservas confirmadas del mes en FINALIZADO ÷ reservas confirmadas del mes) × 100", "%; «confirmada» = alcanzó SOLICITADO y ya terminó (FINALIZADO o CANCELADO)", "VIAJE, HISTORIAL_ESTADO", "Consulta automática en el módulo de reportes",
     "87,9 % (planillas jun–ago 2026)", "≥ 95,0 %", "3 meses desde producción", "Mensual", "Administrador; análisis: Juan Pérez", "Verde ≥ 95,0 · Amarillo ≥ 90,0 y < 95,0 · Rojo < 90,0",
     "Revisar las cancelaciones por origen (KPI-08), que son su complemento"),
    ("KPI-02", "Tiempo promedio de asignación", "OE-02 / P2", "Tiempo entre la apertura de la ventana de despacho y la aceptación del conductor; es el cuello de botella del AS-IS",
     "Σ (t_ACEPTADO − t_inicio_ventana) ÷ n", "Minutos; n = viajes aceptados en la semana (n > 0)", "HISTORIAL_ESTADO, ASIGNACION", "Consulta automática",
     "8 min 40 s (45 asignaciones cronometradas)", "< 3,0 min", "1 mes desde producción", "Semanal", "Despachador; análisis: Carlos Ortiz", "Verde < 3,0 · Amarillo ≥ 3,0 y ≤ 5,0 · Rojo > 5,0 min",
     "Revisar disponibilidad en hora punta y tasa de rechazo (KPI-07)"),
    ("KPI-03", "Adopción de la app por conductores", "OE-03", "Conductores que trabajan sus turnos con la app; sin adopción no hay datos para la sugerencia ni la fila",
     "(conductores con ≥ 1 turno iniciado en la semana ÷ conductores activos al cierre de la semana) × 100", "%", "TURNO, CONDUCTOR, USUARIO", "Consulta automática",
     "0 % (no existe app)", "≥ 90,0 %", "4 semanas desde producción", "Semanal", "Administrador", "Verde ≥ 90,0 · Amarillo ≥ 75,0 y < 90,0 · Rojo < 75,0",
     "Capacitación individual y revisión de problemas de dispositivo"),
    ("KPI-04", "Tiempo muerto de la flota", "Objetivo general", "Proporción del turno sin pasajero; refleja el uso de la capacidad productiva",
     "((Σ horas de turno − Σ horas con viaje en ejecución) ÷ Σ horas de turno) × 100", "%; horas de turno = hora_termino − hora_inicio de los turnos terminados en el mes (Σ > 0)", "TURNO, HISTORIAL_ESTADO", "Consulta automática",
     "35 % (bitácora de 3 conductores, 10 jornadas)", "≤ 28,0 %", "3 meses desde producción", "Mensual", "Administrador; análisis: Juan Pérez", "Verde ≤ 28,0 · Amarillo > 28,0 y ≤ 32,0 · Rojo > 32,0",
     "Analizar distribución horaria y uso de la fila del aeropuerto"),
    ("KPI-05", "Exactitud de la cuadratura de caja", "OE-02 / P3.2", "Coincidencia entre el efectivo registrado por viaje y el rendido en el cierre de cada turno; ataca el descuadre de $34.500 diarios",
     "Con R = Σ monto_registrado y D = Σ |monto_rendido − monto_registrado| de los cierres del día: si R > 0, máx(0; 1 − D ÷ R) × 100; si R = 0 y D = 0, 100; si R = 0 y D > 0, 0",
     "%; por día y empresa. Un monto rendido de $0 con R > 0 da 0 %", "CIERRE_CAJA, TURNO, PAGO_VIAJE", "Cierre de caja de cada turno (HU-31)",
     "Por medir en la marcha blanca; referencia ≈ 93,5 % (descuadre de $34.500 sobre ≈ $531.600 diarios)", "≥ 98,0 %", "1 mes desde producción", "Diaria", "Administrador", "Verde ≥ 98,0 · Amarillo ≥ 95,0 y < 98,0 · Rojo < 95,0",
     "Revisar los cierres con diferencia, los viajes cerrados por la central y las correcciones auditadas"),
    ("KPI-06", "Satisfacción del pasajero", "Impacto en clientes (BSC)", "Calidad percibida del servicio",
     "Σ puntajes ÷ n (se informa además la tasa de respuesta)", "Escala 1–5; n = calificaciones del mes (n > 0; sin respuestas no se informa)", "CALIFICACION", "Encuesta por WhatsApp al finalizar",
     "Por medir: primer mes de operación", "≥ 4,30", "3 meses desde producción", "Mensual", "Administrador", "Verde ≥ 4,30 · Amarillo ≥ 3,80 y < 4,30 · Rojo < 3,80",
     "Revisar viajes con nota ≤ 2 y contactar al pasajero"),
    ("KPI-07", "Tasa de rechazo o expiración", "OE-03 / P2", "Asignaciones que el conductor rechaza o deja expirar; anticipa demoras",
     "((RECHAZADAS + EXPIRADAS) ÷ (ACEPTADAS + RECHAZADAS + EXPIRADAS)) × 100", "%; asignaciones enviadas en la semana y ya respondidas o vencidas", "ASIGNACION", "Consulta automática",
     "Por medir: primeras 2 semanas", "< 10,0 %", "1 mes desde producción", "Semanal", "Despachador", "Verde < 10,0 · Amarillo ≥ 10,0 y ≤ 15,0 · Rojo > 15,0",
     "Revisar por conductor y franja; ajustar criterio de sugerencia"),
    ("KPI-08", "Tasa de cancelación de reservas confirmadas", "P1 / P3", "Reservas confirmadas que terminan canceladas, separadas por origen (pasajero, despachador o administrador, supervisor y sistema por no presentación)",
     "(reservas confirmadas del mes en CANCELADO ÷ reservas confirmadas del mes) × 100, desglosado por origen", "%; misma población que KPI-01, por lo que KPI-01 + KPI-08 = 100 %", "VIAJE (origen_cancelacion), HISTORIAL_ESTADO", "Consulta automática",
     "12,1 % (complemento de la línea base de KPI-01)", "≤ 5,0 %", "3 meses desde producción", "Mensual", "Administrador", "Verde ≤ 5,0 · Amarillo > 5,0 y ≤ 10,0 · Rojo > 10,0",
     "Atacar el origen dominante (por ejemplo, no presentación o falta de conductor)"),
    ("KPI-09", "Puntualidad en recogidas del aeropuerto", "Foco aeropuerto (CC-02)", "Recogidas en que el vehículo está en la zona a la hora vigente, ya ajustada por el vuelo",
     "(recogidas desde el aeropuerto con t_EN_ZONA ≤ hora de recogida vigente ÷ recogidas desde el aeropuerto que llegaron a EN_ZONA) × 100", "%", "HISTORIAL_ESTADO, VIAJE, VUELO", "Consulta automática",
     "Por medir: primer mes", "≥ 90,0 %", "3 meses desde producción", "Mensual", "Despachador; análisis: Juan Pérez", "Verde ≥ 90,0 · Amarillo ≥ 80,0 y < 90,0 · Rojo < 80,0",
     "Revisar márgenes de RN-17 y tamaño de la fila"),
]


def kpi_sla(r):
    r.H1("Implementación de los KPI y SLA")
    r.H2("Descripción de KPI")
    r.P("Se mantienen los ocho indicadores de la formulación (sección 2.5) y se agrega KPI-09 por el foco aeropuerto. Todos miden la **mejora del negocio** y no el "
        "avance del desarrollo; el avance se controla con la velocidad de los sprints (capítulo IX). Ninguno ha sido medido aún con el sistema en "
        "operación: las líneas base con valor provienen de la medición manual de junio a agosto de 2026 y las metas son **proyectadas**. Donde no "
        "hay línea base, se indica el procedimiento y el momento de obtenerla. Cada fórmula usa datos que el modelo registra (Figura {F:er}): "
        "los turnos en TURNO, la cuadratura en CIERRE_CAJA, las respuestas en ASIGNACION y las transiciones en HISTORIAL_ESTADO.")
    r.P("**Correcciones tras la EF2.** Las fórmulas se revisaron con cuatro criterios: 1) **misma población** en numerador y denominador; "
        "2) **operaciones agrupadas** de forma explícita; 3) **casos límite definidos**, en especial el denominador cero; y 4) **semáforos con "
        "decimales**, en intervalos cerrados y contiguos, sin valores que queden fuera. Los cambios concretos son: KPI-08 pasa a medir solo "
        "reservas confirmadas, con lo que resulta el complemento exacto de KPI-01; KPI-07 suma rechazos y expiraciones antes de dividir por las "
        "asignaciones resueltas; KPI-05 se define por tramos y usa como denominador el monto registrado, que es el valor esperado del turno; "
        "KPI-03 y KPI-04 se calculan desde la nueva entidad TURNO; y KPI-09 limita su denominador a las recogidas que llegaron a EN_ZONA.")
    r.P("**Objetivo asociado y acción ante desvío.** La {T:kpi_obj} vincula cada KPI con el objetivo que evalúa y la acción prevista cuando el "
        "resultado cae en rojo. **Continuidad con la primera entrega:** se mantienen los nombres, las líneas base medidas y las metas de KPI-01 a KPI-07; "
        "cambia la meta de KPI-08, de menos de 8 % a 5,0 % o menos, para que sea coherente con el 95,0 % de KPI-01. Se conservan además dos "
        "precisiones anteriores: el denominador de KPI-01 son las reservas confirmadas (para no castigar las solicitudes falsas que la verificación "
        "descarta) y KPI-02 parte en la ventana de despacho (para no contar como demora las reservas programadas con días de anticipación).")
    rows = [(k[0], k[2], k[3], k[14]) for k in KPI]
    r.table("kpi_obj", "Objetivo, relevancia y acción de cada KPI", ["ID", "Objetivo", "Qué mide y por qué importa", "Acción si no se cumple"], rows,
            [1.4, 2.8, 6.8, 5.6], font=7.8)

    r.P("La definición operativa completa (fórmula, unidad, fuente, línea base, meta, plazo, frecuencia, responsable y umbrales) está en la {T:kpi} y la justificación SMART de cada indicador en la {T:smart}.")
    r.landscape_on()
    rows = [(k[0], k[1], k[4], k[5], k[6], k[8], k[9], k[10], k[11], k[12], k[13]) for k in KPI]
    r.table("kpi", "Definición operativa de los KPI", ["ID", "Indicador", "Fórmula", "Unidad y condiciones", "Fuente", "Línea base", "Meta", "Plazo", "Frecuencia", "Responsable", "Semáforo"],
            rows, [1.1, 2.0, 4.3, 3.0, 2.0, 2.4, 1.2, 1.6, 1.3, 1.9, 2.4], font=7.0)
    smart = [
        ("KPI-01", "Mide solo reservas confirmadas y terminadas del mes", "Fórmula con datos del sistema", "+7,1 pp: el MVP elimina las dos fuentes de pérdida observadas (transcripción y búsqueda secuencial)", "Ataca el 12,1 % de pérdida (≈ $2,2 M/mes)", "3 meses, mensual"),
        ("KPI-02", "Solo el tramo ventana → aceptación", "Marcas de tiempo automáticas", "La sugerencia evita las 5–10 llamadas; 60 s de respuesta deja margen", "Es el cuello de botella del AS-IS", "1 mes, semanal"),
        ("KPI-03", "Conductores activos de la empresa", "Turnos registrados en TURNO", "Grupo focal favorable; capacitación previa", "Condición para KPI-02, KPI-04 y KPI-09", "4 semanas, semanal"),
        ("KPI-04", "Horas en turno sin viaje", "TURNO y estados con marca de tiempo", "−7 pp (20 % relativo) por asignación más rápida y fila ordenada", "Capacidad productiva de la flota", "3 meses, mensual"),
        ("KPI-05", "Cierres de caja del día por empresa", "CIERRE_CAJA: registrado frente a rendido", "El cobro se registra en el momento; 2 % de tolerancia por errores de digitación", "Descuadre de $1 M/mes sin trazar", "1 mes, diaria"),
        ("KPI-06", "Calificación de viajes finalizados", "Encuesta 1–5 por WhatsApp", "Meta de la formulación, alineada con plataformas de movilidad", "Perspectiva de clientes del BSC", "3 meses, mensual"),
        ("KPI-07", "Respuestas a asignaciones", "Registro ASIGNACION", "Conductores pidieron poder rechazar; 10 % tolera rechazos justificados", "Anticipa demoras de despacho", "1 mes, semanal"),
        ("KPI-08", "Cancelaciones de reservas confirmadas, por origen", "Campo origen_cancelacion", "Es el complemento de KPI-01: 5,0 % equivale a su meta de 95,0 %", "Separa pérdidas evitables de las del cliente", "3 meses, mensual"),
        ("KPI-09", "Recogidas desde aeropuerto", "EN_ZONA vs hora vigente", "El ajuste por vuelo y la fila hacen alcanzable el 90 %", "Valor diferencial del producto", "3 meses, mensual"),
    ]
    r.page_break()
    r.table("smart", "Justificación SMART de cada KPI", ["ID", "Específico", "Medible", "Alcanzable", "Relevante", "Temporal"], smart,
            [1.3, 3.8, 3.4, 6.2, 4.6, 2.9], font=7.0)
    r.landscape_off()
    r.P("**Indicador auxiliar.** Las cuentas de pasajero que se crean y no se activan, porque nadie confirma el teléfono por WhatsApp, no "
        "generan reservas, por lo que no entran en KPI-01 ni en KPI-08. Se miden aparte, con su propia población: *tasa de cuentas no "
        "activadas* = (cuentas de pasajero creadas en el período que no se activan dentro del plazo ÷ cuentas creadas en el período) × 100. No "
        "tiene meta, porque incluye los registros falsos que la verificación debe filtrar; se vigila su tendencia. Desde CC-18 reemplaza a la "
        "tasa de solicitudes no confirmadas, porque el pedido sin cuenta ya no existe.")
    r.P("**Estado en el sistema.** El módulo de reportes construido (HU-06) ya entrega la liquidación por conductor y método de pago, la "
        "facturación por convenio y la tasa de cancelación por origen, esta última sobre todas las reservas del período (DC-29). La separación "
        "de las reservas confirmadas para KPI-08 y el cierre de caja que alimenta a KPI-05 quedaron construidos con HU-31 (CC-12, DC-32).")
    r.P("**Coherencia entre indicadores, modelo de datos y factibilidad económica.** La {T:coher} verifica que las metas, las entidades y los "
        "supuestos económicos usen los mismos valores.")
    r.table("coher", "Coherencia entre KPI, modelo de datos y factibilidad económica", ["Relación", "Verificación", "Dónde"], [
        ("KPI-01 y factibilidad económica", "Meta de 95,0 % ⇒ pérdida residual de 5,0 % ⇒ 76 de 1.512 reservas. La factibilidad usa ese mismo valor: 183 − 76 = 107 reservas recuperadas", "3.1, Tabla {T:benef}"),
        ("KPI-01 y KPI-08", "Comparten población (reservas confirmadas y terminadas): KPI-01 + KPI-08 = 100 %. Metas: 95,0 % y 5,0 %. Línea base: 87,9 % y 12,1 %", "Tabla {T:kpi}"),
        ("KPI-01 y punto de equilibrio del cliente", "Con KPI-01 = 92,3 % (67 reservas recuperadas) el plan Avanzado ya se paga con el margen de los viajes; la meta deja 2,7 puntos de holgura", "3.1"),
        ("KPI-05 y factibilidad económica", "Meta de 98,0 % ⇒ descuadre ≤ 2 % de lo registrado; desde ≈ 6,5 % es una reducción cercana a 70 %. La factibilidad cuenta como beneficio solo el 30 % del descuadre", "3.1"),
        ("KPI-05 y modelo de datos", "CIERRE_CAJA guarda monto_registrado, monto_rendido, diferencia, responsable y fecha, con un cierre por TURNO", "4.4, Anexo F"),
        ("KPI-03, KPI-04 y modelo de datos", "TURNO conserva el inicio y el término de cada jornada, historial que CONDUCTOR.estado sobrescribía", "4.4, Anexo F"),
        ("KPI-07 y modelo de datos", "ASIGNACION.resultado toma ACEPTADA, RECHAZADA o EXPIRADA; las pendientes de respuesta no cuentan", "Anexo F"),
        ("KPI-09 y RN-17", "La hora de recogida vigente es la ajustada por el vuelo (ETA + margen) y confirmada por el despachador", "2.3, HU-27"),
    ], [4.2, 9.6, 2.8], font=8)
    r.H2("Descripción de SLA")
    r.P("Se definen tres servicios. Los SLA están en estado **propuesto**: se revisan con el cliente en la capacitación de la semana 15 y se aprueban "
        "en la UAT (semana 16); la fecha, el lugar y las firmas quedan en el acta de aprobación. El gestor del nivel de servicio es Carlos Ortiz, líder "
        "de la Unidad 2; el cliente es el administrador de la flota.")
    common = [
        ("Información de autorización", "Gestor del nivel de servicio: Carlos Ortiz (FlotaÁgil). Cliente: administrador de la flota. Fecha y lugar: se registran en el acta de UAT (semana 16, Santiago)."),
        ("Estado del documento", "Propuesto (versión 1.1, corregida tras la EF2). Pasa a Revisado tras la sesión con el cliente de la semana 15 y a Aprobado con la firma de la UAT."),
        ("Tiempo del servicio", "24 horas, 7 días (validado con el cliente, EV-08). Mantenimiento programado: primer domingo de cada mes, 03:00–05:00, aviso con 72 h; máximo 2 h al mes, excluidas del cálculo."),
        ("Medición", "UptimeRobot consulta /health (verifica base de datos y Redis) y el handshake WSS cada 5 min desde fuera de AWS; Sentry y CloudWatch complementan. Informe mensual generado por Carlos Ortiz."),
        ("Soporte y escalamiento", "Canal: WhatsApp de soporte y correo soporte@flotaagil.cl. N1: guardia semanal (Renato o Carlos). N2: el otro desarrollador. N3: proveedores (AWS, Twilio). Funcional: administrador de la flota. Tiempos en la {T:prio}."),
        ("Exclusiones", "Mantenimiento programado; caídas de Twilio/Meta, Google o la API de vuelos (el núcleo sigue operando); fallas de conectividad del cliente o de los teléfonos; caída regional de AWS; fuerza mayor."),
        ("Revisión e incumplimiento", "Revisión mensual con el cliente. Si la disponibilidad cae bajo la meta: análisis de causa raíz en 5 días hábiles y plan de acción; propuesta comercial de crédito de 10 % del plan de servicio mensual bajo 99,0 % y de 25 % bajo 97,0 %. El crédito no afecta la licencia de uso."),
    ]
    sla = [
        ("SLA-01 · Despacho y seguimiento en tiempo real", "Administrador y despachadores (panel); conductores (app)",
         "Ver la flota en el mapa, recibir sugerencias, asignar y que el conductor reciba y responda la asignación.",
         "P2 Despacho y asignación; P3 Ejecución del traslado", "Crítica. Activos: EC2, contenedores api/ws/redis/db, app del conductor, datos de VIAJE, ASIGNACION y POSICION_GPS.",
         "≥ 99,0 % mensual: en un mes de 30 días (720 h), el 1 % equivale a un máximo de 7 h 12 min de indisponibilidad no programada.",
         "No disponible si /health falla en dos consultas consecutivas, si el handshake WSS falla o si el login responde error 5xx durante 5 min o más.",
         "Latencia GPS p95 < 5 s; API p95 < 2 s; asignación entregada a la app en < 2 s; con hasta 50 conductores en turno y 10 usuarios del panel.",
         "RTO 2 h; RPO 6 h, sostenido por snapshots y respaldos lógicos (pg_dump) cada 6 h, alternados con 3 h de desfase (8.2)."),
        ("SLA-02 · Reservas y comunicación con pasajeros", "Pasajeros, supervisores de convenio y despachadores",
         "Que el pasajero solicite, confirme y reciba avisos de su viaje, y que el despachador atienda su conversación.",
         "P1 Recepción y confirmación; P3 (avisos)", "Alta. Activos: portal, módulo de mensajería, webhook, cuenta de Twilio, plantillas aprobadas.",
         "≥ 99,0 % mensual del portal y del webhook propio (la entrega de WhatsApp depende de Meta y se excluye).",
         "No disponible si el portal o el webhook responden error durante 5 min o más.",
         "Formulario procesado en < 2 s; aviso encolado en < 5 s desde el cambio de estado; mensaje entrante visible en el panel en 15 s o menos (revisión periódica).",
         "RTO 2 h; RPO 6 h; mensajes no enviados se reintentan al restablecer."),
        ("SLA-03 · Administración y reportes", "Administrador de la flota",
         "Mantener flota y convenios, consultar auditoría y emitir liquidaciones y reportes.",
         "P3.2 Cuadratura; gestión de convenios", "Media. Activos: módulos Flota, Convenios, Cobros y reportes, Auditoría.",
         "≥ 99,0 % mensual (mismo cálculo; comparte infraestructura).", "No disponible si el panel no permite generar la liquidación durante 15 min o más.",
         "Liquidación diaria en < 5 s; exportación CSV de un mes en < 15 s.", "RTO 4 h (no bloquea la operación); RPO 6 h."),
    ]
    for i, s in enumerate(sla):
        pairs = [("Nombre del servicio", s[0]), ("Cliente / usuarios", s[1]), ("Descripción y resultado deseado", s[2]), ("Procesos que apoya", s[3]),
                 ("Criticidad y activos esenciales", s[4]), ("Meta de disponibilidad", s[5]), ("Condición de no disponible", s[6]),
                 ("Metas de capacidad y desempeño", s[7]), ("Continuidad (restablecimiento)", s[8])]
        if i == 0:
            pairs += common
        else:
            pairs += [("Autorización, estado, horario, medición, soporte, exclusiones y revisión", "Iguales a SLA-01.")]
        r.kv_table(f"sla{i + 1}", s[0], pairs, widths=(4.0, 12.6), font=8)
    r.P("**Coherencia con infraestructura, presupuesto y equipo.** El 99,0 % es alcanzable con una sola instancia si la recuperación automática de "
        "EC2 y el reinicio de contenedores resuelven la mayoría de las fallas en minutos; un incidente mayor (hasta el RTO de 2 h) consume menos de un tercio del presupuesto mensual de 7 h 12 min, "
        "lo que deja margen para incidentes menores. El RPO de 6 h es coherente con el respaldo: tanto los snapshots como los pg_dump se toman cada 6 h (CC-14). Comprometer 99,5 % o más exigiría una segunda instancia, base de datos gestionada y balanceador "
        "(≈ USD 60 adicionales al mes) y guardia 24/7 profesional, fuera del alcance del MVP. La guardia semanal de dos personas es viable para "
        "una sola flota y se revisa si se suman clientes.")


def pruebas_normas(r):
    r.H1("Plan de Pruebas y Aseguramiento de Calidad")
    r.H2("Plan de Pruebas")
    r.P("**Objetivo:** verificar que cada incremento cumple los criterios de aceptación de las HU, las reglas de negocio y los RNF, y validar con el "
        "cliente que la solución resuelve el problema antes del paso a producción. **Alcance:** backend (API, WebSocket, tareas), panel, portal, app "
        "del conductor, integraciones con Twilio, API de vuelos y Google Maps, base de datos, infraestructura de respaldo. **Atributos evaluados:** "
        "adecuación funcional, desempeño, seguridad, usabilidad, compatibilidad y recuperabilidad (ISO/IEC 25010). **Exclusiones justificadas:** la "
        "entrega efectiva de WhatsApp en redes de Meta (fuera de control; se prueba hasta la API de Twilio), pruebas en iOS (la app es solo Android) y "
        "pruebas de penetración profesionales (fuera de presupuesto; se reemplazan por OWASP ZAP y revisión de permisos).")
    tipos = [
        ("Unitarias", "Reglas de dominio, máquina de estados, cálculo de sugerencias, validaciones", "pytest, Vitest", "Developers", "Cada commit (CI)", "Errores de lógica, RN-01 a RN-20"),
        ("Integración", "API + BD + Redis; webhook; adaptadores con respuestas simuladas", "pytest-django, servicios en CI", "Carlos", "Cada PR", "Contratos entre componentes"),
        ("Concurrencia", "Peticiones simultáneas reales sobre PostgreSQL: asignación (CP-14) y renovación de sesión", "pytest con transacciones reales, hilos y barrera", "Carlos", "Sprint 4, semana 14 (CP-14); la de sesión, desde el Sprint 1", "RN-02, RN-03, integridad"),
        ("Contrato con terceros", "Twilio (sandbox) y API de vuelos con credenciales reales", "pytest, respuestas grabadas", "Carlos", "Semana 14–15", "R-04, R-12, cambios del proveedor"),
        ("End-to-end", "Flujos P1, P2 y P3 en el navegador, en escritorio y a 390 px", "Playwright", "Renato", "Al cierre de cada historia (stack local); en staging desde la semana 15", "Regresiones de interfaz"),
        ("Humo", "Salud, login, WSS, reserva de prueba", "Script en Actions", "Carlos", "Cada despliegue", "Despliegues fallidos"),
        ("Regresión", f"Suite completa automatizada ({PRUEBAS} pruebas al corte)", "GitHub Actions", "Automática", "Cada PR a main", "Efectos colaterales"),
        ("Carga y estrés", "50 usuarios REST y 50 conductores WSS; rampa hasta el quiebre", "k6", "Carlos", "Semana 15, en staging", "RNF-02, RNF-03"),
        ("Seguridad", "OWASP ZAP, Bandit, auditoría de dependencias, permisos por rol y empresa", "ZAP, Bandit, Dependabot", "Carlos", "Bandit y permisos en cada historia; ZAP en la semana 15", "OWASP Top 10, RN-13"),
        ("Usabilidad y accesibilidad", "Tareas con una mano (SUS); contraste y teclado del portal (WCAG 2.1 AA)", "Guion, SUS, axe", "Renato", "Semanas 15–16", "RNF-06, R-05"),
        ("Compatibilidad y consumo", "Android 10 a 15 en 3 teléfonos; datos y batería en un turno", "Dispositivos reales", "Renato", "Semanas 14–16", "R-01, R-03, RNF-07"),
        ("Recuperación", "Restaurar dump y snapshot en staging, medir RTO y RPO, y aplicar la carga diferida", "Procedimientos PO-02 y PO-06", "Carlos", "Semana 15 y mensual", "RNF-08, R-09"),
        ("Alfa", "Uso del sistema completo por el equipo y el PO con datos simulados", "Staging", "Equipo + PO", "Semana 15", "Defectos integrales"),
        ("Beta (marcha blanca)", "Operación real con un grupo de conductores, en paralelo a la planilla", "Producción", "Equipo + cliente", "Semanas 15–16", "Adopción, KPI-05"),
        ("Aceptación (UAT)", "Guion por rol con criterios de aceptación", "Producción", "Cliente (A)", "Semana 16", "Aceptación formal"),
    ]
    r.table("tipos", "Tipos de prueba, alcance y justificación", ["Tipo", "Qué se prueba", "Herramienta", "Responsable", "Cuándo", "Riesgo o requisito que cubre"], tipos,
            [2.4, 4.6, 2.5, 2.0, 2.4, 2.7], font=7.6)
    r.P("**Ambientes y datos.** Desarrollo e integración continua usan contenedores efímeros de PostgreSQL/PostGIS y Redis; ahí corrieron las "
        "pruebas unitarias, de integración y de extremo a extremo de los cuatro sprints. **Datos de prueba:** generados con factory_boy "
        "(empresas, 50 conductores, 4.536 viajes de tres meses, 3 convenios) y rutas GPS simuladas; nunca datos personales reales. "
        "**Roles:** Carlos es responsable de las pruebas de backend, concurrencia, carga, seguridad y recuperación; Renato de frontend, app, "
        "usabilidad y compatibilidad; Juan Pérez aprueba los resultados de cada sprint y el cliente la UAT.")
    r.P("**Entorno de staging.** Las pruebas de carga, estrés, seguridad y recuperación exigen un ambiente equivalente a producción. Para no "
        "tener que extrapolar resultados, el staging es **idéntico a producción** ({T:staging}): se lanza con la misma plantilla y solo se "
        "enciende durante las ventanas de prueba, lo que cuesta ≈ USD 0,017 por hora (menos de USD 1 por las jornadas previstas, dentro del "
        "presupuesto de infraestructura del proyecto). Como el tipo de instancia, el disco, las imágenes y los límites de memoria son los "
        "mismos, el p95 medido en staging se compara directamente con RNF-02 y RNF-03. Las únicas diferencias son los datos (sintéticos) y los "
        "servicios externos (sandbox de Twilio y clave de pruebas de vuelos), que no forman parte de lo que mide la carga.")
    r.table("staging", "Configuración del entorno de staging frente a producción", ["Elemento", "Producción", "Staging", "Efecto en los resultados"], [
        ("Instancia", "EC2 t4g.small (2 vCPU Graviton2, 2 GiB), us-east-1a", "Igual", "Ninguno: misma capacidad"),
        ("Disco", "EBS gp3 30 GB, 3.000 IOPS, cifrado", "Igual", "Ninguno"),
        ("Software", "Ubuntu 24.04 ARM64, Docker, 7 contenedores", "Mismas imágenes (misma etiqueta y SHA) y el mismo compose", "Ninguno"),
        ("Límites por contenedor", "PostgreSQL 512 MB, Gunicorn 2 workers, Daphne 150 MB, Celery 250 MB, Redis 128 MB", "Iguales", "Ninguno"),
        ("Datos", "Reales del cliente", "Sintéticos: 3 meses (4.536 viajes) y 50 conductores", "Volumen equivalente al caso de diseño"),
        ("Servicios externos", "Twilio y AeroAPI productivos", "Sandbox de Twilio y clave de pruebas", "Fuera de la medición: se encolan en Celery"),
        ("Generador de carga", "—", "k6 desde un equipo fuera de AWS, por Internet y con TLS", "Incluye la latencia de red real (≈ 130 ms)"),
        ("Disponibilidad", "24/7", "Solo en las ventanas de prueba", "Reduce el costo, no la validez"),
    ], [3.0, 4.6, 4.8, 4.2], font=7.8)
    r.P("**Calendario y dependencias.** Las pruebas unitarias, de integración y de extremo a extremo se ejecutaron con cada historia durante los "
        "cuatro sprints. Quedan para el cierre del Sprint 4 y la semana 15 las que dependen de algo que todavía no existe: concurrencia rediseñada (CP-14, semana 14), "
        "contrato con servicios reales (cuando estén las credenciales), teléfono real (guía de prueba), y carga, estrés, seguridad y "
        "recuperación (semana 15, con el staging en AWS). Usabilidad, consumo, beta y UAT requieren producción y capacitación (semanas 15 y 16). "
        "**Criterios de entrada:** HU que cumple la DoR, código fusionado con CI en verde y ambiente disponible. **Criterios de salida:** 100 % de "
        "los casos de prioridad Alta ejecutados y aprobados, ≥ 90 % de los de prioridad Media, cobertura ≥ 70 % en módulos de negocio y ningún "
        "defecto crítico o alto abierto.")
    sev = [
        ("Crítica", "Bloquea un proceso principal o compromete datos o seguridad", "Se corrige antes de cerrar el sprint; bloquea el despliegue"),
        ("Alta", "Una HU no cumple un criterio de aceptación sin alternativa", "Se corrige en el sprint; bloquea la UAT"),
        ("Media", "Falla con alternativa razonable", "Se planifica en el sprint siguiente"),
        ("Baja", "Cosmética o de texto", "Se agrega al backlog"),
    ]
    r.P("**Gestión de defectos.** Cada defecto se registra como *issue* de GitHub con la plantilla «Defecto» (pasos, resultado esperado y obtenido, "
        "evidencia, severidad, versión), se enlaza al caso de prueba y a la HU, se corrige en una rama con prueba de regresión y se cierra solo cuando "
        "el caso vuelve a ejecutarse y aprueba. Las evidencias (capturas, reportes de CI, salidas de k6 y ZAP) se guardan en /docs/evidencias del "
        "repositorio y se enlazan desde el caso.")
    r.table("sev", "Severidad de defectos y tratamiento", ["Severidad", "Criterio", "Tratamiento"], sev, [2.4, 7.0, 7.2], font=8)
    r.P("**Casos de prueba.** Se diseñaron 45 casos que cubren flujos principales, alternativos y excepciones, datos inválidos y valores límite, "
        "permisos por rol y empresa, integración con servicios externos, integridad y persistencia, rendimiento y concurrencia, seguridad, "
        "usabilidad, recuperación y aceptación. La {T:cp_res} los resume; el Anexo G contiene cada caso con objetivo, precondiciones, datos, pasos, "
        "resultado esperado, prioridad, responsable y los campos de resultado obtenido, estado y evidencia. CP-36 y CP-37 se agregaron con las "
        "historias HU-31 y HU-32, incorporadas al Sprint 4, y CP-38 a CP-45 con las historias de CC-16 a CC-18 (HU-33 a HU-45).")
    r.P("**Rediseño de CP-14 (concurrencia).** La versión anterior asignaba un viaje a un conductor que ya tenía otro: probaba la regla RN-03, "
        "pero una asignación después de la otra, sin competencia real. El caso se rediseñó con **simultaneidad real** en dos variantes: A) dos "
        "despachadores asignan **la misma reserva** a conductores distintos; B) dos despachadores asignan **el mismo conductor** a reservas "
        "distintas. En ambas, dos hilos preparan su petición HTTP y una barrera las libera en el mismo instante contra el PostgreSQL real, sin "
        "transacción envolvente, y la prueba se repite 50 veces por variante para cubrir los distintos entrelazados. El resultado esperado es "
        "que exactamente una petición responda 200 y la otra 409, con una sola ASIGNACION y sin errores 5xx. El mecanismo que lo garantiza ya "
        "está construido: la asignación toma un bloqueo de fila (SELECT … FOR UPDATE) sobre la reserva y sobre el conductor dentro de una "
        "transacción y revalida el estado después de obtenerlo, de modo que la segunda petición espera, ve la reserva ya asignada (o al "
        "conductor ya ocupado) y es rechazada. La técnica de prueba es la misma que ya verifica la renovación concurrente de la sesión. **Resultado "
        "(semana 14):** en ambas variantes una petición respondió 200 y la otra 409, con una sola ASIGNACION. La prueba además dejó a la vista "
        "un riesgo de interbloqueo: la recepción de posiciones tomaba los bloqueos en el orden inverso (conductor y luego viaje), lo que se "
        "corrigió con un bloqueo consultivo.")
    r.P("**Estado de ejecución al corte (semana 14).** Se ejecutaron 37 casos: los 27 de las historias de los cuatro sprints (CP-01 a CP-27), "
        "CP-36 y CP-37 de las historias de la EF2 y CP-38 a CP-45 de las historias de CC-16 a CC-18. De ellos, 30 son conformes y 7 conformes de "
        "forma parcial, porque dependen de servicios reales (Twilio, API de vuelos), de un teléfono real o de carga con 50 conductores. Los 8 "
        "restantes (CP-28 a CP-35) se ejecutan en staging, en el teléfono de pruebas o en la UAT. Los resultados y la evolución de las pruebas "
        "automáticas se presentan en el Anexo P y en el Anexo G.")
    rows = [(c[0], c[1], c[2], c[3], c[8], c[10]) for c in CP]
    r.table("cp_res", "Resumen de casos de prueba", ["ID", "Requisito", "Tipo", "Objetivo", "Prioridad", "Sprint"], rows, [1.4, 2.6, 3.0, 6.6, 1.5, 1.5], font=7.6)

    r.H2("Normas y Estándares")
    r.P("La {T:normas} identifica las normas, marcos y obligaciones que se incorporan, distinguiendo su naturaleza: **norma** (documento "
        "técnico consensuado y publicado por un organismo de normalización), **marco de trabajo**, **buena práctica** y **obligación legal**. En "
        "ningún caso se busca certificación: el proyecto aplica prácticas de las normas y lo evidencia, lo que no equivale a estar certificado.")
    normas = [
        ("ISO/IEC 25010:2023 (calidad del producto)", "Norma", "Clasificar los RNF y orientar las pruebas por característica", "Modelo de calidad del producto (características y subcaracterísticas)", "RNF, plan de pruebas", "Renato", "Tabla {T:rnf} y Tabla {T:tipos}"),
        ("ISO/IEC/IEEE 29119-3:2021 (documentación de pruebas)", "Norma", "Estructurar plan, casos e informes de prueba", "Plan de prueba, especificación de casos, registro de incidentes de prueba", "Plan de pruebas, Anexo G", "Carlos", "Anexo G; issues de defectos"),
        ("ISO/IEC 27001:2022 Anexo A", "Norma (adopción parcial de controles)", "Proteger datos de pasajeros y conductores", "A.5.15 control de acceso, A.8.13 respaldo, A.8.15 registro, A.8.24 criptografía, A.8.25 desarrollo seguro, A.5.24 gestión de incidentes", "Arquitectura, operación", "Carlos", "Configuración, auditoría, procedimientos de 8.2–8.3"),
        ("ISO/IEC 19510:2013 (BPMN 2.0.2) y UML 2.5.1 (OMG)", "Norma / especificación", "Notación común y revisable de procesos y diseño", "Elementos de colaboración, eventos, compuertas; diagramas de casos de uso y componentes", "Capítulo III", "Renato", "Figuras {F:p1} a {F:comp|n}"),
        ("OWASP ASVS 4.0.3 (nivel 1) y OWASP Top 10:2021", "Buena práctica", "Verificar seguridad de la aplicación web y API", "V2 autenticación, V3 sesiones, V4 control de acceso, V5 validación, V7 registro", "Backend, portal", "Carlos", "CP-10, CP-22, CP-23, CP-31; DoD"),
        ("WCAG 2.1 nivel AA (W3C)", "Buena práctica (recomendación W3C)", "Portal usable por cualquier pasajero", "Contraste, etiquetas de formulario, navegación por teclado", "Portal de solicitud", "Renato", "Reporte axe"),
        ("Scrum Guide 2020", "Marco de trabajo", "Gestión iterativa del desarrollo", "Roles, eventos y artefactos", "Gestión del proyecto", "Carlos (SM)", "Tablero y actas de review"),
        ("ITIL 4 (prácticas de servicio)", "Marco de trabajo", "Operación del servicio tras la entrega", "Gestión de disponibilidad, continuidad, configuración, cambios e incidentes", "Capítulo VI", "Carlos", "Registros de cambios e incidentes"),
        ("Conventional Commits, SemVer 2.0, PEP 8 / ESLint", "Buena práctica", "Historial legible y versiones trazables", "Formato de commits, versionado mayor.menor.parche, estilo de código", "Repositorio", "Ambos", "Historial de Git, linters en CI"),
        ("Ley 17.336 (propiedad intelectual)", "Obligación legal", "Proteger el software y definir qué recibe el cliente", "El programa computacional es obra protegida; se otorga una licencia de uso no exclusiva e intransferible, sin cesión de derechos ni entrega del código fuente", "Modelo comercial, contrato de licencia", "Equipo", "Sección 3.1; cláusulas del contrato de licencia"),
        ("Ley 21.719 (protección de datos personales) y Ley 19.628", "Obligación legal", "Tratar datos de pasajeros y conductores", "Licitud y finalidad, información al titular, minimización, seguridad, derechos de acceso/rectificación/supresión, transferencia internacional con garantías", "Portal, app, base de datos", "Renato", "Aviso de privacidad, RN-15, RN-18, RNF-09"),
        ("Código del Trabajo, arts. 5 y 154; Dictamen DT Ord. N° 148 (26-01-2022)", "Obligación legal", "Geolocalización de conductores dependientes", "Medidas de control incluidas en el Reglamento Interno, idóneas y proporcionales, sin vigilancia permanente", "App del conductor", "Cliente (empleador), con apoyo del equipo", "Cláusula sugerida para el reglamento; GPS solo en turno"),
        ("DS 212/1992 del MTT", "Obligación legal (del cliente)", "Reglamento de los servicios de transporte público de pasajeros, que incluye taxis de turismo", "El sistema registra patente y licencia profesional; no reemplaza las obligaciones de inscripción ni de revisión técnica", "Módulo Flota", "Cliente", "Campos de VEHICULO y CONDUCTOR"),
        ("Ley 21.553 (empresas de aplicación de transporte)", "Obligación legal (análisis de aplicabilidad)", "Descartar que FlotaÁgil sea una EAT", "La ley regula plataformas que intermedian entre pasajeros y conductores independientes; FlotaÁgil es una herramienta interna de una empresa con flota registrada", "Modelo de negocio", "Equipo", "Este análisis; revisión si se abre a conductores externos"),
        ("Políticas de WhatsApp Business y de Google Play", "Obligación contractual", "Mantener habilitados los canales", "Opt-in del usuario, plantillas aprobadas; declaración de ubicación en segundo plano", "Mensajería, app", "Carlos / Renato", "Opt-in en PASAJERO; formulario de Play"),
    ]
    r.landscape_on()
    r.table("normas", "Normas, marcos y obligaciones incorporados", ["Norma y edición", "Naturaleza", "Motivo", "Apartados o prácticas adoptadas", "Afecta a", "Responsable", "Evidencia"], normas,
            [4.0, 2.4, 3.4, 5.4, 2.6, 2.2, 3.4], font=6.9,
            source="Elaboración propia con base en International Organization for Standardization (2013, 2021, 2022, 2023), Object Management Group (2017), OWASP Foundation (2021a, 2021b), World Wide Web Consortium (2018), Schwaber y Sutherland (2020), Axelos (2019), Biblioteca del Congreso Nacional de Chile (1970, 1992, 1999, 2023, 2024) y Dirección del Trabajo (2022).")
    r.landscape_off()
    r.P("**Ámbito y limitaciones de la adopción.** De ISO/IEC 27001 se adoptan controles del Anexo A pertinentes a una aplicación SaaS pequeña, sin "
        "implementar un sistema de gestión completo (alcance, evaluación formal de riesgos, auditorías internas). De ISO/IEC/IEEE 29119-3 se usa la "
        "estructura documental, no el proceso organizacional de la serie. La Ley 21.719 entra en vigencia el 1 de diciembre de 2026, durante el "
        "período de operación; el diseño ya cumple sus principios para no requerir cambios. La evidencia del consentimiento ya existe en los datos: el pasajero acepta el aviso de privacidad una vez al crear su cuenta, con fecha y versión (DC-44), y puede eliminar su cuenta (derecho de supresión, HU-45); el conductor acepta el registro de su ubicación al iniciar su primer turno (RN-18) y las posiciones se eliminan a los 30 días con una tarea programada (RN-15). Respecto de la **Ley 21.553**, al corte de este informe su reglamento aún no se publica y la ley rige 30 días después de esa publicación; aun si llegara a aplicarse, el sistema ya registra los datos que la ley exige al operador (conductor con licencia profesional, vehículo con patente y año), por lo que el impacto se limitaría a reportes. **Coherencia:** cada norma se traduce en un requisito "
        "verificable (RNF, regla o caso de prueba) y en una práctica de operación del capítulo VIII, por lo que su cumplimiento se evidencia con los "
        "mismos artefactos del proyecto.")
