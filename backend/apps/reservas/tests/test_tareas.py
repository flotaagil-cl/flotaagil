"""chore/celery: envío en el worker, reintento exponencial, vuelos sin verificar y expiraciones por beat."""

from datetime import timedelta
from unittest.mock import Mock

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from kombu.exceptions import OperationalError as ErrorDeBroker

from apps.aeropuerto.models import Vuelo
from apps.integraciones.notificaciones import AVISO_EN_CAMINO
from apps.integraciones.vuelos import DatosVuelo, EstadoVuelo, VuelosNoDisponibles
from apps.reservas import tareas
from apps.reservas.models import (
    Actor,
    EstadoEntrega,
    EstadoViaje,
    HistorialEstado,
    MensajeWhatsapp,
)
from apps.reservas.tests.fabricas import ViajeFactory
from apps.reservas.tests.test_avisos import como, viaje_con
from apps.reservas.tests.test_whatsapp import TwilioFalso, http_error
from config.celery import app as celery_app

E = EstadoViaje


@pytest.fixture
def chofer(chofer_disponible):
    return chofer_disponible


def twilio_con(monkeypatch, *errores):
    falso = TwilioFalso(*errores)
    falso.intentos = 1  # como en producción: cada tarea hace un intento
    monkeypatch.setattr(tareas, "obtener_notificador", lambda: falso)
    return falso


def espiar_reintentos(monkeypatch, tarea):
    esperas = []
    original = tarea.retry

    def retry(*args, countdown=None, **kwargs):
        esperas.append(countdown)
        return original(*args, countdown=countdown, **kwargs)

    monkeypatch.setattr(tarea, "retry", retry)
    return esperas


@pytest.mark.django_db
class TestEnvio:
    def test_reintenta_con_espera_exponencial_y_se_recupera(self, monkeypatch, chofer, pasajero):
        viaje = viaje_con(chofer, pasajero, E.EN_CAMINO)
        twilio = twilio_con(monkeypatch, http_error(503), http_error(503), http_error(429))
        esperas = espiar_reintentos(monkeypatch, tareas.enviar_aviso)
        tareas.enviar_aviso.delay(viaje.pk, AVISO_EN_CAMINO)
        assert esperas == [2, 4, 8]
        assert len(twilio.enviados) == 4
        mensaje = MensajeWhatsapp.objects.get(viaje=viaje)
        assert mensaje.estado_entrega == EstadoEntrega.QUEUED

    def test_agotados_los_reintentos_queda_en_failed(self, monkeypatch, chofer, pasajero):
        viaje = viaje_con(chofer, pasajero, E.EN_CAMINO)
        twilio = twilio_con(monkeypatch, *[http_error(503) for _ in range(6)])
        esperas = espiar_reintentos(monkeypatch, tareas.enviar_aviso)
        tareas.enviar_aviso.delay(viaje.pk, AVISO_EN_CAMINO)
        assert esperas == [2, 4, 8, 16, 32]
        assert len(twilio.enviados) == 6
        assert MensajeWhatsapp.objects.get(viaje=viaje).estado_entrega == EstadoEntrega.FAILED

    def test_error_definitivo_no_reintenta(self, monkeypatch, chofer, pasajero):
        viaje = viaje_con(chofer, pasajero, E.EN_CAMINO)
        twilio = twilio_con(monkeypatch, http_error(400))
        tareas.enviar_aviso.delay(viaje.pk, AVISO_EN_CAMINO)
        assert len(twilio.enviados) == 1
        assert MensajeWhatsapp.objects.get(viaje=viaje).estado_entrega == EstadoEntrega.FAILED

    def test_verificacion_y_respuesta_tambien_reintentan(self, monkeypatch, pasajero):
        viaje = ViajeFactory(empresa=pasajero.empresa, pasajero=pasajero, estado=E.PENDIENTE_CONFIRMACION)
        twilio = twilio_con(monkeypatch, http_error(503), http_error(503))
        vence = (timezone.now() + timedelta(minutes=15)).isoformat()
        tareas.enviar_verificacion.delay(viaje.pk, vence)
        assert len(twilio.enviados) == 3  # dos fallas y el envío
        tareas.enviar_respuesta.delay(pasajero.pk, viaje.pk, "Listo")
        tareas.enviar_respuesta.delay(pasajero.pk, None, "Sin viaje")
        assert twilio.enviados[-1]["Body"] == "Sin viaje"

    def test_viaje_borrado_no_envia(self, monkeypatch):
        twilio = twilio_con(monkeypatch)
        tareas.enviar_aviso.delay(999999, AVISO_EN_CAMINO)
        tareas.enviar_verificacion.delay(999999, timezone.now().isoformat())
        tareas.enviar_respuesta.delay(999999, None, "x")
        assert twilio.enviados == []

    def test_la_respuesta_al_conductor_no_llama_a_twilio(
        self, monkeypatch, chofer, pasajero, django_capture_on_commit_callbacks
    ):
        """La acción solo encola: Twilio queda fuera de la petición."""
        viaje = viaje_con(chofer, pasajero, E.ACEPTADO)
        twilio = twilio_con(monkeypatch)
        delay = Mock()
        monkeypatch.setattr(tareas.enviar_aviso, "delay", delay)
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = como(chofer.usuario).post(reverse("app-en-camino", args=[viaje.pk]))
        assert respuesta.status_code == 200
        delay.assert_called_once_with(viaje.pk, AVISO_EN_CAMINO)
        assert twilio.enviados == []

    def test_sin_broker_la_accion_no_se_rompe(
        self, monkeypatch, chofer, pasajero, caplog, django_capture_on_commit_callbacks
    ):
        viaje = viaje_con(chofer, pasajero, E.ACEPTADO)
        monkeypatch.setattr(tareas.enviar_aviso, "delay", Mock(side_effect=ErrorDeBroker("sin redis")))
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = como(chofer.usuario).post(reverse("app-en-camino", args=[viaje.pk]))
        assert respuesta.status_code == 200
        assert "No se pudo encolar" in caplog.text

    def test_transaccion_revertida_no_encola(
        self, monkeypatch, chofer, pasajero, django_capture_on_commit_callbacks
    ):
        viaje = viaje_con(chofer, pasajero, E.EN_ZONA)
        delay = Mock()
        monkeypatch.setattr(tareas.enviar_aviso, "delay", delay)
        with django_capture_on_commit_callbacks(execute=True):
            assert como(chofer.usuario).post(reverse("app-en-camino", args=[viaje.pk])).status_code == 409
        delay.assert_not_called()


