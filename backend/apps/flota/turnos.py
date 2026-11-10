"""HU-31 (CC-12): turnos del conductor y cierre de caja.

Un turno se abre al empezar el turno (Disponible) y se cierra al terminarlo, al deshabilitar la cuenta o por
cierre administrativo. Cambiar de vehículo cierra el turno y abre otro. El viaje guarda su turno al aceptarse
(`reservas.asignacion.responder`), así que un cierre forzado posterior (HU-05) sigue sumando en ese turno.

Orden de bloqueo (CP-14): estas funciones se llaman con la fila del conductor ya bloqueada, o bloquean solo el
turno; nunca bloquean un viaje.
"""

from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad

from .models import CierreCaja, Conductor, EstadoConductor, MotivoTerminoTurno, Turno


class ConflictoTurno(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflicto_turno"
    default_detail = "La operación no corresponde al estado del turno."


def turno_abierto(conductor_id: int) -> Turno | None:
    return Turno.objects.filter(conductor_id=conductor_id, hora_termino__isnull=True).first()


def abrir(conductor: Conductor, vehiculo, momento=None) -> Turno:
    """Abre un turno. Quien llama tiene la fila del conductor bloqueada y ya cerró el anterior."""
    return Turno.objects.create(conductor=conductor, vehiculo=vehiculo, hora_inicio=momento or timezone.now())


def cerrar(conductor_id: int, motivo: str, momento=None) -> Turno | None:
    """Cierra el turno abierto del conductor, si lo hay. Quien llama tiene la fila del conductor bloqueada."""
    turno = turno_abierto(conductor_id)
    if turno is None:
        return None
    turno.hora_termino = max(momento or timezone.now(), turno.hora_inicio)
    turno.motivo_termino = motivo
    turno.save(update_fields=["hora_termino", "motivo_termino"])
    return turno


def cerrar_administrativo(conductor: Conductor, *, motivo: str, usuario) -> Turno:
    """El administrador termina el turno de un conductor que olvidó terminarlo: queda No disponible, sin
    vehículo declarado, y el turno se cierra con CIERRE_ADMINISTRATIVO (DC-32). No se puede en viaje
    (RN-03)."""
    from apps.aeropuerto.fila import salir
    from apps.aeropuerto.models import MotivoSalidaFila

    from .tiempo_real import avisar_indicadores, notificar_conductor

    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError({"motivo": ["Indica el motivo del cierre administrativo."]})
    with transaction.atomic():
        conductor = (
            Conductor.objects.select_for_update(of=("self",)).select_related("usuario").get(pk=conductor.pk)
        )
        if conductor.estado == EstadoConductor.EN_VIAJE:
            raise ConflictoTurno(
                f"{conductor.usuario.nombre} está en un viaje: el turno se termina al cerrarlo (RN-03).",
                code="en_viaje",
            )
        turno = turno_abierto(conductor.pk)
        if turno is None:
            raise ConflictoTurno(f"{conductor.usuario.nombre} no tiene un turno abierto.", code="sin_turno")
        previo = conductor.estado
        conductor.estado, conductor.vehiculo_activo = EstadoConductor.NO_DISPONIBLE, None
        conductor.save(update_fields=["estado", "vehiculo_activo"])
        cerrar(conductor.pk, MotivoTerminoTurno.CIERRE_ADMINISTRATIVO)
        turno.refresh_from_db()
        salir(conductor, MotivoSalidaFila.NO_DISPONIBLE)  # HU-29
        auditoria.registrar(
            usuario=usuario,
            entidad=Entidad.TURNO,
            entidad_id=turno.pk,
            accion="CIERRE_ADMINISTRATIVO",
            motivo=motivo[:200],
            datos_previos={"conductor_id": conductor.pk, "estado": previo},
        )
        notificar_conductor(conductor)
        avisar_indicadores(conductor.usuario.empresa_id)
    return turno


# --- Cierre de caja ---


def _viajes_finalizados(turno_id):
    from apps.reservas.models import EstadoViaje, Viaje

    return Viaje.objects.filter(turno_id=turno_id, estado=EstadoViaje.FINALIZADO, pago__isnull=False)


def efectivo_registrado(turno_id: int) -> int:
    from apps.reservas.models import MetodoPago

    total = (
        _viajes_finalizados(turno_id).filter(pago__metodo=MetodoPago.EFECTIVO).aggregate(t=Sum("pago__monto"))
    )
    return total["t"] or 0


def por_cerrar(empresa_id: int):
    """Turnos terminados de la empresa sin cierre de caja, con el efectivo registrado y sus viajes."""
    from apps.reservas.asignacion import EN_EJECUCION
    from apps.reservas.models import EstadoViaje, MetodoPago, Viaje

    return (
        Turno.objects.filter(
            conductor__usuario__empresa_id=empresa_id, hora_termino__isnull=False, cierre_caja__isnull=True
        )
        .select_related("conductor__usuario", "vehiculo")
        .annotate(
            efectivo=Sum(
                "viajes__pago__monto",
                filter=Q(viajes__estado=EstadoViaje.FINALIZADO, viajes__pago__metodo=MetodoPago.EFECTIVO),
                default=0,
            ),
            viajes_finalizados=Count(
                "viajes", filter=Q(viajes__estado=EstadoViaje.FINALIZADO, viajes__pago__isnull=False)
            ),
            con_viaje_en_ejecucion=Exists(
                Viaje.objects.filter(turno=OuterRef("pk"), estado__in=EN_EJECUCION)
            ),
        )
        .order_by("hora_termino", "id")
    )


def cerrar_caja(
    turno_id: int, *, empresa_id: int, monto_rendido: int, observacion: str | None, usuario
) -> CierreCaja:
    """CP-36: fija el efectivo registrado del turno, calcula la diferencia y lo deja en auditoría.

    Solo turnos terminados, sin viajes en ejecución y sin cierre previo (409). La observación es obligatoria
    si
    hay diferencia. El bloqueo de la fila del turno pone en serie dos cierres simultáneos del mismo turno.
    """
    from apps.reservas.asignacion import EN_EJECUCION
    from apps.reservas.models import Viaje

    observacion = (observacion or "").strip() or None
    with transaction.atomic():
        turno = (
            Turno.objects.select_for_update(of=("self",))
            .select_related("conductor__usuario", "vehiculo")
            .filter(pk=turno_id, conductor__usuario__empresa_id=empresa_id)
            .first()
        )
        if turno is None:
            from django.http import Http404

            raise Http404
        if turno.abierto:
            raise ConflictoTurno(
                "El turno sigue abierto: el conductor debe terminarlo primero.", code="turno_abierto"
            )
        if CierreCaja.objects.filter(turno=turno).exists():
            raise ConflictoTurno("Este turno ya tiene su cierre de caja.", code="cierre_repetido")
        if Viaje.objects.filter(turno=turno, estado__in=EN_EJECUCION).exists():
            raise ConflictoTurno(
                "El turno tiene un viaje en ejecución: ciérralo antes de cuadrar la caja.",
                code="viaje_en_ejecucion",
            )
        registrado = efectivo_registrado(turno.pk)
        diferencia = monto_rendido - registrado
        if diferencia != 0 and not observacion:
            raise ValidationError(
                {"observacion": ["Explica la diferencia entre lo rendido y lo registrado."]}
            )
        cierre = CierreCaja.objects.create(
            turno=turno,
            monto_registrado=registrado,
            monto_rendido=monto_rendido,
            diferencia=diferencia,
            observacion=observacion,
            responsable=usuario,
        )
        auditoria.registrar(
            usuario=usuario,
            entidad=Entidad.TURNO,
            entidad_id=turno.pk,
            accion="CIERRE_CAJA",
            motivo=observacion,
            datos_previos={
                "cierre_caja_id": cierre.pk,
                "conductor_id": turno.conductor_id,
                "monto_registrado": registrado,
                "monto_rendido": monto_rendido,
                "diferencia": diferencia,
            },
        )
    cierre.refresh_from_db()
    return cierre
