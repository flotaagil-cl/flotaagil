"""HU-51 (CC-22): reserva pública sin cuenta, para las empresas sin el módulo de cuentas (DC-51).

CC-23 (HU-72): con un pase de convenio (`pase.py`) la reserva es del convenio y queda a nombre del solicitante
(`crear_con_pase`). Sigue la misma confirmación por correo (D3); en vehículos separados, un solo enlace
confirma todos los viajes del `grupo`.

El viaje nace en PENDIENTE_CONFIRMACION y se envía por correo un enlace firmado (`TimestampSigner`).
Vale hasta `confirmar_hasta` (DC-53) y una sola vez: solo confirma mientras el viaje sigue pendiente (DC-56).
"""

import uuid
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.db import transaction
from django.db.models import CharField
from django.db.models.functions import Cast, Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, Throttled, ValidationError

from apps.convenios.models import Convenio, EstadoConvenio
from apps.cuentas.tareas import al_confirmar_correo
from apps.reservas import avisos, estados
from apps.reservas import servicios as reservas
from apps.reservas.models import Actor, Canal, EstadoViaje, OrigenCancelacion, Pasajero, Viaje
from apps.reservas.tipos_aviso import AVISO_CONFIRMACION

from . import pase as pases
from .servicios import capacidad_maxima, validar_capacidad, vuelo_y_recogida

SAL_CONFIRMAR = "reserva-publica-confirmar"
SAL_AUTORIZAR = "reserva-publica-autorizar"  # HU-54: el contacto del convenio autoriza o rechaza


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


class LimiteIP(Throttled):
    default_code = "limite_ip"
    default_detail = (
        "Se enviaron demasiadas solicitudes desde esta conexión. Espera un rato e intenta de nuevo."
    )


def _verificar_limite_ip(empresa, ip: str | None) -> None:
    """DC-59: envíos por IP y por hora, con el parámetro de la empresa (contador en la caché)."""
    if not ip:
        return
    clave = f"reserva_publica:ip:{empresa.pk}:{ip}"
    cache.add(clave, 0, timeout=3600)
    if cache.incr(clave) > empresa.configuracion.reserva_publica_max_ip_hora:
        raise LimiteIP(wait=3600)


def _verificar_limite_correo(empresa, correo: str, datos: dict) -> None:
    """DC-59: envíos por correo y por hora; los autorizados de un convenio aprobado tienen más margen."""
    config = empresa.configuracion
    maximo = config.reserva_publica_max_correo_hora
    if datos.get("es_empresa"):
        convenio = _convenio_aprobado(empresa, datos.get("empresa_rut") or "")
        if convenio is not None and convenio.autoriza(correo):
            maximo = config.reserva_publica_max_convenio_hora
    if solicitudes_recientes(empresa, correo) >= maximo:
        raise LimiteCorreo(wait=3600)


def solicitudes_recientes(empresa, correo: str) -> int:
    """Solicitudes de la última hora con este correo. CC-23: los viajes de un mismo `grupo` cuentan una
    vez."""
    desde = timezone.now() - timedelta(hours=1)
    return (
        Viaje.objects.filter(empresa=empresa, contacto_correo__iexact=correo, creado_en__gte=desde)
        .annotate(solicitud=Coalesce(Cast("grupo", CharField()), Cast("pk", CharField())))
        .values("solicitud")
        .distinct()
        .count()
    )


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
            f"{settings.WEB_URL_BASE}/solicitar/{viaje.empresa.slug}/"
            f"{'registro-empresa' if viaje.empresa.modulo_cuentas else 'convenio'}"
        )
    return texto


def crear(empresa, datos: dict, ip: str | None = None) -> Viaje:
    """Crea la reserva pendiente y envía el correo con el enlace de confirmación."""
    correo = datos["correo"].strip().lower()
    validar_capacidad(empresa, datos.get("pasajeros", 1))  # DC-43
    _verificar_limite_ip(empresa, ip)
    _verificar_limite_correo(empresa, correo, datos)
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
                "origen_coordenadas": datos.get("origen_coordenadas"),  # HU-71
                "destino_coordenadas": datos.get("destino_coordenadas"),
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
            # HU-54: el RUT de un convenio aprobado. Correo autorizado: el viaje es del convenio. Si no, el
            # contacto del convenio decide (autoriza o rechaza); sin contacto, se cobra como particular.
            convenio = _convenio_aprobado(empresa, datos["empresa_rut"])
            if convenio is not None and (convenio.autoriza(correo) or _contacto(convenio)):
                # Un viaje con convenio va por el canal CONVENIO (restricción `viaje_convenio_segun_canal`).
                viaje.convenio, viaje.canal = convenio, Canal.CONVENIO
                viaje.confirma_convenio = not convenio.autoriza(correo)
                campos += ["convenio", "canal", "confirma_convenio"]
        viaje.save(update_fields=campos)
        # Ley 21.719: evidencia de la aceptación del aviso de privacidad (la versión queda en el viaje).
        Pasajero.objects.filter(pk=viaje.pasajero_id).update(privacidad_aceptada_en=ahora)
        avisar_solicitud(viaje)
    return viaje


