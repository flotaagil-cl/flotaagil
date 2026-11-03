"""Reglas de la administración de flota (HU-10): activar y desactivar vehículos, asociar vehículos a
conductores y editar los datos del conductor. Cada cambio queda en AUDITORIA."""

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad
from apps.reservas.models import EstadoViaje, Viaje

from .models import Conductor, ConductorVehiculo, EstadoConductor, Vehiculo

# Estados del viaje en que el vehículo está comprometido con un servicio.
ESTADOS_VIAJE_EN_CURSO = frozenset(
    {
        EstadoViaje.ASIGNADO,
        EstadoViaje.ACEPTADO,
        EstadoViaje.EN_CAMINO,
        EstadoViaje.EN_ZONA,
        EstadoViaje.PASAJERO_A_BORDO,
    }
)
# Estados del conductor en que su vehículo declarado no se puede retirar (RN-05).
ESTADOS_CONDUCTOR_EN_TURNO = frozenset({EstadoConductor.DISPONIBLE, EstadoConductor.EN_VIAJE})


class FlotaEnUso(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "flota_en_uso"
    default_detail = "El vehículo está en uso."


def _en_turno_con(vehiculo: Vehiculo, conductor: Conductor | None = None):
    conductores = Conductor.objects.filter(vehiculo_activo=vehiculo, estado__in=ESTADOS_CONDUCTOR_EN_TURNO)
    if conductor is not None:
        conductores = conductores.filter(pk=conductor.pk)
    return conductores.select_related("usuario").first()


def _liberar_declaracion(vehiculo: Vehiculo, conductor: Conductor | None = None) -> None:
    """Quita el vehículo como declarado a los conductores fuera de turno (NO_DISPONIBLE)."""
    conductores = Conductor.objects.filter(vehiculo_activo=vehiculo, estado=EstadoConductor.NO_DISPONIBLE)
    if conductor is not None:
        conductores = conductores.filter(pk=conductor.pk)
    conductores.update(vehiculo_activo=None)


@transaction.atomic
def editar_vehiculo(vehiculo: Vehiculo, datos: dict, *, usuario) -> Vehiculo:
    vehiculo = Vehiculo.objects.select_for_update().get(pk=vehiculo.pk)
    previos = {campo: getattr(vehiculo, campo) for campo in datos if getattr(vehiculo, campo) != datos[campo]}
    if not previos:
        return vehiculo
    if previos.get("activo") is True:
        # Se está desactivando: no puede estar en un turno ni en un viaje en curso.
        en_turno = _en_turno_con(vehiculo)
        if en_turno:
            raise FlotaEnUso(
                f"El vehículo está declarado por {en_turno.usuario.nombre}, que está en turno. "
                "Debe quedar No disponible antes de desactivarlo."
            )
        if Viaje.objects.filter(vehiculo=vehiculo, estado__in=ESTADOS_VIAJE_EN_CURSO).exists():
            raise FlotaEnUso("El vehículo tiene un viaje en curso.")
        _liberar_declaracion(vehiculo)
    for campo, valor in datos.items():
        setattr(vehiculo, campo, valor)
    vehiculo.save(update_fields=list(previos))
    accion = "EDITAR"
    if "activo" in previos:
        accion = "ACTIVAR" if vehiculo.activo else "DESACTIVAR"
    auditoria.registrar(
        usuario=usuario,
        entidad=Entidad.VEHICULO,
        entidad_id=vehiculo.pk,
        accion=accion,
        datos_previos=previos,
    )
    return vehiculo


@transaction.atomic
def crear_vehiculos(empresa, filas: list[dict], *, usuario) -> list[Vehiculo]:
    vehiculos = Vehiculo.objects.bulk_create([Vehiculo(empresa=empresa, **fila) for fila in filas])
    for vehiculo in vehiculos:
        auditoria.registrar(usuario=usuario, entidad=Entidad.VEHICULO, entidad_id=vehiculo.pk, accion="CREAR")
    return vehiculos


@transaction.atomic
def editar_conductor(conductor: Conductor, datos: dict, *, usuario) -> Conductor:
    conductor = Conductor.objects.select_for_update().select_related("usuario").get(pk=conductor.pk)
    previos = {}
    nombre = datos.pop("nombre", None)
    if nombre is not None and nombre != conductor.usuario.nombre:
        previos["nombre"] = conductor.usuario.nombre
        conductor.usuario.nombre = nombre
        conductor.usuario.save(update_fields=["nombre"])
    cambios = [campo for campo, valor in datos.items() if getattr(conductor, campo) != valor]
    for campo in cambios:
        valor_previo = getattr(conductor, campo)
        previos[campo] = valor_previo.isoformat() if hasattr(valor_previo, "isoformat") else valor_previo
        setattr(conductor, campo, datos[campo])
    if cambios:
        conductor.save(update_fields=cambios)
    if previos:
        auditoria.registrar(
            usuario=usuario,
            entidad=Entidad.CONDUCTOR,
            entidad_id=conductor.pk,
            accion="EDITAR",
            datos_previos=previos,
        )
    return conductor


@transaction.atomic
def asociar_vehiculo(conductor: Conductor, vehiculo: Vehiculo, *, usuario) -> None:
    if not vehiculo.activo:
        raise ValidationError({"vehiculo": ["El vehículo está inactivo."]})
    _, creada = ConductorVehiculo.objects.get_or_create(conductor=conductor, vehiculo=vehiculo)
    if not creada:
        raise ValidationError({"vehiculo": ["El vehículo ya está asociado a este conductor."]})
    auditoria.registrar(
        usuario=usuario,
        entidad=Entidad.CONDUCTOR,
        entidad_id=conductor.pk,
        accion="ASOCIAR_VEHICULO",
        datos_previos={"vehiculo_id": vehiculo.pk, "patente": vehiculo.patente},
    )


@transaction.atomic
def desasociar_vehiculo(conductor: Conductor, vehiculo: Vehiculo, *, usuario) -> None:
    conductor = Conductor.objects.select_for_update().get(pk=conductor.pk)
    asociacion = ConductorVehiculo.objects.filter(conductor=conductor, vehiculo=vehiculo)
    if not asociacion.exists():
        raise ValidationError({"vehiculo": ["El vehículo no está asociado a este conductor."]})
    if _en_turno_con(vehiculo, conductor):
        raise FlotaEnUso(
            "Es el vehículo declarado del turno en curso. El conductor debe quedar No disponible antes de "
            "quitarlo."
        )
    _liberar_declaracion(vehiculo, conductor)
    asociacion.delete()
    auditoria.registrar(
        usuario=usuario,
        entidad=Entidad.CONDUCTOR,
        entidad_id=conductor.pk,
        accion="DESASOCIAR_VEHICULO",
        datos_previos={"vehiculo_id": vehiculo.pk, "patente": vehiculo.patente},
    )
