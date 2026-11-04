"""HU-24 · Calificación del servicio por WhatsApp (RN-14)."""

from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from apps.integraciones.notificaciones import AVISO_ENCUESTA, texto_aviso
from apps.reservas import verificacion
from apps.reservas.models import (
    Calificacion,
    DireccionMensaje,
    EstadoViaje,
    HistorialEstado,
    MensajeWhatsapp,
    PagoViaje,
    TipoMensaje,
)
from apps.reservas.tests.fabricas import ViajeFactory
from apps.reservas.tests.test_avisos import como, viaje_con
from apps.reservas.tests.test_whatsapp import TwilioFalso, entrante, http_error

E = EstadoViaje


@pytest.fixture
def twilio(twilio_avisos):
    return twilio_avisos


@pytest.fixture
def chofer(chofer_disponible):
    return chofer_disponible


def finalizado(chofer, pasajero, hace_horas=1):
    viaje = viaje_con(chofer, pasajero, E.FINALIZADO)
    fin = HistorialEstado.objects.get(viaje=viaje)
    HistorialEstado.objects.filter(pk=fin.pk).update(creado_en=timezone.now() - timedelta(hours=hace_horas))
    return viaje


def responder(viaje, texto="5", sid="SMencuesta0001", **extra):
    return verificacion.procesar_entrante(entrante(viaje, sid=sid, payload="", Body=texto, **extra))


@pytest.mark.django_db
class TestEncuesta:
    def finalizar(self, chofer, viaje):
        return como(chofer.usuario).post(
            reverse("app-finalizar", args=[viaje.pk]), {"metodo": "EFECTIVO", "monto": 1000}, format="json"
        )

    def test_se_envia_al_finalizar(self, twilio, chofer, pasajero, django_capture_on_commit_callbacks):
        viaje = viaje_con(chofer, pasajero, E.PASAJERO_A_BORDO)
        with django_capture_on_commit_callbacks(execute=True):
            assert self.finalizar(chofer, viaje).status_code == 200
        assert len(twilio.enviados) == 1
        cuerpo = twilio.enviados[0]["Body"]
        assert "del 1 al 5" in cuerpo
        assert "Es opcional" in cuerpo
        assert "Muriel Moreno" in cuerpo

    def test_si_falla_el_viaje_igual_se_cierra(
        self, monkeypatch, chofer, pasajero, django_capture_on_commit_callbacks
    ):
        """RN-14."""
        falso = TwilioFalso(*[http_error(503) for _ in range(6)])
        falso.intentos = 1
        monkeypatch.setattr("apps.reservas.tareas.obtener_notificador", lambda: falso)
        viaje = viaje_con(chofer, pasajero, E.PASAJERO_A_BORDO)
        with django_capture_on_commit_callbacks(execute=True):
            assert self.finalizar(chofer, viaje).status_code == 200
        viaje.refresh_from_db()
        assert viaje.estado == E.FINALIZADO
        assert PagoViaje.objects.filter(viaje=viaje).exists()
        assert not Calificacion.objects.filter(viaje=viaje).exists()

    def test_no_se_envia_si_no_se_pudo_finalizar(
        self, twilio, chofer, pasajero, django_capture_on_commit_callbacks
    ):
        viaje = viaje_con(chofer, pasajero, E.EN_ZONA)
        with django_capture_on_commit_callbacks(execute=True):
            assert self.finalizar(chofer, viaje).status_code == 409
        assert twilio.enviados == []

    def test_texto(self, chofer, pasajero):
        cuerpo, variables = texto_aviso(viaje_con(chofer, pasajero, E.FINALIZADO), AVISO_ENCUESTA)
        assert all(valor in cuerpo for valor in variables.values())


