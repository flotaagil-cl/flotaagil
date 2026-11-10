"""CONVENIO, según docs/diccionario-datos.md, con los cambios de HU-34 (DC-35).

Desde HU-34 la empresa cliente se registra sola y queda EN_REVISION hasta que el administrador la aprueba.
Entra con una cuenta propia (USUARIO de rol CONVENIO, `usuario`): el link con token y la contraseña compartida de
HU-11 y HU-25 se retiraron. Los convenios anteriores quedaron APROBADO sin cuenta, con su historial intacto.
Administración en `servicios.py`.
"""

import secrets

from django.db import models
from django.db.models import Q
from django.db.models.functions import Now

from apps.comun.validadores import validar_no_vacio, validar_rut


def generar_token_link() -> str:
    """Solo para la migración 0001 (HU-11): el link con token se retiró en HU-34 (DC-35)."""
    return secrets.token_urlsafe(32)


class EstadoConvenio(models.TextChoices):
    EN_REVISION = "EN_REVISION", "En revisión"
    APROBADO = "APROBADO", "Aprobado"
    RECHAZADO = "RECHAZADO", "Rechazado"
    # RN-08: inactivo corta el acceso sin afectar el historial.
    INACTIVO = "INACTIVO", "Inactivo"


class Convenio(models.Model):
    empresa = models.ForeignKey("cuentas.Empresa", on_delete=models.PROTECT, related_name="convenios")
    cliente_nombre = models.CharField(max_length=120, validators=[validar_no_vacio])
    cliente_rut = models.CharField(max_length=12, validators=[validar_rut])
    direccion = models.CharField(max_length=200, null=True, blank=True)
    encargado_nombre = models.CharField(max_length=80, null=True, blank=True)
    encargado_telefono = models.CharField(max_length=16, null=True, blank=True)
    estado = models.CharField(
        max_length=11,
        choices=EstadoConvenio.choices,
        default=EstadoConvenio.APROBADO,
        db_default=EstadoConvenio.APROBADO,
    )
    motivo_rechazo = models.CharField(max_length=200, null=True, blank=True)
    revisado_por = models.ForeignKey(
        "cuentas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    revisado_en = models.DateTimeField(null=True, blank=True)
    # La cuenta del encargado (rol CONVENIO). NULL en los convenios sin cuenta (anteriores a HU-34 o creados
    # por el administrador para reservas del panel).
    usuario = models.OneToOneField(
        "cuentas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="convenio"
    )
    creado_en = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        db_table = "convenio"
        ordering = ["cliente_nombre"]
        constraints = [
            models.CheckConstraint(condition=~Q(cliente_nombre=""), name="convenio_cliente_nombre_no_vacio"),
            models.CheckConstraint(
                condition=Q(estado__in=EstadoConvenio.values), name="convenio_estado_valido"
            ),
            models.CheckConstraint(
                condition=~Q(estado=EstadoConvenio.RECHAZADO)
                | (Q(motivo_rechazo__isnull=False) & ~Q(motivo_rechazo="")),
                name="convenio_rechazo_con_motivo",
            ),
        ]

    def __str__(self):
        return self.cliente_nombre

    @property
    def activo(self) -> bool:
        """Compatibilidad con HU-11: un convenio vigente es uno aprobado."""
        return self.estado == EstadoConvenio.APROBADO
