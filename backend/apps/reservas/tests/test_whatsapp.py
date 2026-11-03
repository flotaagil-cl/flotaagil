"""HU-20 · Verificación del pasajero por WhatsApp (RN-06).

CP-07: la solicitud del portal envía la plantilla de verificación. CP-08: Confirmar pasa a SOLICITADO y
Cancelar a CANCELADO, por la máquina de estados. CP-09: webhooks firmados e idempotentes; respuestas
fuera de plazo.
"""

import io
import json
import logging
import urllib.error
import urllib.parse
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.integraciones import notificaciones
from apps.integraciones.notificaciones import (
    NotificadorDesarrollo,
    NotificadorTwilio,
    firma_twilio,
    obtener_notificador,
)
from apps.reservas import verificacion
from apps.reservas.models import (
    Actor,
    DireccionMensaje,
    EstadoEntrega,
    EstadoViaje,
    HistorialEstado,
    MensajeWhatsapp,
    OrigenCancelacion,
    TipoMensaje,
)
from apps.reservas.tests.fabricas import PasajeroFactory, ViajeFactory

ENTRANTE = reverse("whatsapp-entrante")
ESTADO = reverse("whatsapp-estado")
TOKEN = "token-sintetico"
URL_BASE = "https://api.flotaagil.example"


class TwilioFalso(NotificadorTwilio):
    """Doble de Twilio: guarda lo enviado y responde un SID, o los errores dados en orden."""

    def __init__(self, *errores):
        super().__init__("AC" + "0" * 32, TOKEN, "+56900000000", "HX" + "1" * 32, URL_BASE, espera_base=0)
        self.errores = list(errores)
        self.enviados = []

    def _post(self, datos):
        self.enviados.append(datos)
        if self.errores:
            raise self.errores.pop(0)
        return {"sid": f"SM{len(self.enviados):032d}"}


def http_error(codigo):
    return urllib.error.HTTPError("https://api.twilio.com", codigo, "x", {}, io.BytesIO(b""))


@pytest.fixture
def pendiente(empresa):
    pasajero = PasajeroFactory(empresa=empresa, nombre="Ana Pérez", telefono="+56900009001")
    return ViajeFactory(empresa=empresa, pasajero=pasajero, estado=EstadoViaje.PENDIENTE_CONFIRMACION)


@pytest.fixture
def twilio(monkeypatch):
    falso = TwilioFalso()
    monkeypatch.setattr(verificacion, "obtener_notificador", lambda: falso)
    return falso


def enviar_verificacion(viaje, notificador):
    notificador.solicitar_verificacion(viaje, timezone.now() + timedelta(minutes=15))
    return MensajeWhatsapp.objects.filter(viaje=viaje, direccion=DireccionMensaje.SALIENTE).latest(
        "creado_en"
    )


def entrante(viaje, sid="SMentrante0001", payload="confirmar", original=None, **extra):
    return {
        "MessageSid": sid,
        "From": f"whatsapp:{viaje.pasajero.telefono}",
        "Body": payload.capitalize(),
        "ButtonPayload": payload,
        **({"OriginalRepliedMessageSid": original} if original else {}),
        **extra,
    }


@pytest.mark.django_db
class TestEnvio:
    def test_plantilla_con_variables_y_callback(self, pendiente):
        twilio = TwilioFalso()
        mensaje = enviar_verificacion(pendiente, twilio)
        datos = twilio.enviados[0]
        assert (datos["From"], datos["To"]) == ("whatsapp:+56900000000", "whatsapp:+56900009001")
        assert datos["ContentSid"].startswith("HX")
        assert json.loads(datos["ContentVariables"])["1"] == "Ana"
        assert datos["StatusCallback"] == f"{URL_BASE}{ESTADO}"
        assert (mensaje.tipo, mensaje.estado_entrega, mensaje.proveedor_sid) == (
            TipoMensaje.PLANTILLA,
            EstadoEntrega.QUEUED,
            "SM" + "1".zfill(32),
        )
        assert "¿La confirmas?" in mensaje.cuerpo

    def test_reintenta_ante_fallas_transitorias(self, pendiente):
        twilio = TwilioFalso(http_error(503), urllib.error.URLError("sin red"))
        assert enviar_verificacion(pendiente, twilio).estado_entrega == EstadoEntrega.QUEUED
        assert len(twilio.enviados) == 3

    def test_sin_servicio_queda_failed_y_la_solicitud_expira_sola(self, pendiente, caplog):
        twilio = TwilioFalso(TimeoutError(), TimeoutError(), TimeoutError())
        mensaje = enviar_verificacion(pendiente, twilio)
        assert (mensaje.estado_entrega, mensaje.proveedor_sid) == (EstadoEntrega.FAILED, None)
        assert "+56900009001" not in caplog.text  # número enmascarado en el log

    def test_error_de_credenciales_no_reintenta(self, pendiente):
        twilio = TwilioFalso(http_error(401))
        assert enviar_verificacion(pendiente, twilio).estado_entrega == EstadoEntrega.FAILED
        assert len(twilio.enviados) == 1

    def test_desarrollo_registra_sin_enviar(self, pendiente, caplog):
        caplog.set_level(logging.INFO)
        mensaje = enviar_verificacion(pendiente, NotificadorDesarrollo())
        assert mensaje.proveedor_sid.startswith("DEV-")
        assert "+569******01" in caplog.text

    def test_elige_el_notificador_segun_la_configuracion(self, settings):
        assert isinstance(obtener_notificador(), NotificadorDesarrollo)
        settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN = "AC1", TOKEN
        settings.TWILIO_WHATSAPP_FROM, settings.TWILIO_PLANTILLA_VERIFICACION = "+56900000000", "HX1"
        settings.WHATSAPP_URL_BASE = URL_BASE
        assert isinstance(obtener_notificador(), NotificadorTwilio)

    def test_post_real_arma_la_peticion(self, pendiente, monkeypatch):
        capturada = {}

        def urlopen(peticion, timeout):
            capturada.update(
                url=peticion.full_url, auth=peticion.get_header("Authorization"), datos=peticion.data
            )
            return io.BytesIO(b'{"sid": "SM123"}')

        monkeypatch.setattr(notificaciones.urllib.request, "urlopen", urlopen)
        NotificadorTwilio("AC9", TOKEN, "+56900000000", "HX9", URL_BASE).responder(
            pendiente.pasajero, pendiente, "Hola"
        )
        assert capturada["url"] == "https://api.twilio.com/2010-04-01/Accounts/AC9/Messages.json"
        assert capturada["auth"].startswith("Basic ")
        assert b"Body=Hola" in capturada["datos"]


