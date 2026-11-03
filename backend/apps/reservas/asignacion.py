"""Asignación de un viaje a un conductor (HU-14).

El despachador (o el administrador) confirma el conductor (RN-02): debe estar Disponible con su vehículo
declarado (RN-01, RN-05), ser de la misma empresa (RN-13) y no tener otro viaje en ejecución (RN-03). El
viaje pasa de SOLICITADO a ASIGNADO por la máquina de estados, queda la ASIGNACION y se avisa a la app del
conductor por su WebSocket. El conductor tiene `SEGUNDOS_PARA_RESPONDER` para aceptar o rechazar (RN-04,
HU-15).
"""

from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.gis.db.models.functions import Distance
from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from apps.flota.models import Conductor, EstadoConductor, PosicionGps
from apps.flota.tiempo_real import notificar_conductor
from apps.integraciones.notificaciones import AVISO_CONDUCTOR

from . import avisos, estados
from .models import Actor, Asignacion, EstadoViaje, OrigenSugerencia, ResultadoAsignacion, Viaje

SEGUNDOS_PARA_RESPONDER = 60  # RN-04
# Estados en que el viaje ocupa al conductor (RN-03).
EN_EJECUCION = (
    EstadoViaje.ASIGNADO,
    EstadoViaje.ACEPTADO,
    EstadoViaje.EN_CAMINO,
    EstadoViaje.EN_ZONA,
    EstadoViaje.PASAJERO_A_BORDO,
)


