"""HU-65 (CC-19, DC-62): estados del viaje para el pasajero con cuenta (módulo de cuentas).

- En vivo: cada cambio de estado llega al portal por `/ws/chat/` (evento `viaje`): «Tu viaje» se actualiza.
- Conductor asignado, llegada al origen y cancelación: por Web Push si el pasajero lo aceptó en algún
  navegador; si no, por correo solo con la casilla de avisos del viaje (`acepta_avisos_correo`). Sin WhatsApp.
- Solo para los viajes que la cuenta puede ver (DC-65): un teléfono sin verificar no recibe avisos de viajes
  de invitado de ese número.
- CC-26: un viaje pedido para otra persona avisa a la cuenta que lo pidió.
"""

from django.db import transaction
from django.db.models import Q

from apps.integraciones import push

from .models import CuentaPasajero, EstadoViaje, HistorialEstado, SuscripcionPush, Viaje
from .tipos_aviso import AVISO_CANCELACION, AVISO_CONDUCTOR, AVISO_EN_ZONA

CLAVE = (AVISO_CONDUCTOR, AVISO_EN_ZONA, AVISO_CANCELACION)


def cuenta_del_viaje(viaje: Viaje) -> CuentaPasajero | None:
    from .cuentas_pasajero import reservas_de

    # CC-26: la cuenta que pidió el viaje (estado inicial con su usuario), primero; luego la del pasajero.
    creador = (
        HistorialEstado.objects.filter(viaje_id=viaje.pk, estado_anterior__isnull=True)
        .values_list("usuario_id", flat=True)
        .first()
    )
    candidatas = CuentaPasajero.objects.select_related("usuario", "empresa").filter(
        Q(pasajero_id=viaje.pasajero_id) | Q(usuario_id=creador)
        if creador
        else Q(pasajero_id=viaje.pasajero_id),
        confirmada_en__isnull=False,
        empresa__modulo_cuentas=True,
    )
    for cuenta in sorted(candidatas, key=lambda c: c.usuario_id != creador):
        if reservas_de(cuenta).filter(pk=viaje.pk).exists():
            return cuenta
    return None


def en_vivo(viaje_id: int) -> None:
    """Después del commit de una transición: avisa al portal del pasajero que el viaje cambió."""
    from apps.chat.servicios import avisar

    viaje = Viaje.objects.filter(pk=viaje_id).only("pk", "estado", "pasajero_id").first()
    cuenta = cuenta_del_viaje(viaje) if viaje else None
    if cuenta is not None:
        avisar([cuenta.usuario_id], lambda _id: {"tipo": "viaje", "viaje": viaje.pk, "estado": viaje.estado})


def programar_en_vivo(viaje_id: int) -> None:
    transaction.on_commit(lambda: en_vivo(viaje_id), robust=True)


def contenido(viaje: Viaje, tipo: str) -> tuple[str, str] | None:
    """Título y texto del aviso (iguales en Web Push y en el correo)."""
    if tipo == AVISO_CONDUCTOR and viaje.conductor_id:
        conductor = viaje.conductor
        vehiculo = conductor.vehiculo_activo
        detalle = (
            f"{vehiculo.marca_modelo}, patente {vehiculo.patente}" if vehiculo else "sin vehículo informado"
        )
        return "Conductor asignado", f"{conductor.usuario.nombre} irá a buscarte ({detalle})."
    if tipo == AVISO_EN_ZONA:
        return "Tu conductor llegó", "Tu conductor llegó al punto de recogida."
    if tipo == AVISO_CANCELACION and viaje.estado == EstadoViaje.CANCELADO:
        return (
            "Viaje cancelado",
            f"Tu viaje N.º {viaje.pk} fue cancelado. Si tienes dudas, contacta a la central.",
        )
    return None


def enviar(viaje: Viaje, tipo: str) -> bool:
    """Desde la tarea `enviar_aviso`, en el worker. True si el viaje es de una cuenta (ya quedó atendido)."""
    from apps.cuentas.tareas import enviar_correo

    from . import tareas

    cuenta = cuenta_del_viaje(viaje)
    if cuenta is None:
        return False
    texto = contenido(viaje, tipo) if tipo in CLAVE else None
    if texto is None:
        return True
    titulo, cuerpo = texto
    suscripciones = list(
        SuscripcionPush.objects.filter(usuario_id=cuenta.usuario_id).values_list("pk", flat=True)
    )
    if push.configurado() and suscripciones:
        url = f"/mis-viajes/{viaje.pk}"
        for suscripcion in suscripciones:
            tareas.enviar_push.delay(suscripcion, {"titulo": titulo, "cuerpo": cuerpo, "url": url})
    elif cuenta.acepta_avisos_correo:
        enviar_correo.delay(
            cuenta.usuario.email, titulo, f"Hola {cuenta.nombre}:\n\n{cuerpo}", viaje.empresa_id
        )
    return True
