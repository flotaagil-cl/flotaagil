"""Reglas comunes de las solicitudes web: límites, vuelo y hora de recogida.

Desde HU-40 (CC-18) no hay pedido sin cuenta: las usan el pasajero con cuenta
(`/api/mi-cuenta/solicitudes/`) y la empresa en convenio (`/api/mi-convenio/solicitudes/`)."""

from datetime import datetime, time, timedelta

from django.conf import settings
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import Throttled, ValidationError

from apps.reservas import servicios as reservas
from apps.reservas.models import Canal, TipoVuelo, Viaje


class LimiteIP(Throttled):
    """429 por IP (throttling de DRF). El `code` permite al portal explicar el caso sin leer el texto."""

    default_code = "limite_ip"
    default_detail = (
        "Se enviaron demasiadas solicitudes desde esta conexión. Espera un momento e intenta de nuevo."
    )


class LimiteTelefono(Throttled):
    """429 por teléfono: demasiadas solicitudes con el mismo número en la ventana."""

    default_code = "limite_telefono"
    default_detail = "Ya enviaste varias solicitudes con este número. Espera unos minutos e intenta de nuevo."


def _verificar_limite_telefono(empresa, telefono: str) -> None:
    """Máximo de solicitudes por número y empresa en la ventana (alineado con RN-06: 3 cada 15 min)."""
    desde = timezone.now() - settings.PORTAL_VENTANA_TELEFONO
    recientes = Viaje.objects.filter(
        empresa=empresa, canal=Canal.WEB, pasajero__telefono=telefono, creado_en__gte=desde
    ).count()
    if recientes >= settings.PORTAL_MAX_SOLICITUDES_POR_TELEFONO:
        raise LimiteTelefono(wait=settings.PORTAL_VENTANA_TELEFONO.total_seconds())


def capacidad_maxima(empresa) -> int | None:
    """DC-43: capacidad del vehículo activo más grande de la empresa (None si no tiene vehículos activos)."""
    from apps.flota.models import Vehiculo

    return Vehiculo.objects.filter(empresa=empresa, activo=True).aggregate(maximo=Max("capacidad"))["maximo"]


def validar_capacidad(empresa, pasajeros: int) -> None:
    """DC-43: titular más acompañantes no superan la mayor capacidad de la flota activa. Sin vehículos
    activos no se limita: la central decide al asignar (y al asignar se exige la capacidad del vehículo)."""
    maximo = capacidad_maxima(empresa)
    if maximo is not None and pasajeros > maximo:
        raise ValidationError(
            {
                "pasajeros": [
                    f"Podemos llevar hasta {maximo} pasajeros en un vehículo. "
                    "Pide otro traslado para el resto."
                ]
            }
        )


def _hora_de_recogida(datos: dict, config):
    """RN-17: desde el aeropuerto, si no viene la hora de recogida es la llegada + margen.

    VUELO no distingue nacional de internacional (DC-12): se usa el margen nacional. Al aeropuerto (HU-39), la
    hora del vuelo de salida menos la antelación de su tipo (DC-42).
    """
    if "recogida_en" in datos:
        return datos["recogida_en"]
    if datos.get("vuelo_salida"):
        salida = datos["vuelo_salida"]
        antelacion = (
            config.antelacion_vuelo_internacional_min
            if salida["tipo"] == TipoVuelo.INTERNACIONAL
            else config.antelacion_vuelo_nacional_min
        )
        return salida["hora"] - timedelta(minutes=antelacion)
    return datos["vuelo"]["hora_llegada"] + timedelta(minutes=config.margen_nacional_min)


def _llegada_por_fecha(vuelo: dict) -> dict:
    """HU-39: con solo el número y la fecha, la hora de llegada la da la API de vuelos. Si no se pudo
    consultar, se pide la hora para no inventarla."""
    mediodia = timezone.make_aware(datetime.combine(vuelo["fecha"], time(12)))
    verificado = reservas.verificar_vuelo({"numero": vuelo["numero"], "hora_programada": mediodia})
    if not verificado["verificado"]:
        raise ValidationError(
            {
                "vuelo": {
                    "hora_llegada": [
                        "No pudimos consultar tu vuelo en este momento. Indica la hora de llegada."
                    ]
                }
            }
        )
    return verificado


def vuelo_y_recogida(empresa, datos: dict) -> tuple[dict | None, object]:
    """Vuelo verificado y hora de recogida, que debe respetar la anticipación mínima. También para HU-25.

    Con `lo_antes_posible` (HU-39) la recogida es ahora + la anticipación mínima (DC-10).
    """
    config = empresa.configuracion
    minimo = timezone.now() + timedelta(minutes=config.anticipacion_minima_min)
    vuelo_verificado = None
    if datos.get("vuelo"):
        vuelo = datos["vuelo"]
        if "hora_llegada" in vuelo:
            # HU-26: la recogida calculada (RN-17) usa la hora de llegada confirmada por la API de vuelos.
            vuelo_verificado = reservas.verificar_vuelo(
                {"numero": vuelo["numero"], "hora_programada": vuelo["hora_llegada"]}
            )
        else:
            vuelo_verificado = _llegada_por_fecha(vuelo)
        datos = {**datos, "vuelo": {**vuelo, "hora_llegada": vuelo_verificado["hora_programada"]}}
    if datos.get("lo_antes_posible"):
        # Al minuto siguiente: la recogida nunca queda bajo el mínimo.
        return vuelo_verificado, minimo.replace(second=0, microsecond=0) + timedelta(minutes=1)
    recogida = _hora_de_recogida(datos, config)
    if recogida < minimo:
        minutos = config.anticipacion_minima_min
        raise ValidationError(
            {"recogida_en": [f"La recogida debe ser al menos {minutos} minutos después de ahora."]}
        )
    return vuelo_verificado, recogida