@pytest.mark.django_db
class TestRespuesta:
    def test_confirmar(self, pendiente, twilio):
        original = enviar_verificacion(pendiente, twilio)
        assert (
            verificacion.procesar_entrante(entrante(pendiente, original=original.proveedor_sid))
            == "confirmada"
        )
        pendiente.refresh_from_db()
        assert pendiente.estado == EstadoViaje.SOLICITADO
        assert pendiente.pasajero.verificado_en is not None
        cambio = HistorialEstado.objects.filter(viaje=pendiente).latest("creado_en")
        assert (cambio.estado_anterior, cambio.estado_nuevo, cambio.actor) == (
            EstadoViaje.PENDIENTE_CONFIRMACION,
            EstadoViaje.SOLICITADO,
            Actor.PASAJERO,
        )
        assert "quedó confirmada" in twilio.enviados[-1]["Body"]
        assert (
            MensajeWhatsapp.objects.filter(viaje=pendiente, direccion=DireccionMensaje.ENTRANTE).count() == 1
        )

    def test_cancelar(self, pendiente, twilio):
        assert verificacion.procesar_entrante(entrante(pendiente, payload="cancelar")) == "cancelada"
        pendiente.refresh_from_db()
        assert pendiente.estado == EstadoViaje.CANCELADO
        assert pendiente.origen_cancelacion == OrigenCancelacion.PASAJERO

    def test_mismo_webhook_dos_veces_no_repite(self, pendiente, twilio):
        datos = entrante(pendiente)
        assert verificacion.procesar_entrante(datos) == "confirmada"
        assert verificacion.procesar_entrante(datos) == "repetido"
        assert (
            HistorialEstado.objects.filter(viaje=pendiente).count() == 1
        )  # solo la transición (sin inicial)
        assert len(twilio.enviados) == 1

    def test_responde_al_mensaje_de_su_viaje(self, pendiente, twilio, empresa):
        """Con dos solicitudes pendientes, se confirma la del mensaje respondido, no la más reciente."""
        original = enviar_verificacion(pendiente, twilio)
        otra = ViajeFactory(
            empresa=empresa, pasajero=pendiente.pasajero, estado=EstadoViaje.PENDIENTE_CONFIRMACION
        )
        verificacion.procesar_entrante(entrante(pendiente, original=original.proveedor_sid))
        pendiente.refresh_from_db()
        otra.refresh_from_db()
        assert (pendiente.estado, otra.estado) == (EstadoViaje.SOLICITADO, EstadoViaje.PENDIENTE_CONFIRMACION)

    def test_fuera_de_plazo(self, pendiente, twilio):
        pendiente.estado, pendiente.motivo_cancelacion = EstadoViaje.CANCELADO, "Expiró (RN-06)."
        pendiente.origen_cancelacion = OrigenCancelacion.SISTEMA
        pendiente.save()
        assert verificacion.procesar_entrante(entrante(pendiente)) == "no_vigente"
        assert "ya no está vigente" in twilio.enviados[-1]["Body"]

    def test_texto_libre_no_cambia_nada(self, pendiente, twilio):
        datos = entrante(pendiente, payload="", Body="¿A qué hora llega?")
        assert verificacion.procesar_entrante(datos) == "sin_accion"
        pendiente.refresh_from_db()
        assert pendiente.estado == EstadoViaje.PENDIENTE_CONFIRMACION
        assert twilio.enviados == []

    def test_texto_si_confirma(self, pendiente, twilio):
        assert verificacion.procesar_entrante(entrante(pendiente, payload="", Body=" Sí ")) == "confirmada"

    def test_numero_desconocido(self, twilio):
        datos = {"MessageSid": "SMx", "From": "whatsapp:+56911112222", "Body": "Confirmar"}
        assert verificacion.procesar_entrante(datos) == "desconocido"
        assert not MensajeWhatsapp.objects.exists()