def _personas(datos: dict) -> list[dict]:
    """El pasajero principal (quien pide, o la otra persona) y luego los acompañantes."""
    if datos["para"] == "OTRO":
        principal = {
            "nombre": datos["pasajero_nombre"],
            "cargo": datos["pasajero_cargo"],
            "telefono": datos["pasajero_telefono"],
            "correo": datos.get("pasajero_correo") or "",
        }
    else:
        principal = {"nombre": datos["nombre"], "cargo": "", "telefono": datos["telefono"], "correo": ""}
    return [principal, *datos["acompanantes"]]


def _validar_personas(empresa, datos: dict, personas: list[dict]) -> None:
    config = empresa.configuracion
    if len(personas) > config.convenio_max_personas:
        raise ValidationError(
            {
                "acompanantes": [
                    f"Puedes pedir para hasta {config.convenio_max_personas} personas por solicitud."
                ]
            }
        )
    if datos["vehiculos"] == "MISMO" and len(personas) > capacidad_maxima(empresa):
        raise ValidationError(
            {
                "acompanantes": [
                    f"Podemos llevar hasta {capacidad_maxima(empresa)} pasajeros en un vehículo. "
                    "Elige «Vehículos separados» para el resto."
                ]
            }
        )


def crear_con_pase(empresa, datos: dict, ip: str | None = None) -> list[Viaje]:
    """CC-23 (HU-72): reserva de convenio con pase. Todo o nada: crea uno o varios viajes en una transacción.

    - Quien pide (D7) queda en `solicitante_*` y `contacto_correo` = el correo del pase: confirma y
      recibe avisos.
    - `pasajero` es quien viaja: el propio solicitante (MI) o la otra persona (OTRO, teléfono obligatorio,
      D4).
    - MISMO: un viaje con `acompanantes` (sin padrón). SEPARADOS: un viaje por persona con el mismo `grupo`.
    - Nace en PENDIENTE_CONFIRMACION con el plazo de DC-53 y un solo enlace al correo del pase (D3).
    """
    convenio, correo = pases.validar(empresa, datos["pase"])
    personas = _personas(datos)
    _validar_personas(empresa, datos, personas)
    _verificar_limite_ip(empresa, ip)
    if solicitudes_recientes(empresa, correo) >= empresa.configuracion.reserva_publica_max_convenio_hora:
        raise LimiteCorreo(wait=3600)
    vuelo, recogida = vuelo_y_recogida(empresa, datos)
    ahora = timezone.now()
    separados = datos["vehiculos"] == "SEPARADOS" and len(personas) > 1
    viajantes = personas if separados else personas[:1]
    grupo = uuid.uuid4() if separados else None
    viajes = []
    with transaction.atomic():
        for indice, persona in enumerate(viajantes):
            viaje = reservas.crear_viaje(
                empresa=empresa,
                datos={
                    "pasajero": {"nombre": persona["nombre"], "telefono": persona["telefono"]},
                    "convenio": convenio,
                    "sentido": datos["sentido"],
                    "origen_dir": datos["origen_dir"],
                    "destino_dir": datos["destino_dir"],
                    "origen_coordenadas": datos.get("origen_coordenadas"),
                    "destino_coordenadas": datos.get("destino_coordenadas"),
                    "recogida_en": recogida,
                    "vuelo": vuelo,
                    "pasajeros": 1 if separados else len(personas),
                    "maletas": datos.get("maletas", 0) if indice == 0 else 0,
                    "vuelo_salida": datos.get("vuelo_salida"),
                },
                canal=Canal.CONVENIO,
                estado_inicial=EstadoViaje.PENDIENTE_CONFIRMACION,
                actor=Actor.PASAJERO,
            )
            viaje.contacto_correo = correo
            viaje.privacidad_version = settings.AVISO_PRIVACIDAD_VERSION
            viaje.confirmar_hasta = plazo_confirmacion(empresa.configuracion, viaje.recogida_en, ahora)
            viaje.solicitante_nombre = datos["nombre"]
            viaje.solicitante_telefono = datos["telefono"]
            viaje.pasajero_cargo = persona.get("cargo") or None
            viaje.pasajero_correo = persona.get("correo") or None
            viaje.acompanantes = [] if separados else [_acompanante(a) for a in personas[1:]]
            viaje.grupo = grupo
            if len(personas) > 1 or datos["para"] == "OTRO":
                viaje.terceros_informados_en = ahora
            viaje.save()
            viajes.append(viaje)
        if datos["para"] == "MI":
            # Ley 21.719: quien pide para sí acepta el aviso; por los demás solo declara que les informó.
            Pasajero.objects.filter(pk=viajes[0].pasajero_id).update(privacidad_aceptada_en=ahora)
        avisar_solicitud_pase(viajes, convenio, personas, separados)
    return viajes


