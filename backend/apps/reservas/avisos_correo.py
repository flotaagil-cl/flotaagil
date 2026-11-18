"""HU-56 (CC-22, DC-55): avisos por correo para las empresas sin el módulo de cuentas.

Para ellas no sale ningún WhatsApp. Al correo de contacto del viaje (`VIAJE.contacto_correo`) llegan:
reserva confirmada, conductor asignado (nombre, patente, modelo y color), cancelación y la encuesta al
finalizar, con un enlace que registra la misma CALIFICACION de HU-24. «En camino» y «en zona» no se envían.
La solicitud recibida (con el enlace para confirmar) sale al crear la reserva pública (HU-51).
"""

from django.conf import settings
from django.core import signing
from django.utils import timezone

from apps.cuentas.tareas import enviar_correo

from .tipos_aviso import AVISO_CANCELACION, AVISO_CONDUCTOR, AVISO_CONFIRMACION, AVISO_ENCUESTA

SAL_ENCUESTA = "reserva-publica-encuesta"
VIGENCIA_ENCUESTA_S = 7 * 24 * 3600  # DC-56: la encuesta por correo vale 7 días


def token_encuesta(viaje) -> str:
    return signing.TimestampSigner(salt=SAL_ENCUESTA).sign(str(viaje.pk))


def viaje_de_encuesta(token: str) -> int:
    """Id del viaje del enlace de la encuesta. `signing.BadSignature` si no es válido o venció."""
    return int(signing.TimestampSigner(salt=SAL_ENCUESTA).unsign(token, max_age=VIGENCIA_ENCUESTA_S))


def _cuando(viaje) -> str:
    return f"{timezone.localtime(viaje.recogida_en):%d-%m-%Y %H:%M}"


def mensaje(viaje, tipo: str) -> tuple[str, str] | None:
    """(asunto, texto) del aviso, o None si ese aviso no va por correo."""
    nombre = viaje.pasajero.nombre
    empresa = viaje.empresa.razon_social
    tramo = f"{viaje.origen_dir} → {viaje.destino_dir}, {_cuando(viaje)}"
    if tipo == AVISO_CONFIRMACION:
        return (
            f"Reserva N.º {viaje.pk} confirmada · {empresa}",
            f"Hola {nombre}:\n\nTu reserva N.º {viaje.pk} quedó confirmada: {tramo}.\n"
            "Te avisaremos por correo cuando tengas conductor.",
        )
    if tipo == AVISO_CONDUCTOR:
        vehiculo = viaje.vehiculo
        color = f", color {vehiculo.color}" if vehiculo.color else ""
        return (
            f"Tu conductor para la reserva N.º {viaje.pk}",
            f"Hola {nombre}:\n\nTu conductor es {viaje.conductor.usuario.nombre}, en {vehiculo.marca_modelo}"
            f"{color}, patente {vehiculo.patente}.\nViaje: {tramo}.",
        )
    if tipo == AVISO_CANCELACION:
        motivo = f"\nMotivo: {viaje.motivo_cancelacion}" if viaje.motivo_cancelacion else ""
        return (
            f"Reserva N.º {viaje.pk} cancelada · {empresa}",
            f"Hola {nombre}:\n\nTu reserva N.º {viaje.pk} ({tramo}) quedó cancelada.{motivo}",
        )
    if tipo == AVISO_ENCUESTA:
        url = f"{settings.WEB_URL_BASE}/solicitar/{viaje.empresa.slug}/encuesta/{token_encuesta(viaje)}"
        return (
            f"¿Cómo fue tu viaje con {empresa}?",
            f"Gracias por viajar con nosotros, {nombre}.\n\n¿Cómo fue tu viaje con "
            f"{viaje.conductor.usuario.nombre}? Califícalo del 1 al 5 (es opcional):\n{url}\n",
        )
    return None  # «en camino» y «en zona» no se envían por correo


def enviar(viaje, tipo: str) -> None:
    """Desde la tarea `enviar_aviso`, ya en el worker: el correo se encola con su propio reintento."""
    contenido = mensaje(viaje, tipo)
    if viaje.contacto_correo and contenido:
        enviar_correo.delay(viaje.contacto_correo, *contenido)
