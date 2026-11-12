import os
"""Capítulo II · Formulación del proyecto: contenido del Informe 1 integrado y actualizado al estado vigente."""
import sec1

F1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "recursos", "inf1img", "")


def formulacion(r):
    r.H1("Formulación del proyecto")
    r.P("Este capítulo integra la formulación aprobada en la primera entrega (Informe 1, 09/09/2026) y la actualiza con los cambios aprobados "
        "después del acta de validación del backlog y con lo aprendido durante la construcción. Donde un dato cambió, se indica el valor vigente "
        "y la solicitud de cambio (CC) o la decisión de cambio (DC) que lo respalda.")

    # ------------------------------------------------------------------ 2.1 organización
    r.H2("La organización")
    r.H3("Descripción de la organización")
    r.P("El proyecto se aborda bajo la modalidad de internalización a una empresa: se entrega una solución de software a una empresa cliente del "
        "rubro del taxi turismo para digitalizar sus procesos operativos y administrativos. Sus aspectos organizacionales son los siguientes:")
    r.bullets([
        "**Tipo y rubro:** empresa privada de servicios (PYME) de transporte de pasajeros y turismo, con vehículos de patente naranja. Opera como "
        "transportista autorizado en el aeropuerto internacional de Santiago, que es el origen o destino de cerca del 40 % de sus viajes (EV-08).",
        "**Posicionamiento:** organización con trayectoria local orientada a traslados desde y hacia el aeropuerto, hoteles y clientes corporativos "
        "con convenio. Compite por puntualidad, seguridad y trato personalizado.",
        "**Tamaño:** flota de 30 a 50 vehículos y alrededor de 1.500 reservas mensuales; la central opera las 24 horas, todos los días.",
        "**Estructura:** jerárquica plana. Del administrador (dueño o gerente) dependen Administración y Finanzas, Operaciones (despachadores) y el "
        "grupo de conductores.",
        "**Misión:** brindar un servicio de transporte privado y turístico seguro, cómodo y puntual, que satisfaga al pasajero en cada trayecto.",
        "**Visión:** ser la flota de taxi turismo preferida y más confiable de la región, reconocida por su excelencia operativa.",
        "**Cadena de valor, actividades primarias:** recepción de reservas particulares y corporativas, asignación y despacho, ejecución del "
        "traslado, venta de convenios a empresas y agencias, y atención al pasajero. **Actividades de apoyo:** mantenimiento de la flota y gestión "
        "de conductores.",
        "**Cuadro de mando integral:** perspectiva financiera (reducir viajes perdidos y tiempos muertos), clientes (menor espera), procesos internos "
        "(digitalizar reserva, despacho y cuadratura) y aprendizaje (adopción de herramientas móviles por el personal).",
        "**Normativa del rubro:** servicios de transporte de pasajeros regulados por el Ministerio de Transportes y Telecomunicaciones (DS 212/1992), "
        "revisión técnica al día y seguros obligatorios de pasajeros.",
        "**Unidades afectadas:** Operaciones y Despacho (gestión de la flota) y Administración y Finanzas (control de cobros y convenios).",
    ])

    r.H3("Justificación de la elección de la organización")
    r.P("La elección responde a criterios técnicos y de pertinencia frente a los estándares actuales del transporte de pasajeros ({T:just}).")
    just = [
        ("Brecha digital verificable", "El taxi turismo gestiona su operación con planillas y mensajería, mientras las plataformas de movilidad urbana operan con despacho asistido y trazabilidad total. La brecha permite un impacto medible."),
        ("Pertinencia frente a estándares", "La geolocalización en tiempo real, el registro digital de transacciones y la trazabilidad del servicio son la línea base del sector; la organización no cumple ninguno."),
        ("Escenario greenfield", "No hay sistemas heredados que integrar, por lo que se aplica una arquitectura cloud moderna (API-first, comunicación en tiempo real, preparada para varias empresas)."),
        ("Escala representativa", "30 a 50 vehículos y más de 1.500 transacciones mensuales exigen resolver concurrencia, procesamiento geoespacial y comunicación bidireccional, sin exceder la capacidad del equipo."),
        ("Viabilidad del levantamiento", "La estructura plana da acceso directo al administrador, a los despachadores y a los conductores."),
        ("Replicabilidad", "El problema es estructural del sector, lo que habilita el modelo SaaS para varias empresas y el uso del producto más allá del caso de estudio."),
        ("Consideración ética", "El proyecto trata datos personales de pasajeros y la ubicación de trabajadores, lo que obliga a aplicar minimización, finalidad y límites al monitoreo (Ley N° 19.628, modificada por la Ley N° 21.719)."),
    ]
    r.table("just", "Criterios de elección de la organización", ["Criterio", "Fundamentación"], just, [4.0, 12.6], font=8.5, first_col_bold=True)

    r.H3("Arquitectura tecnológica y de aplicaciones actual")
    r.P("La organización tiene un nivel de madurez tecnológica bajo y no cuenta con arquitectura empresarial formal ({T:tec_actual}).")
    tec = [
        ("Infraestructura", "Sin servidores propios ni servicios cloud contratados; sin dominio ni correo corporativo."),
        ("Equipamiento", "Dos equipos de escritorio en la central (Windows 10, ofimática básica); conductores con teléfonos personales sin gestión."),
        ("Conectividad", "Banda ancha doméstica en la central, sin enlace de respaldo; conductores con datos móviles propios."),
        ("Software de gestión", "No existe software de flota, ERP, CRM ni sistema de despacho."),
        ("Respaldos", "Planillas guardadas en un solo equipo, sin versionado ni copia externa."),
        ("Seguridad", "Sin control de acceso por usuario, cifrado ni auditoría; datos de pasajeros en mensajería personal."),
        ("Geolocalización", "Inexistente: la ubicación de un vehículo se conoce solo si el conductor la informa."),
    ]
    r.table("tec_actual", "Situación tecnológica previa a la intervención", ["Dimensión", "Situación documentada"], tec, [3.6, 13.0], font=8.5, first_col_bold=True)
    r.figure(F1 + "img-018.png", "apps_asis", "Arquitectura de aplicaciones actual (AS-IS)", width_cm=15)
    r.P("El despachador es el único punto de integración entre herramientas desconectadas: la información se transcribe a mano entre WhatsApp, la "
        "planilla y el cuaderno, sin una fuente única de datos. La {F:apps_asis} muestra esta situación.")

    r.H3("Antecedentes de la organización")
    r.table("antec", "Evolución de la problemática", ["Situación en el pasado", "Situación actual"], [
        ("Con una flota pequeña y pocos clientes, la gestión con cuadernos, llamadas y radio era suficiente y los errores eran fáciles de corregir.",
         "El crecimiento de la demanda y de la flota hizo colapsar el uso de WhatsApp y Excel: se pierden reservas, no se conoce la ubicación de los "
         "vehículos y la caja no cuadra."),
    ], [8.3, 8.3], font=8.5)

    r.H3("Tipo de organización y arquitectura empresarial")
    r.P("La organización es una empresa privada de transporte turístico de pasajeros con estructura jerárquica plana: **gerencia y administración** "
        "(decisiones estratégicas, control financiero y convenios), **operaciones** (recepción, agendamiento y asignación de servicios; en el sistema es "
        "un rol distinto del administrador aunque en la práctica la misma persona pueda cumplir ambos) y **conductores** (ejecución del traslado y "
        "registro del cobro). El proceso primario abordado es la logística externa y las operaciones de la cadena de valor.")
    r.P("La intervención modifica las cuatro capas de la arquitectura empresarial: en **negocio** formaliza el despacho y sus estados; en "
        "**aplicación** introduce el primer sistema de información de la organización; en **datos** crea una fuente única de verdad; y en "
        "**tecnología** incorpora infraestructura cloud sin inversión local.")

    # ------------------------------------------------------------------ 2.2 problema
    r.H2("Identificación del problema")
    r.H3("Diagnóstico de la situación actual y análisis de causas")
    r.P("La asignación es ineficiente: el despachador contacta a los conductores uno por uno para conocer su disponibilidad y ubicación, porque no "
        "existe geolocalización centralizada. Esto produce viajes perdidos, tiempos muertos, un pasajero sin información sobre su traslado y una "
        "cuadratura diaria compleja, porque la mayoría de los viajes se cobran en efectivo al conductor sin registro central. Para ir más allá de los "
        "síntomas se aplicó un diagrama de causa y efecto (Ishikawa) con seis categorías ({F:ishikawa}).")
    r.figure(F1 + "img-021.png", "ishikawa", "Diagrama de causa y efecto (Ishikawa) del problema operativo", width_cm=16)
    r.P("El problema no se origina en la falta de esfuerzo del personal, sino en **tres causas raíz tecnológicas**: la ausencia de una fuente única "
        "de datos, la falta de trazabilidad geográfica de la flota y la inexistencia de un registro digital del cobro. Son exactamente las tres "
        "capacidades que prioriza el MVP. El proceso actual se modela en BPMN 2.0 en la sección 4.1 (Figura {F:asis|n}).")

    r.H3("Descripción del problema")
    r.P("Las empresas de taxi turismo pierden reservas por la gestión manual, no tienen trazabilidad de sus conductores, asignan los viajes de forma "
        "ineficiente y no tienen métricas del negocio. El pasajero no sabe cuándo llega su vehículo ni recibe avisos, y en los traslados desde el "
        "aeropuerto los atrasos de vuelos obligan a reprogramar las recogidas a mano. Los cobros en efectivo al conductor complican la cuadratura si "
        "no se registran el método de pago y el monto.")

    r.H3("Alcance y restricciones del problema")
    r.table("alc_prob", "Límites del problema abordado", ["Dimensión", "Dentro del problema", "Fuera del problema"], [
        ("Proceso", "Reserva, despacho, ejecución del viaje, registro del cobro y seguimiento de vuelos de los pasajeros", "Mantenimiento vehicular, contratación de personal y contabilidad tributaria"),
        ("Actores", "Administrador, despachador, conductor, pasajero particular y supervisor de convenio", "Proveedores, talleres, aseguradoras y fiscalizadores"),
        ("Geografía", "Operación de una empresa en la Región Metropolitana, con foco en el aeropuerto", "Operación multirregional o interurbana de larga distancia"),
        ("Tiempo", "Operación diaria, 24/7", "Planificación estratégica y expansión de la flota"),
        ("Organizacional", "Baja madurez digital del personal, que exige interfaces simples", "Programas de transformación digital de mayor envergadura"),
        ("Tecnológica", "Sin infraestructura local: solución cloud sin hardware propietario", "Integración con taxímetros homologados o GPS dedicados"),
        ("Económica", "Presupuesto de PYME, sin inversión en licencias corporativas", "Modelos que exijan una inversión inicial significativa del cliente"),
    ], [2.6, 7.0, 7.0], font=8.2, first_col_bold=True)

    r.H3("Relevancia del problema y evidencia cuantitativa")
    r.P("Se midió el registro histórico de junio a agosto de 2026, contrastando las planillas de reservas con el cuaderno de caja ({T:evid_q}). Estas "
        "cifras son la línea base de los KPI del capítulo V.")
    r.table("evid_q", "Evidencia cuantitativa del problema (jun–ago 2026)", ["Indicador", "Valor", "Fuente", "Impacto estimado"], [
        ("Reservas ingresadas (promedio mensual)", "1.512", "Planillas Excel de la central", "Volumen base de la operación"),
        ("Reservas perdidas o no ejecutadas", "12,1 % (183/mes)", "Reservas anotadas versus viajes en caja", "≈ $2.196.000 mensuales"),
        ("Tiempo muerto de la flota", "35 % de la jornada", "Bitácora de 3 conductores, 10 jornadas", "Un tercio menos de capacidad productiva"),
        ("Tiempo promedio de asignación", "8 min 40 s", "Cronometraje de 45 asignaciones", "Espera del pasajero y riesgo de fuga"),
        ("Descuadre de caja diario", "$34.500", "Cuaderno de caja versus efectivo rendido", "≈ $1.035.000 mensuales sin trazabilidad"),
        ("Errores de transcripción", "7,4 %", "Auditoría de 300 registros", "Reservas duplicadas o direcciones erróneas"),
        ("Reservas corporativas", "22 %", "Clasificación de planillas", "Segmento sin canal digital"),
    ], [4.6, 2.6, 4.8, 4.6], font=8.2)
    r.P("La solución proyecta bajar la pérdida de reservas a 5,0 % o menos, la asignación a menos de 3 minutos y el tiempo muerto a 28 % o menos. "
        "Los $2.196.000 son ingreso bruto: el efecto sobre la rentabilidad se calcula con el margen neto de esos viajes en la sección 3.1.")

    r.H3("Complejidad del problema")
    r.P("La complejidad está en orquestar eventos concurrentes y datos en tiempo real: actualizar la ubicación de 30 a 50 vehículos que envían su "
        "posición cada 5 a 10 segundos (≈ 300 mensajes por minuto en hora punta), administrar la máquina de estados de más de 1.500 viajes mensuales, "
        "integrar servicios externos que fallan o responden lento (WhatsApp vía Twilio y datos de vuelos) sin bloquear al usuario, y comunicar el "
        "panel y la app de forma bidireccional mediante WebSocket, con una disponibilidad comprometida de 99,0 % (CC-06).")

    # ------------------------------------------------------------------ 2.3 levantamiento
    r.H2("Levantamiento de requerimientos")
    r.H3("Plan e instrumentos de levantamiento")
    r.P("El levantamiento se hizo en tres etapas durante las semanas 1 a 4, más una entrevista de seguimiento ({T:plan_lev}). Las pautas están en el "
        "Anexo B y las evidencias, en el Anexo C.")
    r.table("plan_lev", "Plan de levantamiento ejecutado", ["Etapa", "Instrumento", "Participantes", "Duración", "Evidencia"], [
        ("1. Exploración", "Entrevista semiestructurada al administrador", "Dueño de la flota", "60 min", "EV-01"),
        ("1. Exploración", "Entrevista semiestructurada al despachador", "Despachador con 4 años de antigüedad", "45 min", "EV-02"),
        ("2. Contraste", "Grupo focal con conductores", "3 conductores de distintos turnos", "50 min", "EV-03"),
        ("2. Contraste", "Observación directa en la central", "Observador no participante", "2 jornadas de 4 h", "EV-04"),
        ("3. Validación", "Análisis documental de planillas y caja", "Registros de junio a agosto de 2026", "300 registros", "EV-05, EV-06"),
        ("3. Validación", "Validación del backlog con el cliente", "Administrador y equipo", "40 min", "EV-07 (acta 28/08/2026)"),
        ("4. Seguimiento", "Entrevista sobre la operación en el aeropuerto", "Administrador y despachador", "55 min", "EV-08 (02/09/2026)"),
    ], [2.4, 4.8, 4.2, 2.2, 3.0], font=8.2)

    r.H3("Resultados del levantamiento")
    r.P("Los hallazgos se agruparon por categoría, se contó su frecuencia de mención y cada necesidad se trazó a la historia que la responde "
        "({T:res_lev}).")
    r.table("res_lev", "Hallazgos sistematizados y su trazabilidad", ["Categoría", "Hallazgo", "Menciones", "Necesidad derivada", "HU"], [
        ("Visibilidad de flota", "No se conoce la ubicación sin llamar al conductor", "5 de 5", "Mapa de la flota en tiempo real", "HU-02"),
        ("Asignación", "Buscar un conductor libre es lento y depende de la memoria", "4 de 5", "Sugerencia del conductor más apto", "HU-04, HU-29"),
        ("Registro de reservas", "Las reservas se pierden o duplican al transcribirlas", "5 de 5", "Registro digital único", "HU-03, HU-19"),
        ("Cobros", "No se sabe cuánto se recaudó hasta el cierre", "3 de 5", "Método y monto por viaje", "HU-16, HU-06"),
        ("Clientes corporativos", "Las empresas con convenio llaman por cada traslado", "2 de 5", "Canal digital para convenios", "HU-11, HU-25"),
        ("Experiencia del pasajero", "El pasajero llama para saber si el vehículo viene", "4 de 5", "Avisos de estado por WhatsApp", "HU-21, HU-30"),
        ("Operación del conductor", "Leer el viaje en WhatsApp obliga a hacerlo conduciendo", "3 de 3", "Notificación con aceptación explícita", "HU-14, HU-15"),
        ("Autonomía del conductor", "No hay forma formal de rechazar un viaje", "3 de 3", "Rechazo con reasignación", "HU-15"),
        ("Respaldo del conductor", "No hay registro propio de los viajes del turno", "2 de 3", "Historial del turno en la app", "HU-18"),
        ("Aeropuerto (EV-08)", "Los atrasos de vuelos obligan a reprogramar a mano", "2 de 2", "Seguimiento de vuelos y ajuste de recogida", "HU-26, HU-27"),
        ("Aeropuerto (EV-08)", "El turno de salida en el aeropuerto se resuelve de palabra", "2 de 2", "Fila virtual por orden de llegada", "HU-29"),
    ], [3.0, 5.4, 1.6, 4.2, 2.4], font=8)

    sec1.requerimientos(r)

    # ------------------------------------------------------------------ 2.4 marco teórico
    r.H2("Marco teórico")
    r.H3("Investigación bibliográfica")
    r.P("El proyecto se fundamenta en ingeniería de software, arquitecturas distribuidas y computación en la nube, con citas en formato APA 7:")
    r.bullets([
        "**Ciclo de vida y metodología:** ciclo iterativo e incremental con Scrum. Las metodologías ágiles permiten adaptarse a cambios de "
        "requerimientos mediante entregas continuas (Pressman y Maxim, 2020); Schwaber y Sutherland (2020) definen roles, eventos y artefactos; la "
        "dirección del proyecto se apoya en el PMI (2021).",
        "**Ingeniería de requerimientos:** la calidad del producto depende de la precisión del levantamiento (Sommerville, 2016), lo que justifica "
        "varios instrumentos complementarios y la trazabilidad explícita entre necesidades e historias.",
        "**Arquitectura de software:** los atributos de calidad guían las decisiones de arquitectura desde la formulación (Bass et al., 2021); "
        "Richards y Ford (2020) aportan criterios para arquitecturas distribuidas, bajo los cuales se adopta un diseño API-first.",
        "**Computación en la nube:** la definición del NIST caracteriza el modelo SaaS y su elasticidad, sin infraestructura local para el cliente "
        "(Mell y Grance, 2011).",
        "**Información geográfica:** PostGIS permite almacenar y consultar datos geoespaciales con índices espaciales (Obe y Hsu, 2021), base de la "
        "geocerca y del cálculo de proximidad.",
        "**Tiempo real:** el protocolo WebSocket (Fette y Melnikov, 2011) permite comunicación bidireccional persistente, base de la transmisión de "
        "posiciones y estados.",
        "**Aplicaciones híbridas:** empaquetar una aplicación web como aplicación instalable reduce el esfuerzo frente al desarrollo nativo "
        "(Griffith, 2017), marco de la elección de Capacitor.",
        "**Seguridad y protección de datos:** OWASP Top 10 y ASVS (OWASP Foundation, 2021a, 2021b), ISO/IEC 27001:2022 y la Ley N° 21.719, que "
        "moderniza la Ley N° 19.628 y regula el tratamiento de los datos de pasajeros y conductores.",
    ])

    r.H3("Estado del arte")
    r.P("Se analizaron siete alternativas del mercado nacional e internacional ({T:arte}).")
    r.table("arte", "Soluciones de gestión y despacho de flotas", ["Solución", "Origen", "Modelo", "Hardware propio", "Segmento", "Limitación para el caso"], [
        ("Nexo (GTG)", "Chile", "Licencia e instalación local", "Sí", "Radiotaxis medianos y grandes", "Inversión inicial e instalación local incompatibles con una PYME"),
        ("Taxicab", "Chile", "Cliente-servidor", "Parcial", "Radiotaxis tradicionales", "Orientado al taxi urbano; sin convenios ni traslados programados"),
        ("Autocab", "Reino Unido", "SaaS", "No", "Operadores grandes", "Licencia en moneda extranjera; sobredimensionado para 30–50 vehículos"),
        ("iCabbi", "Irlanda", "SaaS", "No", "Flotas medianas y grandes", "Sin presencia ni soporte en Chile; interfaz no localizada"),
        ("Onde", "Letonia", "SaaS", "No", "Nuevos operadores de movilidad", "Centrado en el pasajero tipo ride-hailing; despachador marginal"),
        ("Apps genéricas de flota", "Varios", "SaaS", "No", "Transporte ejecutivo", "Sin reserva por convenio ni cuadratura de efectivo"),
        ("Planillas y mensajería", "—", "Local y manual", "No", "Microempresas", "Es la situación actual que se busca reemplazar"),
        ("**FlotaÁgil**", "Chile", "SaaS", "No", "PYMES de taxi turismo", "Diseñada para el nicho: aeropuerto con seguimiento de vuelos, convenios, WhatsApp y cobro en efectivo"),
    ], [2.6, 1.5, 2.3, 1.6, 3.0, 5.6], font=7.8)
    r.P("Las soluciones nacionales exigen hardware propietario y las internacionales están dimensionadas para operadores grandes. Ninguna modela "
        "las particularidades del nicho: la reserva por convenio, la conciliación del efectivo, el seguimiento de vuelos con ajuste de la recogida y "
        "el WhatsApp como canal natural del pasajero. FlotaÁgil se ubica en esa brecha.")

    # ------------------------------------------------------------------ 2.5 solución y objetivos
    r.H2("Solución propuesta y objetivos")
    r.H3("Formulación de la solución")
    r.P("La solución se formula sobre cinco atributos de calidad:")
    r.bullets([
        "**Disponibilidad y continuidad:** infraestructura cloud con disponibilidad de 99,0 % 24/7 y snapshots y respaldos lógicos cada 6 h (RPO de 6 h).",
        "**Rendimiento:** WebSocket para posiciones y estados en vivo, y tareas en segundo plano (Celery) para que los servicios externos no hagan "
        "esperar al usuario.",
        "**Seguridad:** JWT con renovación segura para los usuarios internos, acceso por link y contraseña para los convenios, verificación del "
        "pasajero por WhatsApp, cifrado en tránsito y control de acceso por rol y por empresa.",
        "**Integración:** arquitectura API-first con WhatsApp Business API (Twilio), datos de vuelos (FlightAware AeroAPI) y mapas.",
        "**Usabilidad:** interfaces por perfil; en la app del conductor, operación con una mano y pocas interacciones por viaje.",
    ])

    r.H3("Diagrama de contexto")
    r.figure("fig/contexto.png", "contexto", "Diagrama de contexto del sistema", width_cm=15.5)
    r.P("La frontera del sistema ({F:contexto}) deja fuera la definición de tarifas, la facturación tributaria y el mantenimiento de la flota, que "
        "siguen a cargo de la organización.")

    r.H3("Alcance de la solución")
    r.P("**Dentro del alcance:** reserva desde el panel, el portal público, el link de convenio y WhatsApp; verificación del pasajero por WhatsApp; "
        "despacho asistido con confirmación humana; fila virtual del aeropuerto; seguimiento de vuelos con ajuste de la recogida; ejecución del viaje "
        "con estados y geocerca; registro del cobro; avisos y calificación por WhatsApp; chat con el pasajero desde el panel; reportes y auditoría.")
    r.P("**Fuera del alcance:** pasarelas de pago, definición de tarifas, facturación electrónica, aplicación nativa para pasajeros, despacho "
        "automático con inteligencia artificial, chatbot, enmascaramiento telefónico, aislamiento completo entre empresas y cuentas individuales "
        "para trabajadores de convenios.")

    r.H3("Modelo conceptual de datos")
    r.P("El dominio se organiza en torno a las entidades de la {T:conceptual}; su implementación física está en la sección 4.4 y el Anexo F. "
        "Turno y Cierre de caja se agregaron tras la EF2, porque el modelo original no permitía medir la cuadratura ni los indicadores por turno.")
    r.table("conceptual", "Entidades conceptuales del dominio", ["Entidad", "Descripción", "Relaciones principales"], [
        ("Empresa", "Organización dueña de la flota que usa la plataforma", "Agrupa usuarios, conductores, vehículos, convenios y su configuración"),
        ("Usuario", "Persona con acceso interno, diferenciada por rol", "Pertenece a una empresa; opera reservas y asignaciones"),
        ("Conductor", "Operario en ruta que ejecuta los traslados", "Pertenece a una empresa; usa uno o más vehículos; ejecuta viajes"),
        ("Vehículo", "Móvil habilitado para el servicio", "Se asocia a conductores; uno se declara activo por turno"),
        ("Convenio", "Acuerdo con una empresa cliente para reservas corporativas", "Origina viajes; sus cambios se auditan"),
        ("Pasajero", "Solicitante del traslado, particular o de convenio", "Origina viajes; se verifica por WhatsApp"),
        ("Vuelo", "Vuelo asociado a una recogida en el aeropuerto", "Ajusta la hora de recogida de un viaje; genera alertas"),
        ("Turno", "Jornada de un conductor con un vehículo, con su inicio y su término (CC-12)", "Pertenece a un conductor; agrupa sus viajes y cobros; se cuadra con un cierre de caja"),
        ("Cierre de caja", "Cuadratura de un turno: lo registrado frente a lo rendido (CC-12)", "Uno por turno; lo realiza un administrador"),
        ("Viaje", "Traslado desde la solicitud hasta el cierre", "Vincula pasajero, conductor y vehículo; concentra estados, pago, mensajes y calificación"),
    ], [2.6, 6.4, 7.6], font=8.2, first_col_bold=True)

    r.H3("Lista formal de entregables")
    r.table("entregables", "Entregables comprometidos y su estado", ["Código", "Entregable", "Fase", "Criterio de aceptación", "Estado (semana 14)"], [
        ("E-01", "Informe de formulación", "1", "Aprobado por el académico guía", "Entregado (Informe 1)"),
        ("E-02", "Product Backlog priorizado y estimado", "1", "Validado con el cliente (acta)", "Validado (EV-07); vigente en Anexo A"),
        ("E-03", "Modelos AS-IS y TO-BE", "1", "Revisados por el despachador", "Actualizados en BPMN 2.0 (4.1)"),
        ("E-04", "Documento de arquitectura", "2", "Consistente con el backlog", "Completo (capítulo IV), corregido tras la EF2"),
        ("E-05", "Modelo de datos y script de creación", "2", "3FN y validado con datos de prueba", "Implementado (migraciones Django); TURNO y CIERRE_CAJA en el Sprint 4"),
        ("E-06", "Prototipos de interfaz", "2", "Validados con usuarios", "Reemplazados por pantallas funcionales"),
        ("E-07", "Backend con API REST y canal WebSocket", "3", "HU de prioridad alta superan sus pruebas", "Construido: 25 HU en revisión (Sprint 4 en curso); 1.066 pruebas"),
        ("E-08", "Panel web administrativo", "3–4", "Criterios de las HU del panel", "Construido, en revisión"),
        ("E-09", "Portal público y acceso de convenios", "3–4", "Criterios de HU-19, HU-20, HU-25", "Construido, en revisión (HU-19, 20, 11 y 25)"),
        ("E-10", "App del conductor (APK)", "3–4", "Criterios de HU-13 a HU-18 en dispositivo real", "Funcional en emulador y navegador; falta la prueba en teléfono"),
        ("E-11", "Plan y evidencia de pruebas UAT", "5", "Sin defectos críticos abiertos", "Plan listo (6.1); UAT en la semana 16"),
        ("E-12", "Manual de usuario y capacitación", "5", "Sesión ejecutada y registrada", "Pendiente (semana 15)"),
        ("E-13", "Sistema desplegado", "5", "Accesible con TLS vigente", "Pendiente (semana 15; ambiente local en uso)"),
    ], [1.3, 4.6, 1.0, 4.6, 5.1], font=7.8)

    r.H3("Impacto de la solución y registro de interesados")
    r.P("El proceso afectado es la logística externa y las operaciones de la cadena de valor: la solicitud del pasajero se conecta con el despacho "
        "asistido y la ejecución en ruta, y el control administrativo se centraliza en una plataforma. La {T:interesados} registra a los "
        "interesados y la {F:poder} los prioriza según poder e interés.")
    r.table("interesados", "Registro de interesados", ["Interesado", "Influencia", "Interés", "Expectativas", "Estrategia"], [
        ("Dueño / administrador", "Alta", "Alto", "Control de la operación, reportes exactos y rentabilidad", "Gestionar de cerca; demo en cada Sprint Review"),
        ("Despachador", "Media", "Alto", "Sistema rápido, mapa al día y asignación simple", "Mantener informado; pruebas de usabilidad"),
        ("Conductores", "Media", "Alto", "App estable, bajo consumo, avisos claros, poder rechazar", "Grupo focal y UAT en dispositivo real"),
        ("Pasajeros", "Baja", "Medio", "Saber cuándo llega el vehículo y contacto simple", "Monitorear con la calificación del servicio"),
        ("Supervisor de convenio", "Media", "Medio", "Reservar de forma simple y segura", "Mantener informado; validar el acceso por link"),
        ("Product Owner", "Alta", "Alto", "Incrementos que aporten valor al cliente", "Aprueba incrementos y cambios de alcance"),
        ("Equipo de proyecto", "Alta", "Alto", "Alcance claro y requerimientos estables", "Eventos Scrum y control de cambios"),
        ("Académico guía", "Alta", "Alto", "Rigor metodológico y estándares de titulación", "Reportes de avance y revisiones"),
    ], [3.2, 1.7, 1.4, 5.2, 5.1], font=8)
    r.figure(F1 + "img-076.png", "poder", "Mapa de poder e interés de los interesados", width_cm=12.5)

    r.H3("Objetivos del proyecto")
    r.P("**Objetivo general:** desarrollar e implementar un MVP SaaS, compuesto por una plataforma web y una aplicación móvil interconectadas, que "
        "optimice la reserva, el despacho, la geolocalización y el registro de cobros de una empresa de taxi turismo.")
    r.table("oe", "Objetivos específicos y su avance", ["ID", "Objetivo específico", "Resultado verificable", "Avance (semana 14)"], [
        ("OE-01", "Diseñar la arquitectura y el modelo de datos relacional, preparado para varias empresas, asegurando integridad, seguridad y escalabilidad",
         "Documento de arquitectura y modelo de datos (E-04, E-05)", "Cumplido: modelo implementado con separación por empresa; ampliado con TURNO y CIERRE_CAJA (CC-12)"),
        ("OE-02", "Desarrollar el panel web, el portal público y el módulo de convenios con API REST y frameworks web modernos",
         "Panel y portal que cumplen sus HU", "Construido y en revisión: panel, portal y convenios completos"),
        ("OE-03", "Construir la app híbrida del conductor con Capacitor, con geolocalización en segundo plano y WebSocket",
         "APK que cumple HU-13 a HU-18 en dispositivo real", "Construido y en revisión: ciclo completo del viaje, fila y «Mi turno»; falta la validación en teléfono"),
        ("OE-04", "Validar la solución con pruebas de aceptación y de rendimiento, cumpliendo los criterios de disponibilidad y seguridad",
         "Informe de UAT sin defectos críticos (E-11)", "En curso: 1.746 pruebas automáticas; carga y seguridad en la semana 15; UAT en la 16"),
    ], [1.3, 6.2, 4.2, 4.9], font=8)

    # ------------------------------------------------------------------ 2.6 metodología
    r.H2("Metodología de trabajo")
    r.P("Se aplica Scrum con sprints de dos semanas; su selección, roles y eventos se justifican en la sección 3.1 ({T:roles}). Aquí se detallan las "
        "reglas de trabajo, la estimación, la estructura del trabajo, el equipo, los recursos y los riesgos.")
    r.H3("Definition of Ready y Definition of Done")
    r.P("**Definition of Ready.** Una historia entra a un sprint solo si: está redactada como «Como [rol], quiero [acción], para [beneficio]»; tiene "
        "criterios de aceptación verificables; fue estimada con planning poker; no tiene dependencias bloqueantes; sus servicios externos están "
        "identificados; tiene diseño de interfaz si crea una pantalla; cabe en un sprint; y fue priorizada por el Product Owner.")
    r.P("**Definition of Done.** Un incremento está terminado cuando: el código está versionado y en una rama con pull request; la integración "
        "continua está en verde; se cumplen todos los criterios de aceptación; hay pruebas automáticas con cobertura ≥ 70 % en los módulos afectados; "
        "se probó manualmente contra el backend real con evidencia guardada en el repositorio (capturas y resultados); no hay vulnerabilidades OWASP "
        "detectables por análisis estático; la documentación (API OpenAPI, modelo de datos, diccionario de cambios) está al día; y no quedan defectos "
        "críticos o altos abiertos. La historia pasa a «En revisión» en el tablero hasta que el Product Owner la aprueba.")

    r.H3("Estimación de esfuerzo y planificación")
    r.P("Se estimó con planning poker sobre Fibonacci, con HU-17 (navegación externa) = 3 SP ≈ 5 h como referencia (≈ 1,7 h por punto). Con dos "
        "desarrolladores a 25 h semanales y un factor de foco de 75 %, la capacidad es de 75 h por sprint, unos **45 SP**. El backlog vigente suma "
        "**178 SP** en cuatro sprints (45, 45, 42 y 46 SP), con la semana 16 reservada para UAT y paso a producción. La ejecución "
        "real y el ajuste del plan se presentan en el capítulo IX.")

    r.H3("Estructura de desglose del trabajo")
    r.figure("fig/edt.png", "edt", "Estructura de desglose del trabajo (EDT)", width_cm=16)
    r.P("Cada paquete de tercer nivel de la {F:edt} es asignable, estimable y verificable, y se vincula con los entregables de la {T:entregables}.")

    r.H3("Equipo de trabajo y liderazgo")
    r.P("El equipo de desarrollo lo forman dos integrantes, con autorización del académico guía; el rol de Product Owner lo cumple Juan Pérez para "
        "efectos de la metodología (CC-09). El rol de líder de proyecto, exigido por la asignatura, rota entre los integrantes: Renato González en la "
        "Unidad 1 (análisis y formulación) y Carlos Ortiz en la Unidad 2 (diseño y construcción). El líder se relaciona con el docente, controla el "
        "avance, asigna el trabajo, convoca las reuniones y reporta el cumplimiento de cada integrante. Las responsabilidades técnicas son: Renato "
        "González, frontend web y aplicación móvil; Carlos Ortiz, backend, base de datos e infraestructura. Por indicación del académico guía, en "
        "Scrum no se usa matriz RACI: las responsabilidades las definen los roles.")

    r.H3("Plan de recursos")
    r.P("El equipo dispone de su capital humano, dos estaciones de trabajo y un teléfono Android para pruebas de campo. Para la puesta en marcha se "
        "requieren la instancia AWS, las APIs externas (WhatsApp vía Twilio, datos de vuelos y mapas), la licencia de Google Play y el dominio con su "
        "certificado. El presupuesto comercial original del desarrollo, valorizado a precios del mercado chileno, se resume en la {T:presup}; al "
        "definir el proveedor cloud se actualizó a **$14.047.000** y se agregó el costo mensual de operación (sección 3.1 y Anexo J).")
    r.table("presup", "Presupuesto comercial original del desarrollo (16 semanas)", ["Categoría", "Detalle", "Costo (CLP)"], [
        ("Personal", "Dos desarrolladores a $1.500.000 mensuales cada uno, por cuatro meses", "$12.000.000"),
        ("Equipamiento", "Arriendo y depreciación de dos estaciones de trabajo y un teléfono de prueba", "$600.000"),
        ("Infraestructura cloud", "Instancia AWS con PostgreSQL/PostGIS y Redis para pruebas y producción inicial", "$400.000"),
        ("Licencias y APIs", "Mapas, WhatsApp vía Twilio, datos de vuelos y licencia de Google Play", "$150.000"),
        ("Bienes y servicios", "Dominio .cl y certificado TLS", "$30.000"),
        ("Imprevistos (10 %)", "Tipo de cambio, consumo de APIs sobre lo proyectado y requerimientos emergentes", "$1.318.000"),
        ("**Total**", "", "**$14.498.000**"),
    ], [3.6, 10.0, 3.0], font=8.5)

    riesgos(r)


