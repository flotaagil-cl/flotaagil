"""HU-32 (CC-15, DC-33): reservas anotadas durante una caída del sistema e ingresadas después.

El viaje se crea directamente en su estado final, sin pasar por la máquina de estados ni por la asignación:
- FINALIZADO: con conductor, método y monto (RN-10). Historial: PASAJERO_A_BORDO a la hora real de recogida y
  FINALIZADO a la hora real de término. PAGO_VIAJE.registrado_en es la hora real de término.
- CANCELADO: con motivo. Historial: CANCELADO a la hora real de cancelación.
Todas las transiciones van marcadas `contingencia`. No se envían avisos de WhatsApp ni encuesta.

Las horas son pasadas y como máximo `contingencia_max_dias` atrás. El turno es el del conductor que
contiene la
hora real de recogida; si no hay, queda sin turno y el reporte de conciliación lo marca.
"""

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad
from apps.flota.models import Conductor, Turno
from apps.integraciones.geocodificador import Zona, obtener_geocodificador

from . import estados
from .models import (
    Canal,
    EstadoViaje,
    HistorialEstado,
    MetodoPago,
    OrigenCancelacion,
    PagoViaje,
    Viaje,
)
from .servicios import _punto, _validar_origen_en_zona, obtener_pasajero

RESULTADOS = (EstadoViaje.FINALIZADO, EstadoViaje.CANCELADO)


def turno_que_contiene(conductor_id: int, momento) -> Turno | None:
    return (
        Turno.objects.filter(conductor_id=conductor_id, hora_inicio__lte=momento)
        .exclude(hora_termino__lt=momento)
        .order_by("-hora_inicio")
        .first()
    )


def _validar_horas(datos: dict, config) -> None:
    ahora = timezone.now()
    limite = ahora - timedelta(days=config.contingencia_max_dias)
    errores = {}
    for campo in ("recogida_en", "termino_en"):
        valor = datos.get(campo)
        if valor is None:
            continue
        if valor >= ahora:
            errores[campo] = ["La hora real debe estar en el pasado."]
        elif valor < limite:
            errores[campo] = [f"Solo se ingresan viajes de los últimos {config.contingencia_max_dias} días."]
    finalizado = datos["resultado"] == EstadoViaje.FINALIZADO
    if not errores and finalizado and datos["termino_en"] < datos["recogida_en"]:
        errores["termino_en"] = ["El término no puede ser anterior a la recogida."]
    if errores:
        raise ValidationError(errores)


def crear(empresa, datos: dict, *, usuario, geocodificador=None) -> Viaje:
    """`datos` ya validado por ReservaContingenciaSerializer. Devuelve el viaje con su pago si lo tiene."""
    config = empresa.configuracion
    _validar_horas(datos, config)
    resultado = datos["resultado"]
    conductor = None
    if datos.get("conductor") is not None:
        conductor = (
            Conductor.objects.select_related("usuario")
            .filter(pk=datos["conductor"], usuario__empresa=empresa)
            .first()
        )
        if conductor is None:
            raise ValidationError({"conductor": ["El conductor no existe en tu empresa."]})
    if resultado == EstadoViaje.FINALIZADO:
        faltan = {
            c: ["Obligatorio para un viaje finalizado."]
            for c in ("conductor", "metodo", "monto")
            if datos.get(c) is None
        }
        if faltan:
            raise ValidationError(faltan)
        if datos["metodo"] == MetodoPago.CONVENIO:
            raise ValidationError(
                {"metodo": ["Un viaje de contingencia no se cobra al convenio: usa otro método."]}
            )
    elif not (datos.get("motivo") or "").strip():
        raise ValidationError({"motivo": ["Indica el motivo de la cancelación."]})

    geocodificador = geocodificador or obtener_geocodificador()
    zona = Zona.de_configuracion(config)
    origen = _punto(datos["origen_dir"], zona, geocodificador, "origen_dir")
    _validar_origen_en_zona(origen, zona)
    destino = _punto(datos["destino_dir"], zona, geocodificador, "destino_dir")
    actor = estados.actor_de(usuario)
    turno = turno_que_contiene(conductor.pk, datos["recogida_en"]) if conductor else None

    try:
        with transaction.atomic():
            viaje = Viaje.objects.create(
                empresa=empresa,
                pasajero=obtener_pasajero(empresa, **datos["pasajero"]),
                canal=Canal.CONTINGENCIA,
                folio_contingencia=datos["folio"],
                sentido=datos["sentido"],
                origen_dir=datos["origen_dir"],
                origen_geo=origen,
                destino_dir=datos["destino_dir"],
                destino_geo=destino,
                recogida_en=datos["recogida_en"],
                tarifa=datos.get("tarifa"),
                estado=resultado,
                conductor=conductor,
                vehiculo=turno.vehiculo if turno else None,
                turno=turno,
                **(
                    {
                        "motivo_cancelacion": datos["motivo"].strip()[:200],
                        "origen_cancelacion": OrigenCancelacion(actor),
                    }
                    if resultado == EstadoViaje.CANCELADO
                    else {}
                ),
            )
    except IntegrityError as error:
        if "viaje_folio_unico_por_empresa" in str(error):
            raise ValidationError({"folio": ["Ese folio ya fue ingresado en tu empresa."]}) from error
        raise

    with transaction.atomic():
        comunes = {"viaje": viaje, "actor": actor, "usuario": usuario, "contingencia": True}
        if resultado == EstadoViaje.FINALIZADO:
            HistorialEstado.objects.create(
                estado_anterior=None,
                estado_nuevo=EstadoViaje.PASAJERO_A_BORDO,
                creado_en=datos["recogida_en"],
                **comunes,
            )
            HistorialEstado.objects.create(
                estado_anterior=EstadoViaje.PASAJERO_A_BORDO,
                estado_nuevo=EstadoViaje.FINALIZADO,
                creado_en=datos["termino_en"],
                **comunes,
            )
            PagoViaje.objects.create(
                viaje=viaje, metodo=datos["metodo"], monto=datos["monto"], registrado_en=datos["termino_en"]
            )
        else:
            HistorialEstado.objects.create(
                estado_anterior=None,
                estado_nuevo=EstadoViaje.CANCELADO,
                creado_en=datos["termino_en"],
                **comunes,
            )
        auditoria.registrar(
            usuario=usuario,
            entidad=Entidad.VIAJE,
            entidad_id=viaje.pk,
            accion="RESERVA_CONTINGENCIA",
            motivo=datos.get("motivo") or None,
            datos_previos={
                "folio": viaje.folio_contingencia,
                "resultado": resultado,
                "turno_id": turno.pk if turno else None,
            },
        )
    return viaje
