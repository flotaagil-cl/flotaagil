"""HU-35 (CC-16, DC-36): cuenta de pasajero opcional, por empresa. El invitado sigue igual."""

import re
import urllib.parse
from datetime import timedelta

import pytest
from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auditoria.models import Auditoria
from apps.cuentas.models import Rol, Usuario
from apps.reservas import tareas
from apps.reservas.models import (
    Actor,
    Canal,
    CuentaPasajero,
    EstadoViaje,
    HistorialEstado,
    Viaje,
)
from apps.reservas.tests.fabricas import ConductorFactory, PasajeroFactory, ViajeFactory
from apps.reservas.tests.test_whatsapp import TwilioFalso

ORIGEN = "http://localhost:5173"
TELEFONO = "+56900009301"
CLAVE = "Clave-Sintetica-2026"
E = EstadoViaje


@pytest.fixture
def twilio(monkeypatch):
    falso = TwilioFalso()
    monkeypatch.setattr(tareas, "obtener_notificador", lambda: falso)
    return falso


def crear_cuenta(cliente, empresa, **cambios):
    datos = {
        "nombre": "Paula Pasajera",
        "telefono": TELEFONO,
        "email": "paula@correo.example",
        "password": CLAVE,
        "acepta_privacidad": True,  # DC-44
    }
    datos.update(cambios)
    return cliente.post(reverse("portal-crear-cuenta", args=[empresa.slug]), datos, format="json")


def whatsapp(cliente, texto, desde=TELEFONO, sid="SM" + "9" * 32):
    """Como Twilio: application/x-www-form-urlencoded, sin firma (DEBUG)."""
    datos = {"From": f"whatsapp:{desde}", "Body": texto, "MessageSid": sid}
    return cliente.post(
        reverse("whatsapp-entrante"),
        urllib.parse.urlencode(datos),
        content_type="application/x-www-form-urlencoded",
    )


def entrar(email="paula@correo.example", password=CLAVE):
    web = APIClient(HTTP_ORIGIN=ORIGEN)
    respuesta = web.post(reverse("auth-token"), {"email": email, "password": password}, format="json")
    if respuesta.status_code == 200:
        web.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return web, respuesta


@pytest.fixture
def activa(cliente, empresa, twilio, settings, django_capture_on_commit_callbacks):
    """Cuenta creada y confirmada por WhatsApp; devuelve el cliente con sesión."""
    settings.DEBUG = True  # webhook sin firma, como en las pruebas de HU-20
    with django_capture_on_commit_callbacks(execute=True):
        crear_cuenta(cliente, empresa)
        whatsapp(cliente, "Confirmar cuenta")
    web, _ = entrar()
    return web


