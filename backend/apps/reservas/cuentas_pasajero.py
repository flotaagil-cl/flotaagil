"""HU-35 (CC-16, DC-36): cuenta web opcional del pasajero. El invitado sigue igual.

- Registro por empresa: nombre, teléfono, correo y contraseña. El usuario (rol PASAJERO) queda inactivo y
  recibe por correo un enlace de activación de 24 h (HU-64, DC-61). Al abrirlo se activa y se liga al PASAJERO
  de ese teléfono en la empresa; sin verificar el número, ve solo los viajes que pide con la cuenta (DC-65).
- Con la cuenta activa, sus reservas no se verifican otra vez; se mantiene el límite por teléfono del portal.
- Cancela solo sin conductor asignado (RN-09).
- HU-45 (DC-50): el pasajero edita su nombre y su teléfono (al tiro, sin verificación). Eliminar la cuenta la
  anonimiza: el USUARIO queda inactivo, sin clave ni sesiones y con un correo no utilizable; la fila
  CUENTA_PASAJERO se borra (no queda nada que guardar en ella); el PASAJERO pasa a «Pasajero eliminado» con
  teléfono NULL y sus mensajes quedan sin contenido. Los viajes, pagos, historial y auditoría se conservan.
"""

import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError as ErrorDeDjango
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad
from apps.cuentas import credenciales
from apps.cuentas.models import Rol, Usuario

from . import avisos, estados
from . import servicios as reservas
from .models import (
    Actor,
    Canal,
    CuentaPasajero,
    EstadoViaje,
    HistorialEstado,
    MensajeWhatsapp,
    OrigenCancelacion,
    Pasajero,
    SuscripcionPush,
    Viaje,
)
from .tipos_aviso import AVISO_CONFIRMACION

PALABRA_CONFIRMAR = "confirmar cuenta"
CANCELABLES = (EstadoViaje.PENDIENTE_CONFIRMACION, EstadoViaje.SOLICITADO)  # RN-09: sin conductor asignado
# HU-45: con un viaje en uno de estos estados la cuenta no se puede eliminar hasta que termine o se cancele.
VIAJE_ACTIVO = (
    EstadoViaje.SOLICITADO,
    EstadoViaje.ASIGNADO,
    EstadoViaje.ACEPTADO,
    EstadoViaje.EN_CAMINO,
    EstadoViaje.EN_ZONA,
    EstadoViaje.PASAJERO_A_BORDO,
)
CUERPO_ELIMINADO = "[eliminado]"
MOTIVO_ELIMINAR = "Cuenta eliminada por el titular"


