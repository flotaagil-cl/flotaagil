from data_backlog import HU, RETIRADAS, NUEVAS
from datos import PRUEBAS, PRUEBAS_DETALLE, DC_MAX, DC_TOTAL, ENTIDADES


def intro(r):
    r.H1("Introducción", page_break=False)
    r.P("Este informe corresponde a la Evaluación Sumativa 2 del Proyecto de Título «FlotaÁgil», plataforma SaaS para la gestión de flotas de "
        "taxi turismo (vehículos de patente naranja). Presenta las tecnologías seleccionadas, la arquitectura, los indicadores y niveles de "
        "servicio, el plan de pruebas, el plan de implementación y el ajuste del cronograma, corregidos con la retroalimentación de la Evaluación "
        "Formativa 2 y actualizados al corte de la **semana 14** del proyecto (noviembre de 2026). La formulación del proyecto (organización, "
        "problema, levantamiento, objetivos y metodología) está en el Informe 1, corregido con la retroalimentación de la primera evaluación. La "
        "organización es una PYME de la Región Metropolitana que opera como transportista autorizado en el aeropuerto de Santiago, con una flota de 30 a 50 "
        "vehículos y cerca de 1.500 reservas mensuales, y que sostiene su operación en WhatsApp, planillas Excel y un cuaderno de caja.")
    r.P("El problema, medido sobre los registros de junio a agosto de 2026, se traduce en un 12,1 % de reservas perdidas (unos $2.196.000 "
        "mensuales de ingreso bruto), una asignación promedio de 8 min 40 s, un 35 % de tiempo muerto de la flota y un descuadre de caja de "
        "$34.500 diarios. El objetivo general es **desarrollar e implementar un MVP SaaS, compuesto por una plataforma web y una aplicación móvil "
        "interconectadas, que optimice la reserva, el despacho, la geolocalización y el registro de cobros**.")
    r.P("La solución combina un panel web para administración y despacho, un portal de solicitud para pasajeros y convenios, y una aplicación "
        "Android para conductores, sobre un backend Django con PostgreSQL/PostGIS, comunicación en tiempo real por WebSocket y tareas en segundo "
        "plano. Respecto de la formulación original incorpora tres cambios de fondo: la verificación y los avisos al pasajero pasan del SMS a "
        "WhatsApp Business API; se agrega el foco aeropuerto (seguimiento de vuelos, ajuste de la hora de recogida y fila virtual), surgido de una "
        "entrevista con el cliente; y el contacto con el pasajero se concentra en un chat de WhatsApp atendido desde el panel. A ellos se suma un "
        "cuarto, pedido por el cliente en la semana 14: el portal funciona con cuenta, de modo que el pasajero y la empresa con convenio piden "
        "con su propia cuenta, sin contraseñas compartidas y con el teléfono verificado una sola vez.")
    r.P("**Avance a la fecha de corte:** los Sprints 0 a 3 están terminados y el Sprint 4 está en curso. Están construidas, probadas e "
        "integradas en la rama principal las 25 historias del backlog validado (**178 SP**), las dos originadas en la EF2 (HU-31 y HU-32, 8 SP) "
        "y las trece que nacen de los cambios pedidos por el cliente en la semana 14 (HU-33 a HU-45, 72 SP, CC-16 a CC-18): inicio de sesión "
        "único, convenios con cuenta propia, administración de usuarios del panel, portal rediseñado en el que el pasajero pide siempre con "
        "cuenta, y perfil con eliminación de la cuenta. HU-46 a HU-49 quedan para la versión 1.1. El sistema cubre el ciclo completo: reserva "
        "desde el panel, el portal o la cuenta de un convenio, verificación del teléfono al activar la cuenta, validación y monitoreo del vuelo, "
        "despacho asistido con fila virtual del aeropuerto, aceptación en 60 s, ejecución con geocerca y pago, avisos y calificación, cierre "
        "forzado, turnos y cierre de caja, reportes, auditoría, indicadores y chat. "
        f"Suma **{PRUEBAS} pruebas automáticas** ({PRUEBAS_DETALLE}). "
        "Quedan las pruebas con servicios y teléfono reales, el despliegue en AWS y la UAT. El cliente aprobó además, para después de esta "
        "entrega, un chat interno que reemplaza a WhatsApp y a Twilio (CC-19) y la unificación visual y la apariencia por empresa (CC-20 y "
        "CC-21); se presentan como diseño, no como construido.")
    r.P("**Alcance vigente:** reserva (panel, portal, convenio y WhatsApp), verificación del pasajero, despacho asistido con confirmación humana, "
        "fila virtual del aeropuerto, monitoreo de vuelos, ejecución del viaje con estados, registro del cobro, cierre de caja por turno, reportes, "
        "auditoría y chat. **Exclusiones:** pasarelas de pago, definición de tarifas, facturación electrónica, aplicación nativa para pasajeros, "
        "despacho automático con inteligencia artificial, chatbot, enmascaramiento telefónico, aislamiento completo entre empresas y cuentas "
        "individuales para trabajadores de convenios. **Restricciones:** equipo de dos desarrolladores, 16 semanas, presupuesto de PYME y una sola "
        "instancia cloud.")
    r.P("El documento sigue la plantilla de la ES2: la selección de tecnologías con su factibilidad (capítulo II), la arquitectura con sus "
        "diagramas BPMN, UML, de datos, comunicaciones, infraestructura y arquitectura (III), los KPI y SLA (IV), el plan de pruebas y las "
        "normas (V), el plan de implementación con disponibilidad, continuidad y mantención (VI), el ajuste del cronograma (VII) y las "
        "conclusiones (VIII). Lo construido en cada sprint, con sus evidencias, pruebas y defectos, está en el Anexo P, y los requerimientos, "
        "reglas de negocio y riesgos vigentes, en el Anexo O. Donde algo es diseño todavía no construido, se indica de forma expresa. La "
        "sección 1.2 indica dónde se atendió cada observación de la EF2.")

    r.H2("Continuidad con la etapa anterior y registro de cambios")
    r.P("Esta entrega parte del backlog validado con el cliente el 28 de agosto de 2026 (Anexo C, evidencia EV-07). Las historias "
        "conservan su código; las fusionadas o eliminadas se marcan como retiradas y las nuevas se numeran desde HU-26. El backlog vigente suma "
        "**178 story points** frente a los 179 originales y a una capacidad de 180 en cuatro sprints; a ellos se agregan 8 SP de dos historias "
        "originadas en la retroalimentación de la EF2 (HU-31 y HU-32), incorporadas al Sprint 4, y las historias de los cambios CC-16 a CC-18 pedidos por el cliente en la semana 14. La {T:cambios} resume los cambios posteriores al acta; el detalle de cada "
        "solicitud, con su análisis de impacto, está en el Anexo D.")
    rows = [
        ("CC-01", "Verificación y avisos al pasajero: SMS → WhatsApp Business API (Twilio)", "Costo: el SMS estimado (~$343.000/mes) supera el valor del plan; el acta dejó pendiente esta migración", "HU-20, HU-21, HU-24, RN-06, RN-09, R-04", "Aprobado"),
        ("CC-02", "Foco aeropuerto: registro y monitoreo de vuelos, ajuste de recogida, alertas y fila virtual", "Necesidad planteada por el cliente en entrevista", "HU-26 a HU-29, HU-04, RN-16, RN-17, P2", "Aprobado"),
        ("CC-03", "Chat de WhatsApp en el panel reemplaza los enlaces wa.me", "Un solo hilo con la central; no expone el teléfono personal del conductor", "HU-30; retira HU-22 y HU-23", "Aprobado"),
        ("CC-04", "Fusión de los cuatro reportes en un módulo con filtros", "Misma consulta base; ahorro de 15 SP para absorber CC-02", "HU-06 (absorbe 07, 08, 09)", "Aprobado"),
        ("CC-05", "Nuevos estados PENDIENTE_CONFIRMACION y EN_ZONA", "Soportar la verificación por WhatsApp y el aviso «tu vehículo te espera»", "Anexo H, HU-16, HU-20", "Aprobado"),
        ("CC-06", "Disponibilidad comprometida 99,5 % → 99,0 % 24/7; RPO 24 h → 6 h", "Una sola instancia no sostiene 99,5 % (el SLA de AWS por instancia es 99,5 %)", "RNF-01, RNF-08, SLA", "Aprobado"),
        ("CC-07", "Proveedor definido: AWS us-east-1; PostgreSQL en contenedor en vez de servicio gestionado", "Costo y simplicidad; observación del docente sobre la ambigüedad AWS/GCP", "Infraestructura, presupuesto", "Aprobado"),
        ("CC-08", "Clientes web en React + Vite (antes plantillas Django)", "Mismo código base que la app Capacitor", "Componentes, herramientas", "Aprobado"),
        ("CC-09", "Roles Scrum: Product Owner Juan Pérez; líder de proyecto de la Unidad 2 Carlos Ortiz", "Scrum requiere al menos tres personas; rotación del liderazgo", "Equipo, roles Scrum", "Aprobado"),
        ("CC-10", "Marco legal actualizado: Ley 21.719, Código del Trabajo y normativa MTT", "Observación del docente sobre normativa y privacidad del GPS", "RN-18, RNF-09, normas", "Aprobado"),
        ("CC-11", "App del conductor: ajuste del WebView para registrar con la pantalla apagada; si el conductor cierra la app el registro se detiene, con mitigaciones", "Resultado de la prueba de concepto H-3 (Anexo M)", "HU-13, HU-02, R-01", "Aprobado e implementado"),
        ("CC-12", "Entidades TURNO y CIERRE_CAJA y pantalla de cierre de caja por turno; KPI-05 y KPI-08 reformulados", "Observación de la EF2: el modelo no soportaba la cuadratura (P3.2) ni los indicadores por turno", "HU-31, HU-18, HU-06, RN-19, P3.2, KPI-03, 04, 05 y 08, Anexo F", "Aprobado e implementado (HU-31)"),
        ("CC-13", "Modelo comercial: licencia perpetua de uso más plan de servicio mensual por tamaño de flota", "Vender el producto sin ceder el código; coherencia de la factibilidad económica (EF2)", "3.1, EMPRESA.plan, SLA, Anexo J", "Aprobado"),
        ("CC-14", "Respaldo lógico (pg_dump) cada 6 h en vez de diario, alternado con los snapshots", "Observación de la EF2: el respaldo diario no sostenía el RPO de 6 h", "RNF-08, SLA, 8.2, PO-02, CP-30", "Aprobado"),
        ("CC-15", "Canal CONTINGENCIA y procedimiento de carga diferida de los viajes anotados durante una caída", "Observación de la EF2: faltaba el retorno al servicio tras la contingencia manual", "HU-32, RN-20, VIAJE, 8.2, PO-06, CP-37", "Aprobado e implementado (HU-32)"),
        ("CC-16", "Inicio de sesión web único; convenios con cuenta propia y aprobación del administrador; cuenta del pasajero", "Pedido del cliente: un solo acceso y sin contraseñas compartidas por link", "HU-33, HU-34, HU-35; CONVENIO, CUENTA_PASAJERO, USUARIO", "Aprobado e implementado"),
        ("CC-17", "Administración de usuarios del panel por el administrador", "Pedido del cliente: no depender del equipo para crear despachadores", "HU-36, USUARIO, AUDITORIA", "Aprobado e implementado"),
        ("CC-18", "Cuenta obligatoria para pedir y rediseño del portal", "Seguridad: sin reservas de invitados; teléfono verificado una vez al crear la cuenta", "HU-37 a HU-49, RN-06, VIAJE, CUENTA_PASAJERO", "HU-37 a 45 implementadas; HU-46 a 49 en la versión 1.1"),
        ("CC-19", "Chat interno por WebSocket entre pasajero, central y conductor; verificación por correo; avisos por Web Push y correo; se retira Twilio", "Eliminar el costo y la dependencia de WhatsApp Business ahora que todos los usuarios tienen cuenta", "HU-20, 21, 24, 30; RN-06, RN-09; CONVERSACION, MENSAJE_CHAT", "Aprobado para la versión 1.1 (diseño)"),
        ("CC-20", "Unificación visual del panel y la app con el sistema del portal", "Consistencia entre los tres clientes", "Panel y app", "Aprobado para la versión 1.1"),
        ("CC-21", "Apariencia por empresa (logo, nombre y colores)", "Cada empresa cliente muestra su marca", "Portal (tokens de HU-37)", "Aprobado para la versión 1.1"),
    ]
    r.table("cambios", "Cambios respecto de la primera entrega", ["Código", "Cambio", "Motivo", "Elementos afectados", "Estado"], rows,
            [1.2, 4.8, 4.8, 3.4, 2.4], font=8)

    r.H2("Observaciones de la Evaluación Formativa 2 y su tratamiento")
    r.P("La retroalimentación de la EF2 (84,67 de 100) destacó los diagramas BPMN, la matriz comparativa y la separación de capas de la "
        "arquitectura, y señaló una brecha de coherencia: los cálculos económicos, el modelo de datos y los indicadores no conversaban entre sí. "
        "La {T:obs_ef2} registra cada observación, la corrección aplicada y la sección donde se encuentra.")
    r.table("obs_ef2", "Observaciones de la EF2 y su tratamiento", ["Criterio", "Observación del académico guía", "Corrección aplicada", "Sección"], [
        ("Factibilidad económica", "El beneficio se calculó con el ingreso bruto de los viajes recuperados ($219.600) frente a la mensualidad, sin descontar sus costos", "Beneficio con margen neto (supuesto explícito de 25 % y sensibilidad de 15 % a 30 %); punto de equilibrio del cliente en reservas recuperadas", "3.1"),
        ("Factibilidad económica", "Incorporar el modelo de precios del equipo y el costo del soporte", "Modelo vigente: licencia perpetua de uso y plan de servicio mensual por tamaño de flota, con soporte Plus opcional (CC-13)", "3.1, Anexo J"),
        ("Factibilidad económica", "Calcular el punto de equilibrio de FlotaÁgil con sus costos (AWS, Twilio, AeroAPI)", "Costos separados en fijos y variables; margen de contribución por plan; equilibrio operativo y recuperación de la inversión", "3.1, Anexo J"),
        ("Modelo de datos", "El modelo no soporta la cuadratura (P3.2) ni los indicadores por turno: HISTORIAL_ESTADO solo registra viajes y CONDUCTOR.estado se sobrescribe", "Nuevas entidades TURNO (conductor, vehículo, inicio y término) y CIERRE_CAJA (turno, monto rendido, diferencia, responsable y fecha); historia HU-31 (CC-12)", "4.1, 4.4, Anexo F"),
        ("Modelo de datos", "Actualizar el diagrama lógico y el diccionario", f"Figura {{F:er}} regenerada con {ENTIDADES} entidades; diccionario con TURNO, CIERRE_CAJA y ALERTA_VUELO", "4.4, Anexo F"),
        ("KPI", "KPI-08: numerador y denominador de poblaciones distintas", "KPI-08 mide solo reservas confirmadas; las solicitudes que expiran sin confirmar pasan a un indicador auxiliar con su propia población", "5.1"),
        ("KPI", "KPI-07: agrupar la suma de rechazos y expiraciones antes de dividir", "Fórmula con la suma entre paréntesis y denominador definido (asignaciones resueltas)", "5.1"),
        ("KPI", "KPI-05: definir qué ocurre si el monto rendido es cero", "Fórmula por tramos con los casos límite definidos; denominador en el monto registrado", "5.1"),
        ("KPI", "Metas incoherentes: 95 % de cumplimiento frente a 2 % de pérdida en la tabla económica", "Se mantiene la meta de 95,0 % y la factibilidad usa 5,0 % de pérdida residual; KPI-08 pasa a ≤ 5,0 % como complemento de KPI-01", "3.1, 5.1"),
        ("KPI", "Semáforos sin decimales, con vacíos entre intervalos", "Intervalos cerrados y contiguos con decimales en los nueve indicadores", "5.1"),
        ("SLA", "RPO de 6 h con pg_dump diario", "pg_dump cada 6 h, alternado con los snapshots cada 6 h (CC-14)", "5.2, 8.2"),
        ("SLA", "El 1 % de 30 días es 7 h 12 min, no 7 h 18 min", "Corregido: 720 h × 1 % = 7,2 h = 7 h 12 min", "5.2"),
        ("Plan de pruebas", "CP-14 prueba una asignación después de otra", "CP-14 rediseñado con dos peticiones simultáneas sobre la misma reserva y sobre el mismo conductor", "6.1, Anexo G"),
        ("Plan de pruebas", "Explicar el entorno de staging o la extrapolación a producción", "Staging idéntico a producción (misma instancia, imágenes y límites), por lo que no se extrapola", "6.1"),
        ("Cronograma", "Carta Gantt con el avance real y el hito de la EF2; los Sprints 1 y 2 aparecían como planificados", "Gantt de línea base frente a avance real: Sprints 1 a 3 terminados, Sprint 4 en curso, EF2 (semana 12) y ES2 (semana 14)", "9.1"),
        ("Cronograma", "Semana 16 sobrecargada", "Capacitación, despliegue y corrección de defectos se adelantan a la semana 15; carga horaria por semana", "9.1, 8.1"),
        ("Continuidad", "Cómo vuelven al sistema los viajes anotados en papel", "Procedimiento de carga diferida (PO-06) con canal CONTINGENCIA y conciliación por folio; historia HU-32 (CC-15)", "8.2, Anexo L"),
    ], [2.4, 5.2, 7.2, 1.8], font=7.6)

    r.H2("Correcciones y actualizaciones de esta versión")
    r.P("Además de las observaciones de la EF2, esta versión actualiza el documento con lo construido. La {T:correc} resume qué cambió y por "
        "qué; los datos corregidos reemplazan a los anteriores en todo el documento.")
    r.table("correc", "Correcciones respecto de la versión anterior", ["Tema", "Antes", "Ahora", "Respaldo"], [
        ("Estructura", "Capítulos de formulación y de desarrollo por sprint dentro del cuerpo del informe", "El cuerpo sigue la plantilla de la ES2; la formulación está en el Informe 1 corregido y el desarrollo por sprint en el Anexo P", "Anexos O y P"),
        ("Avance real", "Sprint 0 y prueba de concepto H-3 detallados; Sprints 1 y 2 sin documentar (EF2)", "Sprints 0 a 3 terminados y Sprint 4 en curso, con 258 SP construidos e integrados, evidencias, pruebas y defectos", "Capítulo VII"),
        ("Convenios y pedido del pasajero", "Convenio con link y contraseña compartida; pedido del pasajero sin cuenta", "Convenio con cuenta propia aprobada por el administrador (CC-16) y pedido solo con cuenta (CC-18); BPMN P1 y P1.1, casos de uso CU-06, CU-12 y CU-13 y reglas RN-06 a RN-09 actualizados", "4.1, 4.2, Anexos E y O"),
        ("Privacidad del pasajero", "La cuenta del pasajero no se podía eliminar y las posiciones GPS viejas no se borraban", "Eliminación de la cuenta con anonimización (HU-45, DC-50) y purga diaria de las posiciones de más de 30 días (DC-48)", "Anexos D y P"),
        ("Repositorio", "Organización de GitHub con la cuenta de un integrante restringida", "Repositorio en la organización Flotaagil-CL con su historial, issues y tablero; integración continua en verde (DC-49)", "Anexo P"),
        ("Duración de la sesión (JWT)", "Acceso de 30 min y refresco de 8 h (conductores 12 h)", "Acceso de 15 min, refresco de 12 h y tope de sesión de 12 h; refresco del panel en cookie httpOnly y de la app en el almacén cifrado de Android", "4.5, 4.7"),
        ("Largo de los estados (Anexo F)", "VARCHAR(20)", "VARCHAR(22): PENDIENTE_CONFIRMACION tiene 22 caracteres (DC-09)", "Anexos D y F"),
        ("Diccionario de datos", "Modelo del diseño", f"Incorpora las {DC_TOTAL} decisiones de cambio DC-01 a DC-{DC_MAX} de la construcción y las entidades de CC-12 y CC-18", "Anexos D y F"),
        ("Mensajes fuera de 24 h", "No se explicitaba", "Los avisos que inicia la empresa fuera de la ventana de 24 h requieren plantillas aprobadas por Meta (riesgo R-12, pendiente PR-11); CC-19 elimina esta dependencia en la versión 1.1", "3.1, 7.5"),
        ("Tareas en segundo plano", "Diseño con Celery", "Celery implementado: WhatsApp, vuelos y expiraciones con reintento exponencial; reemplaza al servicio temporal de expiración", "7.4"),
        ("GPS con la app cerrada (CC-11)", "Propuesto", "Aprobado: no se exige registrar con la app cerrada; se mitiga en el panel y con la guía del teléfono", "Anexo M"),
        ("Vuelos de salida", "Implícitos en HU-26", "Pospuestos fuera del MVP (PR-08): VUELO registra solo llegadas (DC-06)", "Anexo D"),
        ("Modelo comercial", "Suscripción mensual (Plan Básico de $189.000)", "Licencia perpetua de uso más plan de servicio mensual en tres tramos, con soporte Plus opcional (CC-13)", "3.1"),
        ("Evaluación económica", "Beneficio mensual y punto de equilibrio, sin evaluación en el tiempo", "Flujo de caja a tres años con VAN, TIR y PRI para el cliente y para FlotaÁgil, sensibilidad a 8 %, 12 % y 15 % y escenario con CC-19 (sin Twilio)", "2.1, Anexo J"),
        ("Chat del panel", "Mensaje entrante visible en menos de 3 s", "Visible en 15 s o menos: el panel revisa los mensajes por tiempo (decisión de HU-30)", "5.2, Anexo G"),
    ], [3.0, 3.9, 6.6, 2.1], font=7.8)


