"""HU-51 (CC-22): reserva pública sin cuenta, para las empresas sin el módulo de cuentas (DC-51).

El viaje nace en PENDIENTE_CONFIRMACION y se envía por correo un enlace firmado (`TimestampSigner`).
Vale hasta `confirmar_hasta` (DC-53) y una sola vez: solo confirma mientras el viaje sigue pendiente (DC-56).
"""

from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, Throttled

from apps.cuentas.tareas import al_confirmar_correo
from apps.reservas import estados
from apps.reservas import servicios as reservas
from apps.reservas.models import Actor, Canal, EstadoViaje, Pasajero, Viaje

from .servicios import validar_capacidad, vuelo_y_recogida

SAL_CONFIRMAR = "reserva-publica-confirmar"


class LimiteCorreo(Throttled):
    default_code = "limite_correo"
    default_detail = "Ya enviaste varias solicitudes con este correo. Espera un rato e intenta de nuevo."


class EnlaceInvalido(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "enlace_invalido"
    default_detail = "El enlace no es válido. Revisa que lo copiaste completo."


class EnlaceUsado(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "enlace_usado"
    default_detail = "Esta reserva ya no está pendiente: el enlace ya se usó o la reserva cambió."


class EnlaceVencido(APIException):
    status_code = status.HTTP_410_GONE
    default_code = "enlace_vencido"
    default_detail = "El plazo para confirmar por correo venció. La central te contactará para confirmarla."


def plazo_confirmacion(config, recogida, ahora=None):
    """DC-53: hasta `confirmacion_antes_horas` antes de la recogida; si ya falta menos, el plazo corto."""
    ahora = ahora or timezone.now()
    limite = recogida - timedelta(hours=config.confirmacion_antes_horas)
    return limite if limite > ahora else ahora + timedelta(minutes=config.confirmacion_plazo_corto_min)


def token_de(viaje: Viaje, sal: str = SAL_CONFIRMAR) -> str:
    return signing.TimestampSigner(salt=sal).sign(str(viaje.pk))


def viaje_del_token(empresa, token: str, sal: str = SAL_CONFIRMAR) -> Viaje:
    try:
        pk = int(signing.TimestampSigner(salt=sal).unsign(token))
    except (signing.BadSignature, ValueError) as error:
        raise EnlaceInvalido() from error
    viaje = Viaje.objects.select_related("empresa", "pasajero").filter(pk=pk, empresa=empresa).first()
    if viaje is None:
        raise EnlaceInvalido()
    return viaje


def enlace(empresa, ruta: str, token: str) -> str:
    return f"{settings.WEB_URL_BASE}/solicitar/{empresa.slug}/{ruta}/{token}"


def _verificar_limite_correo(empresa, correo: str) -> None:
    desde = timezone.now() - timedelta(hours=1)
    recientes = Viaje.objects.filter(
        empresa=empresa, contacto_correo__iexact=correo, creado_en__gte=desde
    ).count()
    if recientes >= settings.RESERVA_PUBLICA_MAX_POR_CORREO:
        raise LimiteCorreo(wait=3600)


def texto_solicitud(viaje: Viaje, url: str) -> str:
    texto = (
        f"Hola {viaje.pasajero.nombre}:\n\nRecibimos tu solicitud de traslado N.º {viaje.pk} con "
        f"{viaje.empresa.razon_social}: {viaje.origen_dir} → {viaje.destino_dir}, "
        f"{timezone.localtime(viaje.recogida_en):%d-%m-%Y %H:%M}.\n\n"
        f"Para confirmarla, abre este enlace antes del "
        f"{timezone.localtime(viaje.confirmar_hasta):%d-%m-%Y %H:%M}:\n{url}\n\n"
        "Si no fuiste tú, ignora este correo."
    )
    if viaje.empresa_cliente_rut and viaje.convenio_id is None:
        # HU-51 (punto 4 de CC-22): la empresa sin convenio se cobra como particular.
        texto += (
            "\n\n¿Tu empresa viaja seguido? Solicita un convenio y obtén beneficios:\n"
            f"{settings.WEB_URL_BASE}/solicitar/{viaje.empresa.slug}/convenio"
        )
    return texto


def crear(empresa, datos: dict) -> Viaje:
    """Crea la reserva pendiente y envía el correo con el enlace de confirmación."""
    correo = datos["correo"].strip().lower()
    validar_capacidad(empresa, datos.get("pasajeros", 1))  # DC-43
    _verificar_limite_correo(empresa, correo)
    vuelo, recogida = vuelo_y_recogida(empresa, datos)
    ahora = timezone.now()
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
                "pasajeros": datos.get("pasajeros", 1),
                "maletas": datos.get("maletas", 0),
                "vuelo_salida": datos.get("vuelo_salida"),
            },
            canal=Canal.WEB,
            estado_inicial=EstadoViaje.PENDIENTE_CONFIRMACION,
            actor=Actor.PASAJERO,
        )
        viaje.contacto_correo = correo
        viaje.privacidad_version = settings.AVISO_PRIVACIDAD_VERSION
        viaje.confirmar_hasta = plazo_confirmacion(empresa.configuracion, viaje.recogida_en, ahora)
        campos = ["contacto_correo", "privacidad_version", "confirmar_hasta"]
        if datos.get("es_empresa"):
            viaje.empresa_cliente_razon_social = datos["empresa_razon_social"]
            viaje.empresa_cliente_rut = datos["empresa_rut"]
            viaje.empresa_cliente_contacto = datos["empresa_contacto"]
            campos += ["empresa_cliente_razon_social", "empresa_cliente_rut", "empresa_cliente_contacto"]
        viaje.save(update_fields=campos)
        # Ley 21.719: evidencia de la aceptación del aviso de privacidad (la versión queda en el viaje).
        Pasajero.objects.filter(pk=viaje.pasajero_id).update(privacidad_aceptada_en=ahora)
        avisar_solicitud(viaje)
    return viaje


def avisar_solicitud(viaje: Viaje) -> None:
    url = enlace(viaje.empresa, "confirmar", token_de(viaje))
    al_confirmar_correo(
        viaje.contacto_correo,
        f"Confirma tu reserva N.º {viaje.pk} · {viaje.empresa.razon_social}",
        texto_solicitud(viaje, url),
    )


def confirmar(empresa, token: str) -> Viaje:
    """El pasajero abre el enlace: la reserva pasa a SOLICITADO, una sola vez y dentro del plazo."""
    viaje = viaje_del_token(empresa, token)
    if viaje.estado != EstadoViaje.PENDIENTE_CONFIRMACION or viaje.confirma_convenio:
        raise EnlaceUsado()
    if viaje.confirmar_hasta and viaje.confirmar_hasta < timezone.now():
        raise EnlaceVencido()
    try:
        return estados.transicionar(
            viaje, EstadoViaje.SOLICITADO, desde=EstadoViaje.PENDIENTE_CONFIRMACION, actor=Actor.PASAJERO
        )
    except estados.TransicionInvalida as error:  # otro clic simultáneo ya la confirmó
        raise EnlaceUsado() from error