@pytest.mark.django_db
class TestEstadoDeEntrega:
    def test_solo_avanza(self, pendiente):
        mensaje = enviar_verificacion(pendiente, TwilioFalso())
        sid = mensaje.proveedor_sid
        assert verificacion.procesar_estado({"MessageSid": sid, "MessageStatus": "delivered"}) is True
        assert (
            verificacion.procesar_estado({"MessageSid": sid, "MessageStatus": "sent"}) is False
        )  # llegó tarde
        assert verificacion.procesar_estado({"MessageSid": sid, "MessageStatus": "read"}) is True
        mensaje.refresh_from_db()
        assert mensaje.estado_entrega == EstadoEntrega.READ
        assert verificacion.procesar_estado({"MessageSid": "otro", "MessageStatus": "read"}) is False
        assert verificacion.procesar_estado({"MessageSid": sid, "MessageStatus": "raro"}) is False


@pytest.mark.django_db
class TestWebhooks:
    @pytest.fixture(autouse=True)
    def _twilio(self, settings, twilio):
        settings.TWILIO_AUTH_TOKEN = TOKEN
        settings.WHATSAPP_URL_BASE = URL_BASE

    def firmar(self, ruta, datos):
        return {"HTTP_X_TWILIO_SIGNATURE": firma_twilio(TOKEN, f"{URL_BASE}{ruta}", datos)}

    @staticmethod
    def post(cliente, ruta, datos, **extra):
        """Como Twilio: application/x-www-form-urlencoded."""
        return cliente.generic(
            "POST",
            ruta,
            urllib.parse.urlencode(datos),
            content_type="application/x-www-form-urlencoded",
            **extra,
        )

    def test_entrante_firmado(self, cliente, pendiente):
        datos = entrante(pendiente)
        respuesta = self.post(cliente, ENTRANTE, datos, **self.firmar(ENTRANTE, datos))
        assert respuesta.status_code == 200
        assert respuesta["Content-Type"].startswith("text/xml")
        pendiente.refresh_from_db()
        assert pendiente.estado == EstadoViaje.SOLICITADO

    def test_firma_invalida_403(self, cliente, pendiente):
        datos = entrante(pendiente)
        firma = self.firmar(ENTRANTE, {**datos, "Body": "otra cosa"})
        assert self.post(cliente, ENTRANTE, datos, **firma).status_code == 403
        assert self.post(cliente, ENTRANTE, datos).status_code == 403
        pendiente.refresh_from_db()
        assert pendiente.estado == EstadoViaje.PENDIENTE_CONFIRMACION

    def test_estado_firmado(self, cliente, pendiente):
        mensaje = enviar_verificacion(pendiente, TwilioFalso())
        datos = {"MessageSid": mensaje.proveedor_sid, "MessageStatus": "delivered"}
        assert self.post(cliente, ESTADO, datos, **self.firmar(ESTADO, datos)).status_code == 204
        mensaje.refresh_from_db()
        assert mensaje.estado_entrega == EstadoEntrega.DELIVERED

    def test_sin_token_solo_con_debug(self, cliente, pendiente, settings):
        settings.TWILIO_AUTH_TOKEN = ""
        settings.DEBUG = False
        assert self.post(cliente, ENTRANTE, entrante(pendiente)).status_code == 403
        settings.DEBUG = True
        assert self.post(cliente, ENTRANTE, entrante(pendiente)).status_code == 200


@pytest.mark.django_db
class TestPortalYComando:
    def test_la_solicitud_del_portal_envia_la_verificacion(
        self, cliente, empresa, django_capture_on_commit_callbacks
    ):
        """CP-07: crear la solicitud deja el mensaje de verificación registrado."""
        datos = {
            "nombre": "Ana Pérez",
            "telefono": "+56900009001",
            "origen_dir": "Av. Providencia 1234, Providencia",
            "destino_dir": "Plaza de Armas, Santiago",
            "recogida_en": (timezone.now() + timedelta(hours=3)).isoformat(),
            "acepta_privacidad": True,
            "acepta_whatsapp": True,
        }
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = cliente.post(reverse("portal-solicitudes", args=[empresa.slug]), datos, format="json")
        assert respuesta.status_code == 201
        mensaje = MensajeWhatsapp.objects.get()
        assert (mensaje.direccion, mensaje.tipo) == (DireccionMensaje.SALIENTE, TipoMensaje.PLANTILLA)

    def test_simular_confirmar(self, pendiente, settings, capsys):
        settings.DEBUG = True
        enviar_verificacion(pendiente, NotificadorDesarrollo())
        call_command("simular_whatsapp", pendiente.pk, "confirmar")
        assert "confirmada: el viaje" in capsys.readouterr().out
        pendiente.refresh_from_db()
        assert pendiente.estado == EstadoViaje.SOLICITADO