def requerimientos(r):
    r.H3("Requerimientos y reglas de negocio vigentes")
    r.P("Los requerimientos funcionales se expresan como historias de usuario (HU). La {T:hu} resume las HU vigentes por épica; el Anexo A "
        "contiene cada historia con sus criterios de aceptación. Su origen es el levantamiento de la sección 2.3 (entrevistas EV-01 y EV-02, grupo focal "
        "EV-03, observación EV-04 y acta EV-07), salvo HU-26 a HU-30, que nacen de los cambios CC-02 y CC-03; HU-31 y HU-32, que nacen de las "
        "observaciones de la EF2 (CC-12 y CC-15); y HU-33 a HU-49, que nacen de los cambios CC-16 a CC-18 pedidos por el cliente en la semana 14.")
    by_epic = {}
    for h in HU:
        by_epic.setdefault(h[1], []).append(h)
    rows = []
    for ep, hs in by_epic.items():
        rows.append((ep, ", ".join(h[0] for h in hs), str(sum(h[5] for h in hs)),
                     ", ".join(sorted({h[4] for h in hs}, key=["Alta", "Media", "Baja"].index))))
    rows.append(("Total de los cuatro sprints", f"{len(HU)} historias; {len(RETIRADAS)} retiradas (HU-07, 08, 09, 22, 23)", str(sum(h[5] for h in HU)), "—"))
    rows.append(("Incorporadas al Sprint 4 tras la EF2", "HU-31 (cierre de caja por turno) y HU-32 (reserva de contingencia)", str(sum(h[5] for h in NUEVAS)), "Alta, Media"))
    from data_hu_cc import HU_CC
    s4 = [x for x in HU_CC if "Sprint 4" in x[7]]
    v11 = [x for x in HU_CC if "1.1" in x[7] and "Sprint 4" not in x[7]]
    rows.append(("Incorporadas al Sprint 4 por CC-16 a CC-18", f"{s4[0][0]} a {s4[-1][0]}: sesión única, convenios con cuenta, usuarios del panel, portal con cuenta y perfil", str(sum(int(x[4]) for x in s4)), "—"))
    rows.append(("Planificadas para la versión 1.1 (CC-18)", f"{v11[0][0]} a {v11[-1][0]}: registro del convenio, pedir para el equipo, personas frecuentes y estados del sistema", str(sum(int(x[4]) for x in v11)), "—"))
    r.table("hu", "Historias de usuario vigentes por épica", ["Épica", "Historias", "SP", "Prioridades"], rows, [3.2, 9.0, 1.4, 3.0], font=8.5)

    r.P("Siguiendo a Sommerville (2016), cada requerimiento no funcional se expresa con una condición verificable. Se actualizan y se asocian a la característica de calidad de ISO/IEC 25010:2023 que protegen ({T:rnf}). "
        "En esta tabla y en la de reglas de negocio, la columna «Estado» compara cada requerimiento con la formulación entregada en la primera "
        "evaluación formativa: «Vigente» no cambió, «Modificado» cambió su condición y «Nuevo» no existía.")
    rnf = [
        ("RNF-01", "Disponibilidad mensual ≥ 99,0 % en régimen 24/7, sin contar el mantenimiento programado", "Fiabilidad · disponibilidad", "Monitoreo UptimeRobot cada 5 min; informe mensual", "Modificado"),
        ("RNF-02", "Latencia de posición GPS p95 < 5 s entre emisión y despliegue en el mapa", "Eficiencia · comportamiento temporal", "CP-12 con 50 conductores simulados", "Vigente"),
        ("RNF-03", "Respuesta de la API p95 < 2 s con 50 usuarios concurrentes", "Eficiencia · capacidad", "CP-28 (k6)", "Vigente"),
        ("RNF-04", "Todo el tráfico sobre TLS 1.2 o superior (1.3 preferente) con HSTS", "Seguridad · confidencialidad", "CP-31 (SSL Labs ≥ A)", "Modificado"),
        ("RNF-05", "Contraseñas con PBKDF2-SHA256 y salt individual", "Seguridad · confidencialidad", "Revisión de código y modelo", "Vigente"),
        ("RNF-06", "App del conductor operable con una mano; SUS ≥ 70", "Usabilidad · operabilidad", "CP-32 con 3 conductores", "Modificado"),
        ("RNF-07", "Consumo de datos < 50 MB por turno de 8 h", "Eficiencia · uso de recursos", "CP-33 en dispositivo real", "Vigente"),
        ("RNF-08", "Snapshot y pg_dump cada 6 h, alternados; retención de 7 y 30 días; RPO de 6 h", "Fiabilidad · recuperabilidad", "CP-30 (restauración)", "Modificado (CC-14)"),
        ("RNF-09", "Ubicación del conductor solo en turno y con consentimiento; retención de 30 días; acceso por rol", "Seguridad · confidencialidad", "CP-04", "Nuevo"),
        ("RNF-10", "Toda transición de estado y acción sensible queda registrada con usuario y fecha", "Seguridad · responsabilidad", "CP-24", "Nuevo"),
        ("RNF-11", "Cobertura de pruebas ≥ 70 % en módulos de negocio; CI en verde para fusionar", "Mantenibilidad · capacidad de prueba", "Informe de cobertura en CI", "Nuevo"),
        ("RNF-12", "App en Android 10 o superior; panel en Chrome y Edge (dos últimas versiones)", "Compatibilidad · coexistencia", "Pruebas en dispositivos", "Nuevo"),
        ("RNF-13", "Integraciones con reintento exponencial e idempotencia de webhooks", "Fiabilidad · tolerancia a fallos", "CP-10, CP-21", "Nuevo"),
    ]
    r.table("rnf", "Requerimientos no funcionales vigentes", ["ID", "Requerimiento", "Característica ISO/IEC 25010", "Verificación", "Estado"], rnf,
            [1.4, 6.4, 3.4, 3.6, 1.8], font=8)

    r.P("Las reglas de negocio condicionan el diseño con independencia de la interfaz ({T:rn}). RN-01 a RN-05 y RN-10 a RN-14 no cambian; "
        "RN-06 a RN-09 se ajustan a las cuentas de CC-16 y CC-18, y RN-19 y RN-20 se agregan con las historias originadas en la EF2.")
    rn = [
        ("RN-01", "Solo se asigna a conductores en estado Disponible.", "HU-04, HU-13", "Vigente"),
        ("RN-02", "Ninguna asignación ni ajuste de recogida ocurre sin confirmación del despachador.", "HU-04, HU-27", "Ampliada"),
        ("RN-03", "Un conductor tiene a lo más un viaje en ejecución.", "HU-15, HU-16", "Vigente"),
        ("RN-04", "Sin respuesta en 60 s, la reserva vuelve a SOLICITADO.", "HU-15", "Vigente"),
        ("RN-05", "Con más de un vehículo, el conductor declara cuál usará antes de quedar Disponible.", "HU-13", "Vigente"),
        ("RN-06", "El teléfono del pasajero se verifica por WhatsApp una sola vez, al activar su cuenta; el mensaje de activación vence a los 15 min y admite hasta 3 envíos por número cada 15 min.", "HU-20, HU-35, HU-41", "Modificada (CC-18)"),
        ("RN-07", "Las reservas de un convenio aprobado, hechas con la cuenta de la empresa, omiten la verificación del teléfono.", "HU-25, HU-34", "Modificada (CC-16)"),
        ("RN-08", "Desactivar un convenio corta al instante el acceso de su cuenta sin afectar el historial.", "HU-11, HU-34", "Modificada (CC-16)"),
        ("RN-09", "El pasajero cancela por WhatsApp o desde su cuenta solo sin conductor asignado; después, a través del despachador.", "HU-21, HU-44", "Modificada"),
        ("RN-10", "Ningún viaje se finaliza sin método de pago y monto.", "HU-16", "Vigente"),
        ("RN-11", "El cierre o anulación forzada exige motivo y queda en auditoría.", "HU-05", "Vigente"),
        ("RN-12", "Todo cambio de contraseña o estado de convenio genera auditoría inmutable.", "HU-12", "Vigente"),
        ("RN-13", "Un usuario solo accede a registros de su empresa.", "Transversal", "Vigente"),
        ("RN-14", "La calificación es opcional y no condiciona el cierre.", "HU-24", "Vigente"),
        ("RN-15", "Retención: viajes 24 meses; mensajes 12 meses; posiciones GPS 30 días, borradas por una tarea diaria; registros de eventos 90 días. Al eliminar una cuenta, sus datos personales se anonimizan y se conservan los registros del servicio.", "Transversal, HU-45", "Modificada"),
        ("RN-16", "Para recogidas en el aeropuerto se propone al primer conductor de la fila virtual (orden de ingreso a la geocerca).", "HU-29", "Nueva"),
        ("RN-17", "La nueva hora de recogida es ETA + margen (20 min nacional, 35 min internacional, configurable).", "HU-27", "Nueva"),
        ("RN-18", "La ubicación del conductor se registra solo en turno y tras su consentimiento informado.", "HU-13", "Nueva"),
        ("RN-19", "Todo turno terminado se cuadra una sola vez; el cierre registra monto rendido, diferencia, responsable y fecha, y una diferencia distinta de cero exige observación.", "HU-31", "Nueva (CC-12)"),
        ("RN-20", "Los viajes anotados durante una caída se ingresan con canal CONTINGENCIA y su folio dentro de las 24 h siguientes al restablecimiento; no generan avisos al pasajero y quedan en auditoría.", "HU-32", "Nueva (CC-15)"),
    ]
    r.table("rn", "Reglas de negocio vigentes", ["ID", "Regla", "HU", "Estado"], rn, [1.4, 10.6, 2.6, 2.0], font=8)

    r.P("La trazabilidad completa de cada historia hacia proceso, caso de uso, componente, entidades y caso de prueba está en el Anexo I. Los "
        "parámetros de operación de la {T:pend} se **validaron con el cliente** en la entrevista EV-08 (Anexo C) o los aprobó el Product Owner durante la construcción, y se implementan como parámetros "
        "configurables por empresa, para ajustarlos tras la marcha blanca sin modificar el código.")
    pend = [
        ("Horario de operación", "24/7; menor demanda el domingo de madrugada", "EV-08", "Base del SLA y de la ventana de mantenimiento"),
        ("Márgenes de recogida por vuelo (RN-17)", "20 min nacional / 35 min internacional", "EV-08", "Parámetro configurable"),
        ("Tolerancia fuera de la geocerca (RN-16)", "10 minutos", "EV-08", "Parámetro; se revisa tras la marcha blanca"),
        ("Tiempo de espera por no presentación", "15 minutos en EN_ZONA", "EV-08", "Parámetro configurable"),
        ("Polígono de la geocerca del aeropuerto", "Zona de estacionamiento autorizada del operador", "EV-08", "GeoJSON versionado en el repositorio"),
        ("Vigencia del mensaje de activación de la cuenta (RN-06)", "15 minutos", "EV-08", "Parámetro configurable"),
        ("Anticipación mínima de una solicitud del portal", "30 minutos", "DC-10 (PO)", "Parámetro configurable"),
        ("Precisión mínima para marcar la llegada por geocerca", "50 metros", "DC-16 (PO)", "Parámetro configurable"),
        ("Vigencia de la encuesta de calificación", "24 horas desde el fin del viaje", "DC-19 (PO)", "Parámetro configurable"),
        ("Tiempo para aceptar o rechazar un viaje (RN-04)", "60 segundos", "EV-07", "Regla del sistema"),
    ]
    r.table("pend", "Parámetros de operación vigentes", ["Tema", "Valor acordado", "Origen", "Tratamiento"], pend,
            [4.2, 5.6, 2.8, 4.0], font=8)


