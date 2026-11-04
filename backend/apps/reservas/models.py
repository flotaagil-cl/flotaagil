"""PASAJERO, VIAJE e HISTORIAL_ESTADO, según docs/diccionario-datos.md."""

from django.contrib.gis.db import models as gis
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now

from apps.comun.validadores import validar_no_vacio, validar_telefono_e164


class Pasajero(models.Model):
    """El pasajero no tiene cuenta; se identifica por su WhatsApp, único dentro de cada empresa."""

    empresa = models.ForeignKey("cuentas.Empresa", on_delete=models.PROTECT, related_name="pasajeros")
    nombre = models.CharField(max_length=80, validators=[validar_no_vacio])
    telefono = models.CharField(max_length=16, validators=[validar_telefono_e164])
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


class Sentido(models.TextChoices):
    DESDE_AEROPUERTO = "DESDE_AEROPUERTO", "Desde el aeropuerto"
    HACIA_AEROPUERTO = "HACIA_AEROPUERTO", "Hacia el aeropuerto"
    URBANO = "URBANO", "Urbano"


class OrigenCancelacion(models.TextChoices):
    PASAJERO = "PASAJERO", "Pasajero"
    DESPACHADOR = "DESPACHADOR", "Despachador"
    # DC-08: agregado al dominio del Anexo D, igual que en HISTORIAL_ESTADO.actor (DC-03).
    ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
    SUPERVISOR = "SUPERVISOR", "Supervisor de convenio"
    SISTEMA = "SISTEMA", "Sistema"


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
    canal = models.CharField(max_length=12, choices=Canal.choices)
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
    motivo_cancelacion = models.CharField(max_length=200, null=True, blank=True)
    origen_cancelacion = models.CharField(
        max_length=14, choices=OrigenCancelacion.choices, null=True, blank=True
    )
    # DC-27: el supervisor declara que el pasajero autorizó los avisos. No tiene cuenta: se guarda su nombre.
    autorizacion_avisos_en = models.DateTimeField(null=True, blank=True)
    autorizacion_avisos_supervisor = models.CharField(max_length=80, null=True, blank=True)
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
                condition=~Q(estado=EstadoViaje.CANCELADO)
                | (Q(motivo_cancelacion__isnull=False) & ~Q(motivo_cancelacion="")),
                name="viaje_cancelado_con_motivo",
            ),
            models.CheckConstraint(
                condition=Q(canal=Canal.CONVENIO, convenio__isnull=False)
                | (~Q(canal=Canal.CONVENIO) & Q(convenio__isnull=True)),
                name="viaje_convenio_segun_canal",
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
    """MENSAJE_WHATSAPP (Anexo D). `proveedor_sid` (el SID de Twilio) hace idempotentes los webhooks.
    Retención 12 meses (RN-15)."""

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
