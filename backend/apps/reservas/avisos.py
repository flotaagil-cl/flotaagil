"""Avisos de estado al pasajero por WhatsApp (HU-21).

Se programan desde las acciones reales (panel, app, geocerca) y no desde la máquina de estados, para que los
datos de demostración y otros procesos internos no envíen mensajes. Se encolan después del commit y salen del
worker: la acción no espera a Twilio, y si el envío falla, el mensaje queda en FAILED.

- Confirmación: reserva creada en SOLICITADO. Las del portal ya reciben la respuesta a su verificación
  (HU-20).
- Conductor asignado: al aceptar el conductor, no al asignar. Antes de eso puede rechazar (DC-18).
- Encuesta de 1 a 5 al finalizar (HU-24, RN-14).
- En camino y «tu vehículo te espera»: este último solo con EN_ZONA automático. Si lo indicó el conductor, el
  pasajero ya va a bordo (DC-17).
"""

from . import tareas


def programar(viaje_id: int, tipo: str) -> None:
    tareas.al_confirmar(tareas.enviar_aviso, viaje_id, tipo)