def riesgos(r, heading=True, estado=True):
    if heading:
        r.H3("Matriz de riesgos")
    r.P("Cada riesgo se valora por probabilidad e impacto (1 a 5) y su exposición es el producto de ambos ({T:riesgos_full}). Los de exposición ≥ 12 "
        "se revisan en cada retrospectiva." + (" El estado refleja lo ocurrido hasta el corte de este informe." if estado else ""))
    rows = [
        ("R-01", "El GPS en segundo plano no opera de forma estable en Android", "4", "5", "20", "Mitigar: prueba de concepto H-3 adelantada; contingencia en primer plano", "Mitigado en emulador (Anexo M); falta prueba en teléfono real"),
        ("R-02", "La velocidad real es menor a 45 SP por sprint", "4", "4", "16", "Mitigar: medir al cierre del Sprint 1 y repriorizar", "No ocurrió: los Sprints 1 a 3 completaron 45, 45 y 42 SP; el cierre del Sprint 4 y la puesta en marcha se controlan en horas (9.1)"),
        ("R-03", "El sistema operativo degrada la precisión de la ubicación", "3", "4", "12", "Mitigar: descartar lecturas con precisión > 50 m y marcar posiciones antiguas", "Mitigado: filtro de precisión (DC-16)"),
        ("R-04", "Costo de mensajería mayor a lo presupuestado", "3", "3", "9", "Mitigar: WhatsApp en vez de SMS y límites de envío", "Bajó con CC-01"),
        ("R-05", "Baja adopción de la app por los conductores", "3", "4", "12", "Mitigar: grupo focal, UAT y capacitación", "Abierto: se evalúa en la UAT"),
        ("R-06", "Cambio en las condiciones de Google Maps", "2", "4", "8", "Aceptar: mapa base alternativo sin clave", "Mitigado: el panel funciona sin clave de Google"),
        ("R-07", "Filtración de la contraseña de un convenio", "3", "3", "9", "Transferir y mitigar: rotación y desactivación inmediata", "Mitigado: contraseña generada y rotable, bloqueo tras 5 intentos y auditoría (HU-11, HU-25)"),
        ("R-08", "Ampliación no controlada del alcance", "3", "4", "12", "Evitar: acta y control de cambios", "Controlado: 15 CC y 30 DC registrados"),
        ("R-09", "Pérdida de disponibilidad durante la UAT", "2", "4", "8", "Mitigar: respaldos cada 6 h y restauración probada", "Abierto: simulacro en la semana 15 (CP-30)"),
        ("R-10", "Indisponibilidad de un integrante", "3", "4", "12", "Mitigar: documentación y revisión cruzada", "Mitigado: documentación por historia en el repositorio"),
        ("R-11", "Evidencia del levantamiento insuficiente", "2", "3", "6", "Mitigar: repositorio de evidencias fechadas", "Mitigado"),
        ("R-12", "Mensajes de WhatsApp fuera de la ventana de 24 h sin plantilla aprobada", "3", "4", "12", "Mitigar: plantillas aprobadas por Meta antes de producción", "Abierto: ver 7.7 y 9.1"),
        ("R-13", "La API de vuelos falla o cambia de precio", "2", "4", "8", "Mitigar: reintentos y vuelo «sin verificar» que no bloquea la reserva", "Mitigado en el diseño implementado"),
        ("R-14", "Google Play rechaza la ubicación en segundo plano", "3", "3", "9", "Mitigar: distribución directa de la APK mientras se tramita", "Abierto"),
        ("R-15", "Restricción de la cuenta de GitHub de un integrante por detección automática de spam", "2", "3", "6", "Mitigar: solicitud de revisión; el otro integrante abre los PR; respaldo del repositorio", "Materializado: el repositorio se migró con su historial completo a una nueva organización de GitHub (Flotaagil-CL), donde la integración continua vuelve a ejecutarse"),
        ("R-17", "El margen neto real por viaje es distinto del supuesto (25 %)", "3", "3", "9", "Mitigar: sensibilidad de 15 % a 30 % en la factibilidad; validar con el cliente antes de la UAT", "Abierto: supuesto declarado (3.1)"),
        ("R-18", "La fusión de los pull requests o el despliegue en AWS se retrasan y comprimen la UAT", "3", "4", "12", "Mitigar: fusión como primera tarea de lo que resta del Sprint 4; plan en horas con holgura", "Abierto (9.1)"),
        ("R-16", "Consumo de batería de la app del conductor", "3", "3", "9", "Mitigar: GPS cada 30 s en turno en vez de 1 Hz", "Mitigado en la app base; medir en teléfono real"),
        ("R-19", "Reclamo o fiscalización por el tratamiento de la ubicación de los conductores", "2", "4", "8", "Mitigar: GPS solo en turno, consentimiento, cláusula en el Reglamento Interno, purga a 30 días y acceso por rol", "Mitigado en el diseño implementado (RN-15, RN-18)"),
        ("R-20", "Cambio normativo del transporte de pasajeros (reglamento de la Ley 21.553 u otra exigencia del MTT)", "2", "3", "6", "Aceptar y monitorear: revisión semestral de la normativa; datos de conductor y vehículo ya registrados", "Abierto: reglamento sin publicar al corte"),
    ]
    if estado:
        r.table("riesgos_full", "Matriz de riesgos y estado", ["ID", "Riesgo", "P", "I", "Exp.", "Respuesta", "Estado (semana 14)"], rows,
                [1.1, 4.0, 0.6, 0.6, 0.9, 4.4, 5.0], font=7.6)
    else:
        keep = [x for x in rows if x[0] not in ("R-15", "R-18")]
        r.table("riesgos_full", "Matriz de riesgos", ["ID", "Riesgo", "P", "I", "Exp.", "Respuesta"], [x[:-1] for x in keep],
                [1.2, 6.0, 0.7, 0.7, 1.0, 7.0], font=7.8)
