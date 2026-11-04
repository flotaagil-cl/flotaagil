"""VUELO, GEOCERCA y FILA_AEROPUERTO, según docs/diccionario-datos.md. VUELO, solo para viajes
DESDE_AEROPUERTO (DC-06)."""

from django.contrib.gis.db import models as gis
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now

from apps.comun.validadores import validar_vuelo_iata


class EstadoVuelo(models.TextChoices):
    PROGRAMADO = "PROGRAMADO", "Programado"
    DEMORADO = "DEMORADO", "Demorado"
    ATERRIZADO = "ATERRIZADO", "Aterrizado"
    CANCELADO = "CANCELADO", "Cancelado"
    DESVIADO = "DESVIADO", "Desviado"


class Vuelo(models.Model):
    viaje = models.OneToOneField("reservas.Viaje", on_delete=models.CASCADE, related_name="vuelo")
    numero = models.CharField(max_length=8, validators=[validar_vuelo_iata])
    fecha = models.DateField()
    # Hora de llegada programada: la informa quien ingresa la reserva; HU-26 la valida (DC-06).
    hora_programada = models.DateTimeField()
    hora_estimada = models.DateTimeField(null=True, blank=True)
    estado_vuelo = models.CharField(
        max_length=12,
        choices=EstadoVuelo.choices,
        default=EstadoVuelo.PROGRAMADO,
        db_default=EstadoVuelo.PROGRAMADO,
    )
    ultima_consulta_en = models.DateTimeField(null=True, blank=True)
    # DC-22: monitoreo (HU-27). La propuesta no cambia la recogida hasta que el despachador confirma (RN-02).
    origen_icao = models.CharField(max_length=4, null=True, blank=True)
    eta_referencia = models.DateTimeField(null=True, blank=True)
    recogida_propuesta = models.DateTimeField(null=True, blank=True)
    propuesta_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vuelo"
        constraints = [
            models.CheckConstraint(
                condition=Q(estado_vuelo__in=EstadoVuelo.values), name="vuelo_estado_valido"
            ),
            models.CheckConstraint(
                condition=Q(numero__regex=r"^[A-Z0-9]{2} ?[0-9]{1,4}$"), name="vuelo_numero_iata"
            ),
        ]

    def __str__(self):
        return f"{self.numero} {self.fecha:%Y-%m-%d}"


class Geocerca(models.Model):
    """GEOCERCA (Anexo D). El polígono del aeropuerto es un supuesto configurable por empresa (DC-21)."""

    empresa = models.ForeignKey("cuentas.Empresa", on_delete=models.CASCADE, related_name="geocercas")
    nombre = models.CharField(max_length=60)
    poligono = gis.PolygonField(geography=True, srid=4326)

    class Meta:
        db_table = "geocerca"
        verbose_name = "geocerca"
        verbose_name_plural = "geocercas"

    def __str__(self):
        return self.nombre


class MotivoSalidaFila(models.TextChoices):
    ASIGNADO = "ASIGNADO", "Asignado"
    FUERA_ZONA = "FUERA_ZONA", "Fuera de la zona"
    NO_DISPONIBLE = "NO_DISPONIBLE", "No disponible"


class FilaAeropuerto(models.Model):
    """FILA_AEROPUERTO (Anexo D). RN-16: orden de ingreso a la geocerca."""

    geocerca = models.ForeignKey(Geocerca, on_delete=models.CASCADE, related_name="fila")
    conductor = models.ForeignKey("flota.Conductor", on_delete=models.CASCADE, related_name="entradas_fila")
    ingreso_en = models.DateTimeField(db_default=Now())
    salida_en = models.DateTimeField(null=True, blank=True)
    motivo_salida = models.CharField(max_length=14, choices=MotivoSalidaFila.choices, null=True, blank=True)

    class Meta:
        db_table = "fila_aeropuerto"
        verbose_name = "entrada a la fila"
        verbose_name_plural = "fila del aeropuerto"
        constraints = [
            models.UniqueConstraint(
                fields=["conductor"], condition=Q(salida_en__isnull=True), name="fila_una_entrada_abierta"
            ),
            models.CheckConstraint(
                condition=Q(salida_en__isnull=True, motivo_salida__isnull=True)
                | Q(salida_en__isnull=False, motivo_salida__in=MotivoSalidaFila.values),
                name="fila_salida_con_motivo",
            ),
        ]
        indexes = [models.Index(fields=["geocerca", "ingreso_en"], name="fila_orden")]

    def __str__(self):
        return f"{self.conductor} en {self.geocerca}"


class TipoAlertaVuelo(models.TextChoices):
    ETA_CAMBIADA = "ETA_CAMBIADA", "Cambió la llegada"
    VUELO_CANCELADO = "VUELO_CANCELADO", "Vuelo cancelado"
    VUELO_DESVIADO = "VUELO_DESVIADO", "Vuelo desviado"
    SIN_DATOS = "SIN_DATOS", "Sin datos de la API"


class AlertaVuelo(models.Model):
    """ALERTA_VUELO (DC-23): registro de las alertas de HU-28. Se conserva aunque se edite el vuelo. Con
    `atendida_en` y sin `atendida_por`, la resolvió el sistema."""

    empresa = models.ForeignKey("cuentas.Empresa", on_delete=models.CASCADE, related_name="+")
    viaje = models.ForeignKey("reservas.Viaje", on_delete=models.CASCADE, related_name="alertas_vuelo")
    numero_vuelo = models.CharField(max_length=8)
    tipo = models.CharField(max_length=16, choices=TipoAlertaVuelo.choices)
    detalle = models.CharField(max_length=200)
    eta = models.DateTimeField(null=True, blank=True)
    creada_en = models.DateTimeField(db_default=Now(), editable=False)
    atendida_en = models.DateTimeField(null=True, blank=True)
    atendida_por = models.ForeignKey(
        "cuentas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        db_table = "alerta_vuelo"
        verbose_name = "alerta de vuelo"
        verbose_name_plural = "alertas de vuelos"
        constraints = [
            models.CheckConstraint(condition=Q(tipo__in=TipoAlertaVuelo.values), name="alerta_tipo_valido"),
        ]
        indexes = [models.Index(fields=["empresa", "atendida_en"], name="alerta_pendientes")]

    def __str__(self):
        return f"{self.tipo} · viaje {self.viaje_id}"