class SinCuentaActiva(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "cuenta_sin_confirmar"
    default_detail = "Activa tu cuenta con el enlace que te enviamos por correo."


class NoCancelable(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "con_conductor"
    default_detail = (
        "Tu viaje ya tiene conductor asignado: no se puede cancelar aquí. Comunícate con la central."
    )


class PrivacidadPendiente(PermissionDenied):
    """DC-44: la cuenta debe aceptar el aviso de privacidad vigente antes de pedir."""

    default_code = "aceptar_privacidad"
    default_detail = "Antes de pedir, acepta el aviso de privacidad."


SAL_ACTIVAR = "cuenta-activar"
ASUNTO_ACTIVAR = "Activa tu cuenta"


def token_activacion(cuenta: CuentaPasajero) -> str:
    return signing.TimestampSigner(salt=SAL_ACTIVAR).sign(str(cuenta.pk))


def texto_activacion(cuenta: CuentaPasajero, url: str) -> str:
    return (
        f"Hola {cuenta.nombre}:\n\nCreaste una cuenta en {cuenta.empresa.razon_social}. Para activarla "
        f"abre este enlace (vale {settings.ACTIVACION_CUENTA_HORAS} horas):\n\n{url}\n\n"
        "Si no fuiste tú, ignora este correo."
    )


def enviar_activacion(cuenta: CuentaPasajero) -> None:
    """DC-61 (HU-64): el enlace de activación va al correo de la cuenta, después del commit."""
    from apps.cuentas.tareas import al_confirmar_correo
    from apps.portal.publico import enlace

    url = enlace(cuenta.empresa, "activar", token_activacion(cuenta))
    al_confirmar_correo(cuenta.usuario.email, ASUNTO_ACTIVAR, texto_activacion(cuenta, url))


class EnlaceActivacionInvalido(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "enlace_invalido"
    default_detail = "El enlace no es válido. Revisa que lo hayas copiado completo."


class EnlaceActivacionVencido(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "enlace_vencido"
    default_detail = "El enlace venció. Pide uno nuevo desde «Activa tu cuenta»."


class TelefonoEnUso(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "telefono_en_uso"
    default_detail = (
        "Ese teléfono ya está asociado a otra cuenta de esta empresa. Si es tuyo, contacta a la empresa."
    )


class ViajeActivo(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "viaje_activo"
    default_detail = "Tienes un viaje en curso. Podrás eliminar tu cuenta cuando termine o lo canceles."


def _telefono_de_otra_cuenta(cuenta: CuentaPasajero, telefono: str) -> bool:
    return (
        CuentaPasajero.objects.filter(empresa=cuenta.empresa, telefono=telefono, confirmada_en__isnull=False)
        .exclude(pk=cuenta.pk)
        .exists()
    )


class CredencialesPendientes(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "cuenta_no_encontrada"
    default_detail = "No encontramos una cuenta por activar con ese correo y contraseña."


class CuentaYaActiva(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "cuenta_activa"
    default_detail = "Tu cuenta ya está activa: ingresa con tu correo y contraseña."


class LimiteReenvios(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "limite_reenvio"
    default_detail = "Ya te reenviamos el mensaje varias veces. Espera unos minutos e intenta de nuevo."


def cuenta_por_credenciales(empresa, email: str, password: str) -> CuentaPasajero:
    """HU-41: la cuenta de esta empresa con ese correo y contraseña (la del alta). Sin decir cuál falló."""
    usuario = Usuario.objects.filter(email__iexact=email.strip(), rol=Rol.PASAJERO).first()
    cuenta = getattr(usuario, "cuenta_pasajero", None) if usuario else None
    if cuenta is None or cuenta.empresa_id != empresa.pk or not usuario.check_password(password):
        raise CredencialesPendientes()
    return cuenta


def estado_activacion(empresa, email: str, password: str) -> dict:
    cuenta = cuenta_por_credenciales(empresa, email, password)
    return {"activa": cuenta.confirmada_en is not None, "correo": cuenta.usuario.email}


@transaction.atomic
def reenviar_activacion(empresa, email: str, password: str) -> CuentaPasajero:
    """HU-41 y HU-64: reenvía el enlace de activación al correo, con límite por cuenta."""
    from apps.cuentas.credenciales import dentro_del_limite

    cuenta = cuenta_por_credenciales(empresa, email, password)
    cuenta = CuentaPasajero.objects.select_for_update().select_related("empresa", "usuario").get(pk=cuenta.pk)
    if cuenta.confirmada_en is not None:
        raise CuentaYaActiva()
    if not dentro_del_limite(f"activacion:{cuenta.pk}", settings.ACTIVACION_MAX_REENVIOS):
        raise LimiteReenvios()
    cuenta.reenviada_en = timezone.now()
    cuenta.save(update_fields=["reenviada_en"])
    enviar_activacion(cuenta)
    return cuenta


@transaction.atomic
def activar(empresa, token: str) -> CuentaPasajero:
    """DC-61 (HU-64): el enlace del correo activa la cuenta (24 h desde su envío). Abrirlo de nuevo no cambia
    nada.

    La cuenta se liga al PASAJERO de su teléfono en la empresa, pero sin verificar el número solo verá los
    viajes que pida ella (DC-65). Si ese teléfono ya es de otra cuenta activa de la empresa, responde 409.
    """
    try:
        pk = int(
            signing.TimestampSigner(salt=SAL_ACTIVAR).unsign(
                token, max_age=timedelta(hours=settings.ACTIVACION_CUENTA_HORAS)
            )
        )
    except signing.SignatureExpired as error:
        raise EnlaceActivacionVencido() from error
    except (signing.BadSignature, ValueError) as error:
        raise EnlaceActivacionInvalido() from error
    cuenta = (
        CuentaPasajero.objects.select_for_update(of=("self",))
        .select_related("usuario")
        .filter(pk=pk, empresa=empresa)
        .first()
    )
    if cuenta is None:
        raise EnlaceActivacionInvalido()
    if cuenta.confirmada_en is not None:
        return cuenta
    if _telefono_de_otra_cuenta(cuenta, cuenta.telefono):
        raise TelefonoEnUso()
    pasajero = reservas.obtener_pasajero(empresa, nombre=cuenta.nombre, telefono=cuenta.telefono)
    cuenta.pasajero, cuenta.confirmada_en = pasajero, timezone.now()
    cuenta.save(update_fields=["pasajero", "confirmada_en"])
    Usuario.objects.filter(pk=cuenta.usuario_id).update(activo=True)
    # DC-65: el correo ya está verificado; sus viajes públicos confirmados por correo pasan a la cuenta. Por
    # teléfono no se asocia nada: no está verificado.
    asociados = list(viajes_del_correo(cuenta).exclude(pasajero=pasajero).values_list("pk", flat=True))
    Viaje.objects.filter(pk__in=asociados).update(pasajero=pasajero)
    auditoria.registrar(
        usuario=cuenta.usuario,
        entidad=Entidad.USUARIO,
        entidad_id=cuenta.usuario_id,
        accion="ACTIVAR_CUENTA",
        datos_previos={"viajes_asociados": asociados} if asociados else None,
    )
    return cuenta


@transaction.atomic
def registrar(empresa, datos: dict) -> CuentaPasajero:
    """Crea la cuenta pendiente y envía el enlace de activación al correo (DC-61). Si el correo ya tiene una
    cuenta pendiente de esta empresa, la reemplaza (otros datos o un enlace vencido); cualquier otro uso del
    correo responde 400."""
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
        usuario=usuario,
        empresa=empresa,
        nombre=datos["nombre"],
        telefono=datos["telefono"],
        # DC-44: la casilla del alta es la aceptación única (fecha y versión del aviso).
        privacidad_aceptada_en=timezone.now(),
        privacidad_version=settings.AVISO_PRIVACIDAD_VERSION,
        acepta_avisos_correo=datos.get("acepta_avisos_correo", False),  # DC-62 (HU-65)
    )
    cuenta.usuario = usuario
    enviar_activacion(cuenta)
    return cuenta


@transaction.atomic
def actualizar_perfil(usuario, datos: dict) -> CuentaPasajero:
    """HU-45 y HU-64 (DC-61): el nombre y el teléfono cambian al tiro (cuenta, PASAJERO y USUARIO). El
    teléfono es un dato de contacto sin verificar: no se fusiona con otro PASAJERO y, al cambiarlo, la cuenta
    deja de ver viajes que no pidió ella (DC-65)."""
    cuenta = cuenta_activa(usuario)
    cuenta = (
        CuentaPasajero.objects.select_for_update(of=("self",))
        .select_related("empresa__configuracion", "pasajero")
        .get(pk=cuenta.pk)
    )
    cambios = []
    nombre = datos.get("nombre")
    if nombre is not None and nombre != cuenta.nombre:
        cuenta.nombre = nombre
        cuenta.save(update_fields=["nombre"])
        Pasajero.objects.filter(pk=cuenta.pasajero_id).update(nombre=nombre)
        Usuario.objects.filter(pk=usuario.pk).update(nombre=nombre)
        cambios.append("nombre")
    telefono = datos.get("telefono")
    if telefono and telefono != cuenta.telefono:
        # Otro PASAJERO de la empresa con ese número es otra persona (o un invitado): no se fusiona (DC-65).
        en_uso = Pasajero.objects.filter(empresa=cuenta.empresa, telefono=telefono).exclude(
            pk=cuenta.pasajero_id
        )
        if _telefono_de_otra_cuenta(cuenta, telefono) or en_uso.exists():
            raise TelefonoEnUso()
        cuenta.telefono, cuenta.telefono_verificado = telefono, False
        cuenta.save(update_fields=["telefono", "telefono_verificado"])
        Pasajero.objects.filter(pk=cuenta.pasajero_id).update(telefono=telefono, verificado_en=None)
        cambios.append("telefono")
    avisos_correo = datos.get("acepta_avisos_correo")
    if avisos_correo is not None and avisos_correo != cuenta.acepta_avisos_correo:
        cuenta.acepta_avisos_correo = avisos_correo
        cuenta.save(update_fields=["acepta_avisos_correo"])
        cambios.append("acepta_avisos_correo")  # DC-62: el consentimiento queda en la auditoría
    if cambios:
        # Solo qué cambió: el nombre o el número anteriores son datos personales y la auditoría se conserva.
        auditoria.registrar(
            usuario=usuario,
            entidad=Entidad.USUARIO,
            entidad_id=usuario.pk,
            accion="EDITAR_PERFIL",
            datos_previos={"campos": cambios},
        )
    return cuenta


def privacidad_vigente(cuenta: CuentaPasajero) -> bool:
    """DC-44: la cuenta aceptó la versión vigente del aviso de privacidad."""
    return cuenta.privacidad_version == settings.AVISO_PRIVACIDAD_VERSION and bool(
        cuenta.privacidad_aceptada_en
    )


def debe_aceptar_privacidad(usuario) -> bool:
    """DC-44: pasajero con cuenta que no aceptó el aviso vigente (cuentas antiguas o versión nueva)."""
    if usuario.rol != Rol.PASAJERO:
        return False
    cuenta = CuentaPasajero.objects.filter(usuario=usuario).first()
    return cuenta is not None and not privacidad_vigente(cuenta)


@transaction.atomic
def aceptar_privacidad(usuario) -> CuentaPasajero:
    """DC-44: registra la aceptación de la versión vigente y la deja en el PASAJERO de la cuenta."""
    cuenta = CuentaPasajero.objects.select_for_update().get(usuario=usuario)
    ahora = timezone.now()
    cuenta.privacidad_aceptada_en, cuenta.privacidad_version = ahora, settings.AVISO_PRIVACIDAD_VERSION
    cuenta.save(update_fields=["privacidad_aceptada_en", "privacidad_version"])
    if cuenta.pasajero_id:
        Pasajero.objects.filter(pk=cuenta.pasajero_id).update(opt_in_en=ahora, privacidad_aceptada_en=ahora)
    auditoria.registrar(
        usuario=usuario,
        entidad=Entidad.USUARIO,
        entidad_id=usuario.pk,
        accion="ACEPTAR_PRIVACIDAD",
        datos_previos={"version": cuenta.privacidad_version},
    )
    return cuenta


def cuenta_activa(usuario) -> CuentaPasajero:
    cuenta = (
        CuentaPasajero.objects.select_related("pasajero", "empresa__configuracion")
        .filter(usuario=usuario)
        .first()
    )
    if cuenta is None or cuenta.confirmada_en is None:
        raise SinCuentaActiva()
    return cuenta


def _confirmados_por_correo():
    """Viajes del formulario público cuyo pasajero confirmó con el enlace del correo (CC-22): pasaron de
    PENDIENTE_CONFIRMACION a SOLICITADO por acción del pasajero, no por teléfono desde el despacho."""
    return Exists(
        HistorialEstado.objects.filter(
            viaje=OuterRef("pk"),
            estado_anterior=EstadoViaje.PENDIENTE_CONFIRMACION,
            estado_nuevo=EstadoViaje.SOLICITADO,
            actor=Actor.PASAJERO,
        )
    )


def viajes_del_correo(cuenta: CuentaPasajero):
    """DC-65 (validado): viajes públicos de la empresa pedidos y confirmados con el correo de la cuenta."""
    return Viaje.objects.filter(
        empresa_id=cuenta.empresa_id, contacto_correo__iexact=cuenta.usuario.email
    ).filter(_confirmados_por_correo())


def _pedidos_por(usuario_id: int):
    """CC-26: viajes que pidió la cuenta (su usuario registró el estado inicial), sean o no para ella."""
    return Exists(HistorialEstado.objects.filter(viaje=OuterRef("pk"), usuario_id=usuario_id))


def reservas_de(cuenta: CuentaPasajero):
    """Con el teléfono verificado por WhatsApp (cuentas anteriores a CC-19), todos los viajes de su PASAJERO;
    si no, los que pidió la cuenta y los públicos confirmados con su mismo correo (DC-65). Un número sin
    verificar no da acceso a viajes de invitado. CC-26: también los que pidió para otras personas."""
    propios = Q(pasajero=cuenta.pasajero)
    if not cuenta.telefono_verificado:
        del_correo = Q(contacto_correo__iexact=cuenta.usuario.email) & Q(_confirmados_por_correo())
        propios &= Q(_pedidos_por(cuenta.usuario_id)) | del_correo
    pedidos = Q(empresa_id=cuenta.empresa_id) & Q(_pedidos_por(cuenta.usuario_id))
    return Viaje.objects.filter(propios | pedidos).order_by("-recogida_en", "-id")


def _verificar_limite(cuenta: CuentaPasajero) -> None:
    """Máximo de solicitudes por cuenta en la ventana (como el límite por teléfono). CC-26: cuenta las que
    pidió para otras personas y un grupo de vehículos separados vale una solicitud."""
    from apps.portal.servicios import LimiteTelefono

    desde = timezone.now() - settings.PORTAL_VENTANA_TELEFONO
    recientes = Viaje.objects.filter(
        empresa_id=cuenta.empresa_id, canal=Canal.WEB, creado_en__gte=desde
    ).filter(Q(pasajero__telefono=cuenta.pasajero.telefono) | Q(_pedidos_por(cuenta.usuario_id)))
    solicitudes = (
        recientes.filter(grupo__isnull=True).count()
        + recientes.filter(grupo__isnull=False).values("grupo").distinct().count()
    )
    if solicitudes >= settings.PORTAL_MAX_SOLICITUDES_POR_TELEFONO:
        raise LimiteTelefono(wait=settings.PORTAL_VENTANA_TELEFONO.total_seconds())


def solicitar(cuenta: CuentaPasajero, datos: dict, *, usuario) -> tuple[list[Viaje], dict]:
    """Sin verificación (el teléfono se confirmó al crear la cuenta). Mantiene el límite por cuenta.

    CC-26 (HU-76, DC-82), con las reglas de CC-23 (DC-76): viaja quien tiene la cuenta o la otra persona, con
    acompañantes en el mismo vehículo o un viaje por persona con el mismo `grupo`. Todo o nada. Si viajan
    otras personas, la cuenta queda en `solicitante_*` y la declaración de que les informó del aviso de
    privacidad, en `terceros_informados_en`. Los avisos del viaje van a la cuenta que pidió.
    """
    from apps.portal.publico import _acompanante, _personas, _validar_personas
    from apps.portal.servicios import validar_capacidad, vuelo_y_recogida

    if not privacidad_vigente(cuenta):
        raise PrivacidadPendiente()
    empresa = cuenta.empresa
    datos = {**datos, "nombre": cuenta.pasajero.nombre, "telefono": cuenta.pasajero.telefono}
    personas = _personas(datos)
    _validar_personas(empresa, datos, personas)
    separados = datos["vehiculos"] == "SEPARADOS" and len(personas) > 1
    viajantes = personas if separados else personas[:1]
    validar_capacidad(empresa, 1 if separados else len(personas))  # DC-43
    _verificar_limite(cuenta)
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
                },
                canal=Canal.WEB,
                estado_inicial=EstadoViaje.SOLICITADO,
                actor=Actor.PASAJERO,
                usuario=usuario,
            )
            if terceros:
                viaje.solicitante_nombre = cuenta.pasajero.nombre
                viaje.solicitante_telefono = cuenta.pasajero.telefono
                viaje.acompanantes = [] if separados else [_acompanante(a) for a in personas[1:]]
                viaje.grupo = grupo
                viaje.terceros_informados_en = ahora
                viaje.save(
                    update_fields=[
                        "solicitante_nombre",
                        "solicitante_telefono",
                        "acompanantes",
                        "grupo",
                        "terceros_informados_en",
                    ]
                )
            viajes.append(viaje)
        if datos["para"] == "MI":
            # DC-44: el pedido no vuelve a aceptar; el PASAJERO lleva la aceptación de la cuenta.
            aceptada = cuenta.privacidad_aceptada_en
            Pasajero.objects.filter(pk=cuenta.pasajero_id).update(
                opt_in_en=aceptada, privacidad_aceptada_en=aceptada
            )
        for viaje in viajes:
            avisos.programar(viaje.pk, AVISO_CONFIRMACION)  # HU-21
    return viajes, {
        "estado": viajes[0].estado,
        "recogida_en": viajes[0].recogida_en,
        "expira_en": None,
        "viajes": len(viajes),
        "mensaje": (
            "Tu solicitud quedó registrada. Te avisaremos cuando la central asigne "
            + ("un conductor a cada viaje." if separados else "un conductor.")
        ),
    }


# HU-44: motivos que el pasajero elige al cancelar desde su cuenta (quedan en el texto del motivo).
MOTIVOS_CANCELACION = {
    "CAMBIO_DE_PLANES": "Cambié de planes",
    "VUELO_CANCELADO": "Mi vuelo se canceló",
    "OTRO": "Otro motivo",
}


def cancelar(cuenta: CuentaPasajero, viaje_id: int, *, usuario, motivo: str | None = None) -> Viaje:
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
            motivo_cancelacion=(
                f"Cancelada por el pasajero desde su cuenta: {MOTIVOS_CANCELACION[motivo]}."
                if motivo in MOTIVOS_CANCELACION
                else "Cancelada por el pasajero desde su cuenta."
            ),
            origen_cancelacion=OrigenCancelacion.PASAJERO,
        )
    except estados.TransicionInvalida as error:
        raise NoCancelable() from error


@transaction.atomic
def eliminar(usuario) -> None:
    """HU-45 (DC-50): anonimiza la cuenta del titular. Con un viaje activo responde 409 (`viaje_activo`).

    - USUARIO: inactivo, correo `eliminado-<id>@invalid`, clave inutilizable y sesiones revocadas.
    - CUENTA_PASAJERO: se borra; lo único que guardaba eran datos personales (nombre, teléfono, fechas).
    - PASAJERO: «Pasajero eliminado» y teléfono NULL.
    - MENSAJE_WHATSAPP: sin contenido; quedan fecha, tipo y estado.
    - VIAJE, PAGO_VIAJE, HISTORIAL_ESTADO y AUDITORIA se conservan; la auditoría registra la eliminación.
    """
    usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
    cuenta = CuentaPasajero.objects.select_for_update().filter(usuario=usuario).first()
    pasajero_id = cuenta.pasajero_id if cuenta else None
    if pasajero_id and Viaje.objects.filter(pasajero_id=pasajero_id, estado__in=VIAJE_ACTIVO).exists():
        raise ViajeActivo()
    CuentaPasajero.objects.filter(usuario=usuario).delete()
    SuscripcionPush.objects.filter(usuario=usuario).delete()  # HU-65: no quedan avisos a sus navegadores
    usuario.set_unusable_password()
    usuario.email = f"eliminado-{usuario.pk}@invalid"
    usuario.nombre = "Cuenta eliminada"
    usuario.activo = False
    usuario.save(update_fields=["password", "email", "nombre", "activo"])
    credenciales.revocar_sesiones(usuario)
    if pasajero_id:
        Pasajero.objects.filter(pk=pasajero_id).update(nombre=Pasajero.NOMBRE_ELIMINADO, telefono=None)
        MensajeWhatsapp.objects.filter(pasajero_id=pasajero_id).update(cuerpo=CUERPO_ELIMINADO)
    auditoria.registrar(
        usuario=usuario,
        entidad=Entidad.USUARIO,
        entidad_id=usuario.pk,
        accion="ELIMINAR_CUENTA",
        motivo=MOTIVO_ELIMINAR,
        datos_previos={"pasajero_id": pasajero_id} if pasajero_id else None,
    )
