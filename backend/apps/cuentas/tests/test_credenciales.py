"""Contraseña temporal, cambio obligatorio, revocación de sesiones y logout de la app.

HU-10, DC-14 y PR-02.
"""

import logging
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auditoria.models import Auditoria, Entidad
from apps.cuentas import credenciales
from apps.cuentas.models import Rol, Usuario
from apps.cuentas.tests.fabricas import CLAVE_PRUEBA, UsuarioFactory

LOGIN_APP = reverse("auth-app-token")
REFRESH_APP = reverse("auth-app-refresh")
LOGOUT_APP = reverse("auth-app-logout")
PASSWORD = reverse("auth-password")
YO = reverse("auth-yo")
NUEVA = "otra-clave-segura-2026"


def login_app(email, password):
    return APIClient().post(LOGIN_APP, {"email": email, "password": password}, format="json")


def con_access(access):
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return cliente


@pytest.fixture
def chofer(empresa):
    return UsuarioFactory(empresa=empresa, rol=Rol.CONDUCTOR)


@pytest.fixture
def temporal(chofer, administrador):
    password, _ = credenciales.asignar_password_temporal(chofer, por=administrador)
    return password


class TestGenerar:
    def test_largo_y_alfabeto_sin_ambiguos(self):
        for _ in range(200):
            password = credenciales.nueva_password_temporal()
            assert len(password) == 14
            assert not set(password) & set("0Oo1lIi")
            assert any(c.isupper() for c in password)
            assert any(c.islower() for c in password)
            assert any(c.isdigit() for c in password)

    def test_no_se_repiten(self):
        assert len({credenciales.nueva_password_temporal() for _ in range(100)}) == 100


@pytest.mark.django_db
class TestTemporal:
    def test_se_guarda_solo_el_hash_y_no_queda_en_auditoria_ni_logs(self, chofer, administrador, caplog):
        caplog.set_level(logging.DEBUG)
        password, vence = credenciales.asignar_password_temporal(chofer, por=administrador)
        chofer.refresh_from_db()
        assert chofer.password.startswith("pbkdf2_sha256$")
        assert password not in chofer.password
        assert chofer.debe_cambiar_password is True
        assert timedelta(hours=71, minutes=59) < vence - timezone.now() <= timedelta(hours=72)
        registro = Auditoria.objects.get(entidad=Entidad.USUARIO, entidad_id=chofer.pk)
        assert registro.accion == "RESTABLECER_PASSWORD"
        assert password not in str(registro.datos_previos)
        assert password not in caplog.text

    def test_primera_vez_es_generar(self, empresa, administrador):
        cuenta = Usuario.objects.create_user(
            "nuevo@x.example", None, nombre="N", empresa=empresa, rol=Rol.CONDUCTOR
        )
        assert not cuenta.has_usable_password()
        assert credenciales.estado_de_acceso(cuenta) == "SIN_PASSWORD"
        credenciales.asignar_password_temporal(cuenta, por=administrador)
        assert Auditoria.objects.get(entidad_id=cuenta.pk).accion == "GENERAR_PASSWORD"

    def test_cierra_las_sesiones_abiertas(self, chofer, administrador):
        refresh = login_app(chofer.email, CLAVE_PRUEBA).data["refresh"]
        credenciales.asignar_password_temporal(chofer, por=administrador)
        respuesta = APIClient().post(REFRESH_APP, {"refresh": refresh}, format="json")
        assert respuesta.status_code == 401

    def test_desbloquea_la_cuenta(self, chofer, administrador):
        Usuario.objects.filter(pk=chofer.pk).update(
            intentos_fallidos=5, bloqueado_hasta=timezone.now() + timedelta(hours=1)
        )
        password, _ = credenciales.asignar_password_temporal(chofer, por=administrador)
        assert login_app(chofer.email, password).status_code == 200


