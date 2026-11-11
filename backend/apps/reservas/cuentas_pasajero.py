"""HU-35 (CC-16, DC-36): cuenta web opcional del pasajero. El invitado sigue igual.

- Registro por empresa: nombre, teléfono, correo y contraseña. El usuario (rol PASAJERO) queda inactivo y se
  le pide por WhatsApp responder «CONFIRMAR CUENTA» (mismo canal que HU-20). Al confirmar se activa y se liga
  al PASAJERO de ese teléfono en la empresa: recién ahí ve sus reservas, también las de invitado.
- Con la cuenta activa, sus reservas no se verifican otra vez; se mantiene el límite por teléfono del portal.
- Cancela solo sin conductor asignado (RN-09).
- Eliminar la cuenta borra la credencial y el correo; el pasajero y sus reservas quedan como de invitado.
"""

from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as ErrorDeDjango
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad
from apps.cuentas import credenciales
from apps.cuentas.models import Rol, Usuario
from apps.integraciones.notificaciones import AVISO_CONFIRMACION

from . import avisos, estados, tareas
from . import servicios as reservas
from .models import (
    Actor,
    Canal,
    CuentaPasajero,
    EstadoViaje,
    OrigenCancelacion,
    Pasajero,
    Viaje,
)

PALABRA_CONFIRMAR = "confirmar cuenta"
CANCELABLES = (EstadoViaje.PENDIENTE_CONFIRMACION, EstadoViaje.SOLICITADO)  # RN-09: sin conductor asignado


