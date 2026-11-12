from datos import DC_MAX
from data_cu import CU
from datamodel import E

F = "fig/"


def bpmn_desc(r, key, title, d):
    pairs = [(k, v) for k, v in d]
    r.kv_table(key, title, pairs, widths=(3.4, 13.2), font=8)


def arquitectura(r):
    r.H1("Detalle de la Arquitectura a implementar")
    r.H2("Diagrama BPMN")
    r.P("Se modelaron con BPMN 2.0 los tres procesos principales del negocio que el diagnóstico identificó como origen del problema: "
        "**P1 Recepción y confirmación de reservas** (causa raíz: ausencia de una fuente única de datos; síntoma: 12,1 % de reservas perdidas y 7,4 % "
        "de errores de transcripción), **P2 Despacho y asignación de viajes** (causa raíz: falta de trazabilidad de la flota; síntoma: 8 min 40 s por "
        "asignación) y **P3 Ejecución del traslado y cobro** (causa raíz: cobro sin registro digital; síntoma: descuadre de $34.500 diarios). Son "
        "procesos de negocio, no pantallas: cada uno cruza varios participantes y termina en un resultado de valor para el cliente. Cada proceso tiene "
        "subprocesos desarrollados: P1.1; P2.1 y P2.2; P3.1 y P3.2.")
    r.P("**Convenciones:** los pools nombran el proceso o participante; los carriles, el rol responsable. Las tareas usan verbos en infinitivo y "
        "marcadores de tipo: engranaje (servicio, automatizada por FlotaÁgil), persona (de usuario, apoyada por una pantalla), sobre negro (envío "
        "de mensaje) y mano (manual, fuera del sistema). Las líneas continuas son flujos de secuencia dentro de un pool; las discontinuas con círculo "
        "y flecha blanca, flujos de mensaje entre participantes. Ningún flujo sale de un evento de término. Todos los modelos son **TO-BE**, "
        "salvo la Figura {F:asis}, que corrige el AS-IS de la formulación según las observaciones del docente. A la fecha de corte, P1, P2 y P3 y sus "
        "subprocesos P1.1, P2.1, P2.2 y P3.1 están implementados; de P3.2 está construida la liquidación del turno y falta el registro del "
        "cierre de caja, que llega con HU-31 (CC-12).")
    r.figure(F + "bpmn_asis.png", "asis", "Proceso actual de reserva, despacho y cobro (AS-IS, corregido)", width_cm=16.4)
    r.P("El AS-IS muestra el ciclo de búsqueda secuencial del conductor (bucle «llamar al siguiente») y el cobro anotado al cierre del turno, "
        "desacoplado del momento del pago; son los dos cuellos de botella que los procesos TO-BE eliminan.")

    # ---------- P1
    r.landscape_on()
    r.H3("P1 · Recepción y confirmación de reservas")
    r.figure(F + "bpmn_p1.png", "p1", "BPMN del proceso P1 Recepción y confirmación de reservas (TO-BE)", width_cm=20.0)
    r.landscape_off()
    bpmn_desc(r, "d_p1", "Descripción del proceso P1", [
        ("Objetivo", "Registrar toda solicitud en una fuente única, hecha por un solicitante con cuenta habilitada, sin transcripción manual."),
        ("Participantes", "Pasajero o empresa cliente con convenio (pool externo); Plataforma FlotaÁgil y Despachador (carriles)."),
        ("Inicio", "Dos canales: ingreso al portal con la cuenta del pasajero o del convenio (evento de mensaje) y llamada o WhatsApp recibido por el despachador."),
        ("Actividades", "¿Cuenta habilitada? → si no, Crear y habilitar la cuenta (P1.1) → ¿Habilitada?; Recibir pedido y validar datos, capacidad y "
                        "vuelo; Ingresar reserva en el panel; Registrar estado SOLICITADO y notificar."),
        ("Reglas", "RN-06 (teléfono verificado una vez, al activar la cuenta), RN-07 (convenio aprobado sin verificación), RN-08 (convenio desactivado sin acceso), RN-13."),
        ("Excepciones", "Cuenta sin activar o convenio rechazado en P1.1; pedido con más pasajeros que la capacidad de la flota (DC-43); bloqueo del ingreso tras 5 intentos."),
        ("Entradas / salidas", "Entrada: datos del viaje (tipo, origen, destino, hora, pasajeros, maletas y vuelo si aplica). Salida: reserva en SOLICITADO con su número y aviso al pasajero."),
        ("Mejora", "Elimina la transcripción (7,4 % de errores) y la pérdida de reservas anotadas en distintos medios; cada reserva queda en el historial de su cuenta y el vuelo queda registrado para P2.2."),
        ("Requerimientos", "HU-03, HU-19, HU-25, HU-26, HU-33, HU-39, HU-40, HU-42 · CU-01, CU-12."),
    ])
    r.figure(F + "bpmn_p1_1.png", "p1_1", "Subproceso P1.1 Crear y habilitar la cuenta", width_cm=16.0)
    r.P("P1.1 se ejecuta una sola vez por solicitante, no en cada reserva (CC-16 y CC-18). Una compuerta exclusiva separa los dos tipos de "
        "cuenta. La del **pasajero** usa una compuerta basada en eventos: si responde «CONFIRMAR CUENTA» por WhatsApp dentro de 15 minutos, el "
        "teléfono queda verificado y la cuenta activa; si vence el plazo, la cuenta queda sin activar y el mensaje se puede reenviar o corregir el "
        "número (RN-06). La de la **empresa cliente** queda EN_REVISION hasta que el administrador la aprueba o la rechaza con motivo, y el "
        "resultado se avisa por correo (HU-34). Requerimientos: HU-20, HU-34, HU-35, HU-38, HU-41 · CU-06, CU-13.")

    # ---------- P2
    r.landscape_on()
    r.H3("P2 · Despacho y asignación de viajes")
    r.figure(F + "bpmn_p2.png", "p2", "BPMN del proceso P2 Despacho y asignación de viajes (TO-BE)", width_cm=20.5)
    r.landscape_off()
    bpmn_desc(r, "d_p2", "Descripción del proceso P2", [
        ("Objetivo", "Asignar cada reserva al conductor más apto en menos de 3 minutos, manteniendo la decisión en el despachador."),
        ("Participantes", "Plataforma FlotaÁgil, Despachador y Conductor (app) en carriles; Pasajero como pool externo."),
        ("Inicio", "Reserva en SOLICITADO; un evento temporizador abre la ventana de despacho (inmediata o antes de la hora de recogida, que P2.2 puede ajustar)."),
        ("Actividades", "¿Recogida en aeropuerto? → Proponer primer conductor de la fila (P2.1) o Calcular sugerencias por distancia y turno → "
                        "Confirmar conductor → Enviar asignación → Aceptar o rechazar (temporizador de borde de 60 s) → Notificar conductor asignado."),
        ("Reglas", "RN-01, RN-02, RN-03, RN-04, RN-16; el bucle «Devolver reserva a SOLICITADO» reinicia la sugerencia."),
        ("Excepciones", "Rechazo o 60 s sin respuesta; sin conductores disponibles (la reserva permanece en SOLICITADO y se alerta)."),
        ("Entradas / salidas", "Entrada: reserva SOLICITADO, posiciones y fila. Salida: viaje ACEPTADO y pasajero informado con datos del conductor y vehículo."),
        ("Mejora", "Sustituye el contacto secuencial por radio o teléfono (5 a 10 llamadas por asignación en hora punta) por una sugerencia ordenada y una respuesta explícita."),
        ("Requerimientos", "HU-02, HU-04, HU-14, HU-15, HU-29 · CU-02, CU-03, CU-10, CU-16."),
    ])
    r.figure(F + "bpmn_p2_1.png", "p2_1", "Subproceso P2.1 Gestionar fila virtual del aeropuerto", width_cm=15.5)
    r.P("P2.1 se ejecuta con cada posición o cambio de estado del conductor. Una compuerta exclusiva clasifica la situación: ingreso a la geocerca "
        "estando Disponible (se agrega al final, FIFO), salida por más de 10 minutos, paso a No Disponible o asignación (se retira y se reordena), o "
        "sin cambio (termina). El orden de la fila es el que usa P2 para las recogidas en el aeropuerto.")
    r.figure(F + "bpmn_p2_2.png", "p2_2", "Subproceso P2.2 Monitorear vuelo y ajustar recogida", width_cm=16.0)
    r.P("P2.2 inicia tres horas antes de la hora programada del vuelo. Si la ETA cambia 15 minutos o más, o el vuelo se cancela o desvía, recalcula la "
        "recogida (RN-17) y alerta al despachador, quien valida el ajuste: el sistema propone y la persona decide (RN-02). El bucle se repite con un "
        "temporizador intermedio hasta el aterrizaje o la cancelación. La consulta a la API es un intercambio de mensajes con un participante externo.")

    # ---------- P3
    r.landscape_on()
    r.H3("P3 · Ejecución del traslado y cobro")
    r.figure(F + "bpmn_p3.png", "p3", "BPMN del proceso P3 Ejecución del traslado y cobro (TO-BE)", width_cm=20.5)
    r.landscape_off()
    bpmn_desc(r, "d_p3", "Descripción del proceso P3", [
        ("Objetivo", "Ejecutar el traslado con el pasajero informado en cada etapa y el cobro registrado en el momento en que ocurre."),
        ("Participantes", "Plataforma FlotaÁgil, Conductor (app) y Despachador; Pasajero como pool externo."),
        ("Inicio", "Viaje ACEPTADO (salida de P2)."),
        ("Actividades", "Iniciar trayecto → Notificar «en camino» → evento condicional «vehículo a < 150 m» → Marcar EN_ZONA y avisar «tu vehículo te espera» "
                        "→ Recoger pasajero y marcar A_BORDO → Realizar el traslado (manual) → Registrar cobro y cerrar viaje (P3.1) → Solicitar calificación."),
        ("Reglas", "RN-10 (sin pago no se finaliza), RN-14 (calificación opcional), RN-11 (cierre forzado con motivo)."),
        ("Excepciones", "15 minutos en EN_ZONA sin pasajero (temporizador de borde) → Gestionar no presentación → Viaje CANCELADO."),
        ("Entradas / salidas", "Entrada: viaje aceptado. Salida: viaje FINALIZADO con PAGO_VIAJE, conductor DISPONIBLE y encuesta enviada."),
        ("Mejora", "El pasajero deja de llamar para preguntar por su móvil y cada cobro queda registrado en el instante del pago."),
        ("Requerimientos", "HU-16, HU-17, HU-21, HU-24 · CU-11, CU-14."),
    ])
    r.figure(F + "bpmn_p3_1.png", "p3_1", "Subproceso P3.1 Registrar cobro y cerrar viaje", width_cm=14.5)
    r.P("En P3.1 el conductor selecciona el método y el monto; la plataforma valida RN-10 y, si los datos no son válidos, el flujo vuelve a la "
        "compuerta de unión inicial para pedirlos de nuevo. Con datos válidos registra PAGO_VIAJE, cambia el viaje a FINALIZADO y libera al conductor.")
    r.figure(F + "bpmn_p3_2.png", "p3_2", "Subproceso P3.2 Cuadrar caja al cierre de turno", width_cm=14.5)
    r.P("P3.2 reemplaza el cuaderno de caja. Al terminar un turno (entidad TURNO), el administrador solicita su cierre; la plataforma calcula el "
        "efectivo registrado en los viajes de ese turno; el administrador cuenta el efectivo que entrega el conductor (tarea manual) y, si hay "
        "diferencia, la registra con una observación, que queda en auditoría; al confirmar, la plataforma guarda el CIERRE_CAJA con el monto "
        "registrado, el monto rendido, la diferencia, el responsable y la fecha. Es la fuente del KPI-05. El subproceso se corrigió tras la EF2 "
        "(CC-12): antes terminaba en «cerrar turno» sin dejar un registro de lo rendido. La liquidación por conductor y método ya está "
        "construida (HU-06, HU-18); el registro del cierre está construido con HU-31 (DC-32).")

    # ---------- CU
    r.H2("Diagramas de caso de uso")
    r.P("El diagrama de la Figura {F:cu} delimita el sistema y muestra los cinco actores humanos y los tres sistemas externos que participan como "
        "actores secundarios. Los 17 casos de uso cubren las 25 HU de los cuatro sprints, las dos incorporadas tras la EF2 (HU-31 en CU-08 y HU-32 "
        "en CU-01) y las de CC-16 a CC-18 (HU-33 a HU-45 en CU-05, CU-06, CU-12 y CU-13). Se usa «extend» cuando un comportamiento solo ocurre "
        "bajo una condición: la fila virtual (CU-16) extiende la asignación (CU-03) cuando la recogida es en el aeropuerto. Desde CC-18 la "
        "verificación del teléfono ya no extiende la solicitud: ocurre una sola vez al crear y activar la cuenta (CU-13), que es precondición de "
        "CU-12 junto con el convenio aprobado (CU-06). No se usó «include» porque no hay comportamiento obligatorio compartido que "
        "convenga separar, ni generalización de actores, porque los roles tienen permisos disjuntos (RBAC).")
    r.figure(F + "uml_cu.png", "cu", "Diagrama de casos de uso de FlotaÁgil (UML 2.5)", width_cm=15.2)
    rows = [(c["id"], c["nombre"], c["act"], c["sec"], c["req"]) for c in CU]
    r.table("cu_res", "Casos de uso, actores y requerimientos", ["ID", "Caso de uso", "Actor principal", "Actores secundarios", "HU · RN"], rows,
            [1.4, 4.4, 3.0, 3.4, 4.4], font=8)
    r.P("**Consistencia con los procesos:** P1 se apoya en CU-01, CU-12 y CU-13; P2 en CU-02, CU-03, CU-10, CU-15 y CU-16; P3 en CU-11 y CU-14; "
        "P3.2 en CU-08; el subproceso P1.1, en CU-06 y CU-13. La especificación completa de cada caso de uso —objetivo, actores, precondiciones, evento de inicio, flujo principal con "
        "acciones del actor y respuestas del sistema, flujos alternativos, excepciones, postcondiciones y reglas— está en el Anexo E. A modo de "
        "ejemplo, la {T:cu03} presenta CU-03.")
    c = CU[2]
    r.kv_table("cu03", "Especificación del caso de uso CU-03 Asignar viaje con sugerencia", [
        ("Objetivo", c["obj"]), ("Actor principal / secundarios", f'{c["act"]} / {c["sec"]}'), ("Requerimientos", c["req"]),
        ("Precondiciones", c["pre"]), ("Evento de inicio", c["ini"]), ("Flujo principal", "\n".join(c["flujo"])),
        ("Flujos alternativos", "\n".join(c["alt"])), ("Excepciones", "\n".join(c["exc"])), ("Postcondiciones", c["post"]), ("Reglas", c["reglas"]),
    ], font=8)

    # ---------- componentes
    r.H2("Diagrama de componentes")
    r.P("El diagrama de la Figura {F:comp} sigue UML 2.5: cada componente lleva el estereotipo «component» y su ícono; las interfaces "
        "proporcionadas se dibujan como círculo (lollipop) y las requeridas como semicírculo (socket), unidas en conectores de ensamble; las "
        "dependencias internas son flechas discontinuas «use». Se distinguen los componentes lógicos del backend (dentro del subsistema), los "
        "clientes desplegables y los componentes físicos de datos («database») y externos («external»).")
    r.figure(F + "uml_comp.png", "comp", "Diagrama de componentes de FlotaÁgil (UML 2.5)", width_cm=16.4)
    comp = [
        ("Panel administrativo", "Interfaz de despacho, mapa, reportes, convenios y chat", "Requiere IApiRest, IRealtime, IMapas", "React + Vite", "—"),
        ("Portal del pasajero y convenios", "Pedido con cuenta en tres tipos de viaje, tu viaje, mis viajes y registro de empresas cliente (CC-16, CC-18)", "Requiere IApiRest", "React + Vite", "—"),
        ("App del conductor", "Estado, asignaciones, viaje, cobro y envío de GPS", "Requiere IApiRest, IRealtime", "React + Capacitor", "—"),
        ("Autenticación y RBAC", "Inicio de sesión único para los cinco roles; JWT; permisos por rol y empresa; recuperación de contraseña", "Proporciona /api/auth/*; usado por todos", "simplejwt, DRF", "USUARIO"),
        ("Cuentas de pasajero", "Crear y activar la cuenta por WhatsApp; aviso de privacidad; viajes propios", "Proporciona /api/mi-cuenta/*; usa Mensajería y Auditoría", "DRF", "CUENTA_PASAJERO, PASAJERO"),
        ("Reservas y despacho", "Ciclo de vida del viaje y máquina de estados", "Proporciona /api/viajes, /asignar; usa Motor, Mensajería, Auditoría", "DRF", "VIAJE, ASIGNACION, HISTORIAL_ESTADO"),
        ("Motor de sugerencia", "Ordenar candidatos por distancia y turno o por fila", "Proporciona /api/viajes/{id}/sugerencias; usa Flota y Fila", "PostGIS", "CONDUCTOR, POSICION_GPS"),
        ("Gateway tiempo real", "Recibir posiciones y difundir eventos", "Proporciona IRealtime (/ws/flota, /ws/conductor); usa Redis", "Channels, Daphne", "POSICION_GPS"),
        ("Flota", "Conductores, vehículos, vehículo activo y carga CSV", "Proporciona /api/conductores, /api/vehiculos", "DRF", "CONDUCTOR, VEHICULO, CONDUCTOR_VEHICULO"),
        ("Convenios", "Registro de la empresa cliente, aprobación, cuenta propia y vigencia (DC-35)", "Proporciona /api/convenios; usa Autenticación y Auditoría", "DRF", "CONVENIO"),
        ("Fila virtual aeropuerto", "Ingreso, orden y salida de la fila", "Proporciona servicio interno a Motor; usa Gateway", "PostGIS", "GEOCERCA, FILA_AEROPUERTO"),
        ("Mensajería WhatsApp", "Plantillas, avisos, verificación, chat y webhook", "Proporciona IWebhook (/webhooks/whatsapp); requiere IMensajes", "Twilio SDK, Celery", "MENSAJE_WHATSAPP, PASAJERO"),
        ("Cobros y reportes", "Registro de pagos, turnos, cierre de caja, liquidación, CSV", "Proporciona /api/viajes/{id}/pago, /api/reportes, /api/turnos/{id}/cierre", "DRF", "PAGO_VIAJE, CALIFICACION, TURNO, CIERRE_CAJA"),
        ("Monitoreo de vuelos", "Programar y ejecutar consultas, proponer ajustes, generar alertas", "Usa Adaptador de vuelos y Reservas", "Celery beat", "VUELO, ALERTA_VUELO"),
        ("Adaptador de vuelos", "Traducir el proveedor (AeroAPI/AeroDataBox) a un contrato propio", "Requiere IEstadoVuelo", "httpx", "—"),
        ("Auditoría", "Registro inmutable de acciones sensibles", "Proporciona /api/auditoria (solo lectura)", "DRF + trigger", "AUDITORIA"),
    ]
    r.table("comp", "Componentes, responsabilidades e interfaces", ["Componente", "Responsabilidad", "Interfaces y dependencias", "Tecnología", "Datos"], comp,
            [3.0, 4.1, 4.6, 2.0, 2.9], font=7.5)
    r.P("**Funcionamiento conjunto.** Cuando el despachador confirma una asignación, el panel llama a Reservas y despacho por IApiRest; este "
        "verifica permisos con Autenticación, toma la sugerencia del Motor (que consulta Flota y Fila virtual), registra la asignación en una "
        "transacción y publica el evento en Redis; el Gateway lo entrega a la app del conductor por IRealtime y Mensajería encola el aviso al "
        "pasajero, que Twilio entrega por IMensajes. Cada componente del backend corresponde a una aplicación Django del monolito modular "
        "descrito en 4.7 y se despliega en los contenedores de la Figura {F:infra}.")
    r.P("**Clientes web y apariencia por empresa.** El panel y el portal son un mismo proyecto React con dos entradas: el inicio de sesión "
        "único (CC-16) lleva al administrador y al despachador al panel, y al pasajero y al supervisor de convenio a su vista del portal. El "
        "portal usa un sistema visual propio (tokens de color, tipografía autoalojada y componentes accesibles, HU-37) y cada empresa ve su "
        "logo, su nombre y su color, que se aplican como variables CSS sobre los mismos componentes; los colores de estado (éxito, alerta, "
        "error) son fijos para no perder legibilidad. Así, una sola versión del código atiende a varias empresas sin bifurcarlo, coherente con el "
        "modelo multiempresa (RN-13).")

    # ---------- datos
    r.H2("Modelo de datos")
    r.P("El modelo lógico relacional (Figura {F:er}) evoluciona el modelo conceptual de la sección 2.5.4 para cubrir el alcance vigente: **23 entidades** en tercera forma normal. A las 18 del diseño "
        "original se suman CONFIGURACION_EMPRESA (parámetros por empresa, DC-02) y ALERTA_VUELO (DC-23), agregadas en la construcción; **TURNO y "
        "CIERRE_CAJA**, agregadas tras la EF2 (CC-12); y **CUENTA_PASAJERO**, agregada con la cuenta obligatoria del portal (CC-18). "
        "Se usa notación de pata de gallo: dos barras indican «exactamente uno», círculo y barra «cero o uno», y círculo con pata «cero o muchos».")
    r.figure(F + "modelo_datos.png", "er", "Modelo lógico de datos de FlotaÁgil (23 entidades)", width_cm=16.6)
    r.P("**Corrección de la EF2: turnos y cuadratura.** El modelo anterior no permitía medir el proceso P3.2 ni los indicadores por turno: "
        "HISTORIAL_ESTADO registra las transiciones de los viajes, no las jornadas, y CONDUCTOR.estado se sobrescribe en cada cambio, con lo que "
        "se pierde la historia. Se agregan dos entidades ({T:nuevas_ent}). **TURNO** registra cada jornada con su conductor, su vehículo, su hora de "
        "inicio y su hora de término; un índice único parcial impide dos turnos abiertos del mismo conductor. **CIERRE_CAJA** registra la "
        "cuadratura de un turno: el monto registrado por el sistema, el monto rendido, la diferencia, quién hizo el cuadre y cuándo; tiene a lo "
        "más un cierre por turno. Los viajes de un turno son los que el conductor finalizó entre su inicio y su término, el mismo criterio que "
        "ya usa «Mi turno» (HU-18), por lo que no se agrega una clave foránea en VIAJE.")
    r.table("nuevas_ent", "Entidades agregadas tras la EF2 y lo que permiten medir", ["Entidad", "Atributos pedidos en la EF2", "Atributos adicionales", "Qué habilita"], [
        ("TURNO", "conductor_id, vehiculo_id, hora_inicio, hora_termino", "motivo_termino", "KPI-03 (adopción por turnos), KPI-04 (horas de turno), «Mi turno» con historial y base del cierre de caja"),
        ("CIERRE_CAJA", "turno_id, monto_rendido, diferencia, responsable_id, fecha_cierre", "monto_registrado (fija el valor esperado al cerrar) y observacion (obligatoria si hay diferencia)", "KPI-05 (exactitud de la cuadratura), proceso P3.2 y trazabilidad de cada diferencia"),
    ], [2.4, 5.0, 4.6, 4.6], font=8)
    r.P("Estas dos entidades **están implementadas (DC-32)** junto con la pantalla de cierre de caja (HU-31): la migración trasladó a TURNO "
        "los turnos que antes se guardaban en dos columnas de CONDUCTOR (DC-26), y cada cálculo de KPI-03, KPI-04 y KPI-05 y cada cierre se "
        "reconstruyen desde registros del diccionario (Anexo F).")
    r.P("**Cambios de la semana 14 (CC-16 a CC-18).** Al pasar a un inicio de sesión único y a pedir siempre con cuenta, el modelo cambió en "
        "cuatro puntos ({T:ent_s14}). Ninguno rompe la trazabilidad de los viajes ya registrados: las migraciones dejan los convenios existentes "
        "aprobados y las reservas anteriores conservan su verificación por WhatsApp (RN-06).")
    r.table("ent_s14", "Cambios del modelo de datos por CC-16 a CC-18", ["Entidad", "Cambio", "Motivo", "Decisión"], [
        ("CUENTA_PASAJERO (nueva)", "Usuario de rol PASAJERO ligado a un PASAJERO al confirmar el teléfono; registra la aceptación del aviso de privacidad y su versión", "Pedir con cuenta (CC-18) y dejar evidencia del consentimiento (Ley 21.719)", "DC-36, DC-44, DC-45"),
        ("CONVENIO", "Se retiran el token del link y la contraseña compartida; se agregan estado (EN_REVISION, APROBADO, RECHAZADO, INACTIVO), encargado, revisión y cuenta propia", "Cada empresa cliente entra con su cuenta y el administrador la aprueba (CC-16)", "DC-35"),
        ("VIAJE", "pasajeros, maletas, vuelo_salida_en y vuelo_salida_tipo; la autorización de avisos queda ligada al usuario del convenio", "Asignar un vehículo con capacidad suficiente y sugerir la hora de salida hacia el aeropuerto", "DC-42, DC-43"),
        ("USUARIO", "rol agrega CONVENIO y PASAJERO", "Un solo inicio de sesión web para los cinco roles", "DC-34"),
        ("PASAJERO y CUENTA_PASAJERO", "PASAJERO.telefono admite nulo; CUENTA_PASAJERO guarda el WhatsApp nuevo por confirmar; al eliminar la cuenta, los datos personales se anonimizan y se conservan viajes, pagos y auditoría", "Derecho de supresión del titular (Ley 21.719, HU-45)", "DC-50"),
    ], [3.0, 6.0, 5.0, 2.6], font=8)
    r.P("**Decisiones principales:**")
    r.bullets([
        "**Multiempresa desde el diseño:** EMPRESA es la raíz y su identificador se propaga a las entidades de negocio, lo que permite aplicar RN-13 "
        "en cada consulta y evolucionar a multi-tenant sin migraciones estructurales.",
        "**Relación N:M resuelta:** un conductor puede usar varios vehículos y un vehículo puede tener conductores en distintos turnos; "
        "CONDUCTOR_VEHICULO resuelve la relación con clave compuesta.",
        "**Historial y auditoría:** HISTORIAL_ESTADO registra cada transición del viaje (base de KPI-01, KPI-02 y KPI-09), TURNO cada jornada (base de KPI-03 y KPI-04) y AUDITORIA las acciones "
        "sensibles; ambas son de solo inserción, garantizado con permisos y un trigger que rechaza UPDATE y DELETE.",
        "**Geoespacial:** origen, destino, posiciones y geocercas usan GEOGRAPHY de PostGIS (SRID 4326) con índices GiST para ST_DWithin y ST_Distance.",
        "**Normalización:** PAGO_VIAJE, VUELO y CALIFICACION son entidades 1:0..1 con VIAJE, y CIERRE_CAJA lo es con TURNO, para no dejar columnas nulas en viajes que no las usan "
        "y conservar su propia marca temporal. Se acepta una desnormalización controlada: la última posición de cada conductor vive en Redis para "
        "no escribir en la base con cada ping.",
        "**Integridad:** claves foráneas con ON DELETE PROTECT (nada se borra en cascada; se desactiva con «activo»); CHECK para dominios "
        "(estado, método, puntaje 1–5, monto ≥ 0); índice único parcial que impide a un conductor tener dos entradas abiertas en la fila "
        "(salida_en IS NULL), otro que impide dos turnos abiertos por conductor y, para RN-03, un bloqueo de fila sobre la reserva y el conductor "
        "al asignar, de modo que un conductor no quede con dos viajes en ejecución (CP-14).",
        "**Datos sensibles:** teléfonos, nombres, direcciones y ubicaciones se marcan como personales en el diccionario; las credenciales solo "
        "existen como hash. POSICION_GPS se purga a los 30 días por una tarea programada (RN-15).",
    ])
    r.P("La base de datos es relacional, por lo que los elementos propios de modelos no relacionales (colecciones, documentos embebidos o "
        "patrones de consulta NoSQL) no aplican; Redis se usa solo como canal y caché efímera, sin datos que no estén también en PostgreSQL.")
    r.P("**Relación con procesos y casos de uso:** P1 escribe PASAJERO, VIAJE, VUELO y MENSAJE_WHATSAPP; P2 lee POSICION_GPS, FILA_AEROPUERTO y "
        "CONDUCTOR y escribe ASIGNACION y ALERTA_VUELO; el inicio y el término de la jornada del conductor (CU-09) abren y cierran TURNO; P3 escribe HISTORIAL_ESTADO, PAGO_VIAJE y CALIFICACION; P3.2 lee TURNO y PAGO_VIAJE y escribe CIERRE_CAJA y AUDITORIA. El "
        "diccionario de datos completo, con tipo, longitud, nulidad, claves, dominios, valores por defecto, validaciones y sensibilidad de cada campo, "
        f"está en el Anexo F, actualizado con las decisiones de cambio DC-01 a DC-{DC_MAX} de la construcción y con los cambios CC-12 a CC-18, y usa los mismos nombres del diagrama.")

    # ---------- topología
    r.H2("Topología de comunicaciones")
    r.P("La Figura {F:topo} muestra las tres zonas de red: la de los usuarios (red local de la central y redes móviles 4G/5G), la nube de AWS y "
        "los servicios externos en Internet. Toda comunicación con la plataforma entra por el puerto 443 de Nginx; los servicios internos "
        "(Gunicorn, Daphne, Redis y PostgreSQL) solo escuchan en la red interna de Docker.")
    r.figure(F + "topologia.png", "topo", "Topología de comunicaciones", width_cm=16.4)
    flows = [
        ("PC de la central / supervisor", "Nginx", "HTTPS (TLS 1.2+)", "443/TCP", "API REST, portal, estáticos", "Bajo demanda"),
        ("PC de la central", "Nginx → Daphne", "WSS", "443/TCP", "Mapa y alertas en tiempo real", "Persistente"),
        ("App del conductor", "Nginx → Daphne", "WSS", "443/TCP", "Envío de posición, recepción de asignaciones", "Ping cada 5–10 s"),
        ("App del conductor", "Nginx → Gunicorn", "HTTPS", "443/TCP", "Cambios de estado, pago", "Por evento"),
        ("Twilio", "Nginx → Gunicorn", "HTTPS (webhook firmado)", "443/TCP", "Respuestas del pasajero, estados de entrega", "Por evento"),
        ("Celery / Gunicorn", "Twilio, API de vuelos, Sentry, S3", "HTTPS saliente", "443/TCP", "Mensajes, vuelos, errores, respaldos", "Por evento / programado"),
        ("Navegador del panel", "Google Maps", "HTTPS", "443/TCP", "Mapa base y geocodificación", "Bajo demanda"),
        ("Equipo de proyecto", "EC2", "SSH con llave", "22/TCP (IP autorizada)", "Administración", "Excepcional"),
        ("Contenedores internos", "PostgreSQL / Redis", "TCP", "5432 / 6379 (red Docker)", "Persistencia y canales", "Continuo"),
        ("Usuarios", "Route 53", "DNS", "53/UDP", "Resolver app.flotaagil.cl", "Por sesión"),
    ]
    r.table("flujos", "Flujos de comunicación, protocolos y puertos", ["Origen", "Destino", "Protocolo", "Puerto", "Propósito", "Frecuencia"], flows,
            [3.2, 2.8, 2.6, 2.4, 3.6, 2.0], font=7.8)
    r.P("**Características de transmisión.** Un ping GPS es un JSON de unos 200 bytes; con encabezados WebSocket y TLS ronda los 500 bytes. Con 50 "
        "conductores a un ping cada 7,5 s en promedio, el tráfico entrante es de unos 3,3 KB/s, despreciable para el enlace de la instancia. Por "
        "conductor, un turno de 8 horas genera unas 3.840 posiciones (≈ 2 MB) más las llamadas a la API, muy por debajo de los 50 MB de RNF-07, porque "
        "la navegación usa la app externa y no descarga mapas. **Supuestos de conectividad:** cobertura 4G con latencia de 50–150 ms en Santiago y "
        "banda ancha en la central; la meta de latencia de 5 s (RNF-02) deja margen para redes móviles degradadas.")
    r.P("**Protección.** TLS en todo el tráfico externo con HSTS; JWT en cada petición y en el handshake WSS (enviado como subprotocolo, no en la URL, para que no quede en los registros); Security Group que solo abre 443 "
        "a Internet y 22 a la IP del equipo; validación de la firma X-Twilio-Signature en el webhook; CORS restringido al dominio propio; límites de "
        "tasa en el inicio de sesión, el registro de cuentas y la recuperación de contraseña. **Dependencias y efecto de su interrupción:** si cae la conexión del conductor, la app "
        "encola posiciones y reintenta, y el panel marca el dato como no confiable a los 60 s; si cae Internet en la central, el despachador opera "
        "desde un teléfono con datos móviles (8.2); si falla Twilio, los avisos quedan en cola y el despachador recibe una alerta; si falla la API de "
        "vuelos, se reintenta y se alerta tras dos fallas.")
    r.P("**Recorrido de una solicitud representativa (asignación):** el despachador confirma en el panel → POST HTTPS a app.flotaagil.cl/api/"
        "viajes/{id}/asignar → Route 53 resuelve a la Elastic IP → Nginx termina TLS y reenvía a Gunicorn:8000 → Django valida el JWT y el rol, "
        "abre una transacción en PostgreSQL:5432 y registra ASIGNACION → publica el evento en Redis:6379 → Daphne lo entrega por WSS a la app "
        "del conductor (≈ 0,5 s) → el conductor acepta (POST HTTPS) → Celery envía el aviso a la API de Twilio (HTTPS saliente) → WhatsApp lo "
        "entrega al pasajero.")

    # ---------- infraestructura
    r.H2("Diagrama de Infraestructura")
    r.P("La infraestructura es de **nube pública** con modelo de servicio de infraestructura (IaaS; Mell y Grance, 2011) en AWS, región us-east-1, sobre una instancia EC2 en una subred pública de una VPC "
        "propia. La aplicación, la base de datos y Redis corren como contenedores Docker en la misma instancia; el almacenamiento es un volumen EBS "
        "gp3 cifrado y los respaldos van a snapshots EBS y a un bucket S3.")
    r.figure(F + "infraestructura.png", "infra", "Infraestructura de producción en AWS", width_cm=16.4)
    infra = [
        ("EC2 t4g.small", "2 vCPU Graviton2, 2 GiB RAM, Ubuntu 24.04 LTS ARM64, Docker", "Ejecutar los 7 contenedores", "≈ 12,3"),
        ("EBS gp3", "30 GB, 3.000 IOPS base, cifrado KMS", "Volumen raíz y datos de PostgreSQL", "≈ 2,4"),
        ("Snapshots EBS (DLM)", "Cada 6 h, retención 7 días (Amazon Web Services, 2026c)", "Respaldo de máquina completa (RPO 6 h)", "≈ 1,0"),
        ("S3", "Bucket privado, cifrado SSE-S3, versionado, ciclo de vida 30 días", "pg_dump cada 6 h y configuración", "≈ 0,2"),
        ("Elastic IP (IPv4 pública)", "Asociada a la instancia", "Dirección estable para DNS", "≈ 3,7"),
        ("Route 53", "Zona flotaagil.cl", "DNS", "≈ 0,5"),
        ("CloudWatch + SNS", "Agente con CPU, memoria y disco; alarmas por correo; acción de recuperación automática", "Monitoreo de infraestructura", "≈ 0,9"),
        ("IAM + SSM Parameter Store", "Rol de instancia con permisos mínimos; parámetros SecureString", "Credenciales y secretos", "$0"),
        ("Security Group", "Entrada 443 abierto, 22 solo IP del equipo; salida 443", "Cortafuegos de la instancia", "$0"),
    ]
    r.table("infra", "Recursos de infraestructura y costo mensual", ["Recurso", "Especificación", "Función", "USD/mes"], infra, [3.2, 6.6, 5.0, 1.8], font=8,
            source="Elaboración propia con precios on-demand de Amazon Web Services (2026a) para us-east-1, consultados en octubre de 2026.")
    r.P("**Dimensionamiento.** El caso de diseño es una flota de 50 conductores en turno y hasta 10 usuarios del panel; RNF-03 se verifica con 50 "
        "usuarios concurrentes. Ese volumen produce unas 5 escrituras de posición por segundo en Redis y menos de 2 por segundo en PostgreSQL, y "
        "decenas de peticiones REST por minuto, lo que cabe con holgura en 2 vCPU. La memoria es la restricción (presupuesto en 3.2); si el uso supera "
        "el 80 % sostenido se escala verticalmente a t4g.medium (4 GiB, ≈ USD 24/mes) con un reinicio de minutos.")
    r.P("**Ambientes.** Desarrollo: Docker Compose en el equipo de cada integrante con datos sintéticos. Pruebas: CI en GitHub Actions con "
        "PostgreSQL/PostGIS y Redis como servicios efímeros, más un ambiente de *staging* **idéntico a producción** (misma instancia t4g.small, "
        "mismo disco e imágenes) que se enciende solo durante las ventanas de prueba y la UAT (sección 6.1). Producción: la instancia del diagrama. "
        "Los tres usan las mismas imágenes; solo cambian los parámetros de SSM.")
    r.P("**Responsabilidades (modelo de responsabilidad compartida).** AWS responde por el hardware, la red física, el hipervisor y la durabilidad "
        "de EBS y S3. El equipo responde por el sistema operativo y sus parches, Docker, la aplicación, la base de datos, los respaldos, los "
        "secretos y la configuración de red. **Dependencias externas:** Twilio/Meta, API de vuelos, Google Maps, Let's Encrypt y GitHub.")
    spof = [
        ("Instancia EC2 única", "Caída total del servicio", "Recuperación automática de CloudWatch; recreación desde snapshot en otra AZ en < 2 h", "Aceptado por costo"),
        ("Zona de disponibilidad us-east-1a", "Caída total", "Snapshots y dumps en servicios regionales; AMI para relanzar en us-east-1b", "Aceptado por costo"),
        ("PostgreSQL en contenedor", "Pérdida de datos desde el último respaldo", "Snapshot y pg_dump cada 6 h, alternados; prueba mensual de restauración", "Mitigado"),
        ("Twilio / Meta", "Sin avisos ni verificación", "Cola con reintentos; alerta al despachador; confirmación telefónica manual", "Mitigado"),
        ("Conexión de la central", "Despachador sin panel", "Panel accesible desde teléfono con datos móviles", "Mitigado"),
    ]
    r.table("spof", "Puntos únicos de falla", ["Elemento", "Efecto", "Medida", "Tratamiento"], spof, [3.2, 3.2, 7.6, 2.6], font=8)
    r.P("**Correspondencia con presupuesto y metas de servicio.** La infraestructura cuesta ≈ USD 21 mensuales, dentro de los $100.000 del "
        "proyecto y de la estructura de costos de la {T:costos}. La meta de disponibilidad se fijó en 99,0 % precisamente porque una sola instancia, "
        "cuyo compromiso de AWS es 99,5 % (Amazon Web Services, 2026b), no puede sostener más una vez sumadas las fallas propias; RTO de 2 h y RPO de 6 h se derivan de la "
        "recreación desde snapshot y de la frecuencia de snapshots (8.2).")

    # ---------- arquitectura
    r.H2("Diagrama de Arquitectura")
    r.P("La solución adopta una **arquitectura cliente-servidor en capas con un backend monolítico modular**, complementado con un canal de eventos "
        "en tiempo real (publicación/suscripción sobre Redis) y procesamiento asíncrono (Celery). Las integraciones externas siguen el patrón de "
        "puertos y adaptadores. La Figura {F:arq} integra los componentes de software con la infraestructura que los soporta.")
    r.figure(F + "arquitectura.png", "arq", "Arquitectura de la solución por capas", width_cm=16.0)
    capas = [
        ("Presentación", "Panel, portal y app; validación de formularios, mapa, experiencia por rol", "React 19, Capacitor 7", "PC de la central; Android de conductores"),
        ("Borde y seguridad", "DNS, terminación TLS, proxy inverso, autenticación JWT y autorización por rol y empresa", "Route 53, Nginx, simplejwt", "EC2 (contenedor nginx)"),
        ("Aplicación", "Casos de uso expuestos por API REST, canal WSS y tareas asíncronas", "DRF + Gunicorn, Channels + Daphne, Celery", "EC2 (api, ws, worker, beat)"),
        ("Dominio", "Reglas de negocio y máquina de estados en módulos Django", "Django 5", "EC2"),
        ("Integración", "Adaptadores a WhatsApp, vuelos y mapas con reintentos e idempotencia", "Twilio SDK, httpx", "EC2 → Internet"),
        ("Datos", "Persistencia transaccional y geoespacial, canales y caché, respaldos", "PostgreSQL + PostGIS, Redis, S3, snapshots", "EBS gp3, S3"),
        ("Transversal", "Registro de eventos, errores, disponibilidad, CI/CD y secretos", "JSON logs, Sentry, UptimeRobot, CloudWatch, Actions, SSM", "SaaS y AWS"),
    ]
    r.table("capas", "Capas, responsabilidades y soporte de infraestructura", ["Capa", "Responsabilidad", "Software", "Hardware / infraestructura"], capas,
            [2.4, 6.2, 4.4, 3.6], font=8)
    r.P("**Justificación.** Siguiendo el análisis de atributos de calidad de Bass et al. (2021) y los criterios de Richards y Ford (2020), un monolito modular es la opción adecuada para dos desarrolladores y una sola instancia: una sola base de código, "
        "transacciones locales entre reserva, asignación y pago, y despliegue simple; los módulos separados permiten extraer servicios más adelante si "
        "la escala lo exige. Los microservicios multiplicarían la operación sin beneficio a este volumen.")
    r.P("**Autenticación y autorización.** Usuarios internos con contraseña y JWT: acceso de 15 min que vive solo en memoria y "
        "refresco de 12 h que rota en cada uso, con tope de sesión de 12 h. En el panel el refresco va en una cookie httpOnly con verificación del "
        "origen; en la app, en el almacén cifrado de Android (Keystore), con cierre de sesión en el servidor. Bloqueo de 15 min "
        "tras cinco intentos; contraseña temporal con cambio obligatorio (DC-14); el mismo inicio de sesión sirve a los convenios (cuenta aprobada por el administrador) y a los pasajeros (cuenta activada al verificar su teléfono por WhatsApp). Permisos por "
        "rol en cada endpoint y filtro por empresa en cada consulta (RN-13). **Errores y registro de eventos:** manejador de excepciones de DRF con "
        "respuestas uniformes; registros en JSON con identificador de correlación por petición, retenidos 90 días; errores no controlados a Sentry; "
        "reintentos con espera exponencial para Twilio y la API de vuelos; webhooks idempotentes por su identificador.")
    rnf_map = [
        ("RNF-01 Disponibilidad", "Reinicio automático de contenedores, recuperación automática de EC2, monitoreo externo y respaldos"),
        ("RNF-02 / RNF-03 Desempeño", "WSS persistente, última posición en Redis, índices GiST, consultas paginadas, tareas lentas fuera de la petición"),
        ("RNF-04 / RNF-05 Seguridad", "TLS + HSTS, PBKDF2, JWT de vida corta, secretos en SSM, Security Group mínimo"),
        ("RNF-07 Consumo de datos", "Pings compactos, frecuencia adaptativa (10 s detenido, 5 s en movimiento), navegación externa"),
        ("RNF-09 / RNF-10 Privacidad y trazabilidad", "GPS solo en turno, purga a 30 días, auditoría e historial de solo inserción"),
        ("RNF-11 Mantenibilidad", "Módulos Django con pruebas, CI obligatoria, contenedores reproducibles"),
        ("RNF-13 Tolerancia a fallos", "Adaptadores con reintentos, cola en Celery, idempotencia de webhooks"),
    ]
    r.table("rnf_arq", "Cómo responde la arquitectura a los requerimientos no funcionales", ["Requerimiento", "Mecanismo"], rnf_map, [4.6, 12.0], font=8)
    r.P("**Recorrido completo de información.** Un pasajero con su cuenta activa envía el pedido desde el portal (Presentación) → Nginx lo recibe "
        "por HTTPS (Borde) → la API valida la sesión, la capacidad y el vuelo y crea el VIAJE en SOLICITADO (Aplicación y Dominio, PostgreSQL) → "
        "Celery envía el aviso de confirmación por el adaptador de WhatsApp (Integración) → el despachador ve la reserva en el panel por WSS, "
        "pide sugerencias (PostGIS) y asigna → la app recibe la asignación, el conductor acepta, envía posiciones durante el trayecto y registra el "
        "pago → el viaje queda FINALIZADO y alimenta reportes y KPI. Cada paso deja su traza en HISTORIAL_ESTADO y en los registros de eventos.")
    adr = [
        ("Monolito modular en una instancia", "Simplicidad y costo", "Punto único de falla; escalamiento vertical", "Snapshots, AMI y escalamiento a t4g.medium"),
        ("PostgreSQL en contenedor", "Ahorro frente a RDS (≈ USD 15/mes)", "Respaldos y parches a cargo del equipo", "DLM, pg_dump, prueba mensual de restauración"),
        ("Capacitor para la app", "Reutilización de React", "GPS en segundo plano según fabricante (R-01)", "PoC H-3; alternativa en primer plano"),
        ("WhatsApp vía Twilio", "Sandbox inmediato y SDK", "Costo por mensaje (R-04) y plantillas de Meta (R-12)", "Adaptador; en la versión 1.1 se reemplaza por el chat interno (CC-19)"),
        ("Datos en us-east-1", "Costo y servicios", "Transferencia internacional (Ley 21.719)", "Garantías contractuales y aviso de privacidad"),
    ]
    r.table("adr", "Decisiones, limitaciones y riesgos arquitectónicos", ["Decisión", "Motivo", "Limitación o riesgo", "Medida"], adr, [3.6, 3.4, 4.6, 5.0], font=8)
    r.P("**Consistencia.** Las capas corresponden a los componentes de la {T:comp}, a los contenedores de la Figura {F:infra}, a los flujos de la "
        "{T:flujos} y a las entidades de la Figura {F:er}; las tecnologías son las seleccionadas en el capítulo III.")

    r.H3("Diseño aprobado para la versión 1.1 (CC-19 a CC-21)")
    r.P("El cliente aprobó en la semana 14 tres cambios que se construyen **después de esta entrega**, en la versión 1.1, para no comprometer "
        "la UAT. Se presentan aquí como diseño: no forman parte de lo construido ni de las pruebas al corte. El de mayor efecto es **CC-19**, "
        "que aprovecha que desde CC-18 todos los usuarios tienen cuenta para reemplazar a WhatsApp como canal con el pasajero ({T:cc19}).")
    r.table("cc19", "Diseño de CC-19: chat interno y retiro de WhatsApp", ["Elemento", "Diseño"], [
        ("Chat interno", "Conversaciones por WebSocket (Django Channels, la misma capa de tiempo real del mapa) en ambos sentidos: pasajero ↔ central, "
         "desde que pide hasta 24 h después del viaje; central ↔ conductor, durante todo el turno; y conductor ↔ pasajero, solo en EN_CAMINO y "
         "EN_ZONA, con respuestas rápidas para que el conductor no escriba mientras maneja. La central responde como equipo y puede leer el chat "
         "conductor ↔ pasajero, con auditoría."),
        ("Verificación de la cuenta", "Por correo, con un enlace que vence a las 24 h; reemplaza la confirmación por WhatsApp de HU-20."),
        ("Avisos al pasajero", "Notificación del navegador (Web Push) y correo (Amazon SES), con una casilla para aceptar el correo de viajes. Los "
         "correos de la cuenta (activación y recuperación) se envían siempre."),
        ("Emergencias sin costo", "Botones «Llamar a la central» (tel:) y «Escribir a la central por WhatsApp» (wa.me, desde el WhatsApp propio "
         "del pasajero), sin intermediario."),
        ("Modelo de datos", "Entidades nuevas CONVERSACION y MENSAJE_CHAT, con empresa (RN-13) y retención de 12 meses (RN-15); MENSAJE_WHATSAPP "
         "queda como historial."),
        ("Historias y reglas afectadas", "Cambian HU-20, HU-21, HU-24 y HU-30, RN-06 (verificación por correo) y RN-09 (cancelar desde la cuenta "
         "o por el chat); se retira Twilio por completo."),
        ("Efecto", "Desaparece la dependencia de las plantillas de Meta (R-12) y el costo por mensaje (R-04): el consumo variable baja de ≈ $88 "
         "a ≈ $20 por reserva (sección 3.1)."),
        ("Riesgo aceptado", "En iPhone, el aviso del navegador solo funciona con el portal agregado a la pantalla de inicio; si no, el aviso "
         "llega por correo."),
    ], [3.6, 13.0], font=8)
    r.P("**CC-20** unifica el aspecto del panel y de la app del conductor con el sistema visual del portal («Tiffany degradé», HU-37), y "
        "**CC-21** permite que cada empresa cliente muestre su logo, su nombre y sus colores en el portal, algo que los tokens de HU-37 ya "
        "dejan preparado. Las llamadas de voz dentro de la plataforma (WebRTC) quedan como evolución sin solicitud de cambio, y la biometría "
        "se descartó: para el pasajero es desproporcionada, y para el conductor se evaluará una fotografía de inicio de turno revisada por el "
        "despachador, sin datos biométricos.")