@pytest.mark.django_db
class TestCambioObligatorio:
    def test_login_con_la_temporal_avisa_y_bloquea_el_resto_de_la_api(self, chofer, temporal):
        sesion = login_app(chofer.email, temporal)
        assert sesion.status_code == 200
        assert sesion.data["usuario"]["debe_cambiar_password"] is True
        cliente = con_access(sesion.data["access"])
        yo = cliente.get(YO)
        assert (yo.status_code, yo.data["debe_cambiar_password"]) == (200, True)
        for url in (reverse("viaje-list"), reverse("conductor-list")):
            respuesta = cliente.get(url)
            assert respuesta.status_code == 403, url
            assert respuesta.json()["code"] == "cambio_password_requerido"

    def test_refresh_y_logout_siguen_disponibles(self, chofer, temporal):
        sesion = login_app(chofer.email, temporal).data
        renovada = APIClient().post(REFRESH_APP, {"refresh": sesion["refresh"]}, format="json")
        assert renovada.status_code == 200
        assert (
            APIClient().post(LOGOUT_APP, {"refresh": renovada.data["refresh"]}, format="json").status_code
            == 204
        )

    def test_cambiar_entrega_tokens_nuevos_y_libera_la_api(self, chofer, temporal):
        sesion = login_app(chofer.email, temporal).data
        respuesta = con_access(sesion["access"]).post(
            PASSWORD, {"password_actual": temporal, "password_nueva": NUEVA}, format="json"
        )
        assert respuesta.status_code == 200, respuesta.json()
        assert set(respuesta.data) == {"access", "refresh"}
        chofer.refresh_from_db()
        assert (chofer.debe_cambiar_password, chofer.password_temporal_vence) == (False, None)
        assert con_access(respuesta.data["access"]).get(YO).status_code == 200
        # La sesión de la temporal quedó cerrada; la nueva renueva.
        assert APIClient().post(REFRESH_APP, {"refresh": sesion["refresh"]}, format="json").status_code == 401
        assert (
            APIClient().post(REFRESH_APP, {"refresh": respuesta.data["refresh"]}, format="json").status_code
            == 200
        )
        assert login_app(chofer.email, NUEVA).status_code == 200
        assert login_app(chofer.email, temporal).status_code == 401
        assert Auditoria.objects.filter(entidad_id=chofer.pk, accion="CAMBIAR_PASSWORD").exists()

    @pytest.mark.parametrize(
        ("actual", "nueva", "campo"),
        [
            ("incorrecta", NUEVA, "password_actual"),
            (None, "corta", "password_nueva"),
            (None, "1234567890123", "password_nueva"),
            (None, None, "password_nueva"),
        ],
    )
    def test_cambiar_rechaza(self, chofer, temporal, actual, nueva, campo):
        sesion = login_app(chofer.email, temporal).data
        datos = {"password_actual": actual or temporal, "password_nueva": nueva or temporal}
        respuesta = con_access(sesion["access"]).post(PASSWORD, datos, format="json")
        assert respuesta.status_code == 400
        assert campo in respuesta.json()
        chofer.refresh_from_db()
        assert chofer.debe_cambiar_password is True

    def test_la_temporal_vencida_no_sirve(self, chofer, temporal):
        Usuario.objects.filter(pk=chofer.pk).update(
            password_temporal_vence=timezone.now() - timedelta(minutes=1)
        )
        respuesta = login_app(chofer.email, temporal)
        assert respuesta.status_code == 401
        assert respuesta.json()["code"] == "password_temporal_vencida"
        chofer.refresh_from_db()
        assert credenciales.estado_de_acceso(chofer) == "TEMPORAL_VENCIDA"

    def test_cambio_voluntario_desde_el_panel(self, panel, administrador):
        """Un usuario sin temporal también puede cambiarla; en el panel el refresh vuelve en la cookie."""
        sesion = panel.post(
            reverse("auth-token"), {"email": administrador.email, "password": CLAVE_PRUEBA}, format="json"
        )
        panel.credentials(HTTP_AUTHORIZATION=f"Bearer {sesion.data['access']}")
        respuesta = panel.post(
            PASSWORD, {"password_actual": CLAVE_PRUEBA, "password_nueva": NUEVA}, format="json"
        )
        assert respuesta.status_code == 200
        assert set(respuesta.data) == {"access"}
        assert respuesta.cookies["refresh_panel"].value

    def test_sin_sesion(self):
        assert APIClient().post(PASSWORD, {}, format="json").status_code == 401


@pytest.mark.django_db
class TestLogoutApp:
    def test_invalida_el_refresh(self, conductor):
        refresh = login_app(conductor.email, CLAVE_PRUEBA).data["refresh"]
        assert APIClient().post(LOGOUT_APP, {"refresh": refresh}, format="json").status_code == 204
        assert APIClient().post(REFRESH_APP, {"refresh": refresh}, format="json").status_code == 401

    @pytest.mark.parametrize("cuerpo", [{}, {"refresh": "basura"}])
    def test_siempre_204(self, cuerpo):
        assert APIClient().post(LOGOUT_APP, cuerpo, format="json").status_code == 204

    def test_no_toca_un_refresh_del_panel(self, panel, administrador):
        panel.post(
            reverse("auth-token"), {"email": administrador.email, "password": CLAVE_PRUEBA}, format="json"
        )
        refresh = panel.cookies["refresh_panel"].value
        assert APIClient().post(LOGOUT_APP, {"refresh": refresh}, format="json").status_code == 204
        assert panel.post(reverse("auth-refresh")).status_code == 200


@pytest.mark.django_db
def test_revocar_sesiones_cuenta_solo_las_vigentes(chofer):
    login_app(chofer.email, CLAVE_PRUEBA)
    login_app(chofer.email, CLAVE_PRUEBA)
    assert credenciales.revocar_sesiones(chofer) == 2
    assert credenciales.revocar_sesiones(chofer) == 0
