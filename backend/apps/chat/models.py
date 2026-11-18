"""Chat interno (CC-19, DC-60): CONVERSACION, PARTICIPANTE y MENSAJE.

- CENTRAL: hilo de un conductor con el equipo (administrador y despachadores). Uno por conductor, siempre
  activo.
- DIRECTO: uno a uno entre dos personas del personal (`clave` = «menor-mayor» de los ids, para no duplicarlo).
- GRUPO: con nombre e integrantes; al borrarlo queda oculto (`borrado_en`) y auditado.
- VIAJE y SOPORTE: con el pasajero (módulo de cuentas, HU-66).

El equipo entra a CENTRAL y SOPORTE por regla, no por fila; su PARTICIPANTE se crea al marcar leído.
"""

from django.db import models
from django.db.models import Q

MAX_TEXTO = 1000


class TipoConversacion(models.TextChoices):
    CENTRAL = "CENTRAL", "Central"
    DIRECTO = "DIRECTO", "Directo"
    GRUPO = "GRUPO", "Grupo"
    VIAJE = "VIAJE", "Viaje"
    SOPORTE = "SOPORTE", "Soporte"


class RespuestaRapida(models.TextChoices):
    """Respuestas rápidas de la app del conductor: el texto lo pone el servidor."""

    EN_CAMINO = "EN_CAMINO", "Voy en camino"
    LLEGUE = "LLEGUE", "Llegué"
    NO_APARECE = "NO_APARECE", "Pasajero no aparece"
    ATRASO = "ATRASO", "Me atraso 10 min"
    AYUDA = "AYUDA", "Necesito ayuda"


class Conversacion(models.Model):
    empresa = models.ForeignKey("cuentas.Empresa", on_delete=models.PROTECT, related_name="+")
    tipo = models.CharField(max_length=10, choices=TipoConversacion.choices)
    nombre = models.CharField(max_length=60, blank=True, default="")
    conductor = models.ForeignKey(
        "flota.Conductor", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    viaje = models.ForeignKey(
        "reservas.Viaje", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    pasajero_usuario = models.ForeignKey(
        "cuentas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    clave = models.CharField(max_length=24, null=True, blank=True)
    creado_por = models.ForeignKey(
        "cuentas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    ultimo_mensaje_en = models.DateTimeField(null=True, blank=True)
    borrado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "conversacion"
        constraints = [
            models.CheckConstraint(
                condition=Q(tipo__in=TipoConversacion.values), name="conversacion_tipo_valido"
            ),
            models.UniqueConstraint(
                fields=["conductor"], condition=Q(tipo="CENTRAL"), name="conversacion_central_unica"
            ),
            models.UniqueConstraint(
                fields=["empresa", "clave"], condition=Q(tipo="DIRECTO"), name="conversacion_directo_unico"
            ),
            models.UniqueConstraint(
                fields=["viaje"], condition=Q(tipo="VIAJE"), name="conversacion_viaje_unica"
            ),
            models.UniqueConstraint(
                fields=["pasajero_usuario"], condition=Q(tipo="SOPORTE"), name="conversacion_soporte_unica"
            ),
            models.CheckConstraint(
                condition=~Q(tipo="CENTRAL") | Q(conductor__isnull=False),
                name="conversacion_central_con_conductor",
            ),
            models.CheckConstraint(
                condition=~Q(tipo="GRUPO") | ~Q(nombre=""), name="conversacion_grupo_con_nombre"
            ),
        ]
        indexes = [models.Index(fields=["empresa", "tipo"], name="conversacion_empresa_tipo_idx")]

    def __str__(self):
        return f"{self.tipo} #{self.pk}"


class Participante(models.Model):
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name="participantes")
    usuario = models.ForeignKey("cuentas.Usuario", on_delete=models.PROTECT, related_name="+")
    ultimo_leido_id = models.BigIntegerField(default=0, db_default=0)
    agregado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "participante"
        constraints = [
            models.UniqueConstraint(fields=["conversacion", "usuario"], name="participante_unico"),
        ]

    def __str__(self):
        return f"{self.usuario_id} en {self.conversacion_id}"


class Mensaje(models.Model):
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name="mensajes")
    autor = models.ForeignKey("cuentas.Usuario", on_delete=models.PROTECT, related_name="+")
    texto = models.CharField(max_length=MAX_TEXTO)
    rapida = models.CharField(max_length=12, choices=RespuestaRapida.choices, blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mensaje_chat"
        constraints = [models.CheckConstraint(condition=~Q(texto=""), name="mensaje_texto_no_vacio")]
        indexes = [
            models.Index(fields=["conversacion", "-id"], name="mensaje_conversacion_idx"),
            models.Index(fields=["creado_en"], name="mensaje_creado_en_idx"),
        ]

    def __str__(self):
        return f"Mensaje #{self.pk} de {self.conversacion_id}"
