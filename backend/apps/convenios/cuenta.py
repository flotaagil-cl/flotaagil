"""HU-34: lo que hace la cuenta de la empresa cliente (rol CONVENIO).

- EN_REVISION y RECHAZADO entran y ven su estado, pero no reservan.
- INACTIVO no entra: al desactivar se deshabilita la cuenta (RN-08).
- APROBADO reserva a nombre del pasajero sin verificación por WhatsApp (RN-07), declarando que el pasajero
  autorizó los avisos; la declaración queda ligada al usuario que reserva (DC-35). Ve las reservas de su
  convenio.
"""

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.integraciones.notificaciones import AVISO_CONFIRMACION
from apps.reservas import avisos
from apps.reservas import servicios as reservas
from apps.reservas.models import Actor, Canal, EstadoViaje, Pasajero, Viaje

from .models import Convenio, EstadoConvenio


class ConvenioNoAprobado(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "convenio_no_aprobado"
    default_detail = "Tu convenio aún no está aprobado: no puedes pedir viajes."


def del_usuario(usuario) -> Convenio:
    return Convenio.objects.select_related("empresa__configuracion").get(usuario=usuario)


def crear_solicitud(convenio: Convenio, datos: dict, *, usuario) -> tuple[Viaje, dict]:
    """RN-07: la reserva queda SOLICITADO, con el convenio y sin verificación por WhatsApp."""
    from apps.portal.servicios import validar_capacidad, vuelo_y_recogida

    if convenio.estado != EstadoConvenio.APROBADO:
        raise ConvenioNoAprobado()
    empresa = convenio.empresa
    validar_capacidad(empresa, datos.get("pasajeros", 1))  # DC-43
    vuelo, recogida = vuelo_y_recogida(empresa, datos)
    with transaction.atomic():
        viaje = reservas.crear_viaje(
            empresa=empresa,
            datos={
                "pasajero": {"nombre": datos["nombre"], "telefono": datos["telefono"]},
                "sentido": datos["sentido"],
                "origen_dir": datos["origen_dir"],
                "destino_dir": datos["destino_dir"],
                "recogida_en": recogida,
                "vuelo": vuelo,
                # HU-39 (DC-42).
                "pasajeros": datos.get("pasajeros", 1),
                "maletas": datos.get("maletas", 0),
                "vuelo_salida": datos.get("vuelo_salida"),
                "convenio": convenio,
            },
            canal=Canal.CONVENIO,
            estado_inicial=EstadoViaje.SOLICITADO,
            actor=Actor.PASAJERO,
            usuario=usuario,
        )
        ahora = timezone.now()
        Pasajero.objects.filter(pk=viaje.pasajero_id).update(opt_in_en=ahora, privacidad_aceptada_en=ahora)
        viaje.autorizacion_avisos_en, viaje.autorizacion_avisos_por = ahora, usuario
        viaje.save(update_fields=["autorizacion_avisos_en", "autorizacion_avisos_por"])
        avisos.programar(viaje.pk, AVISO_CONFIRMACION)  # HU-21
    return viaje, {
        "estado": viaje.estado,
        "recogida_en": viaje.recogida_en,
        "expira_en": None,
        "mensaje": (
            f"Recibimos la solicitud a nombre de {convenio.cliente_nombre}. La central asignará un conductor."
        ),
    }
