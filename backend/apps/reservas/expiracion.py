"""RN-06 con CC-22 (DC-53): una solicitud que no se confirma dentro de su plazo NO se cancela. Queda «Sin
confirmar» (PENDIENTE_CONFIRMACION con el plazo vencido) y el despacho decide: confirmarla por teléfono
(auditado), cancelarla o dejarla.

- Reserva pública (HU-51): el plazo es `confirmar_hasta` (24 h antes de la recogida, o 60 min).
- Reservas anteriores sin `confirmar_hasta`: creación + `expiracion_verificacion_min` de su empresa.

Celery beat (`apps.reservas.tareas.expirar_solicitudes`) solo cuenta las vencidas para el log.
"""

from datetime import timedelta

from django.db.models import DateTimeField, ExpressionWrapper, F, Q
from django.utils import timezone

from .models import EstadoViaje, Viaje


def vence_en(viaje: Viaje):
    if viaje.confirmar_hasta:
        return viaje.confirmar_hasta
    return viaje.creado_en + timedelta(minutes=viaje.empresa.configuracion.expiracion_verificacion_min)


def es_sin_confirmar(viaje: Viaje, ahora=None) -> bool:
    return viaje.estado == EstadoViaje.PENDIENTE_CONFIRMACION and vence_en(viaje) <= (ahora or timezone.now())


def sin_confirmar(queryset=None, ahora=None):
    """Las reservas «Sin confirmar»: pendientes con el plazo vencido."""
    ahora = ahora or timezone.now()
    queryset = Viaje.objects.all() if queryset is None else queryset
    plazo_anterior = ExpressionWrapper(
        F("creado_en") + F("empresa__configuracion__expiracion_verificacion_min") * timedelta(minutes=1),
        output_field=DateTimeField(),
    )
    return (
        queryset.filter(estado=EstadoViaje.PENDIENTE_CONFIRMACION)
        .annotate(vence_anterior=plazo_anterior)
        .filter(Q(confirmar_hasta__lte=ahora) | Q(confirmar_hasta__isnull=True, vence_anterior__lte=ahora))
    )


def expirar_pendientes(ahora=None) -> int:
    """Desde CC-22 no cancela: devuelve cuántas reservas están «Sin confirmar» (para el log)."""
    return sin_confirmar(ahora=ahora).count()