class SinCuentaActiva(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "cuenta_sin_confirmar"
    default_detail = "Confirma tu cuenta respondiendo el WhatsApp que te enviamos."


class NoCancelable(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "con_conductor"
    default_detail = (
        "Tu viaje ya tiene conductor asignado: no se puede cancelar aquí. Comunícate con la central."
    )


def texto_confirmacion(cuenta: CuentaPasajero) -> str:
    return (
        f"Hola {cuenta.nombre}, creaste una cuenta en {cuenta.empresa.razon_social}. Para activarla responde "
        f"CONFIRMAR CUENTA. Si no fuiste tú, ignora este mensaje."
    )


def vence_en(cuenta: CuentaPasajero):
    return cuenta.creada_en + timedelta(minutes=cuenta.empresa.configuracion.expiracion_verificacion_min)


@transaction.atomic
def registrar(empresa, datos: dict) -> CuentaPasajero:
    """Crea la cuenta pendiente y envía el WhatsApp. Si el correo ya tiene una cuenta pendiente de esta
    empresa, la reemplaza (otro teléfono o un mensaje vencido); cualquier otro uso del correo responde
    400."""
    email = datos["email"].strip().lower()
    existente = Usuario.objects.filter(email__iexact=email).select_related("cuenta_pasajero").first()
    if existente is not None:
        cuenta = getattr(existente, "cuenta_pasajero", None)
        if (
            existente.rol != Rol.PASAJERO
            or cuenta is None
            or cuenta.confirmada_en
            or cuenta.empresa_id != empresa.pk
        ):
            raise ValidationError(
                {"email": ["No se pudo crear la cuenta con ese correo. Si ya tienes una, inicia sesión."]}
            )
        usuario = existente
    else:
        usuario = Usuario(empresa=empresa, email=email, rol=Rol.PASAJERO, activo=False)
    usuario.nombre = datos["nombre"]
    try:
        validate_password(datos["password"], usuario)
    except ErrorDeDjango as error:
        raise ValidationError({"password": list(error.messages)}) from error
    usuario.set_password(datos["password"])
    try:
        with transaction.atomic():
            usuario.save()
    except IntegrityError as error:
        raise ValidationError({"email": ["No se pudo crear la cuenta con ese correo."]}) from error
    CuentaPasajero.objects.filter(usuario=usuario).delete()
    cuenta = CuentaPasajero.objects.create(
        usuario=usuario, empresa=empresa, nombre=datos["nombre"], telefono=datos["telefono"]
    )
    # El mensaje necesita un PASAJERO (MENSAJE_WHATSAPP.pasajero_id). Se crea como invitado si no existía; la
    # cuenta no lo ve hasta confirmar.
    pasajero = reservas.obtener_pasajero(empresa, nombre=datos["nombre"], telefono=datos["telefono"])
    tareas.al_confirmar(tareas.enviar_respuesta, pasajero.pk, None, texto_confirmacion(cuenta))
    return cuenta


def confirmar_por_whatsapp(telefono: str, texto: str) -> str | None:
    """Desde el webhook (HU-20). Devuelve el resultado si el mensaje era «CONFIRMAR CUENTA», o None."""
    if (texto or "").strip().lower() != PALABRA_CONFIRMAR:
        return None
    ahora = timezone.now()
    with transaction.atomic():
        cuentas = list(
            CuentaPasajero.objects.select_for_update(of=("self",))
            .select_related("empresa__configuracion", "usuario")
            .filter(telefono=telefono, confirmada_en__isnull=True)
        )
        vigentes = [c for c in cuentas if vence_en(c) > ahora]
        if not vigentes:
            return "cuenta_no_vigente"
        for cuenta in vigentes:
            if CuentaPasajero.objects.filter(
                empresa=cuenta.empresa, telefono=telefono, confirmada_en__isnull=False
            ).exists():
                continue  # ese teléfono ya tiene cuenta en la empresa
            pasajero, _ = Pasajero.objects.get_or_create(
                empresa=cuenta.empresa, telefono=telefono, defaults={"nombre": cuenta.nombre}
            )
            Pasajero.objects.filter(pk=pasajero.pk).update(verificado_en=ahora)
            cuenta.pasajero, cuenta.confirmada_en = pasajero, ahora
            cuenta.save(update_fields=["pasajero", "confirmada_en"])
            Usuario.objects.filter(pk=cuenta.usuario_id).update(activo=True)
            auditoria.registrar(
                usuario=cuenta.usuario,
                entidad=Entidad.USUARIO,
                entidad_id=cuenta.usuario_id,
                accion="CONFIRMAR_CUENTA",
            )
    return "cuenta_confirmada"


def cuenta_activa(usuario) -> CuentaPasajero:
    cuenta = (
        CuentaPasajero.objects.select_related("pasajero", "empresa__configuracion")
        .filter(usuario=usuario)
        .first()
    )
    if cuenta is None or cuenta.confirmada_en is None:
        raise SinCuentaActiva()
    return cuenta


def reservas_de(cuenta: CuentaPasajero):
    return Viaje.objects.filter(pasajero=cuenta.pasajero).order_by("-recogida_en", "-id")


def solicitar(cuenta: CuentaPasajero, datos: dict, *, usuario) -> tuple[Viaje, dict]:
    """Sin verificación (el teléfono se confirmó al crear la cuenta). Mantiene el límite por teléfono."""
    from apps.portal.servicios import _verificar_limite_telefono, validar_capacidad, vuelo_y_recogida

    empresa = cuenta.empresa
    validar_capacidad(empresa, datos.get("pasajeros", 1))  # DC-43
    _verificar_limite_telefono(empresa, cuenta.pasajero.telefono)
    vuelo, recogida = vuelo_y_recogida(empresa, datos)
    with transaction.atomic():
        viaje = reservas.crear_viaje(
            empresa=empresa,
            datos={
                "pasajero": {"nombre": cuenta.pasajero.nombre, "telefono": cuenta.pasajero.telefono},
                "sentido": datos["sentido"],
                "origen_dir": datos["origen_dir"],
                "destino_dir": datos["destino_dir"],
                "recogida_en": recogida,
                "vuelo": vuelo,
                # HU-39 (DC-42).
                "pasajeros": datos.get("pasajeros", 1),
                "maletas": datos.get("maletas", 0),
                "vuelo_salida": datos.get("vuelo_salida"),
            },
            canal=Canal.WEB,
            estado_inicial=EstadoViaje.SOLICITADO,
            actor=Actor.PASAJERO,
            usuario=usuario,
        )
        ahora = timezone.now()
        Pasajero.objects.filter(pk=cuenta.pasajero_id).update(opt_in_en=ahora, privacidad_aceptada_en=ahora)
        avisos.programar(viaje.pk, AVISO_CONFIRMACION)  # HU-21
    return viaje, {
        "estado": viaje.estado,
        "recogida_en": viaje.recogida_en,
        "expira_en": None,
        "mensaje": (
            "Tu solicitud quedó registrada. Te avisaremos por WhatsApp cuando la central asigne un conductor."
        ),
    }


def cancelar(cuenta: CuentaPasajero, viaje_id: int, *, usuario) -> Viaje:
    viaje = reservas_de(cuenta).filter(pk=viaje_id).first()
    if viaje is None:
        from django.http import Http404

        raise Http404
    if viaje.estado not in CANCELABLES:
        raise NoCancelable()
    try:
        return estados.transicionar(
            viaje,
            EstadoViaje.CANCELADO,
            actor=Actor.PASAJERO,
            usuario=usuario,
            motivo_cancelacion="Cancelada por el pasajero desde su cuenta.",
            origen_cancelacion=OrigenCancelacion.PASAJERO,
        )
    except estados.TransicionInvalida as error:
        raise NoCancelable() from error


@transaction.atomic
def eliminar(usuario) -> None:
    """Borra la credencial y el correo; el PASAJERO y sus reservas quedan como de invitado."""
    usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
    CuentaPasajero.objects.filter(usuario=usuario).delete()
    usuario.set_unusable_password()
    usuario.email = f"eliminada-{usuario.pk}@cuentas.invalid"
    usuario.nombre = "Cuenta eliminada"
    usuario.activo = False
    usuario.save(update_fields=["password", "email", "nombre", "activo"])
    credenciales.revocar_sesiones(usuario)
    auditoria.registrar(
        usuario=usuario, entidad=Entidad.USUARIO, entidad_id=usuario.pk, accion="ELIMINAR_CUENTA"
    )
