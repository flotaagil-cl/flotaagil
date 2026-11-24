"""HU-74 (CC-24, DC-78, CP-64): acceso del conductor a la app desde su alta.

Alta con la temporal en la misma respuesta (una sola vez, sin texto plano en la base ni en la auditoría),
primer ingreso con cambio obligatorio, cambio del correo de acceso por el administrador y cambio de contraseña
desde la app.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auditoria.models import Auditoria, Entidad
from apps.cuentas.models import Usuario
from apps.cuentas.tests.fabricas import CLAVE_PRUEBA
from apps.flota.models import EstadoConductor
from apps.reservas.tests.fabricas import ConductorFactory, VehiculoFactory

CONDUCTORES = reverse("conductor-list")
VENCE = (timezone.localdate() + timedelta(days=400)).isoformat()
NUEVA = "Otra-Clave-Segura-2026"


def alta(**cambios):
    return {
        "nombre": "Rosa Pérez",
        "email": "rosa@flota.example",
        "rut": "12.345.678-5",
        "telefono": "9 0000 1234",
        "licencia_clase": "A2",
        "licencia_vence": VENCE,
    } | cambios


def login_app(email, password=CLAVE_PRUEBA):
    return APIClient().post(reverse("auth-app-token"), {"email": email, "password": password}, format="json")


def correo(conductor):
    return reverse("conductor-correo", args=[conductor.pk])


@pytest.fixture
def api(cliente, administrador):
    cliente.force_authenticate(administrador)
    return cliente


@pytest.fixture
def chofer(empresa):
    return ConductorFactory(usuario__empresa=empresa, usuario__email="pedro@flota.example")


@pytest.mark.django_db
class TestAltaConAcceso:
    def test_temporal_una_vez_sin_cache_ni_texto_plano(self, api):
        respuesta = api.post(CONDUCTORES, alta(), format="json")
        assert respuesta.status_code == 201
        assert respuesta["Cache-Control"] == "no-store"
        datos = respuesta.json()
        password = datos["password_temporal"]
        assert len(password) == 14 and datos["vence_en"]
        cuenta = Usuario.objects.get(email="rosa@flota.example")
        assert password not in cuenta.password and cuenta.check_password(password)
        assert password not in str(list(Auditoria.objects.values()))
        ficha = api.get(reverse("conductor-detail", args=[datos["id"]])).json()
        assert "password_temporal" not in ficha and password not in str(ficha)
        acciones = set(Auditoria.objects.values_list("accion", flat=True))
        assert {"CREAR", "GENERAR_PASSWORD"} <= acciones

    def test_primer_ingreso_obliga_a_cambiarla(self, api):
        password = api.post(CONDUCTORES, alta(), format="json").json()["password_temporal"]
        sesion = login_app("rosa@flota.example", password)
        assert sesion.status_code == 200
        assert sesion.data["usuario"]["debe_cambiar_password"] is True
        app = APIClient()
        app.credentials(HTTP_AUTHORIZATION=f"Bearer {sesion.data['access']}")
        assert app.get(reverse("app-perfil")).status_code == 403  # cambio_password_requerido
        cambio = app.post(
            reverse("auth-password"), {"password_actual": password, "password_nueva": NUEVA}, format="json"
        )
        assert cambio.status_code == 200
        assert login_app("rosa@flota.example", NUEVA).data["usuario"]["debe_cambiar_password"] is False

    def test_correo_repetido_no_crea_nada(self, api, chofer):
        respuesta = api.post(CONDUCTORES, alta(email="PEDRO@flota.example"), format="json")
        assert respuesta.status_code == 400 and "email" in respuesta.json()
        assert not Usuario.objects.filter(nombre="Rosa Pérez").exists()

    def test_ficha_con_ultimo_ingreso(self, api, chofer):
        assert api.get(reverse("conductor-detail", args=[chofer.pk])).json()["ultimo_ingreso"] is None
        login_app(chofer.usuario.email)
        assert api.get(reverse("conductor-detail", args=[chofer.pk])).json()["ultimo_ingreso"] is not None


@pytest.mark.django_db
class TestCambiarCorreo:
    def test_cambia_cierra_sesiones_y_audita(self, api, chofer):
        refresh = login_app("pedro@flota.example").data["refresh"]
        respuesta = api.post(correo(chofer), {"email": " Pedro.Soto@Flota.example "}, format="json")
        assert respuesta.status_code == 200, respuesta.json()
        assert respuesta.json()["email"] == "pedro.soto@flota.example"
        renovar = APIClient().post(reverse("auth-app-refresh"), {"refresh": refresh}, format="json")
        assert renovar.status_code == 401
        assert login_app("pedro@flota.example").status_code == 401
        assert login_app("pedro.soto@flota.example").status_code == 200
        registro = Auditoria.objects.get(accion="CAMBIAR_CORREO")
        assert (registro.entidad, registro.entidad_id) == (Entidad.USUARIO, chofer.usuario_id)
        assert registro.datos_previos == {"email": "pedro@flota.example"}

    def test_correo_usado_400(self, api, chofer, despachador):
        respuesta = api.post(correo(chofer), {"email": despachador.email.upper()}, format="json")
        assert respuesta.status_code == 400 and "email" in respuesta.json()
        assert not Auditoria.objects.filter(accion="CAMBIAR_CORREO").exists()

    def test_mismo_correo_no_hace_nada(self, api, chofer):
        assert api.post(correo(chofer), {"email": "pedro@flota.example"}, format="json").status_code == 200
        assert not Auditoria.objects.filter(accion="CAMBIAR_CORREO").exists()

    def test_409_en_viaje(self, api, empresa, chofer):
        chofer.vehiculo_activo, chofer.estado = VehiculoFactory(empresa=empresa), EstadoConductor.EN_VIAJE
        chofer.save()
        respuesta = api.post(correo(chofer), {"email": "nuevo@flota.example"}, format="json")
        assert respuesta.status_code == 409
        assert Usuario.objects.get(pk=chofer.usuario_id).email == "pedro@flota.example"

    def test_solo_administrador(self, cliente, despachador, chofer):
        cliente.force_authenticate(despachador)
        assert cliente.post(correo(chofer), {"email": "x@flota.example"}, format="json").status_code == 403

    def test_de_otra_empresa_404(self, api, otra_empresa):
        ajeno = ConductorFactory(usuario__empresa=otra_empresa)
        assert api.post(correo(ajeno), {"email": "x@flota.example"}, format="json").status_code == 404


@pytest.mark.django_db
class TestCambiarPasswordDesdeLaApp:
    def test_con_la_actual_cierra_otras_sesiones(self, chofer):
        otra = login_app("pedro@flota.example").data["refresh"]
        sesion = login_app("pedro@flota.example").data
        app = APIClient()
        app.credentials(HTTP_AUTHORIZATION=f"Bearer {sesion['access']}")
        malo = app.post(
            reverse("auth-password"), {"password_actual": "mala", "password_nueva": NUEVA}, format="json"
        )
        assert malo.status_code == 400 and "password_actual" in malo.json()
        datos = {"password_actual": CLAVE_PRUEBA, "password_nueva": NUEVA}
        bueno = app.post(reverse("auth-password"), datos, format="json")
        assert bueno.status_code == 200 and bueno.json()["refresh"]
        renovar = APIClient().post(reverse("auth-app-refresh"), {"refresh": otra}, format="json")
        assert renovar.status_code == 401
        assert Auditoria.objects.filter(accion="CAMBIAR_PASSWORD", entidad_id=chofer.usuario_id).exists()
