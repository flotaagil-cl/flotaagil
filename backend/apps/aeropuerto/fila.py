"""Fila virtual del aeropuerto (HU-29, RN-16): se propone al primero, por orden de ingreso a la geocerca.

- Entra quien está Disponible, con vehículo y sin viaje, al enviar una posición precisa dentro de la geocerca.
- Sale tras `tolerancia_fila_min` sin posiciones precisas dentro de la zona, al pasar a No disponible o al ser
  asignado. Sin señal también sale: no se puede confirmar que siga ahí (DC-21).
- Si después rechaza o no responde, vuelve al final con su siguiente posición dentro de la zona (DC-21).
"""

from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone

from apps.flota.models import EstadoConductor, PosicionGps

from .models import FilaAeropuerto, Geocerca, MotivoSalidaFila


def abiertas():
    return FilaAeropuerto.objects.filter(salida_en__isnull=True)


def _avisar_a_la_fila(geocerca_id: int, conductor_id: int) -> None:
    """Cada conductor de la fila vuelve a leer su lugar, y también quien entró o salió. Tras el commit."""
    from apps.reservas.asignacion import grupo_conductor

    capa = get_channel_layer()
    if capa is None:
        return
    avisados = set(abiertas().filter(geocerca_id=geocerca_id).values_list("conductor_id", flat=True))
    for destinatario in avisados | {conductor_id}:
        async_to_sync(capa.group_send)(grupo_conductor(destinatario), {"type": "conductor.fila"})


def _al_cambiar(geocerca_id: int, conductor_id: int) -> None:
    transaction.on_commit(lambda: _avisar_a_la_fila(geocerca_id, conductor_id))


def registrar_posiciones(conductor, posiciones: list[dict]) -> FilaAeropuerto | None:
    """Ingreso a la fila con el lote recibido. El orden lo da el instante de la primera posición dentro de la
    zona. Se llama con la fila del conductor bloqueada, así que no hay dos ingresos a la vez."""
    from apps.reservas.asignacion import EN_EJECUCION
    from apps.reservas.models import Viaje

    if conductor.estado != EstadoConductor.DISPONIBLE or conductor.vehiculo_activo_id is None:
        return None
    if abiertas().filter(conductor=conductor).exists():
        return None
    if Viaje.objects.filter(conductor=conductor, estado__in=EN_EJECUCION).exists():
        return None
    empresa = conductor.usuario.empresa
    configuracion = empresa.configuracion
    ahora = timezone.now()
    limite = ahora - timedelta(minutes=configuracion.tolerancia_fila_min)
    for posicion in sorted(posiciones, key=lambda p: p["registrada_en"]):
        precision = posicion.get("precision_m")
        if precision is None or precision > configuracion.precision_geocerca_m:
            continue
        if posicion["registrada_en"] < limite:
            continue  # un lote atrasado no da un lugar que ya habría perdido
        punto = Point(posicion["lon"], posicion["lat"], srid=4326)
        geocerca = Geocerca.objects.filter(empresa=empresa, poligono__covers=punto).first()
        if geocerca is None:
            continue
        entrada = FilaAeropuerto.objects.create(
            geocerca=geocerca, conductor=conductor, ingreso_en=min(posicion["registrada_en"], ahora)
        )
        _al_cambiar(geocerca.pk, conductor.pk)
        return entrada
    return None


def salir(conductor, motivo: str) -> bool:
    entradas = list(abiertas().filter(conductor=conductor))
    for entrada in entradas:
        entrada.salida_en = timezone.now()
        entrada.motivo_salida = motivo
        entrada.save(update_fields=["salida_en", "motivo_salida"])
        _al_cambiar(entrada.geocerca_id, conductor.pk)
    return bool(entradas)


def posiciones_en_fila(empresa_id: int) -> dict[int, int]:
    """Lugar en la fila (1, 2, …) de cada conductor de la empresa. RN-16: orden de ingreso."""
    entradas = (
        abiertas()
        .filter(geocerca__empresa_id=empresa_id)
        .order_by("geocerca_id", "ingreso_en", "id")
        .values_list("geocerca_id", "conductor_id")
    )
    lugares: dict[int, int] = {}
    por_geocerca: dict[int, int] = {}
    for geocerca_id, conductor_id in entradas:
        por_geocerca[geocerca_id] = por_geocerca.get(geocerca_id, 0) + 1
        lugares[conductor_id] = por_geocerca[geocerca_id]
    return lugares


def estado_de(conductor) -> dict | None:
    """Lo que ve el conductor en la app: su lugar, de cuántos y en qué zona."""
    entrada = abiertas().filter(conductor=conductor).select_related("geocerca").first()
    if entrada is None:
        return None
    return {
        "posicion": posiciones_en_fila(entrada.geocerca.empresa_id)[conductor.pk],
        "total": abiertas().filter(geocerca=entrada.geocerca).count(),
        "zona": entrada.geocerca.nombre,
        "ingreso_en": entrada.ingreso_en,
    }


def revisar(ahora=None) -> int:
    """Saca a quien ya no corresponde. Puede correr varias veces sin efectos duplicados. Devuelve cuántos."""
    ahora = ahora or timezone.now()
    salidas = 0
    entradas = abiertas().select_related("geocerca", "conductor__usuario__empresa__configuracion")
    for entrada in entradas:
        conductor = entrada.conductor
        if conductor.estado != EstadoConductor.DISPONIBLE:
            motivo = (
                MotivoSalidaFila.ASIGNADO
                if conductor.estado == EstadoConductor.EN_VIAJE
                else MotivoSalidaFila.NO_DISPONIBLE
            )
        else:
            configuracion = conductor.usuario.empresa.configuracion
            limite = ahora - timedelta(minutes=configuracion.tolerancia_fila_min)
            if entrada.ingreso_en >= limite:
                continue
            sigue_dentro = PosicionGps.objects.filter(
                conductor=conductor,
                registrada_en__gte=limite,
                precision_m__lte=configuracion.precision_geocerca_m,
                punto__coveredby=entrada.geocerca.poligono,
            ).exists()
            if sigue_dentro:
                continue
            motivo = MotivoSalidaFila.FUERA_ZONA
        with transaction.atomic():
            if salir(conductor, motivo):
                salidas += 1
    return salidas
