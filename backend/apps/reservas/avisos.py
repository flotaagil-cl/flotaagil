"""Avisos de estado al pasajero (HU-21, con CC-22 y CC-19): por correo o Web Push; sin WhatsApp desde HU-67.

Se programan desde las acciones reales (panel, app, geocerca) y no desde la máquina de estados, para que los
datos de demostración y otros procesos internos no envíen avisos. Se encolan después del commit y salen del
worker: la acción no espera al proveedor de correo ni al servicio de push.

- Confirmación: reserva creada en SOLICITADO.
- Conductor asignado: al aceptar el conductor, no al asignar. Antes de eso puede rechazar (DC-18).
- Encuesta al finalizar (HU-24, RN-14), por correo (HU-56).
- En camino y llegada: la llegada solo con EN_ZONA automático. Si lo indicó el conductor, el pasajero ya va a
  bordo (DC-17).
"""

from . import tareas


def programar(viaje_id: int, tipo: str) -> None:
    tareas.al_confirmar(tareas.enviar_aviso, viaje_id, tipo)
