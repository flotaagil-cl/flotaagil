"""Operaciones del chat (CC-19): centrales, directos, publicar, leído y eventos en vivo por usuario."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, transaction
from django.db.models import Max, Min
from django.utils import timezone

from apps.cuentas.autenticacion import ROLES_PANEL
from apps.cuentas.models import Rol, Usuario
from apps.flota.models import Conductor

from .models import Conversacion, Mensaje, Participante, TipoConversacion
from .permisos import destinatarios, es_equipo

T = TipoConversacion
NOMBRE_CENTRAL = "Central"


def grupo_usuario(id_usuario: int) -> str:
    return f"chat_usuario_{id_usuario}"


def avisar(ids, datos_por_usuario) -> None:
    """Después del commit envía a cada usuario su evento. `datos_por_usuario(id)` arma el de cada uno."""
    ids = list(ids)

    def enviar():
        capa = get_channel_layer()
        if capa is None:
            return
        for id_usuario in ids:
            async_to_sync(capa.group_send)(
                grupo_usuario(id_usuario), {"type": "chat.evento", "datos": datos_por_usuario(id_usuario)}
            )

    transaction.on_commit(enviar, robust=True)


def asegurar_centrales(empresa_id: int) -> None:
    """Un hilo central por conductor activo, creado la primera vez que alguien lo necesita."""
    faltan = Conductor.objects.filter(usuario__empresa_id=empresa_id, usuario__activo=True).exclude(
        pk__in=Conversacion.objects.filter(tipo=T.CENTRAL, empresa_id=empresa_id).values("conductor_id")
    )
    Conversacion.objects.bulk_create(
        [Conversacion(empresa_id=empresa_id, tipo=T.CENTRAL, conductor=c) for c in faltan],
        ignore_conflicts=True,
    )


def _uno_solo(filtro: dict, crear: dict) -> Conversacion:
    """Get-or-create que tolera dos aperturas simultáneas (la restricción única decide)."""
    existente = Conversacion.objects.filter(**filtro).first()
    if existente:
        return existente
    try:
        with transaction.atomic():
            return Conversacion.objects.create(**filtro, **crear)
    except IntegrityError:
        return Conversacion.objects.get(**filtro)


def conversacion_de_viaje(viaje) -> Conversacion:
    """HU-66: el hilo del viaje entre el conductor y el pasajero, uno por viaje."""
    return _uno_solo({"tipo": T.VIAJE, "viaje": viaje}, {"empresa_id": viaje.empresa_id})


def soporte_de(usuario: Usuario) -> Conversacion:
    """HU-66: el hilo de soporte del pasajero con la central, uno por cuenta."""
    return _uno_solo({"tipo": T.SOPORTE, "pasajero_usuario": usuario}, {"empresa_id": usuario.empresa_id})


def clave_directo(a: int, b: int) -> str:
    return f"{min(a, b)}-{max(a, b)}"


def directo(usuario: Usuario, otro: Usuario) -> tuple[Conversacion, bool]:
    """El directo entre dos personas es uno solo: si ya existe se devuelve (también si se pide dos veces)."""
    clave = clave_directo(usuario.pk, otro.pk)
    existente = Conversacion.objects.filter(
        empresa_id=usuario.empresa_id, tipo=T.DIRECTO, clave=clave
    ).first()
    if existente:
        return existente, False
    try:
        with transaction.atomic():
            conversacion = Conversacion.objects.create(
                empresa_id=usuario.empresa_id, tipo=T.DIRECTO, clave=clave, creado_por=usuario
            )
            Participante.objects.bulk_create(
                [Participante(conversacion=conversacion, usuario=u) for u in (usuario, otro)]
            )
    except IntegrityError:
        return Conversacion.objects.get(empresa_id=usuario.empresa_id, tipo=T.DIRECTO, clave=clave), False
    return conversacion, True


def titulo(conversacion: Conversacion, usuario: Usuario) -> str:
    if conversacion.tipo == T.CENTRAL:
        return conversacion.conductor.usuario.nombre if es_equipo(usuario) else NOMBRE_CENTRAL
    if conversacion.tipo == T.DIRECTO:
        otros = [p.usuario.nombre for p in conversacion.participantes.all() if p.usuario_id != usuario.pk]
        return otros[0] if otros else usuario.nombre
    if conversacion.tipo == T.VIAJE:
        # HU-66: el conductor ve solo el nombre del pasajero; el pasajero, el de su conductor.
        viaje = conversacion.viaje
        if usuario.rol == Rol.PASAJERO:
            return viaje.conductor.usuario.nombre if viaje.conductor_id else f"Viaje N.º {viaje.pk}"
        return viaje.pasajero.nombre
    if conversacion.tipo == T.SOPORTE:
        return f"Soporte · {conversacion.pasajero_usuario.nombre}" if es_equipo(usuario) else "Soporte"
    return conversacion.nombre


def nombre_autor(mensaje: Mensaje, conversacion: Conversacion, usuario: Usuario) -> str:
    """En el hilo central y en el de soporte, el conductor o el pasajero ven al equipo como «Central»; el
    equipo ve quién escribió."""
    del_equipo_oculto = conversacion.tipo in (T.CENTRAL, T.SOPORTE) and not es_equipo(usuario)
    if del_equipo_oculto and mensaje.autor_id != usuario.pk and mensaje.autor.rol in ROLES_PANEL:
        return NOMBRE_CENTRAL
    return mensaje.autor.nombre


def datos_mensaje(mensaje: Mensaje, conversacion: Conversacion, usuario: Usuario) -> dict:
    return {
        "id": mensaje.pk,
        "conversacion": conversacion.pk,
        "texto": mensaje.texto,
        "rapida": mensaje.rapida,
        "autor": nombre_autor(mensaje, conversacion, usuario),
        "propio": mensaje.autor_id == usuario.pk,
        "creado_en": mensaje.creado_en,
    }


def leido_por_otros(conversacion: Conversacion, usuario: Usuario) -> int:
    """Hasta qué mensaje leyó «el otro lado»: en un grupo, todos los demás; en el central, el otro lado."""
    otros = Participante.objects.filter(conversacion=conversacion).exclude(usuario=usuario)
    if conversacion.tipo in (T.CENTRAL, T.SOPORTE):
        # El otro lado del equipo es el conductor (central) o el pasajero (soporte), y viceversa.
        unico = (
            conversacion.conductor.usuario_id
            if conversacion.tipo == T.CENTRAL
            else conversacion.pasajero_usuario_id
        )
        otros = otros.filter(usuario_id=unico) if usuario.pk != unico else otros
    elif conversacion.tipo == T.VIAJE:
        otros = otros.exclude(usuario__rol__in=ROLES_PANEL)  # la lectura de la central no cuenta como leído
    agregado = Min if conversacion.tipo == T.GRUPO else Max
    return otros.aggregate(v=agregado("ultimo_leido_id"))["v"] or 0


def marcar_leido(usuario: Usuario, conversacion: Conversacion, hasta: int) -> None:
    participante, _ = Participante.objects.get_or_create(conversacion=conversacion, usuario=usuario)
    if hasta > participante.ultimo_leido_id:
        Participante.objects.filter(pk=participante.pk, ultimo_leido_id__lt=hasta).update(
            ultimo_leido_id=hasta
        )
        otros = [i for i in destinatarios(conversacion) if i != usuario.pk]
        avisar(otros, lambda _id: {"tipo": "leido", "conversacion": conversacion.pk})


def publicar(usuario: Usuario, conversacion: Conversacion, texto: str, rapida: str = "") -> Mensaje:
    with transaction.atomic():
        mensaje = Mensaje.objects.create(conversacion=conversacion, autor=usuario, texto=texto, rapida=rapida)
        Conversacion.objects.filter(pk=conversacion.pk).update(ultimo_mensaje_en=mensaje.creado_en)
        participante, _ = Participante.objects.get_or_create(conversacion=conversacion, usuario=usuario)
        Participante.objects.filter(pk=participante.pk).update(ultimo_leido_id=mensaje.pk)
        receptores = {u.pk: u for u in Usuario.objects.filter(pk__in=destinatarios(conversacion))}
        avisar(
            receptores,
            lambda i: {
                "tipo": "mensaje",
                "mensaje": _serializable(datos_mensaje(mensaje, conversacion, receptores[i])),
            },
        )
    return mensaje


def avisar_cambio(conversacion: Conversacion, ids_extra=()) -> None:
    """Cambió una conversación (creada, renombrada, borrada o con otros integrantes): se piden las listas."""
    ids = set(destinatarios(conversacion)) | set(ids_extra)
    avisar(ids, lambda _id: {"tipo": "conversaciones"})


def alertar_llegada(viaje) -> None:
    """HU-63: la geocerca marcó EN_ZONA. Avisa al equipo de la empresa en el panel (sonido y notificación)."""
    nombre = viaje.conductor.usuario.nombre
    ids = Usuario.objects.filter(empresa_id=viaje.empresa_id, rol__in=ROLES_PANEL, activo=True).values_list(
        "pk", flat=True
    )
    datos = {
        "tipo": "llegada",
        "viaje": viaje.pk,
        "conductor": nombre,
        "texto": f"{nombre} llegó al origen del viaje #{viaje.pk}",
    }
    avisar(ids, lambda _id: datos)


def borrar_grupo(conversacion: Conversacion) -> None:
    ids = destinatarios(conversacion)
    Conversacion.objects.filter(pk=conversacion.pk).update(borrado_en=timezone.now())
    avisar(ids, lambda _id: {"tipo": "conversaciones"})


def _serializable(datos: dict) -> dict:
    return {**datos, "creado_en": datos["creado_en"].isoformat()}
