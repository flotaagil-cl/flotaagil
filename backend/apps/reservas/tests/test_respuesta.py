"""HU-15 · Aceptar o rechazar el viaje en 60 s (RN-04): resultado en ASIGNACION y reserva que vuelve a
SOLICITADO."""

from datetime import timedelta

import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.flota.models import ConductorVehiculo, EstadoConductor
from apps.reservas import asignacion as servicio
from apps.reservas.models import Actor, Asignacion, EstadoViaje, HistorialEstado, ResultadoAsignacion
from apps.reservas.tests.fabricas import ConductorFactory, VehiculoFactory, ViajeFactory
from config.asgi import application


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


@pytest.fixture
def asignada(empresa, despachador):
    conductor = disponible(empresa)
    viaje = ViajeFactory(empresa=empresa, estado=EstadoViaje.SOLICITADO)
    return servicio.asignar(viaje, conductor.pk, usuario=despachador)


def app(conductor):
    cliente = APIClient()
    cliente.force_authenticate(conductor.usuario)
    return cliente


def url(asignacion, accion):
    return reverse(f"app-{accion}", args=[asignacion.pk])


def ultimo_cambio(viaje):
    return HistorialEstado.objects.filter(viaje=viaje).order_by("-id").first()


@pytest.mark.django_db
class TestResponder:
    def test_aceptar(self, asignada):
        respuesta = app(asignada.conductor).post(url(asignada, "aceptar"))
        assert respuesta.status_code == 200
        assert respuesta.json() == {
            "asignacion": asignada.pk,
            "viaje": asignada.viaje_id,
            "resultado": "ACEPTADA",
            "estado_viaje": "ACEPTADO",
        }
        asignada.refresh_from_db()
        assert asignada.respondida_en is not None
        asignada.conductor.refresh_from_db()
        assert asignada.conductor.estado == EstadoConductor.EN_VIAJE
        cambio = ultimo_cambio(asignada.viaje)
        assert (cambio.estado_nuevo, cambio.actor) == (EstadoViaje.ACEPTADO, Actor.CONDUCTOR)

    def test_rechazar_vuelve_a_solicitado_sin_conductor(self, asignada):
        respuesta = app(asignada.conductor).post(url(asignada, "rechazar"))
        assert respuesta.json()["resultado"] == "RECHAZADA"
        viaje = asignada.viaje
        viaje.refresh_from_db()
        assert (viaje.estado, viaje.conductor_id, viaje.vehiculo_id) == (EstadoViaje.SOLICITADO, None, None)
        asignada.conductor.refresh_from_db()
        assert asignada.conductor.estado == EstadoConductor.DISPONIBLE
        assert ultimo_cambio(viaje).actor == Actor.CONDUCTOR

    def test_despues_de_60_s_no_se_puede(self, asignada):
        Asignacion.objects.filter(pk=asignada.pk).update(enviada_en=timezone.now() - timedelta(seconds=61))
        respuesta = app(asignada.conductor).post(url(asignada, "aceptar"))
        assert (respuesta.status_code, respuesta.json()["code"]) == (409, "asignacion_no_permitida")
        assert "60 s" in respuesta.json()["detail"]

    def test_responder_dos_veces(self, asignada):
        cliente = app(asignada.conductor)
        cliente.post(url(asignada, "rechazar"))
        assert cliente.post(url(asignada, "aceptar")).status_code == 409

    def test_solo_el_conductor_asignado(self, asignada, empresa):
        otro = disponible(empresa)
        assert app(otro).post(url(asignada, "aceptar")).status_code == 400
        asignada.refresh_from_db()
        assert asignada.resultado is None

    def test_reasignar_tras_rechazo(self, asignada, empresa, despachador):
        app(asignada.conductor).post(url(asignada, "rechazar"))
        otro = disponible(empresa)
        segunda = servicio.asignar(asignada.viaje, otro.pk, usuario=despachador)
        assert Asignacion.objects.filter(viaje=asignada.viaje).count() == 2
        assert segunda.resultado is None


@pytest.mark.django_db
class TestExpiracion:
    def test_sin_respuesta_en_60_s_expira(self, asignada):
        assert servicio.expirar_asignaciones(timezone.now() + timedelta(seconds=59)) == 0
        assert servicio.expirar_asignaciones(timezone.now() + timedelta(seconds=61)) == 1
        asignada.refresh_from_db()
        assert (asignada.resultado, asignada.respondida_en) == (ResultadoAsignacion.EXPIRADA, None)
        viaje = asignada.viaje
        viaje.refresh_from_db()
        assert (viaje.estado, viaje.conductor_id) == (EstadoViaje.SOLICITADO, None)
        assert ultimo_cambio(viaje).actor == Actor.SISTEMA
        # Idempotente: otra pasada no hace nada.
        assert servicio.expirar_asignaciones(timezone.now() + timedelta(seconds=120)) == 0

    def test_la_respondida_no_expira(self, asignada):
        app(asignada.conductor).post(url(asignada, "aceptar"))
        assert servicio.expirar_asignaciones(timezone.now() + timedelta(seconds=120)) == 0
        asignada.viaje.refresh_from_db()
        assert asignada.viaje.estado == EstadoViaje.ACEPTADO

    def test_comando(self, asignada, capsys):
        Asignacion.objects.filter(pk=asignada.pk).update(enviada_en=timezone.now() - timedelta(seconds=61))
        call_command("expirar_asignaciones")
        assert "Asignaciones expiradas: 1" in capsys.readouterr().out


@pytest.mark.django_db(transaction=True)
def test_la_app_cierra_el_aviso_al_rechazar(empresa, despachador):
    conductor = disponible(empresa)
    viaje = ViajeFactory(empresa=empresa, estado=EstadoViaje.SOLICITADO)
    token = str(AccessToken.for_user(conductor.usuario))

    @database_sync_to_async
    def asignar_y_rechazar():
        asignacion = servicio.asignar(viaje, conductor.pk, usuario=despachador)
        servicio.responder(asignacion.pk, usuario=conductor.usuario, aceptar=False)
        return asignacion.pk

    async def prueba():
        com = WebsocketCommunicator(application, "/ws/conductor/", subprotocols=["flotaagil", token])
        await com.connect()
        id_asignacion = await asignar_y_rechazar()
        primero = await com.receive_json_from(timeout=2)
        segundo = await com.receive_json_from(timeout=2)
        await com.disconnect()
        return id_asignacion, primero, segundo

    id_asignacion, primero, segundo = async_to_sync(prueba)()
    assert primero["tipo"] == "asignado"
    assert segundo == {"tipo": "sin_asignacion", "asignacion": id_asignacion}