class ConsultorFalso:
    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.consultas = 0

    def consultar(self, numero, hora):
        self.consultas += 1
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


@pytest.mark.django_db
class TestVueloSinVerificar:
    @pytest.fixture
    def vuelo(self, empresa):
        viaje = ViajeFactory(empresa=empresa, estado=E.SOLICITADO)
        return Vuelo.objects.create(
            viaje=viaje,
            numero="LA123",
            fecha=timezone.localdate(viaje.recogida_en),
            hora_programada=viaje.recogida_en,
        )

    def usar(self, monkeypatch, *respuestas):
        consultor = ConsultorFalso(*respuestas)
        monkeypatch.setattr(tareas, "obtener_consultor_vuelos", lambda: consultor)
        return consultor

    def test_reintenta_y_guarda_los_datos(self, monkeypatch, vuelo):
        hora = vuelo.hora_programada + timedelta(minutes=10)
        datos = DatosVuelo("LA123", hora, hora, EstadoVuelo.DEMORADO)
        consultor = self.usar(monkeypatch, VuelosNoDisponibles("x"), VuelosNoDisponibles("x"), datos)
        esperas = espiar_reintentos(monkeypatch, tareas.consultar_vuelo)
        tareas.consultar_vuelo.delay(vuelo.pk)
        assert esperas == [30, 60]
        assert consultor.consultas == 3
        vuelo.refresh_from_db()
        assert (vuelo.hora_programada, vuelo.estado_vuelo) == (hora, EstadoVuelo.DEMORADO)
        assert vuelo.ultima_consulta_en is not None

    def test_agotados_los_reintentos_sigue_sin_verificar(self, monkeypatch, vuelo, caplog):
        self.usar(monkeypatch, *[VuelosNoDisponibles("x") for _ in range(7)])
        esperas = espiar_reintentos(monkeypatch, tareas.consultar_vuelo)
        tareas.consultar_vuelo.delay(vuelo.pk)
        assert esperas == [30, 60, 120, 240, 480, 960]
        vuelo.refresh_from_db()
        assert vuelo.ultima_consulta_en is None
        assert "sigue sin verificar" in caplog.text

    def test_ya_verificado_no_consulta(self, monkeypatch, vuelo):
        consultor = self.usar(monkeypatch)
        Vuelo.objects.filter(pk=vuelo.pk).update(ultima_consulta_en=timezone.now())
        tareas.consultar_vuelo.delay(vuelo.pk)
        assert consultor.consultas == 0

    def test_no_aparece_en_la_api(self, monkeypatch, vuelo, caplog):
        self.usar(monkeypatch, None)
        tareas.consultar_vuelo.delay(vuelo.pk)
        vuelo.refresh_from_db()
        assert vuelo.ultima_consulta_en is None
        assert "no aparece" in caplog.text


@pytest.mark.django_db
class TestPeriodicas:
    def test_rn06_expira_la_solicitud_vencida(self, empresa):
        viaje = ViajeFactory(empresa=empresa, estado=E.PENDIENTE_CONFIRMACION)
        type(viaje).objects.filter(pk=viaje.pk).update(creado_en=timezone.now() - timedelta(minutes=16))
        HistorialEstado.objects.create(viaje=viaje, estado_nuevo=viaje.estado, actor=Actor.PASAJERO)
        assert tareas.expirar_solicitudes.delay().get() == 1
        viaje.refresh_from_db()
        assert viaje.estado == E.CANCELADO
        assert tareas.expirar_solicitudes.delay().get() == 0

    def test_rn04_tarea_de_asignaciones(self):
        assert tareas.expirar_asignaciones.delay().get() == 0


def test_las_pruebas_no_pueden_llegar_al_broker_real():
    """Una vez corrieron contra el worker de desarrollo y dejaron datos en su base."""
    assert celery_app.conf.task_always_eager is True
    assert celery_app.conf.broker_url == "memory://"
    assert tareas.enviar_aviso.app.conf.task_always_eager is True


def test_beat_programa_las_expiraciones():
    programa = {t["task"]: t["schedule"] for t in settings.CELERY_BEAT_SCHEDULE.values()}
    assert programa["apps.reservas.tareas.expirar_solicitudes"] == timedelta(seconds=60)
    assert programa["apps.reservas.tareas.expirar_asignaciones"] == timedelta(seconds=5)
    assert settings.CELERY_TIMEZONE == "America/Santiago"
