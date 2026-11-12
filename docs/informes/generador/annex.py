from data_backlog import HU, RETIRADAS, SPRINTS, RESP, NUEVAS
from data_cu import CU
from data_tests import CP
from datamodel import E, REL
from datos import DC_MAX


def AH(r, title):
    """Título de anexo (nivel 2 dentro de X. Anexos)."""
    r.page_break()
    p = r.H2(title, numbered=False)
    return p


def anexos(r):
    r.H1("Anexos")
    r.P("Los anexos forman una sola serie, con letras en el orden en que se citan en el cuerpo del informe, e integran los de la formulación "
        "(backlog, instrumentos y evidencias del levantamiento, glosario y máquina de estados), actualizados.")
    idx = [("A", "Product Backlog vigente y estado de cada historia", "2.3, 9.1"),
           ("B", "Instrumentos de levantamiento", "2.3"),
           ("C", "Evidencias del levantamiento y entrevista de seguimiento (EV-08)", "1.1, 2.3"),
           ("D", f"Registro de solicitudes de cambio (CC-01 a CC-21) y decisiones de cambio (DC-01 a DC-{DC_MAX})", "1.1, 1.3, VII, 8.3"),
           ("E", "Especificación de casos de uso", "4.2"), ("F", "Diccionario de datos", "4.4"),
           ("G", "Casos de prueba y resultado de su ejecución", "6.1, VII"),
           ("H", "Máquina de estados del viaje", "1.1, 4.1"), ("I", "Matriz de trazabilidad", "2.3, X"),
           ("J", "Respaldo de costos, modelo comercial, punto de equilibrio, flujo de caja a tres años (VAN, TIR y PRI) y matrices de decisión", "2.6, 3.1"), ("K", "Glosario", "Transversal"),
           ("L", "Procedimientos operativos (PO-01 a PO-07) y formularios", "8.1–8.3"),
           ("M", "Informe técnico de la prueba de concepto de GPS en segundo plano (H-3)", "2.6, VII"),
           ("N", "Ecosistema de desarrollo implementado (Sprint 0)", "VII, IX"),
           ("O", "Requerimientos, reglas de negocio, parámetros y matriz de riesgos vigentes", "1.1, 3.1, 9.1"),
           ("P", "Desarrollo e implementación de la solución por sprint (evidencias, pruebas y defectos)", "1.1, 6.1, 9.1")]
    r.table("idx_anx", "Índice de anexos", ["Anexo", "Contenido", "Citado en"], idx, [1.6, 10.6, 4.4], font=8.5)

    # ---------------- A
    r.landscape_on()
    AH(r, "Anexo A. Product Backlog vigente")
    r.P("Historias vigentes con criterios de aceptación, prioridad, estimación (story points, planning poker sobre Fibonacci con HU-17 = 3 SP "
        "como referencia), sprint asignado, cambio respecto del backlog validado el 28/08/2026 y estado de construcción al corte de la semana 14. Las 25 "
        "historias de los cuatro sprints están construidas e integradas en la rama principal; las dos de la {T:backlog_n} se incorporaron al "
        "Sprint 4 tras la EF2. HU-11, HU-19, HU-20 y HU-25 se muestran en su versión vigente, ajustada por CC-16 y CC-18.")
    NOTA = {"HU-24": "; el promedio por conductor se ve en HU-06", "HU-18": "; guarda solo el último turno (pasa a TURNO con HU-31)",
            "HU-27": "; aviso al pasajero pendiente (PR-14)", "HU-26": "; vuelos de salida fuera del MVP (PR-08)"}
    def est(h):
        return h[7] + "\n**Construida e integrada**" + NOTA.get(h[0], "")
    rows = [(h[0], h[1], h[2], h[3], h[4], str(h[5]), h[6].replace("S", "Sprint ") + "\n" + RESP.get(h[0], "Carlos"), est(h)) for h in HU]
    r.table("backlog", "Product Backlog vigente", ["ID", "Épica", "Historia de usuario", "Criterios de aceptación", "Prior.", "SP", "Sprint y resp.", "Estado"], rows,
            [1.3, 2.0, 6.0, 7.2, 1.3, 0.9, 1.6, 2.7], font=7.4)
    rows = [(h[0], h[1], h[2], h[3], h[4], str(h[5]), h[6].replace("S", "Sprint ") + "\n" + ("Renato" if h[0] == "HU-31" else "Carlos"), h[7] + "\n**Construida e integrada**") for h in NUEVAS]
    r.table("backlog_n", "Historias incorporadas tras la EF2", ["ID", "Épica", "Historia de usuario", "Criterios de aceptación", "Prior.", "SP", "Sprint y resp.", "Estado"], rows,
            [1.3, 2.0, 6.0, 7.2, 1.3, 0.9, 1.9, 2.4], font=7.4)
    from data_hu_cc import HU_CC
    r.P("Las historias de la {T:backlog_cc} nacen de las solicitudes de cambio CC-16 a CC-18, aprobadas por el Product Owner en la semana 14 "
        "(Anexo D). HU-33 a HU-44 se construyeron en el Sprint 4, y HU-45 (perfil y eliminación de la cuenta) se adelantó desde la versión 1.1 "
        "porque responde a un derecho del titular de los datos (Ley N° 21.719). HU-46 a HU-49 quedan para la versión 1.1, después de la UAT, para "
        "no comprometer la puesta en marcha.")
    rows = [(x[0], x[1], x[2], x[3], x[4], x[5], x[6], "**" + x[7] + "**") for x in HU_CC]
    r.table("backlog_cc", "Historias incorporadas por las solicitudes de cambio CC-16 a CC-18", ["ID", "Épica", "Historia de usuario", "Criterios de aceptación", "SP", "Origen", "Resp.", "Estado"], rows,
            [1.3, 2.0, 6.0, 7.6, 0.9, 1.3, 1.6, 2.6], font=7.2)
    rows = [(x[0], x[1], x[2], str(x[3])) for x in RETIRADAS]
    r.table("retiradas", "Historias retiradas", ["ID", "Historia original", "Motivo", "SP liberados"], rows, [1.6, 6.0, 12.0, 2.4], font=8)
    r.landscape_off()

    # ---------------- B
    AH(r, "Anexo B. Instrumentos de levantamiento")
    r.P("**B.1 Pauta de entrevista semiestructurada al administrador** (60 min). Objetivo: identificar los puntos de dolor y las expectativas de "
        "la gerencia respecto de la digitalización.")
    r.bullets([
        "¿Cómo describiría el proceso completo desde que un cliente solicita un traslado hasta que el viaje se cierra?",
        "¿Qué herramientas usan hoy para registrar y coordinar las reservas, y quién las opera?",
        "¿Con qué frecuencia una reserva se pierde o no se ejecuta, y cuál cree que es la causa principal?",
        "¿Cómo determina al cierre del día cuánto se recaudó y cuánto debe rendir cada conductor?",
        "¿Qué proporción de sus servicios proviene de convenios con empresas, hoteles o agencias, y cómo los gestiona?",
        "¿Qué información necesitaría para tomar mejores decisiones sobre su operación?",
        "Si pudiera resolver un solo problema de su operación, ¿cuál elegiría y por qué?",
        "¿Qué restricciones de presupuesto, tiempo o capacidad técnica debe considerar una solución para ser viable?",
    ])
    r.P("**B.2 Pauta de entrevista semiestructurada al despachador** (45 min). Objetivo: caracterizar la operación diaria del despacho y sus "
        "cuellos de botella.")
    r.bullets([
        "Describa paso a paso lo que hace desde que recibe una solicitud hasta que confirma que un conductor la tomó.",
        "¿Cómo sabe qué conductores están disponibles y dónde se encuentran?",
        "¿Cuánto tarda habitualmente en asignar un viaje y qué lo hace demorar más?",
        "¿Qué ocurre cuando un conductor no responde o no puede tomar el viaje?",
        "¿Qué información anota de cada reserva y en qué herramienta?",
        "¿Con qué consultas lo contactan los pasajeros mientras esperan su vehículo?",
        "¿Qué parte de su trabajo podría resolverse automáticamente?",
    ])
    r.P("**B.3 Guion del grupo focal con conductores** (3 conductores de distintos turnos, 50 min). Objetivo: recoger la perspectiva del "
        "conductor sobre la asignación, la comunicación y el registro de cobros.")
    r.bullets([
        "Apertura: presentación del proyecto, confidencialidad y consentimiento verbal de los participantes.",
        "¿Cómo se enteran hoy de que se les asignó un viaje y qué dificultades tiene ese método mientras conducen?",
        "¿Qué información necesitan ver antes de aceptar un traslado?",
        "¿Han tenido que rechazar un viaje ya asignado? ¿Cómo lo resuelven?",
        "¿Cómo contactan al pasajero cuando no lo ubican en el punto de recogida?",
        "¿Cómo registran los viajes y montos cobrados durante su turno?",
        "¿Qué les preocuparía de usar una aplicación durante la jornada (datos, batería, distracción)?",
        "Cierre: priorización conjunta de las tres funcionalidades más útiles.",
    ])
    r.P("**B.4 Ficha de observación directa en la central** (no participante, 2 jornadas de 4 h).")
    r.table("ficha_obs", "Ficha de observación", ["Dimensión", "Variable registrada", "Medición"], [
        ("Volumen de operación", "Solicitudes por hora y canal de ingreso", "Conteo por bloques de 30 min"),
        ("Tiempo de asignación", "Tiempo entre el ingreso de la solicitud y la confirmación del conductor", "Cronómetro por evento"),
        ("Intentos de contacto", "Conductores contactados antes de conseguir uno disponible", "Conteo por asignación"),
        ("Interrupciones", "Llamadas de pasajeros consultando por su viaje", "Conteo y motivo"),
        ("Errores observados", "Reservas duplicadas, direcciones corregidas o datos incompletos", "Registro descriptivo"),
        ("Herramientas usadas", "Cambios de aplicación del despachador durante una asignación", "Secuencia de uso"),
    ], [3.4, 8.2, 5.0], font=8.2)

    AH(r, "Anexo C. Evidencias del levantamiento y entrevista de seguimiento")
    r.P("**C.1 Síntesis de hallazgos por participante.**")
    r.table("sintesis", "Hallazgos por participante", ["Código", "Perfil", "Antigüedad", "Hallazgos principales"], [
        ("P-01", "Administrador / dueño", "12 años", "Prioriza el control de la recaudación y la pérdida de reservas. Dispuesto a pagar por una solución sin inversión en hardware."),
        ("P-02", "Despachador, turno día", "4 años", "Buscar un conductor disponible es lo que más tiempo consume: entre 5 y 10 llamadas por asignación en hora punta."),
        ("P-03", "Conductor, turno día", "6 años", "Leer asignaciones por WhatsApp mientras conduce es inseguro; pide alerta sonora y confirmar con un toque."),
        ("P-04", "Conductor, turno noche", "2 años", "Necesita rechazar formalmente un viaje cuando ya está en otro servicio."),
        ("P-05", "Conductor, turno rotativo", "9 años", "No tiene registro propio de su turno, lo que genera diferencias con la administración."),
    ], [1.4, 3.4, 1.8, 10.0], font=8.2)
    r.P("**C.2 Acta de validación del Product Backlog (28/08/2026, EV-07).** Acuerdos: se aprueba el alcance del MVP con 25 historias; la "
        "definición de tarifas queda como decisión del cliente y el sistema solo registra el monto cobrado; se excluyen las pasarelas de pago; el "
        "temporizador de aceptación es de 60 s con reasignación por el despachador; se valida un acceso digital para los convenios protegido "
        "con contraseña, cuya custodia queda a cargo de la empresa cliente (en la semana 14 se reemplazó por una cuenta propia de cada empresa, "
        "CC-16); y queda pendiente evaluar el paso de SMS a WhatsApp Business API, que luego se "
        "aprobó como CC-01.")
    r.table("evidencias_lev", "Registro de evidencias", ["Código", "Tipo", "Descripción", "Fecha"], [
        ("EV-01", "Transcripción", "Entrevista al administrador, 8 páginas", "12/08/2026"),
        ("EV-02", "Transcripción", "Entrevista al despachador del turno día, 6 páginas", "13/08/2026"),
        ("EV-03", "Notas de sesión", "Grupo focal con tres conductores y priorización conjunta", "19/08/2026"),
        ("EV-04", "Fichas de observación", "Dos jornadas en la central con cronometraje de 45 asignaciones", "20 y 21/08/2026"),
        ("EV-05", "Documento anonimizado", "Extracto de la planilla de reservas de julio de 2026", "22/08/2026"),
        ("EV-06", "Documento anonimizado", "Fotografía del cuaderno de caja de una semana", "22/08/2026"),
        ("EV-07", "Acta", "Validación del Product Backlog firmada por el administrador", "28/08/2026"),
        ("EV-08", "Registro de entrevista", "Entrevista de seguimiento sobre la operación en el aeropuerto (C.3)", "02/09/2026"),
    ], [1.6, 3.4, 9.0, 2.6], font=8.2, source="Material resguardado por el equipo conforme al compromiso de confidencialidad con el cliente.")
    r.P("**C.3 Registro de la entrevista que originó el foco aeropuerto (CC-02).** El foco en los traslados desde y hacia el aeropuerto surgió en una "
        "entrevista de seguimiento con el cliente, posterior al acta del 28/08/2026, en la que además se validaron los parámetros de operación de la "
        "{T:pend}:")
    r.kv_table("entrevista", "Registro de la entrevista con el cliente", [
        ("Código de evidencia", "EV-08"),
        ("Fecha, lugar y duración", "02/09/2026 · central de operaciones del cliente · 55 minutos"),
        ("Técnica", "Entrevista semiestructurada con la pauta del Anexo B, ampliada con preguntas sobre la operación en el aeropuerto"),
        ("Participantes", "Administrador de la flota (dueño), despachador del turno día y equipo de proyecto (Renato González y Carlos Ortiz)"),
        ("Tema", "Operación de traslados desde y hacia el aeropuerto como operador autorizado y parámetros de operación de la central."),
        ("Hallazgos", "• Cerca del 40 % de los viajes son desde o hacia el aeropuerto; los atrasos de vuelos obligan a reprogramar las recogidas a mano.\n"
                      "• Los conductores esperan en la zona de estacionamiento autorizada del operador y el turno de salida se resuelve de palabra, lo que genera reclamos entre ellos.\n"
                      "• Alrededor de la mitad de los pasajeros escribe primero a la central por WhatsApp.\n"
                      "• La central opera las 24 horas, todos los días; el domingo de madrugada es el período de menor demanda."),
        ("Parámetros acordados", "• Margen de recogida después del aterrizaje: 20 min en vuelos nacionales y 35 min en internacionales.\n"
                                 "• Un conductor sale de la fila virtual si permanece 10 min fuera de la zona.\n"
                                 "• Espera máxima por no presentación del pasajero: 15 min desde que el vehículo llega al punto de recogida.\n"
                                 "• Geocerca: polígono de la zona de estacionamiento autorizada, trazado sobre el mapa junto al administrador."),
        ("Acuerdos", "• Incorporar registro y monitoreo de vuelos con ajuste de recogida confirmado por el despachador.\n"
                     "• Incorporar una fila virtual por orden de llegada a la zona.\n"
                     "• Mantener los convenios corporativos.\n"
                     "• Dejar los parámetros configurables desde el panel para ajustarlos tras la marcha blanca."),
        ("Respaldo", "Notas de la entrevista revisadas y aprobadas por correo por el administrador"),
    ], font=8)
    AH(r, "Anexo D. Registro de solicitudes de cambio y decisiones de cambio")
    r.P("**D.1 Solicitudes de cambio.** Cada cambio siguió el procedimiento de 8.3. Impacto: A = alcance, T = tiempo, C = costo, Q = calidad, R = riesgo.")
    cc = [
        ("CC-01", "Equipo (análisis de costos)", "SMS → WhatsApp Business API vía Twilio", "A: HU-20, 21, 24 modificadas · T: −6 SP · C: ≈ −$239.000/mes en operación · Q: nuevos CP-07 a CP-10 · R: R-04 baja, nace R-12", "PO + cliente"),
        ("CC-02", "Cliente (entrevista EV-08)", "Foco aeropuerto: vuelos, ajuste de recogida, alertas, fila virtual", "A: HU-26 a 29 (+26 SP), HU-04 −5 SP · T: absorbido con CC-03/04 · C: API de vuelos ≈ USD 30/mes · R: nace R-13", "PO + cliente"),
        ("CC-03", "Equipo", "Chat de WhatsApp en el panel; retiro de enlaces wa.me", "A: HU-30 (+5 SP), retiro HU-22 y 23 (−6 SP) · Q: privacidad del conductor", "PO"),
        ("CC-04", "Equipo", "Fusión de reportes", "A: HU-06 absorbe 07, 08 y 09 (−15 SP) · Q: un solo módulo con filtros", "PO"),
        ("CC-05", "Equipo", "Estados PENDIENTE_CONFIRMACION y EN_ZONA", "A: Anexo H · Q: CP-08, CP-16", "PO"),
        ("CC-06", "Equipo", "Disponibilidad 99,0 % y RPO 6 h", "Q: meta realista · C: sin costo adicional · R: reduce el riesgo de incumplir el SLA", "PO + cliente"),
        ("CC-07", "Docente / equipo", "AWS us-east-1; PostgreSQL en contenedor", "C: −USD 15/mes frente a RDS · R: respaldo a cargo del equipo", "PO"),
        ("CC-08", "Equipo", "Clientes web en React + Vite", "T: neutro · Q: código compartido con la app", "PO"),
        ("CC-09", "Docente", "Roles Scrum con Product Owner", "Q: separación entre quien desarrolla y quien aprueba", "Docente / equipo"),
        ("CC-10", "Docente", "Marco legal actualizado", "A: RN-18, RNF-09 · Q: cumplimiento legal", "PO"),
        ("CC-11", "Equipo (resultado de la PoC H-3)", "App del conductor: ajuste del WebView para registrar con la pantalla apagada; si el conductor cierra la app el registro se detiene y se mitiga con guía de configuración del teléfono, reanudación al reabrir y umbral de 60 s en el panel", "A: criterios de HU-13 y HU-02 · T: absorbido en la app base · Q: R-01 en mitigación · R: nace R-16 (batería)", "PO"),
        ("CC-12", "Docente (EF2)", "Entidades TURNO y CIERRE_CAJA; pantalla de cierre de caja por turno; KPI-05 y KPI-08 reformulados", "A: HU-31 (+5 SP), migración de DC-26, ajuste del reporte de cancelaciones · T: 9 h en la semana 14 · C: sin costo · Q: KPI-03, 04 y 05 medibles; CP-36 · R: baja el riesgo de un indicador que no se puede calcular", "PO"),
        ("CC-13", "Equipo / docente (EF2)", "Modelo comercial: licencia perpetua de uso más plan de servicio mensual en tres tramos", "A: sin efecto en las HU; EMPRESA.plan cambia de dominio · C: precio según tamaño de flota; ingreso único por licencia · Q: factibilidad con margen neto y punto de equilibrio · R: nace R-17 (margen supuesto)", "PO"),
        ("CC-14", "Docente (EF2)", "Respaldo lógico cada 6 h, alternado con los snapshots", "A: RNF-08, PO-02 · C: sin costo adicional relevante en S3 (retención escalonada) · Q: el RPO de 6 h queda sostenido por cada mecanismo · R: baja R-09", "PO"),
        ("CC-15", "Docente (EF2)", "Canal CONTINGENCIA, folio y procedimiento de carga diferida", "A: HU-32 (+3 SP), VIAJE.canal y folio_contingencia, PO-06 · T: 5 h en la semana 14 · Q: CP-37; conciliación por folio · R: evita la pérdida de registros tras una caída", "PO"),
    ]
    cc += [
        ("CC-16", "Cliente / PO (10/11/2026)", "Inicio de sesión web único para todos los roles; autoregistro de convenios con aprobación del administrador (reemplaza el link con contraseña); cuenta del pasajero", "A: HU-33, 34 y 35 (+24 SP); retira el acceso por link de HU-11 y HU-25 · T: Sprint 4 · Q: CP de inicio de sesión, aprobación y activación · R: R-07 baja (sin contraseña compartida)", "PO"),
        ("CC-17", "Cliente / PO (10/11/2026)", "Administración de usuarios del panel por el administrador", "A: HU-36 (+3 SP) · Q: la empresa nunca queda sin administrador; revocación inmediata de sesiones", "PO"),
        ("CC-18", "Cliente / PO (11/11/2026)", "Cuenta obligatoria para pedir en el portal y rediseño del portal (tres tipos de viaje, revisa tu pedido, tu viaje, mis viajes)", "A: HU-37 a 44 (+40 SP) y HU-45 (+5 SP, adelantada por privacidad) en el Sprint 4; HU-46 a 49 (+16 SP) en la versión 1.1 · T: HU-46 a 49 después de la UAT · Q: privacidad aceptada una vez al crear la cuenta (DC-44) · R: retira el pedido sin cuenta, con lo que baja el riesgo de reservas falsas", "PO + cliente"),
        ("CC-19", "Cliente / PO (12/11/2026)", "Chat interno por WebSocket en ambos sentidos (pasajero ↔ central, central ↔ conductor y conductor ↔ pasajero); verificación de la cuenta por correo; avisos por notificación del navegador (Web Push) y por correo (Amazon SES); se retira Twilio", "A: cambian HU-20, 21, 24 y 30, RN-06 y RN-09; nuevas CONVERSACION y MENSAJE_CHAT · T: versión 1.1, después de la UAT · C: baja el costo variable al eliminar los mensajes de WhatsApp · Q: retención de 12 meses (RN-15) y permisos por empresa (RN-13) · R: desaparece la dependencia de las plantillas de Meta; se acepta que en iPhone el aviso del navegador exige agregar el portal a la pantalla de inicio (si no, llega por correo)", "PO + cliente"),
        ("CC-20", "Equipo / PO (12/11/2026)", "Unificación visual del panel y la app del conductor con el sistema «Tiffany degradé» del portal", "A: versión 1.1, sin cambio de funciones · Q: los tres clientes comparten tokens y componentes", "PO"),
        ("CC-21", "Cliente / PO (12/11/2026)", "Apariencia por empresa: logo, nombre y colores del portal", "A: versión 1.1; los tokens de HU-37 ya lo permiten · Q: cada empresa cliente muestra su marca", "PO"),
    ]
    r.P("CC-19 a CC-21 están aprobadas para después de la entrega: se presentan como diseño (sección 4.7) y no forman parte de lo "
        "construido al corte.")
    r.table("cc_det", "Detalle de las solicitudes de cambio", ["Código", "Solicitante", "Cambio", "Análisis de impacto", "Aprobó"], cc,
            [1.3, 2.6, 4.0, 6.8, 1.9], font=7.6)
    r.P("**D.2 Decisiones de cambio de la construcción.** Durante la construcción, todo desvío respecto del diccionario de datos del diseño se "
        "registró como decisión de cambio (DC), con su motivo, y fue aprobado por el Product Owner. Las DC ya están incorporadas al Anexo F.")
    dc = [
        ("DC-01", "Agregado", "EMPRESA", "Columna slug para la URL del portal (/solicitar/<slug>)", "Implementado"),
        ("DC-02", "Agregado", "CONFIGURACION_EMPRESA", "Tabla 1:1 con los parámetros configurables por empresa y la zona de operación", "Implementado"),
        ("DC-03", "Desvío de dominio", "HISTORIAL_ESTADO", "actor agrega ADMINISTRADOR, que también cambia estados", "Implementado"),
        ("DC-04", "Agregado técnico", "USUARIO", "Columnas del sistema de autenticación de Django (solo para el admin interno)", "Implementado"),
        ("DC-05", "Diseño", "VIAJE", "Coordenadas obtenidas con un geocodificador detrás de un adaptador", "Implementado"),
        ("DC-06", "Precisión de uso", "VUELO", "Solo para viajes desde el aeropuerto; la hora programada es la de llegada", "Implementado"),
        ("DC-07", "Supuesto", "USUARIO", "Bloqueo de 15 min configurable tras 5 intentos fallidos", "Implementado"),
        ("DC-08", "Desvío de dominio", "VIAJE", "origen_cancelacion agrega ADMINISTRADOR", "Implementado"),
        ("DC-09", "Corrección de tipo", "VIAJE, HISTORIAL_ESTADO", "Estados de VARCHAR(20) a VARCHAR(22): PENDIENTE_CONFIRMACION tiene 22 caracteres", "Implementado"),
        ("DC-10", "Agregado", "CONFIGURACION_EMPRESA", "anticipacion_minima_min (30) para solicitudes del portal", "Implementado"),
        ("DC-11", "Agregado", "PASAJERO", "privacidad_aceptada_en: evidencia de la aceptación del aviso de privacidad", "Implementado"),
        ("DC-12", "Supuesto", "VUELO", "Sin distinción nacional/internacional: se usa el margen nacional; revisar en HU-27", "Implementado"),
        ("DC-13", "Agregado", "AUDITORIA", "entidad agrega VEHICULO y CONDUCTOR", "Implementado"),
        ("DC-14", "Agregado", "USUARIO", "debe_cambiar_password y password_temporal_vence (contraseña temporal de 72 h)", "Implementado"),
        ("DC-15", "Agregado", "POSICION_GPS", "Único (conductor, registrada_en) para que un reenvío no duplique posiciones", "Implementado"),
        ("DC-16", "Supuesto", "CONFIGURACION_EMPRESA", "precision_geocerca_m (50): solo posiciones precisas marcan la llegada", "Implementado"),
        ("DC-17", "Supuesto", "HISTORIAL_ESTADO", "EN_ZONA puede marcarlo el conductor si la geocerca no lo hizo", "Implementado"),
        ("DC-18", "Supuesto", "MENSAJE_WHATSAPP", "Reglas de los avisos: conductor asignado al aceptar; «te espera» solo con geocerca; cancelar ambiguo no cancela", "Implementado"),
        ("DC-19", "Supuesto", "CONFIGURACION_EMPRESA", "encuesta_vigencia_horas (24) para la calificación", "Implementado"),
        ("DC-20", "Agregado", "HISTORIAL_ESTADO", "manual y distancia_m: trazabilidad de la llegada indicada a mano (DC-17)", "Implementado"),
        ("DC-21", "Supuesto", "GEOCERCA, FILA_AEROPUERTO", "Reglas de la fila: polígono aproximado de SCL ajustable por empresa; solo cuentan posiciones precisas; sin posiciones en la zona durante la tolerancia, sale; si rechaza, vuelve al final", "Implementado"),
        ("DC-22", "Agregado", "VUELO, CONFIGURACION_EMPRESA", "origen_icao, eta_referencia, recogida_propuesta y propuesta_en; cinco parámetros del monitoreo; vuelo nacional si el ICAO de origen empieza con SC", "Implementado"),
        ("DC-23", "Agregado", "ALERTA_VUELO (nueva)", "Registro de las alertas de vuelo con su tipo, detalle y atención", "Implementado"),
        ("DC-24", "Precisión de uso", "CONVENIO", "La contraseña la genera el servidor y se muestra una vez; rotarla no cambia el token; sin RUT único por empresa", "Implementado"),
        ("DC-25", "Precisión de uso", "AUDITORIA, PAGO_VIAJE", "Acciones ANULACION_FORZADA y CIERRE_FORZADO; solo con el pasajero a bordo; cerrar exige motivo, método y monto", "Implementado"),
        ("DC-26", "Agregado", "CONDUCTOR", "turno_inicio y turno_fin del último turno, para «Mi turno»", "Implementado; se reemplaza por TURNO (CC-12)"),
        ("DC-27", "Agregado", "CONVENIO, AUDITORIA, VIAJE", "Bloqueo del link (intentos_fallidos, bloqueado_hasta); usuario_id nulo para eventos sin usuario; declaración del supervisor sobre los avisos", "Implementado"),
        ("DC-28", "Supuesto", "VEHICULO, CONDUCTOR", "«En línea»: vehículo declarado por un conductor en turno; se separa con señal y sin señal (60 s)", "Implementado"),
        ("DC-29", "Supuesto", "Sin cambio de columnas", "Definiciones de los reportes: liquidación y facturación por día de pago; cancelaciones e historial por día de recogida; sin comisiones; CSV para Excel", "Implementado; la base de las cancelaciones se ajusta con CC-12"),
        ("DC-30", "Precisión de uso", "VIAJE", "navegar_con: la app navega con la dirección escrita mientras el geocodificador sea el de desarrollo", "Implementado"),
    ]
    dc += [
        ("DC-31", "Agregado", "CONFIGURACION_EMPRESA", "vigencia_verificacion_dias (90): un teléfono verificado no se vuelve a verificar dentro de la vigencia", "Implementado"),
        ("DC-32", "Agregado", "TURNO, CIERRE_CAJA (nuevas)", "Turnos y cuadratura de caja por turno (CC-12, HU-31); migra los turnos de DC-26", "Implementado"),
        ("DC-33", "Agregado", "VIAJE, HISTORIAL_ESTADO", "Canal CONTINGENCIA y folio único por empresa (CC-15, HU-32)", "Implementado"),
        ("DC-34", "Agregado", "USUARIO", "rol agrega CONVENIO y PASAJERO; un solo inicio de sesión web (CC-16)", "Implementado"),
        ("DC-35", "Desvío de dominio", "CONVENIO, VIAJE", "Convenio con estado y cuenta propia; se retiran token y contraseña compartida (CC-16)", "Implementado"),
        ("DC-36", "Agregado", "CUENTA_PASAJERO (nueva)", "Cuenta del pasajero que se activa al confirmar el teléfono por WhatsApp", "Implementado"),
        ("DC-37", "Precisión de uso", "USUARIO", "El administrador crea, edita y desactiva administradores y despachadores (CC-17)", "Implementado"),
        ("DC-38", "Precisión de uso", "EMPRESA, USUARIO", "Alta de empresas cliente con un comando y primer administrador con contraseña temporal", "Implementado"),
        ("DC-39", "Corrección de dominio", "EMPRESA", "plan pasa a INICIAL | ESTANDAR | AVANZADO, como el modelo comercial (CC-13)", "Implementado"),
        ("DC-40", "Corrección", "USUARIO", "Pantalla de primer ingreso para cambiar la contraseña temporal en todos los roles web", "Implementado"),
        ("DC-41", "Cambio de alcance", "VIAJE, PASAJERO", "Solo se pide en el portal con cuenta de pasajero o de convenio (CC-18)", "Implementado"),
        ("DC-42", "Columnas nuevas", "VIAJE, CONFIGURACION_EMPRESA", "pasajeros, maletas, vuelo_salida_en y vuelo_salida_tipo; antelación sugerida al aeropuerto", "Implementado"),
        ("DC-43", "Regla de negocio", "VIAJE, VEHICULO, ASIGNACION", "Los pasajeros no superan la capacidad de la flota y no se asigna un vehículo de menor capacidad", "Implementado"),
        ("DC-44", "Columnas nuevas", "CUENTA_PASAJERO, PASAJERO", "Aviso de privacidad y avisos por WhatsApp aceptados una vez al crear la cuenta, con su versión", "Implementado"),
        ("DC-45", "Columna nueva", "CUENTA_PASAJERO, USUARIO", "Reenvío del mensaje de activación y recuperación de contraseña con enlace de 30 min", "Implementado"),
        ("DC-46", "Precisión de uso", "VIAJE, HISTORIAL_ESTADO", "El pasajero ve y cancela solo sus propios viajes", "Implementado"),
        ("DC-47", "Acuerdo de integración", "— (proceso)", "El ruleset de main exige pull request, check de CI y fusión squash; la revisión cruzada pasa a ser un acuerdo de trabajo con lista de chequeo y deja de ser una aprobación obligatoria de GitHub", "Vigente"),
        ("DC-48", "Índice y tarea", "POSICION_GPS", "Índice por fecha y tarea diaria que borra las posiciones de más de 30 días (RN-15)", "Implementado"),
        ("DC-49", "Cambio de repositorio", "— (proceso)", "El repositorio pasa a la organización Flotaagil-CL con su historial, issues, tablero y ruleset; CI en verde en el repositorio nuevo", "Aplicado"),
        ("DC-50", "Columnas y anonimización", "PASAJERO, CUENTA_PASAJERO, USUARIO, MENSAJE_WHATSAPP", "WhatsApp nuevo por confirmar; eliminar la cuenta anonimiza los datos personales y conserva viajes, pagos y auditoría", "Implementado"),
    ]
    r.table("dc", "Decisiones de cambio de la construcción", ["Código", "Tipo", "Tabla", "Cambio", "Estado"], dc, [1.3, 2.3, 3.5, 7.3, 2.2], font=7.6)
    r.P("**D.3 Pendientes por resolver.** Los temas que requieren una decisión del Product Owner o del cliente se registran como PR-xx. A la "
        "fecha de corte siguen abiertos PR-01 (retención de la auditoría frente a RN-15), PR-03 (corrección del teléfono del pasajero), PR-04 "
        "(texto del aviso de privacidad), PR-05 (portal en inglés), PR-09, PR-11 y PR-12 (credenciales de servicios externos), PR-13 (aviso con "
        "la app cerrada), PR-14 (aviso al pasajero cuando cambia la hora de recogida, que requiere una plantilla de Meta) y PR-15 (el correo es "
        "único en todo el sistema, por lo que una persona necesita un correo distinto por empresa); PR-08 (vuelos de salida) quedó pospuesto "
        "fuera del MVP y PR-02, PR-06, PR-07 y PR-10 están cerrados. PR-11 y PR-14 dejan de aplicar cuando se implemente CC-19, que retira Twilio.")

    # ---------------- C
    AH(r, "Anexo E. Especificación de casos de uso")
    for c in CU:
        r.kv_table("cu_" + c["id"], f'{c["id"]} {c["nombre"]}', [
            ("Objetivo", c["obj"]), ("Actor principal", c["act"]), ("Actores secundarios", c["sec"]), ("Requerimientos", c["req"]),
            ("Precondiciones", c["pre"]), ("Evento de inicio", c["ini"]), ("Flujo principal", "\n".join(c["flujo"])),
            ("Flujos alternativos", "\n".join(c["alt"])), ("Excepciones", "\n".join(c["exc"])), ("Postcondiciones", c["post"]),
            ("Reglas y criterios", c["reglas"]),
        ], widths=(3.4, 13.2), font=7.8)

    # ---------------- D
    r.landscape_on()
    AH(r, "Anexo F. Diccionario de datos")
    r.P(f"Diccionario vigente, con las decisiones de cambio DC-01 a DC-{DC_MAX} ya incorporadas (cada campo agregado o modificado indica su DC) y con "
        "los cambios originados en la EF2: las entidades TURNO y CIERRE_CAJA (CC-12), el dominio de EMPRESA.plan (CC-13) y el canal CONTINGENCIA "
        "con su folio (CC-15), todos ya implementados (DC-32, DC-33 y DC-39), y los cambios de la semana 14: convenio con cuenta propia, cuenta del pasajero, capacidad del viaje y eliminación de la cuenta con anonimización (CC-16 a CC-18, DC-50). "
        "Convenciones: PK clave primaria, FK clave foránea, UK valor único. Todas las claves foráneas usan ON DELETE PROTECT. Fechas y horas en "
        "UTC (TIMESTAMPTZ) y se muestran en hora de Chile. Montos en pesos chilenos enteros. Columna «Sensible»: dato personal, credencial o "
        "ubicación con acceso restringido por rol.")
    for name, (desc, cols) in E.items():
        rows = [(c[0], c[1], c[2], c[3] or "—", c[4], c[5], c[6], c[7] or "—") for c in cols]
        r.table("dd_" + name, f"{name}: {desc}", ["Campo", "Tipo / formato", "Nulo", "Clave", "Significado", "Dominio, restricción o validación", "Defecto", "Sensible"],
                rows, [3.2, 3.6, 1.1, 1.6, 4.4, 5.6, 2.4, 1.6], font=7.4)
    rels = [(p, c, k) for p, c, k in REL]
    r.table("dd_rel", "Relaciones y cardinalidades", ["Entidad padre", "Entidad hija", "Cardinalidad"], rels, [6.0, 6.0, 4.0], font=8)

    # ---------------- E
    AH(r, "Anexo G. Casos de prueba y resultado de su ejecución")
    r.P("Estado al corte de la semana 14. Los casos de las historias construidas se ejecutaron de forma automática y manual contra el "
        "backend real con datos sintéticos; su evidencia está en *docs/evidencias/HU-xx/* del repositorio. Los que dependen de servicios reales, "
        "teléfono real o carga se indican como parciales, y los que requieren staging o producción, como planificados. CP-38 a CP-45 cubren las "
        "historias de las solicitudes de cambio CC-16 a CC-18 (HU-33 a HU-45).")
    EJEC = {
        "CP-01": ("OK", "HU-10"), "CP-02": ("OK", "HU-10"), "CP-03": ("OK", "HU-13"), "CP-04": ("OK", "HU-13"),
        "CP-05": ("OK", "HU-03"), "CP-06": ("OK", "HU-03"),
        "CP-07": ("OK con doble de Twilio (Sprint 1); desde CC-18 la verificación ocurre al activar la cuenta (CP-40)", "HU-20"),
        "CP-08": ("OK; aplica a las reservas anteriores a CC-18", "HU-20"), "CP-09": ("OK; el límite se mantiene en la activación (CP-40)", "HU-19"),
        "CP-10": ("OK", "HU-20"), "CP-11": ("OK con respuestas simuladas", "HU-26"),
        "CP-12": ("Parcial: p95 59 ms con 2 conductores; falta carga con 50", "HU-02"),
        "CP-13": ("OK: vuelve a SOLICITADO a los 58–64 s", "HU-15"),
        "CP-14": ("OK con PostgreSQL real: en ambas variantes una petición responde 200 y la otra 409; se corrigió un orden de bloqueo invertido", "CP-14"),
        "CP-15": ("OK", "HU-16"), "CP-16": ("OK con posiciones simuladas; falta GPS real", "HU-16, HU-21"), "CP-17": ("OK", "HU-21"),
        "CP-18": ("OK: 12 comprobaciones", "HU-04"), "CP-19": ("OK: lugares 1, 2 y 3 en orden de ingreso", "HU-29"),
        "CP-20": ("OK: a los 9 min conserva el lugar y a los 11 sale", "HU-29"),
        "CP-21": ("OK con API de vuelos simulada; alerta visible a los 10,9 s; falta FlightAware real", "HU-27, HU-28"),
        "CP-22": ("OK en el Sprint 3 y otra vez con la cuenta del convenio tras CC-16: la sesión abierta pierde el acceso al instante; historial intacto", "HU-11, HU-34"),
        "CP-23": ("OK: 404 para registros de otra empresa y 403 por rol, en cada historia", "HU-06, HU-11, HU-12"),
        "CP-24": ("OK: modelo y trigger rechazan cambios; la API responde 405", "HU-12"),
        "CP-25": ("OK: totales iguales a los esperados", "HU-06"),
        "CP-26": ("OK: bloqueo al quinto intento; desde CC-16 lo aplica el inicio de sesión único (DC-07)", "HU-25, HU-33"),
        "CP-27": ("OK con doble de Twilio; mensajes visibles en 5 a 15 s", "HU-30"),
        "CP-28": ("Planificado: semana 15, en staging", "—"), "CP-29": ("Planificado: semana 15, en staging", "—"),
        "CP-30": ("Planificado: semana 15, en staging", "—"), "CP-31": ("Planificado: semana 15, en staging", "—"),
        "CP-32": ("Planificado: semanas 15–16, teléfono real", "—"), "CP-33": ("Planificado: semanas 15–16, teléfono real", "—"),
        "CP-34": ("Planificado: primer despliegue (semana 15)", "—"), "CP-35": ("Planificado: semana 16", "—"),
        "CP-36": ("OK: diferencia calculada, observación exigida y segundo cierre rechazado", "HU-31"),
        "CP-37": ("OK: 29 pruebas en verde; folio repetido rechazado y conciliación por folio", "HU-32"),
        "CP-38": ("OK; correo con el adaptador de consola (SES sin credenciales reales)", "HU-33"),
        "CP-39": ("OK; avisos por correo con el adaptador de consola", "HU-34"),
        "CP-40": ("OK con doble de Twilio; falta Twilio real", "HU-35, HU-41"),
        "CP-41": ("OK: 409 en ambos casos; revocación inmediata", "HU-36"),
        "CP-42": ("OK con pasajero sintético", "HU-39, HU-40, HU-42"),
        "CP-43": ("OK: 404 para el viaje ajeno; cancelar solo sin conductor", "HU-43, HU-44"),
        "CP-44": ("OK: anonimización completa, 409 con viaje activo y purga de las posiciones de 31 y 90 días", "HU-45"),
        "CP-45": ("OK: 57 pruebas de componentes; revisión a 390 y 1440 px", "HU-37, HU-38"),
    }
    rows = [(c[0], c[1], c[2], f"{c[3]}. Pre: {c[4]}", c[5], c[6], c[7], f"{c[8]} · {c[9]}", c[10],
             EJEC.get(c[0], ("Pendiente", "—"))[0], EJEC.get(c[0], ("Pendiente", "—"))[1]) for c in CP]
    r.table("cp_full", "Casos de prueba", ["ID", "Req.", "Tipo", "Objetivo y precondición", "Datos", "Pasos", "Resultado esperado", "Prior. · Resp.",
                                           "Ejecución", "Resultado obtenido", "Evidencia"], rows,
            [1.1, 1.6, 1.8, 3.6, 2.6, 2.8, 3.4, 1.7, 1.3, 1.5, 1.2], font=6.9)
    r.landscape_off()

    # ---------------- F
    AH(r, "Anexo H. Máquina de estados del viaje")
    r.P("Actualiza la máquina de estados de la formulación. Se agregan PENDIENTE_CONFIRMACION (reserva del portal a la espera de la confirmación por WhatsApp) y "
        "EN_ZONA (vehículo a menos de 150 m del origen, que dispara el aviso «tu vehículo te espera»), y la cancelación por el pasajero pasa a "
        "hacerse respondiendo el mensaje de WhatsApp. Desde CC-18 solo se pide con una cuenta activa, cuyo teléfono ya se verificó al activarla: "
        "las reservas del portal nacen en SOLICITADO, y el pasajero también puede cancelar desde «Mis viajes» mientras no haya conductor (RN-09). "
        "PENDIENTE_CONFIRMACION se conserva solo para las reservas anteriores a ese cambio.")
    r.figure("fig/estados.png", "estados", "Máquina de estados del viaje", width_cm=16.4)
    st = [
        ("PENDIENTE_CONFIRMACION", "Reserva del portal sin confirmar (solo reservas anteriores a CC-18)", "→ SOLICITADO, → CANCELADO", "Pasajero (WhatsApp) o sistema (15 min)", "Nuevo; sin uso desde CC-18"),
        ("SOLICITADO", "Reserva confirmada sin conductor", "→ ASIGNADO, → CANCELADO", "Despachador; pasajero o supervisor (cancela)", "Vigente"),
        ("ASIGNADO", "Conductor notificado, 60 s para responder", "→ ACEPTADO, → SOLICITADO", "Conductor o temporizador", "Vigente"),
        ("ACEPTADO", "Conductor confirmó el viaje", "→ EN_CAMINO, → CANCELADO", "Conductor o despachador", "Vigente"),
        ("EN_CAMINO", "En ruta al punto de recogida", "→ EN_ZONA, → CANCELADO", "Sistema (geocerca), conductor (DC-17) o despachador", "Modificado"),
        ("EN_ZONA", "Vehículo a < 150 m del origen", "→ PASAJERO_A_BORDO, → CANCELADO", "Sistema (geocerca, precisión ≤ 50 m) o conductor si la geocerca no marcó (DC-17, queda «manual» con su distancia, DC-20); despachador (no presentación a los 15 min)", "Nuevo"),
        ("PASAJERO_A_BORDO", "Traslado en ejecución", "→ FINALIZADO, → CANCELADO (anulación forzada)", "Conductor; despachador (HU-05)", "Vigente"),
        ("FINALIZADO", "Viaje terminado con pago registrado", "Terminal", "Conductor o despachador (cierre forzado)", "Vigente"),
        ("CANCELADO", "Anulado con motivo y origen", "Terminal", "—", "Vigente"),
    ]
    r.table("estados_t", "Estados, transiciones y actores", ["Estado", "Descripción", "Transiciones", "Actor", "Cambio"], st, [3.6, 4.0, 3.8, 3.6, 1.6], font=7.8)
    r.P("Toda transición se registra en HISTORIAL_ESTADO. El despachador conserva la transición excepcional de cierre o anulación desde ACEPTADO, "
        "EN_CAMINO, EN_ZONA o PASAJERO_A_BORDO con motivo obligatorio (RN-11).")

    # ---------------- G
    AH(r, "Anexo I. Matriz de trazabilidad")
    r.P("Vincula cada historia con su objetivo, regla, proceso BPMN, caso de uso, componente, entidades principales y casos de prueba. Incluye "
        "las dos historias incorporadas tras la EF2, que enlazan el proceso P3.2 y la continuidad, y las de las solicitudes de cambio CC-16 a "
        "CC-18 (HU-33 a HU-45), que enlazan la creación y habilitación de cuentas (P1.1) y el portal rediseñado.")
    tr = {
        "HU-01": ("OE-02", "RN-13", "P2", "CU-02", "Reservas y despacho, Gateway", "VIAJE, CONDUCTOR", "CP-12"),
        "HU-02": ("OE-02", "RN-13, RN-18", "P2", "CU-02", "Gateway tiempo real", "POSICION_GPS", "CP-12"),
        "HU-03": ("OE-02", "RN-13", "P1", "CU-01", "Reservas y despacho", "VIAJE, HISTORIAL_ESTADO", "CP-05, CP-06"),
        "HU-04": ("OE-02", "RN-01, RN-02", "P2", "CU-03", "Motor de sugerencia", "ASIGNACION, POSICION_GPS", "CP-18"),
        "HU-05": ("OE-02", "RN-11", "P3", "CU-04", "Reservas y despacho, Auditoría", "AUDITORIA", "CP-24"),
        "HU-06": ("OE-02", "RN-10", "P3.2", "CU-08", "Cobros y reportes", "PAGO_VIAJE", "CP-25"),
        "HU-10": ("OE-02", "RN-05", "—", "CU-05", "Flota", "CONDUCTOR, VEHICULO", "CP-01, CP-02"),
        "HU-11": ("OE-02", "RN-08", "P1.1", "CU-06", "Convenios", "CONVENIO", "CP-22, CP-39"),
        "HU-12": ("OE-02", "RN-12", "—", "CU-07", "Auditoría", "AUDITORIA", "CP-24"),
        "HU-13": ("OE-03", "RN-05, RN-18", "P2.1", "CU-09", "App, Flota", "CONDUCTOR, TURNO", "CP-03, CP-04"),
        "HU-14": ("OE-03", "—", "P2", "CU-10", "App, Gateway", "ASIGNACION", "CP-13"),
        "HU-15": ("OE-03", "RN-03, RN-04", "P2", "CU-10", "Reservas y despacho", "ASIGNACION", "CP-13, CP-14"),
        "HU-16": ("OE-03", "RN-10", "P3, P3.1", "CU-11", "App, Cobros", "PAGO_VIAJE, HISTORIAL_ESTADO", "CP-15, CP-16"),
        "HU-17": ("OE-03", "—", "P3", "CU-11", "App", "—", "E2E"),
        "HU-18": ("OE-03", "—", "P3, P3.2", "CU-11", "App, Cobros", "PAGO_VIAJE, TURNO", "E2E"),
        "HU-19": ("OE-02", "RN-13", "P1", "CU-12", "Portal, Reservas", "PASAJERO, VIAJE", "CP-42"),
        "HU-20": ("OE-02", "RN-06", "P1.1", "CU-13", "Mensajería WhatsApp", "MENSAJE_WHATSAPP", "CP-07 a CP-10, CP-40"),
        "HU-21": ("OE-02", "RN-09", "P3", "CU-14", "Mensajería WhatsApp", "MENSAJE_WHATSAPP", "CP-16, CP-17"),
        "HU-24": ("OE-02", "RN-14", "P3", "CU-14", "Mensajería, Cobros", "CALIFICACION", "E2E"),
        "HU-25": ("OE-02", "RN-07, RN-08", "P1", "CU-12", "Portal, Convenios", "CONVENIO, VIAJE", "CP-22, CP-26, CP-39"),
        "HU-26": ("OE-02", "—", "P1", "CU-01, CU-15", "Monitoreo de vuelos", "VUELO", "CP-11"),
        "HU-27": ("OE-02", "RN-02, RN-17", "P2.2", "CU-15", "Monitoreo y adaptador de vuelos", "VUELO, VIAJE", "CP-21"),
        "HU-28": ("OE-02", "RN-17", "P2.2", "CU-15", "Monitoreo de vuelos, Gateway", "VUELO, ALERTA_VUELO", "CP-21"),
        "HU-29": ("OE-02", "RN-16", "P2, P2.1", "CU-16", "Fila virtual", "FILA_AEROPUERTO, GEOCERCA", "CP-19, CP-20"),
        "HU-30": ("OE-02", "—", "P1", "CU-17", "Mensajería WhatsApp", "MENSAJE_WHATSAPP", "CP-27"),
    }
    rows = [(h[0],) + tr[h[0]] for h in HU]
    rows.append(("HU-31", "OE-02", "RN-19", "P3.2", "CU-08", "Cobros y reportes, Auditoría", "TURNO, CIERRE_CAJA, PAGO_VIAJE", "CP-36"))
    rows.append(("HU-32", "OE-02", "RN-20", "P1 (retorno, 8.2)", "CU-01", "Reservas y despacho, Auditoría", "VIAJE, AUDITORIA", "CP-37, CP-30"))
    rows += [
        ("HU-33", "OE-02", "RN-13", "P1", "CU-12, CU-13", "Autenticación", "USUARIO", "CP-26, CP-38"),
        ("HU-34", "OE-02", "RN-08, RN-12", "P1.1", "CU-06", "Convenios, Auditoría", "CONVENIO, USUARIO, AUDITORIA", "CP-22, CP-39"),
        ("HU-35", "OE-02", "RN-06, RN-09", "P1.1", "CU-13", "Portal, Mensajería WhatsApp", "CUENTA_PASAJERO, PASAJERO", "CP-40"),
        ("HU-36", "OE-02", "RN-13", "—", "CU-05", "Autenticación, Auditoría", "USUARIO, AUDITORIA", "CP-41"),
        ("HU-37", "OE-02", "—", "—", "CU-12, CU-13", "Portal (sistema visual)", "—", "CP-45"),
        ("HU-38", "OE-02", "RN-06", "P1.1", "CU-13", "Portal, Autenticación", "USUARIO, CUENTA_PASAJERO", "CP-38, CP-45"),
        ("HU-39", "OE-02", "RN-13, RN-17", "P1", "CU-12", "Portal, Reservas, Monitoreo de vuelos", "VIAJE, VUELO", "CP-42"),
        ("HU-40", "OE-02", "RN-06", "P1", "CU-12", "Portal, Reservas", "VIAJE, PASAJERO", "CP-42"),
        ("HU-41", "OE-02", "RN-06", "P1.1", "CU-13", "Autenticación, Portal", "USUARIO, CUENTA_PASAJERO", "CP-40"),
        ("HU-42", "OE-02", "—", "P1", "CU-12", "Portal", "VIAJE", "CP-42"),
        ("HU-43", "OE-02", "RN-13", "P3", "CU-12", "Portal, Gateway", "VIAJE, HISTORIAL_ESTADO", "CP-43"),
        ("HU-44", "OE-02", "RN-09", "P1", "CU-12", "Portal, Reservas", "VIAJE", "CP-43"),
        ("HU-45", "OE-01", "RN-15", "—", "CU-13", "Portal, Flota", "USUARIO, PASAJERO, CUENTA_PASAJERO, POSICION_GPS", "CP-44"),
        ("Modelo de datos y seguridad", "OE-01", "RN-13, RN-15", "—", "—", "Todos", "Modelo lógico completo", "CP-23, CP-24"),
    ]
    rows.append(("RNF-01 a 13", "OE-04", "Transversal", "—", "—", "Arquitectura e infraestructura", "—", "CP-12, CP-14, 28 a 34"))
    r.table("traz", "Matriz de trazabilidad", ["HU", "Objetivo", "Reglas", "Proceso", "Caso de uso", "Componente", "Entidades", "Pruebas"], rows,
            [1.4, 1.3, 2.0, 1.6, 2.0, 3.3, 3.2, 1.8], font=7.4)

    # ---------------- H
    AH(r, "Anexo J. Respaldo de costos y matrices de decisión")
    r.P("**J.1 Supuestos.** Tipo de cambio $950 por dólar (supuesto; variación de ±10 % cubierta por imprevistos). Volumen: 1.512 reservas/mes "
        "(promedio jun–ago 2026), 50 conductores, 40 % de viajes con vuelo y la mitad de las reservas iniciadas por WhatsApp (EV-08). Precios "
        "on-demand publicados en octubre de 2026, sin impuestos.")
    aws = [
        ("EC2 t4g.small", "USD 0,0168/h × 730 h", "12,26"), ("EBS gp3 30 GB", "USD 0,08/GB-mes × 30", "2,40"),
        ("Snapshots incrementales", "≈ 20 GB-mes × USD 0,05", "1,00"), ("IPv4 pública", "USD 0,005/h × 730 h", "3,65"),
        ("S3 (dumps cada 6 h, retención escalonada)", "≈ 6 GB × USD 0,023", "0,14"), ("Route 53", "1 zona alojada", "0,50"),
        ("CloudWatch", "3 métricas personalizadas × USD 0,30; alarmas en capa gratuita", "0,90"), ("Transferencia de salida", "< 100 GB (gratuita)", "0,00"),
        ("**Total AWS**", "", "**20,85 ≈ $19.800**"),
    ]
    r.table("h_aws", "Costo mensual de AWS", ["Ítem", "Cálculo", "USD/mes"], aws, [4.6, 8.6, 3.4], font=8,
            source="Amazon Web Services (2026a).")
    wa = [
        ("Plantillas de utilidad (reservas que no parten con mensaje del pasajero)", "756 × (USD 0,02 Meta + 0,005 Twilio)", "18,90"),
        ("Mensajes de sesión por reserva (5 salientes + 2 entrantes)", "1.512 × 7 × USD 0,005", "52,92"),
        ("Chat con el despachador (4 mensajes promedio)", "1.512 × 4 × USD 0,005", "30,24"),
        ("Recordatorios con ventana cerrada (20 % de reservas)", "302 × USD 0,025", "7,55"),
        ("**Total WhatsApp vía Twilio**", "", "**109,61 ≈ $104.100**"),
        ("Referencia: SMS (3 por reserva)", "4.536 × USD 0,0797", "361,52 ≈ $343.400"),
        ("Referencia: Cloud API directa (solo Meta)", "(756 + 302) × USD 0,02", "21,16 ≈ $20.100"),
    ]
    r.table("h_wa", "Costo mensual de mensajería", ["Ítem", "Cálculo", "USD/mes"], wa, [7.0, 6.2, 3.4], font=8,
            source="Twilio (2026a, 2026b) y Meta Platforms (2025): utilidad en Chile USD 0,02; mensajes de servicio y plantillas de utilidad dentro de la ventana de 24 h sin cobro de Meta.")
    r.P("**J.2 Consultas a la API de vuelos.** ≈ 605 viajes con vuelo al mes × 10 consultas (consulta inicial; 3 h, 2,5 h, 2 h, 1,5 h y 1 h antes; "
        "cada 10 min en la última hora) ≈ 6.050 consultas, menos las compartidas por vuelos repetidos. Presupuesto: USD 30/mes, conservador frente "
        "a las tarifas por consulta de AeroAPI (FlightAware, 2026) y a los planes de AeroDataBox (2026); se confirma al contratar.")
    r.P("**J.3 Matrices de decisión con puntaje por criterio** (escala 1–5; puntaje = Σ nota × peso).")
    mats = [
        ("Backend", "Dominio del equipo 30 · Geoespacial 20 · Tiempo real 20 · Seguridad 15 · Productividad 15",
         "Django 5-5-4-5-4 = 4,65 · NestJS 3-3-5-3-4 = 3,55 · FastAPI 4-3-4-3-3 = 3,50 · Spring Boot 2-3-4-5-3 = 3,20"),
        ("Base de datos", "Proximidad 35 · Integridad 25 · Costo 20 · Experiencia 20",
         "PostgreSQL+PostGIS 5-5-5-4 = 4,80 · MySQL 3-5-5-4 = 4,10 · MongoDB 4-2-4-2 = 3,10"),
        ("Frontend", "Reutilización con la app 35 · Experiencia 25 · Mapas 20 · Rendimiento 20",
         "React 5-5-5-4 = 4,80 · Angular 3-2-4-4 = 3,15 · Plantillas Django 1-4-3-4 = 2,75"),
    ]
    r.table("h_mat", "Detalle de matrices resumidas en la Tabla {T:m_stack}", ["Decisión", "Criterios (peso %)", "Notas por criterio y puntaje"], mats,
            [2.4, 6.4, 7.8], font=8)

    r.P("**J.4 Modelo comercial y punto de equilibrio.** Respaldo de las cifras de la sección 3.1. Supuestos: precios sin IVA; costo variable "
        "de $88 por reserva ($87,6 = 132.500 ÷ 1.512: $68,8 de WhatsApp y $18,8 de vuelos); costos fijos de plataforma de $31.150 al mes; "
        "$8.000 al mes por cada cliente adicional; tarifa media de $12.000 y margen neto supuesto de 25 % por viaje.")
    r.table("j_tope", "Margen de contribución de cada plan en su tope de reservas (peor caso)", ["Plan", "Tope de reservas", "Precio mensual", "Consumo en el tope", "Contribución mínima", "Reservas que dejan contribución cero"], [
        ("Inicial", "350", "$59.000", "$30.800", "$28.200", "670 (59.000 ÷ 88)"),
        ("Estándar", "1.000", "$129.000", "$88.000", "$41.000", "1.465"),
        ("Avanzado", "1.800", "$199.000", "$158.400", "$40.600", "2.261"),
    ], [2.2, 2.2, 2.4, 2.8, 2.8, 4.2], font=8)
    r.P("En los tres planes el tope de reservas queda muy por debajo del volumen en que la contribución se haría cero, y cada reserva sobre el "
        "tope se cobra a $120, con $32 de margen. El precio de la licencia cubre además el costo de la puesta en marcha: unas 12 horas "
        "(configuración 3 h, carga de datos 3 h y capacitación 6 h), que al valor hora del presupuesto ($1.500.000 ÷ 108 h ≈ $13.900) son "
        "≈ $167.000, menos que la licencia más baja ($200.000).")
    import data_van as dv
    filas_cart = []
    for nombre, lista in (("1 Avanzado (cliente actual)", ["A"]),
                          ("Año 1: 2 Avanzado + 1 Estándar + 1 Inicial", dv.CARTERA[1]),
                          ("Año 2: 3 Avanzado + 2 Estándar + 2 Inicial", dv.CARTERA[2]),
                          ("Año 3: 4 Avanzado + 3 Estándar + 3 Inicial", dv.CARTERA[3])):
        lic, contrib, fijos, res = dv.resumen_cartera(lista)
        acum = lic + 24 * res
        filas_cart.append((nombre, dv.pesos(lic), dv.pesos(contrib), dv.pesos(fijos), dv.pesos(res), dv.pesos(acum),
                           f"{acum / dv.INV_VALORIZADA * 100:.1f} %".replace(".", ",")))
    r.table("j_cartera", "Resultado de FlotaÁgil según la cartera de clientes", ["Cartera", "Licencias (único)", "Contribución mensual", "Costos fijos mensuales", "Resultado mensual", "Acumulado a 24 meses", "Inversión recuperada"],
            filas_cart, [4.2, 2.0, 2.2, 2.2, 2.0, 2.2, 1.8], font=7.8,
            source="Elaboración propia. Clientes con el volumen de ejemplo de la Tabla {T:equil}; acumulado = licencias + 24 × resultado mensual, con toda la cartera activa desde el primer mes; inversión valorizada de $14.047.000.")
    r.table("j_flotas", "Beneficio mensual del cliente según el tamaño de su flota", ["Flota y plan", "Reservas al mes", "Reservas recuperadas (7,1 %)", "Margen neto (25 %)", "Caja recuperada (30 %)", "Plan", "Beneficio neto", "Licencia recuperada en", "Pesimista: margen de 20 %, sin caja"], [
        ("10 vehículos · Inicial", "350", "25", "$75.000", "$72.000", "$59.000", "$88.000", "2,3 meses", "$60.000 − $59.000 = $1.000"),
        ("25 vehículos · Estándar", "900", "64", "$192.000", "$185.000", "$129.000", "$248.000", "1,4 meses", "$153.600 − $129.000 = $24.600"),
        ("40 vehículos · Avanzado", "1.512", "107", "$321.000", "$310.500", "$199.000", "$432.500", "1,2 meses", "$256.800 − $199.000 = $57.800"),
    ], [2.6, 1.3, 1.7, 1.6, 1.7, 1.4, 1.5, 1.6, 3.2], font=7.4,
            source="Elaboración propia. El descuadre de caja se supone proporcional al número de reservas ($1.035.000 para 1.512).")
    r.P("**Cloud API.** Si la mensajería se envía por la Cloud API directa de Meta, el costo de WhatsApp del cliente actual baja de $104.000 a "
        "≈ $20.100 al mes y el costo variable total de ≈ $88 a ≈ $32 por reserva (48.600 ÷ 1.512). El resultado con un solo cliente Avanzado "
        "pasa de $35.350 a $119.250 al mes. Con CC-19, que retira WhatsApp y Twilio, esta alternativa deja de ser necesaria.")

    import data_van as dv
    r.P("**J.5 Flujo de caja proyectado a tres años.** Respaldo de la {T:van_res}. Tasa de descuento de 12 % anual; flujos al cierre de cada "
        "año; año 0 = puesta en marcha. Consumo por cliente con la operación actual: $132.500 (Avanzado, volumen del cliente actual), "
        "$79.200 (Estándar, 900 reservas) y $30.800 (Inicial, 350 reservas); con CC-19: $29.500, $18.000 y $7.000 (≈ $20 por reserva). "
        "Costos fijos: $31.150 al mes más $8.000 por cada cliente adicional. Cartera activa: tres clientes nuevos por año, uno de cada plan; "
        "año 1, el cliente actual más 1 Avanzado, 1 Estándar y 1 Inicial (4); año 2, 7; año 3, 4 Avanzado, 3 Estándar y 3 Inicial (10). Cada "
        "cliente nuevo paga su licencia el año en que se incorpora. "
        "El escenario con CC-19 es una proyección de la versión 1.1 e incluye su desarrollo como inversión del año 1 ({T:j_cc19}).")
    r.table("j_cc19", "Estimación del desarrollo de CC-19 (proyección v1.1)", ["Componente", "Horas"],
            [(t, str(h)) for t, h in dv.CC19_TAREAS] + [
                ("**Total de horas**", f"**{dv.CC19_HORAS}**"),
                (f"Costo: {dv.CC19_HORAS} h × {dv.pesos(dv.TARIFA_HORA)} (tarifa del presupuesto: $1.500.000 ÷ 108 h) + 10 % de imprevistos", f"**{dv.pesos(dv.CC19_COSTO)}**"),
            ], [13.6, 3.0], font=7.8,
            source="Elaboración propia. Estimación previa a la planificación detallada de la versión 1.1; equivale a cerca de un sprint y medio del equipo.")
    for esc, tid in (("actual", "j_flujo_act"), ("cc19", "j_flujo_cc19")):
        filas = dv.detalle_flotaagil(esc)
        rows = [(str(f["anio"]), str(f["clientes"]), dv.pesos(f["planes"]), dv.pesos(-f["consumo"]), dv.pesos(-f["fijos"]),
                 dv.pesos(f["licencias"]), dv.pesos(f["inversion"]), "**" + dv.pesos(f["flujo"]) + "**", dv.pesos(f["acumulado"]),
                 dv.pesos(f["descontado"]), dv.pesos(f["acum_desc"])) for f in filas]
        r.table(tid, "Flujo de caja de FlotaÁgil · " + dv.ESCENARIOS[esc],
                ["Año", "Clientes", "Planes", "Consumo", "Costos fijos", "Licencias", "Inversión", "Flujo neto", "Acumulado", "Descontado (12 %)", "Acumulado descontado"],
                rows, [0.9, 1.2, 1.7, 1.6, 1.5, 1.5, 1.8, 1.8, 1.8, 1.7, 1.8], font=6.8,
                source="Elaboración propia. Planes, consumo y costos fijos anuales (12 × mensual).")
    rows = []
    for clave in ("meta", "prudente"):
        f = dv.flujos_cliente(clave)
        rows.append((dv.CLIENTE[clave]["desc"], *[dv.pesos(x) for x in f], dv.pesos(dv.van(f)), dv.tir_texto(f), dv.periodo(dv.pri(f))))
    r.table("j_flujo_cli", "Flujo de caja del cliente actual (plan Avanzado)", ["Escenario", "Año 0", "Año 1", "Año 2", "Año 3", "VAN 12 %", "TIR", "PRI"],
            rows, [4.0, 1.5, 1.6, 1.6, 1.6, 1.7, 2.6, 1.6], font=7.2,
            source="Elaboración propia. Año 0: licencia; años 1 a 3: 12 × beneficio neto mensual (meta $432.500; prudente $57.800, Tabla {T:sens}). "
                   "La TIR del escenario meta no es significativa porque la inversión inicial es mínima frente al beneficio anual.")
    da, dc = dv.flujos_flotaagil("actual", dv.INV_DESEMBOLSO), dv.flujos_flotaagil("cc19", dv.INV_DESEMBOLSO)
    r.P("**Evaluación sobre el desembolso.** Si en el año 0 se considera solo el desembolso de $847.000 ($770.000 más 10 % de imprevistos), "
        f"el VAN al 12 % es {dv.pesos(dv.van(da))} con la operación actual y {dv.pesos(dv.van(dc))} con CC-19; la TIR no es significativa "
        "con una inversión inicial tan baja. La evaluación principal usa la inversión valorizada porque las horas del equipo tienen un costo de "
        "oportunidad, aunque no sean un gasto.")

    # ---------------- I
    AH(r, "Anexo K. Glosario")
    r.P("Términos técnicos y de negocio usados en el informe, en orden alfabético.")
    gl = [
        ("APK", "Archivo instalable de una aplicación Android; formato en que se distribuye la app del conductor."),
        ("API REST", "Interfaz que expone las operaciones del sistema sobre HTTP mediante mensajes JSON."),
        ("Capacitor", "Framework que empaqueta una aplicación web como aplicación móvil instalable, con acceso a funciones nativas mediante plugins."),
        ("Celery", "Sistema de tareas en segundo plano: un worker ejecuta las tareas encoladas y beat lanza las periódicas."),
        ("Convenio corporativo", "Acuerdo con una organización cliente que le permite solicitar traslados con un acceso propio."),
        ("Definition of Done (DoD)", "Condiciones que un incremento debe cumplir para considerarse terminado."),
        ("Definition of Ready (DoR)", "Condiciones que una historia debe cumplir antes de entrar a un sprint."),
        ("Despacho", "Proceso por el que una reserva se asigna a un conductor disponible."),
        ("Doble de prueba", "Imitación controlada de un servicio externo (por ejemplo, Twilio) usada en las pruebas automáticas."),
        ("Escenario greenfield", "Contexto sin sistemas heredados que condicionen el diseño."),
        ("Geolocalización en segundo plano", "Capacidad de la app de seguir enviando la ubicación cuando no está en pantalla."),
        ("Historia de usuario (HU)", "Requerimiento descrito desde la perspectiva del usuario y su beneficio."),
        ("JWT", "Token firmado que transporta la identidad y los permisos del usuario autenticado."),
        ("Multiempresa (multi-tenant)", "Una sola instancia de software que atiende a varias organizaciones con sus datos aislados."),
        ("MVP", "Producto mínimo viable: versión con el mínimo de funciones que entrega valor y permite validar la solución."),
        ("PostGIS", "Extensión de PostgreSQL con tipos y funciones geoespaciales e índices espaciales."),
        ("Pull request (PR)", "Solicitud para incorporar los cambios de una rama a la rama principal, con revisión de otro integrante."),
        ("RBAC", "Control de acceso basado en roles."),
        ("SaaS", "Software ofrecido como servicio en la nube, sin infraestructura local del cliente."),
        ("SLA", "Acuerdo de niveles de servicio, como disponibilidad y tiempos de respuesta."),
        ("Sprint", "Iteración de duración fija de Scrum, al final de la cual se entrega un incremento usable."),
        ("Story point (SP)", "Unidad relativa de estimación del esfuerzo de una historia."),
        ("Taxi turismo", "Transporte de pasajeros en vehículos de patente naranja, orientado a traslados turísticos, corporativos y de aeropuerto."),
        ("Tiempo muerto", "Tiempo en que un vehículo está conectado sin transportar pasajeros."),
        ("WebSocket", "Protocolo de comunicación bidireccional y persistente, usado para posiciones y estados en vivo."),
        ("Compuerta basada en eventos", "Elemento BPMN que espera el primero de varios eventos posibles y sigue el camino del que ocurra."),
        ("ETA", "Hora estimada de llegada de un vuelo informada por el proveedor de datos."),
        ("Fila virtual", "Orden de salida de los conductores que esperan en el aeropuerto, según su hora de ingreso a la geocerca."),
        ("Geocerca", "Polígono geográfico que delimita una zona y permite detectar entradas y salidas de vehículos."),
        ("Plantilla de WhatsApp", "Mensaje preaprobado por Meta, obligatorio para iniciar conversaciones fuera de la ventana de servicio."),
        ("Ventana de servicio", "Período de 24 horas desde el último mensaje del usuario en que la empresa puede responder libremente por WhatsApp."),
        ("Webhook", "Llamada HTTP que un servicio externo hace a la plataforma para avisar un evento, como una respuesta del pasajero."),
        ("RTO / RPO", "Tiempo máximo para restablecer un servicio / máxima pérdida de datos tolerable, expresada en tiempo."),
        ("Snapshot", "Copia puntual de un volumen de disco, usada para restaurar la máquina completa."),
        ("Monolito modular", "Aplicación desplegada como una unidad pero dividida internamente en módulos con responsabilidades separadas."),
        ("Puertos y adaptadores", "Patrón que aísla el núcleo de la aplicación de los proveedores externos mediante interfaces propias."),
        ("Marcha blanca", "Período inicial de operación real con apoyo intensivo y procedimientos de respaldo."),
        ("Licencia perpetua de uso", "Derecho a usar el software por tiempo indefinido, sin recibir el código fuente ni los derechos de autor; no es exclusiva ni transferible."),
        ("Margen neto por viaje", "Lo que le queda a la empresa de la tarifa después de los costos directos del traslado (combustible, peajes, parte del conductor y desgaste)."),
        ("Margen de contribución", "Ingreso de un cliente menos los costos que varían con su uso; es lo que aporta para cubrir los costos fijos."),
        ("Punto de equilibrio", "Nivel de actividad en que los ingresos igualan a los costos: ni se gana ni se pierde."),
        ("Turno", "Jornada de un conductor con un vehículo, desde que empieza hasta que termina; se registra en la entidad TURNO."),
        ("Cierre de caja", "Cuadratura de un turno: comparación entre el efectivo registrado por el sistema y el que rinde el conductor."),
        ("Staging", "Ambiente de pruebas equivalente a producción, usado para carga, seguridad y recuperación."),
        ("Concurrencia", "Situación en que dos operaciones ocurren al mismo tiempo sobre el mismo dato; el sistema debe garantizar que solo una se concrete."),
        ("Reserva de contingencia", "Reserva ingresada después de una caída del sistema a partir de la planilla en papel, identificada por su folio."),
    ]
    gl.sort(key=lambda x: x[0].lower().replace("é", "e"))
    r.table("glos", "Glosario", ["Término", "Definición"], gl, [4.0, 12.6], font=8)

    # ---------------- J
    AH(r, "Anexo L. Procedimientos operativos y formularios")
    po = [
        ("PO-01 Despliegue", "1) Fusionar a main con CI en verde. 2) Crear tag vX.Y.Z; Actions construye y publica imágenes. 3) En la instancia: "
         "docker compose pull con la nueva etiqueta. 4) docker compose run api python manage.py migrate. 5) Reinicio contenedor por contenedor. "
         "6) Prueba de humo (CP-34). 7) Registrar en el issue de la release.", "Carlos", "Humo OK; release registrada"),
        ("PO-02 Restauración", "1) Declarar contingencia y activar la planilla con folio. 2) Elegir el respaldo válido más reciente: snapshot (03, 09, 15 y 21 h) "
         "o pg_dump (00, 06, 12 y 18 h). 3) Lanzar la instancia desde el snapshot o, si el volumen está comprometido, una instancia nueva con "
         "pg_restore del dump. 4) Cargar parámetros SSM y levantar con el tag vigente. 5) Reasociar la Elastic IP. 6) Validar con humo y conteos "
         "de control. 7) Registrar la hora del respaldo usado (RPO real) y la del restablecimiento (RTO real). 8) Seguir con PO-06.", "Carlos (Renato de respaldo)", "Conteos iguales al respaldo; servicio en < 2 h; pérdida ≤ 6 h"),
        ("PO-03 Reversión de versión", "1) Detectar falla en humo o alertas. 2) Volver a la etiqueta anterior en compose. 3) Si la migración no es "
         "reversible: restaurar el dump previo al despliegue. 4) Humo. 5) Abrir defecto.", "Carlos", "Versión anterior operativa"),
        ("PO-04 Rotación de secretos", "1) Generar nuevo secreto en el proveedor. 2) Actualizar SSM. 3) Reiniciar contenedores. 4) Revocar el anterior. "
         "5) Registrar en AUDITORIA o en el issue.", "Carlos", "Servicio operativo con el nuevo secreto"),
        ("PO-05 Purga y retención", "Tarea diaria de Celery: elimina POSICION_GPS > 30 días, MENSAJE_WHATSAPP > 12 meses y anonimiza viajes > 24 meses; "
         "registra filas afectadas.", "Automático; revisa Carlos", "Registro de la tarea sin errores"),
        ("PO-06 Retorno al servicio y carga diferida", "1) El líder declara el fin de la contingencia; la operación vuelve al sistema. 2) El despachador cierra con "
         "cierre o anulación forzada (HU-05) los viajes que estaban en curso al fallar. 3) Ingresa cada fila de la planilla como «Reserva de "
         "contingencia» con su folio C-NNN, horas reales, conductor, estado final y pago. 4) Si se restauró un respaldo, reconstruye las reservas "
         "creadas entre la hora del respaldo y la falla a partir del historial de mensajes de Twilio y del cuaderno de la central, con folios "
         "R-NNN. 5) Emite el reporte de conciliación: folios de la planilla frente a reservas ingresadas, y suma de montos. 6) El administrador "
         "revisa, firma y archiva la planilla. 7) Los cobros entran al cierre de caja del turno (PO-07). Plazo: 24 h desde el restablecimiento.",
         "Despachador de turno; revisa el administrador", "Folios y montos conciliados al 100 %; registro en AUDITORIA"),
        ("PO-07 Cierre de caja del turno", "1) El conductor termina el turno y revisa sus totales en «Mi turno». 2) El administrador abre el cierre del turno; el "
         "sistema muestra el efectivo registrado. 3) Cuenta el efectivo que entrega el conductor. 4) Ingresa el monto rendido. 5) Si hay "
         "diferencia, escribe la observación. 6) Confirma; el sistema guarda el CIERRE_CAJA y lo deja en auditoría. Un turno se cierra una sola vez.",
         "Administrador", "Cierre registrado; KPI-05 del día calculado"),
    ]
    r.table("po", "Procedimientos operativos", ["Procedimiento", "Pasos", "Responsable", "Verificación"], po, [2.8, 9.6, 2.2, 2.0], font=7.6)
    r.kv_table("rfc", "Formulario de solicitud de cambio (plantilla de issue «Solicitud de cambio»)", [
        ("Código", "CC-NN (asignado por el líder)"), ("Solicitante y fecha", "Nombre y rol de quien pide el cambio; fecha de la solicitud"), ("Descripción del cambio", "Qué se modifica y en qué entregable"), ("Motivo y beneficio", "Problema que resuelve y valor esperado"),
        ("Elementos afectados", "HU, componentes, datos, documentos, SLA"), ("Clasificación", "Estándar / Normal / Emergencia"),
        ("Impacto", "Alcance (SP) · Tiempo · Costo · Calidad · Riesgos"), ("Decisión", "Aprobado / Rechazado / Diferido — quién y cuándo"),
        ("Programación", "Sprint o ventana"), ("Pruebas y reversión", "Casos de prueba que deben aprobarse y forma de deshacer el cambio"), ("Cierre", "Resultado, fecha, documentación actualizada"),
    ], font=8)
    r.kv_table("planilla", "Planilla de contingencia (una fila por viaje; se usa mientras el sistema no está disponible)", [
        ("Folio", "C-NNN correlativo de la planilla; R-NNN para lo reconstruido de la ventana del respaldo"),
        ("Solicitud", "Fecha y hora en que se recibió; canal (teléfono o WhatsApp)"), ("Pasajero", "Nombre y teléfono; convenio, si corresponde"),
        ("Viaje", "Origen, destino, sentido, número de vuelo y hora de recogida"), ("Asignación", "Conductor, patente y hora en que aceptó por teléfono"),
        ("Resultado", "Finalizado o cancelado; hora de término; motivo si se canceló"), ("Cobro", "Método de pago y monto, según el formulario del conductor"),
        ("Anotó", "Despachador que registró la fila"), ("Ingreso al sistema", "Fecha, hora y usuario que la ingresó como reserva de contingencia; visto bueno del administrador"),
    ], font=8)
    r.kv_table("inc", "Formulario de registro de incidente (plantilla de issue «Incidente»)", [
        ("Identificador", "INC-AAAA-NNN"), ("Detección", "Fecha y hora; alerta automática o usuario que reporta"), ("Servicio y componente", "SLA afectado; componente"),
        ("Descripción y evidencia", "Síntoma, capturas, enlaces a Sentry/logs"), ("Impacto · Urgencia · Prioridad", "Según la matriz de 8.3"),
        ("Responsable", "Guardia asignada"), ("Bitácora de acciones", "Hora y acción, incluidos escalamientos y comunicaciones"),
        ("Restablecimiento", "Hora; solución temporal o definitiva; validación"), ("Causa raíz y cierre", "Causa; HU o tarea derivada; ¿incidente repetido?"),
    ], font=8)

    # ---------------- K
    AH(r, "Anexo M. Informe técnico de la prueba de concepto de GPS en segundo plano (H-3)")
    r.P("**Objetivo.** Comprobar, antes de construir HU-02, HU-04 y HU-29, que un teléfono Android sigue registrando la ubicación del conductor "
        "con la aplicación en segundo plano y la pantalla apagada (riesgo R-01). Se construyó una aplicación de prueba sobre el mismo stack de la "
        "app del conductor. El informe completo, con cada sesión, está en el repositorio "
        "(docs/poc-gps.md).")
    r.kv_table("h3_conf", "Configuración de la prueba", [
        ("Teléfono (T1)", "Xiaomi 14T · Android 16 · Xiaomi HyperOS 3.0 (una de las capas más restrictivas con las apps en segundo plano)"),
        ("Aplicación", "React 19.3 + Vite 6.4 + TypeScript; Capacitor 7.6.9; plugin @capacitor-community/background-geolocation 1.2.26 (MIT); appId cl.flotaagil.conductor; Android 10+ (minSdk 29, targetSdk 35)"),
        ("Muestreo", "El plugin entrega una posición por segundo (distanceFilter 0, para que un conductor detenido siga generando posiciones); la app registra una cada 10 s en modo «En viaje» y cada 30 s en modo «En espera», que es lo que enviaría la app real"),
        ("Registro", "CSV de posiciones y de eventos dentro del teléfono, exportable; la PoC no envía datos a ningún servidor. Al repositorio se suben versiones anonimizadas, sin coordenadas, altitud ni rumbo"),
        ("Consentimiento", "Pantalla de consentimiento informado antes de la primera sesión y notificación fija mientras se registra (RN-18)"),
        ("Diagnóstico", "Registro del sistema capturado por USB y un «latido» nativo cada 5 s en las versiones de depuración, para distinguir si se detiene solo el JavaScript o el proceso completo"),
    ], font=8)
    crit = [
        ("C1", "Intervalo en viaje de 10 s", "Capítulo II (persistencia cada 10 s en viaje)", "Pendiente (prueba E3)"),
        ("C2", "Intervalo en espera de 30 s", "Capítulo II (cada 30 s en espera)", "Cumple en E2 parcial: mediana 30,0 s; p95 33,3 s"),
        ("C3", "Ningún hueco > 60 s con la pantalla apagada", "HU-02 (posición > 60 s = no confiable)", "Cumple en D3 y E2 parcial: máximo 34,9 s"),
        ("C4", "Datos < 50 MB por turno de 8 h", "RNF-07", "Cumple por estimación: 0,16 MB por turno; la medición real queda para HU-02"),
        ("C5", "Precisión p95 ≤ 50 m", "Propuesta del equipo (geocerca EN_ZONA de 150 m)", "Cumple: mediana 3,4 m; p95 11,9 m"),
        ("C6", "Consumo de batería", "Sin meta; se registra", "≈ 6,8 %/h (3 % en 26,6 min; baja resolución)"),
    ]
    r.table("h3_crit", "Criterios de éxito de H-3 y resultado preliminar", ["ID", "Criterio", "Origen", "Resultado de la prueba de concepto (semana 7)"], crit, [1.0, 4.6, 5.0, 6.0], font=8)
    diag = [
        ("D1", "Sin ajustes; ahorro de batería de la app sin confirmar", "Android entregó posiciones cada segundo, pero el JavaScript dejó de recibirlas ≈ 60 s después de pasar a segundo plano; llegaron todas juntas al reabrir (hueco ≈ 225 s)", "No pasa"),
        ("D2", "Prioridad del proceso de render del WebView", "Mismo comportamiento: hueco de 348,9 s", "No pasa"),
        ("D3", "Ventana del WebView informada como visible al pasar a segundo plano + HyperOS configurado (sin restricciones de batería, inicio automático, candado en recientes)", "JavaScript activo todo el periodo; latido nativo continuo; 9 muestras con la pantalla apagada; máximo 34,8 s", "Pasa"),
        ("D3b", "Solo HyperOS configurado, sin el ajuste del WebView", "El JavaScript se suspende igual; hueco de 260,7 s; el proceso nativo no se congela", "No pasa"),
        ("E2 parcial", "Versión final (ajuste del WebView + HyperOS configurado), sin cable, modo espera", "26,6 min con la pantalla apagada; 53 muestras; sin huecos; precisión p95 11,9 m", "Pasa"),
        ("E4", "Cerrar la app deslizándola desde recientes", "El registro se detiene y no se reanuda solo; al reabrir, la app marca la sesión como interrumpida", "Comportamiento aceptado (CC-11)"),
    ]
    r.table("h3_diag", "Sesiones de diagnóstico y prueba", ["Sesión", "Condición", "Resultado observado", "Veredicto"], diag, [1.6, 5.0, 7.6, 2.4], font=7.8)
    r.figure("fig/h3_intervalos.png", "h3", "Intervalo máximo sin posición con la pantalla apagada en cada sesión; D1 y D2, marcadas con asterisco, se hicieron sin confirmar el ahorro de batería de la app", width_cm=15.6)
    r.P("**Conclusión preliminar.** El proceso nativo de la app nunca se congeló; lo que se suspende es el WebView, donde corre el JavaScript, "
        "unos 60 segundos después de que la app pasa a segundo plano. El ajuste que informa al WebView que su ventana sigue visible "
        "(*dispatchWindowVisibilityChanged* en *MainActivity.onStop*) es necesario y, junto con la configuración recomendada del teléfono, "
        "suficiente en T1. **Se mantiene el plugin previsto**: no hace falta un módulo nativo propio ni cambiar el stack. Si el conductor cierra la "
        "app, el registro se detiene; el equipo decidió aceptarlo con tres mitigaciones: guiar al conductor para bloquear la app en recientes, "
        "reanudar la sesión al reabrir si el turno sigue activo y marcar al conductor como «sin señal» en el panel tras 60 s sin posiciones (HU-02).")
    adj = [
        ("A1", "Consumo de batería", "≈ 6,8 %/h con el GPS a 1 Hz, cerca de 54 % en un turno de 8 h; confirmar con las pruebas de 60 min", "HU-02, HU-13 · R-16"),
        ("A2", "Intervalo nativo del GPS", "Pedir posiciones cada 10 s en viaje y cada 30 s en espera en vez de cada segundo; verificar que no aparezcan huecos", "HU-02, HU-13"),
        ("A3", "Dependencia del ajuste del WebView", "Puede dejar de funcionar con una actualización del WebView o de Capacitor; repetir el diagnóstico tras cada actualización", "Mantención"),
        ("A4", "Configuración del teléfono", "La app real debe guiar al conductor para dejar sin restricciones de batería, inicio automático y candado; falta medir qué pasa sin esa configuración (E2b)", "HU-13"),
        ("A5", "Cierre de la app", "Registro detenido; mitigado con reanudación al reabrir y umbral de 60 s en el panel", "HU-02, HU-13 · CC-11"),
        ("A6", "Representatividad", "Un solo teléfono y fabricante; falta un segundo teléfono de otra marca", "Pruebas de compatibilidad"),
        ("A7", "Posiciones de baja precisión", "Al iniciar bajo techo hubo posiciones de ±88 a ±1.400 m durante 9 min; no deben usarse para la geocerca", "Aplicado: DC-16 (solo posiciones ≤ 50 m marcan la llegada) y marca de precisión > 100 m en el mapa"),
    ]
    r.table("h3_adj", "Ajustes y riesgos que se trasladan a la app real", ["ID", "Tema", "Detalle", "Dónde se aborda"], adj, [1.0, 3.4, 8.6, 3.6], font=7.8)
    r.P("**Sesión de uso normal (S1).** Además de las pruebas controladas, una sesión de uso normal de 94 minutos se registró sin huecos. "
        "**Decisión aplicada en la app real:** el registro con la app cerrada no se exige; la app base retoma la sesión al reabrirla si el turno "
        "sigue activo y el panel marca como no confiable toda posición de más de 60 s (HU-02). "
        "**Pendiente para cerrar H-3:** prueba de 60 minutos con el teléfono quieto y la pantalla apagada (E2 completa), prueba de 60 minutos en "
        "movimiento (E3), la misma prueba sin configurar el teléfono (E2b) y una repetición en un teléfono de otro fabricante.")

    # ---------------- L
    AH(r, "Anexo N. Ecosistema de desarrollo implementado (Sprint 0)")
    r.P("El Sprint 0 dejó operativo el entorno en el que se construyeron y se controlan todas las historias. La {T:eco} resume lo configurado "
        "y cómo se verificó. Las figuras muestran el tablero al cierre del Sprint 0. En la semana 14 el repositorio pasó a la organización "
        "*Flotaagil-CL* con su historial, issues, tablero y ruleset (DC-49); al corte, las historias construidas están en la columna «Hecho» y la "
        "tarea H-3 sigue «En curso», a la espera de la prueba en un teléfono real.")
    eco = [
        ("Organización", "flotaagil (desde la semana 14, Flotaagil-CL), con verificación en dos pasos obligatoria, permiso base de solo lectura y sin creación de repositorios por los miembros", "Lectura de la configuración por API"),
        ("Repositorio", "flotaagil/flotaagil (desde la semana 14, Flotaagil-CL/flotaagil), público; carpetas backend/, web/, app/, infra/ y docs/ con su responsable; .gitignore que impide subir secretos, llaves de firma y evidencias sin anonimizar", "Primer commit en main"),
        ("Protección de main", "Ruleset «Proteger main»: sin push directo ni borrado; pull request con 1 aprobación, resolución de conversaciones y fusión squash; check «ci» obligatorio; historial lineal. En el repositorio nuevo el ruleset no tiene excepciones y la revisión cruzada es un acuerdo de trabajo con lista de chequeo (DC-47)", "Push directo de prueba rechazado (GH013)"),
        ("Integración continua", "GitHub Actions: título del PR en Conventional Commits; backend con Ruff, Bandit y pytest con cobertura ≥ 70 % sobre PostgreSQL 16 + PostGIS 3.4 y Redis; web y app con ESLint, typecheck, Vitest y build; job final «ci» obligatorio", "Primer run en verde"),
        ("Seguridad", "Secret scanning con push protection, alertas y actualizaciones de seguridad de Dependabot, reporte privado de vulnerabilidades", "Configuración leída por API; Dependabot abrió 4 PR"),
        ("Plantillas", "Issues de historia, defecto, solicitud de cambio (RFC del Anexo L) e incidente; plantilla de pull request con la definición de terminado; CODEOWNERS", "Archivos en .github/"),
        ("Tablero Scrum", "Proyecto «FlotaÁgil — Backlog»: columnas Backlog, Sprint Backlog, En curso, En revisión y Hecho; campos Sprint, SP, Responsable, Épica y Prioridad; vistas Tablero y Por Sprint; 6 automatizaciones", "Figuras {F:tablero|n} y {F:porsprint|n}"),
        ("Backlog cargado", "25 HU y la tarea H-3 como issues, con criterios como lista de verificación, reglas de negocio, casos de prueba y dependencias enlazadas; 19 etiquetas; milestones Sprint 0 a Sprint 4", "45, 45, 42 y 46 SP por sprint; 178 SP; 89 SP por integrante"),
    ]
    r.table("eco", "Elementos del ecosistema de desarrollo", ["Elemento", "Configuración", "Verificación"], eco, [2.8, 9.8, 4.0], font=7.8)
    r.figure("fig/tablero.png", "tablero", "Vista Tablero del proyecto en GitHub al cierre del Sprint 0", width_cm=16.4, source="Captura de pantalla.")
    r.figure("fig/por_sprint.png", "porsprint", "Vista Por Sprint, con la suma de story points de cada sprint", width_cm=16.4, source="Captura de pantalla.")
    r.P("**Incidencia.** Al cargar el backlog, la creación de 27 issues en pocos segundos activó la detección automática de spam de GitHub y "
        "restringió la cuenta del integrante que ejecutó la carga: mientras dure, sus issues y pull requests no son visibles sin iniciar sesión "
        "y la integración continua no se ejecuta en sus pull requests. Se solicitó la revisión a GitHub (riesgo R-15) y a la fecha de corte "
        "no tuvo respuesta. Como medida de mitigación, en la semana 14 el repositorio se trasladó a la organización *Flotaagil-CL* con su "
        "historial, issues, tablero y ruleset, previo respaldo completo en un archivo *git bundle* (DC-49). En el repositorio nuevo la "
        "integración continua corre en todos los pull requests y las tarjetas son visibles para cualquier visitante.")
