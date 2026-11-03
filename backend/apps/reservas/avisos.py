"""Avisos de estado al pasajero por WhatsApp (HU-21).

Se programan desde las acciones reales (panel, app, geocerca) y no desde la máquina de estados, para que los
datos de demostración y otros procesos internos no envíen mensajes. Se envían después del commit: si el envío
falla, el cambio de estado no se revierte y el mensaje queda en FAILED.

- Confirmación: reserva creada en SOLICITADO. Las del portal ya reciben la respuesta a su verificación
  (HU-20).
- Conductor asignado: al aceptar el conductor, no al asignar. Antes de eso puede rechazar (DC-18).
- Encuesta de 1 a 5 al finalizar (HU-24, RN-14).
- En camino y «tu vehículo te espera»: este último solo con EN_ZONA automático. Si lo indicó el conductor, el
  pasajero ya va a bordo (DC-17).
"""

from django.db import transaction

from apps.integraciones.notificaciones import obtener_notificador

from .models import Viaje


def _enviar(viaje_id: int, tipo: str) -> None:
    viaje = (
        Viaje.objects.select_related("pasajero", "empresa", "conductor__usuario", "vehiculo")
        .filter(pk=viaje_id)
        .first()
    )
    if viaje is not None:
        obtener_notificador().avisar(viaje, tipo)


def programar(viaje_id: int, tipo: str) -> None:
    # Con lambda y no `partial`: al fallar, Django registra su __qualname__, que un `partial` no tiene.
    transaction.on_commit(lambda: _enviar(viaje_id, tipo), robust=True)
