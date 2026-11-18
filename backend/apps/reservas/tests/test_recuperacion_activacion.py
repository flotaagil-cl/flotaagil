"""HU-41 (DC-45) y HU-64 (DC-61): recuperación con enlace de 30 min y hasta 3 envíos por correo cada 15 min;
reenvío del enlace de activación por correo, con límite por cuenta; estado de la activación."""

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.reservas.models import CuentaPasajero
from apps.reservas.tests.fabricas import CuentaPasajeroFactory

CLAVE = "Clave-Sintetica-2026"
EMAIL = "paula@correo.example"


@pytest.fixture
def pendiente(cliente, empresa, twilio, django_capture_on_commit_callbacks):
    """Cuenta recién creada por la API, sin confirmar."""
    datos = {"nombre": "Paula Pasajera", "telefono": "+56900009301", "email": EMAIL, "password": CLAVE}
    with django_capture_on_commit_callbacks(execute=True):
        respuesta = cliente.post(
            reverse("portal-crear-cuenta", args=[empresa.slug]),
            {**datos, "acepta_privacidad": True},
            format="json",
        )
    assert respuesta.status_code == 201
    return CuentaPasajero.objects.get()


def url(nombre, empresa):
    return reverse(nombre, args=[empresa.slug])


@pytest.mark.django_db
class TestRecuperacion:
    def test_hasta_3_envios_por_correo_en_la_ventana(
        self, cliente, empresa, django_capture_on_commit_callbacks
    ):
        cuenta = CuentaPasajeroFactory(empresa=empresa, usuario__email=EMAIL)
        cuenta.usuario.set_password(CLAVE)
        cuenta.usuario.save()
        with django_capture_on_commit_callbacks(execute=True):
            estados = [
                cliente.post(reverse("auth-recuperar"), {"email": EMAIL.upper()}, format="json").status_code
                for _ in range(4)
            ]
        assert estados == [202, 202, 202, 202]  # misma respuesta siempre
        assert len(mail.outbox) == 3

    def test_el_limite_cuenta_tambien_correos_inexistentes(self, cliente):
        for _ in range(5):
            assert (
                cliente.post(
                    reverse("auth-recuperar"), {"email": "nadie@correo.example"}, format="json"
                ).status_code
                == 202
            )
        assert mail.outbox == []

    def test_el_enlace_vence_a_los_30_minutos(self, settings):
        assert settings.PASSWORD_RESET_TIMEOUT == 30 * 60

    def test_el_personal_del_panel_no_recibe_enlace(
        self, cliente, administrador, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = cliente.post(reverse("auth-recuperar"), {"email": administrador.email}, format="json")
        assert respuesta.status_code == 202
        assert mail.outbox == []


@pytest.mark.django_db
class TestActivacion:
    def test_estado_pendiente_y_activa(self, cliente, empresa, pendiente):
        respuesta = cliente.post(
            url("portal-cuenta-estado", empresa), {"email": EMAIL, "password": CLAVE}, format="json"
        )
        assert respuesta.status_code == 200
        assert respuesta.json() == {"activa": False, "correo": "p***@correo.example"}
        pendiente.confirmada_en = timezone.now()
        pendiente.pasajero = CuentaPasajeroFactory(empresa=empresa).pasajero
        pendiente.save()
        respuesta = cliente.post(
            url("portal-cuenta-estado", empresa), {"email": EMAIL, "password": CLAVE}, format="json"
        )
        assert respuesta.json()["activa"] is True

    @pytest.mark.parametrize("email,password", [(EMAIL, "otra-clave-xyz"), ("otro@correo.example", CLAVE)])
    def test_credenciales_incorrectas_no_dicen_cual(self, cliente, empresa, pendiente, email, password):
        for ruta in ("portal-cuenta-estado", "portal-cuenta-reenviar"):
            respuesta = cliente.post(
                url(ruta, empresa), {"email": email, "password": password}, format="json"
            )
            assert respuesta.status_code == 400
            assert respuesta.json()["code"] == "cuenta_no_encontrada"

    def test_la_cuenta_de_otra_empresa_no_sirve(self, cliente, otra_empresa, pendiente):
        respuesta = cliente.post(
            url("portal-cuenta-estado", otra_empresa), {"email": EMAIL, "password": CLAVE}, format="json"
        )
        assert respuesta.status_code == 400

    def test_reenvia_el_enlace_por_correo_sin_whatsapp(
        self, cliente, empresa, pendiente, twilio, django_capture_on_commit_callbacks
    ):
        antes = len(mail.outbox)
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = cliente.post(
                url("portal-cuenta-reenviar", empresa), {"email": EMAIL, "password": CLAVE}, format="json"
            )
        assert respuesta.status_code == 200
        assert len(mail.outbox) == antes + 1
        assert "/activar/" in mail.outbox[-1].body
        assert twilio.enviados == []
        assert CuentaPasajero.objects.get().reenviada_en is not None

    def test_hasta_3_reenvios_en_la_ventana(self, cliente, empresa, pendiente):
        datos = {"email": EMAIL, "password": CLAVE}
        estados = [
            cliente.post(url("portal-cuenta-reenviar", empresa), datos, format="json").status_code
            for _ in range(4)
        ]
        assert estados == [200, 200, 200, 429]

    def test_cuenta_ya_activa(self, cliente, empresa):
        cuenta = CuentaPasajeroFactory(empresa=empresa, usuario__email=EMAIL)
        cuenta.usuario.set_password(CLAVE)
        cuenta.usuario.save()
        respuesta = cliente.post(
            url("portal-cuenta-reenviar", empresa), {"email": EMAIL, "password": CLAVE}, format="json"
        )
        assert respuesta.status_code == 409
        assert respuesta.json()["code"] == "cuenta_activa"
