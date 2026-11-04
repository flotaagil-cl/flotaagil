"""Casos de uso de reservas: crear, editar y cancelar viajes (HU-03).

El portal (HU-19) reutiliza crear_viaje.
"""

import logging

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from apps.aeropuerto.models import EstadoVuelo, Vuelo
from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad
from apps.cuentas.models import Rol
from apps.integraciones.geocodificador import (
    Coordenadas,
    GeocodificacionError,
    Zona,
    obtener_geocodificador,
)
from apps.integraciones.vuelos import VuelosNoDisponibles, obtener_consultor_vuelos

from . import estados, tareas
from .models import EstadoViaje, MetodoPago, OrigenCancelacion, PagoViaje, Pasajero, Sentido, Viaje

logger = logging.getLogger(__name__)


class ConflictoEstado(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflicto_estado"
    default_detail = "La reserva no admite esta operación en su estado actual."


def normalizar_vuelo(numero: str) -> str:
    return " ".join(numero.upper().split())


def _punto(direccion: str, zona: Zona, geocodificador, campo: str) -> Point:
    try:
        coordenadas = geocodificador.geocodificar(direccion, zona)
    except GeocodificacionError as error:
        raise ValidationError({campo: [str(error)]}) from error
    return Point(coordenadas.lon, coordenadas.lat, srid=4326)


def _validar_origen_en_zona(punto: Point, zona: Zona) -> None:
    if not zona.contiene(Coordenadas(lat=punto.y, lon=punto.x)):
        raise ValidationError({"origen_dir": ["El origen está fuera de la zona de operación de la empresa."]})


def _validar_recogida(recogida_en) -> None:
    if recogida_en <= timezone.now():
        raise ValidationError({"recogida_en": ["La hora de recogida debe ser futura."]})


def _validar_vuelo(sentido: str, vuelo: dict | None) -> None:
    if vuelo and sentido != Sentido.DESDE_AEROPUERTO:
        raise ValidationError(
            {"vuelo": ["El vuelo solo se registra en viajes desde el aeropuerto (llegadas)."]}
        )


def verificar_vuelo(vuelo: dict, consultor=None) -> dict:
    """HU-26: consulta inicial a la API de vuelos.

    - No existe una llegada de ese vuelo al aeropuerto ese día: 400 en `vuelo.numero`.
    - Existe: se guarda la hora programada de la API (corrige la informada, DC-06), la estimada y el estado.
    - La API no responde: se guarda como se informó, sin verificar (`ultima_consulta_en` vacío), para no
      bloquear la reserva. La tarea `consultar_vuelo` reintenta; el monitoreo (HU-27/HU-28) avisa si sigue
      sin datos.
    """
    consultor = consultor or obtener_consultor_vuelos()
    numero = normalizar_vuelo(vuelo["numero"])
    informada = vuelo["hora_programada"]
    try:
        datos = consultor.consultar(numero, informada)
    except VuelosNoDisponibles as error:
        logger.warning("Vuelo %s sin verificar: %s", numero, error)
        return {"numero": numero, "hora_programada": informada, "verificado": False}
    if datos is None:
        dia = timezone.localtime(informada).strftime("%d-%m-%Y")
        raise ValidationError(
            {
                "vuelo": {
                    "numero": [
                        f"No encontramos el vuelo {numero} con llegada a {settings.AEROPUERTO_IATA} "
                        f"el {dia}. Revisa el número y la fecha."
                    ]
                }
            }
        )
    return {
        "numero": numero,
        "hora_programada": datos.hora_programada,
        "hora_estimada": datos.hora_estimada,
        "estado_vuelo": datos.estado,
        "ultima_consulta_en": timezone.now(),
        "verificado": True,
    }


def _guardar_vuelo(viaje: Viaje, vuelo: dict | None) -> None:
    Vuelo.objects.filter(viaje=viaje).delete()
    if vuelo:
        hora = vuelo["hora_programada"]
        creado = Vuelo.objects.create(
            viaje=viaje,
            numero=normalizar_vuelo(vuelo["numero"]),
            fecha=timezone.localdate(hora),
            hora_programada=hora,
            hora_estimada=vuelo.get("hora_estimada"),
            estado_vuelo=vuelo.get("estado_vuelo") or EstadoVuelo.PROGRAMADO,
            ultima_consulta_en=vuelo.get("ultima_consulta_en"),
        )
        if creado.ultima_consulta_en is None:
            # La API no respondió al registrarlo: se reintenta en segundo plano.
            tareas.al_confirmar(tareas.consultar_vuelo, creado.pk)


def obtener_pasajero(empresa, *, nombre: str, telefono: str) -> Pasajero:
    pasajero, _ = Pasajero.objects.get_or_create(
        empresa=empresa, telefono=telefono, defaults={"nombre": nombre}
    )
    return pasajero


def crear_viaje(
    *,
    empresa,
    datos: dict,
    canal: str,
    estado_inicial: str,
    actor: str,
    usuario=None,
    geocodificador=None,
    validar_futuro: bool = True,
) -> Viaje:
    """Crea la reserva con sus coordenadas, el vuelo (si corresponde) y el primer registro del historial.

    Estado inicial: SOLICITADO si la ingresa el despachador o llega por convenio; PENDIENTE_CONFIRMACION
    si llega desde el portal (RN-06).
    """
    geocodificador = geocodificador or obtener_geocodificador()
    zona = Zona.de_configuracion(empresa.configuracion)
    sentido = datos.get("sentido") or Sentido.URBANO
    vuelo = datos.get("vuelo")
    if validar_futuro:
        _validar_recogida(datos["recogida_en"])
    _validar_vuelo(sentido, vuelo)
    if vuelo and "verificado" not in vuelo:
        vuelo = verificar_vuelo(vuelo)
    origen = _punto(datos["origen_dir"], zona, geocodificador, "origen_dir")
    _validar_origen_en_zona(origen, zona)
    destino = _punto(datos["destino_dir"], zona, geocodificador, "destino_dir")

    with transaction.atomic():
        pasajero = obtener_pasajero(empresa, **datos["pasajero"])
        viaje = Viaje.objects.create(
            empresa=empresa,
            pasajero=pasajero,
            convenio=datos.get("convenio"),
            canal=canal,
            sentido=sentido,
            origen_dir=datos["origen_dir"],
            origen_geo=origen,
            destino_dir=datos["destino_dir"],
            destino_geo=destino,
            recogida_en=datos["recogida_en"],
            tarifa=datos.get("tarifa"),
            estado=estado_inicial,
        )
        _guardar_vuelo(viaje, vuelo)
        estados.registrar_inicial(viaje, actor=actor, usuario=usuario)
    return viaje


def editar_viaje(viaje: Viaje, datos: dict, *, geocodificador=None) -> Viaje:
    """HU-03: edición antes del despacho (PENDIENTE_CONFIRMACION o SOLICITADO)."""
    if viaje.estado not in estados.EDITABLES:
        raise ConflictoEstado(
            "Solo se puede editar una reserva pendiente de confirmación o solicitada (antes del despacho)."
        )
    geocodificador = geocodificador or obtener_geocodificador()
    zona = Zona.de_configuracion(viaje.empresa.configuracion)

    sentido = datos.get("sentido", viaje.sentido)
    # El vuelo existente solo se toca si se envía uno nuevo (o null) o si el viaje deja de ser desde el
    # aeropuerto; así se conservan la ETA y el estado que registra el monitoreo (HU-27).
    reemplazar_vuelo = "vuelo" in datos or sentido != Sentido.DESDE_AEROPUERTO
    if "vuelo" in datos:
        _validar_vuelo(sentido, datos["vuelo"])
        if datos["vuelo"]:
            datos = {**datos, "vuelo": verificar_vuelo(datos["vuelo"])}
    if "recogida_en" in datos:
        _validar_recogida(datos["recogida_en"])

    campos = {k: datos[k] for k in ("sentido", "recogida_en", "tarifa") if k in datos}
    if "origen_dir" in datos and datos["origen_dir"] != viaje.origen_dir:
        campos["origen_dir"] = datos["origen_dir"]
        campos["origen_geo"] = _punto(datos["origen_dir"], zona, geocodificador, "origen_dir")
        _validar_origen_en_zona(campos["origen_geo"], zona)
    if "destino_dir" in datos and datos["destino_dir"] != viaje.destino_dir:
        campos["destino_dir"] = datos["destino_dir"]
        campos["destino_geo"] = _punto(datos["destino_dir"], zona, geocodificador, "destino_dir")

    with transaction.atomic():
        for campo, valor in campos.items():
            setattr(viaje, campo, valor)
        if campos:
            viaje.save(update_fields=list(campos))
        if reemplazar_vuelo:
            _guardar_vuelo(viaje, datos.get("vuelo"))
    return Viaje.objects.get(pk=viaje.pk)


ORIGEN_POR_ROL = {
    Rol.ADMINISTRADOR: OrigenCancelacion.ADMINISTRADOR,
    Rol.DESPACHADOR: OrigenCancelacion.DESPACHADOR,
}


def _liberar_conductor(conductor, viaje: Viaje) -> None:
    """El viaje cancelado ya no ocupa al conductor: vuelve a Disponible y la app se entera."""
    from apps.flota.models import Conductor, EstadoConductor
    from apps.flota.tiempo_real import notificar_conductor

    from .ejecucion import avisar_viaje_actualizado

    Conductor.objects.filter(pk=conductor.pk, estado=EstadoConductor.EN_VIAJE).update(
        estado=EstadoConductor.DISPONIBLE
    )
    conductor.refresh_from_db()
    notificar_conductor(conductor)
    conductor_id, viaje_id = conductor.pk, viaje.pk
    transaction.on_commit(lambda: avisar_viaje_actualizado(conductor_id, viaje_id))


def cancelar_viaje(viaje: Viaje, *, motivo: str, usuario) -> Viaje:
    """Cancelación desde el panel: exige motivo, registra el historial y la auditoría.

    origen_cancelacion es DESPACHADOR o ADMINISTRADOR según el rol de quien cancela (DC-08).
    """
    if viaje.estado not in estados.CANCELABLES:
        raise ConflictoEstado(f"Una reserva en estado {viaje.estado} no se puede cancelar desde aquí.")
    estado_previo = viaje.estado
    conductor = viaje.conductor
    with transaction.atomic():
        try:
            viaje = estados.transicionar(
                viaje,
                EstadoViaje.CANCELADO,
                actor=estados.actor_de(usuario),
                usuario=usuario,
                motivo_cancelacion=motivo,
                origen_cancelacion=ORIGEN_POR_ROL[usuario.rol],
            )
        except estados.TransicionInvalida as error:
            raise ConflictoEstado(str(error)) from error
        auditoria.registrar(
            usuario=usuario,
            entidad=Entidad.VIAJE,
            entidad_id=viaje.pk,
            accion="CANCELACION",
            motivo=motivo,
            datos_previos={"estado": estado_previo},
        )
        if conductor is not None:
            _liberar_conductor(conductor, viaje)
    return viaje


def _viaje_a_bordo(viaje: Viaje) -> Viaje:
    """HU-05: solo con el pasajero a bordo. Antes de eso existe la cancelación normal."""
    viaje = Viaje.objects.select_for_update(of=("self",)).select_related("conductor").get(pk=viaje.pk)
    if viaje.estado != EstadoViaje.PASAJERO_A_BORDO:
        raise ConflictoEstado(f"Solo se fuerza con el pasajero a bordo; la reserva está en {viaje.estado}.")
    return viaje


@transaction.atomic
def anular_forzado(viaje: Viaje, *, motivo: str, usuario) -> Viaje:
    """RN-11: anulación con motivo, en auditoría con el responsable."""
    viaje = _viaje_a_bordo(viaje)
    conductor = viaje.conductor
    viaje = estados.transicionar(
        viaje,
        EstadoViaje.CANCELADO,
        actor=estados.actor_de(usuario),
        usuario=usuario,
        forzada=True,
        desde=EstadoViaje.PASAJERO_A_BORDO,
        motivo_cancelacion=motivo,
        origen_cancelacion=ORIGEN_POR_ROL[usuario.rol],
    )
    auditoria.registrar(
        usuario=usuario,
        entidad=Entidad.VIAJE,
        entidad_id=viaje.pk,
        accion="ANULACION_FORZADA",
        motivo=motivo,
        datos_previos={"estado": EstadoViaje.PASAJERO_A_BORDO},
    )
    if conductor is not None:
        _liberar_conductor(conductor, viaje)
    return viaje


@transaction.atomic
def cerrar_forzado(viaje: Viaje, *, motivo: str, metodo: str, monto: int, usuario) -> Viaje:
    """RN-10 y RN-11: tampoco se finaliza sin método de pago y monto. Sin encuesta: fue un caso anómalo."""
    viaje = _viaje_a_bordo(viaje)
    if metodo == MetodoPago.CONVENIO and viaje.convenio_id is None:
        raise ValidationError({"metodo": ["Este viaje no pertenece a un convenio."]})
    conductor = viaje.conductor
    PagoViaje.objects.create(viaje=viaje, metodo=metodo, monto=monto)
    viaje = estados.transicionar(
        viaje,
        EstadoViaje.FINALIZADO,
        actor=estados.actor_de(usuario),
        usuario=usuario,
        desde=EstadoViaje.PASAJERO_A_BORDO,
    )
    auditoria.registrar(
        usuario=usuario,
        entidad=Entidad.VIAJE,
        entidad_id=viaje.pk,
        accion="CIERRE_FORZADO",
        motivo=motivo,
        datos_previos={"estado": EstadoViaje.PASAJERO_A_BORDO, "metodo": metodo, "monto": monto},
    )
    if conductor is not None:
        _liberar_conductor(conductor, viaje)
    return viaje
