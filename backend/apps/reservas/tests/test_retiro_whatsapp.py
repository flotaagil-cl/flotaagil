"""HU-67 y HU-68 (CC-19): ningún envío por WhatsApp (CP-57) y la purga de los mensajes a los 12 meses."""

from datetime import timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.chat.models import Conversacion, Mensaje, TipoConversacion
from apps.reservas import tareas
from apps.reservas.models import DireccionMensaje, MensajeWhatsapp, TipoMensaje
from apps.reservas.retencion import purgar_mensajes
from apps.reservas.tests.fabricas import ConductorFactory, PasajeroFactory

RAIZ = Path(settings.BASE_DIR)


class TestRetiroDeTwilio:
    """CP-57: sin cliente, webhooks, plantillas ni variables de Twilio en el código."""

    def test_el_codigo_no_menciona_twilio(self):
        fuentes = [
            p
            for carpeta in ("apps", "config")
            for p in (RAIZ / carpeta).rglob("*.py")
            if "tests" not in p.parts and "migrations" not in p.parts
        ]
        con_twilio = [
            str(p.relative_to(RAIZ)) for p in fuentes if "twilio" in p.read_text(encoding="utf-8").lower()
        ]
        assert con_twilio == []
        assert not [nombre for nombre in dir(settings) if nombre.startswith(("TWILIO", "WHATSAPP"))]
        assert "twilio" not in (RAIZ / "requirements.txt").read_text(encoding="utf-8").lower()

    def test_los_webhooks_ya_no_existen(self, cliente):
        for nombre in ("whatsapp-entrante", "whatsapp-estado"):
            with pytest.raises(NoReverseMatch):
                reverse(nombre)
        assert cliente.post("/api/whatsapp/entrante/", {"Body": "CONFIRMAR"}).status_code == 404

    def test_no_quedan_tareas_de_whatsapp(self):
        for tarea in ("enviar_verificacion", "enviar_respuesta", "enviar_chat", "encolar_chat"):
            assert not hasattr(tareas, tarea)


@pytest.mark.django_db
class TestRetencion:
    """HU-68 (RN-15): mensajes del chat y del historial de WhatsApp, 12 meses."""

    def test_purga_lo_mas_antiguo_y_deja_lo_reciente(self, empresa):
        conductor = ConductorFactory(usuario__empresa=empresa)
        central = Conversacion.objects.create(
            empresa=empresa, tipo=TipoConversacion.CENTRAL, conductor=conductor
        )
        viejo = Mensaje.objects.create(conversacion=central, autor=conductor.usuario, texto="Viejo")
        nuevo = Mensaje.objects.create(conversacion=central, autor=conductor.usuario, texto="Nuevo")
        pasajero = PasajeroFactory(empresa=empresa)
        wa_viejo = MensajeWhatsapp.objects.create(
            pasajero=pasajero, direccion=DireccionMensaje.ENTRANTE, tipo=TipoMensaje.SESION, cuerpo="Viejo"
        )
        hace_mas_de_un_anio = timezone.now() - timedelta(days=366)
        Mensaje.objects.filter(pk=viejo.pk).update(creado_en=hace_mas_de_un_anio)
        MensajeWhatsapp.objects.filter(pk=wa_viejo.pk).update(creado_en=hace_mas_de_un_anio)
        MensajeWhatsapp.objects.create(
            pasajero=pasajero, direccion=DireccionMensaje.ENTRANTE, tipo=TipoMensaje.SESION, cuerpo="Reciente"
        )
        assert tareas.purgar_mensajes.delay().get() == {"chat": 1, "whatsapp": 1}
        assert list(Mensaje.objects.values_list("pk", flat=True)) == [nuevo.pk]
        assert list(MensajeWhatsapp.objects.values_list("cuerpo", flat=True)) == ["Reciente"]
        assert Conversacion.objects.filter(pk=central.pk).exists()

    def test_el_plazo_se_configura(self, empresa, settings):
        conductor = ConductorFactory(usuario__empresa=empresa)
        central = Conversacion.objects.create(
            empresa=empresa, tipo=TipoConversacion.CENTRAL, conductor=conductor
        )
        mensaje = Mensaje.objects.create(conversacion=central, autor=conductor.usuario, texto="Hace 40 días")
        Mensaje.objects.filter(pk=mensaje.pk).update(creado_en=timezone.now() - timedelta(days=40))
        assert purgar_mensajes() == {"chat": 0, "whatsapp": 0}
        settings.RETENCION_MENSAJES_DIAS = 30
        assert purgar_mensajes() == {"chat": 1, "whatsapp": 0}