@pytest.mark.django_db
class TestRespuesta:
    @pytest.mark.parametrize("puntaje", [1, 2, 3, 4, 5])
    def test_registra_el_puntaje_asociado_al_conductor(self, twilio, chofer, pasajero, puntaje):
        viaje = finalizado(chofer, pasajero)
        assert responder(viaje, f" {puntaje} ") == "calificada"
        calificacion = Calificacion.objects.get(viaje=viaje)
        assert calificacion.puntaje == puntaje
        assert calificacion.viaje.conductor == chofer
        assert "Gracias" in twilio.enviados[-1]["Body"]
        assert MensajeWhatsapp.objects.get(viaje=viaje, direccion=DireccionMensaje.ENTRANTE).cuerpo.strip()

    @pytest.mark.parametrize("texto", ["0", "6", "45", "5 minutos", "gracias", ""])
    def test_otra_respuesta_no_califica(self, twilio, chofer, pasajero, texto):
        viaje = finalizado(chofer, pasajero)
        assert responder(viaje, texto) == "sin_accion"
        assert not Calificacion.objects.exists()

    def test_vale_la_primera_respuesta(self, twilio, chofer, pasajero):
        viaje = finalizado(chofer, pasajero)
        mensaje = MensajeWhatsapp.objects.create(
            pasajero=pasajero,
            viaje=viaje,
            direccion=DireccionMensaje.SALIENTE,
            tipo=TipoMensaje.SESION,
            cuerpo="encuesta",
            proveedor_sid="SMencuesta",
        )
        assert responder(viaje, "5", original=mensaje.proveedor_sid) == "calificada"
        assert responder(viaje, "1", sid="SMotra", original=mensaje.proveedor_sid) == "ya_calificada"
        assert Calificacion.objects.get(viaje=viaje).puntaje == 5

    def test_mismo_webhook_dos_veces(self, twilio, chofer, pasajero):
        viaje = finalizado(chofer, pasajero)
        assert responder(viaje) == "calificada"
        assert responder(viaje) == "repetido"
        assert Calificacion.objects.count() == 1

    def test_fuera_de_plazo_es_conversacion(self, twilio, chofer, pasajero):
        """DC-19: un «5» dos días después no es una calificación."""
        viaje = finalizado(chofer, pasajero, hace_horas=25)
        assert responder(viaje) == "sin_accion"
        assert not Calificacion.objects.exists()

    def test_el_plazo_es_configurable_por_empresa(self, twilio, chofer, pasajero):
        configuracion = pasajero.empresa.configuracion
        configuracion.encuesta_vigencia_horas = 48
        configuracion.save()
        viaje = finalizado(chofer, pasajero, hace_horas=25)
        assert responder(viaje) == "calificada"
        assert Calificacion.objects.filter(viaje=viaje).exists()

    def test_sin_cita_va_al_ultimo_viaje_sin_calificar(self, twilio, chofer, pasajero):
        anterior = finalizado(chofer, pasajero, hace_horas=3)
        ultimo = finalizado(chofer, pasajero, hace_horas=1)
        assert responder(ultimo, "4") == "calificada"
        assert Calificacion.objects.get().viaje == ultimo
        assert responder(anterior, "2", sid="SMotra") == "calificada"
        assert Calificacion.objects.get(viaje=anterior).puntaje == 2

    def test_citando_un_viaje_viejo_no_cae_en_otro(self, twilio, chofer, pasajero):
        viejo = finalizado(chofer, pasajero, hace_horas=30)
        reciente = finalizado(chofer, pasajero, hace_horas=1)
        MensajeWhatsapp.objects.create(
            pasajero=pasajero,
            viaje=viejo,
            direccion=DireccionMensaje.SALIENTE,
            tipo=TipoMensaje.SESION,
            cuerpo="encuesta",
            proveedor_sid="SMviejo",
        )
        assert responder(reciente, "3", original="SMviejo") == "sin_accion"
        assert not Calificacion.objects.exists()

    def test_viaje_en_curso_no_se_califica(self, twilio, chofer, pasajero):
        viaje = viaje_con(chofer, pasajero, E.EN_CAMINO)
        assert responder(viaje) == "sin_accion"
        assert not Calificacion.objects.exists()

    def test_numero_no_cancela_ni_confirma_una_pendiente(self, twilio, pasajero):
        viaje = ViajeFactory(empresa=pasajero.empresa, pasajero=pasajero, estado=E.PENDIENTE_CONFIRMACION)
        assert responder(viaje) == "sin_accion"
        viaje.refresh_from_db()
        assert viaje.estado == E.PENDIENTE_CONFIRMACION

    def test_no_toca_el_estado_del_viaje(self, twilio, chofer, pasajero):
        viaje = finalizado(chofer, pasajero)
        antes = HistorialEstado.objects.filter(viaje=viaje).count()
        responder(viaje)
        viaje.refresh_from_db()
        assert viaje.estado == E.FINALIZADO
        assert HistorialEstado.objects.filter(viaje=viaje).count() == antes


@pytest.mark.django_db
class TestModeloYApi:
    def test_el_puntaje_fuera_de_rango_no_entra(self, chofer, pasajero):
        viaje = finalizado(chofer, pasajero)
        for puntaje in (0, 6):
            with pytest.raises(IntegrityError), transaction.atomic():
                Calificacion.objects.create(viaje=viaje, puntaje=puntaje)

    def test_ficha_del_panel(self, despachador, chofer, pasajero):
        viaje = finalizado(chofer, pasajero)
        ruta = reverse("viaje-detail", args=[viaje.pk])
        assert como(despachador).get(ruta).data["calificacion"] is None
        Calificacion.objects.create(viaje=viaje, puntaje=4)
        assert como(despachador).get(ruta).data["calificacion"] == 4