def tecnologias(r):
    r.H1("Detalle de las Tecnologías a implementar")
    r.H2("Análisis cualitativo/cuantitativo de las tecnologías que serán implementadas")
    r.P("Se identificaron siete decisiones que condicionan el proyecto: proveedor cloud, framework de backend, base de datos, frontend web, "
        "aplicación del conductor, canal de mensajería con el pasajero y fuente de datos de vuelos, además de la metodología. Cada una se evaluó con "
        "una matriz ponderada: los criterios derivan de los requerimientos y restricciones; los pesos suman 100 %; cada alternativa se puntúa de 1 "
        "(no cumple) a 5 (cumple plenamente) y el puntaje final es la suma de nota × peso. Las notas se fundamentan en costos publicados por los "
        "proveedores (consulta de octubre de 2026), en la documentación técnica citada y en la experiencia declarada del equipo. Supuestos "
        "comunes: tipo de cambio de $950 por dólar, 1.512 reservas mensuales y 50 conductores en turno simultáneo como peor caso.")

    r.H3("Proveedor cloud")
    rows = [
        ("Costo mensual de la configuración mínima (30 %)", "5 · t4g.small ≈ USD 12,3 + EBS 30 GB USD 2,4", "4 · e2-small ≈ USD 12–15", "3 · B1ms ≈ USD 15", "4 · VPS 2 GB ≈ USD 12"),
        ("Servicios de respaldo, DNS y monitoreo integrados (20 %)", "5 · snapshots DLM, S3, Route 53, CloudWatch", "5 · equivalentes", "5 · equivalentes", "2 · limitados"),
        ("Experiencia del equipo y material académico (20 %)", "5 · mayor familiaridad del equipo", "3", "2", "3"),
        ("Latencia hacia Chile (10 %)", "3 · ~130 ms desde Santiago", "5 · región Santiago", "3", "3"),
        ("Documentación y comunidad (10 %)", "5", "4", "4", "3"),
        ("Riesgo de dependencia del proveedor (10 %)", "3 · mitigado con Docker", "3", "3", "4"),
        ("**Puntaje ponderado**", "**4,60**", "**4,00**", "**3,30**", "**3,20**"),
    ]
    r.table("m_cloud", "Matriz ponderada: proveedor cloud", ["Criterio (peso)", "AWS", "Google Cloud", "Azure", "VPS (DigitalOcean)"], rows,
            [4.4, 3.6, 2.9, 2.8, 2.9], font=8, source="Elaboración propia con precios de Amazon Web Services (2026a), Google Cloud (2026), Microsoft (2026) y DigitalOcean (2026).")
    r.P("Se selecciona **AWS**. La latencia de ~130 ms desde Santiago es irrelevante frente a la meta de 5 s de RNF-02, y su costo y la experiencia "
        "del equipo pesan más que la región local de Google Cloud. Se descarta Azure por costo y menor experiencia, y el VPS por carecer de snapshots "
        "programados y monitoreo integrado. **Limitación:** los datos se alojan fuera de Chile; la Ley 21.719 permite la transferencia internacional "
        "con garantías contractuales, que se cubren con el acuerdo de tratamiento de datos de AWS y se informan en el aviso de privacidad.")

    r.H3("Backend, base de datos y frontend")
    rows = [
        ("Backend (pesos: dominio del equipo 30, soporte geoespacial 20, tiempo real 20, seguridad integrada 15, productividad 15)",
         "**Django 5 + DRF + Channels: 4,65**", "NestJS: 3,55 · FastAPI: 3,50 · Spring Boot: 3,20",
         "GeoDjango, Channels y el panel de administración reducen trabajo (Django Software Foundation, 2025); FastAPI exige armar autenticación, ORM geoespacial y admin por separado."),
        ("Base de datos (consultas de proximidad 35, integridad transaccional 25, costo 20, experiencia 20)",
         "**PostgreSQL 16 + PostGIS 3.4: 4,80**", "MySQL 8 espacial: 4,10 · MongoDB: 3,10",
         "PostGIS ofrece índices GiST, tipo geography y ST_DWithin/ST_Distance (Obe y Hsu, 2021); MongoDB no asegura la integridad entre viaje, pago y asignación."),
        ("Frontend web (reutilización con la app 35, experiencia 25, ecosistema de mapas 20, rendimiento 20)",
         "**React 19 + Vite + TypeScript: 4,80**", "Angular: 3,15 · Plantillas Django + JS: 2,75",
         "Un solo lenguaje y componentes compartidos entre panel, portal y app Capacitor (CC-08)."),
    ]
    r.table("m_stack", "Resumen de matrices: backend, base de datos y frontend (detalle por criterio en el Anexo J)", ["Decisión y criterios (peso %)", "Seleccionada", "Alternativas (puntaje)", "Fundamento"],
            rows, [4.4, 3.2, 3.6, 5.4], font=8)

    r.H3("Aplicación del conductor")
    rows = [
        ("GPS en segundo plano estable (35 %)", "4 · plugin background-geolocation", "5", "4", "4", "1 · se detiene sin primer plano"),
        ("Reutilización del código web (25 %)", "5", "1", "3", "1", "5"),
        ("Tiempo de desarrollo (20 %)", "5", "2", "3", "3", "5"),
        ("Experiencia del equipo (20 %)", "4", "2", "3", "1", "4"),
        ("**Puntaje ponderado**", "**4,45**", "**2,80**", "**3,35**", "**2,45**", "**3,40**"),
    ]
    r.table("m_app", "Matriz ponderada: aplicación del conductor", ["Criterio (peso)", "Capacitor", "Kotlin nativo", "React Native", "Flutter", "PWA"],
            rows, [4.2, 3.0, 2.1, 2.3, 1.9, 3.1], font=8)
    r.P("Se mantiene **Capacitor**, que empaqueta la misma aplicación web como app nativa con acceso a las funciones del teléfono (Griffith, 2017). Su riesgo es el comportamiento del GPS en segundo plano en distintos fabricantes Android (R-01), mitigado con la "
        "prueba de concepto del hito H-3 y, si falla, transmisión en primer plano con aviso al conductor. La PWA se descarta porque deja de enviar "
        "posiciones al minimizarse, lo que invalida la sugerencia por distancia y la fila virtual.")

    r.H3("Canal de mensajería con el pasajero")
    r.P("Es la decisión con mayor efecto económico. La {T:m_msg} compara el costo mensual con el volumen de la empresa, asumiendo tres mensajes por "
        "reserva para SMS y, para WhatsApp, que la mitad de las reservas parte con un mensaje del pasajero, según informó el cliente (EV-08) (ventana de servicio abierta, sin cobro de "
        "Meta) y que cada reserva genera siete mensajes y cuatro de chat con cobro de Twilio de USD 0,005 cada uno. El detalle está en el Anexo J.")
    rows = [
        ("Costo mensual estimado (30 %)", "1 · ≈ $343.000 (4.536 SMS × USD 0,0797)", "3 · ≈ $104.000 (Meta USD 0,02 por plantilla + Twilio USD 0,005 por mensaje)", "5 · ≈ $20.000 (solo tarifas de Meta)", "5 · $0 (manual)"),
        ("Automatización de avisos y conversación (20 %)", "2 · avisos solo salientes", "5 · avisos y chat en el mismo hilo", "5 · igual", "1 · todo manual"),
        ("Trazabilidad en el sistema (15 %)", "3 · estado de entrega", "5 · webhook con firma", "5 · webhook", "1 · ninguna"),
        ("Esfuerzo y riesgo de plazo (25 %)", "5 · integración simple", "5 · SDK y sandbox sin verificación previa", "2 · app de Meta, verificación y tokens propios", "5 · nulo"),
        ("Hábito del usuario (10 %)", "3", "5", "5", "5"),
        ("**Puntaje ponderado**", "**2,70**", "**4,40**", "**4,25**", "**3,60**"),
    ]
    r.table("m_msg", "Matriz ponderada: canal de mensajería", ["Criterio (peso)", "SMS (Twilio)", "WhatsApp API vía Twilio", "WhatsApp Cloud API directa", "Enlaces wa.me"],
            rows, [3.6, 3.0, 3.8, 3.4, 2.8], font=8, source="Elaboración propia con tarifas de Twilio (2026a, 2026b) y Meta Platforms (2025).")
    r.P("Se adopta **WhatsApp Business API vía Twilio** (CC-01): reduce el costo a menos de un tercio del SMS y entrega un canal conversacional que "
        "el pasajero ya usa. La Cloud API directa de Meta es más barata, pero exige completar la verificación de negocio antes de poder probar; por eso "
        "la mensajería queda detrás de un adaptador y la migración a la Cloud API se deja como palanca de costo para la operación (ahorro ≈ $84.000 "
        "mensuales). **Limitaciones:** las plantillas requieren aprobación de Meta y la cuenta debe pasar la verificación de negocio, "
        "lo que puede tardar días. Además, WhatsApp solo permite texto libre dentro de la **ventana de servicio de 24 horas** desde el último "
        "mensaje del pasajero: todo aviso que la empresa inicie fuera de ella (por ejemplo, el de una reserva telefónica de un pasajero que nunca "
        "escribió) debe usar una **plantilla aprobada por Meta**, o no se entrega. Por eso la verificación, los avisos y la encuesta tienen "
        "plantillas propias. Mientras se tramitan se usa el sandbox de Twilio, que no admite plantillas propias y envía la verificación como "
        "texto (riesgo R-12, pendiente PR-11).")

    r.H3("Fuente de datos de vuelos")
    r.P("Se compararon FlightAware AeroAPI (FlightAware, 2026), AeroDataBox (AeroDataBox, 2026) y la consulta manual en el sitio del aeropuerto. Ambas API entregan estado y hora estimada "
        "por número de vuelo; AeroAPI tiene un crédito mensual gratuito útil para el desarrollo y AeroDataBox tarifas de entrada bajas para producción. "
        "Se decide **aislar el proveedor detrás de un adaptador** (patrón puertos y adaptadores) y operar con AeroAPI durante el proyecto y con el de "
        "menor costo en producción. El polling se acota (consultas desde 3 h antes, cada 30 min y cada 10 min en la última hora, compartidas entre "
        "reservas del mismo vuelo) a unas 6.000 consultas mensuales, con un presupuesto conservador de USD 30.")

    r.H3("Diferenciación frente a la competencia")
    r.P("El estado del arte (sección 2.4) mostró que las soluciones nacionales exigen hardware propietario y que las internacionales no modelan "
        "convenios ni cobros en efectivo. Esta entrega suma dos diferenciadores que ninguna de las siete soluciones analizadas ofrece para una PYME "
        "de taxi turismo: el **seguimiento del vuelo con ajuste asistido de la recogida y la fila virtual por orden de llegada en el aeropuerto**, y "
        "el **pasajero atendido de punta a punta por WhatsApp** (verificación, avisos, cancelación, calificación y chat) sin instalar nada.")

    r.H3("Metodología de desarrollo")
    rows = [
        ("Estabilidad de requerimientos (25 %)", "5 · ya hubo 10 cambios post-acta", "4", "4", "1"),
        ("Participación del cliente (20 %)", "5 · revisión cada 2 semanas", "3", "4", "2"),
        ("Equipo pequeño (20 %)", "4 · roles combinados", "5", "4", "3"),
        ("Plazos con hitos académicos fijos (20 %)", "5 · sprints alineados a EF2 y ES2", "3", "4", "4"),
        ("Gestión de riesgo técnico (15 %)", "4 · PoC y retrospectivas", "3", "5", "2"),
        ("**Puntaje ponderado**", "**4,65**", "**3,65**", "**4,15**", "**2,35**"),
    ]
    r.table("m_met", "Matriz ponderada: metodología", ["Criterio (peso)", "Scrum", "Kanban", "XP", "Cascada"], rows, [4.6, 4.2, 2.6, 2.6, 2.6], font=8)
    r.P("Se mantiene **Scrum** (Schwaber y Sutherland, 2020), cuya adaptación ante requerimientos cambiantes es su principal ventaja (Pressman y Maxim, 2020), con sprints de dos semanas y un tablero Kanban en GitHub Projects para visualizar el flujo, y se adoptan dos prácticas de "
        "XP: integración continua y revisión de código por pull request. Por indicación del académico guía, Scrum requiere al menos tres personas; "
        "el rol de **Product Owner** lo asume **Juan Pérez**, que representa al cliente y aprueba los incrementos. Así, quien desarrolla no es quien "
        "aprueba. La {T:roles} muestra la aplicación concreta de Scrum en el proyecto.")
    roles = [
        ("Product Owner", "Juan Pérez (rol asumido para efectos de la metodología)", "Prioriza el backlog, aprueba incrementos y cambios de alcance"),
        ("Scrum Master y líder de proyecto (Unidad 2)", "Carlos Ortiz", "Facilita eventos, remueve impedimentos, reporta avance al docente"),
        ("Developers", "Renato González (frontend y móvil) · Carlos Ortiz (backend y cloud)", "Estiman, construyen y prueban; revisión cruzada de cada PR"),
        ("Stakeholder", "Administrador de la flota (cliente)", "Participa en la Sprint Review y firma la UAT"),
        ("Eventos", "Planning 90 min · Daily asíncrona 15 min · Review 60 min · Retro 45 min · Refinement semanal", "Artefactos: Product Backlog (Anexo A), Sprint Backlog e incremento en GitHub Projects; DoR y DoD de la sección 2.6.1"),
    ]
    r.table("roles", "Aplicación de Scrum en el proyecto", ["Elemento", "Responsable / cadencia", "Responsabilidad / artefacto"], roles, [4.0, 5.6, 7.0], font=8)

    r.H3("Factibilidad técnica")
    r.P("**Capacidades y brechas.** Renato asume el frontend y la app móvil (JavaScript y React) y Carlos el backend y la nube (Python y "
        "Django), según la distribución definida en la formulación (sección 2.6). Las brechas son Django Channels, PostGIS, el "
        "plugin de GPS en segundo plano, la API de WhatsApp y la operación en AWS. Las cuatro primeras se cerraron durante la construcción: la prueba "
        "de concepto de GPS (H-3, Anexo M), el mapa en vivo y la fila virtual sobre Channels y PostGIS (HU-02, HU-29) y la mensajería probada con "
        "un doble de Twilio. Queda la operación en AWS, que se aborda en la semana 15 con el despliegue de staging y producción.")
    r.P("**Compatibilidad y recursos.** El escenario es greenfield: no hay sistemas que integrar y la única migración es la carga inicial de "
        "conductores, vehículos y convenios desde planillas. El cliente dispone de dos PC con Windows 10 y navegador moderno; los conductores usan "
        "teléfonos Android propios, por lo que RNF-12 exige Android 10 o superior. La organización de GitHub ya está operativa (Anexo N) y el entorno de desarrollo móvil (Node, JDK 21, Android Studio y SDK) quedó instalado y probado con la PoC H-3; las cuentas de "
        "AWS, Twilio (sandbox), Google Maps y AeroAPI son de alta inmediata, gratuita o con crédito inicial. La única gestión con plazo externo es "
        "la verificación de negocio en Meta para el número de WhatsApp productivo (R-12).")
    r.P("**Dependencias y restricciones.** Twilio/Meta para mensajería, la API de vuelos, Google Maps y AWS; una sola instancia (punto único de "
        "falla aceptado, ver 8.1) y memoria de 2 GiB que obliga a dimensionar los procesos. **Conclusión:** el proyecto es técnicamente factible; las "
        "tecnologías son maduras, documentadas y conocidas al menos por un integrante, y los dos riesgos técnicos relevantes (GPS en segundo plano y "
        "aprobación de Meta) tienen contingencia definida.")

    r.H3("Factibilidad económica")
    r.P("Esta sección se rehízo tras la retroalimentación de la EF2. Cambia tres cosas: el beneficio del cliente se calcula con el **margen neto** "
        "de los viajes recuperados y no con el ingreso bruto; se incorpora el **modelo comercial vigente** (licencia perpetua de uso más plan de "
        "servicio mensual, CC-13); y se calcula el **punto de equilibrio** de FlotaÁgil con sus propios costos (AWS, Twilio y API de vuelos). "
        "Moneda: pesos chilenos sin IVA; período: 16 semanas de desarrollo y un mes tipo de operación; respaldo de cada cifra en el Anexo J.")
    r.P("**Costos.** La {T:costos} separa la inversión del proyecto, valorizada en la formulación (sección 2.6), de los costos recurrentes de "
        "operación, que ahora se clasifican en **fijos de plataforma** (no dependen del número de reservas) y **variables** (crecen con cada "
        "reserva). Esa distinción es la base del punto de equilibrio.")
    costos = [
        ("Inicial", "Personal (2 ingenieros × 4 meses, valorizado)", "12.000.000", "Sin cambio respecto de la formulación; es trabajo propio, no desembolso"),
        ("Inicial", "Equipamiento (arriendo y depreciación)", "600.000", "Sin cambio"),
        ("Inicial", "Infraestructura cloud del proyecto", "100.000", "Antes $400.000; t4g.small y staging por horas"),
        ("Inicial", "Licencias y APIs (Google Play USD 25, pruebas Twilio y vuelos)", "60.000", "Antes $150.000"),
        ("Inicial", "Dominio .cl", "10.000", "Certificado TLS gratuito (Let's Encrypt)"),
        ("Inicial", "Imprevistos (10 %)", "1.277.000", ""),
        ("Inicial", "**Total inversión del proyecto**", "**14.047.000**", "Desembolso efectivo: $770.000 más imprevistos"),
        ("Fijo mensual", "AWS (EC2, EBS, snapshots, IPv4, S3, Route 53, CloudWatch)", "19.800", "≈ USD 20,9"),
        ("Fijo mensual", "Monitoreo (UptimeRobot Solo; Sentry Developer gratuito)", "10.500", "≈ EUR 10"),
        ("Fijo mensual", "Dominio prorrateado", "850", ""),
        ("Fijo mensual", "**Total fijo de plataforma**", "**31.150**", "No depende del volumen"),
        ("Variable mensual", "WhatsApp Business API vía Twilio", "104.000", "≈ USD 109,6 para 1.512 reservas: ≈ $69 por reserva"),
        ("Variable mensual", "API de vuelos", "28.500", "≈ USD 30 para 1.512 reservas: ≈ $19 por reserva"),
        ("Variable mensual", "Google Maps Platform", "0", "Dentro de la cuota gratuita mensual"),
        ("Variable mensual", "**Total variable (cliente actual)**", "**132.500**", "**≈ $88 por reserva** ($87,6)"),
        ("Recurrente", "**Total operación con el cliente actual**", "**163.650 / mes**", "31.150 fijos + 132.500 variables"),
        ("Por cliente adicional", "Almacenamiento, respaldos y prorrateo del escalamiento a t4g.medium", "≈ 8.000 / mes", "Desde el segundo cliente"),
    ]
    r.table("costos", "Costos iniciales y recurrentes", ["Tipo", "Ítem", "Monto (CLP)", "Observación"], costos, [2.6, 6.6, 2.6, 4.8], font=8,
            source="Elaboración propia con tarifas de Amazon Web Services (2026a), Twilio (2026a), Meta Platforms (2025), UptimeRobot (2026) y Google (2026), consultadas en octubre de 2026.")
    r.P("**Diferencia con el presupuesto del Informe 1.** La formulación valorizó la inversión en $14.498.000 antes de definir el proveedor "
        "cloud y las tarifas de los servicios. Con AWS ya elegido (CC-07) y las cuotas de prueba de cada servicio conocidas, bajan la "
        "infraestructura del proyecto ($400.000 → $100.000), las licencias y API ($150.000 → $60.000) y el dominio ($30.000 → $10.000, porque "
        "el certificado TLS es gratuito), y con ellos los imprevistos ($1.318.000 → $1.277.000). La diferencia de $451.000 explica la cifra de "
        "$14.047.000 que usa esta factibilidad; el personal y el equipamiento no cambian.")
    r.P("**Planes gratuitos y sus límites.** Sentry Developer admite un usuario y 5.000 errores mensuales (alertas a un correo compartido); GitHub "
        "Free incluye 2.000 minutos de Actions al mes para repositorios privados; Google Maps tiene una cuota mensual gratuita por producto; AeroAPI "
        "un crédito mensual de USD 5 suficiente para pruebas; UptimeRobot Free monitorea cada 5 minutos y se usa durante el proyecto, pasando al plan "
        "Solo en operación comercial.")

    r.P("**Modelo comercial (CC-13).** FlotaÁgil no se vende como código ni como desarrollo a medida. El cliente adquiere una **licencia perpetua "
        "de uso, no exclusiva e intransferible**: puede usar el sistema de forma indefinida, pero el código y la propiedad intelectual siguen "
        "siendo del equipo (Ley N° 17.336), lo que permite licenciar el mismo producto a otras flotas. La operación se cobra aparte, en un **plan "
        "de servicio mensual** que incluye el alojamiento, la mantención, los respaldos, el soporte según el SLA y el consumo de los servicios "
        "externos hasta el tope del plan ({T:planes}). Hoy ese consumo es WhatsApp vía Twilio y la API de vuelos; con CC-19 los planes ya no "
        "incluyen WhatsApp, porque los avisos pasan a la notificación del navegador y al correo, y mantienen su precio. El plan lo determina el "
        "mayor entre el número de vehículos y el de reservas mensuales.")
    r.table("planes", "Licencia y planes de servicio por tamaño de flota", ["Concepto", "Inicial", "Estándar", "Avanzado"], [
        ("Tamaño de la flota", "Hasta 10 vehículos", "11 a 30 vehículos", "31 a 50 vehículos"),
        ("Reservas incluidas al mes", "Hasta 350", "Hasta 1.000", "Hasta 1.800"),
        ("**Licencia perpetua de uso (pago único)**", "**$200.000**", "**$350.000**", "**$500.000**"),
        ("**Plan de servicio (mensual)**", "**$59.000**", "**$129.000**", "**$199.000**"),
        ("Reserva sobre el tope", "$120 por reserva", "$120 por reserva", "$120 por reserva"),
        ("Soporte Plus (opcional)", "$49.000 al mes", "$49.000 al mes", "$49.000 al mes"),
        ("Corresponde a", "Flotas pequeñas", "Flota mediana", "Cliente actual (40 vehículos, 1.512 reservas)"),
    ], [5.2, 3.6, 3.6, 4.2], font=8, source="Elaboración propia. Valores sin IVA.")
    r.P("La licencia incluye la puesta en marcha (configuración de la empresa, carga inicial de conductores, vehículos y convenios, y "
        "capacitación), que antes se cobraba como «implementación». Todas las funciones están en los tres planes; lo que cambia es el volumen "
        "incluido. Si el cliente deja de pagar el plan, la licencia sigue vigente pero el servicio alojado se suspende; sus datos se le entregan "
        "exportados dentro de 30 días (Ley N° 21.719) y puede reactivar sin pagar otra vez la licencia. Una instalación en infraestructura del "
        "cliente se cotiza aparte.")

    r.P("**Beneficio para el cliente, con margen neto.** Cada reserva recuperada genera un ingreso, pero también costos directos: combustible, "
        "peajes y estacionamiento del aeropuerto, la parte del conductor y el desgaste del vehículo. Por eso el beneficio se calcula sobre el "
        "margen que le queda a la empresa. El margen real por viaje no se obtuvo en el levantamiento, así que se trabaja con un **supuesto "
        "explícito de 25 % ($3.000 por viaje de $12.000)**, que se sensibiliza entre 15 % y 30 % y se validará con el cliente antes de la UAT "
        "(riesgo R-17). La {T:benef} desarrolla el cálculo para el cliente actual, con las metas de los KPI como hipótesis: la pérdida de "
        "reservas baja de 12,1 % a 5,0 % (KPI-01 = 95,0 %).")
    r.table("benef", "Beneficio mensual del cliente actual (escenario meta)", ["Concepto", "Cálculo", "Monto mensual"], [
        ("Reservas perdidas hoy", "1.512 × 12,1 %", "183 reservas"),
        ("Reservas perdidas con la meta de KPI-01 (95,0 %)", "1.512 × 5,0 %", "76 reservas"),
        ("Reservas recuperadas", "183 − 76", "107 reservas"),
        ("Ingreso bruto recuperado", "107 × $12.000", "$1.284.000"),
        ("Costos directos de esos viajes (75 %)", "Combustible, peajes, parte del conductor y desgaste", "− $963.000"),
        ("**A. Margen neto de los viajes recuperados (25 %)**", "107 × $3.000", "**$321.000**"),
        ("**B. Caja recuperada**", "30 % del descuadre de $1.035.000 (sin costos asociados)", "**$310.500**"),
        ("Beneficio mensual total", "A + B", "$631.500"),
        ("Plan de servicio Avanzado", "", "− $199.000"),
        ("**Beneficio neto mensual**", "", "**$432.500**"),
        ("Recuperación de la licencia ($500.000)", "500.000 ÷ 432.500", "≈ 1,2 meses"),
        ("Resultado del primer año", "12 × 432.500 − 500.000", "$4.690.000"),
    ], [6.2, 6.6, 3.8], font=8)
    r.P("El descuadre de caja se trata aparte porque no es un ingreso por viajes: es dinero ya cobrado que hoy no se puede trazar, así que "
        "recuperarlo no tiene costos asociados. La meta de KPI-05 (exactitud ≥ 98,0 %) supone reducir el descuadre de cerca de 6,5 % de la "
        "recaudación diaria a 2 % o menos, es decir, casi 70 %. No todo ese descuadre es dinero perdido (una parte son errores de anotación), "
        "por lo que la factibilidad cuenta como beneficio solo el **30 %**, menos de la mitad de la reducción que exige la meta.")
    r.P("**Sensibilidad y punto de equilibrio del cliente.** La {T:sens} muestra el beneficio neto mensual según el margen real. Considerando "
        "solo los viajes recuperados, el plan se paga cuando el cliente recupera **67 reservas al mes** (199.000 ÷ 3.000), el 36,6 % de las que hoy "
        "pierde; equivale a bajar la pérdida de 12,1 % a 7,7 % (KPI-01 = 92,3 %), bastante antes de la meta. Si además se prorratea la licencia en "
        "12 meses, el equilibrio sube a 81 reservas (KPI-01 = 93,3 %). El margen mínimo que hace rentable el plan solo con viajes, cumpliendo la "
        "meta, es 15,5 %.")
    r.table("sens", "Sensibilidad del beneficio neto mensual del cliente al margen por viaje", ["Margen neto por viaje", "Margen de 107 reservas", "Solo viajes, menos el plan", "Con caja recuperada (30 %), menos el plan"], [
        ("15 % ($1.800)", "$192.600", "− $6.400", "$304.100"),
        ("20 % ($2.400)", "$256.800", "$57.800", "$368.300"),
        ("**25 % ($3.000), supuesto base**", "**$321.000**", "**$122.000**", "**$432.500**"),
        ("30 % ($3.600)", "$385.200", "$186.200", "$496.700"),
    ], [4.6, 3.8, 3.8, 4.4], font=8)
    r.P("**Flotas más pequeñas.** El modelo por tramos mantiene la conveniencia para un cliente de menor volumen. Con los mismos supuestos "
        "(margen de 25 %, pérdida de 12,1 % a 5,0 % y descuadre proporcional al volumen), una flota de 10 vehículos y 350 reservas recupera 25 "
        "reservas ($75.000 de margen) y $72.000 de caja: paga $59.000 y le quedan $88.000 al mes, con lo que la licencia de $200.000 se recupera "
        "en 2,3 meses. Una flota de 25 vehículos y 900 reservas obtiene $377.000 de beneficio, paga $129.000 y le quedan $248.000 (licencia "
        "recuperada en 1,4 meses). En el caso pesimista (margen de 20 % y sin mejora de caja) la flota pequeña queda en equilibrio ($60.000 "
        "frente a $59.000) y las otras dos siguen en positivo.")
    r.P("**Beneficios no monetizables:** menos llamadas de consulta, trazabilidad ante disputas con convenios, puntualidad en el aeropuerto y "
        "mejor experiencia del conductor.")

    r.P("**Punto de equilibrio de FlotaÁgil.** Cada reserva cuesta ≈ $88 en WhatsApp y vuelos, por lo que el margen de contribución de un "
        "cliente es el precio de su plan menos su consumo ({T:equil}). Los costos fijos son $31.150 mensuales por la plataforma, más unos "
        "$8.000 por cada cliente adicional.")
    r.table("equil", "Margen de contribución por plan y punto de equilibrio de FlotaÁgil", ["Plan y volumen de ejemplo", "Ingreso mensual", "Consumo ($88 por reserva)", "Margen de contribución", "Cubre los $31.150 fijos"], [
        ("Inicial · 350 reservas", "$59.000", "$30.800", "$28.200", "No por sí solo: se requieren dos clientes"),
        ("Estándar · 900 reservas", "$129.000", "$79.200", "$49.800", "Sí; resultado de $18.650"),
        ("Avanzado · 1.512 reservas (cliente actual)", "$199.000", "$132.500", "$66.500", "Sí; resultado de **$35.350**"),
        ("Avanzado en su tope · 1.800 reservas", "$199.000", "$158.400", "$40.600", "Sí; resultado de $9.450"),
    ], [4.8, 2.4, 3.0, 2.8, 3.6], font=8, source="Elaboración propia. El consumo del cliente actual es el de la Tabla {T:costos}; los demás usan $88 por reserva.")
    r.bullets([
        "**Equilibrio operativo:** con el cliente actual en el plan Avanzado, FlotaÁgil cubre todos sus costos de operación ($163.650) y obtiene "
        "$35.350 mensuales. El equilibrio se alcanza con **un cliente Estándar o Avanzado, o con dos clientes Inicial** (2 × 28.200 − 8.000 = "
        "$48.400). Ningún plan queda con margen negativo dentro de su tope, y cada reserva sobre el tope deja $32 ($120 − $88).",
        "**Recuperación del desembolso:** los $770.000 de desembolso presupuestado (equipamiento, nube, licencias y dominio) se recuperan con la licencia del primer cliente "
        "más ocho meses de operación (500.000 + 8 × 35.350 = $782.800).",
        "**Recuperación de la inversión valorizada:** recuperar los $14.047.000, que en su mayoría son horas propias del equipo, exige crecer. "
        "Con una cartera de 11 clientes (3 Inicial, 4 Estándar y 4 Avanzado) se obtienen $4.000.000 en licencias y $438.650 mensuales "
        "(549.800 de contribución menos 111.150 de costos fijos). Como la cartera se forma de manera gradual, la recuperación se evalúa con "
        "flujo de caja descontado más abajo ({T:van_res}).",
        "**Soporte Plus:** cada contratación agrega $49.000 mensuales sin costo variable, porque usa la misma guardia del equipo.",
        "**Palanca de costo:** el 78 % del costo variable es WhatsApp enviado a través de Twilio. Es el costo que retira CC-19.",
    ])
    r.P("**Escenario con CC-19 (retiro total de Twilio).** CC-19, aprobada para la versión 1.1, reemplaza los mensajes de WhatsApp por el chat "
        "interno, pasa la verificación de la cuenta al correo y envía los avisos por notificación del navegador (Web Push, sin costo) y por "
        "Amazon SES (USD 0,10 por cada 1.000 correos, ≈ $1.000 al mes con unos diez correos por reserva). El costo de Twilio desaparece por "
        "completo y el costo variable queda casi solo en la API de vuelos ({T:cc19_ahorro}). Supera además a la migración a la Cloud API "
        "directa de Meta (≈ $32 por reserva, Anexo J), que deja de ser necesaria.")
    r.table("cc19_ahorro", "Ahorro de CC-19 con el cliente actual (1.512 reservas al mes)", ["Concepto", "Operación actual", "Con CC-19", "Diferencia"], [
        ("WhatsApp vía Twilio", "$104.000", "$0", "−$104.000"),
        ("API de vuelos", "$28.500", "$28.500", "$0"),
        ("Correo (Amazon SES) y Web Push", "$0", "≈ $1.000", "+$1.000"),
        ("**Costo variable mensual**", "**$132.500**", "**$29.500**", "**−$103.000**"),
        ("Costo variable por reserva", "≈ $88", "≈ $20", "−$68"),
        ("Costos fijos de plataforma", "$31.150", "$31.150", "$0"),
        ("**Operación mensual del cliente actual**", "**$163.650**", "**≈ $60.650**", "**−63 %**"),
        ("Ahorro anual", "—", "—", "**≈ $1.236.000**"),
        ("Resultado mensual de FlotaÁgil con el plan Avanzado ($199.000)", "$35.350", "$138.350", "+$103.000"),
        ("Margen del plan Avanzado sobre su precio", "≈ 18 %", "≈ 70 %", "+52 puntos"),
        ("Margen de cada reserva sobre el tope ($120)", "$32", "$100", "+$68"),
    ], [7.2, 3.0, 3.0, 3.4], font=8, source="Elaboración propia con las tarifas de la {T:costos} y de Amazon Web Services (2026a).")
    r.P("Para el cliente nada cambia en precio: el plan cuesta lo mismo y deja de depender de que el pasajero use WhatsApp. El ahorro queda en "
        "FlotaÁgil, que con el mismo cliente pasa de cubrir apenas sus costos a obtener cerca de 70 % de margen sobre el plan.")
    van_eval(r)
    r.P("**Conclusión.** Para el cliente la solución es económicamente factible: en el escenario meta recupera la licencia en poco más de un mes, "
        "con un VAN a tres años cercano a $12 millones, y aun en el escenario prudente el VAN es positivo y la licencia se recupera antes de un "
        "año. Para FlotaÁgil, el proyecto es **viable condicionado a CC-19 y a alcanzar 11 clientes**: la operación se sostiene desde el primer "
        "cliente, pero con la mensajería vía Twilio la inversión valorizada no se recupera en tres años; con CC-19, aun pagando su desarrollo, "
        "el VAN es positivo hasta una tasa de 15 % y la inversión se recupera en unos dos años y medio, siempre que la cartera llegue a la meta. "
        "Por eso CC-19 es la primera prioridad de la versión 1.1, y la cartera y el consumo por reserva se revisan periódicamente (R-04). La coherencia de estas hipótesis con las metas de los KPI se muestra en la sección 5.1.")

    r.H3("Factibilidad implementativa")
    r.P("**Condiciones organizacionales.** El administrador patrocina el proyecto y validó el backlog; el despachador y tres conductores ya "
        "participaron del levantamiento. **Disponibilidad:** el cliente asiste a la Sprint Review (60 min), a la capacitación de la semana 15 y a la UAT de la semana 16. "
        "**Capacitación:** administrador 2 h, despachadores 3 h, conductores 1 h en grupos, con guías rápidas (E-12). **Adaptación de procesos:** "
        "el despacho deja de hacerse por llamadas; durante la marcha blanca se mantiene la planilla de contingencia (8.2). **Carga inicial:** "
        "conductores, vehículos y convenios vigentes por CSV (HU-10). **Restricciones:** calendario académico fijo, aprobación de Meta, permisos de "
        "ubicación en los teléfonos personales y política de Google Play sobre ubicación en segundo plano (la APK se distribuye directamente "
        "mientras se tramita).")
    r.P("**Riesgos de adopción:** resistencia de conductores por percepción de control (R-05), mitigada con consentimiento informado, ubicación "
        "solo en turno y la fila virtual como beneficio visible para ellos; y doble digitación durante la transición, mitigada con un corte "
        "definido (desde el día 1 de producción el registro oficial es FlotaÁgil). **Conclusión:** la implementación es factible si la verificación "
        "de Meta y la aprobación de las plantillas (pendiente PR-11) se completan antes de la UAT y la capacitación ocurre antes de la marcha blanca; "
        "por eso la capacitación se adelantó a la semana 15 (sección 9.1).")

    r.H2("Herramientas, aplicaciones, lenguajes y componentes que serán implementados")
    r.P("La {T:herr} inventaría los recursos con su versión prevista, función, relación con componentes o requerimientos, licencia, costo y ambiente "
        "(D: desarrollo, P: pruebas, O: operación). El criterio de versión es usar la última versión estable con soporte de largo plazo y con imagen "
        "oficial para ARM64, ya que la instancia es Graviton. Las versiones del frontend móvil son las fijadas en la PoC H-3, con al menos dos "
        "semanas desde su publicación.")
    herr = [
        ("Python", "3.12", "Lenguaje del backend", "Backend", "PSF", "$0", "D P O"),
        ("Django + Django REST Framework", "5.2 LTS · 3.16", "API REST, ORM, admin, GeoDjango", "Todos los módulos de negocio", "BSD-3", "$0", "D P O"),
        ("Django Channels + Daphne", "4.x", "WebSocket (WSS) para GPS y notificaciones", "Gateway tiempo real, HU-02/14", "BSD-3", "$0", "D P O"),
        ("Celery (worker y beat)", "5.5", "Tareas asíncronas y programadas", "Mensajería, vuelos, expiraciones", "BSD-3", "$0", "D P O"),
        ("simplejwt", "5.x", "Tokens JWT de acceso y refresco", "Autenticación (RBAC)", "MIT", "$0", "D P O"),
        ("Gunicorn", "23", "Servidor WSGI", "API REST", "MIT", "$0", "O"),
        ("PostgreSQL + PostGIS", "16 · 3.4", "Base de datos relacional y geoespacial", "Persistencia, sugerencia, geocerca", "PostgreSQL · GPL-2 (servidor)", "$0", "D P O"),
        ("Redis", "7.2", "Capa de canales, caché de última posición, broker", "Tiempo real, Celery", "BSD-3 (alternativa: Valkey 8)", "$0", "D P O"),
        ("Node.js + TypeScript", "22.23 LTS · 5.9", "Entorno y lenguaje del frontend", "Panel, portal, app", "MIT · Apache-2.0", "$0", "D"),
        ("React + Vite", "19.3 · 6.4", "Interfaces web", "Panel y portal", "MIT", "$0", "D P O"),
        ("Capacitor + background-geolocation", "7.6.9 · 1.2.26", "Empaquetado Android y GPS en segundo plano", "App del conductor, OE-03", "MIT", "$0", "D P O"),
        ("Android Studio + SDK + JDK 21 (Temurin)", "2026.2 · API 29–35", "Compilación y firma de la APK (Gradle requiere JDK 21)", "App del conductor", "Apache-2.0 / términos SDK", "$0", "D"),
        ("Nginx + Certbot", "1.26 · 3.x", "Proxy inverso, TLS, estáticos", "Borde", "BSD-2 · Apache-2.0", "$0", "O"),
        ("Docker Engine + Compose", "27 · v2", "Contenedores reproducibles", "Todos los ambientes", "Apache-2.0", "$0", "D P O"),
        ("GitHub (org flotaagil) + Projects", "Free", "Control de versiones, tablero Scrum, PR", "Gestión de configuración", "SaaS", "$0", "D"),
        ("GitHub Actions + Dependabot", "—", "CI/CD, actualización de dependencias", "Calidad, despliegue", "SaaS", "$0 (2.000 min)", "D P"),
        ("pytest + pytest-django + coverage", "8.x", "Pruebas unitarias e integración backend", "RNF-11", "MIT", "$0", "D P"),
        ("Vitest + Playwright", "3.x · 1.5x", "Pruebas unitarias y E2E web", "Panel, portal", "MIT · Apache-2.0", "$0", "D P"),
        ("k6", "1.x", "Carga y estrés (HTTP y WebSocket)", "RNF-02, RNF-03", "AGPL-3.0 (herramienta local)", "$0", "P"),
        ("OWASP ZAP · Bandit · Ruff/ESLint", "2.16 · 1.8 · —", "Seguridad y análisis estático", "OWASP Top 10, DoD", "Apache-2.0 · MIT", "$0", "D P"),
        ("Figma (Starter)", "—", "Prototipos de interfaz (E-06)", "Diseño", "SaaS", "$0", "D"),
        ("AWS: EC2 t4g.small, EBS gp3, S3, DLM, Route 53, CloudWatch, IAM, SSM", "—", "Hosting, respaldo, DNS, métricas, secretos", "Infraestructura", "Pago por uso", "≈ USD 21/mes", "P O"),
        ("Twilio WhatsApp Business API", "API 2010", "Verificación, avisos y chat", "Mensajería, HU-20/21/30", "Pago por uso", "≈ USD 110/mes", "P O"),
        ("FlightAware AeroAPI / AeroDataBox", "v4 · v1", "Estado y ETA de vuelos", "Monitoreo de vuelos, HU-26/27", "Pago por uso", "≈ USD 30/mes", "P O"),
        ("Google Maps Platform (Maps JS API)", "—", "Mapa del panel y geocodificación", "HU-02, HU-03", "Pago por uso", "Cuota gratuita", "D P O"),
        ("Sentry · UptimeRobot", "SaaS", "Errores de aplicación y disponibilidad", "SLA, incidentes", "SaaS", "$0 · EUR 10", "P O"),
    ]
    r.table("herr", "Inventario de herramientas y servicios", ["Recurso", "Versión", "Función", "Relación", "Licencia", "Costo", "Amb."], herr,
            [3.6, 1.9, 3.3, 3.0, 2.2, 1.6, 1.0], font=7.5)
    r.P("**Hardware y recursos mínimos.** Servidor: EC2 t4g.small (2 vCPU ARM Graviton2, 2 GiB de RAM, 30 GB gp3). El presupuesto de memoria es "
        "PostgreSQL 512 MB, Gunicorn 2 workers × 120 MB, Daphne 150 MB, Celery 250 MB, Redis 128 MB, Nginx 20 MB y sistema 300 MB (≈ 1,6 GB), con "
        "2 GB de swap como resguardo y escalamiento vertical a t4g.medium si el uso supera el 80 % sostenido. La carga esperada es baja para esta "
        "capacidad: 300 mensajes GPS por minuto equivalen a 5 por segundo. Almacenamiento: con posiciones persistidas cada 30 s en espera y cada 10 s en "
        "viaje, 30 días de retención ocupan menos de 1 GB. Clientes: PC con Windows 10 y Chrome o Edge; teléfonos Android 10+ con GPS, 2 GB de RAM y "
        "plan de datos. Equipo: dos estaciones de trabajo y un teléfono Android de pruebas.")
    r.P("**Integración de las tecnologías.** Los tres clientes React consumen la API REST (JSON sobre HTTPS) y abren un canal WSS con Channels. "
        "Django valida el JWT y el rol en cada petición, persiste en PostgreSQL y publica eventos en Redis, desde donde Channels los entrega a los "
        "suscriptores (panel o conductor) por WebSocket (Fette y Melnikov, 2011). Las tareas que dependen de terceros (WhatsApp, vuelos) corren en Celery para no bloquear la API, con "
        "reintentos. Twilio devuelve las respuestas del pasajero por un webhook que entra por Nginx. Todo se empaqueta en contenedores Docker que "
        "se construyen y prueban en GitHub Actions y se despliegan con Docker Compose en la instancia EC2.")


