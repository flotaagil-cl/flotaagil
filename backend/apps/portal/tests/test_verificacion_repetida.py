"""DC-31: un teléfono verificado hace poco no se vuelve a verificar (P1.1 del informe).

Si el pasajero de ese número en la empresa confirmó por WhatsApp dentro de `vigencia_verificacion_dias`
(90 por defecto), la solicitud del portal queda SOLICITADO y se envía el aviso de confirmación (HU-21) en vez
de la plantilla de verificación. El límite de 3 solicitudes cada 15 min sigue igual.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.reservas import tareas
from apps.reservas.models import Actor, EstadoViaje, HistorialEstado, Viaje
from apps.reservas.tests.fabricas import PasajeroFactory
from apps.reservas.tests.test_whatsapp import TwilioFalso

from .test_portal import solicitud, url

TELEFONO = "+56900009101"  # el de `solicitud()`, normalizado


@pytest.fixture
def twilio(monkeypatch):
    falso = TwilioFalso()
    monkeypatch.setattr(tareas, "obtener_notificador", lambda: falso)
    return falso


def pedir(cliente, empresa, captura, **cambios):
    with captura(execute=True):
        return cliente.post(url(empresa), solicitud(**cambios), format="json")


def verificado_hace(empresa, dias: float, telefono: str = TELEFONO):
    return PasajeroFactory(
        empresa=empresa, telefono=telefono, verificado_en=timezone.now() - timedelta(days=dias)
    )


@pytest.mark.django_db
class TestVerificacionRepetida:
    def test_verificado_hace_poco_queda_solicitado_y_recibe_la_confirmacion(
        self, cliente, empresa, twilio, django_capture_on_commit_callbacks
    ):
        verificado_hace(empresa, 10)
        respuesta = pedir(cliente, empresa, django_capture_on_commit_callbacks)
        assert respuesta.status_code == 201, respuesta.data
        assert respuesta.data["estado"] == EstadoViaje.SOLICITADO
        assert respuesta.data["expira_en"] is None
        assert "quedó registrada" in respuesta.data["mensaje"]
        viaje = Viaje.objects.get()
        assert viaje.estado == EstadoViaje.SOLICITADO
        historial = HistorialEstado.objects.get(viaje=viaje)
        assert (historial.estado_anterior, historial.estado_nuevo, historial.actor) == (
            None,
            EstadoViaje.SOLICITADO,
            Actor.PASAJERO,
        )
        assert len(twilio.enviados) == 1
        assert "confirmó tu viaje" in twilio.enviados[0]["Body"]

    def test_verificacion_vencida_pide_verificar_otra_vez(
        self, cliente, empresa, twilio, django_capture_on_commit_callbacks
    ):
        verificado_hace(empresa, 91)
        respuesta = pedir(cliente, empresa, django_capture_on_commit_callbacks)
        assert respuesta.data["estado"] == EstadoViaje.PENDIENTE_CONFIRMACION
        assert respuesta.data["expira_en"] is not None
        assert "confirmó tu viaje" not in twilio.enviados[0].get("Body", "")

    def test_el_limite_es_configurable_por_empresa(
        self, cliente, empresa, twilio, django_capture_on_commit_callbacks
    ):
        empresa.configuracion.vigencia_verificacion_dias = 5
        empresa.configuracion.save()
        verificado_hace(empresa, 6)
        assert pedir(cliente, empresa, django_capture_on_commit_callbacks).data["estado"] == (
            EstadoViaje.PENDIENTE_CONFIRMACION
        )

    def test_cero_dias_desactiva_la_regla(self, cliente, empresa, twilio, django_capture_on_commit_callbacks):
        empresa.configuracion.vigencia_verificacion_dias = 0
        empresa.configuracion.save()
        verificado_hace(empresa, 0.01)
        assert pedir(cliente, empresa, django_capture_on_commit_callbacks).data["estado"] == (
            EstadoViaje.PENDIENTE_CONFIRMACION
        )

    def test_nunca_verificado_pide_verificar(
        self, cliente, empresa, twilio, django_capture_on_commit_callbacks
    ):
        PasajeroFactory(empresa=empresa, telefono=TELEFONO, verificado_en=None)
        assert pedir(cliente, empresa, django_capture_on_commit_callbacks).data["estado"] == (
            EstadoViaje.PENDIENTE_CONFIRMACION
        )

    def test_la_verificacion_de_otra_empresa_no_cuenta(
        self, cliente, empresa, otra_empresa, twilio, django_capture_on_commit_callbacks
    ):
        verificado_hace(otra_empresa, 1)
        assert pedir(cliente, empresa, django_capture_on_commit_callbacks).data["estado"] == (
            EstadoViaje.PENDIENTE_CONFIRMACION
        )

    def test_se_mantiene_el_limite_de_solicitudes_por_telefono(
        self, cliente, empresa, twilio, django_capture_on_commit_callbacks
    ):
        verificado_hace(empresa, 1)
        estados = [pedir(cliente, empresa, django_capture_on_commit_callbacks).status_code for _ in range(4)]
        assert estados == [201, 201, 201, 429]
        assert Viaje.objects.filter(estado=EstadoViaje.SOLICITADO).count() == 3

    def test_registra_las_aceptaciones(self, cliente, empresa, twilio, django_capture_on_commit_callbacks):
        pasajero = verificado_hace(empresa, 1)
        pedir(cliente, empresa, django_capture_on_commit_callbacks)
        pasajero.refresh_from_db()
        assert pasajero.opt_in_en is not None
        assert pasajero.privacidad_aceptada_en is not None

    def test_la_trampa_responde_igual_sin_crear_nada(
        self, cliente, empresa, twilio, django_capture_on_commit_callbacks
    ):
        verificado_hace(empresa, 1)
        respuesta = pedir(
            cliente, empresa, django_capture_on_commit_callbacks, sitio_web="http://spam.example"
        )
        assert respuesta.status_code == 201
        assert respuesta.data["estado"] == EstadoViaje.PENDIENTE_CONFIRMACION
        assert not Viaje.objects.exists()
        assert twilio.enviados == []
