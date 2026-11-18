"""Chat sintético para desarrollo (CC-19): el hilo central de conductor1, un grupo y un directo.

Idempotente: si la empresa ya tiene mensajes del chat, no agrega nada.
"""

from apps.cuentas.models import Rol, Usuario

from .models import Conversacion, Mensaje, Participante, RespuestaRapida, TipoConversacion
from .servicios import clave_directo

T = TipoConversacion


def cargar(empresa, conductores: list[Usuario]) -> int:
    if Mensaje.objects.filter(conversacion__empresa=empresa).exists() or len(conductores) < 2:
        return 0
    despacho = Usuario.objects.filter(empresa=empresa, rol=Rol.DESPACHADOR).order_by("pk").first()
    if despacho is None:
        return 0
    uno, dos = conductores[0], conductores[1]
    central, _ = Conversacion.objects.get_or_create(empresa=empresa, tipo=T.CENTRAL, conductor=uno.conductor)
    grupo = Conversacion.objects.create(
        empresa=empresa, tipo=T.GRUPO, nombre="Turno noche", creado_por=despacho
    )
    directo = Conversacion.objects.create(
        empresa=empresa, tipo=T.DIRECTO, clave=clave_directo(uno.pk, dos.pk), creado_por=uno
    )
    Participante.objects.bulk_create(
        [Participante(conversacion=grupo, usuario=u) for u in (despacho, uno, dos)]
        + [Participante(conversacion=directo, usuario=u) for u in (uno, dos)]
    )
    textos = [
        (central, uno, RespuestaRapida.EN_CAMINO),
        (central, despacho, "El pasajero espera en la puerta 3 de llegadas nacionales."),
        (central, uno, RespuestaRapida.LLEGUE),
        (grupo, despacho, "Esta noche hay tres llegadas internacionales entre las 23:00 y la 01:00."),
        (grupo, dos, "Yo tomo la de las 23:40."),
        (directo, dos, "¿Me cubres la fila del aeropuerto 10 minutos?"),
        (directo, uno, "Sí, voy para allá."),
    ]
    for conversacion, autor, texto in textos:
        rapida = texto if isinstance(texto, RespuestaRapida) else ""
        mensaje = Mensaje.objects.create(
            conversacion=conversacion,
            autor=autor,
            texto=texto.label if rapida else texto,
            rapida=rapida,
        )
        Conversacion.objects.filter(pk=conversacion.pk).update(ultimo_mensaje_en=mensaje.creado_en)
    return len(textos)


def historial_whatsapp(empresa) -> int:
    """HU-67 (CC-19): mensajes sintéticos del canal retirado, para ver su historial en solo lectura."""
    from apps.reservas.models import DireccionMensaje, EstadoEntrega, MensajeWhatsapp, TipoMensaje, Viaje

    if MensajeWhatsapp.objects.filter(pasajero__empresa=empresa).exists():
        return 0
    viaje = Viaje.objects.filter(empresa=empresa, pasajero__telefono__isnull=False).order_by("pk").first()
    if viaje is None:
        return 0
    textos = [
        (
            DireccionMensaje.SALIENTE,
            TipoMensaje.PLANTILLA,
            "Tu reserva quedó confirmada. Te avisaremos al asignar.",
        ),
        (DireccionMensaje.ENTRANTE, TipoMensaje.SESION, "Gracias. ¿Pueden llegar 10 minutos antes?"),
        (DireccionMensaje.SALIENTE, TipoMensaje.SESION, "Claro, le avisamos al conductor."),
    ]
    for direccion, tipo, cuerpo in textos:
        MensajeWhatsapp.objects.create(
            pasajero=viaje.pasajero,
            viaje=viaje,
            direccion=direccion,
            tipo=tipo,
            cuerpo=cuerpo,
            estado_entrega=EstadoEntrega.DELIVERED,
        )
    return len(textos)
