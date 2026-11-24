"""PASAJERO, VIAJE e HISTORIAL_ESTADO, según docs/diccionario-datos.md."""

from django.contrib.gis.db import models as gis
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now

from apps.comun.validadores import validar_no_vacio, validar_rut, validar_telefono_e164, validar_vuelo_iata


class Pasajero(models.Model):
    """El pasajero no tiene cuenta; se identifica por su WhatsApp, único dentro de cada empresa.

    DC-50 (HU-45): al eliminar su cuenta queda anonimizado, con `telefono` NULL y el nombre
    «Pasajero eliminado».
    La unicidad por empresa sigue valiendo para los teléfonos no nulos (PostgreSQL no compara NULL).
    """

    NOMBRE_ELIMINADO = "Pasajero eliminado"

    empresa = models.ForeignKey("cuentas.Empresa", on_delete=models.PROTECT, related_name="pasajeros")
    nombre = models.CharField(max_length=80, validators=[validar_no_vacio])
    telefono = models.CharField(max_length=16, null=True, blank=True, validators=[validar_telefono_e164])
    verificado_en = models.DateTimeField(null=True, blank=True)
    opt_in_en = models.DateTimeField(null=True, blank=True)
    # DC-11: evidencia de la aceptación del aviso de privacidad en el portal (HU-19).
    privacidad_aceptada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pasajero"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "telefono"], name="pasajero_telefono_unico_por_empresa"
            ),
            models.CheckConstraint(condition=~Q(nombre=""), name="pasajero_nombre_no_vacio"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.telefono})"


class EstadoViaje(models.TextChoices):
    PENDIENTE_CONFIRMACION = "PENDIENTE_CONFIRMACION", "Pendiente de confirmación"
    SOLICITADO = "SOLICITADO", "Solicitado"
    ASIGNADO = "ASIGNADO", "Asignado"
    ACEPTADO = "ACEPTADO", "Aceptado"
    EN_CAMINO = "EN_CAMINO", "En camino"
    EN_ZONA = "EN_ZONA", "En zona"
    PASAJERO_A_BORDO = "PASAJERO_A_BORDO", "Pasajero a bordo"
    FINALIZADO = "FINALIZADO", "Finalizado"
    CANCELADO = "CANCELADO", "Cancelado"


class Canal(models.TextChoices):
    WEB = "WEB", "Portal web"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    TELEFONO = "TELEFONO", "Teléfono"
    CONVENIO = "CONVENIO", "Convenio"
    # DC-33 (HU-32): viajes anotados durante una caída del sistema e ingresados después.
    CONTINGENCIA = "CONTINGENCIA", "Contingencia"


class Sentido(models.TextChoices):
    DESDE_AEROPUERTO = "DESDE_AEROPUERTO", "Desde el aeropuerto"
    HACIA_AEROPUERTO = "HACIA_AEROPUERTO", "Hacia el aeropuerto"
    URBANO = "URBANO", "Urbano"


class TipoVuelo(models.TextChoices):
    """HU-39: tipo del vuelo de salida (define la antelación sugerida de la recogida)."""

    NACIONAL = "NACIONAL", "Nacional"
    INTERNACIONAL = "INTERNACIONAL", "Internacional"


# DC-43: un viaje lleva a lo más la capacidad del vehículo más grande (CHECK de VEHICULO: 1 a 7).
MAX_PASAJEROS = 7


class OrigenCancelacion(models.TextChoices):
    PASAJERO = "PASAJERO", "Pasajero"
    DESPACHADOR = "DESPACHADOR", "Despachador"
    # DC-08: agregado al dominio del Anexo D, igual que en HISTORIAL_ESTADO.actor (DC-03).
    ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
    SUPERVISOR = "SUPERVISOR", "Supervisor de convenio"
    SISTEMA = "SISTEMA", "Sistema"
    # DC-59 (HU-60): la reserva pública que nadie confirmó (se cierra 2 h después de la recogida) y la que el
    # contacto del convenio rechazó. KPI-01 (reservas perdidas) no las cuenta.
    NO_CONFIRMADA = "NO_CONFIRMADA", "No confirmada"
    CONVENIO = "CONVENIO", "Rechazada por el convenio"


