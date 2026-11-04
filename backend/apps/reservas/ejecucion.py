"""Ejecución del viaje desde la app (HU-16): en camino, en zona, pasajero a bordo y fin con pago (RN-10).

Todo cambio de estado pasa por la máquina de estados. EN_ZONA se marca solo cuando una posición precisa cae
dentro de `RADIO_ZONA_M` del origen (actor SISTEMA). Si el GPS no lo logra, el conductor igual puede indicar
que el pasajero subió: se registra EN_ZONA con actor CONDUCTOR, marcado como manual y con su distancia al
origen (DC-20), y luego PASAJERO_A_BORDO (DC-17).
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from apps.flota.models import Conductor, EstadoConductor, PosicionGps
from apps.flota.tiempo_real import notificar_conductor
from apps.integraciones.notificaciones import AVISO_EN_CAMINO, AVISO_EN_ZONA, AVISO_ENCUESTA

from . import avisos, estados
from .asignacion import grupo_conductor
from .models import Actor, EstadoViaje, HistorialEstado, MetodoPago, PagoViaje, Viaje

# Geocerca del punto de recogida (informe: 150 m).
RADIO_ZONA_M = 150


class EstadoNoPermitido(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "estado_no_permitido"
    default_detail = "El viaje no admite este cambio en su estado actual."


def avisar_viaje_actualizado(conductor_id: int, viaje_id: int) -> None:
    """La app vuelve a leer el viaje (EN_ZONA automático, cancelación desde el panel)."""
    capa = get_channel_layer()
    if capa is not None:
        mensaje = {"type": "conductor.viaje", "viaje": viaje_id}
        async_to_sync(capa.group_send)(grupo_conductor(conductor_id), mensaje)


def _avisar_a_la_app(viaje: Viaje) -> None:
    """Tras el commit. Si la respuesta de la API se pierde, la app igual se entera por el canal."""
    conductor_id, viaje_id = viaje.conductor_id, viaje.pk
    transaction.on_commit(lambda: avisar_viaje_actualizado(conductor_id, viaje_id))


def _del_conductor(viaje_id: int, usuario) -> Viaje:
    viaje = (
        Viaje.objects.select_for_update(of=("self",))
        .select_related("conductor")
        .filter(pk=viaje_id, conductor__usuario=usuario)
        .first()
    )
    if viaje is None:
        raise ValidationError({"viaje": ["No tienes un viaje con ese número."]})
    return viaje


def _salida(viaje: Viaje) -> HistorialEstado | None:
    return (
        HistorialEstado.objects.filter(viaje=viaje, estado_nuevo=EstadoViaje.EN_CAMINO)
        .order_by("-id")
        .first()
    )


def _distancia_al_origen(viaje: Viaje) -> int | None:
    """Metros entre el origen y la última posición del conductor desde que salió. None si no envió ninguna:
    una posición de antes de salir no dice dónde estaba al indicar la llegada."""
    salida = _salida(viaje)
    posiciones = PosicionGps.objects.filter(conductor_id=viaje.conductor_id)
    if salida:
        posiciones = posiciones.filter(registrada_en__gte=salida.creado_en)
    ultima = (
        posiciones.annotate(al_origen=Distance("punto", viaje.origen_geo)).order_by("-registrada_en").first()
    )
    return None if ultima is None else round(ultima.al_origen.m)


def _cambiar(viaje: Viaje, nuevo: str, *, actor: str, usuario=None, historial: dict | None = None) -> Viaje:
    try:
        return estados.transicionar(
            viaje, nuevo, desde=viaje.estado, actor=actor, usuario=usuario, historial=historial
        )
    except estados.TransicionInvalida as error:
        raise EstadoNoPermitido(str(error)) from error


@transaction.atomic
def en_camino(viaje_id: int, *, usuario) -> Viaje:
    viaje = _del_conductor(viaje_id, usuario)
    if viaje.estado != EstadoViaje.ACEPTADO:
        raise EstadoNoPermitido(f"Solo un viaje aceptado pasa a En camino; este está en {viaje.estado}.")
    avisos.programar(viaje.pk, AVISO_EN_CAMINO)  # HU-21
    _avisar_a_la_app(viaje)
    return _cambiar(viaje, EstadoViaje.EN_CAMINO, actor=Actor.CONDUCTOR, usuario=usuario)


@transaction.atomic
def pasajero_a_bordo(viaje_id: int, *, usuario) -> Viaje:
    viaje = _del_conductor(viaje_id, usuario)
    if viaje.estado == EstadoViaje.EN_CAMINO:
        # DC-17: la geocerca no lo marcó (GPS impreciso): queda registrado que lo indicó el conductor.
        viaje = _cambiar(
            viaje,
            EstadoViaje.EN_ZONA,
            actor=Actor.CONDUCTOR,
            usuario=usuario,
            historial={"manual": True, "distancia_m": _distancia_al_origen(viaje)},
        )
    if viaje.estado != EstadoViaje.EN_ZONA:
        raise EstadoNoPermitido(
            f"El pasajero sube después de llegar a la zona; el viaje está en {viaje.estado}."
        )
    _avisar_a_la_app(viaje)
    return _cambiar(viaje, EstadoViaje.PASAJERO_A_BORDO, actor=Actor.CONDUCTOR, usuario=usuario)


@transaction.atomic
def finalizar(viaje_id: int, *, usuario, metodo: str, monto: int) -> Viaje:
    """RN-10: ningún viaje se finaliza sin método de pago y monto. El conductor queda Disponible (RN-03)."""
    viaje = _del_conductor(viaje_id, usuario)
    if viaje.estado != EstadoViaje.PASAJERO_A_BORDO:
        raise EstadoNoPermitido(f"Solo se finaliza con el pasajero a bordo; el viaje está en {viaje.estado}.")
    if metodo == MetodoPago.CONVENIO and viaje.convenio_id is None:
        raise ValidationError({"metodo": ["Este viaje no pertenece a un convenio."]})
    PagoViaje.objects.create(viaje=viaje, metodo=metodo, monto=monto)
    _avisar_a_la_app(viaje)
    conductor_id = viaje.conductor_id
    viaje = _cambiar(viaje, EstadoViaje.FINALIZADO, actor=Actor.CONDUCTOR, usuario=usuario)
    Conductor.objects.filter(pk=conductor_id).update(estado=EstadoConductor.DISPONIBLE)
    notificar_conductor(Conductor.objects.get(pk=conductor_id))
    avisos.programar(viaje.pk, AVISO_ENCUESTA)  # HU-24: si falla, el viaje igual queda cerrado (RN-14)
    return viaje


def marcar_en_zona(conductor: Conductor, posiciones: list[dict]) -> bool:
    """EN_ZONA automático al recibir posiciones. Solo cuentan las precisas, tomadas desde que el viaje pasó a
    EN_CAMINO (una posición atrasada de antes no lo marca). Devuelve True si cambió el estado."""
    configuracion = conductor.usuario.empresa.configuracion
    with transaction.atomic():
        viaje = (
            Viaje.objects.select_for_update(of=("self",))
            .filter(conductor=conductor, estado=EstadoViaje.EN_CAMINO)
            .first()
        )
        if viaje is None:
            return False
        conductor_id, viaje_id = conductor.pk, viaje.pk
        cambio = _salida(viaje)
        for posicion in posiciones:
            precision = posicion.get("precision_m")
            if precision is None or precision > configuracion.precision_geocerca_m:
                continue
            if cambio and posicion["registrada_en"] < cambio.creado_en:
                continue
            punto = Point(posicion["lon"], posicion["lat"], srid=4326)
            if Viaje.objects.filter(pk=viaje.pk, origen_geo__dwithin=(punto, D(m=RADIO_ZONA_M))).exists():
                estados.transicionar(
                    viaje, EstadoViaje.EN_ZONA, desde=EstadoViaje.EN_CAMINO, actor=Actor.SISTEMA
                )
                transaction.on_commit(lambda: avisar_viaje_actualizado(conductor_id, viaje_id))
                avisos.programar(viaje_id, AVISO_EN_ZONA)  # HU-21: solo la llegada automática (DC-17)
                return True
    return False
