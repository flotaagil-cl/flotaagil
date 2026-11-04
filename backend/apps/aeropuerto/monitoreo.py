"""Monitoreo del vuelo y ajuste de la recogida (HU-27, RN-17, RN-02).

Desde `consulta_vuelo_desde_min` antes de la llegada se consulta cada `consulta_vuelo_cada_min`, y cada
`consulta_vuelo_final_cada_min` en la última `consulta_vuelo_final_ventana_min`. Si la ETA cambia en
`cambio_eta_min` o más respecto de la última referencia, se PROPONE recogida = ETA + margen (RN-17).

La recogida no cambia hasta que el despachador lo confirma (RN-02). Confirmar o descartar fija una nueva
referencia: la misma ETA no se vuelve a proponer. El margen es internacional si el vuelo viene de fuera de
Chile; sin origen conocido, nacional (DC-12, DC-22).
"""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad

from .models import EstadoVuelo, Vuelo

# Aeropuertos con vuelos comerciales en Chile: un vuelo desde otro origen usa el margen internacional.
# fmt: off
AEROPUERTOS_DE_CHILE = frozenset({
    "ARI", "IQQ", "CJC", "ANF", "CPO", "LSC", "ZCO", "PMC", "ZAL", "ZOS", "WPU", "CCP",
    "BBA", "GXQ", "PUQ", "WCA", "SCL", "TLX", "FTE", "IPC", "YAI", "LOB", "ESR", "PNT",
})
# fmt: on
ESTADOS_FINALES = (EstadoVuelo.ATERRIZADO, EstadoVuelo.CANCELADO, EstadoVuelo.DESVIADO)
# Después de esto no se sigue gastando consultas en un vuelo que la API nunca marcó como aterrizado.
HORAS_TRAS_LA_LLEGADA = 2