def van_eval(r):
    """Evaluación a tres años con VAN, TIR y PRI (2.1.9). Cifras de data_van.py."""
    import data_van as dv
    r.P("**Evaluación a tres años: VAN, TIR y PRI.** Para medir la factibilidad en el tiempo se proyectó el flujo de caja anual desde dos "
        "miradas, la del cliente actual y la de FlotaÁgil como negocio. Supuestos: horizonte de tres años; tasa de descuento de 12 % anual, con "
        "sensibilidad a 8 % y 15 %; flujos al cierre de cada año y año 0 = puesta en marcha; precios, consumos y costos fijos de esta sección, "
        "sin IVA. El cliente paga la licencia en el año 0 y recibe el beneficio neto de la {T:benef} cada año. FlotaÁgil invierte los "
        "$14.047.000 valorizados en el año 0, cobra una licencia por cada cliente que se incorpora y obtiene el resultado de operar su "
        "cartera, que crece de 1 a 4 y a 11 clientes (año 2: el cliente actual, un Avanzado, un Estándar y un Inicial; año 3: 4 Avanzado, "
        "4 Estándar y 3 Inicial). **Por qué 1 → 4 → 11:** el primer año se dedica a estabilizar el producto con el cliente actual, que luego "
        "sirve de caso de referencia ante otros operadores de taxi turismo y de traslados al aeropuerto, y 11 es la cartera con la que el "
        "punto anterior recupera la inversión valorizada; es una meta comercial, no una demanda validada. El escenario con CC-19 es una "
        f"**proyección de la versión 1.1**: suma en el año 1 su desarrollo, estimado en {dv.CC19_HORAS} horas a la tarifa del presupuesto "
        f"({dv.pesos(dv.TARIFA_HORA)} por hora, más 10 % de imprevistos), es decir, {dv.pesos(dv.CC19_COSTO)}, y desde ese año opera sin Twilio. "
        "El detalle año a año y la estimación por componente están en el Anexo J.")
    r.table("van_res", "Indicadores de la evaluación a tres años", ["Evaluación", "VAN 8 %", "VAN 12 %", "VAN 15 %", "TIR", "PRI"],
            dv.indicadores(), [5.6, 2.1, 2.1, 2.1, 2.3, 2.4], font=7.6,
            source="Elaboración propia. VAN = Σ flujo ÷ (1 + tasa)^año; TIR = tasa con VAN cero; PRI sin descontar, interpolado dentro del año.")
    r.P("La TIR del cliente en el escenario meta no es significativa: la licencia de $500.000 es mínima frente a un beneficio de $5.190.000 "
        "al año, y la tasa que anula el VAN supera el 1.000 %, una cifra sin lectura económica útil. Para el cliente, los indicadores que "
        "importan son el VAN y el PRI.")
    fa, fc = dv.flujos_flotaagil("actual"), dv.flujos_flotaagil("cc19")
    r.table("van_flujo", "Flujo de caja anual de FlotaÁgil", ["Escenario", "Año 0", "Año 1", "Año 2", "Año 3", "VAN 12 %"], [
        (dv.ESCENARIOS["actual"], *[dv.pesos(x) for x in fa], dv.pesos(dv.van(fa))),
        (dv.ESCENARIOS["cc19"], *[dv.pesos(x) for x in fc], dv.pesos(dv.van(fc))),
        ("Clientes activos", "1", "1", "4", "11", "—"),
    ], [4.6, 2.5, 2.1, 2.1, 2.4, 2.3], font=7.8,
        source=f"Elaboración propia. Año 0: inversión valorizada más la licencia del cliente actual. Año 1 con CC-19: incluye su desarrollo ({dv.pesos(dv.CC19_COSTO)}).")
    inc = dv.van(fc) - dv.van(fa)
    v4 = dv.van_con_cartera("cc19", ["A", "A", "E", "I"])
    v9 = dv.van_con_cartera("cc19", ["A"] * 3 + ["E"] * 3 + ["I"] * 3)
    v10 = dv.van_con_cartera("cc19", ["A"] * 4 + ["E"] * 3 + ["I"] * 3)
    da, dc = dv.flujos_flotaagil("actual", dv.INV_DESEMBOLSO), dv.flujos_flotaagil("cc19", dv.INV_DESEMBOLSO)
    r.bullets([
        "**Cliente:** la inversión es pequeña frente al beneficio. En el escenario meta la licencia se recupera en "
        f"{dv.periodo(dv.pri(dv.flujos_cliente('meta')))}; en el prudente, con margen de 20 % y sin mejora de caja, el VAN sigue positivo "
        f"({dv.pesos(dv.van(dv.flujos_cliente('prudente')))}), la TIR es {dv.tir_texto(dv.flujos_cliente('prudente'))} y la recuperación toma "
        f"{dv.periodo(dv.pri(dv.flujos_cliente('prudente')))}. CC-19 no cambia esta mirada, porque el precio del plan es el mismo.",
        f"**FlotaÁgil con la operación actual:** el VAN es negativo con las tres tasas ({dv.pesos(dv.van(fa))} al 12 %) y la TIR es "
        f"{dv.pct(dv.tir(fa))}. A los tres años el flujo acumulado es {dv.pesos(sum(fa))}: el margen de $35.350 a $66.500 por cliente que deja "
        "Twilio no alcanza a devolver las horas invertidas mientras la cartera se forma.",
        f"**FlotaÁgil con CC-19 (proyección v1.1):** aun pagando su desarrollo, el VAN es {dv.pesos(dv.van(fc))} al 12 % y se mantiene "
        f"positivo al 15 % ({dv.pesos(dv.van(fc, 0.15))}); la TIR es {dv.pct(dv.tir(fc))}, sobre las tres tasas evaluadas, y la inversión se "
        f"recupera en {dv.periodo(dv.pri(fc))} ({dv.periodo(dv.pri(fc, dv.TASA))} con flujos descontados). Frente a seguir con Twilio, CC-19 "
        f"aporta {dv.pesos(inc)} de VAN neto de su costo.",
        "**Sensibilidad a la cartera:** el resultado depende de llegar a la meta. Con CC-19, si en el año 3 la cartera se queda en 4 clientes "
        f"el VAN es {dv.pesos(v4)}; con 9 clientes es {dv.pesos(v9)} y recién con 10 pasa a positivo ({dv.pesos(v10)}). Por eso la cartera "
        "se sigue cada trimestre junto con el consumo por reserva (R-04).",
        "**Si solo se mira el desembolso:** con los $847.000 que efectivamente se gastan (equipamiento, nube, licencias, dominio e imprevistos), "
        f"el VAN es positivo en ambos escenarios ({dv.pesos(dv.van(da))} y {dv.pesos(dv.van(dc))} al 12 %). La diferencia con la evaluación "
        "valorizada es el costo de oportunidad de las horas del equipo.",
        "**Límites del cálculo:** no se valoriza el tiempo del equipo en soporte y guardia, por lo que el resultado operativo es lo que queda "
        "para remunerarlo, y no se incluyen impuestos. El costo de CC-19 es una estimación previa a su planificación detallada.",
    ])
