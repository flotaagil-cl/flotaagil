"""CP-14: asignación con dos peticiones simultáneas reales, y orden de bloqueo (viaje, luego conductor).

Patrón de `cuentas/tests/test_concurrencia.py`: una transacción «llave» toma la fila que las dos peticiones
necesitan; se lanzan las dos peticiones HTTP reales en hilos y se confirma con pg_stat_activity que **las
dos**
están esperando el mismo bloqueo, es decir, que de verdad llegaron a la vez. Al soltar la llave, una gana y la
otra debe ver el estado nuevo: exactamente una 200 y una 409, y una sola ASIGNACION.

Corre contra PostgreSQL (compose y CI); el bloqueo de fila y pg_stat_activity no existen en SQLite.
"""

import threading
import time

import pytest
from django.db import DatabaseError, connection, connections, transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.flota.models import Conductor, ConductorVehiculo, EstadoConductor
from apps.reservas.models import Actor, Asignacion, EstadoViaje, HistorialEstado, Viaje
from apps.reservas.tests.fabricas import ConductorFactory, VehiculoFactory, ViajeFactory

from .test_ejecucion import CERCA, ORIGEN, posicion

TOPE_SEGUNDOS = 10
E = EstadoViaje


def esperar(condicion) -> bool:
    limite = time.monotonic() + TOPE_SEGUNDOS
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.01)
    return False


def sesiones_esperando_un_bloqueo() -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_stat_activity "
            "WHERE datname = current_database() AND wait_event_type = 'Lock' AND pid <> pg_backend_pid()"
        )
        return cursor.fetchone()[0]


def disponible(empresa):
    vehiculo = VehiculoFactory(empresa=empresa)
    conductor = ConductorFactory(
        usuario__empresa=empresa,
        estado=EstadoConductor.DISPONIBLE,
        vehiculo_activo=vehiculo,
        consentimiento_gps_en=timezone.now(),
    )
    ConductorVehiculo.objects.create(conductor=conductor, vehiculo=vehiculo)
    return conductor


def solicitado(empresa):
    viaje = ViajeFactory(empresa=empresa, estado=E.SOLICITADO)
    HistorialEstado.objects.create(viaje=viaje, estado_nuevo=E.SOLICITADO, actor=Actor.DESPACHADOR)
    return viaje


def asignar(usuario, viaje_id, conductor_id):
    cliente = APIClient()
    cliente.force_authenticate(usuario)
    return cliente.post(reverse("viaje-asignar", args=[viaje_id]), {"conductor": conductor_id}, format="json")


def en_paralelo(llave, peticiones):
    """`llave` bloquea una fila hasta que el evento se active. Lanza las peticiones, exige que todas esperen
    ese bloqueo a la vez y luego suelta la llave. Devuelve las respuestas en el orden dado."""
    tiene_la_fila = threading.Event()
    soltar = threading.Event()
    respuestas = [None] * len(peticiones)

    def sostener():
        try:
            with transaction.atomic():
                llave()
                tiene_la_fila.set()
                soltar.wait(TOPE_SEGUNDOS)
        finally:
            connections.close_all()

    def correr(i, peticion):
        try:
            respuestas[i] = peticion()
        finally:
            connections.close_all()

    hilo_llave = threading.Thread(target=sostener)
    hilo_llave.start()
    assert tiene_la_fila.wait(TOPE_SEGUNDOS)
    hilos = [threading.Thread(target=correr, args=(i, p)) for i, p in enumerate(peticiones)]
    for hilo in hilos:
        hilo.start()
    try:
        todas_esperaron = esperar(lambda: sesiones_esperando_un_bloqueo() >= len(peticiones))
    finally:
        soltar.set()
        hilo_llave.join(TOPE_SEGUNDOS)
        for hilo in hilos:
            hilo.join(TOPE_SEGUNDOS)
    assert todas_esperaron, (
        f"Las peticiones no llegaron a la vez: {[r and r.status_code for r in respuestas]}"
    )
    return respuestas