@pytest.mark.django_db
class TestRegistro:
    def test_queda_pendiente_y_envia_el_whatsapp(
        self, cliente, empresa, twilio, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = crear_cuenta(cliente, empresa)
        assert respuesta.status_code == 201, respuesta.data
        cuenta = CuentaPasajero.objects.get()
        assert (cuenta.empresa, cuenta.telefono, cuenta.confirmada_en, cuenta.pasajero) == (
            empresa,
            TELEFONO,
            None,
            None,
        )
        assert (cuenta.usuario.rol, cuenta.usuario.activo) == (Rol.PASAJERO, False)
        assert "CONFIRMAR CUENTA" in twilio.enviados[0]["Body"]

    def test_sin_confirmar_no_entra(self, cliente, empresa, twilio):
        crear_cuenta(cliente, empresa)
        _, respuesta = entrar()
        assert (respuesta.status_code, respuesta.data["code"]) == (401, "cuenta_sin_confirmar")

    @pytest.mark.parametrize(
        ("campo", "valor"), [("telefono", "123"), ("email", "x"), ("password", "corta"), ("nombre", " ")]
    )
    def test_valida(self, cliente, empresa, campo, valor):
        assert crear_cuenta(cliente, empresa, **{campo: valor}).status_code == 400
        assert not CuentaPasajero.objects.exists()

    def test_correo_de_otra_cuenta(self, cliente, empresa, despachador):
        respuesta = crear_cuenta(cliente, empresa, email=despachador.email)
        assert respuesta.status_code == 400
        assert "email" in respuesta.data

    def test_repetir_el_registro_pendiente_lo_reemplaza(self, cliente, empresa, twilio):
        crear_cuenta(cliente, empresa)
        assert crear_cuenta(cliente, empresa, telefono="+56900009302").status_code == 201
        assert CuentaPasajero.objects.get().telefono == "+56900009302"

    def test_trampa(self, cliente, empresa):
        assert crear_cuenta(cliente, empresa, sitio_web="http://spam.example").status_code == 201
        assert not CuentaPasajero.objects.exists()


@pytest.mark.django_db
class TestConfirmacion:
    def test_confirmar_activa_y_liga_las_reservas_de_invitado(self, cliente, empresa, twilio, settings):
        settings.DEBUG = True
        anterior = PasajeroFactory(empresa=empresa, telefono=TELEFONO)
        de_invitado = ViajeFactory(empresa=empresa, pasajero=anterior)
        crear_cuenta(cliente, empresa)
        assert whatsapp(cliente, "CONFIRMAR CUENTA").status_code == 200
        cuenta = CuentaPasajero.objects.get()
        assert (cuenta.pasajero, cuenta.usuario.activo) == (anterior, True)
        anterior.refresh_from_db()
        assert anterior.verificado_en is not None
        web, respuesta = entrar()
        assert respuesta.status_code == 200
        assert [r["id"] for r in web.get(reverse("mi-cuenta-reservas")).json()["results"]] == [de_invitado.pk]

    def test_vencida_no_confirma(self, cliente, empresa, twilio, settings):
        settings.DEBUG = True
        crear_cuenta(cliente, empresa)
        CuentaPasajero.objects.update(creada_en=timezone.now() - timedelta(minutes=16))
        whatsapp(cliente, "CONFIRMAR CUENTA")
        assert CuentaPasajero.objects.get().confirmada_en is None

    def test_confirmar_una_reserva_no_confirma_la_cuenta(self, cliente, empresa, twilio, settings):
        settings.DEBUG = True
        crear_cuenta(cliente, empresa)
        whatsapp(cliente, "Confirmar")
        assert CuentaPasajero.objects.get().confirmada_en is None

    def test_un_telefono_confirmado_tiene_una_cuenta_por_empresa(self, cliente, empresa, twilio, settings):
        settings.DEBUG = True
        crear_cuenta(cliente, empresa)
        whatsapp(cliente, "CONFIRMAR CUENTA")
        crear_cuenta(cliente, empresa, email="otra@correo.example")
        whatsapp(cliente, "CONFIRMAR CUENTA", sid="SM" + "8" * 32)
        assert CuentaPasajero.objects.filter(confirmada_en__isnull=False).count() == 1


@pytest.mark.django_db
class TestReservas:
    def solicitud(self, **cambios):
        datos = {
            "origen_dir": "Av. Providencia 1234, Providencia",
            "destino_dir": "Plaza de Armas, Santiago",
            "recogida_en": (timezone.now() + timedelta(hours=2)).isoformat(),
            "acepta_privacidad": True,
            "acepta_whatsapp": True,
        }
        datos.update(cambios)
        return datos

    def test_pide_sin_verificar_con_sus_datos(self, activa, twilio):
        respuesta = activa.post(
            reverse("mi-cuenta-solicitudes"),
            self.solicitud(nombre="Otro", telefono="+56900000000"),
            format="json",
        )
        assert respuesta.status_code == 201, respuesta.data
        assert (respuesta.data["estado"], respuesta.data["expira_en"]) == ("SOLICITADO", None)
        viaje = Viaje.objects.get()
        assert (viaje.pasajero.telefono, viaje.canal) == (TELEFONO, Canal.WEB)
        historial = HistorialEstado.objects.get(viaje=viaje)
        assert (historial.actor, historial.usuario.email) == (Actor.PASAJERO, "paula@correo.example")

    def test_mantiene_el_limite(self, activa):
        estados = [
            activa.post(reverse("mi-cuenta-solicitudes"), self.solicitud(), format="json").status_code
            for _ in range(4)
        ]
        assert estados == [201, 201, 201, 429]

    def test_ve_su_historial(self, activa):
        activa.post(reverse("mi-cuenta-solicitudes"), self.solicitud(), format="json")
        fila = activa.get(reverse("mi-cuenta-reservas")).json()["results"][0]
        assert fila["cancelable"] is True
        assert [h["estado_nuevo"] for h in fila["historial"]] == ["SOLICITADO"]

    def test_cancela_sin_conductor(self, activa):
        activa.post(reverse("mi-cuenta-solicitudes"), self.solicitud(), format="json")
        viaje = Viaje.objects.get()
        respuesta = activa.post(reverse("mi-cuenta-cancelar", args=[viaje.pk]))
        assert respuesta.status_code == 200
        viaje.refresh_from_db()
        assert (viaje.estado, viaje.origen_cancelacion) == (E.CANCELADO, "PASAJERO")

    @pytest.mark.parametrize("estado", [E.ASIGNADO, E.ACEPTADO, E.EN_CAMINO])
    def test_con_conductor_no_cancela(self, activa, empresa, estado):
        pasajero = CuentaPasajero.objects.get().pasajero
        viaje = ViajeFactory(
            empresa=empresa,
            pasajero=pasajero,
            estado=estado,
            conductor=ConductorFactory(usuario__empresa=empresa),
        )
        respuesta = activa.post(reverse("mi-cuenta-cancelar", args=[viaje.pk]))
        assert (respuesta.status_code, respuesta.data["code"]) == (409, "con_conductor")

    def test_no_ve_ni_cancela_reservas_ajenas(self, activa, empresa):
        ajena = ViajeFactory(empresa=empresa, estado=E.SOLICITADO)
        assert activa.post(reverse("mi-cuenta-cancelar", args=[ajena.pk])).status_code == 404
        assert activa.get(reverse("mi-cuenta-reservas")).json()["results"] == []

    def test_el_panel_sigue_cerrado(self, activa):
        assert activa.get(reverse("viaje-list")).status_code == 403


@pytest.mark.django_db
class TestRecuperacion:
    def test_envia_el_enlace_y_permite_cambiarla(
        self, activa, cliente, empresa, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            assert (
                cliente.post(
                    reverse("auth-recuperar"), {"email": "paula@correo.example"}, format="json"
                ).status_code
                == 202
            )
        enlace = re.search(r"/recuperar/([^/]+)/([^/?\s]+)\?empresa=([a-z0-9-]+)", mail.outbox[0].body)
        assert enlace and mail.outbox[0].body.startswith("Hola")
        uid, token, slug = enlace.groups()
        # HU-41: vence en 30 minutos y el enlace lleva la empresa (su marca en la pantalla).
        assert "vence en 30 minutos" in mail.outbox[0].body and slug == empresa.slug
        nueva = "Otra-Clave-Sintetica-1"
        respuesta = cliente.post(
            reverse("auth-recuperar-confirmar"),
            {"uid": uid, "token": token, "password": nueva},
            format="json",
        )
        assert respuesta.status_code == 204
        assert entrar(password=nueva)[1].status_code == 200
        # el enlace sirve una vez
        otra = cliente.post(
            reverse("auth-recuperar-confirmar"),
            {"uid": uid, "token": token, "password": "Tercera-Clave-1"},
            format="json",
        )
        assert otra.status_code == 400

    def test_no_dice_si_el_correo_existe(self, cliente, despachador):
        for email in ["nadie@correo.example", despachador.email]:
            assert cliente.post(reverse("auth-recuperar"), {"email": email}, format="json").status_code == 202
        assert mail.outbox == []

    def test_token_invalido(self, activa, cliente):
        respuesta = cliente.post(
            reverse("auth-recuperar-confirmar"),
            {"uid": "MQ", "token": "x-y", "password": "Otra-Clave-1"},
            format="json",
        )
        assert respuesta.status_code == 400

    def test_bloqueo_tras_5_intentos(self, activa):
        for _ in range(settings.LOGIN_MAX_INTENTOS):
            entrar(password="mala")
        assert entrar()[1].data["code"] == "cuenta_bloqueada"


@pytest.mark.django_db
class TestEliminar:
    def test_anonimiza_y_conserva_las_reservas(self, activa, empresa):
        # HU-45 (DC-50): con la reserva en curso no se puede eliminar; terminada, sí.
        activa.post(
            reverse("mi-cuenta-solicitudes"),
            TestReservas().solicitud(),
            format="json",
        )
        pasajero = CuentaPasajero.objects.get().pasajero
        assert activa.delete(reverse("mi-cuenta")).status_code == 409
        Viaje.objects.filter(pasajero=pasajero).update(estado=E.FINALIZADO)
        assert activa.delete(reverse("mi-cuenta")).status_code == 204
        assert not CuentaPasajero.objects.exists()
        usuario = Usuario.objects.get(rol=Rol.PASAJERO)
        assert (usuario.has_usable_password(), usuario.activo) == (False, False)
        assert "paula" not in usuario.email
        pasajero.refresh_from_db()
        assert (pasajero.nombre, pasajero.telefono) == ("Pasajero eliminado", None)
        assert Viaje.objects.filter(pasajero=pasajero).count() == 1
        assert entrar()[1].status_code == 401
        assert Auditoria.objects.filter(accion="ELIMINAR_CUENTA").exists()