def _acompanante(persona: dict) -> dict:
    return {campo: persona.get(campo) or "" for campo in ("nombre", "cargo", "telefono", "correo")}


def _resumen(viaje: Viaje) -> str:
    texto = (
        f"{viaje.origen_dir} → {viaje.destino_dir}, {timezone.localtime(viaje.recogida_en):%d-%m-%Y %H:%M}"
    )
    vuelo = getattr(viaje, "vuelo", None)
    if vuelo is not None:
        texto += f", vuelo {vuelo.numero}"
    elif viaje.vuelo_salida_numero:
        texto += f", vuelo {viaje.vuelo_salida_numero}"
    return texto


def avisar_solicitud_pase(viajes: list[Viaje], convenio: Convenio, personas: list[dict], separados: bool):
    """D3/D7: un solo enlace al solicitante; aviso informativo (sin enlace) a quienes dejaron correo y, si
    quien pide no es el contacto del convenio, al contacto."""
    primero = viajes[0]
    empresa = primero.empresa
    url = enlace(empresa, "confirmar", token_de(primero))
    numeros = ", ".join(f"N.º {v.pk}" for v in viajes)
    detalle = "\n".join(f"- N.º {v.pk}: {v.pasajero.nombre}" for v in viajes) if separados else ""
    acompanan = ", ".join(p["nombre"] for p in personas[1:])
    texto = (
        f"Hola {primero.solicitante_nombre}:\n\nRecibimos tu solicitud de traslado ({numeros}) con "
        f"{empresa.razon_social}, a nombre del convenio de {convenio.cliente_nombre}: "
        f"{_resumen(primero)}.\n\n"
        + (f"Un vehículo por persona:\n{detalle}\n\n" if separados else "")
        + (
            f"Pasajero: {primero.pasajero.nombre}" + (f", con {acompanan}" if acompanan else "") + ".\n\n"
            if not separados
            else ""
        )
        + f"Para confirmar{' todos los viajes' if separados else ''}, abre este enlace antes del "
        f"{timezone.localtime(primero.confirmar_hasta):%d-%m-%Y %H:%M}:\n{url}\n\n"
        "Si no fuiste tú, ignora este correo."
    )
    al_confirmar_correo(
        primero.contacto_correo,
        f"Confirma tu reserva {numeros} · {empresa.razon_social}",
        texto,
        empresa.pk,
    )
    informados = {primero.contacto_correo}
    for persona in personas:
        destino = (persona.get("correo") or "").lower()
        if destino and destino not in informados:
            informados.add(destino)
            al_confirmar_correo(
                destino,
                f"Tu traslado con {empresa.razon_social}",
                f"Hola {persona['nombre']}:\n\n{primero.solicitante_nombre} pidió un traslado para ti con "
                f"{empresa.razon_social} ({convenio.cliente_nombre}): {_resumen(primero)}.\n\n"
                "Este correo es solo informativo: la reserva la confirma quien la pidió.",
                empresa.pk,
            )
    contacto = (convenio.contacto_correo or "").lower()
    if contacto and contacto != primero.contacto_correo:
        al_confirmar_correo(
            contacto,
            f"Nueva reserva con el convenio de {convenio.cliente_nombre}",
            f"Hola {convenio.encargado_nombre or ''}:\n\n{primero.solicitante_nombre} "
            f"({primero.contacto_correo}) pidió con la clave del convenio {len(viajes)} "
            f"{'traslados' if len(viajes) > 1 else 'traslado'} ({numeros}): {_resumen(primero)}.\n\n"
            "Es solo un aviso: no necesitas hacer nada. Si no lo reconoces, pide a "
            f"{empresa.razon_social} que regenere la clave.",
            empresa.pk,
        )