@pytest.mark.django_db(transaction=True)
class TestCP14:
    def test_misma_reserva_a_dos_conductores(self, empresa, despachador):
        assert connection.vendor == "postgresql", "Esta prueba debe correr contra PostgreSQL, nunca SQLite."
        viaje = solicitado(empresa)
        uno, dos = disponible(empresa), disponible(empresa)
        respuestas = en_paralelo(
            lambda: Viaje.objects.select_for_update().get(pk=viaje.pk),
            [lambda: asignar(despachador, viaje.pk, uno.pk), lambda: asignar(despachador, viaje.pk, dos.pk)],
        )
        assert sorted(r.status_code for r in respuestas) == [200, 409]
        assert Asignacion.objects.filter(viaje=viaje).count() == 1
        viaje.refresh_from_db()
        ganador = next(c for c, r in zip((uno, dos), respuestas, strict=True) if r.status_code == 200)
        assert (viaje.estado, viaje.conductor_id) == (E.ASIGNADO, ganador.pk)

    def test_mismo_conductor_a_dos_reservas(self, empresa, despachador):
        assert connection.vendor == "postgresql", "Esta prueba debe correr contra PostgreSQL, nunca SQLite."
        primera, segunda = solicitado(empresa), solicitado(empresa)
        conductor = disponible(empresa)
        respuestas = en_paralelo(
            lambda: Conductor.objects.select_for_update().get(pk=conductor.pk),
            [
                lambda: asignar(despachador, primera.pk, conductor.pk),
                lambda: asignar(despachador, segunda.pk, conductor.pk),
            ],
        )
        assert sorted(r.status_code for r in respuestas) == [200, 409]
        perdedora = next(r for r in respuestas if r.status_code == 409)
        assert "RN-03" in perdedora.data["detail"]
        assert Asignacion.objects.filter(conductor=conductor).count() == 1
        estados = sorted(
            Viaje.objects.filter(pk__in=[primera.pk, segunda.pk]).values_list("estado", flat=True)
        )
        assert estados == [E.ASIGNADO, E.SOLICITADO]


@pytest.mark.django_db(transaction=True)
def test_la_geocerca_no_bloquea_el_viaje_con_el_conductor_tomado(empresa):
    """Regresión del orden de bloqueo (viaje y luego conductor). Al recibir posiciones, la fila del conductor
    no queda tomada mientras la petición espera el viaje: ni por la FK de POSICION_GPS (KEY SHARE sobre el
    viaje) ni por EN_ZONA (FOR UPDATE del viaje). Antes, el lote tomaba la fila del conductor con FOR UPDATE y
    podía bloquearse mutuamente con una cancelación o un cierre forzado, que toman el viaje y luego el
    conductor."""
    assert connection.vendor == "postgresql", "Esta prueba debe correr contra PostgreSQL, nunca SQLite."
    chofer = disponible(empresa)
    Conductor.objects.filter(pk=chofer.pk).update(estado=EstadoConductor.EN_VIAJE)
    viaje = ViajeFactory(
        empresa=empresa,
        conductor=chofer,
        vehiculo=chofer.vehiculo_activo,
        estado=E.EN_CAMINO,
        origen_geo=ORIGEN,
    )
    HistorialEstado.objects.create(viaje=viaje, estado_nuevo=E.EN_CAMINO, actor=Actor.CONDUCTOR)
    cliente = APIClient()
    cliente.force_authenticate(chofer.usuario)
    conductor_libre = {}

    def enviar():
        respuesta = cliente.post(reverse("app-posiciones"), {"posiciones": [posicion(CERCA)]}, format="json")
        return respuesta

    def probar_conductor():
        # Con la petición esperando el viaje, se tiene que poder actualizar el conductor, como lo hace una
        # cancelación (UPDATE = FOR NO KEY UPDATE; no choca con el KEY SHARE de la FK de las posiciones).
        try:
            with transaction.atomic():
                Conductor.objects.select_for_update(no_key=True, nowait=True).get(pk=chofer.pk)
            conductor_libre["ok"] = True
        except DatabaseError:
            conductor_libre["ok"] = False
        finally:
            connections.close_all()

    tiene_el_viaje = threading.Event()
    soltar = threading.Event()
    resultado = {}

    def sostener_viaje():
        try:
            with transaction.atomic():
                Viaje.objects.select_for_update().get(pk=viaje.pk)
                tiene_el_viaje.set()
                soltar.wait(TOPE_SEGUNDOS)
        finally:
            connections.close_all()

    def peticion():
        try:
            resultado["r"] = enviar()
        finally:
            connections.close_all()

    llave = threading.Thread(target=sostener_viaje)
    llave.start()
    assert tiene_el_viaje.wait(TOPE_SEGUNDOS)
    hilo = threading.Thread(target=peticion)
    hilo.start()
    try:
        assert esperar(lambda: sesiones_esperando_un_bloqueo() >= 1)
        sonda = threading.Thread(target=probar_conductor)
        sonda.start()
        sonda.join(TOPE_SEGUNDOS)
    finally:
        soltar.set()
        llave.join(TOPE_SEGUNDOS)
        hilo.join(TOPE_SEGUNDOS)
    assert conductor_libre == {"ok": True}
    assert resultado["r"].status_code == 201
    viaje.refresh_from_db()
    assert viaje.estado == E.EN_ZONA