class PropuestaNoVigente(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "propuesta_no_vigente"
    default_detail = "La propuesta cambió o ya se resolvió. Revisa la hora actual."


def _estados_monitoreados():
    from apps.reservas.models import EstadoViaje as E

    return (E.SOLICITADO, E.ASIGNADO, E.ACEPTADO, E.EN_CAMINO, E.EN_ZONA, E.PASAJERO_A_BORDO)


def _estados_ajustables():
    from apps.reservas.models import EstadoViaje as E

    return (E.SOLICITADO, E.ASIGNADO, E.ACEPTADO, E.EN_CAMINO)


def eta_de(vuelo: Vuelo):
    return vuelo.hora_estimada or vuelo.hora_programada


def es_internacional(origen_iata: str | None) -> bool:
    return bool(origen_iata) and origen_iata not in AEROPUERTOS_DE_CHILE


def margen_de(vuelo: Vuelo, configuracion) -> timedelta:
    minutos = (
        configuracion.margen_internacional_min
        if es_internacional(vuelo.origen_iata)
        else configuracion.margen_nacional_min
    )
    return timedelta(minutes=minutos)


def intervalo_de(eta, ahora, configuracion) -> timedelta | None:
    """Cada cuánto consultar ahora; None si está fuera de la ventana de monitoreo."""
    falta = eta - ahora
    if falta > timedelta(minutes=configuracion.consulta_vuelo_desde_min):
        return None
    if falta < -timedelta(hours=HORAS_TRAS_LA_LLEGADA):
        return None
    if falta <= timedelta(minutes=configuracion.consulta_vuelo_final_ventana_min):
        return timedelta(minutes=configuracion.consulta_vuelo_final_cada_min)
    return timedelta(minutes=configuracion.consulta_vuelo_cada_min)


def vuelos_por_consultar(ahora=None) -> list[Vuelo]:
    """Los que toca consultar, los más atrasados primero, hasta el límite de la API por minuto."""
    ahora = ahora or timezone.now()
    candidatos = (
        Vuelo.objects.filter(viaje__estado__in=_estados_monitoreados())
        .exclude(estado_vuelo__in=ESTADOS_FINALES)
        .filter(
            hora_programada__gte=ahora - timedelta(days=1),
            hora_programada__lte=ahora + timedelta(days=1),
        )
        .select_related("viaje__empresa__configuracion")
    )
    pendientes = []
    for vuelo in candidatos:
        cada = intervalo_de(eta_de(vuelo), ahora, vuelo.viaje.empresa.configuracion)
        if cada is None:
            continue
        ultima = vuelo.ultima_consulta_en
        if ultima is None or ahora - ultima >= cada:
            pendientes.append(vuelo)
    pendientes.sort(key=lambda v: v.ultima_consulta_en or v.hora_programada - timedelta(days=30))
    return pendientes[: settings.VUELOS_CONSULTAS_POR_MINUTO]


@transaction.atomic
def aplicar(vuelo_id: int, datos) -> Vuelo:
    """Guarda lo que informó la API y actualiza la propuesta. Nunca cambia la recogida (RN-02)."""
    from apps.reservas.models import Viaje

    vuelo = Vuelo.objects.select_for_update().get(pk=vuelo_id)
    viaje = Viaje.objects.select_related("empresa__configuracion").get(pk=vuelo.viaje_id)
    configuracion = viaje.empresa.configuracion
    referencia = vuelo.eta_referencia or vuelo.hora_programada
    vuelo.hora_programada = datos.hora_programada
    vuelo.hora_estimada = datos.hora_estimada
    vuelo.estado_vuelo = datos.estado
    vuelo.origen_iata = datos.origen_iata or vuelo.origen_iata
    vuelo.ultima_consulta_en = timezone.now()

    eta = eta_de(vuelo)
    propuesta = None
    if (
        viaje.estado in _estados_ajustables()
        and datos.estado not in (EstadoVuelo.CANCELADO, EstadoVuelo.DESVIADO)
        and abs(eta - referencia) >= timedelta(minutes=configuracion.cambio_eta_min)
    ):
        propuesta = eta + margen_de(vuelo, configuracion)
        if abs(propuesta - viaje.recogida_en) < timedelta(minutes=1):
            propuesta = None  # la recogida ya es esa
    if propuesta != vuelo.recogida_propuesta:
        vuelo.propuesta_en = timezone.now() if propuesta else None
    vuelo.recogida_propuesta = propuesta
    vuelo.save()
    return vuelo


def _propuesta_vigente(viaje, esperada) -> Vuelo:
    vuelo = Vuelo.objects.select_for_update().filter(viaje=viaje).first()
    if vuelo is None or vuelo.recogida_propuesta is None or vuelo.recogida_propuesta != esperada:
        raise PropuestaNoVigente()
    if viaje.estado not in _estados_ajustables():
        raise PropuestaNoVigente("El viaje ya no admite cambiar la recogida.")
    return vuelo


def _resolver(vuelo: Vuelo) -> None:
    vuelo.eta_referencia = eta_de(vuelo)
    vuelo.recogida_propuesta = None
    vuelo.propuesta_en = None
    vuelo.save(update_fields=["eta_referencia", "recogida_propuesta", "propuesta_en"])


@transaction.atomic
def confirmar(viaje, *, usuario, esperada):
    """RN-02: el despachador confirma. Si el vuelo cambió mientras lo miraba, 409: no confirma lo no visto."""
    from apps.reservas.ejecucion import avisar_viaje_actualizado
    from apps.reservas.models import Viaje

    viaje = Viaje.objects.select_for_update(of=("self",)).get(pk=viaje.pk)
    vuelo = _propuesta_vigente(viaje, esperada)
    anterior = viaje.recogida_en
    viaje.recogida_en = vuelo.recogida_propuesta
    viaje.save(update_fields=["recogida_en"])
    auditoria.registrar(
        usuario=usuario,
        entidad=Entidad.VIAJE,
        entidad_id=viaje.pk,
        accion="AJUSTE_RECOGIDA",
        datos_previos={"recogida_en": anterior.isoformat(), "eta": eta_de(vuelo).isoformat()},
    )
    _resolver(vuelo)
    if viaje.conductor_id:
        conductor_id, viaje_id = viaje.conductor_id, viaje.pk
        transaction.on_commit(lambda: avisar_viaje_actualizado(conductor_id, viaje_id))
    return viaje


@transaction.atomic
def descartar(viaje, *, usuario, esperada):
    from apps.reservas.models import Viaje

    viaje = Viaje.objects.select_for_update(of=("self",)).get(pk=viaje.pk)
    vuelo = _propuesta_vigente(viaje, esperada)
    auditoria.registrar(
        usuario=usuario,
        entidad=Entidad.VIAJE,
        entidad_id=viaje.pk,
        accion="DESCARTE_RECOGIDA",
        datos_previos={"recogida_propuesta": vuelo.recogida_propuesta.isoformat()},
    )
    _resolver(vuelo)
    return viaje