def _convenio_aprobado(empresa, rut: str) -> Convenio | None:
    return (
        Convenio.objects.select_related("usuario")
        .filter(empresa=empresa, cliente_rut=rut, estado=EstadoConvenio.APROBADO)
        .first()
    )


def _contacto(convenio: Convenio) -> str | None:
    return convenio.contacto_correo or (convenio.usuario.email if convenio.usuario_id else None)


def avisar_solicitud(viaje: Viaje) -> None:
    if viaje.confirma_convenio:
        _pedir_autorizacion(viaje)
        return
    url = enlace(viaje.empresa, "confirmar", token_de(viaje))
    al_confirmar_correo(
        viaje.contacto_correo,
        f"Confirma tu reserva N.º {viaje.pk} · {viaje.empresa.razon_social}",
        texto_solicitud(viaje, url),
        viaje.empresa_id,
    )


def confirmar(empresa, token: str) -> Viaje:
    """El pasajero abre el enlace: la reserva pasa a SOLICITADO, una sola vez y dentro del plazo.

    CC-23 (DC-76): si el viaje es de un `grupo` (vehículos separados), el mismo enlace confirma todos los
    viajes del grupo que siguen pendientes, en una transacción; los cancelados o ya confirmados no se tocan.
    """
    viaje = viaje_del_token(empresa, token)
    if viaje.grupo:
        return _confirmar_grupo(empresa, viaje)
    if viaje.estado != EstadoViaje.PENDIENTE_CONFIRMACION or viaje.confirma_convenio:
        raise EnlaceUsado()
    if viaje.confirmar_hasta and viaje.confirmar_hasta < timezone.now():
        raise EnlaceVencido()
    try:
        viaje = estados.transicionar(
            viaje, EstadoViaje.SOLICITADO, desde=EstadoViaje.PENDIENTE_CONFIRMACION, actor=Actor.PASAJERO
        )
    except estados.TransicionInvalida as error:  # otro clic simultáneo ya la confirmó
        raise EnlaceUsado() from error
    avisos.programar(viaje.pk, AVISO_CONFIRMACION)  # HU-56
    return viaje


def _confirmar_grupo(empresa, viaje: Viaje) -> Viaje:
    with transaction.atomic():
        pendientes = list(
            Viaje.objects.select_for_update()
            .filter(empresa=empresa, grupo=viaje.grupo, estado=EstadoViaje.PENDIENTE_CONFIRMACION)
            .order_by("pk")
        )
        if not pendientes:
            raise EnlaceUsado()
        if any(v.confirmar_hasta and v.confirmar_hasta < timezone.now() for v in pendientes):
            raise EnlaceVencido()
        confirmados = []
        for pendiente in pendientes:
            try:
                confirmados.append(
                    estados.transicionar(
                        pendiente,
                        EstadoViaje.SOLICITADO,
                        desde=EstadoViaje.PENDIENTE_CONFIRMACION,
                        actor=Actor.PASAJERO,
                    )
                )
            except estados.TransicionInvalida as error:
                raise EnlaceUsado() from error
    for confirmado in confirmados:
        avisos.programar(confirmado.pk, AVISO_CONFIRMACION)  # HU-56
    return next((c for c in confirmados if c.pk == viaje.pk), confirmados[0])