class Viaje(models.Model):
    empresa = models.ForeignKey("cuentas.Empresa", on_delete=models.PROTECT, related_name="viajes")
    pasajero = models.ForeignKey(Pasajero, on_delete=models.PROTECT, related_name="viajes")
    convenio = models.ForeignKey(
        "convenios.Convenio", on_delete=models.PROTECT, null=True, blank=True, related_name="viajes"
    )
    conductor = models.ForeignKey(
        "flota.Conductor", on_delete=models.PROTECT, null=True, blank=True, related_name="viajes"
    )
    vehiculo = models.ForeignKey(
        "flota.Vehiculo", on_delete=models.PROTECT, null=True, blank=True, related_name="viajes"
    )
    # HU-31 (CC-12): turno en que el conductor aceptó el viaje. Lo fija la aceptación, no el cierre: un cierre
    # forzado (HU-05) queda en el turno correcto aunque ocurra después de terminado.
    turno = models.ForeignKey(
        "flota.Turno", on_delete=models.PROTECT, null=True, blank=True, related_name="viajes"
    )
    canal = models.CharField(max_length=12, choices=Canal.choices)
    # DC-33 (HU-32): folio de la hoja de contingencia; único por empresa y obligatorio con ese canal.
    folio_contingencia = models.CharField(max_length=20, null=True, blank=True)
    sentido = models.CharField(
        max_length=16, choices=Sentido.choices, default=Sentido.URBANO, db_default=Sentido.URBANO
    )
    origen_dir = models.CharField(max_length=200, validators=[validar_no_vacio])
    origen_geo = gis.PointField(geography=True, srid=4326)
    destino_dir = models.CharField(max_length=200, validators=[validar_no_vacio])
    destino_geo = gis.PointField(geography=True, srid=4326)
    recogida_en = models.DateTimeField()
    estado = models.CharField(
        max_length=22,
        choices=EstadoViaje.choices,
        default=EstadoViaje.PENDIENTE_CONFIRMACION,
        db_default=EstadoViaje.PENDIENTE_CONFIRMACION,
    )
    tarifa = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    # DC-42 (HU-39): titular más acompañantes y equipaje declarados al pedir.
    pasajeros = models.PositiveSmallIntegerField(
        default=1, db_default=1, validators=[MinValueValidator(1), MaxValueValidator(MAX_PASAJEROS)]
    )
    maletas = models.PositiveSmallIntegerField(default=0, db_default=0, validators=[MaxValueValidator(20)])
    # DC-42 (HU-39): vuelo de salida en los viajes al aeropuerto. Solo se guarda; no se monitorea.
    vuelo_salida_en = models.DateTimeField(null=True, blank=True)
    vuelo_salida_tipo = models.CharField(max_length=13, choices=TipoVuelo.choices, null=True, blank=True)
    # HU-69 (DC-69): número del vuelo de salida, opcional; tampoco se monitorea.
    vuelo_salida_numero = models.CharField(
        max_length=8, null=True, blank=True, validators=[validar_vuelo_iata]
    )
    motivo_cancelacion = models.CharField(max_length=200, null=True, blank=True)
    origen_cancelacion = models.CharField(
        max_length=14, choices=OrigenCancelacion.choices, null=True, blank=True
    )
    # DC-27: el supervisor declara que el pasajero autorizó los avisos. No tiene cuenta: se guarda su nombre.
    autorizacion_avisos_en = models.DateTimeField(null=True, blank=True)
    autorizacion_avisos_supervisor = models.CharField(max_length=80, null=True, blank=True)
    # DC-35 (HU-34): desde las cuentas de convenio la declaración queda ligada al usuario que reserva.
    # El nombre escrito (DC-27) se conserva solo en las reservas hechas con el link anterior.
    autorizacion_avisos_por = models.ForeignKey(
        "cuentas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # DC-52 (CC-22): reserva del formulario público. El correo de contacto vive en el viaje (el PASAJERO sigue
    # identificado por su teléfono); la empresa sin convenio se cobra como particular.
    contacto_correo = models.EmailField(max_length=254, null=True, blank=True)
    privacidad_version = models.CharField(max_length=20, null=True, blank=True)
    empresa_cliente_razon_social = models.CharField(max_length=120, null=True, blank=True)
    empresa_cliente_rut = models.CharField(max_length=12, null=True, blank=True, validators=[validar_rut])
    empresa_cliente_contacto = models.CharField(max_length=80, null=True, blank=True)
    # DC-53: hasta cuándo vale el enlace de confirmación; después la reserva queda «Sin confirmar».
    confirmar_hasta = models.DateTimeField(null=True, blank=True)
    # DC-52 (HU-54): la confirma el contacto del convenio (el correo que reservó no está autorizado).
    confirma_convenio = models.BooleanField(default=False, db_default=False)
    # DC-59 (HU-60): quién autorizó por el convenio y cuándo (no es un PASAJERO).
    autorizado_por_correo = models.EmailField(max_length=254, null=True, blank=True)
    autorizado_en = models.DateTimeField(null=True, blank=True)
    # CC-23 (DC-76): reserva con pase de convenio. El viaje queda a nombre de quien lo pide (solicitante, D7);
    # `pasajero` es quien viaja. Acompañantes del mismo vehículo: [{nombre, cargo, telefono, correo}] sin
    # padrón.
    # Vehículos separados: un viaje por persona con el mismo `grupo`, que se confirma con un solo enlace.
    solicitante_nombre = models.CharField(max_length=80, null=True, blank=True)
    solicitante_telefono = models.CharField(max_length=16, null=True, blank=True)
    pasajero_cargo = models.CharField(max_length=80, null=True, blank=True)
    pasajero_correo = models.EmailField(max_length=254, null=True, blank=True)
    acompanantes = models.JSONField(default=list, blank=True)
    grupo = models.UUIDField(null=True, blank=True, db_index=True)
    # El solicitante declaró que informó del aviso de privacidad a las personas que viajan (Ley 21.719).
    terceros_informados_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        db_table = "viaje"
        ordering = ["recogida_en", "id"]
        indexes = [
            models.Index(fields=["empresa", "recogida_en"], name="viaje_empresa_recogida_idx"),
            models.Index(fields=["empresa", "estado"], name="viaje_empresa_estado_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(estado__in=EstadoViaje.values), name="viaje_estado_valido"),
            models.CheckConstraint(condition=Q(canal__in=Canal.values), name="viaje_canal_valido"),
            models.CheckConstraint(condition=Q(sentido__in=Sentido.values), name="viaje_sentido_valido"),
            models.CheckConstraint(
                condition=Q(tarifa__isnull=True) | Q(tarifa__gte=0), name="viaje_tarifa_no_negativa"
            ),
            models.CheckConstraint(
                condition=Q(pasajeros__gte=1, pasajeros__lte=MAX_PASAJEROS), name="viaje_pasajeros_1_7"
            ),
            models.CheckConstraint(condition=Q(maletas__lte=20), name="viaje_maletas_max_20"),
            models.CheckConstraint(
                condition=Q(vuelo_salida_tipo__isnull=True) | Q(vuelo_salida_tipo__in=TipoVuelo.values),
                name="viaje_vuelo_salida_tipo_valido",
            ),
            models.CheckConstraint(
                condition=~Q(estado=EstadoViaje.CANCELADO)
                | (Q(motivo_cancelacion__isnull=False) & ~Q(motivo_cancelacion="")),
                name="viaje_cancelado_con_motivo",
            ),
            models.CheckConstraint(
                condition=Q(canal=Canal.CONVENIO, convenio__isnull=False)
                | (~Q(canal=Canal.CONVENIO) & Q(convenio__isnull=True)),
                name="viaje_convenio_segun_canal",
            ),
            models.CheckConstraint(
                condition=Q(canal=Canal.CONTINGENCIA, folio_contingencia__isnull=False)
                | (~Q(canal=Canal.CONTINGENCIA) & Q(folio_contingencia__isnull=True)),
                name="viaje_folio_segun_canal",
            ),
            models.UniqueConstraint(
                fields=["empresa", "folio_contingencia"],
                condition=Q(folio_contingencia__isnull=False),
                name="viaje_folio_unico_por_empresa",
            ),
        ]

    def __str__(self):
        return f"Viaje #{self.pk} ({self.estado})"


class Actor(models.TextChoices):
    CONDUCTOR = "CONDUCTOR", "Conductor"
    DESPACHADOR = "DESPACHADOR", "Despachador"
    # DC-03: agregado al dominio del Anexo D.
    ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
    PASAJERO = "PASAJERO", "Pasajero"
    SISTEMA = "SISTEMA", "Sistema"


class HistorialEstado(models.Model):
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name="historial")
    estado_anterior = models.CharField(max_length=22, choices=EstadoViaje.choices, null=True, blank=True)
    estado_nuevo = models.CharField(max_length=22, choices=EstadoViaje.choices)
    actor = models.CharField(max_length=14, choices=Actor.choices)
    usuario = models.ForeignKey(
        "cuentas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # DC-20: EN_ZONA indicado por el conductor (DC-17) y su distancia al origen en ese momento.
    manual = models.BooleanField(default=False, db_default=False)
    distancia_m = models.PositiveIntegerField(null=True, blank=True)
    # DC-33: transición registrada después, con la hora real anotada durante una caída (HU-32).
    contingencia = models.BooleanField(default=False, db_default=False)
    creado_en = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        db_table = "historial_estado"
        verbose_name = "historial de estado"
        verbose_name_plural = "historial de estados"
        ordering = ["creado_en", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(actor__in=Actor.values), name="historial_actor_valido"),
            models.CheckConstraint(
                condition=Q(estado_nuevo__in=EstadoViaje.values), name="historial_estado_valido"
            ),
        ]

    def __str__(self):
        return f"{self.estado_anterior or '—'} → {self.estado_nuevo} ({self.actor})"


class DireccionMensaje(models.TextChoices):
    ENTRANTE = "ENTRANTE", "Entrante"
    SALIENTE = "SALIENTE", "Saliente"


class TipoMensaje(models.TextChoices):
    PLANTILLA = "PLANTILLA", "Plantilla"
    SESION = "SESION", "Sesión"


class EstadoEntrega(models.TextChoices):
    QUEUED = "QUEUED", "En cola"
    SENT = "SENT", "Enviado"
    DELIVERED = "DELIVERED", "Entregado"
    READ = "READ", "Leído"
    FAILED = "FAILED", "Falló"


class MensajeWhatsapp(models.Model):
    """MENSAJE_WHATSAPP (Anexo D). Desde CC-19 (HU-67, DC-63) es un historial de solo lectura: el canal se
    retiró y ya no se agregan mensajes. `proveedor_sid` es el identificador que tenía el mensaje en el
    proveedor. Retención 12 meses (RN-15, HU-68)."""

    pasajero = models.ForeignKey(Pasajero, on_delete=models.CASCADE, related_name="mensajes")
    viaje = models.ForeignKey(
        Viaje, on_delete=models.SET_NULL, null=True, blank=True, related_name="mensajes"
    )
    direccion = models.CharField(max_length=8, choices=DireccionMensaje.choices)
    tipo = models.CharField(max_length=10, choices=TipoMensaje.choices)
    cuerpo = models.TextField(max_length=1024)
    proveedor_sid = models.CharField(max_length=40, unique=True, null=True, blank=True)
    estado_entrega = models.CharField(
        max_length=12,
        choices=EstadoEntrega.choices,
        default=EstadoEntrega.QUEUED,
        db_default=EstadoEntrega.QUEUED,
    )
    usuario = models.ForeignKey(
        "cuentas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    creado_en = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        db_table = "mensaje_whatsapp"
        verbose_name = "mensaje de WhatsApp"
        verbose_name_plural = "mensajes de WhatsApp"
        ordering = ["creado_en", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(direccion__in=DireccionMensaje.values), name="mensaje_direccion"
            ),
            models.CheckConstraint(condition=Q(tipo__in=TipoMensaje.values), name="mensaje_tipo"),
            models.CheckConstraint(
                condition=Q(estado_entrega__in=EstadoEntrega.values), name="mensaje_estado"
            ),
        ]

    def __str__(self):
        return f"{self.direccion} {self.tipo} #{self.pk}"


class OrigenSugerencia(models.TextChoices):
    FILA = "FILA", "Fila del aeropuerto"
    DISTANCIA = "DISTANCIA", "Distancia"
    MANUAL = "MANUAL", "Manual"


class ResultadoAsignacion(models.TextChoices):
    ACEPTADA = "ACEPTADA", "Aceptada"
    RECHAZADA = "RECHAZADA", "Rechazada"
    EXPIRADA = "EXPIRADA", "Expirada"


class Asignacion(models.Model):
    """ASIGNACION (Anexo D): cada vez que el despachador confirma un conductor para un viaje (RN-02). El
    conductor tiene 60 s para responder (RN-04, HU-15)."""

    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name="asignaciones")
    conductor = models.ForeignKey("flota.Conductor", on_delete=models.PROTECT, related_name="asignaciones")
    despachador = models.ForeignKey("cuentas.Usuario", on_delete=models.PROTECT, related_name="+")
    origen_sugerencia = models.CharField(max_length=10, choices=OrigenSugerencia.choices)
    enviada_en = models.DateTimeField(db_default=Now())
    respondida_en = models.DateTimeField(null=True, blank=True)
    resultado = models.CharField(max_length=10, choices=ResultadoAsignacion.choices, null=True, blank=True)

    class Meta:
        db_table = "asignacion"
        verbose_name = "asignación"
        verbose_name_plural = "asignaciones"
        ordering = ["-enviada_en", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(origen_sugerencia__in=OrigenSugerencia.values), name="asignacion_origen_valido"
            ),
            models.CheckConstraint(
                condition=Q(resultado__isnull=True) | Q(resultado__in=ResultadoAsignacion.values),
                name="asignacion_resultado_valido",
            ),
            # Una sola asignación esperando respuesta por viaje.
            models.UniqueConstraint(
                fields=["viaje"], condition=Q(resultado__isnull=True), name="asignacion_pendiente_unica"
            ),
        ]

    def __str__(self):
        return f"Viaje {self.viaje_id} → conductor {self.conductor_id}"


