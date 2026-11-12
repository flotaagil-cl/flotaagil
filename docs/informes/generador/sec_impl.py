"""Capítulo VII · Desarrollo e implementación de la solución (avance al corte de la semana 14)."""

IMG = "fig/impl/"


def implementacion_real(r):
    r.H1("Desarrollo e implementación de la solución")
    r.P("Este capítulo presenta lo **construido y probado** al corte de la semana 14: los incrementos de los Sprints 0 a 3 y el avance del Sprint 4, en curso, "
        "sus resultados de prueba, los defectos encontrados y las decisiones tomadas durante la construcción. Todo se probó con **datos sintéticos** "
        "(empresas, conductores y pasajeros ficticios con dominios *.example* y RUT ficticios); no se usaron datos personales reales ni se envió "
        "ningún mensaje real de WhatsApp. La evidencia de cada historia (capturas y resultados) está versionada en el repositorio, en "
        "*docs/evidencias/*, y la bitácora en *docs/avance.md*.")

    # ------------------------------------------------------------------ 7.1
    r.H2("Estrategia de construcción y flujo de trabajo")
    r.P("Cada historia se construye en su propia rama (*feat/HU-xx-…*; *fix/…* para correcciones y *chore/…* para tareas técnicas) y termina en "
        "un pull request con *Closes #n* hacia el issue de la historia. La integración continua (GitHub Actions) ejecuta en cada cambio el análisis "
        "estático (Ruff, Bandit, ESLint, TypeScript) y las pruebas con cobertura mínima de 70 %, y la rama *main* está protegida: exige una "
        "aprobación, la verificación *ci* en verde y fusión por *squash*. Al terminar una historia se cumplen siempre los mismos pasos, que son la "
        "forma concreta de la Definition of Done ({T:flujo}).")
    r.table("flujo", "Pasos de cierre de cada historia", ["Paso", "Qué se hace", "Dónde queda"], [
        ("1. Inicio", "La tarjeta pasa a «En curso» en el tablero; rama encadenada desde la anterior", "GitHub Projects"),
        ("2. Construcción", "Backend, panel y app con sus pruebas automáticas; contrato OpenAPI regenerado", "Commits con referencia al issue (*Refs #n*)"),
        ("3. Prueba manual", "Recorrido contra el backend real con datos sintéticos y capturas en escritorio y en celular (390 px)", "*docs/evidencias/HU-xx/*"),
        ("4. Resultados", "Totales de las suites, casos de prueba (CP) con esperado y obtenido, pendientes", "*docs/evidencias/HU-xx/resultados.md*"),
        ("5. Cambios", "Todo desvío del diccionario de datos se registra como decisión de cambio (DC)", "*docs/diccionario-cambios.md* (Anexo D)"),
        ("6. Pull request", "Cuerpo con qué cambia, cómo probarlo, *Closes #n* y checklist de la DoD", "*docs/prs/HU-xx.md*"),
        ("7. Revisión", "La tarjeta pasa a «En revisión»; el otro integrante revisa y el Product Owner aprueba", "Tablero y PR"),
    ], [2.6, 9.0, 5.0], font=8.2)
    r.P("Las historias se construyeron en ramas encadenadas (cada una parte de la anterior), por lo que se fusionan en orden mediante **cuatro "
        "pull requests, uno por sprint**, con todos los *Closes #n* de sus historias. La fusión se acumuló porque la cuenta de GitHub de uno de "
        "los integrantes quedó restringida (riesgo R-15) y los pull requests debe abrirlos el otro. A la fecha de corte las 25 historias están "
        "en «En revisión» y los cuatro pull requests están redactados (*docs/prs/plan-de-fusion.md*); su apertura y fusión, que además ejecuta "
        "la integración continua sobre estas ramas, es la primera tarea de lo que resta del Sprint 4.")
    r.P("La {T:repo} resume el tamaño del repositorio al corte. Los sprints se ejecutaron en las semanas de la línea base: Sprint 0 y prueba de "
        "concepto H-3 en las semanas 6 y 7, Sprint 1 en las semanas 8 y 9, Sprint 2 en la 10 y 11, Sprint 3 en la 12 y 13, y el Sprint 4, en "
        "curso, en la 14 y 15 (sección 9.1).")
    r.table("repo", "Tamaño del repositorio al corte de la semana 14", ["Componente", "Archivos de código", "Líneas (sin migraciones)", "Pruebas automáticas", "Cobertura"], [
        ("Backend (Django 5.2, DRF, Channels, Celery 5.5)", "173", "19.427", "1.066 (pytest)", "98,1 % de líneas"),
        ("Panel web y portal (React 19, Vite 6, TanStack Query)", "157", "17.417", "591 (Vitest)", "94,4 %"),
        ("App del conductor (Capacitor 7, React 19)", "43", "3.759", "89 (Vitest)", "95,3 % en la lógica"),
        ("**Total**", "**373**", "**40.603**", "**1.746**", "—"),
    ], [5.8, 2.4, 2.8, 3.0, 2.6], font=8.2, source="Elaboración propia a partir del repositorio *flotaagil/flotaagil* (133 commits en la rama de integración).")

    # ------------------------------------------------------------------ 7.2
    r.H2("Sprint 0 y prueba de concepto H-3")
    r.P("El **Sprint 0** (semanas 6 y 7) dejó listo el ecosistema de desarrollo: organización y repositorio en GitHub, tablero con las 25 historias y "
        "sus criterios, plantillas de issues (historia, defecto, solicitud de cambio, incidente), plantilla de pull request con la DoD, "
        "integración continua, Dependabot y protección de *main* (Anexo N).")
    r.P("La **prueba de concepto H-3** (semana 7) validó el riesgo de mayor exposición (R-01): registrar la ubicación con la app en segundo plano "
        "y la pantalla apagada. Se descubrió que Android suspendía el JavaScript del WebView y se corrigió manteniendo visible el proceso de "
        "render; se definió además que no se exige registrar con la app cerrada, con mitigaciones en el panel (Anexo M). Su código pasó a ser la "
        "base de la app del conductor.")

    # ------------------------------------------------------------------ 7.3
    r.H2("Incremento del Sprint 1")
    r.P("El Sprint 1 comprometió **45 SP** y los completó: la base del backend y del panel, las reservas, el portal del pasajero con su verificación "
        "por WhatsApp, el registro de vuelos, la flota y el turno del conductor ({T:s1}).")
    r.table("s1", "Historias del Sprint 1 y su resultado", ["HU", "SP", "Qué se construyó", "Verificación", "Estado"], [
        ("Base", "—", "Backend Django con GeoDjango, JWT y aislamiento por empresa (RN-13); panel con sesión segura y cliente tipado de la API", "Pruebas de autenticación, tope de sesión de 12 h y concurrencia en la renovación", "Integrado"),
        ("HU-03", "8", "Listado, detalle, creación, edición y cancelación de reservas; máquina de estados con historial y auditoría; geocodificador detrás de adaptador; horas en America/Santiago con cambio de horario", "CP-05, CP-06; horas inexistentes y repetidas del cambio de horario", "En revisión"),
        ("HU-19", "8", "Portal público */solicitar/<empresa>* sin cuenta, con aviso de privacidad, límite de 3 solicitudes por número cada 15 min y anticipación mínima (DC-10)", "CP-08, CP-09; expiración a los 15 min (RN-06)", "En revisión"),
        ("HU-10", "8", "Vehículos y conductores desde el panel y por CSV; cuentas con contraseña temporal de 14 caracteres, cambio obligatorio y vencimiento a 72 h (DC-14); auditoría (DC-13)", "CP-01, CP-02; la contraseña temporal no aparece en logs, base ni navegador", "En revisión"),
        ("HU-13", "8", "Inicio y fin del turno en la app con selector de vehículo (RN-05) y consentimiento (RN-18); el GPS sigue al turno", "CP-03, CP-04; el panel refleja el cambio en vivo", "En revisión"),
        ("HU-17", "3", "Botones para abrir Google Maps o Waze hacia la recogida o, con el pasajero a bordo, hacia el destino", "Casos de la HU; botones ≥ 44 px", "En revisión"),
        ("HU-20", "5", "Verificación del pasajero por WhatsApp con botones Confirmar/Cancelar; webhooks firmados e idempotentes; adaptador Twilio", "CP-07 a CP-10 con un doble de Twilio", "En revisión"),
        ("HU-26", "5", "Consulta del vuelo a la API al registrarlo: rechaza vuelos inexistentes, corrige la hora y marca «sin verificar» si la API no responde", "CP-11 con respuestas simuladas de FlightAware", "En revisión"),
        ("App base", "—", "Login con sesión en el almacén cifrado de Android, cambio de contraseña temporal y envío del GPS que sobrevive al vencimiento del token", "Emulador: 4 min con pantalla apagada sin huecos de posición", "En revisión"),
    ], [1.4, 0.8, 7.0, 4.8, 2.0], font=7.6)
    r.figure(IMG + "HU-10_conductores-escritorio.png", "imp_flota", "Panel: listado de conductores con el estado de sus cuentas (HU-10)", width_cm=14.5,
             source="Captura del sistema con datos sintéticos.")
    r.figure(IMG + "HU-26_panel-vuelo-verificado.png", "imp_vuelo", "Panel: reserva desde el aeropuerto con el vuelo verificado contra la API (HU-26)", width_cm=14.5,
             source="Captura del sistema con datos sintéticos.")
    r.figure(IMG + "HU-20_panel-confirmada-por-whatsapp.png", "imp_wa", "Panel: historial de una solicitud confirmada por el pasajero en WhatsApp (HU-20)", width_cm=14.5,
             source="Captura del sistema con datos sintéticos.")
    r.figure(IMG + "app_montaje1.png", "imp_app1", "App del conductor: consentimiento, aceptación con cuenta regresiva y viaje en curso (HU-13, HU-15, HU-17)", width_cm=15.5,
             source="Capturas del sistema con datos sintéticos.")

    # ------------------------------------------------------------------ 7.4
    r.H2("Incremento del Sprint 2")
    r.P("El Sprint 2 comprometió **45 SP** y también los completó: el mapa en tiempo real, el ciclo completo del viaje en la app, los avisos al "
        "pasajero y la calificación ({T:s2}). Además se resolvieron tres correcciones y dos tareas técnicas detectadas durante la construcción.")
    r.table("s2", "Historias y tareas del Sprint 2", ["HU", "SP", "Qué se construyó", "Verificación", "Estado"], [
        ("HU-02", "13", "Mapa del panel con los conductores en turno por WebSocket; ficha con nombre, patente y estado; posición «no confiable» sobre 60 s", "Latencia p95 = **59 ms** en local (meta < 5 s); 12 pruebas de WebSocket con aislamiento por empresa", "En revisión"),
        ("HU-14", "8", "El despachador asigna desde el panel (RN-01 a RN-03) y la app recibe el aviso con sonido, vibración y notificación", "El aviso llegó **362 ms** después de asignar", "En revisión"),
        ("HU-15", "8", "Aceptar o rechazar en 60 s; sin respuesta, la reserva vuelve a SOLICITADO y la asignación queda EXPIRADA (RN-04)", "Expiración observada a los 58–64 s", "En revisión"),
        ("HU-16", "8", "Estados secuenciales en la app; EN_ZONA automático por geocerca de 150 m con posiciones de precisión ≤ 50 m (DC-16); pago obligatorio (RN-10)", "CP-15, CP-16; la app mostró EN_ZONA en 205 ms", "En revisión"),
        ("HU-21", "5", "Avisos de confirmación, conductor asignado, en camino y «tu vehículo te espera»; cancelación por WhatsApp solo sin conductor (RN-09, DC-18)", "CP-16, CP-17 con el notificador de desarrollo", "En revisión"),
        ("HU-24", "3", "Encuesta opcional de 1 a 5 por WhatsApp al finalizar; nota asociada al viaje y al conductor (RN-14, DC-19)", "Casos de la HU; parcial aceptado: el promedio por conductor se verá en HU-06", "En revisión"),
        ("Estado en vivo", "—", "El listado de conductores recibe los cambios de estado por el canal en vivo (cierra PR-07)", "86 a 1.386 ms", "En revisión"),
        ("DC-20", "—", "La llegada indicada a mano queda marcada con la distancia al origen y se ve en el historial", "Prueba manual a 444 m del origen", "Subida"),
        ("Peticiones de la app", "—", "Tiempo límite de 10 s y relectura del viaje tras cada acción", "Sin la corrección fallan 4 de 7 pruebas; con ella, la pantalla se corrigió en 226 ms", "Subida"),
        ("Celery", "—", "Worker y beat: WhatsApp, vuelos y expiraciones como tareas con reintento exponencial", "Respuesta al conductor de ≈ 3 s a ≈ 50 ms con Twilio lento", "Subida"),
        ("Mapa Google", "—", "Adaptador de Google Maps con clave por entorno; sin clave, mapa esquemático", "Probado con un doble de la API", "Subida"),
    ], [1.9, 0.8, 6.6, 4.8, 1.9], font=7.6)
    r.figure(IMG + "HU-02_panel-mapa-escritorio.png", "imp_mapa", "Panel: mapa en tiempo real de los conductores en turno (HU-02)", width_cm=14.5,
             source="Captura del sistema con datos sintéticos; mapa esquemático de desarrollo.")
    r.figure(IMG + "app_montaje2.png", "imp_app2", "App del conductor: viaje desde el aeropuerto, llegada por geocerca y pago (HU-14, HU-16)", width_cm=15.5,
             source="Capturas del sistema con datos sintéticos.")
    r.figure(IMG + "fix-dc17_panel-llegada-manual-escritorio.png", "imp_dc17", "Panel: historial completo de un viaje con la llegada indicada a mano y su distancia (DC-17 y DC-20)", width_cm=14.5,
             source="Captura del sistema con datos sintéticos.")
    r.figure(IMG + "HU-24_panel-calificacion-escritorio.png", "imp_calif", "Panel: ficha de un viaje finalizado con la calificación del pasajero (HU-24)", width_cm=14.5,
             source="Captura del sistema con datos sintéticos.")
    r.P("La conversación registrada en MENSAJE_WHATSAPP durante la prueba de HU-21 muestra el ciclo completo de avisos al pasajero: confirmación de "
        "la reserva, intento de cancelación rechazado porque ya había conductor (RN-09), conductor asignado con vehículo y patente, «va en camino» "
        "y «tu vehículo te espera».")

    # ------------------------------------------------------------------ 7.5
    r.H2("Incremento del Sprint 3")
    r.P("El Sprint 3 comprometió **42 SP** y los completó: el despacho asistido y el foco aeropuerto, que es el diferenciador del producto, más "
        "la administración de convenios ({T:s3}). Con él, una recogida en el aeropuerto se asigna al primer conductor de la fila virtual y su "
        "hora se ajusta según el vuelo real, siempre con la confirmación del despachador (RN-02).")
    r.table("s3", "Historias del Sprint 3 y su resultado", ["HU", "SP", "Qué se construyó", "Verificación", "Estado"], [
        ("HU-04", "8", "Sugerencia del conductor más apto: ordena por distancia (PostGIS) y, con menos de 1 km de diferencia, por tiempo sin viaje; propone a uno y deja al resto en un desplegable; descarta posiciones antiguas o imprecisas; nunca asigna sin confirmación", "CP-18: 12 comprobaciones conformes; la asignación queda como DISTANCIA o MANUAL", "En revisión"),
        ("HU-29", "8", "Fila virtual del aeropuerto: el conductor entra al llegar a la geocerca estando Disponible, con posiciones precisas; sale tras 10 min sin posiciones en la zona, al quedar No disponible o al ser asignado; si rechaza vuelve al final (DC-21); el panel propone al primero y el conductor ve su lugar", "CP-19 y CP-20; al asignar al primero, la app del segundo pasó a «Eres el primero» en 7 ms. Sin probar con GPS real", "En revisión"),
        ("HU-27", "8", "Monitoreo del vuelo: consultas desde 3 h antes, cada 30 min y cada 10 min en la última hora; si la ETA cambia 15 min o más propone ETA + margen (20 min nacional, 35 internacional, según el código ICAO de origen, DC-22); el despachador confirma o descarta y queda en auditoría", "CP-21 con una API de vuelos simulada: 17 comprobaciones conformes. Falta FlightAware real; el aviso al pasajero queda pendiente (PR-14)", "En revisión"),
        ("HU-28", "5", "Alertas de demora, cancelación o desvío: visuales y sonoras en todo el panel, registradas en ALERTA_VUELO (DC-23) y con la reserva marcada hasta que se atiende; alerta «sin datos» si la API no responde", "CP-21: alerta visible a los 10,9 s. El sonido se comprobó por código, no en un equipo con altavoz", "En revisión"),
        ("HU-11", "13", "Convenios: token de 256 bits para el link, contraseña generada por el servidor que se muestra una sola vez y se rota (DC-24), activar y desactivar sin borrar el historial (RN-08), auditoría y volumen de reservas", "CP-22: 11 comprobaciones conformes; el despachador recibe 403", "En revisión"),
    ], [1.4, 0.8, 7.2, 4.8, 1.8], font=7.6)
    r.figure(IMG + "HU-29_panel-fila.png", "imp_fila", "Panel: al asignar una recogida en el aeropuerto se propone al primero de la fila virtual (HU-04, HU-29)", width_cm=14.5,
             source="Captura del sistema con datos sintéticos.")
    r.figure(IMG + "HU-27_panel-propuesta.png", "imp_prop", "Panel: propuesta de nueva hora de recogida por el cambio del vuelo, pendiente de confirmar (HU-27)", width_cm=14.5,
             source="Captura del sistema con datos sintéticos y una API de vuelos simulada.")
    r.figure(IMG + "HU-28_panel-alerta.png", "imp_alerta", "Panel: alerta de vuelo visible sobre el listado de reservas (HU-28)", width_cm=14.5,
             source="Captura del sistema con datos sintéticos.")

    # ------------------------------------------------------------------ 7.6
    r.H2("Incremento del Sprint 4")
    r.P("El Sprint 4 (semanas 14 y 15) está **en curso**. Comprometió **46 SP**: el control de la operación (cierre forzado, reportes, "
        "auditoría e indicadores), el acceso de los convenios y el chat con el pasajero. Al corte, sus siete historias están construidas y en "
        "revisión ({T:s4}), con lo que quedan construidas las 25 historias del backlog validado. El avance se explica porque estas historias "
        "reutilizan lo construido en los sprints anteriores: los reportes usan las mismas consultas de la liquidación, la auditoría ya existía "
        "desde el Sprint 1 y el chat se apoya en los webhooks de HU-20. Lo que resta del sprint es la fusión de los pull requests y las "
        "correcciones de la EF2 (HU-31, HU-32 y CP-14).")
    r.table("s4", "Historias y ajustes del Sprint 4", ["HU", "SP", "Qué se construyó", "Verificación", "Estado"], [
        ("HU-05", "5", "Cierre o anulación forzada con el pasajero a bordo: anular exige motivo; cerrar exige motivo, método de pago y monto (RN-10, RN-11, DC-25); queda en auditoría, el conductor vuelve a Disponible y no se envía encuesta", "Casos de la HU. El aviso a la app se comprobó con una prueba automática, no con una app abierta", "En revisión"),
        ("HU-18", "5", "«Mi turno» en la app: viajes finalizados del turno actual o del último, los cerrados por la central marcados y totales por método de pago para rendir la caja (DC-26)", "Casos de la HU. Solo guarda el último turno: es el origen de la entidad TURNO (CC-12)", "En revisión"),
        ("HU-12", "5", "Auditoría de convenios en su ficha: quién, qué y cuándo, en solo lectura y sin credenciales (RN-12)", "CP-24: el modelo y un trigger impiden modificar o borrar; POST, PATCH y DELETE responden 405", "En revisión"),
        ("HU-25", "13", "Acceso de convenio por link con contraseña: la reserva queda con el convenio y sin verificación (RN-07); bloqueo de 15 min tras 5 intentos, en auditoría; sesión de 2 h sin uso en cookie httpOnly; desactivar corta el acceso al instante (RN-08); el supervisor declara que el pasajero autorizó los avisos (DC-27)", "CP-22 y CP-26: 18 comprobaciones conformes", "En revisión"),
        ("HU-30", "5", "Chat de WhatsApp en el panel: bandeja por pasajero con su reserva; texto libre dentro de las 24 h y campo deshabilitado fuera de ellas; cada mensaje queda con su autor y las fallas de envío se ven", "CP-27 con un doble de Twilio; los mensajes nuevos aparecen en 5 a 15 s", "En revisión"),
        ("HU-01", "5", "Panel de indicadores: reservas del día por estado y vehículos en línea con señal, en línea sin señal y fuera de línea (DC-28), actualizado por WebSocket", "Cambios visibles en 10 a 68 ms en local; perder la señal tarda hasta 75 s en verse", "En revisión"),
        ("HU-06", "8", "Reportes: liquidación por conductor y método con los cierres forzados identificados, facturación por convenio, cancelaciones por origen e historial con calificación; filtros, totales y CSV (DC-29)", "CP-25: totales iguales a los esperados; el CSV neutraliza fórmulas", "En revisión"),
        ("Ajustes del PO", "—", "Señal separada en los indicadores (HU-01), declaración del supervisor y desbloqueo auditado (HU-25), y navegación con la dirección escrita mientras no haya geocodificador real (HU-17, DC-30)", "Suites completas en verde: 1.066, 591 y 89", "Subidos"),
    ], [1.6, 0.8, 7.0, 4.8, 1.8], font=7.6)
    r.figure(IMG + "HU-05_panel-dialogo.png", "imp_cierre", "Panel: cierre forzado de un viaje con motivo, método de pago y monto (HU-05)", width_cm=14.5,
             source="Captura del sistema con datos sintéticos.")
    r.figure(IMG + "HU-06_panel-liquidacion.png", "imp_liq", "Panel: liquidación por conductor y método de pago, con los cierres forzados identificados (HU-06)", width_cm=14.5,
             source="Captura del sistema con datos sintéticos.")
    r.figure(IMG + "HU-01_panel-indicadores.png", "imp_ind", "Panel: indicadores del día y de la flota, con la señal de los vehículos (HU-01)", width_cm=14.5,
             source="Captura del sistema con datos sintéticos.")
    r.figure(IMG + "HU-30_panel-hilo.png", "imp_chat", "Panel: conversación de WhatsApp con un pasajero dentro de la ventana de 24 horas (HU-30)", width_cm=14.5,
             source="Captura del sistema con datos sintéticos y el notificador de desarrollo.")
    r.figure(IMG + "app_montaje3.png", "imp_app3", "Acceso de un convenio por link, lugar del conductor en la fila del aeropuerto y «Mi turno» (HU-25, HU-29, HU-18)", width_cm=16.0,
             source="Capturas del sistema con datos sintéticos, en un navegador con ancho de celular (390 px).")
    r.P("**Relación con las observaciones de la EF2.** HU-18 dejó a la vista el límite que señaló el académico guía: el turno se guarda como dos "
        "columnas del conductor y solo se conserva el último, por lo que no hay historial ni un registro de lo rendido. Los totales por método "
        "de pago de «Mi turno» y la liquidación de HU-06 son la mitad del proceso P3.2; la otra mitad, comparar ese total con el efectivo que "
        "entrega el conductor y dejar constancia de la diferencia, es lo que agregan las entidades TURNO y CIERRE_CAJA con la historia HU-31.")

    # ------------------------------------------------------------------ 7.7
    r.H2("Calidad, defectos y pendientes")
    r.P("La {T:evol} muestra cómo creció la red de pruebas automáticas con cada historia; ninguna historia se cerró con pruebas en rojo y la "
        "cobertura se mantuvo muy por encima del 70 % exigido (RNF-11).")
    r.table("evol", "Evolución de las pruebas automáticas", ["Corte", "Backend (pytest)", "Panel web (Vitest)", "App (Vitest)"], [
        ("HU-10", "504 · 98,5 %", "438 · 94,4 %", "—"),
        ("App base", "519 · 99 %", "438", "28 · 87 %"),
        ("HU-13", "535 · 99 %", "439 · 94,4 %", "29 · 87 %"),
        ("HU-26 / HU-20", "564–586 · 98–99 %", "441 · 94,4 %", "31"),
        ("HU-02", "598 · 99 %", "451 · 94,5 %", "31"),
        ("HU-14 / HU-15", "611–624 · 98 %", "455–462 · 94,4 %", "37 · 87,7 %"),
        ("HU-16 / HU-21 / HU-24", "652–705 · 98 %", "462–464 · 94,4 %", "51 · 87,9 %"),
        ("Peticiones de la app", "711", "464", "71 · 95,3 %"),
        ("Celery (cierre del Sprint 2)", "727 · 98 %", "464 · 94,4 %", "71 · 95,3 %"),
        ("HU-04 / HU-29", "741–769 · 98 %", "486–488 · 94,7 %", "72 · 95,3 %"),
        ("HU-27 / HU-28", "818–840 · 98 %", "493–503 · 94,9 %", "72"),
        ("HU-11 (cierre del Sprint 3)", "866 · 98 %", "520 · 94,4 %", "72 · 95,3 %"),
        ("HU-05 / HU-18 / HU-12", "909–935 · 98 %", "532–539 · 94,3 %", "80 · 95,3 %"),
        ("HU-25 / HU-30 (Sprint 4)", "967–988 · 98 %", "552–565 · 94,4 %", "80"),
        ("HU-01 / HU-06", "1.006–1.043 · 98 %", "572–588 · 94,4 %", "80"),
        ("Ajustes del PO (corte, semana 14)", "**1.066 · 98,1 %**", "**591 · 94,4 %**", "**89**"),
    ], [4.0, 4.2, 4.2, 4.2], font=8.2)
    r.P("Las pruebas manuales contra el backend real encontraron defectos que las automáticas no cubrían; todos se corrigieron y quedaron con una "
        "prueba que los reproduce ({T:defectos}).")
    r.table("defectos", "Defectos encontrados durante la construcción", ["Defecto", "Severidad", "Causa", "Corrección"], [
        ("La pantalla de la app quedó en «Aceptado» 30 s tras «Voy en camino» (1 de 3 recorridos)", "Alta", "Una lectura sin tiempo límite quedó colgada", "Tiempo límite de 10 s, relectura tras cada acción y evento del canal en vivo"),
        ("Cancelar un viaje en curso dejaba al conductor «En viaje» para siempre", "Alta", "Faltaba liberar al conductor al cancelar", "El conductor vuelve a Disponible y la app se entera"),
        ("La asociación conductor-vehículo marcaba el día siguiente después de las 21:00", "Media", "Se usaba la fecha UTC en vez de la de Chile", "Fecha local de America/Santiago"),
        ("Posible bloqueo entre transacciones al renovar la sesión", "Media", "Bloqueo de fila más fuerte de lo necesario", "Bloqueo FOR NO KEY UPDATE"),
        ("El servicio de expiración no corría en el ambiente local", "Media", "Imagen del servicio desactualizada", "Comparte la imagen del backend; luego reemplazado por Celery beat"),
        ("Un error inesperado al avisar por WhatsApp rompía la respuesta de la API", "Media", "El registro del error pedía el nombre de una función parcial", "Manejo del error y prueba automática"),
        ("Las primeras pruebas de Celery enviaron tareas al worker de desarrollo", "Baja", "Configuración de pruebas sin modo *eager*", "Configuración de pruebas propia; se limpiaron 2 mensajes simulados y 4 vuelos; ningún mensaje salió por Twilio"),
        ("Quien salía de la fila del aeropuerto seguía viendo su lugar en la app (HU-29)", "Media", "El aviso solo llegaba a los conductores que seguían en la fila", "Aviso también a quien sale, con su prueba automática"),
        ("Los botones de Google Maps y Waze llevaban a un punto equivocado (HU-17)", "Media", "El geocodificador de desarrollo genera coordenadas aproximadas a partir del texto", "Mientras no haya geocodificador real, se navega con la dirección escrita (DC-30)"),
        ("«Salir» del acceso de convenio no cerraba la sesión (HU-25)", "Media", "Una respuesta 204 sin cuerpo se trataba como error", "Manejo de la respuesta vacía y prueba automática"),
        ("Errores 500 por unos minutos en el ambiente de desarrollo (HU-18, HU-25)", "Media", "Se editó un modelo antes de aplicar su migración y el código montado se recargó solo", "La migración se aplica en el mismo paso que la edición"),
        ("Al cambiar de reporte se veían un instante los datos del anterior (HU-06)", "Baja", "Se conservaban los datos previos entre reportes distintos", "Solo se conservan dentro del mismo reporte; prueba que falla si reaparece"),
        ("Dos pruebas de formularios fallaban a veces (origen del fallo intermitente de HU-24)", "Baja", "Superaban el límite de 5 s con la máquina cargada", "Límite de 20 s para esas pruebas"),
    ], [5.0, 1.6, 4.4, 5.6], font=7.8)
    r.P("Durante la construcción se tomaron **30 decisiones de cambio** respecto del diccionario de datos (DC-01 a DC-30), todas registradas con su "
        "motivo y aprobadas por el Product Owner (Anexo D). Las de mayor efecto en la operación son DC-14 (contraseña temporal), DC-16 (precisión "
        "de 50 m para la geocerca), DC-17 y DC-20 (llegada manual con trazabilidad), DC-21 (reglas de la fila), DC-22 (vuelo nacional o "
        "internacional según el código ICAO), DC-25 (reglas del cierre forzado), DC-27 (bloqueo del link y declaración del supervisor) y DC-28 "
        "(qué es un vehículo en línea). Lo que falta para cerrar el proyecto se resume en la {T:pend_prod}.")
    r.table("pend_prod", "Pendientes para el paso a producción", ["Código", "Pendiente", "Efecto si no se resuelve", "Plan"], [
        ("Fusión", "Abrir y fusionar los cuatro pull requests, uno por sprint", "Las 25 historias siguen «En revisión» y la integración continua no ha corrido sobre estas ramas", "Semana 14, en el orden del plan de fusión"),
        ("HU-31 · CC-12", "Entidades TURNO y CIERRE_CAJA y pantalla de cierre de caja", "KPI-05 no se puede medir y P3.2 queda a medias", "Sprint 4, semanas 14–15 (5 SP); CP-36"),
        ("HU-32 · CC-15", "Reserva de contingencia con canal CONTINGENCIA y conciliación por folio", "Los viajes anotados durante una caída no vuelven al sistema de forma trazable", "Sprint 4, semanas 14–15 (3 SP); CP-37"),
        ("CP-14", "Prueba de asignación con simultaneidad real", "El bloqueo está construido, pero sin evidencia de concurrencia", "Sprint 4, semana 14"),
        ("Despliegue", "Producción y staging en AWS; carga, estrés, seguridad y recuperación", "RNF-02, RNF-03 y RNF-08 solo están verificados en local", "Semana 15; CP-28 a CP-31"),
        ("PR-11", "Cuenta de Twilio, número de WhatsApp aprobado y **plantillas aprobadas por Meta**", "Fuera de la ventana de 24 h (por ejemplo, una reserva telefónica de un pasajero que nunca escribió) los avisos no llegan", "Crear y aprobar las plantillas de verificación, avisos y encuesta antes de la UAT"),
        ("PR-09", "Clave de FlightAware AeroAPI", "Los vuelos se validan con el consultor de desarrollo", "Contratar y probar con la clave real (≈ USD 30/mes)"),
        ("PR-12", "Clave de Google Maps restringida por dominio", "El panel usa el mapa esquemático", "Crear la clave con restricción de dominio"),
        ("Guía E–H", "Prueba en teléfono real: selector de vehículo, navegación, geocerca y fila con GPS real, sonido, notificación y «Mi turno»", "La geolocalización solo está probada en emulador y con posiciones simuladas; H-3 sigue «En curso»", "Semana 14, con el teléfono de pruebas"),
        ("PR-14", "Aviso al pasajero cuando cambia la hora de recogida por el vuelo", "El despachador confirma la nueva hora, pero el pasajero no se entera por WhatsApp", "Plantilla aprobada por Meta, junto con PR-11"),
        ("PR-13", "Aviso con la app cerrada (push por Firebase)", "Si el conductor cerró la app no recibe el viaje; la asignación vence a los 60 s", "Evaluar como solicitud de cambio"),
        ("PR-04", "Texto definitivo del aviso de privacidad", "El portal muestra un texto marcado como provisional", "Redactar y validar con el cliente"),
    ], [1.6, 5.0, 5.4, 4.6], font=7.8)

    # ------------------------------------------------------------------ 7.8
    r.H2("Consideraciones éticas y jurídicas en la implementación")
    r.P("La implementación aplica los compromisos legales y éticos declarados en el diseño (sección 6.2):")
    r.bullets([
        "**Datos sintéticos:** todo el desarrollo y las pruebas usan datos generados; ninguna evidencia contiene datos de personas reales.",
        "**Consentimiento y minimización (Ley N° 21.719, RN-18):** el conductor acepta un aviso que explica qué se registra, cuándo, quién lo ve y "
        "por cuánto tiempo (Figura {F:imp_app1|n}a); la ubicación se registra solo en turno y se detiene al terminarlo.",
        "**Aislamiento entre empresas (RN-13):** cada consulta y cada canal en vivo filtran por empresa; un usuario de otra empresa recibe 404 y no "
        "ve posiciones ajenas.",
        "**Credenciales:** contraseñas con PBKDF2; la contraseña temporal se muestra una sola vez y se verificó que no queda en logs, auditoría, "
        "base de datos ni navegador; las claves de servicios externos viven en variables de entorno y nunca se versionan.",
        "**Trazabilidad:** toda transición de estado guarda actor, usuario y hora, y las acciones sensibles quedan en una auditoría de solo inserción "
        "(RN-12, RNF-10).",
        "**Autorización de avisos en convenios (DC-27):** el supervisor no puede aceptar por el pasajero sin más; debe declarar expresamente que "
        "el pasajero autorizó recibir avisos por WhatsApp, y la declaración queda registrada con su nombre y la fecha.",
        "**Propiedad intelectual (Ley N° 17.336):** el cliente recibe una licencia de uso y sus datos siguen siendo suyos; el código no se cede.",
        "**Honestidad de la evidencia:** cada resultado indica qué se probó con servicios reales y qué con dobles o en emulador, y los fallos "
        "intermitentes se registran aunque no se haya encontrado su causa.",
    ])
