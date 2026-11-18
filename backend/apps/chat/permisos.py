"""Quién lee y quién escribe en cada conversación (CC-19). Siempre dentro de la misma empresa (RN-13).

- CENTRAL: su conductor y el equipo (administrador y despachadores).
- DIRECTO y GRUPO: solo sus participantes. El administrador no lee los ajenos (Código del Trabajo, art. 5;
  criterio de la DT): para moderar ve solo metadatos (`moderacion`).
- VIAJE y SOPORTE: con el pasajero (HU-66).
"""

from django.db.models import Exists, OuterRef, Q

from apps.cuentas.autenticacion import ROLES_PANEL
from apps.cuentas.models import Rol

from .models import Conversacion, Participante, TipoConversacion

T = TipoConversacion
# El personal de la empresa: los que usan el chat de trabajo.
ROLES_PERSONAL = ROLES_PANEL | {Rol.CONDUCTOR}


def es_equipo(usuario) -> bool:
    return usuario.rol in ROLES_PANEL


def es_personal(usuario) -> bool:
    return usuario.rol in ROLES_PERSONAL


def visibles(usuario):
    """Conversaciones que el usuario puede leer (sin las borradas)."""
    participa = Exists(Participante.objects.filter(conversacion=OuterRef("pk"), usuario=usuario))
    regla = Q(tipo__in=(T.DIRECTO, T.GRUPO)) & Q(participa=True)
    if es_equipo(usuario):
        regla |= Q(tipo=T.CENTRAL)
    elif usuario.rol == Rol.CONDUCTOR:
        regla |= Q(tipo=T.CENTRAL, conductor__usuario=usuario)
    return (
        Conversacion.objects.filter(empresa_id=usuario.empresa_id, borrado_en__isnull=True)
        .annotate(participa=participa)
        .filter(regla)
    )


def puede_escribir(usuario, conversacion: Conversacion) -> bool:
    """En las conversaciones del personal, quien la lee también escribe."""
    return conversacion.tipo in (T.CENTRAL, T.DIRECTO, T.GRUPO)


def destinatarios(conversacion: Conversacion) -> list[int]:
    """Ids de los usuarios que reciben los eventos en vivo de la conversación."""
    from apps.cuentas.models import Usuario

    ids = set(conversacion.participantes.values_list("usuario_id", flat=True))
    if conversacion.tipo == T.CENTRAL:
        ids = set(
            Usuario.objects.filter(
                empresa_id=conversacion.empresa_id, rol__in=ROLES_PANEL, activo=True
            ).values_list("pk", flat=True)
        )
        ids.add(conversacion.conductor.usuario_id)
    return sorted(ids)
