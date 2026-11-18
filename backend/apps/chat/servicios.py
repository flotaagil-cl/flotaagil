"""Operaciones del chat (CC-19): centrales, directos, publicar, leído y eventos en vivo por usuario."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, transaction
from django.db.models import Max, Min
from django.utils import timezone

from apps.cuentas.models import Usuario
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
    return conversacion.nombre


def nombre_autor(mensaje: Mensaje, conversacion: Conversacion, usuario: Usuario) -> str:
    """En el hilo central el conductor ve a todo el equipo como «Central»; el equipo ve quién escribió."""
    if conversacion.tipo == T.CENTRAL and not es_equipo(usuario) and mensaje.autor_id != usuario.pk:
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
    if conversacion.tipo == T.CENTRAL:
        conductor = conversacion.conductor.usuario_id
        otros = otros.filter(usuario_id=conductor) if usuario.pk != conductor else otros
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


def borrar_grupo(conversacion: Conversacion) -> None:
    ids = destinatarios(conversacion)
    Conversacion.objects.filter(pk=conversacion.pk).update(borrado_en=timezone.now())
    avisar(ids, lambda _id: {"tipo": "conversaciones"})


def _serializable(datos: dict) -> dict:
    return {**datos, "creado_en": datos["creado_en"].isoformat()}
