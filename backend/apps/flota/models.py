"""CONDUCTOR, VEHICULO y CONDUCTOR_VEHICULO, según docs/diccionario-datos.md."""

from django.contrib.gis.db import models as gis
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now
from django.utils import timezone

from apps.comun.validadores import validar_movil_chile, validar_no_vacio, validar_patente, validar_rut

ANTIGUEDAD_MAXIMA_ANIOS = 12


def validar_anio_vehiculo(anio: int) -> None:
    """Antigüedad máxima del servicio: año ≥ año actual - 12."""
    minimo = timezone.localdate().year - ANTIGUEDAD_MAXIMA_ANIOS
    if anio < minimo:
        raise ValidationError(f"El vehículo debe ser del año {minimo} o posterior.", code="antiguedad")


class Vehiculo(models.Model):
    empresa = models.ForeignKey("cuentas.Empresa", on_delete=models.PROTECT, related_name="vehiculos")
    patente = models.CharField(max_length=8, unique=True, validators=[validar_patente])
    marca_modelo = models.CharField(max_length=60, validators=[validar_no_vacio])
    anio = models.PositiveSmallIntegerField(validators=[validar_anio_vehiculo])
    capacidad = models.PositiveSmallIntegerField(
        default=4, db_default=4, validators=[MinValueValidator(1), MaxValueValidator(7)]
    )
    activo = models.BooleanField(default=True, db_default=True)

    class Meta:
        db_table = "vehiculo"
        ordering = ["patente"]
        constraints = [
            models.CheckConstraint(
                condition=Q(capacidad__gte=1, capacidad__lte=7), name="vehiculo_capacidad_1_7"
            ),
            models.CheckConstraint(
                condition=Q(patente__regex=r"^([A-Z]{2}[0-9]{4}|[A-Z]{4}[0-9]{2})$"),
                name="vehiculo_patente_formato",
            ),
            models.CheckConstraint(condition=~Q(marca_modelo=""), name="vehiculo_marca_modelo_no_vacio"),
        ]

    def __str__(self):
        return f"{self.patente} ({self.marca_modelo})"


class LicenciaClase(models.TextChoices):
    A1 = "A1", "A1"
    A2 = "A2", "A2"
    A3 = "A3", "A3"


class EstadoConductor(models.TextChoices):
    DISPONIBLE = "DISPONIBLE", "Disponible"
    NO_DISPONIBLE = "NO_DISPONIBLE", "No disponible"
    EN_VIAJE = "EN_VIAJE", "En viaje"


class Conductor(models.Model):
    """La empresa del conductor es la de su usuario (USUARIO.empresa_id)."""

    usuario = models.OneToOneField("cuentas.Usuario", on_delete=models.PROTECT, related_name="conductor")
    rut = models.CharField(max_length=12, unique=True, validators=[validar_rut])
    telefono = models.CharField(max_length=16, validators=[validar_movil_chile])
    licencia_clase = models.CharField(max_length=4, choices=LicenciaClase.choices)
    licencia_vence = models.DateField()
    estado = models.CharField(
        max_length=14,
        choices=EstadoConductor.choices,
        default=EstadoConductor.NO_DISPONIBLE,
        db_default=EstadoConductor.NO_DISPONIBLE,
    )
    vehiculo_activo = models.ForeignKey(
        Vehiculo, on_delete=models.PROTECT, null=True, blank=True, related_name="conductores_activos"
    )
    consentimiento_gps_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "conductor"
        verbose_name_plural = "conductores"
        constraints = [
            models.CheckConstraint(
                condition=Q(licencia_clase__in=LicenciaClase.values), name="conductor_licencia_clase"
            ),
            models.CheckConstraint(
                condition=Q(estado__in=EstadoConductor.values), name="conductor_estado_valido"
            ),
            # RN-05: el vehículo declarado es obligatorio para quedar Disponible.
            models.CheckConstraint(
                condition=~Q(estado=EstadoConductor.DISPONIBLE) | Q(vehiculo_activo__isnull=False),
                name="conductor_disponible_con_vehiculo",
            ),
        ]

    def __str__(self):
        return self.usuario.nombre

    @property
    def empresa_id(self):
        return self.usuario.empresa_id

    def clean(self):
        if self._state.adding and self.licencia_vence and self.licencia_vence <= timezone.localdate():
            raise ValidationError(
                {"licencia_vence": "La licencia debe estar vigente al dar de alta al conductor."}
            )


class ConductorVehiculo(models.Model):
    pk = models.CompositePrimaryKey("conductor_id", "vehiculo_id")
    conductor = models.ForeignKey(Conductor, on_delete=models.CASCADE, related_name="asociaciones")
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name="asociaciones")
    # La fecha de Chile: la base trabaja en UTC y desde las 21:00 ya marcaría el día siguiente.
    desde = models.DateField(default=timezone.localdate, db_default=Now())

    class Meta:
        db_table = "conductor_vehiculo"
        verbose_name = "asociación conductor-vehículo"
        verbose_name_plural = "asociaciones conductor-vehículo"

    def __str__(self):
        return f"{self.conductor} / {self.vehiculo}"


