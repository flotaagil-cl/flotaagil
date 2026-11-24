"""HU-34: lo que hace la cuenta de la empresa cliente (rol CONVENIO).

- EN_REVISION y RECHAZADO entran y ven su estado, pero no reservan.
- INACTIVO no entra: al desactivar se deshabilita la cuenta (RN-08).
- APROBADO reserva a nombre del pasajero sin verificación por WhatsApp (RN-07), declarando que el pasajero
  autorizó los avisos; la declaración queda ligada al usuario que reserva (DC-35). Ve las reservas de su
  convenio.
"""

import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.reservas import avisos
from apps.reservas import servicios as reservas
from apps.reservas.models import Actor, Canal, EstadoViaje, Pasajero, Viaje
from apps.reservas.tipos_aviso import AVISO_CONFIRMACION

from .models import Convenio, EstadoConvenio


class ConvenioNoAprobado(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "convenio_no_aprobado"
    default_detail = "Tu convenio aún no está aprobado: no puedes pedir viajes."


def del_usuario(usuario) -> Convenio:
    return Convenio.objects.select_related("empresa__configuracion").get(usuario=usuario)


def crear_solicitud(convenio: Convenio, datos: dict, *, usuario) -> tuple[list[Viaje], dict]:
    """RN-07: los viajes quedan SOLICITADO, con el convenio y sin enlace de confirmación.

    CC-25 (HU-47), con las reglas de CC-23 (DC-76): quien pide queda en `solicitante_*`; viaja él o la otra
    persona, con acompañantes en el mismo vehículo o un viaje por persona con el mismo `grupo`. Todo o nada.
    La declaración por los terceros queda ligada al usuario que reserva (DC-35, DC-81).
    """
    from apps.portal.publico import _acompanante, _personas, _validar_personas
    from apps.portal.servicios import validar_capacidad, vuelo_y_recogida

    if convenio.estado != EstadoConvenio.APROBADO:
        raise ConvenioNoAprobado()
    empresa = convenio.empresa
    personas = _personas(datos)
    _validar_personas(empresa, datos, personas)
    separados = datos["vehiculos"] == "SEPARADOS" and len(personas) > 1
    viajantes = personas if separados else personas[:1]
    validar_capacidad(empresa, 1 if separados else len(personas))  # DC-43
    vuelo, recogida = vuelo_y_recogida(empresa, datos)
    grupo = uuid.uuid4() if separados else None
    terceros = len(personas) > 1 or datos["para"] == "OTRO"
    ahora = timezone.now()
    viajes = []
    with transaction.atomic():
        for indice, persona in enumerate(viajantes):
            viaje = reservas.crear_viaje(
                empresa=empresa,
                datos={
                    "pasajero": {"nombre": persona["nombre"], "telefono": persona["telefono"]},
                    "sentido": datos["sentido"],
                    "origen_dir": datos["origen_dir"],
                    "destino_dir": datos["destino_dir"],
                    "origen_coordenadas": datos.get("origen_coordenadas"),  # HU-71
                    "destino_coordenadas": datos.get("destino_coordenadas"),
                    "recogida_en": recogida,
                    "vuelo": vuelo,
                    # HU-39 (DC-42): las maletas van en el primer viaje.
                    "pasajeros": 1 if separados else len(personas),
                    "maletas": datos.get("maletas", 0) if indice == 0 else 0,
                    "vuelo_salida": datos.get("vuelo_salida"),
                    "convenio": convenio,
                },
                canal=Canal.CONVENIO,
                estado_inicial=EstadoViaje.SOLICITADO,
                actor=Actor.PASAJERO,
                usuario=usuario,
            )
            viaje.solicitante_nombre = datos["nombre"]
            viaje.solicitante_telefono = datos["telefono"]
            viaje.pasajero_cargo = persona.get("cargo") or None
            viaje.pasajero_correo = persona.get("correo") or None
            viaje.acompanantes = [] if separados else [_acompanante(a) for a in personas[1:]]
            viaje.grupo = grupo
            viaje.terceros_informados_en = ahora if terceros else None
            viaje.autorizacion_avisos_en, viaje.autorizacion_avisos_por = ahora, usuario
            viaje.save()
            Pasajero.objects.filter(pk=viaje.pasajero_id).update(opt_in_en=ahora)
            viajes.append(viaje)
        if datos["para"] == "MI":
            # Ley 21.719: quien pide para sí acepta el aviso; por los demás solo declara que les informó.
            Pasajero.objects.filter(pk=viajes[0].pasajero_id).update(privacidad_aceptada_en=ahora)
        for viaje in viajes:
            avisos.programar(viaje.pk, AVISO_CONFIRMACION)  # HU-21
    numeros = ", ".join(f"N.º {v.pk}" for v in viajes)
    return viajes, {
        "estado": viajes[0].estado,
        "recogida_en": viajes[0].recogida_en,
        "expira_en": None,
        "viajes": len(viajes),
        "mensaje": (
            f"Recibimos la solicitud ({numeros}) a nombre de {convenio.cliente_nombre}: la central "
            "asignará " + ("un conductor a cada viaje." if separados else "un conductor.")
        ),
    }