class AsignacionNoPermitida(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "asignacion_no_permitida"
    default_detail = "No se puede asignar este viaje ahora."


def grupo_conductor(conductor_id: int) -> str:
    return f"conductor_{conductor_id}"


def con_viaje_en_ejecucion(empresa_id: int):
    return Viaje.objects.filter(
        empresa_id=empresa_id, estado__in=EN_EJECUCION, conductor__isnull=False
    ).values("conductor_id")


def candidatos(viaje: Viaje) -> list[dict]:
    """Conductores Disponibles de la empresa sin viaje en ejecución, los más cercanos al origen primero (si se
    conoce su última posición). La sugerencia automática es HU-04; aquí el despachador elige (MANUAL)."""
    ultima = PosicionGps.objects.filter(conductor=OuterRef("pk")).order_by("-registrada_en")
    conductores = (
        Conductor.objects.filter(
            usuario__empresa_id=viaje.empresa_id,
            usuario__activo=True,
            estado=EstadoConductor.DISPONIBLE,
            vehiculo_activo__isnull=False,
        )
        .exclude(pk__in=con_viaje_en_ejecucion(viaje.empresa_id))
        .select_related("usuario", "vehiculo_activo")
        .annotate(ultima_id=Subquery(ultima.values("pk")[:1]))
    )
    conductores = list(conductores)
    posiciones = {
        p.pk: p
        for p in PosicionGps.objects.filter(
            pk__in=[c.ultima_id for c in conductores if c.ultima_id]
        ).annotate(distancia=Distance("punto", viaje.origen_geo))
    }
    filas = []
    for conductor in conductores:
        posicion = posiciones.get(conductor.ultima_id)
        filas.append(
            {
                "id": conductor.pk,
                "nombre": conductor.usuario.nombre,
                "patente": conductor.vehiculo_activo.patente,
                "distancia_m": round(posicion.distancia.m) if posicion else None,
                "posicion_en": posicion.registrada_en if posicion else None,
            }
        )
    return sorted(filas, key=lambda f: (f["distancia_m"] is None, f["distancia_m"] or 0, f["nombre"]))


def datos_para_la_app(asignacion: Asignacion) -> dict:
    """Lo que ve el conductor al recibir el viaje (HU-14): origen, destino, pasajero, tarifa y vuelo con
    ETA."""
    viaje = asignacion.viaje
    vuelo = getattr(viaje, "vuelo", None)
    vence = asignacion.enviada_en + timedelta(seconds=SEGUNDOS_PARA_RESPONDER)
    return {
        "asignacion": asignacion.pk,
        "viaje": viaje.pk,
        "pasajero": viaje.pasajero.nombre,
        "origen": {"direccion": viaje.origen_dir, "lat": viaje.origen_geo.y, "lon": viaje.origen_geo.x},
        "destino": {"direccion": viaje.destino_dir, "lat": viaje.destino_geo.y, "lon": viaje.destino_geo.x},
        "recogida_en": viaje.recogida_en.isoformat(),
        "tarifa": viaje.tarifa,
        "vuelo": None
        if vuelo is None
        else {
            "numero": vuelo.numero,
            "hora_programada": vuelo.hora_programada.isoformat(),
            "hora_estimada": vuelo.hora_estimada.isoformat() if vuelo.hora_estimada else None,
        },
        "vence_en": vence.isoformat(),
    }


def asignacion_pendiente(conductor: Conductor) -> Asignacion | None:
    return (
        Asignacion.objects.filter(
            conductor=conductor, resultado__isnull=True, viaje__estado=EstadoViaje.ASIGNADO
        )
        .select_related("viaje__pasajero", "viaje__vuelo")
        .first()
    )


def _avisar_al_conductor(asignacion: Asignacion) -> None:
    capa = get_channel_layer()
    if capa is not None:
        mensaje = {"type": "conductor.asignado", "asignacion": datos_para_la_app(asignacion)}
        async_to_sync(capa.group_send)(grupo_conductor(asignacion.conductor_id), mensaje)


def asignar(viaje: Viaje, conductor_id: int, *, usuario) -> Asignacion:
    with transaction.atomic():
        # Estado actual con bloqueo: dos despachadores no pueden asignar la misma reserva a la vez.
        viaje = Viaje.objects.select_for_update(of=("self",)).get(pk=viaje.pk)
        conductor = (
            Conductor.objects.select_for_update(of=("self",))
            .select_related("usuario", "vehiculo_activo")
            .filter(pk=conductor_id, usuario__empresa_id=viaje.empresa_id)
            .first()
        )
        if conductor is None:
            raise ValidationError({"conductor": ["El conductor no existe en tu empresa."]})
        if viaje.estado != EstadoViaje.SOLICITADO:
            raise AsignacionNoPermitida(
                f"Solo se asigna una reserva solicitada; esta está en {viaje.estado}."
            )
        if not conductor.usuario.activo or conductor.estado != EstadoConductor.DISPONIBLE:
            raise AsignacionNoPermitida(f"{conductor.usuario.nombre} no está Disponible (RN-01).")
        if conductor.vehiculo_activo is None:
            raise AsignacionNoPermitida(f"{conductor.usuario.nombre} no tiene vehículo declarado (RN-05).")
        if Viaje.objects.filter(conductor=conductor, estado__in=EN_EJECUCION).exists():
            raise AsignacionNoPermitida(f"{conductor.usuario.nombre} ya tiene un viaje en ejecución (RN-03).")
        try:
            viaje = estados.transicionar(
                viaje,
                EstadoViaje.ASIGNADO,
                desde=EstadoViaje.SOLICITADO,
                actor=estados.actor_de(usuario),
                usuario=usuario,
                conductor=conductor,
                vehiculo=conductor.vehiculo_activo,
            )
        except estados.TransicionInvalida as error:
            raise AsignacionNoPermitida(str(error)) from error
        asignacion = Asignacion.objects.create(
            viaje=viaje, conductor=conductor, despachador=usuario, origen_sugerencia=OrigenSugerencia.MANUAL
        )
        asignacion = Asignacion.objects.select_related("viaje__pasajero", "viaje__vuelo").get(
            pk=asignacion.pk
        )
        transaction.on_commit(lambda: _avisar_al_conductor(asignacion))
    return asignacion


# --- Respuesta del conductor y expiración (HU-15, RN-04) ---


def vence_en(asignacion: Asignacion):
    return asignacion.enviada_en + timedelta(seconds=SEGUNDOS_PARA_RESPONDER)


def _avisar_fin(asignacion: Asignacion) -> None:
    """La app cierra el aviso (rechazo, expiración o aceptación desde otro dispositivo)."""
    capa = get_channel_layer()
    if capa is not None:
        mensaje = {"type": "conductor.sin_asignacion", "asignacion": asignacion.pk}
        async_to_sync(capa.group_send)(grupo_conductor(asignacion.conductor_id), mensaje)


def _volver_a_solicitado(asignacion: Asignacion, *, actor: str, usuario=None) -> None:
    """RN-04: la reserva vuelve a SOLICITADO, sin conductor ni vehículo, para reasignarla."""
    estados.transicionar(
        asignacion.viaje,
        EstadoViaje.SOLICITADO,
        desde=EstadoViaje.ASIGNADO,
        actor=actor,
        usuario=usuario,
        conductor=None,
        vehiculo=None,
    )


def responder(asignacion_id: int, *, usuario, aceptar: bool) -> Asignacion:
    """El conductor acepta o rechaza dentro de los 60 s. Aceptar deja el viaje ACEPTADO y al conductor
    EN_VIAJE (RN-03); rechazar devuelve la reserva a SOLICITADO (RN-04). Ambos quedan en ASIGNACION."""
    ahora = timezone.now()
    with transaction.atomic():
        asignacion = (
            Asignacion.objects.select_for_update(of=("self",))
            .select_related("viaje", "conductor")
            .filter(pk=asignacion_id, conductor__usuario=usuario)
            .first()
        )
        if asignacion is None:
            raise ValidationError({"asignacion": ["No existe una asignación tuya con ese número."]})
        if asignacion.resultado is not None:
            raise AsignacionNoPermitida("Esta asignación ya fue respondida o venció.")
        if vence_en(asignacion) <= ahora:
            raise AsignacionNoPermitida(
                "Se acabó el tiempo para responder (60 s): la reserva vuelve a la central."
            )
        asignacion.respondida_en = ahora
        if aceptar:
            asignacion.resultado = ResultadoAsignacion.ACEPTADA
            estados.transicionar(
                asignacion.viaje,
                EstadoViaje.ACEPTADO,
                desde=EstadoViaje.ASIGNADO,
                actor=Actor.CONDUCTOR,
                usuario=usuario,
            )
            Conductor.objects.filter(pk=asignacion.conductor_id).update(estado=EstadoConductor.EN_VIAJE)
            avisos.programar(asignacion.viaje_id, AVISO_CONDUCTOR)  # HU-21
        else:
            asignacion.resultado = ResultadoAsignacion.RECHAZADA
            _volver_a_solicitado(asignacion, actor=Actor.CONDUCTOR, usuario=usuario)
        asignacion.save(update_fields=["respondida_en", "resultado"])
        notificar_conductor(asignacion.conductor)  # el mapa ve el cambio a En viaje
        transaction.on_commit(lambda: _avisar_fin(asignacion))
    return asignacion


def expirar_asignaciones(ahora=None) -> int:
    """RN-04: las asignaciones sin respuesta a los 60 s quedan EXPIRADA y la reserva vuelve a SOLICITADO.
    Puede correr varias veces o en paralelo sin efectos duplicados. Devuelve cuántas expiró."""
    ahora = ahora or timezone.now()
    limite = ahora - timedelta(seconds=SEGUNDOS_PARA_RESPONDER)
    expiradas = 0
    for asignacion_id in Asignacion.objects.filter(
        resultado__isnull=True, enviada_en__lte=limite
    ).values_list("pk", flat=True):
        with transaction.atomic():
            asignacion = (
                Asignacion.objects.select_for_update(of=("self",), skip_locked=True)
                .select_related("viaje")
                .filter(pk=asignacion_id, resultado__isnull=True)
                .first()
            )
            if asignacion is None:
                continue  # la respondió el conductor o la tomó otro proceso
            asignacion.resultado = ResultadoAsignacion.EXPIRADA
            asignacion.save(update_fields=["resultado"])
            if asignacion.viaje.estado == EstadoViaje.ASIGNADO:
                _volver_a_solicitado(asignacion, actor=Actor.SISTEMA)
            transaction.on_commit(lambda a=asignacion: _avisar_fin(a))
        expiradas += 1
    return expiradas
