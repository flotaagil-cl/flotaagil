"""HU-25: acceso del supervisor al link del convenio (RN-07, RN-08).

Bloqueo: tras CONVENIO_MAX_INTENTOS fallos, el convenio no admite contraseña durante CONVENIO_BLOQUEO (DC-27).
Sesión: valor firmado en una cookie httpOnly, que se renueva en cada uso y vence tras CONVENIO_SESION sin
usarla. No guarda nada en el servidor: lleva el convenio y una huella de su contraseña, así que rotarla la
invalida. Cada petición lee el convenio de la base: desactivarlo corta el acceso al instante.
"""

import hashlib

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad
from apps.convenios.models import Convenio
from apps.integraciones.notificaciones import AVISO_CONFIRMACION
from apps.reservas import avisos
from apps.reservas import servicios as reservas
from apps.reservas.models import Actor, Canal, EstadoViaje, Pasajero, Viaje

SAL_SESION = "flotaagil.convenio.sesion"


class PasswordIncorrecta(APIException):
    # Las vistas públicas no tienen autenticadores: AuthenticationFailed saldría como 403.
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "credenciales_invalidas"
    default_detail = "La contraseña no es correcta."


class ConvenioBloqueado(APIException):
    status_code = status.HTTP_423_LOCKED
    default_code = "convenio_bloqueado"
    default_detail = "El acceso está bloqueado por intentos fallidos. Intenta de nuevo más tarde."


class SesionVencida(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "sesion_convenio_vencida"
    default_detail = "Tu sesión venció. Ingresa de nuevo la contraseña."


def convenio_del_link(token: str) -> Convenio:
    """RN-08: un link desconocido, de un convenio inactivo o de una empresa inactiva responden igual: 404."""
    return get_object_or_404(
        Convenio.objects.select_related("empresa__configuracion"),
        token_link=token,
        activo=True,
        empresa__activa=True,
    )


def _huella(convenio: Convenio) -> str:
    return hashlib.sha256(convenio.password_hash.encode()).hexdigest()[:16]


def emitir_sesion(convenio: Convenio) -> str:
    return signing.dumps({"c": convenio.pk, "h": _huella(convenio)}, salt=SAL_SESION)


def sesion_valida(valor: str | None, convenio: Convenio) -> bool:
    if not valor:
        return False
    try:
        datos = signing.loads(valor, salt=SAL_SESION, max_age=settings.CONVENIO_SESION)
    except signing.BadSignature:  # También cubre la firma vencida.
        return False
    return datos == {"c": convenio.pk, "h": _huella(convenio)}


def intentar_acceso(convenio: Convenio, password: str) -> None:
    """Valida la contraseña bajo el bloqueo de la fila, para que intentos simultáneos no escapen del conteo.

    El error se lanza fuera de la transacción: si no, se desharían el conteo y la auditoría.
    """
    error = None
    with transaction.atomic():
        convenio = Convenio.objects.select_for_update().get(pk=convenio.pk)
        ahora = timezone.now()
        if convenio.bloqueado_hasta is not None and convenio.bloqueado_hasta > ahora:
            error = ConvenioBloqueado()
        else:
            if convenio.bloqueado_hasta is not None:  # El bloqueo venció: se parte de cero.
                convenio.intentos_fallidos, convenio.bloqueado_hasta = 0, None
            if convenio.check_password(password):
                convenio.intentos_fallidos = 0
            else:
                convenio.intentos_fallidos += 1
                error = PasswordIncorrecta()
                if convenio.intentos_fallidos >= settings.CONVENIO_MAX_INTENTOS:
                    convenio.bloqueado_hasta = ahora + settings.CONVENIO_BLOQUEO
                    error = ConvenioBloqueado()
                    # Nadie inició sesión: el evento no tiene usuario (DC-27).
                    auditoria.registrar(
                        usuario=None,
                        empresa_id=convenio.empresa_id,
                        entidad=Entidad.CONVENIO,
                        entidad_id=convenio.pk,
                        accion="BLOQUEO_LINK",
                        datos_previos={"intentos": convenio.intentos_fallidos},
                    )
            convenio.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
    if error is not None:
        raise error


def crear_solicitud(convenio: Convenio, datos: dict) -> tuple[Viaje, dict]:
    """RN-07: la reserva queda SOLICITADO, con el convenio y sin verificación por WhatsApp."""
    from apps.portal.servicios import vuelo_y_recogida

    empresa = convenio.empresa
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
                "convenio": convenio,
            },
            canal=Canal.CONVENIO,
            estado_inicial=EstadoViaje.SOLICITADO,
            actor=Actor.PASAJERO,  # DC-27: el supervisor no tiene cuenta.
        )
        ahora = timezone.now()
        Pasajero.objects.filter(pk=viaje.pasajero_id).update(opt_in_en=ahora, privacidad_aceptada_en=ahora)
        avisos.programar(viaje.pk, AVISO_CONFIRMACION)  # HU-21
    return viaje, {
        "estado": viaje.estado,
        "recogida_en": viaje.recogida_en,
        "mensaje": (
            f"Recibimos la solicitud a nombre de {convenio.cliente_nombre}. La central asignará un conductor."
        ),
    }