class PosicionGps(models.Model):
    """POSICION_GPS (Anexo D). Solo en turno y con consentimiento (RN-18). Retención 30 días (RN-15).

    DC-15: única por (conductor, registrada_en), para que la app pueda reenviar un lote sin duplicar.
    """

    conductor = models.ForeignKey(Conductor, on_delete=models.CASCADE, related_name="posiciones")
    viaje = models.ForeignKey(
        "reservas.Viaje", on_delete=models.SET_NULL, null=True, blank=True, related_name="posiciones"
    )
    punto = gis.PointField(geography=True, srid=4326)
    precision_m = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(500)])
    registrada_en = models.DateTimeField()

    class Meta:
        db_table = "posicion_gps"
        verbose_name = "posición GPS"
        verbose_name_plural = "posiciones GPS"
        constraints = [
            models.UniqueConstraint(
                fields=["conductor", "registrada_en"], name="posicion_unica_por_instante"
            ),
            models.CheckConstraint(
                condition=Q(precision_m__isnull=True) | Q(precision_m__lte=500),
                name="posicion_precision_0_500",
            ),
        ]
        indexes = [models.Index(fields=["conductor", "-registrada_en"], name="posicion_conductor_reciente")]

    def __str__(self):
        return f"{self.conductor_id} @ {self.registrada_en:%Y-%m-%d %H:%M:%S}"

    @property
    def confiable(self) -> bool:
        """El Anexo D marca como no confiable una precisión mayor a 100 m."""
        return self.precision_m is not None and self.precision_m <= 100


class MotivoTerminoTurno(models.TextChoices):
    CONDUCTOR = "CONDUCTOR", "Conductor"
    CUENTA_DESHABILITADA = "CUENTA_DESHABILITADA", "Cuenta deshabilitada"
    CIERRE_ADMINISTRATIVO = "CIERRE_ADMINISTRATIVO", "Cierre administrativo"


class Turno(models.Model):
    """HU-31 (CC-12): historial de turnos. Reemplaza `turno_inicio` y `turno_fin` de DC-26.

    Un turno va de «Empezar turno» a «Terminar turno» con un mismo vehículo: cambiar de vehículo lo cierra y
    abre otro. A lo más uno abierto por conductor (índice único parcial). `vehiculo` es NULL solo en turnos
    migrados
    desde DC-26 cuyo vehículo no se pudo saber.
    """

    conductor = models.ForeignKey(Conductor, on_delete=models.PROTECT, related_name="turnos")
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.PROTECT, null=True, blank=True, related_name="turnos"
    )
    hora_inicio = models.DateTimeField()
    hora_termino = models.DateTimeField(null=True, blank=True)
    motivo_termino = models.CharField(
        max_length=21, choices=MotivoTerminoTurno.choices, null=True, blank=True
    )

    class Meta:
        db_table = "turno"
        ordering = ["-hora_inicio", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["conductor"],
                condition=Q(hora_termino__isnull=True),
                name="turno_un_abierto_por_conductor",
            ),
            models.CheckConstraint(
                condition=Q(motivo_termino__isnull=True) | Q(motivo_termino__in=MotivoTerminoTurno.values),
                name="turno_motivo_valido",
            ),
            # Abierto sin término ni motivo; terminado con ambos, después del inicio.
            models.CheckConstraint(
                condition=Q(hora_termino__isnull=True, motivo_termino__isnull=True)
                | Q(
                    hora_termino__isnull=False,
                    motivo_termino__isnull=False,
                    hora_termino__gte=models.F("hora_inicio"),
                ),
                name="turno_termino_coherente",
            ),
        ]
        indexes = [models.Index(fields=["conductor", "-hora_inicio"], name="turno_conductor_idx")]

    def __str__(self):
        return f"Turno {self.pk} de {self.conductor_id}"

    @property
    def abierto(self) -> bool:
        return self.hora_termino is None


class CierreCaja(models.Model):
    """HU-31 (CC-12): cuadratura del efectivo de un turno terminado. Uno por turno.

    `monto_registrado` es el efectivo de PAGO_VIAJE de los viajes del turno, fijado al cerrar; `diferencia` es
    rendido - registrado (positiva: sobra; negativa: falta).
    """

    turno = models.OneToOneField(Turno, on_delete=models.PROTECT, related_name="cierre_caja")
    monto_registrado = models.PositiveIntegerField()
    monto_rendido = models.PositiveIntegerField(validators=[MaxValueValidator(50_000_000)])
    diferencia = models.IntegerField()
    observacion = models.CharField(max_length=200, null=True, blank=True)
    responsable = models.ForeignKey("cuentas.Usuario", on_delete=models.PROTECT, related_name="+")
    fecha_cierre = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "cierre_caja"
        verbose_name = "cierre de caja"
        verbose_name_plural = "cierres de caja"
        constraints = [
            models.CheckConstraint(
                condition=Q(diferencia=models.F("monto_rendido") - models.F("monto_registrado")),
                name="cierre_caja_diferencia_calculada",
            ),
            models.CheckConstraint(
                condition=Q(diferencia=0) | (Q(observacion__isnull=False) & ~Q(observacion="")),
                name="cierre_caja_observacion_si_hay_diferencia",
            ),
        ]

    def __str__(self):
        return f"Cierre de caja del turno {self.turno_id}"