class MetodoPago(models.TextChoices):
    EFECTIVO = "EFECTIVO", "Efectivo"
    TARJETA = "TARJETA", "Tarjeta"
    TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
    CONVENIO = "CONVENIO", "Convenio"


MONTO_MAXIMO = 500_000


class PagoViaje(models.Model):
    """PAGO_VIAJE (Anexo D). RN-10: ningún viaje se finaliza sin método de pago y monto."""

    viaje = models.OneToOneField(Viaje, on_delete=models.PROTECT, related_name="pago")
    metodo = models.CharField(max_length=14, choices=MetodoPago.choices)
    monto = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(MONTO_MAXIMO)])
    registrado_en = models.DateTimeField(db_default=Now(), editable=False)
    corregido_por = models.ForeignKey(
        "cuentas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        db_table = "pago_viaje"
        verbose_name = "pago de viaje"
        verbose_name_plural = "pagos de viajes"
        constraints = [
            models.CheckConstraint(condition=Q(metodo__in=MetodoPago.values), name="pago_metodo_valido"),
            models.CheckConstraint(
                condition=Q(monto__gte=0, monto__lte=MONTO_MAXIMO), name="pago_monto_rango"
            ),
        ]

    def __str__(self):
        return f"Viaje {self.viaje_id}: {self.metodo} {self.monto}"


class Calificacion(models.Model):
    """CALIFICACION (Anexo D). RN-14: es opcional y no condiciona el cierre. El conductor es el del viaje."""

    viaje = models.OneToOneField(Viaje, on_delete=models.PROTECT, related_name="calificacion")
    puntaje = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    creado_en = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        db_table = "calificacion"
        verbose_name = "calificación"
        verbose_name_plural = "calificaciones"
        constraints = [
            models.CheckConstraint(
                condition=Q(puntaje__gte=1, puntaje__lte=5), name="calificacion_puntaje_rango"
            ),
        ]

    def __str__(self):
        return f"Viaje {self.viaje_id}: {self.puntaje}"


class CuentaPasajero(models.Model):
    """HU-35 (DC-36): cuenta web opcional del pasajero, por empresa.

    Se crea con el usuario inactivo y se activa con el enlace que llega al correo (24 h, DC-61). Recién ahí
    `pasajero` apunta al PASAJERO de ese teléfono en la empresa. El teléfono es un dato de contacto sin
    verificar: la cuenta ve solo los viajes que pidió ella (DC-65), salvo las cuentas confirmadas antes por
    WhatsApp. Eliminar la cuenta borra esta fila y anonimiza al usuario: el pasajero y sus reservas quedan
    como de invitado.
    """

    usuario = models.OneToOneField(
        "cuentas.Usuario", on_delete=models.PROTECT, related_name="cuenta_pasajero"
    )
    empresa = models.ForeignKey("cuentas.Empresa", on_delete=models.PROTECT, related_name="+")
    nombre = models.CharField(max_length=80, validators=[validar_no_vacio])
    telefono = models.CharField(max_length=16, validators=[validar_telefono_e164])
    pasajero = models.ForeignKey(
        Pasajero, on_delete=models.PROTECT, null=True, blank=True, related_name="cuentas"
    )
    confirmada_en = models.DateTimeField(null=True, blank=True)
    # DC-44 (Ley 21.719): aceptación única del aviso de privacidad y de los avisos por WhatsApp,
    # con la versión del aviso.
    privacidad_aceptada_en = models.DateTimeField(null=True, blank=True)
    # HU-41 (DC-45): último reenvío del WhatsApp de activación; la vigencia corre desde ahí.
    reenviada_en = models.DateTimeField(null=True, blank=True)
    # DC-65 (CC-19): el teléfono se confirmó por WhatsApp (cuentas anteriores a CC-19). Sin esa confirmación
    # la cuenta solo ve los viajes que pidió ella misma, no los de invitado con ese número.
    telefono_verificado = models.BooleanField(default=False, db_default=False)
    # DC-62 (HU-65): casilla de avisos del viaje por correo (conductor asignado, llegada y cancelación) cuando
    # no hay Web Push. Los correos de la cuenta (activación, recuperar la clave) salen siempre.
    acepta_avisos_correo = models.BooleanField(default=False, db_default=False)
    privacidad_version = models.CharField(max_length=20, null=True, blank=True)
    creada_en = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        db_table = "cuenta_pasajero"
        constraints = [
            # Un teléfono confirmado tiene a lo más una cuenta por empresa.
            models.UniqueConstraint(
                fields=["empresa", "telefono"],
                condition=Q(confirmada_en__isnull=False),
                name="cuenta_pasajero_telefono_unico",
            ),
            models.CheckConstraint(
                condition=Q(confirmada_en__isnull=True) | Q(pasajero__isnull=False),
                name="cuenta_pasajero_confirmada_con_pasajero",
            ),
        ]

    def __str__(self):
        return f"Cuenta de {self.nombre}"


class SuscripcionPush(models.Model):
    """DC-62 (HU-65): suscripción Web Push de un navegador del pasajero (con su aceptación del permiso).

    `endpoint` es la URL del servicio de push del navegador; `p256dh` y `auth` cifran el contenido (RFC 8291).
    Se borra al quitar el permiso, al eliminar la cuenta o cuando el servicio responde 404 o 410.
    """

    usuario = models.ForeignKey(
        "cuentas.Usuario", on_delete=models.CASCADE, related_name="suscripciones_push"
    )
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=100)
    auth = models.CharField(max_length=40)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "suscripcion_push"

    def __str__(self):
        return f"Push de {self.usuario_id}"