def _pedir_autorizacion(viaje: Viaje) -> None:
    """HU-54: el correo que reservó no está autorizado; se avisa al pasajero y el enlace va al contacto."""
    convenio = viaje.convenio
    cuando = f"{timezone.localtime(viaje.recogida_en):%d-%m-%Y %H:%M}"
    al_confirmar_correo(
        viaje.contacto_correo,
        f"Tu reserva N.º {viaje.pk} espera la autorización de {convenio.cliente_nombre}",
        f"Hola {viaje.pasajero.nombre}:\n\nRecibimos tu solicitud N.º {viaje.pk} ({viaje.origen_dir} → "
        f"{viaje.destino_dir}, {cuando}). Como tu correo no está autorizado en el convenio de "
        f"{convenio.cliente_nombre}, le pedimos a la empresa que la autorice. Te avisaremos por correo.",
        viaje.empresa_id,
    )
    url = enlace(viaje.empresa, "autorizar", token_de(viaje, SAL_AUTORIZAR))
    al_confirmar_correo(
        _contacto(convenio),
        f"Autoriza la reserva N.º {viaje.pk} · {viaje.empresa.razon_social}",
        f"Hola {convenio.encargado_nombre or ''}:\n\n{viaje.pasajero.nombre} ({viaje.contacto_correo}) "
        f"pidió un traslado con el RUT de {convenio.cliente_nombre}: {viaje.origen_dir} → "
        f"{viaje.destino_dir}, {cuando}.\n\n"
        f"Para autorizarlo o rechazarlo, abre este enlace antes del "
        f"{timezone.localtime(viaje.confirmar_hasta):%d-%m-%Y %H:%M}:\n{url}\n",
        viaje.empresa_id,
    )


def autorizar(empresa, token: str, decision: str) -> Viaje:
    """HU-54: el contacto del convenio autoriza (SOLICITADO) o rechaza (CANCELADO y aviso al solicitante)."""
    viaje = viaje_del_token(empresa, token, SAL_AUTORIZAR)
    if viaje.estado != EstadoViaje.PENDIENTE_CONFIRMACION or not viaje.confirma_convenio:
        raise EnlaceUsado()
    if viaje.confirmar_hasta and viaje.confirmar_hasta < timezone.now():
        raise EnlaceVencido()
    # DC-59 (HU-60): quien decide por el convenio no es un PASAJERO: el historial queda con actor SISTEMA y la
    # autorización guarda el correo del contacto y la hora; el rechazo usa el origen CONVENIO.
    try:
        if decision == "autorizar":
            viaje = estados.transicionar(
                viaje, EstadoViaje.SOLICITADO, desde=EstadoViaje.PENDIENTE_CONFIRMACION, actor=Actor.SISTEMA
            )
            Viaje.objects.filter(pk=viaje.pk).update(
                autorizado_por_correo=_contacto(viaje.convenio), autorizado_en=timezone.now()
            )
            avisos.programar(viaje.pk, AVISO_CONFIRMACION)  # HU-56
            viaje.refresh_from_db()
            return viaje
        viaje = estados.transicionar(
            viaje,
            EstadoViaje.CANCELADO,
            desde=EstadoViaje.PENDIENTE_CONFIRMACION,
            actor=Actor.SISTEMA,
            motivo_cancelacion=f"No autorizada por el convenio de {viaje.convenio.cliente_nombre}.",
            origen_cancelacion=OrigenCancelacion.CONVENIO,
        )
    except estados.TransicionInvalida as error:
        raise EnlaceUsado() from error
    al_confirmar_correo(
        viaje.contacto_correo,
        f"Tu reserva N.º {viaje.pk} no fue autorizada",
        f"Hola {viaje.pasajero.nombre}:\n\n{viaje.convenio.cliente_nombre} no autorizó tu reserva "
        f"N.º {viaje.pk}, así que quedó cancelada. Si la necesitas igual, puedes pedirla como particular.",
        viaje.empresa_id,
    )
    return viaje


class YaCalificado(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "ya_calificado"
    default_detail = "Este viaje ya tiene tu calificación. ¡Gracias!"


def calificar(empresa, token: str, puntaje: int):
    """HU-56: la encuesta por correo crea la misma CALIFICACION de HU-24 (RN-14: opcional). Vale una vez."""
    from apps.reservas.avisos_correo import viaje_de_encuesta
    from apps.reservas.models import Calificacion

    try:
        pk = viaje_de_encuesta(token)
    except (signing.BadSignature, ValueError) as error:
        raise EnlaceInvalido() from error
    viaje = Viaje.objects.filter(pk=pk, empresa=empresa, estado=EstadoViaje.FINALIZADO).first()
    if viaje is None:
        raise EnlaceInvalido()
    calificacion, creada = Calificacion.objects.get_or_create(viaje=viaje, defaults={"puntaje": puntaje})
    if not creada:
        raise YaCalificado()
    return calificacion
