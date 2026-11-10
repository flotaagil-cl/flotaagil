"""HU-33 (CC-16, DC-34): un solo inicio de sesión web para administrador, despachador, convenio y pasajero."""

import smtplib
from unittest import mock

import pytest
from django.conf import settings
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient

from apps.cuentas import tareas
from apps.integraciones import correo

from .fabricas import CLAVE_PRUEBA, UsuarioFactory

ORIGEN = "http://localhost:5173"
COOKIE = settings.JWT_COOKIE["nombre"]


def web():
    return APIClient(HTTP_ORIGIN=ORIGEN)


def entrar(cliente, usuario):
    return cliente.post(
        reverse("auth-token"), {"email": usuario.email, "password": CLAVE_PRUEBA}, format="json"
    )


@pytest.mark.django_db
class TestLoginWeb:
    @pytest.mark.parametrize("rol", ["ADMINISTRADOR", "DESPACHADOR", "CONVENIO", "PASAJERO"])
    def test_los_cuatro_roles_entran_con_la_cookie(self, empresa, rol):
        usuario = UsuarioFactory(empresa=empresa, rol=rol)
        respuesta = entrar(web(), usuario)
        assert respuesta.status_code == 200, respuesta.data
        assert respuesta.data["usuario"]["rol"] == rol
        assert respuesta.data["usuario"]["empresa"]["slug"] == empresa.slug
        assert COOKIE in respuesta.cookies

    def test_el_conductor_sigue_en_la_app(self, empresa):
        conductor = UsuarioFactory(empresa=empresa, rol="CONDUCTOR")
        respuesta = entrar(web(), conductor)
        assert (respuesta.status_code, respuesta.data["code"]) == (403, "rol_no_permitido")

    @pytest.mark.parametrize("rol", ["CONVENIO", "PASAJERO"])
    def test_la_app_no_admite_los_roles_web(self, empresa, rol):
        usuario = UsuarioFactory(empresa=empresa, rol=rol)
        respuesta = APIClient().post(
            reverse("auth-app-token"), {"email": usuario.email, "password": CLAVE_PRUEBA}, format="json"
        )
        assert respuesta.status_code == 403

    @pytest.mark.parametrize("rol", ["CONVENIO", "PASAJERO"])
    def test_renueva_la_sesion(self, empresa, rol):
        cliente = web()
        entrar(cliente, UsuarioFactory(empresa=empresa, rol=rol))
        assert cliente.post(reverse("auth-refresh")).status_code == 200

    @pytest.mark.parametrize("rol", ["CONVENIO", "PASAJERO"])
    @pytest.mark.parametrize(
        "ruta",
        [
            "viaje-list",
            "conductor-list",
            "vehiculo-list",
            "convenio-list",
            "turnos-por-cerrar",
            "indicadores",
        ],
    )
    def test_no_ven_nada_del_panel(self, empresa, rol, ruta):
        cliente = web()
        access = entrar(cliente, UsuarioFactory(empresa=empresa, rol=rol)).data["access"]
        cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        assert cliente.get(reverse(ruta)).status_code == 403

    def test_yo_y_cambiar_password_si(self, empresa):
        cliente = web()
        access = entrar(cliente, UsuarioFactory(empresa=empresa, rol="PASAJERO")).data["access"]
        cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        assert cliente.get(reverse("auth-yo")).status_code == 200

    def test_bloqueo_tras_5_intentos_tambien(self, empresa):
        usuario = UsuarioFactory(empresa=empresa, rol="PASAJERO")
        cliente = web()
        for _ in range(settings.LOGIN_MAX_INTENTOS):
            cliente.post(reverse("auth-token"), {"email": usuario.email, "password": "mala"}, format="json")
        assert entrar(cliente, usuario).data["code"] == "cuenta_bloqueada"


@pytest.mark.django_db
class TestCorreo:
    def test_envia_por_el_backend_configurado(self):
        tareas.enviar_correo.delay("ana@ejemplo.example", "Asunto", "Texto")
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["ana@ejemplo.example"]
        assert mail.outbox[0].from_email == settings.DEFAULT_FROM_EMAIL

    def test_falla_transitoria_reintenta(self):
        llamadas = []

        def falla_una_vez(*args, **kwargs):
            llamadas.append(1)
            if len(llamadas) == 1:
                raise smtplib.SMTPServerDisconnected("se cortó")
            return 1

        with mock.patch("apps.integraciones.correo.send_mail", side_effect=falla_una_vez):
            tareas.enviar_correo.apply(args=["ana@ejemplo.example", "A", "T"])
        assert len(llamadas) == 2

    def test_rechazo_definitivo_no_reintenta(self):
        error = smtplib.SMTPResponseException(554, b"Message rejected")
        with mock.patch("apps.integraciones.correo.send_mail", side_effect=error) as envio:
            resultado = tareas.enviar_correo.apply(args=["ana@ejemplo.example", "A", "T"])
        assert envio.call_count == 1
        assert resultado.failed()

    def test_enmascara_para_el_log(self):
        assert correo.enmascarar("ana.perez@ejemplo.cl") == "a***@ejemplo.cl"

    def test_ses_se_activa_por_configuracion(self, monkeypatch):
        import importlib

        from config import settings as modulo

        monkeypatch.setenv("CORREO_PROVEEDOR", "ses")
        monkeypatch.setenv("SES_SMTP_USUARIO", "AKIAEJEMPLO")
        monkeypatch.setenv("SES_SMTP_CLAVE", "clave-de-ejemplo")
        try:
            recargado = importlib.reload(modulo)
            assert recargado.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend"
            assert recargado.EMAIL_HOST == "email-smtp.us-east-1.amazonaws.com"
            assert (recargado.EMAIL_PORT, recargado.EMAIL_USE_TLS) == (587, True)
        finally:
            monkeypatch.delenv("CORREO_PROVEEDOR")
            importlib.reload(modulo)
