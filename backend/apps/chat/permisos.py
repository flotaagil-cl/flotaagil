"""Quién lee y quién escribe en cada conversación (CC-19). Siempre dentro de la misma empresa (RN-13).

- CENTRAL: su conductor y el equipo (administrador y despachadores).
- DIRECTO y GRUPO: solo sus participantes. El administrador no lee los ajenos (Código del Trabajo, art. 5;
  criterio de la DT): para moderar ve solo metadatos (`moderacion`).
- VIAJE (HU-66, módulo de cuentas): el conductor del viaje y la cuenta del pasajero. Escriben de ACEPTADO a
  PASAJERO_A_BORDO; después, solo lectura. El conductor ve solo el nombre del pasajero. El equipo no lo ve en
  su lista: lo lee en solo lectura desde la reserva y cada lectura queda en auditoría.
- SOPORTE (HU-66): la cuenta del pasajero y el equipo.
"""

from django.db.models import Exists, OuterRef, Q

from apps.cuentas.autenticacion import ROLES_PANEL
from apps.cuentas.models import Rol

from .models import Conversacion, Participante, TipoConversacion

T = TipoConversacion
# El personal de la empresa: los que usan el chat de trabajo.
ROLES_PERSONAL = ROLES_PANEL | {Rol.CONDUCTOR}
# Estados en que conductor y pasajero se escriben (HU-66); FINALIZADO y CANCELADO quedan en solo lectura.
ESTADOS_CHAT_VIAJE = ("ACEPTADO", "EN_CAMINO", "EN_ZONA", "PASAJERO_A_BORDO")
ESTADOS_CON_CHAT = (*ESTADOS_CHAT_VIAJE, "FINALIZADO", "CANCELADO")


def es_equipo(usuario) -> bool:
    return usuario.rol in ROLES_PANEL


def es_personal(usuario) -> bool:
    return usuario.rol in ROLES_PERSONAL


def es_pasajero_con_modulo(usuario) -> bool:
    return usuario.rol == Rol.PASAJERO and usuario.empresa.modulo_cuentas


def viajes_del_pasajero(usuario):
    """Ids de los viajes que la cuenta del pasajero ve (DC-65), como subconsulta."""
    from apps.reservas.cuentas_pasajero import reservas_de
    from apps.reservas.models import CuentaPasajero, Viaje

    cuenta = CuentaPasajero.objects.filter(usuario=usuario, confirmada_en__isnull=False).first()
    return reservas_de(cuenta).values("pk") if cuenta else Viaje.objects.none().values("pk")


def visibles(usuario):
    """Conversaciones que el usuario ve en su lista y puede leer (sin las borradas)."""
    participa = Exists(Participante.objects.filter(conversacion=OuterRef("pk"), usuario=usuario))
    regla = Q(tipo__in=(T.DIRECTO, T.GRUPO)) & Q(participa=True)
    if es_equipo(usuario):
        regla |= Q(tipo__in=(T.CENTRAL, T.SOPORTE))
    elif usuario.rol == Rol.CONDUCTOR:
        regla |= Q(tipo=T.CENTRAL, conductor__usuario=usuario) | Q(
            tipo=T.VIAJE, viaje__conductor__usuario=usuario
        )
    elif es_pasajero_con_modulo(usuario):
        regla = Q(tipo=T.SOPORTE, pasajero_usuario=usuario) | Q(
            tipo=T.VIAJE, viaje__in=viajes_del_pasajero(usuario)
        )
    else:
        return Conversacion.objects.none()
    return (
        Conversacion.objects.filter(empresa_id=usuario.empresa_id, borrado_en__isnull=True)
        .annotate(participa=participa)
        .filter(regla)
    )


def puede_escribir(usuario, conversacion: Conversacion) -> bool:
    """El personal escribe donde lee; en un viaje, solo conductor y pasajero mientras está en curso."""
    if conversacion.tipo == T.VIAJE:
        return not es_equipo(usuario) and conversacion.viaje.estado in ESTADOS_CHAT_VIAJE
    return True


def destinatarios(conversacion: Conversacion) -> list[int]:
    """Ids de los usuarios que reciben los eventos en vivo de la conversación."""
    from apps.cuentas.models import Usuario
    from apps.reservas.avisos_pasajero import cuenta_del_viaje

    ids = set(conversacion.participantes.values_list("usuario_id", flat=True))
    equipo = Usuario.objects.filter(empresa_id=conversacion.empresa_id, rol__in=ROLES_PANEL, activo=True)
    if conversacion.tipo == T.CENTRAL:
        ids = set(equipo.values_list("pk", flat=True)) | {conversacion.conductor.usuario_id}
    elif conversacion.tipo == T.SOPORTE:
        ids = set(equipo.values_list("pk", flat=True)) | {conversacion.pasajero_usuario_id}
    elif conversacion.tipo == T.VIAJE:
        viaje = conversacion.viaje
        cuenta = cuenta_del_viaje(viaje)  # DC-65: solo la cuenta que ve ese viaje
        ids = {cuenta.usuario_id} if cuenta else set()
        if viaje.conductor_id:
            ids.add(viaje.conductor.usuario_id)
    return sorted(ids)
