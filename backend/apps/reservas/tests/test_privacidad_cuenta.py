"""DC-44 (Ley 21.719): el pasajero acepta el aviso de privacidad y los avisos por WhatsApp una sola
vez, al crear la cuenta, con la fecha y la versión del aviso. El pedido no vuelve a aceptar. Las cuentas
antiguas (y todas, si cambia la versión) aceptan una vez al ingresar."""

import pytest
from django.urls import reverse

from apps.auditoria.models import Auditoria
from apps.portal.tests.test_portal import solicitud
from apps.reservas import tareas
from apps.reservas.models import CuentaPasajero, EstadoViaje, Pasajero, Viaje
from apps.reservas.tests.fabricas import CuentaPasajeroFactory
from apps.reservas.tests.test_whatsapp import TwilioFalso

ALTA = {
    "nombre": "Paula Pasajera",
    "telefono": "+56900009301",
    "email": "paula@correo.example",
    "password": "Clave-Sintetica-2026",
}


@pytest.fixture
def twilio(monkeypatch):
    falso = TwilioFalso()
    monkeypatch.setattr(tareas, "obtener_notificador", lambda: falso)
    return falso


@pytest.mark.django_db
class TestAlta:
    def test_sin_la_casilla_no_se_crea(self, cliente, empresa):
        respuesta = cliente.post(reverse("portal-crear-cuenta", args=[empresa.slug]), ALTA, format="json")
        assert respuesta.status_code == 400
        assert "acepta_privacidad" in respuesta.data
        desmarcada = {**ALTA, "acepta_privacidad": False}
        respuesta = cliente.post(
            reverse("portal-crear-cuenta", args=[empresa.slug]), desmarcada, format="json"
        )
        assert respuesta.status_code == 400
        assert not CuentaPasajero.objects.exists()

    def test_registra_la_fecha_y_la_version(self, cliente, empresa, twilio, settings):
        settings.AVISO_PRIVACIDAD_VERSION = "2026-11"
        datos = {**ALTA, "acepta_privacidad": True}
        assert (
            cliente.post(
                reverse("portal-crear-cuenta", args=[empresa.slug]), datos, format="json"
            ).status_code
            == 201
        )
        cuenta = CuentaPasajero.objects.get()
        assert cuenta.privacidad_version == "2026-11"
        assert cuenta.privacidad_aceptada_en is not None


@pytest.mark.django_db
class TestCuentaAntigua:
    def test_la_sesion_avisa_que_debe_aceptar(self, cuenta_antigua):
        assert cuenta_antigua.get(reverse("auth-yo")).json()["debe_aceptar_privacidad"] is True

    def test_no_pide_hasta_aceptar(self, cuenta_antigua):
        respuesta = cuenta_antigua.post(reverse("mi-cuenta-solicitudes"), solicitud(), format="json")
        assert respuesta.status_code == 403
        assert respuesta.json()["code"] == "aceptar_privacidad"
        assert not Viaje.objects.exists()

    def test_acepta_una_vez_y_queda_registrado(self, cuenta_antigua, settings):
        settings.AVISO_PRIVACIDAD_VERSION = "2026-11"
        respuesta = cuenta_antigua.post(reverse("mi-cuenta-privacidad"), {"acepta": True}, format="json")
        assert respuesta.status_code == 200
        assert respuesta.json()["version"] == "2026-11"
        cuenta = CuentaPasajero.objects.get()
        assert (cuenta.privacidad_version, cuenta.privacidad_aceptada_en is not None) == ("2026-11", True)
        pasajero = Pasajero.objects.get(pk=cuenta.pasajero_id)
        assert pasajero.privacidad_aceptada_en == cuenta.privacidad_aceptada_en == pasajero.opt_in_en
        assert Auditoria.objects.filter(accion="ACEPTAR_PRIVACIDAD").count() == 1
        assert cuenta_antigua.get(reverse("auth-yo")).json()["debe_aceptar_privacidad"] is False
        assert (
            cuenta_antigua.post(reverse("mi-cuenta-solicitudes"), solicitud(), format="json").status_code
            == 201
        )

    def test_sin_marcar_no_acepta(self, cuenta_antigua):
        respuesta = cuenta_antigua.post(reverse("mi-cuenta-privacidad"), {"acepta": False}, format="json")
        assert respuesta.status_code == 400
        assert CuentaPasajero.objects.get().privacidad_version is None

    def test_una_version_nueva_pide_aceptar_otra_vez(self, con_cuenta, settings):
        assert con_cuenta.get(reverse("auth-yo")).json()["debe_aceptar_privacidad"] is False
        settings.AVISO_PRIVACIDAD_VERSION = "2027-01"
        assert con_cuenta.get(reverse("auth-yo")).json()["debe_aceptar_privacidad"] is True
        assert (
            con_cuenta.post(reverse("mi-cuenta-solicitudes"), solicitud(), format="json").status_code == 403
        )


@pytest.mark.django_db
class TestPedido:
    def test_el_pedido_no_acepta_nada(self, con_cuenta):
        """Las aceptaciones del pedido se ignoran: la de la cuenta es la que vale."""
        cuerpo = {k: v for k, v in solicitud().items() if not k.startswith("acepta_")}
        assert con_cuenta.post(reverse("mi-cuenta-solicitudes"), cuerpo, format="json").status_code == 201
        falsas = solicitud(acepta_privacidad=False, acepta_whatsapp=False)
        assert con_cuenta.post(reverse("mi-cuenta-solicitudes"), falsas, format="json").status_code == 201
        cuenta = CuentaPasajero.objects.get()
        for viaje in Viaje.objects.all():
            assert viaje.estado == EstadoViaje.SOLICITADO
            assert viaje.pasajero.privacidad_aceptada_en == cuenta.privacidad_aceptada_en

    def test_otros_roles_no_deben_aceptar(self, cliente, despachador):
        cliente.force_authenticate(despachador)
        assert cliente.get(reverse("auth-yo")).json()["debe_aceptar_privacidad"] is False

    def test_pasajero_sin_cuenta_no_debe_aceptar(self, cliente, empresa):
        cuenta = CuentaPasajeroFactory(empresa=empresa)
        cuenta.delete()
        cliente.force_authenticate(cuenta.usuario)
        assert cliente.get(reverse("auth-yo")).json()["debe_aceptar_privacidad"] is False


@pytest.mark.django_db
class TestConfiguracionPublica:
    def test_sin_correo_de_soporte(self, cliente, settings):
        settings.SOPORTE_CORREO = ""
        assert cliente.get(reverse("configuracion-publica")).json() == {"soporte_correo": None}

    def test_con_correo_de_soporte(self, cliente, settings):
        settings.SOPORTE_CORREO = "soporte@flotaagil.example"
        assert cliente.get(reverse("configuracion-publica")).json() == {
            "soporte_correo": "soporte@flotaagil.example"
        }
