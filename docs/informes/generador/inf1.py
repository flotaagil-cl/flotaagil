"""Informe 1 (formulación) corregido con la retroalimentación de la EF1, según la plantilla de la Unidad 1."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from lib import Report
import sec0, sec1, sec3, sec4, annex
from data_backlog import HU, NUEVAS, RETIRADAS, RESP
from data_cu import CU
from data_hu_cc import HU_CC
from build import pdf, page_texts, norm

F1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "recursos", "inf1img", "")
SENT = "⁣"

COVER = dict(carrera="  ·  Ingeniería en Informática", seccion="2026/P TIHI84/V-IEI-N8-P1-C1/V", sede="La Granja",
             docente="Alan Gajardo Medina", integrantes="Renato González – Carlos Ortiz",
             fecha="Noviembre de 2026", version="Informe 1 · Formulación del proyecto · versión corregida según la retroalimentación de la EF1",
             titulo="FlotaÁgil: Plataforma SaaS para la Gestión de Flotas de Taxi Turismo")


# ======================================================================== I
def intro(r):
    r.H1("Introducción", page_break=False)
    r.P("Este informe presenta la formulación del Proyecto de Título «FlotaÁgil», una plataforma SaaS para la gestión de flotas de taxi turismo "
        "(vehículos de patente naranja) en Chile. El rubro, clave en el turismo y en los traslados desde y hacia el aeropuerto, no cuenta con "
        "herramientas accesibles que no exijan infraestructura local ni hardware propietario. La organización estudiada es una PYME de la Región "
        "Metropolitana que opera como transportista autorizado en el aeropuerto de Santiago, con 30 a 50 vehículos y cerca de 1.500 reservas al "
        "mes, y que hoy coordina su operación con WhatsApp, planillas Excel y un cuaderno de caja.")
    r.P("El problema se midió con evidencia propia (entrevistas, grupo focal, observación directa y tres meses de registros): un 12,1 % de "
        "reservas perdidas, 8 min 40 s por asignación, 35 % de tiempo muerto de la flota y $34.500 diarios de descuadre de caja. Se propone un "
        "producto mínimo viable compuesto por un panel web de administración y despacho, un portal para pasajeros y empresas con convenio, y una "
        "aplicación Android para conductores, que no solo digitaliza la operación: **anticipa** los atrasos de vuelos y ajusta la recogida, "
        "**recomienda** al conductor más adecuado con datos de ubicación, turno y capacidad, **alerta** las desviaciones de la operación y "
        "**mide** el negocio con indicadores para decidir (sección 4.3).")
    r.P("El documento sigue la plantilla de la Unidad 1: identificación y justificación del problema (capítulo II), levantamiento de "
        "requerimientos (III), marco teórico con el estado del arte y la propuesta de valor (IV), solución, impacto y objetivos (V), "
        "metodología, cronograma, equipo, recursos y riesgos (VI), arquitectura de TI (VII), arquitectura empresarial (VIII) y conclusiones (IX). "
        "Esta versión incorpora la retroalimentación de la evaluación formativa y es coherente con el Informe 2, que desarrolla el diseño y la "
        "implementación de la solución.")

    r.H2("Retroalimentación de la evaluación formativa y su tratamiento")
    r.P("El académico guía destacó que el problema no solo está descrito, sino respaldado con evidencia concreta obtenida mediante entrevistas, "
        "observación y antecedentes operacionales; esa base se mantiene. Señaló como principal mejora demostrar qué aporta la propuesta "
        "tecnológicamente más allá de digitalizar la operación actual, y pidió profundizar el marco normativo del transporte remunerado de "
        "pasajeros y la privacidad del seguimiento GPS de los conductores. La {T:obs1} registra cada observación, incluidas las anotaciones "
        "sobre los diagramas, y dónde se atendió.")
    rows = [
        ("La propuesta es principalmente una innovación incremental; falta una capacidad realmente diferenciadora", "Se definen cinco capacidades de apoyo a la decisión basadas en datos: detección anticipada de atrasos de vuelos con ajuste de la recogida, asignación inteligente asistida, alertas de desviación de la operación, tablero de indicadores y, como evolución, predicción de demanda. Cada una indica qué datos usa, qué técnica aplica y qué decisión mejora", "4.3, 5.1.1"),
        ("Incorporar con mayor profundidad el marco normativo específico del transporte remunerado de pasajeros", "Análisis de la Ley 18.696, el DS 212/1992 del MTT, la Ley de Tránsito, el seguro obligatorio, la operación en el aeropuerto y la Ley 21.553, con su efecto en el diseño", "2.2.3"),
        ("Revisar la privacidad asociada al seguimiento GPS de los conductores", "Ubicación solo en turno y con consentimiento (RN-18), finalidad declarada, cláusula en el Reglamento Interno (DT Ord. N° 148), acceso por rol, retención de 30 días con eliminación automática (RN-15) y derechos de la Ley 21.719", "2.2.3, 7.6.5"),
        ("AS-IS (p. 11): falta el nombre del proceso, las acciones no usan verbo en infinitivo y hay acciones después de un evento de término", "Se rehízo en BPMN 2.0: pool con el nombre del proceso, carriles por actor, todas las tareas en infinitivo y un único evento de término al final", "2.1.7"),
        ("RNF sin indicar el atributo de calidad que protegen (p. 17)", "Cada RNF se asocia a una característica de ISO/IEC 25010 y a su forma de verificación", "3.3"),
        ("TO-BE (p. 23): revisar la simbología y usar verbo en infinitivo", "El TO-BE se modela en tres procesos BPMN 2.0 (recepción de reservas, despacho y ejecución con cobro) con eventos, compuertas y flujos de mensaje correctos", "5.1.2"),
        ("Matriz RACI (p. 41): conflicto de interés, la misma persona es responsable y aprueba", "Se elimina la matriz RACI: en Scrum las responsabilidades las definen los roles. El Product Owner (Juan Pérez) es distinto de quienes desarrollan, y el cliente acepta en la UAT", "6.3"),
        ("Diagramas de contenedores y componentes (pp. 48–49)", "Se reemplazan por un diagrama de componentes UML 2.5 con interfaces proporcionadas y requeridas y las rutas de la API", "7.3"),
        ("Despliegue (p. 50): «¿Cuál? ¿Son los mismos recursos?» por la indicación AWS / GCP", "Se define un solo proveedor, AWS (región us-east-1), con los recursos concretos (EC2 t4g.small, EBS, S3, Route 53, CloudWatch) y PostgreSQL 16 en contenedor; los mismos del Informe 2", "7.4"),
    ]
    r.table("obs1", "Observaciones de la evaluación formativa y su tratamiento", ["Observación", "Tratamiento", "Sección"], rows, [5.6, 9.2, 1.8], font=8)


# ======================================================================== II
def problema(r):
    r.H1("Identificación del Problema")
    r.H2("Actualización y justificación del problema")
    r.H3("Descripción de la organización")
    r.P("El proyecto se aborda bajo la modalidad de internalización a una empresa: se entrega una solución de software a una empresa cliente del "
        "rubro del taxi turismo para digitalizar y optimizar sus procesos operativos y administrativos. Sus aspectos organizacionales son:")
    r.bullets([
        "**Tipo y rubro:** empresa privada de servicios (PYME) de transporte de pasajeros y turismo, con vehículos de patente naranja. Opera como "
        "transportista autorizado en el aeropuerto internacional de Santiago, origen o destino de cerca del 40 % de sus viajes (EV-08).",
        "**Posicionamiento:** trayectoria local en traslados desde y hacia el aeropuerto, hoteles y clientes corporativos con convenio. Compite por "
        "puntualidad, seguridad y trato personalizado.",
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
        ("Consideración ética", "El proyecto trata datos personales de pasajeros y la ubicación de trabajadores, lo que obliga a aplicar finalidad, minimización y límites al monitoreo (Ley N° 19.628, modificada por la Ley N° 21.719; sección 2.2.3)."),
    ]
    r.table("just", "Criterios de elección de la organización", ["Criterio", "Fundamentación"], just, [4.0, 12.6], font=8.5, first_col_bold=True)

    r.H3("Arquitectura tecnológica actual")
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
    r.table("tec_actual", "Situación tecnológica actual", ["Dimensión", "Situación documentada"], tec, [3.6, 13.0], font=8.5, first_col_bold=True)

    r.H3("Arquitectura de aplicaciones actual")
    r.figure(F1 + "img-018.png", "apps_asis", "Arquitectura de aplicaciones actual (AS-IS)", width_cm=15)
    r.P("El despachador es el único punto de integración entre herramientas desconectadas: la información se transcribe a mano entre WhatsApp, la "
        "planilla y el cuaderno, sin una fuente única de datos ({F:apps_asis}).")

    r.H3("Antecedentes de la organización")
    r.table("antec", "Evolución de la problemática", ["Situación en el pasado", "Situación actual"], [
        ("Con una flota pequeña y pocos clientes, la gestión con cuadernos, llamadas y radio era suficiente y los errores eran fáciles de corregir.",
         "El crecimiento de la demanda y de la flota hizo colapsar el uso de WhatsApp y Excel: se pierden reservas, no se conoce la ubicación de los "
         "vehículos y la caja no cuadra."),
    ], [8.3, 8.3], font=8.5)

    r.H3("Diagnóstico de la situación actual y análisis de causas")
    r.P("La asignación es ineficiente: el despachador contacta a los conductores uno por uno para conocer su disponibilidad y ubicación, porque no "
        "existe geolocalización centralizada. Esto produce viajes perdidos, tiempos muertos, un pasajero sin información sobre su traslado y una "
        "cuadratura diaria compleja, porque la mayoría de los viajes se cobran en efectivo al conductor sin registro central. Para ir más allá de los "
        "síntomas se aplicó un diagrama de causa y efecto (Ishikawa) con seis categorías ({F:ishikawa}).")
    r.figure(F1 + "img-021.png", "ishikawa", "Diagrama de causa y efecto (Ishikawa) del problema operativo", width_cm=16)
    r.P("El problema no se origina en la falta de esfuerzo del personal, sino en **tres causas raíz tecnológicas**: la ausencia de una fuente única "
        "de datos, la falta de trazabilidad geográfica de la flota y la inexistencia de un registro digital del cobro. A ellas se suma una causa de "
        "decisión: el despachador asigna por memoria, sin datos sobre quién está más cerca, quién lleva más tiempo esperando o si un vuelo se "
        "atrasó. Las tres primeras se resuelven digitalizando; la cuarta exige apoyo a la decisión (sección 4.3).")

    r.H3("Modelo AS-IS del proceso actual")
    r.P("La {F:asis} modela el proceso actual en BPMN 2.0. Respecto de la versión anterior se corrigió la notación: el pool lleva el nombre del "
        "proceso («Proceso actual de reserva, despacho y cobro»), cada carril corresponde a un actor (despachador y conductor), el pasajero es un "
        "participante externo que se comunica por flujos de mensaje, todas las tareas se nombran con verbo en infinitivo y el proceso termina en un "
        "único evento de término, sin acciones posteriores.")
    r.figure("fig/bpmn_asis.png", "asis", "Modelo AS-IS: proceso actual de reserva, despacho y cobro (BPMN 2.0)", width_cm=16.6)
    r.P("El modelo evidencia dos cuellos de botella. El primero es el ciclo de búsqueda secuencial del conductor disponible (compuerta "
        "«¿Disponible?»), que se repite hasta encontrar uno libre y cuya duración crece con el tamaño de la flota. El segundo es el registro manual "
        "del cobro al cierre del turno, desacoplado del momento del pago, que introduce errores de memoria y omisiones.")

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
        ("Normativa", "Datos que la normativa exige registrar (conductor, licencia, vehículo) y tratamiento lícito de datos personales", "Trámites ante el MTT, el aeropuerto o las aseguradoras, que siguen a cargo de la empresa"),
    ], [2.6, 7.0, 7.0], font=8.2, first_col_bold=True)

    r.H2("Justificación del problema")
    r.H3("Relevancia del problema y evidencia cuantitativa")
    r.P("Se midió el registro histórico de junio a agosto de 2026, contrastando las planillas de reservas con el cuaderno de caja ({T:evid_q}). Estas "
        "cifras son la línea base de los indicadores de gestión de la sección 5.2.3.")
    r.table("evid_q", "Evidencia cuantitativa del problema (jun–ago 2026)", ["Indicador", "Valor", "Fuente", "Impacto estimado"], [
        ("Reservas ingresadas (promedio mensual)", "1.512", "Planillas Excel de la central", "Volumen base de la operación"),
        ("Reservas perdidas o no ejecutadas", "12,1 % (183/mes)", "Reservas anotadas versus viajes en caja", "≈ $2.196.000 mensuales de ingreso bruto"),
        ("Tiempo muerto de la flota", "35 % de la jornada", "Bitácora de 3 conductores, 10 jornadas", "Un tercio menos de capacidad productiva"),
        ("Tiempo promedio de asignación", "8 min 40 s", "Cronometraje de 45 asignaciones", "Espera del pasajero y riesgo de fuga"),
        ("Descuadre de caja diario", "$34.500", "Cuaderno de caja versus efectivo rendido", "≈ $1.035.000 mensuales sin trazabilidad"),
        ("Errores de transcripción", "7,4 %", "Auditoría de 300 registros", "Reservas duplicadas o direcciones erróneas"),
        ("Reservas corporativas", "22 %", "Clasificación de planillas", "Segmento sin canal digital"),
        ("Viajes desde o hacia el aeropuerto", "≈ 40 %", "Entrevista de seguimiento (EV-08)", "Recogidas expuestas a atrasos de vuelos"),
    ], [4.6, 2.6, 4.8, 4.6], font=8.2)
    r.P("La solución proyecta bajar la pérdida de reservas a 5,0 % o menos, la asignación a menos de 3 minutos y el tiempo muerto a 28 % o menos. "
        "Los $2.196.000 son ingreso bruto: el efecto sobre la rentabilidad se calcula con el margen neto de esos viajes en la factibilidad "
        "económica del Informe 2.")

    r.H3("Complejidad del problema")
    r.P("La complejidad está en orquestar eventos concurrentes y datos en tiempo real: actualizar la ubicación de 30 a 50 vehículos que envían su "
        "posición cada 5 a 30 segundos (≈ 300 mensajes por minuto en hora punta), administrar la máquina de estados de más de 1.500 viajes "
        "mensuales sin que dos despachadores asignen al mismo conductor, integrar servicios externos que fallan o responden lento (WhatsApp y "
        "datos de vuelos) sin bloquear al usuario, recalcular recogidas cuando un vuelo cambia su hora estimada y comunicar el panel y la app de "
        "forma bidireccional por WebSocket, todo con una disponibilidad comprometida de 99,0 %. Se suma una complejidad no técnica: hacerlo "
        "respetando la normativa del transporte y la privacidad de los conductores.")

    r.H3("Marco normativo del transporte remunerado de pasajeros y de la privacidad")
    r.P("La solución opera dentro de un rubro regulado. La {T:normativa} resume las normas que rigen a la organización, qué exigen y cómo "
        "condicionan el diseño. El sistema **no reemplaza** las obligaciones de la empresa ante la autoridad (inscripciones, revisiones, "
        "permisos), pero sí debe registrar los datos que esas obligaciones requieren y no inducir incumplimientos.")

    r.table("normativa", "Marco normativo aplicable y su efecto en el diseño", ["Norma", "Qué regula", "Exigencia relevante para el caso", "Efecto en FlotaÁgil"], [
        ("Ley N° 18.696 (1988), art. 3", "Faculta al Ministerio de Transportes y Telecomunicaciones (MTT) para regular el transporte público de pasajeros",
         "Los servicios de taxi, incluido el taxi turismo, se prestan bajo las condiciones que fije el MTT por reglamento",
         "El sistema se diseña para una empresa ya autorizada; no presta ni intermedia servicios por sí mismo"),
        ("DS N° 212/1992 del MTT (Reglamento de los Servicios Nacionales de Transporte Público de Pasajeros)", "Inscripción de los servicios y vehículos en el Registro Nacional de Servicios de Transporte Público de Pasajeros; condiciones de los taxis, entre ellos los de turismo",
         "Vehículo inscrito con su patente, antigüedad máxima y revisión técnica vigente; conductor habilitado",
         "VEHICULO registra patente, año y capacidad (antigüedad validada); CONDUCTOR registra licencia y su vencimiento, para alertar antes de que expire"),
        ("Ley de Tránsito N° 18.290 (texto refundido DFL N° 1/2009)", "Licencias de conducir y normas de circulación",
         "Licencia profesional para conducir vehículos de transporte de pasajeros; prohibición de manipular el teléfono al conducir",
         "Clase y vencimiento de la licencia en CONDUCTOR; app operable con una mano, aceptación con un toque y sin lectura de mensajes en ruta (RNF-06)"),
        ("Ley N° 18.490 (seguro obligatorio de accidentes personales)", "Seguro obligatorio de los vehículos motorizados",
         "Seguro vigente para circular; los servicios de pasajeros suman seguros exigidos por el MTT",
         "Fuera del sistema; se registra como requisito del vehículo en la carga inicial"),
        ("Contrato de concesión y reglas del aeropuerto de Santiago", "Acceso de transportistas a la zona de embarque y estacionamientos",
         "Solo operadores autorizados recogen en la zona asignada y respetan el orden de salida",
         "La fila virtual (RN-16) reproduce el orden de llegada a la zona autorizada, sin alterar las reglas del concesionario"),
        ("Ley N° 21.553 (2023), empresas de aplicación de transporte (EAT)", "Plataformas que intermedian entre pasajeros y conductores; registro de EAT y de conductores",
         "Se aplica a quien conecta pasajeros con conductores de terceros; su reglamento no se había publicado al cierre de este informe y la ley rige 30 días después de esa publicación",
         "FlotaÁgil es una herramienta interna de una empresa con flota propia o registrada, no una EAT; si en el futuro abriera el servicio a conductores independientes, debería evaluarse su inscripción"),
        ("Ley N° 19.628, modificada por la Ley N° 21.719 (entra en vigencia el 1 de diciembre de 2026)", "Tratamiento de datos personales; crea la Agencia de Protección de Datos Personales",
         "Licitud, finalidad, proporcionalidad, información al titular, seguridad, derechos de acceso, rectificación, supresión, oposición y portabilidad",
         "Aviso de privacidad aceptado al crear la cuenta, con fecha y versión; retención limitada (RN-15); eliminación de la cuenta; acceso por rol y empresa (RN-13)"),
        ("Código del Trabajo, arts. 5 y 154, y Dictamen DT Ord. N° 148 (2022)", "Medidas de control del empleador y respeto de los derechos fundamentales",
         "La geolocalización de trabajadores debe estar en el Reglamento Interno, ser general, idónea y proporcional, y no transformarse en vigilancia permanente",
         "GPS solo en turno y con consentimiento (RN-18); cláusula tipo para el Reglamento Interno del cliente; sin seguimiento fuera de la jornada"),
    ], [3.2, 3.35, 4.5, 5.55], font=7.2,
        source="Elaboración propia con base en Biblioteca del Congreso Nacional de Chile (1986, 1988, 1992, 1999, 2009, 2023, 2024) y Dirección del Trabajo (2022).")

    r.P("**Privacidad del seguimiento GPS de los conductores.** Es el tratamiento de datos más sensible del proyecto, porque registra dónde "
        "está una persona mientras trabaja. Se aborda con seis decisiones, detalladas en la sección 7.6.5: 1) **finalidad** declarada y "
        "limitada (despacho, seguridad del pasajero, fila del aeropuerto e indicadores de operación), sin uso para sanciones automáticas ni para "
        "perfilar al conductor; 2) **proporcionalidad**: el teléfono envía su posición solo durante el turno y deja de hacerlo al terminarlo "
        "(RN-18); 3) **información y consentimiento**: el conductor acepta un aviso que explica qué se registra, cuándo, quién lo ve y por cuánto "
        "tiempo, y la aceptación queda registrada; 4) **base laboral**: si el conductor es dependiente, la medida se incorpora al Reglamento "
        "Interno de la empresa, como exige la Dirección del Trabajo; 5) **acceso restringido**: solo el administrador y el despachador de su "
        "empresa ven la ubicación (RN-13); y 6) **retención mínima**: las posiciones se eliminan a los 30 días con una tarea programada "
        "(RN-15). Así, la geolocalización queda como herramienta de operación y no como mecanismo de vigilancia.")


# ======================================================================== III
def levantamiento(r):
    r.H1("Levantamiento de Requerimientos")
    r.H2("Plan e instrumentos de levantamiento")
    r.P("El levantamiento se hizo en tres etapas durante las semanas 1 a 4, más una entrevista de seguimiento ({T:plan_lev}). Las pautas están en el "
        "Anexo 2 y las evidencias, en el Anexo 3.")
    r.table("plan_lev", "Plan de levantamiento ejecutado", ["Etapa", "Instrumento", "Participantes", "Duración", "Evidencia"], [
        ("1. Exploración", "Entrevista semiestructurada al administrador", "Dueño de la flota", "60 min", "EV-01"),
        ("1. Exploración", "Entrevista semiestructurada al despachador", "Despachador con 4 años de antigüedad", "45 min", "EV-02"),
        ("2. Contraste", "Grupo focal con conductores", "3 conductores de distintos turnos", "50 min", "EV-03"),
        ("2. Contraste", "Observación directa en la central", "Observador no participante", "2 jornadas de 4 h", "EV-04"),
        ("3. Validación", "Análisis documental de planillas y caja", "Registros de junio a agosto de 2026", "300 registros", "EV-05, EV-06"),
        ("3. Validación", "Validación del backlog con el cliente", "Administrador y equipo", "40 min", "EV-07 (acta 28/08/2026)"),
        ("4. Seguimiento", "Entrevista sobre la operación en el aeropuerto", "Administrador y despachador", "55 min", "EV-08 (02/09/2026)"),
    ], [2.4, 4.8, 4.2, 2.2, 3.0], font=8.2)

    r.H2("Resultados del levantamiento")
    r.P("Los hallazgos se agruparon por categoría, se contó su frecuencia de mención y cada necesidad se trazó a la historia que la responde "
        "({T:res_lev}).")
    r.table("res_lev", "Hallazgos sistematizados y su trazabilidad", ["Categoría", "Hallazgo", "Menciones", "Necesidad derivada", "HU"], [
        ("Visibilidad de flota", "No se conoce la ubicación sin llamar al conductor", "5 de 5", "Mapa de la flota en tiempo real", "HU-02"),
        ("Asignación", "Buscar un conductor libre es lento y depende de la memoria", "4 de 5", "Sugerencia del conductor más apto", "HU-04, HU-29"),
        ("Registro de reservas", "Las reservas se pierden o duplican al transcribirlas", "5 de 5", "Registro digital único", "HU-03, HU-19"),
        ("Cobros", "No se sabe cuánto se recaudó hasta el cierre", "3 de 5", "Método y monto por viaje y cierre por turno", "HU-16, HU-06, HU-31"),
        ("Clientes corporativos", "Las empresas con convenio llaman por cada traslado", "2 de 5", "Canal digital para convenios", "HU-11, HU-25"),
        ("Experiencia del pasajero", "El pasajero llama para saber si el vehículo viene", "4 de 5", "Avisos de estado por WhatsApp", "HU-21, HU-30"),
        ("Operación del conductor", "Leer el viaje en WhatsApp obliga a hacerlo conduciendo", "3 de 3", "Notificación con aceptación explícita", "HU-14, HU-15"),
        ("Autonomía del conductor", "No hay forma formal de rechazar un viaje", "3 de 3", "Rechazo con reasignación", "HU-15"),
        ("Respaldo del conductor", "No hay registro propio de los viajes del turno", "2 de 3", "Historial del turno en la app", "HU-18"),
        ("Aeropuerto (EV-08)", "Los atrasos de vuelos obligan a reprogramar a mano", "2 de 2", "Seguimiento de vuelos y ajuste de recogida", "HU-26, HU-27"),
        ("Aeropuerto (EV-08)", "El turno de salida en el aeropuerto se resuelve de palabra", "2 de 2", "Fila virtual por orden de llegada", "HU-29"),
    ], [3.0, 5.4, 1.6, 4.2, 2.4], font=8)

    r.H2("Detalle de los requerimientos")
    h3 = r.H3
    r.H3 = lambda text: None
    sec1.requerimientos(r)
    r.H3 = h3


# ======================================================================== IV
def marco(r):
    r.H1("Marco Teórico")
    r.H2("Investigación bibliográfica")
    r.P("El proyecto se fundamenta en ingeniería de software, arquitecturas distribuidas, computación en la nube y el marco legal chileno, con "
        "citas en formato APA 7. Las fuentes se buscaron en libros de referencia de la disciplina, especificaciones de organismos técnicos (IETF, "
        "NIST, ISO, OWASP) y en la Biblioteca del Congreso Nacional, y se seleccionaron por su pertinencia directa con una decisión del proyecto:")
    r.bullets([
        "**Ciclo de vida y metodología:** ciclo iterativo e incremental con Scrum. Las metodologías ágiles permiten adaptarse a cambios de "
        "requerimientos mediante entregas continuas (Pressman y Maxim, 2020); Schwaber y Sutherland (2020) definen roles, eventos y artefactos; la "
        "dirección del proyecto se apoya en la guía PMBOK (Project Management Institute [PMI], 2021).",
        "**Ingeniería de requerimientos:** la calidad del producto depende de la precisión del levantamiento (Sommerville, 2016), lo que justifica "
        "varios instrumentos complementarios y la trazabilidad explícita entre necesidades e historias. ISO/IEC 25010 (ISO, 2023) organiza los "
        "requerimientos no funcionales por característica de calidad.",
        "**Arquitectura de software:** los atributos de calidad guían las decisiones de arquitectura desde la formulación (Bass et al., 2021); "
        "Richards y Ford (2020) aportan criterios para arquitecturas distribuidas, bajo los cuales se adopta un diseño API-first.",
        "**Computación en la nube:** la definición del NIST caracteriza el modelo SaaS y su elasticidad, sin infraestructura local para el cliente "
        "(Mell y Grance, 2011).",
        "**Información geográfica:** PostGIS permite almacenar y consultar datos geoespaciales con índices espaciales (Obe y Hsu, 2021), base de la "
        "geocerca, del cálculo de proximidad y de la fila virtual.",
        "**Tiempo real:** el protocolo WebSocket (Fette y Melnikov, 2011) permite comunicación bidireccional persistente, base de la transmisión de "
        "posiciones y estados.",
        "**Aplicaciones híbridas:** empaquetar una aplicación web como aplicación instalable reduce el esfuerzo frente al desarrollo nativo "
        "(Griffith, 2017), marco de la elección de Capacitor.",
        "**Modelado de procesos:** BPMN 2.0 (ISO/IEC 19510; ISO, 2013) define la notación de los modelos AS-IS y TO-BE, y UML 2.5 (Object "
        "Management Group, 2017) la de casos de uso y componentes.",
        "**Seguridad y protección de datos:** OWASP Top 10 y ASVS (OWASP Foundation, 2021a, 2021b), ISO/IEC 27001:2022 y la Ley N° 21.719, que "
        "moderniza la Ley N° 19.628; para la geolocalización laboral, el Dictamen N° 148 de la Dirección del Trabajo (2022).",
        "**Transporte de pasajeros:** el DS N° 212 del MTT (Biblioteca del Congreso Nacional de Chile, 1992) y la Ley N° 21.553 (2023) definen el "
        "marco en que opera la organización (sección 2.2.3).",
    ])

    r.H2("Estado del arte")
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

    r.H2("Propuesta de valor y capacidades diferenciadoras")
    r.P("Digitalizar el proceso actual (registrar reservas en un formulario, ver la flota en un mapa, anotar el cobro en la app) es necesario, "
        "pero no basta: el despachador seguiría decidiendo por memoria y enterándose tarde de lo que pasa. La propuesta de FlotaÁgil es pasar de "
        "**registrar** la operación a **apoyar las decisiones** con los datos que la propia operación genera. Se definen cinco capacidades "
        "({T:difer}); las cuatro primeras forman parte del producto mínimo viable y la quinta es su evolución natural, porque usa los datos que "
        "el MVP empieza a acumular.")

    r.table("difer", "Capacidades diferenciadoras de FlotaÁgil", ["Capacidad", "Qué hace", "Datos y técnica", "Decisión que mejora", "Alcance"], [
        ("1. Detección anticipada de atrasos de vuelos y ajuste de la recogida",
         "Monitorea el vuelo de cada recogida en el aeropuerto y, cuando cambia su hora estimada de llegada, propone la nueva hora de recogida y alerta las cancelaciones y desvíos. Lema para el pasajero: «Seguimos tu vuelo por ti: no necesitas avisarnos si se atrasa»",
         "Número de vuelo validado contra una API de datos de vuelos; consultas programadas cada 30 min y cada 10 min en la última hora; nueva recogida = hora estimada + margen nacional o internacional (RN-17)",
         "Cuándo enviar al conductor: evita esperas pagadas y recogidas perdidas sin depender de que el pasajero avise. El despachador confirma (RN-02)",
         "MVP (HU-26, HU-27, HU-28)"),
        ("2. Asignación inteligente asistida",
         "Ordena a los conductores candidatos para cada reserva y explica por qué propone a cada uno",
         "Filtra por estado Disponible (RN-01), sin viaje en curso (RN-03) y con capacidad suficiente para los pasajeros; ordena por el turno de la fila virtual en el aeropuerto (RN-16) o por distancia real calculada con PostGIS sobre la última posición",
         "A quién asignar: reemplaza 5 a 10 llamadas por una propuesta de un clic; meta < 3 min por asignación",
         "MVP (HU-04, HU-29)"),
        ("3. Alertas de desviación de la operación",
         "Detecta lo que se desvía del plan antes de que el pasajero llame",
         "Temporizador de 60 s sin respuesta del conductor (RN-04); llegada automática por geocerca de 150 m; espera por no presentación; salida de la fila tras 10 min fuera de la zona; alertas de vuelo",
         "Cuándo intervenir: reasignar, llamar al pasajero o liberar al conductor a tiempo",
         "MVP (HU-15, HU-16, HU-28, HU-29)"),
        ("4. Tablero de indicadores para decidir",
         "Calcula nueve indicadores con semáforo y meta, y cuadra la caja por turno",
         "Consultas sobre el historial de estados, asignaciones, turnos y pagos; intervalos de semáforo definidos (sección 5.2.3)",
         "Dónde mejorar: horas con más pérdida, conductores con más rechazos, diferencias de caja",
         "MVP (HU-01, HU-06, HU-31)"),
        ("5. Predicción de demanda por franja horaria",
         "Estima cuántos viajes habrá por hora y cuántos conductores conviene tener en la fila del aeropuerto",
         "Historial de viajes por día y hora más las llegadas programadas de vuelos al aeropuerto; promedio móvil estacional como primera versión, evaluable contra lo real",
         "Cuántos conductores programar y cuándo: reduce el tiempo muerto (meta ≤ 28 %)",
         "Evolución posterior al MVP: requiere al menos tres meses de datos del sistema"),
    ], [2.9, 4.1, 4.5, 3.35, 1.75], font=7.0)

    r.P("**Por qué es más que digitalizar.** En el proceso actual el despachador se entera de un atraso cuando el pasajero llama, elige al "
        "conductor según a quién logra contactar y conoce el resultado del día solo al cuadrar la caja. Con FlotaÁgil el sistema **anticipa** "
        "(el vuelo se atrasó y la recogida ya tiene una propuesta), **recomienda** (estos son los tres mejores conductores y por qué), **alerta** "
        "(este conductor no respondió; este pasajero no se presentó) y **mide** (el indicador de la semana está en rojo). La decisión final sigue "
        "siendo humana (RN-02), porque la responsabilidad del servicio es de la empresa; lo que cambia es que se toma con datos. Ninguna de las "
        "siete soluciones del estado del arte combina estas capacidades para una PYME de taxi turismo, y menos con el pasajero atendido de punta "
        "a punta por WhatsApp, sin instalar una aplicación.")


# ======================================================================== V
def objetivos(r):
    r.H1("Objetivos del Proyecto")
    r.H2("Solución tecnológica")
    r.H3("Formulación de la solución")
    r.P("La solución es un SaaS con tres clientes sobre un mismo backend: un **panel web** para el administrador y el despachador (mapa de la "
        "flota, reservas, despacho asistido, reportes y auditoría), un **portal web** para el pasajero y las empresas con convenio (pedir, seguir "
        "y cancelar viajes con su cuenta) y una **aplicación Android** para el conductor (turno, aceptación de viajes, navegación, cobro y envío de "
        "su posición). Integra WhatsApp para verificar y avisar al pasajero, una API de datos de vuelos y mapas. Sus capacidades diferenciadoras "
        "son las de la sección 4.3. Se formula sobre cinco atributos de calidad:")
    r.bullets([
        "**Disponibilidad y continuidad:** infraestructura cloud con disponibilidad de 99,0 % 24/7, snapshots y respaldos lógicos cada 6 h (RPO de 6 h).",
        "**Rendimiento:** WebSocket para posiciones y estados en vivo, y tareas en segundo plano para que los servicios externos no hagan "
        "esperar al usuario.",
        "**Seguridad y privacidad:** autenticación con tokens de corta duración y renovación segura, control de acceso por rol y por empresa, "
        "cifrado en tránsito y en reposo, auditoría de acciones sensibles y GPS solo en turno con consentimiento.",
        "**Integración:** arquitectura API-first con WhatsApp Business API (vía Twilio), datos de vuelos y mapas, cada uno detrás de un adaptador "
        "para poder cambiar de proveedor.",
        "**Usabilidad:** interfaces por perfil; en la app del conductor, operación con una mano y pocas interacciones por viaje.",
    ])

    r.H3("Modelo TO-BE del proceso propuesto")
    r.P("El proceso propuesto se modela en BPMN 2.0 en tres procesos principales, que corresponden a las etapas del flujo actual: recepción y "
        "confirmación de reservas (P1), despacho y asignación (P2) y ejecución del traslado y cobro (P3). Cada uno tiene su pool con nombre, "
        "carriles por actor (incluido el sistema), tareas en infinitivo, compuertas exclusivas con sus condiciones, eventos de temporizador y de "
        "mensaje, y un único evento de término por camino. Los subprocesos de cada uno se detallan en el Informe 2.")
    r.figure("fig/bpmn_p1.png", "p1", "TO-BE · P1 Recepción y confirmación de reservas (BPMN 2.0)", width_cm=16.6)
    r.figure("fig/bpmn_p2.png", "p2", "TO-BE · P2 Despacho y asignación de viajes (BPMN 2.0)", width_cm=16.6)
    r.figure("fig/bpmn_p3.png", "p3", "TO-BE · P3 Ejecución del traslado y cobro (BPMN 2.0)", width_cm=16.6)
    r.P("La comparación entre ambos modelos permite cuantificar la mejora esperada ({T:asis_tobe}).")
    r.table("asis_tobe", "Comparación entre el proceso actual y el propuesto", ["Aspecto del proceso", "Situación AS-IS", "Situación TO-BE", "Mejora esperada"], [
        ("Ingreso de la reserva", "Transcripción manual desde WhatsApp o llamada", "Registro digital directo por el pasajero con cuenta, el convenio o el despachador", "Elimina el 7,4 % de errores de transcripción"),
        ("Identificación del solicitante", "Confianza verbal, sin verificación", "Teléfono verificado por WhatsApp o cuenta de la empresa con convenio", "Reduce reservas falsas o erróneas"),
        ("Atrasos de vuelos", "El pasajero avisa (o no) y la recogida se reprograma a mano", "El sistema monitorea el vuelo y propone la nueva hora", "Menos esperas y recogidas perdidas"),
        ("Búsqueda de conductor", "Contacto secuencial uno a uno", "Sugerencia por fila del aeropuerto, distancia, disponibilidad y capacidad", "Asignación de 8 min 40 s a menos de 3 min"),
        ("Confirmación del conductor", "Respuesta verbal sin registro", "Aceptación o rechazo explícito con temporizador de 60 s", "Reasignación oportuna ante no respuesta"),
        ("Seguimiento del viaje", "Inexistente; el pasajero llama a la central", "Estados en vivo y avisos por WhatsApp", "Menos llamadas de consulta"),
        ("Registro del cobro", "Anotación manual al cierre de la jornada", "Método y monto al finalizar cada viaje y cierre de caja por turno", "Elimina el descuadre promedio de $34.500 diarios"),
    ], [3.2, 4.0, 5.0, 4.4], font=8)

    r.H3("Alcance y restricciones de la solución")
    r.P("**Dentro del alcance:** reserva desde el panel, el portal (con cuenta del pasajero o de la empresa con convenio) y WhatsApp; verificación "
        "del pasajero por WhatsApp; despacho asistido con confirmación humana; fila virtual del aeropuerto; seguimiento de vuelos con ajuste de la "
        "recogida; ejecución del viaje con estados y geocerca; registro del cobro y cierre de caja por turno; avisos y calificación por WhatsApp; "
        "chat con el pasajero desde el panel; indicadores, reportes y auditoría.")
    r.P("**Fuera del alcance:** pasarelas de pago, definición de tarifas, facturación electrónica, aplicación nativa para pasajeros, despacho "
        "automático sin confirmación humana, predicción de demanda (evolución posterior), chatbot y aislamiento completo entre empresas. "
        "**Restricciones:** equipo de dos desarrolladores, 16 semanas, presupuesto de PYME, una sola instancia cloud y Android 10 o superior.")

    r.H3("Diagrama de contexto")
    r.figure("fig/contexto.png", "contexto", "Diagrama de contexto del sistema", width_cm=15.5)
    r.P("La frontera del sistema ({F:contexto}) deja fuera la definición de tarifas, la facturación tributaria, el mantenimiento de la flota y los "
        "trámites ante la autoridad, que siguen a cargo de la organización.")

    r.H3("Casos de uso")
    r.P("Los requerimientos se organizan en 17 casos de uso UML 2.5 ({F:cu}; {T:cu_list}). Los actores principales son el administrador, el "
        "despachador, el conductor, el pasajero y el supervisor de convenio; los secundarios, los servicios de WhatsApp, de datos de vuelos y de "
        "mapas, y el temporizador del sistema. La especificación completa de cada caso se presenta en el Informe 2.")
    r.figure("fig/uml_cu.png", "cu", "Diagrama de casos de uso de FlotaÁgil (UML 2.5)", width_cm=16.6)
    rows = [(c["id"], c["nombre"], c["act"], c["obj"]) for c in CU]
    r.table("cu_list", "Casos de uso y su objetivo", ["ID", "Caso de uso", "Actor principal", "Objetivo"], rows, [1.4, 4.0, 3.2, 8.0], font=7.8)

    r.H3("Modelo conceptual de datos")
    r.P("El dominio se organiza en torno a las entidades de la {T:conceptual}; su modelo lógico está en la sección 7.5.")
    r.table("conceptual", "Entidades conceptuales del dominio", ["Entidad", "Descripción", "Relaciones principales"], [
        ("Empresa", "Organización dueña de la flota que usa la plataforma", "Agrupa usuarios, conductores, vehículos, convenios y su configuración"),
        ("Usuario", "Persona con acceso, diferenciada por rol", "Pertenece a una empresa; opera reservas y asignaciones"),
        ("Conductor", "Operario en ruta que ejecuta los traslados", "Pertenece a una empresa; usa uno o más vehículos; ejecuta viajes"),
        ("Vehículo", "Móvil habilitado para el servicio", "Se asocia a conductores; uno se declara activo por turno"),
        ("Convenio", "Acuerdo con una empresa cliente para reservas corporativas", "Origina viajes; tiene su propia cuenta; sus cambios se auditan"),
        ("Pasajero", "Solicitante del traslado, particular o de convenio", "Origina viajes; se verifica por WhatsApp; puede tener cuenta"),
        ("Vuelo", "Vuelo asociado a una recogida en el aeropuerto", "Ajusta la hora de recogida de un viaje; genera alertas"),
        ("Turno", "Jornada de un conductor con un vehículo, con su inicio y su término", "Agrupa sus viajes, cobros y posiciones; se cuadra con un cierre de caja"),
        ("Cierre de caja", "Cuadratura de un turno: lo registrado frente a lo rendido", "Uno por turno; lo realiza un administrador"),
        ("Viaje", "Traslado desde la solicitud hasta el cierre", "Vincula pasajero, conductor y vehículo; concentra estados, pago, mensajes y calificación"),
    ], [2.6, 6.4, 7.6], font=8.2, first_col_bold=True)

    r.H3("Lista formal de entregables")
    r.table("entregables", "Entregables comprometidos", ["Código", "Entregable", "Fase", "Criterio de aceptación"], [
        ("E-01", "Informe de formulación", "1", "Aprobado por el académico guía"),
        ("E-02", "Product Backlog priorizado y estimado", "1", "Validado con el cliente (acta)"),
        ("E-03", "Modelos AS-IS y TO-BE", "1", "Revisados por el despachador"),
        ("E-04", "Documento de arquitectura", "2", "Consistente con el backlog"),
        ("E-05", "Modelo de datos y script de creación", "2", "3FN y validado con datos de prueba"),
        ("E-06", "Prototipos de interfaz", "2", "Validados con usuarios"),
        ("E-07", "Backend con API REST y canal WebSocket", "3", "HU de prioridad alta superan sus pruebas"),
        ("E-08", "Panel web administrativo", "3–4", "Criterios de las HU del panel"),
        ("E-09", "Portal del pasajero y de convenios", "3–4", "Criterios de las HU del portal"),
        ("E-10", "App del conductor (APK)", "3–4", "Criterios de HU-13 a HU-18 en dispositivo real"),
        ("E-11", "Plan y evidencia de pruebas UAT", "5", "Sin defectos críticos abiertos"),
        ("E-12", "Manual de usuario y capacitación", "5", "Sesión ejecutada y registrada"),
        ("E-13", "Sistema desplegado", "5", "Accesible con TLS vigente"),
    ], [1.4, 6.6, 1.2, 7.4], font=8)

    r.H2("Impacto de la solución")
    r.H3("Proceso de negocio afectado")
    r.P("El proceso afectado es la logística externa y las operaciones de la cadena de valor: la solicitud del pasajero se conecta con el despacho "
        "asistido y la ejecución en ruta, y el control administrativo se centraliza en una plataforma. Cambian las tres etapas del proceso "
        "(reserva, despacho y ejecución con cobro) y se agrega una actividad que hoy no existe: el monitoreo de vuelos.")
    r.H3("Registro de interesados")
    r.P("La {T:interesados} registra a los interesados y la {F:poder} los prioriza según poder e interés.")
    r.table("interesados", "Registro de interesados", ["Interesado", "Influencia", "Interés", "Expectativas", "Estrategia"], [
        ("Dueño / administrador", "Alta", "Alto", "Control de la operación, reportes exactos y rentabilidad", "Gestionar de cerca; demo en cada Sprint Review"),
        ("Despachador", "Media", "Alto", "Sistema rápido, mapa al día y asignación simple", "Mantener informado; pruebas de usabilidad"),
        ("Conductores", "Media", "Alto", "App estable, bajo consumo, avisos claros, poder rechazar y privacidad fuera del turno", "Grupo focal, aviso de privacidad y UAT en dispositivo real"),
        ("Pasajeros", "Baja", "Medio", "Saber cuándo llega el vehículo y contacto simple", "Monitorear con la calificación del servicio"),
        ("Supervisor de convenio", "Media", "Medio", "Reservar de forma simple y segura", "Mantener informado; validar el acceso con cuenta propia"),
        ("Product Owner", "Alta", "Alto", "Incrementos que aporten valor al cliente", "Aprueba incrementos y cambios de alcance"),
        ("Equipo de proyecto", "Alta", "Alto", "Alcance claro y requerimientos estables", "Eventos Scrum y control de cambios"),
        ("Académico guía", "Alta", "Alto", "Rigor metodológico y estándares de titulación", "Reportes de avance y revisiones"),
    ], [3.2, 1.7, 1.4, 5.2, 5.1], font=8)
    r.figure(F1 + "img-076.png", "poder", "Mapa de poder e interés de los interesados", width_cm=12.5)

    r.H3("Indicadores de gestión")
    r.P("Los indicadores miden la mejora del negocio, no el avance del desarrollo. Cada uno tiene fórmula, línea base, meta y frecuencia "
        "({T:kpi1}); las metas son coherentes entre sí (el 95,0 % de cumplimiento de KPI-01 es el complemento del 5,0 % de cancelaciones de "
        "KPI-08). La ficha SMART completa, con fuentes, responsables, semáforos y acciones, está en el Informe 2.")
    rows = [(k[0], k[1], k[4], k[8], k[9], k[11]) for k in sec3.KPI]
    r.table("kpi1", "Indicadores de gestión", ["ID", "Indicador", "Fórmula", "Línea base", "Meta", "Frecuencia"], rows, [1.4, 3.0, 5.6, 3.0, 1.8, 1.8], font=7.6)

    r.H3("Niveles de servicio")
    r.P("Los niveles de servicio comprometidos con el cliente se resumen en la {T:sla1}. La disponibilidad se fijó en 99,0 % y no en 99,5 % "
        "porque una sola instancia cloud no puede sostener 99,5 % (es el compromiso que el propio proveedor ofrece por instancia), y el RPO baja "
        "de 24 a 6 horas porque los respaldos se toman cada 6 horas.")
    r.table("sla1", "Niveles de servicio comprometidos", ["Dimensión", "Compromiso"], [
        ("Disponibilidad", "≥ 99,0 % mensual en régimen 24/7, sin contar el mantenimiento programado: en un mes de 30 días (720 h), como máximo 7 h 12 min de indisponibilidad no programada"),
        ("Latencia de geolocalización", "La posición de un vehículo aparece en el mapa en menos de 5 s (p95) desde que el teléfono la envía"),
        ("Tiempo de respuesta", "API p95 < 2 s con 50 usuarios concurrentes"),
        ("Recuperación ante desastres", "RTO de 2 h y RPO de 6 h para los servicios críticos (snapshot del disco y respaldo lógico cada 6 h, alternados)"),
        ("Soporte", "Canal de WhatsApp y correo; incidentes críticos atendidos en 1 h y resueltos o con contingencia en 4 h, 24/7 durante la marcha blanca; incidentes menores en 2 días hábiles"),
        ("Mantenimiento programado", "Domingo de madrugada (período de menor demanda), con aviso de 48 h"),
    ], [4.0, 12.6], font=8.2, first_col_bold=True)

    r.H2("Objetivos del proyecto")
    r.H3("Objetivo general")
    r.P("Desarrollar e implementar un producto mínimo viable SaaS, compuesto por una plataforma web y una aplicación móvil interconectadas, que "
        "optimice la reserva, el despacho, la geolocalización y el registro de cobros de una empresa de taxi turismo, con apoyo a la decisión "
        "basado en datos de la operación.")
    r.H3("Objetivos específicos")
    r.table("oe", "Objetivos específicos", ["ID", "Objetivo específico", "Resultado verificable"], [
        ("OE-01", "Diseñar la arquitectura y el modelo de datos relacional, preparado para varias empresas, asegurando integridad, seguridad, privacidad y escalabilidad",
         "Documento de arquitectura y modelo de datos (E-04, E-05)"),
        ("OE-02", "Desarrollar el panel web, el portal y el módulo de convenios con API REST, incluyendo la asignación asistida, el seguimiento de vuelos y el tablero de indicadores",
         "Panel y portal que cumplen sus HU (E-08, E-09)"),
        ("OE-03", "Construir la app híbrida del conductor con Capacitor, con geolocalización en segundo plano limitada al turno y comunicación por WebSocket",
         "APK que cumple HU-13 a HU-18 en dispositivo real (E-10)"),
        ("OE-04", "Validar la solución con pruebas de aceptación, de rendimiento y de seguridad, cumpliendo los niveles de servicio comprometidos",
         "Informe de UAT sin defectos críticos (E-11)"),
    ], [1.4, 9.4, 5.8], font=8.2)


# ======================================================================== VI
def metodologia(r):
    r.H1("Metodología de Trabajo")
    r.H2("Metodología de desarrollo")
    r.P("Se aplica **Scrum** (Schwaber y Sutherland, 2020) con sprints de dos semanas, seleccionado por su capacidad de adaptarse a "
        "requerimientos cambiantes mediante entregas incrementales validadas por el cliente (Pressman y Maxim, 2020). Se compararon Scrum, "
        "Kanban, XP y cascada con una matriz ponderada de cinco criterios, con notas de 1 a 5; Scrum obtuvo el mayor puntaje, 4,65 de 5 "
        "({T:m_met1}). Se complementa con prácticas de XP: integración continua y revisión de código por pull request.")
    r.table("m_met1", "Matriz ponderada para elegir la metodología", ["Criterio (peso)", "Scrum", "Kanban", "XP", "Cascada"], [
        ("Requerimientos que pueden cambiar (25 %)", "5", "4", "4", "1"),
        ("Participación del cliente (20 %)", "5", "3", "4", "2"),
        ("Equipo pequeño (20 %)", "4", "5", "4", "3"),
        ("Plazos con hitos académicos fijos (20 %)", "5", "3", "4", "4"),
        ("Gestión del riesgo técnico (15 %)", "4", "3", "5", "2"),
        ("**Puntaje ponderado**", "**4,65**", "**3,65**", "**4,15**", "**2,35**"),
    ], [6.0, 2.4, 2.4, 2.4, 2.4], font=8.2, source="Elaboración propia. Puntaje = suma de nota × peso.")
    r.P("Scrum queda primero porque es el único que combina una revisión con el cliente cada dos semanas con entregas fijas que calzan con las "
        "evaluaciones de la asignatura. XP obtiene el mejor puntaje en riesgo técnico por sus prácticas de ingeniería, que se adoptan dentro de "
        "Scrum; Kanban se descarta por no tener iteraciones con fecha, y cascada por su rigidez ante cambios.")
    r.P("Scrum requiere separar a quien prioriza y aprueba de quien construye. Por eso el rol de **Product Owner** lo asume **Juan Pérez**, que "
        "representa al cliente, y no un integrante del equipo de desarrollo ({T:roles1}).")
    r.table("roles1", "Aplicación de Scrum en el proyecto", ["Elemento", "Responsable / cadencia", "Responsabilidad / artefacto"], [
        ("Product Owner", "Juan Pérez (rol asumido para efectos de la metodología)", "Prioriza el backlog, define criterios de aceptación, aprueba incrementos y cambios de alcance"),
        ("Scrum Master", "Carlos Ortiz", "Facilita los eventos, remueve impedimentos y vela por la DoD"),
        ("Developers", "Renato González (frontend web y móvil) · Carlos Ortiz (backend, datos e infraestructura)", "Estiman, construyen y prueban; revisión cruzada de cada pull request"),
        ("Stakeholder", "Administrador de la flota (cliente)", "Participa en la Sprint Review y firma la UAT"),
        ("Sprint Planning", "Al inicio de cada sprint, 90 min", "Sprint Backlog con historias que cumplen la DoR"),
        ("Daily Scrum", "Diaria, asíncrona, 15 min", "Avance e impedimentos"),
        ("Sprint Review", "Al cierre de cada sprint, 60 min, con el cliente", "Incremento demostrado y retroalimentación registrada"),
        ("Retrospectiva", "Al cierre de cada sprint, 45 min", "Acuerdos de mejora para el sprint siguiente"),
        ("Refinamiento", "Semanal", "Historias del próximo sprint detalladas y estimadas"),
        ("Artefactos", "Product Backlog (Anexo 1), Sprint Backlog e incremento", "Tablero en GitHub Projects; DoR y DoD (6.1.1 y 6.1.2)"),
    ], [3.2, 6.0, 7.4], font=8)

    r.H3("Definition of Ready (DoR)")
    r.P("Una historia entra a un sprint solo si: está redactada como «Como [rol], quiero [acción], para [beneficio]»; tiene criterios de "
        "aceptación verificables; fue estimada con planning poker; no tiene dependencias bloqueantes; sus servicios externos (API, credenciales, "
        "permisos) están identificados; tiene diseño de interfaz si crea una pantalla; cabe en un sprint; y fue priorizada por el Product Owner.")
    r.H3("Definition of Done (DoD)")
    r.P("Un incremento está terminado cuando: el código está versionado y entra a la rama principal por pull request; la integración continua "
        "está en verde; se cumplen todos los criterios de aceptación; hay pruebas automáticas con cobertura ≥ 70 % en los módulos afectados; se "
        "probó manualmente contra el backend real, en dispositivo móvil cuando corresponde, con evidencia guardada en el repositorio; no hay "
        "vulnerabilidades OWASP detectables por análisis estático; no expone secretos ni datos personales; la documentación (API, modelo de "
        "datos, registro de cambios) está al día; no quedan defectos críticos o altos abiertos; y el Product Owner lo aprobó.")
    r.H3("Estimación de esfuerzo y planificación de sprints")
    r.P("Se estimó con planning poker sobre la escala de Fibonacci, con HU-17 (abrir la navegación externa) = 3 SP ≈ 5 h como referencia "
        "(≈ 1,7 h por punto). Con dos desarrolladores a 25 h semanales y un factor de foco de 75 %, la capacidad es de 75 h por sprint, unos "
        "**45 SP**. El backlog del producto mínimo viable suma **178 SP** en cuatro sprints ({T:plan_sprints}), con la semana 16 reservada para "
        "la UAT y el paso a producción.")
    from data_backlog import SPRINTS
    rows = []
    for s, (sem, obj) in SPRINTS.items():
        hs = [h for h in HU if h[6] == s]
        rows.append((s.replace("S", "Sprint "), sem, obj, ", ".join(h[0] for h in hs), str(sum(h[5] for h in hs))))
    rows.append(("**Total**", "8 a 15", "", f"{len(HU)} historias", f"**{sum(h[5] for h in HU)}**"))
    r.table("plan_sprints", "Planificación de los sprints", ["Sprint", "Semanas", "Objetivo", "Historias", "SP"], rows, [1.6, 1.6, 6.4, 5.6, 1.4], font=8)

    r.H2("Duración y cronograma")
    r.H3("Carta Gantt")
    r.P("El proyecto dura 16 semanas, desde el 10 de agosto de 2026, en cinco fases ({F:gantt1}): análisis y formulación (semanas 1 a 5), "
        "diseño y Sprint 0 (6 y 7), cuatro sprints de construcción (8 a 15) y UAT con paso a producción (16). Los hitos son H-1 formulación "
        "aprobada (semana 5), H-2 diseño y H-3 prueba de concepto del GPS en segundo plano (semana 7), H-4 incremento del Sprint 3 (semana 13), "
        "H-5 sistema desplegado (semana 15) y H-6 UAT firmada (semana 16). El avance real se controla en el Informe 2.")
    r.figure(F1 + "img-089.png", "gantt1", "Carta Gantt de línea base: fases, sprints y entregables (16 semanas)", width_cm=16.4)
    r.P("**Dependencias principales:** la formulación aprobada precede al diseño; la prueba de concepto del GPS (H-3) precede a las historias de la "
        "app; la verificación por WhatsApp precede al portal; la fila virtual depende del mapa en tiempo real; el despliegue depende de la fusión "
        "del último sprint; y la UAT depende de la capacitación.")
    r.H3("Estructura de Desglose del Trabajo (EDT)")
    r.figure("fig/edt.png", "edt", "Estructura de desglose del trabajo (EDT)", width_cm=16)
    r.P("Cada paquete de tercer nivel de la {F:edt} es asignable, estimable y verificable, y se vincula con los entregables de la {T:entregables}.")

    r.H2("Equipo de trabajo")
    r.P("El equipo de desarrollo lo forman dos integrantes, con autorización del académico guía, y el rol de Product Owner lo cumple Juan Pérez "
        "para efectos de la metodología. El rol de **líder de proyecto**, exigido por la asignatura, rota entre los integrantes: Renato González en "
        "la Unidad 1 (análisis y formulación) y Carlos Ortiz en la Unidad 2 (diseño y construcción). El líder se relaciona con el docente, controla "
        "el avance, asigna el trabajo, convoca las reuniones y reporta el cumplimiento de cada integrante ({T:equipo}).")
    r.table("equipo", "Equipo de trabajo y responsabilidades", ["Integrante", "Rol Scrum", "Área técnica", "Liderazgo del proyecto"], [
        ("Renato González", "Developer", "Frontend web (panel y portal) y aplicación móvil; usabilidad y pruebas de interfaz", "Líder en la Unidad 1"),
        ("Carlos Ortiz", "Scrum Master y Developer", "Backend, base de datos, integraciones e infraestructura cloud; pruebas de backend, carga y seguridad", "Líder en la Unidad 2"),
        ("Juan Pérez", "Product Owner", "Representa al cliente: prioriza, define criterios de aceptación y aprueba", "—"),
    ], [3.0, 3.2, 7.4, 3.0], font=8.2)
    r.P("**Sobre la matriz RACI.** La versión anterior incluía una matriz RACI en la que un mismo integrante aparecía como responsable (R) y "
        "aprobador (A) de varias tareas, lo que el académico guía observó como **conflicto de interés**. Se elimina: en Scrum las "
        "responsabilidades las definen los roles, y la separación que la RACI buscaba asegurar se obtiene con la estructura anterior. Quien "
        "construye una historia no la aprueba: el código lo revisa el otro integrante en el pull request, el incremento lo aprueba el Product "
        "Owner y la aceptación final la firma el cliente en la UAT.")

    r.H2("Plan de recursos")
    r.P("El equipo dispone de su capital humano, dos estaciones de trabajo y un teléfono Android para pruebas de campo. Para la puesta en marcha se "
        "requieren la instancia AWS, las API externas (WhatsApp vía Twilio, datos de vuelos y mapas), la licencia de Google Play y el dominio con su "
        "certificado. El presupuesto del desarrollo, valorizado a precios del mercado chileno, se resume en la {T:presup}; el costo mensual de "
        "operación y el modelo comercial se calculan en la factibilidad económica del Informe 2.")
    r.table("presup", "Presupuesto del desarrollo (16 semanas)", ["Categoría", "Detalle", "Costo (CLP)"], [
        ("Personal", "Dos desarrolladores a $1.500.000 mensuales cada uno, por cuatro meses", "$12.000.000"),
        ("Equipamiento", "Arriendo y depreciación de dos estaciones de trabajo y un teléfono de prueba", "$600.000"),
        ("Infraestructura cloud", "Instancia AWS con PostgreSQL/PostGIS y Redis para pruebas y producción inicial", "$400.000"),
        ("Licencias y API", "Mapas, WhatsApp vía Twilio, datos de vuelos y licencia de Google Play", "$150.000"),
        ("Bienes y servicios", "Dominio .cl y certificado TLS", "$30.000"),
        ("Imprevistos (10 %)", "Tipo de cambio, consumo de API sobre lo proyectado y requerimientos emergentes", "$1.318.000"),
        ("**Total**", "", "**$14.498.000**"),
    ], [3.6, 10.0, 3.0], font=8.5)
    r.P("Este presupuesto se valorizó antes de elegir el proveedor cloud y de conocer las cuotas de prueba de cada servicio. En el Informe 2, con "
        "AWS ya definido, bajan la infraestructura del proyecto (a $100.000), las licencias y API (a $60.000), el dominio (a $10.000, con "
        "certificado TLS gratuito) y los imprevistos (a $1.277.000): la inversión valorizada queda en **$14.047.000**, $451.000 menos, sin "
        "cambios en el personal ni en el equipamiento.")

    r.H2("Matriz de riesgos")
    sec0.riesgos(r, heading=False, estado=False)


# ======================================================================== VII
def arquitectura(r):
    r.H1("Definición de Arquitectura TI")
    r.H2("Arquitectura AS-IS y TO-BE")
    r.P("En el AS-IS ({F:apps_asis}) no hay sistemas: el despachador integra a mano WhatsApp, la planilla y el cuaderno. En el TO-BE todas las "
        "interfaces consumen una sola API, con una base de datos única como fuente de verdad, comunicación en tiempo real con la flota e "
        "integraciones con servicios externos detrás de adaptadores. La {F:arq1} muestra la arquitectura propuesta.")
    r.H2("Arquitectura general en capas")
    r.figure("fig/arquitectura.png", "arq1", "Arquitectura de la solución por capas", width_cm=16.6)
    r.P("**Presentación:** panel web y portal (React + Vite) y app del conductor (React + Capacitor). **Servicios:** API REST (Django REST "
        "Framework) y WebSocket (Django Channels) detrás de Nginx con TLS. **Lógica de negocio:** un monolito modular por dominio (reservas, "
        "despacho, flota, convenios, vuelos, cobros, mensajería, auditoría) con tareas en segundo plano (Celery). **Persistencia:** PostgreSQL 16 "
        "con PostGIS y Redis como canal y caché efímera. **Infraestructura:** una instancia AWS EC2 con contenedores Docker, respaldos en S3 y "
        "monitoreo.")
    r.H2("Diagrama de componentes")
    r.figure("fig/uml_comp.png", "comp1", "Diagrama de componentes (UML 2.5)", width_cm=16.4)
    r.P("Cada componente lleva el estereotipo «component»; las interfaces proporcionadas se dibujan como círculo y las requeridas como "
        "semicírculo. Las rutas de la API que expone cada componente (por ejemplo /api/viajes, /api/convenios, /ws/flota) y su detalle de "
        "responsabilidades se especifican en el Informe 2.")
    r.H2("Diagrama de despliegue e infraestructura")
    r.P("Se define **un solo proveedor, Amazon Web Services**, en la región us-east-1 (Virginia del Norte), elegido por costo y experiencia del "
        "equipo, con tarifas por hora publicadas (Amazon Web Services, 2026a) y un acuerdo de nivel de servicio de EC2 que respalda la meta de "
        "disponibilidad (Amazon Web Services, 2026b); la latencia desde Santiago (≈ 130 ms) es irrelevante frente a la meta de 5 s del GPS. Los recursos son los mismos en todos los "
        "documentos del proyecto ({T:recursos}).")
    r.figure("fig/infraestructura.png", "infra1", "Infraestructura de despliegue en AWS", width_cm=16.6)
    r.table("recursos", "Recursos de infraestructura", ["Recurso", "Configuración", "Uso"], [
        ("EC2 t4g.small", "2 vCPU ARM (Graviton2), 2 GiB, Ubuntu 24.04", "Contenedores de Nginx, Gunicorn (API), Daphne (WebSocket), Celery, PostgreSQL 16 + PostGIS y Redis"),
        ("EBS gp3", "30 GB cifrado; snapshots cada 6 h con Data Lifecycle Manager", "Disco del servidor y recuperación rápida"),
        ("S3", "Bucket privado, cifrado y versionado", "Respaldos lógicos (pg_dump) cada 6 h, alternados con los snapshots"),
        ("Route 53 y Certbot", "Dominio .cl y certificados TLS", "Resolución de nombres y HTTPS"),
        ("CloudWatch, Sentry y UptimeRobot", "Métricas, errores y disponibilidad", "Monitoreo y alertas"),
        ("SSM Parameter Store", "Parámetros cifrados por ambiente", "Secretos fuera del código"),
    ], [3.6, 5.6, 7.4], font=8)
    r.P("PostgreSQL se ejecuta en un contenedor y no como servicio gestionado (RDS) porque cuesta menos y los respaldos cada 6 h cubren el RPO "
        "comprometido; la contrapartida es que el respaldo queda a cargo del equipo. Una sola instancia es un punto único de falla aceptado y "
        "explica la disponibilidad de 99,0 %.")
    r.H2("Modelo de datos")
    r.figure("fig/modelo_datos.png", "er1", "Modelo lógico de datos (23 entidades)", width_cm=16.6)
    r.P("El modelo lógico en tercera forma normal concreta el modelo conceptual de la sección 5.1.6. EMPRESA es la raíz y su identificador se "
        "propaga a las entidades de negocio (RN-13); HISTORIAL_ESTADO registra cada transición del viaje; TURNO y CIERRE_CAJA permiten medir la "
        "cuadratura y los indicadores por turno; POSICION_GPS guarda la ubicación ligada al turno y se purga a los 30 días; y AUDITORIA registra "
        "las acciones sensibles en modo solo inserción. El diccionario de datos completo está en el Informe 2.")

    r.H2("Diseño de seguridad")
    r.H3("Autenticación")
    r.P("Inicio de sesión único para los cinco roles; tokens JWT de acceso de 15 minutos y de renovación de 12 horas, con rotación y lista de "
        "revocación. En el panel la renovación viaja en una cookie httpOnly y en la app se guarda en el almacén cifrado de Android. Contraseñas "
        "con PBKDF2-SHA256, bloqueo temporal tras cinco intentos fallidos y contraseña temporal con cambio obligatorio en el primer ingreso.")
    r.H3("Autorización")
    r.P("Control de acceso por rol (administrador, despachador, conductor, pasajero y supervisor de convenio) y por empresa: cada consulta filtra "
        "por la empresa del usuario (RN-13). El pasajero solo ve sus propios viajes y el conductor solo los que tiene asignados.")
    r.H3("Cifrado y protección de datos")
    r.P("TLS 1.2 o superior con HSTS en todo el tráfico; disco y respaldos cifrados; secretos en SSM, nunca en el repositorio. Los datos personales "
        "(nombres, teléfonos, direcciones y ubicaciones) se marcan como sensibles y su acceso queda restringido por rol. La transferencia "
        "internacional (servidores en Estados Unidos) se cubre con el acuerdo de tratamiento de datos del proveedor y se informa en el aviso de "
        "privacidad.")
    r.H3("Respaldos y continuidad")
    r.P("Snapshot del disco y respaldo lógico de la base de datos cada 6 horas, alternados; retención de 7 días para los de 6 horas y de 30 días "
        "para el diario. RTO de 2 horas y RPO de 6 horas, con un modo manual de contingencia y un procedimiento para ingresar después los viajes "
        "anotados durante una caída.")
    r.H3("Privacidad del seguimiento GPS de los conductores")
    r.P("Traduce a diseño lo expuesto en la sección 2.2.3 ({T:gps_priv}).")
    r.table("gps_priv", "Medidas de privacidad de la geolocalización", ["Principio", "Medida en FlotaÁgil", "Regla o requisito"], [
        ("Finalidad", "La ubicación se usa solo para despachar, para la seguridad del pasajero, para la fila del aeropuerto y para indicadores agregados; no genera sanciones automáticas ni perfiles del conductor", "Aviso de privacidad"),
        ("Proporcionalidad", "La app envía la posición solo con el turno iniciado, cada 30 s; al terminar el turno se detiene; el conductor ve cuándo se está registrando", "RN-18, RNF-09"),
        ("Información y consentimiento", "Antes del primer turno el conductor lee y acepta qué se registra, cuándo, quién lo ve y por cuánto tiempo; la aceptación queda con su fecha", "RN-18, CONDUCTOR.consentimiento_gps_en"),
        ("Base laboral", "Si el conductor es dependiente, la medida se incorpora al Reglamento Interno del cliente con una cláusula tipo que el equipo entrega", "Código del Trabajo, art. 154; DT Ord. N° 148"),
        ("Acceso restringido", "Solo el administrador y el despachador de la empresa ven la ubicación en vivo; el historial solo para resolver incidentes", "RN-13, auditoría"),
        ("Retención mínima", "Las posiciones se eliminan a los 30 días con una tarea programada diaria", "RN-15"),
        ("Derechos del titular", "Acceso, rectificación, supresión y oposición se canalizan por la empresa; la cuenta del pasajero puede eliminarse desde el portal", "Ley 21.719"),
        ("Seguridad", "Transmisión cifrada, base de datos cifrada en reposo y registro de quién consulta datos sensibles", "RNF-04, RNF-10"),
    ], [3.0, 9.6, 4.0], font=8)

    r.H2("Matriz de trazabilidad")
    r.P("La matriz vincula cada historia con su objetivo, regla, proceso BPMN, caso de uso, componente, entidades y casos de prueba "
        "({T:traz}). Así, cada objetivo específico puede seguirse hasta el código y la prueba que lo demuestran. Dos columnas remiten al diseño "
        "detallado del Informe 2: los casos de prueba (CP-xx), documentados según ISO/IEC/IEEE 29119-3 (International Organization for "
        "Standardization, 2021) en su plan de pruebas, y los subprocesos P1.1, P2.1 y P3.2, que detallan una tarea de los procesos P1, P2 y P3 "
        "de la sección 5.1.")
    _run_annex_segment(r, 'AH(r, "Anexo I. Matriz de trazabilidad")', "# ---------------- H", skip_head=True, landscape=True)


# ======================================================================== VIII y IX
def empresarial(r):
    r.H1("Reconocimiento de Arquitectura Empresarial")
    r.H2("Identificación del tipo de organización y su estructura")
    r.P("La organización es una empresa privada de transporte turístico de pasajeros con estructura jerárquica plana: **gerencia y "
        "administración** (decisiones estratégicas, control financiero y convenios), **operaciones** (recepción, agendamiento y asignación de "
        "servicios) y **conductores** (ejecución del traslado y registro del cobro). El proceso primario abordado es la logística externa y las "
        "operaciones de la cadena de valor.")
    r.P("La intervención modifica las cuatro capas de la arquitectura empresarial ({T:capas_ae}).")
    r.table("capas_ae", "Efecto de la solución en las capas de la arquitectura empresarial", ["Capa", "Situación actual", "Situación propuesta"], [
        ("Negocio", "Proceso informal, sin estados ni responsables definidos", "Proceso formalizado en BPMN con estados del viaje, reglas de negocio y decisiones apoyadas en datos"),
        ("Aplicación", "WhatsApp, planillas y cuaderno sin integración", "Primer sistema de información de la organización: panel, portal y app sobre una API"),
        ("Datos", "Información duplicada y dispersa", "Fuente única de verdad con historial, auditoría y retención definida"),
        ("Tecnología", "Dos PC y teléfonos personales", "Infraestructura cloud sin inversión local, con respaldos y monitoreo"),
    ], [2.6, 6.0, 8.0], font=8.2, first_col_bold=True)


def conclusiones(r):
    r.H1("Conclusiones")
    r.P("La formulación parte de un problema medido y no supuesto: un 12,1 % de reservas perdidas, 8 min 40 s por asignación, 35 % de tiempo "
        "muerto y $34.500 diarios de descuadre, respaldados por entrevistas, un grupo focal, observación directa y tres meses de registros. El "
        "análisis de causas mostró que el origen no está en el esfuerzo de las personas, sino en tres carencias tecnológicas (sin fuente única "
        "de datos, sin trazabilidad de la flota y sin registro del cobro) y en una de decisión: hoy se asigna por memoria.")
    r.P("La retroalimentación de la evaluación formativa llevó la propuesta un paso más allá. Digitalizar resuelve las tres primeras carencias, "
        "pero el valor diferenciador está en la cuarta: un sistema que anticipa los atrasos de vuelos, recomienda al conductor más adecuado, "
        "alerta las desviaciones y mide el negocio, manteniendo la decisión en manos del despachador. Esas capacidades, ausentes en las soluciones "
        "analizadas para una PYME de taxi turismo, son las que justifican el proyecto frente a una planilla mejor organizada.")
    r.P("El proyecto también reconoce que opera en un rubro regulado y con datos sensibles. El análisis normativo precisa qué exige la "
        "autoridad del transporte y qué debe registrar el sistema, y descarta que FlotaÁgil sea una empresa de aplicación de transporte. La "
        "geolocalización de los conductores se diseñó para ser una herramienta de operación y no de vigilancia: solo en turno, con "
        "consentimiento, con acceso restringido y con eliminación a los 30 días.")
    r.P("La metodología Scrum, con roles separados entre quien construye y quien aprueba, cuatro sprints de 45 SP y una arquitectura cloud "
        "simple pero completa, hace el proyecto factible en 16 semanas con dos desarrolladores. Los modelos se corrigieron para respetar la "
        "notación BPMN 2.0 y UML 2.5, y la infraestructura quedó definida en un solo proveedor con los mismos recursos que usa el diseño "
        "detallado del Informe 2, lo que asegura la coherencia entre ambos documentos.")


def referencias(r):
    extra = [
        "Biblioteca del Congreso Nacional de Chile. (1986). *Ley N° 18.490 que establece el seguro obligatorio de accidentes personales causados por circulación de vehículos motorizados*. https://www.bcn.cl/leychile/navegar?idNorma=29893",
        "Biblioteca del Congreso Nacional de Chile. (1988). *Ley N° 18.696 que modifica el artículo 6° de la Ley N° 18.502, autoriza importación de vehículos que señala y establece normas sobre transporte de pasajeros*. https://www.bcn.cl/leychile/navegar?idLey=18696",
        "Biblioteca del Congreso Nacional de Chile. (2009). *Decreto con Fuerza de Ley N° 1 que fija el texto refundido, coordinado y sistematizado de la Ley de Tránsito*. https://www.bcn.cl/leychile/navegar?idNorma=1007469",
    ]
    keep = ("Griffith", "Mell", "Project Management", "Bass", "Biblioteca", "Dirección del Trabajo", "Fette", "International Organization",
            "Obe", "Object Management", "OWASP", "Pressman", "Richards", "Schwaber", "Sommerville", "Amazon Web Services. (2026a)", "Amazon Web Services. (2026b)")
    old = sec4.REFS
    sec4.REFS = [x for x in old if x.startswith(keep) and "17.336" not in x] + extra
    sec4.referencias(r)
    sec4.REFS = old


# ======================================================================== XI
def _run_annex_segment(r, start, end, rename=None, skip_head=False, landscape=False):
    src = open(os.path.join(os.path.dirname(__file__), "annex.py")).read()
    i = src.index(start)
    j = src.index(end, i)
    seg = src[i:j]
    if skip_head:
        seg = seg.split("\n", 2)[2]  # quita el AH y el párrafo de apertura (primera línea)
        seg = seg[seg.index("    tr = {"):] if "    tr = {" in seg else seg
    if rename:
        for a, b in rename:
            seg = seg.replace(a, b)
    lines = [l[4:] if l.startswith("    ") else l for l in seg.split("\n")]
    code = "\n".join(lines)
    if landscape:
        r.landscape_on()
    ns = dict(r=r, AH=annex.AH, HU=HU, NUEVAS=NUEVAS, RETIRADAS=RETIRADAS, RESP=RESP)
    exec(compile(code, "annex_seg", "exec"), ns)
    if landscape:
        r.landscape_off()


def anexos(r):
    r.H1("Anexos")
    # 1 backlog
    r.landscape_on()
    annex.AH(r, "Anexo 1. Product Backlog")
    r.P("Historias del producto mínimo viable con sus criterios de aceptación, prioridad, estimación (planning poker sobre Fibonacci, con HU-17 = "
        "3 SP como referencia) y sprint. Las historias conservan el código del backlog validado con el cliente el 28/08/2026; las retiradas y las "
        "incorporadas por solicitudes de cambio se listan al final.")
    rows = [(h[0], h[1], h[2], h[3], h[4], str(h[5]), h[6].replace("S", "Sprint ") + "\n" + RESP.get(h[0], "Carlos")) for h in HU]
    rows += [(h[0], h[1], h[2], h[3], h[4], str(h[5]), h[6].replace("S", "Sprint ") + "\n" + ("Renato" if h[0] == "HU-31" else "Carlos")) for h in NUEVAS]
    r.table("backlog", "Product Backlog", ["ID", "Épica", "Historia de usuario", "Criterios de aceptación", "Prior.", "SP", "Sprint y resp."], rows,
            [1.3, 2.2, 6.6, 8.4, 1.3, 0.9, 1.9], font=7.4)
    rows = [(x[0], x[2], x[4], x[5]) for x in HU_CC]
    r.table("backlog_cc1", "Historias incorporadas por solicitudes de cambio posteriores (CC-16 a CC-18)", ["ID", "Historia de usuario", "SP", "Origen"], rows,
            [1.4, 16.4, 1.2, 3.6], font=7.4)
    rows = [(x[0], x[1], x[2], str(x[3])) for x in RETIRADAS]
    r.table("retiradas", "Historias retiradas", ["ID", "Historia original", "Motivo", "SP liberados"], rows, [1.6, 6.0, 12.6, 2.4], font=8)
    r.landscape_off()
    # 2 y 3 instrumentos y evidencias
    _run_annex_segment(r, 'AH(r, "Anexo B.', 'AH(r, "Anexo D.', rename=[
        ('"Anexo B. Instrumentos de levantamiento"', '"Anexo 2. Instrumentos de levantamiento"'),
        ('"Anexo C. Evidencias del levantamiento y entrevista de seguimiento"', '"Anexo 3. Evidencias del levantamiento"'),
        ("**B.", "**2."), ("**C.", "**3."), ("(C.3)", "(3.3)"), ("pauta del Anexo B", "pauta del Anexo 2")])
    # 4 glosario
    _run_annex_segment(r, 'AH(r, "Anexo K.', 'AH(r, "Anexo L.', rename=[('"Anexo K. Glosario"', '"Anexo 4. Glosario de términos"')])
    # 5 máquina de estados
    _run_annex_segment(r, 'AH(r, "Anexo H.', "# ---------------- G", rename=[
        ('"Anexo H. Máquina de estados del viaje"', '"Anexo 5. Máquina de estados del viaje"'),
        ("Actualiza la máquina de estados de la formulación. Se agregan", "Estados del viaje y sus transiciones. Respecto de la primera versión se agregan")])


def remap1(t):
    t = re.sub(r"secci[oó]n 2\.3\b", "sección 3.1", t)
    t = re.sub(r"\bAnexo A\b", "Anexo 1", t)
    t = re.sub(r"\bAnexo B\b", "Anexo 2", t)
    t = re.sub(r"\bAnexo C\b", "Anexo 3", t)
    t = re.sub(r"\bel Anexo I\b", "la sección 7.7", t)
    t = re.sub(r"\bAnexo I\b", "sección 7.7", t)
    t = t.replace("P1 (retorno, 8.2)", "P1 (retorno al servicio)")
    t = t.replace("observaciones de la EF2", "observaciones del académico guía sobre el diseño").replace("tras la EF2", "tras la revisión del diseño")
    t = t.replace("originadas en la EF2", "originadas en la revisión del diseño")
    return t


def build(toc_entries, out):
    r = Report("template.docx", COVER)
    r.remap = remap1
    r.toc(toc_entries)
    intro(r)
    problema(r)
    levantamiento(r)
    marco(r)
    objetivos(r)
    metodologia(r)
    arquitectura(r)
    empresarial(r)
    conclusiones(r)
    referencias(r)
    anexos(r)
    r.save(out)
    patch_docx(out, {"word/document.xml": [("DESARROLLO E IMPLEMENTACIÓN", "FORMULACIÓN")],
                     "word/footer2.xml": [(">Desarrollo<", ">Formulación<")]})
    return r


def patch_docx(path, repl):
    import zipfile, shutil
    tmp = path + ".tmp"
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            data = zin.read(it.filename)
            if it.filename in repl:
                txt = data.decode("utf-8")
                for a, b in repl[it.filename]:
                    txt = txt.replace(a, b)
                data = txt.encode("utf-8")
            zout.writestr(it, data)
    shutil.move(tmp, path)


def run(name):
    os.makedirs("out", exist_ok=True)
    r = build([(1, "x", 0)], "out/_e1_pass0.docx")
    heads = [(l, t) for l, t in r.headings if l <= 2]
    build([(l, t, 99) for l, t in heads], "out/_e1_pass1.docx")
    pages = page_texts(pdf("out/_e1_pass1.docx"))
    toc_pages = [i for i, t in enumerate(pages) if t.count("....") > 8]
    cur = (max(toc_pages) + 1) if toc_pages else 1
    res = []
    for l, t in heads:
        key = norm(t)[:45]
        found = next((i for i in range(cur, len(pages)) if key in pages[i]), None)
        if found is None:
            print("NO ENCONTRADO:", t); found = cur
        cur = found
        res.append((l, t, found + 1))
    build(res, f"out/{name}.docx")
    import revisar
    errores = revisar.main([f"out/{name}.docx"])
    if errores and "--forzar" not in sys.argv:
        print("\nRevisión con errores: no se genera el PDF. Corrige o usa --forzar.")
        sys.exit(1)
    p = pdf(f"out/{name}.docx")
    pages2 = page_texts(p)
    bad = [(t, pg) for l, t, pg in res if norm(t)[:45] not in pages2[pg - 1]]
    print("páginas:", len(pages2), "desajustes:", bad[:10])
    return p


if __name__ == "__main__":
    run("Informe1_FlotaAgil_corregido")
