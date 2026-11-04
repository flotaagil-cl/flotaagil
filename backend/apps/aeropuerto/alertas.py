"""Alertas de vuelo en el panel (HU-28): cambio de ETA, cancelación, desvío o API sin datos.

Quedan registradas (ALERTA_VUELO, DC-23) y marcan la reserva hasta que alguien las atiende. Atender una alerta
no hace que se repita con el mismo dato: el cambio de ETA vuelve a avisar solo si la ETA se movió de nuevo en
`cambio_eta_min` o más, y «sin datos» solo si la API volvió a responder entremedio.
"""

from datetime import timedelta

from django.utils import timezone

from .models import AlertaVuelo, TipoAlertaVuelo


def _hora(momento) -> str:
    return timezone.localtime(momento).strftime("%d-%m %H:%M")


def pendientes():
    return AlertaVuelo.objects.filter(atendida_en__isnull=True)


def _crear(viaje, vuelo, tipo: str, detalle: str, eta=None) -> AlertaVuelo:
    return AlertaVuelo.objects.create(
        empresa_id=viaje.empresa_id,
        viaje=viaje,
        numero_vuelo=vuelo.numero,
        tipo=tipo,
        detalle=detalle,
        eta=eta,
    )


def _una_sola_vez(viaje, vuelo, tipo: str, detalle: str) -> None:
    if not AlertaVuelo.objects.filter(viaje=viaje, tipo=tipo).exists():
        _crear(viaje, vuelo, tipo, detalle)


def _cambio_eta(viaje, vuelo, eta, umbral: timedelta) -> None:
    detalle = f"El vuelo {vuelo.numero} ahora llega el {_hora(eta)}."
    ultima = (
        AlertaVuelo.objects.filter(viaje=viaje, tipo=TipoAlertaVuelo.ETA_CAMBIADA).order_by("-id").first()
    )
    if ultima is None:
        _crear(viaje, vuelo, TipoAlertaVuelo.ETA_CAMBIADA, detalle, eta)
    elif ultima.atendida_en is None:
        ultima.detalle, ultima.eta = detalle, eta  # sigue sin atender: se actualiza, no se acumula
        ultima.save(update_fields=["detalle", "eta"])
    elif abs(eta - ultima.eta) >= umbral:
        _crear(viaje, vuelo, TipoAlertaVuelo.ETA_CAMBIADA, detalle, eta)


def al_recibir_datos(viaje, vuelo, *, estado_anterior: str, hubo_cambio_eta: bool, umbral: timedelta) -> None:
    from .models import EstadoVuelo

    # La API volvió a responder: «sin datos» se resuelve sola, sin un usuario.
    pendientes().filter(viaje=viaje, tipo=TipoAlertaVuelo.SIN_DATOS).update(atendida_en=timezone.now())
    if vuelo.estado_vuelo == EstadoVuelo.CANCELADO and estado_anterior != EstadoVuelo.CANCELADO:
        detalle = f"El vuelo {vuelo.numero} fue cancelado."
        _una_sola_vez(viaje, vuelo, TipoAlertaVuelo.VUELO_CANCELADO, detalle)
    elif vuelo.estado_vuelo == EstadoVuelo.DESVIADO and estado_anterior != EstadoVuelo.DESVIADO:
        detalle = f"El vuelo {vuelo.numero} fue desviado."
        _una_sola_vez(viaje, vuelo, TipoAlertaVuelo.VUELO_DESVIADO, detalle)
    elif hubo_cambio_eta:
        _cambio_eta(viaje, vuelo, vuelo.hora_estimada or vuelo.hora_programada, umbral)


def sin_datos(viaje, vuelo) -> None:
    ultima = AlertaVuelo.objects.filter(viaje=viaje, tipo=TipoAlertaVuelo.SIN_DATOS).order_by("-id").first()
    # Sin atender, o atendida por alguien y la API sigue sin responder: no se repite.
    if ultima and (ultima.atendida_en is None or ultima.atendida_por_id):
        return
    _crear(
        viaje,
        vuelo,
        TipoAlertaVuelo.SIN_DATOS,
        f"La API de vuelos no entrega datos del vuelo {vuelo.numero}.",
    )


def atender(alerta: AlertaVuelo, *, usuario) -> AlertaVuelo:
    if alerta.atendida_en is None:
        alerta.atendida_en = timezone.now()
        alerta.atendida_por = usuario
        alerta.save(update_fields=["atendida_en", "atendida_por"])
    return alerta


def atender_cambio_eta(viaje, *, usuario) -> None:
    """Confirmar o descartar la nueva hora ya es atender la alerta del cambio."""
    pendientes().filter(viaje=viaje, tipo=TipoAlertaVuelo.ETA_CAMBIADA).update(
        atendida_en=timezone.now(), atendida_por=usuario
    )
