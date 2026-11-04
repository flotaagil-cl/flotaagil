"""Mapa en tiempo real (HU-02): estado y última posición de los conductores en turno, por empresa.

Cada cambio (posición recibida, inicio o fin de turno, cuenta deshabilitada) se envía al grupo de la empresa
del conductor después del commit. El mapa recibe la foto inicial al conectarse y luego solo los cambios.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import OuterRef, Subquery

from .models import Conductor, EstadoConductor, PosicionGps

EN_TURNO = (EstadoConductor.DISPONIBLE, EstadoConductor.EN_VIAJE)


def grupo_mapa(empresa_id: int) -> str:
    return f"mapa_empresa_{empresa_id}"


def datos_conductor(conductor: Conductor, posicion: PosicionGps | None) -> dict:
    return {
        "id": conductor.pk,
        "nombre": conductor.usuario.nombre,
        "estado": conductor.estado,
        "patente": conductor.vehiculo_activo.patente if conductor.vehiculo_activo else None,
        "posicion": None
        if posicion is None
        else {
            "lat": posicion.punto.y,
            "lon": posicion.punto.x,
            "precision_m": posicion.precision_m,
            "registrada_en": posicion.registrada_en.isoformat(),
        },
    }


def ultima_posicion(conductor: Conductor) -> PosicionGps | None:
    return PosicionGps.objects.filter(conductor=conductor).order_by("-registrada_en").first()


def conductores_del_mapa(empresa_id: int) -> list[dict]:
    """Foto inicial: los conductores en turno de la empresa con su última posición."""
    ultima = PosicionGps.objects.filter(conductor=OuterRef("pk")).order_by("-registrada_en")
    conductores = list(
        Conductor.objects.filter(usuario__empresa_id=empresa_id, estado__in=EN_TURNO, usuario__activo=True)
        .select_related("usuario", "vehiculo_activo")
        .annotate(ultima_id=Subquery(ultima.values("pk")[:1]))
        .order_by("usuario__nombre")
    )
    posiciones = PosicionGps.objects.in_bulk([c.ultima_id for c in conductores if c.ultima_id])
    return [datos_conductor(c, posiciones.get(c.ultima_id)) for c in conductores]


def _enviar(empresa_id: int, mensaje: dict) -> None:
    capa = get_channel_layer()
    if capa is not None:
        async_to_sync(capa.group_send)(grupo_mapa(empresa_id), mensaje)


def grupo_indicadores(empresa_id: int) -> str:
    return f"indicadores_empresa_{empresa_id}"


def avisar_indicadores(empresa_id: int) -> None:
    """HU-01: cambiaron reservas, turnos o vehículos. Con robust, un corte de Redis no daña la acción.

    Una posición solo pasa por aquí si el conductor recuperó la señal. Perderla no genera eventos: el panel
    lo nota en su revisión periódica.
    """

    def enviar():
        capa = get_channel_layer()
        if capa is not None:
            async_to_sync(capa.group_send)(grupo_indicadores(empresa_id), {"type": "indicadores.cambio"})

    transaction.on_commit(enviar, robust=True)


def notificar_conductor(conductor: Conductor) -> None:
    """Después del commit: estado, vehículo y última posición del conductor, o que salió del turno."""
    conductor = Conductor.objects.select_related("usuario", "vehiculo_activo").get(pk=conductor.pk)
    en_turno = conductor.estado in EN_TURNO and conductor.usuario.activo
    if en_turno:
        mensaje = {
            "type": "mapa.conductor",
            "conductor": datos_conductor(conductor, ultima_posicion(conductor)),
        }
    else:
        mensaje = {"type": "mapa.fuera", "id": conductor.pk}
    empresa_id = conductor.usuario.empresa_id
    transaction.on_commit(lambda: _enviar(empresa_id, mensaje))
