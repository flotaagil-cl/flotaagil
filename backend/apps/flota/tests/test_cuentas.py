"""Alta de conductores con su cuenta, contraseña temporal, deshabilitar y habilitar, y carga por CSV.

HU-10, CP-02.
"""

from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.auditoria.models import Auditoria, Entidad
from apps.cuentas import credenciales
from apps.cuentas.models import Rol, Usuario
from apps.cuentas.tests.fabricas import CLAVE_PRUEBA, UsuarioFactory
from apps.flota.models import Conductor, EstadoConductor
from apps.reservas.tests.fabricas import ConductorFactory, VehiculoFactory

CONDUCTORES = reverse("conductor-list")
IMPORTAR = reverse("conductor-importar")
VENCE = (timezone.localdate() + timedelta(days=400)).isoformat()


def url(nombre, conductor):
    return reverse(f"conductor-{nombre}", args=[conductor.pk])


def alta(**cambios):
    return {
        "nombre": "Rosa Pérez",
        "email": "Rosa@Flota.example",
        "rut": "12.345.678-5",
        "telefono": "9 0000 1234",
        "licencia_clase": "A2",
        "licencia_vence": VENCE,
    } | cambios


@pytest.fixture
def api(cliente, administrador):
    cliente.force_authenticate(administrador)
    return cliente


@pytest.fixture
def chofer(empresa):
    return ConductorFactory(usuario__empresa=empresa, usuario__nombre="Pedro Soto")


def login_app(email, password=CLAVE_PRUEBA):
    return APIClient().post(reverse("auth-app-token"), {"email": email, "password": password}, format="json")


@pytest.mark.django_db
class TestAlta:
    def test_crea_cuenta_sin_password_utilizable(self, api, empresa):
        respuesta = api.post(CONDUCTORES, alta(), format="json")
        assert respuesta.status_code == 201, respuesta.json()
        datos = respuesta.json()
        assert (datos["email"], datos["rut"], datos["telefono"], datos["acceso"], datos["estado"]) == (
            "rosa@flota.example",
            "12345678-5",
            "+56900001234",
            "SIN_PASSWORD",
            "NO_DISPONIBLE",
        )
        cuenta = Usuario.objects.get(email="rosa@flota.example")
        assert (cuenta.rol, cuenta.empresa, cuenta.has_usable_password()) == (Rol.CONDUCTOR, empresa, False)
        assert Auditoria.objects.get(entidad=Entidad.CONDUCTOR).accion == "CREAR"
        assert login_app("rosa@flota.example", "").status_code in (400, 401)

    @pytest.mark.parametrize("campo", ["email", "rut"])
    def test_correo_y_rut_unicos(self, api, chofer, campo):
        valor = chofer.usuario.email.upper() if campo == "email" else chofer.rut
        respuesta = api.post(CONDUCTORES, alta(**{campo: valor}), format="json")
        assert respuesta.status_code == 400
        assert campo in respuesta.json()

    def test_licencia_vencida(self, api):
        respuesta = api.post(CONDUCTORES, alta(licencia_vence="2020-01-01"), format="json")
        assert "licencia_vence" in respuesta.json()

    def test_solo_administrador(self, cliente, despachador):
        cliente.force_authenticate(despachador)
        assert cliente.post(CONDUCTORES, alta(), format="json").status_code == 403


@pytest.mark.django_db
class TestPassword:
    def test_genera_una_vez_sin_cache_y_obliga_a_cambiarla(self, api, chofer):
        respuesta = api.post(url("password", chofer))
        assert respuesta.status_code == 201
        assert respuesta["Cache-Control"] == "no-store"
        password = respuesta.json()["password_temporal"]
        assert len(password) == 14
        assert api.get(url("detail", chofer)).json()["acceso"] == "TEMPORAL"
        assert password not in str(api.get(url("detail", chofer)).json())
        sesion = login_app(chofer.usuario.email, password)
        assert sesion.data["usuario"]["debe_cambiar_password"] is True

    def test_restablecer_cierra_las_sesiones(self, api, chofer):
        refresh = login_app(chofer.usuario.email).data["refresh"]
        api.post(url("password", chofer))
        renovar = APIClient().post(reverse("auth-app-refresh"), {"refresh": refresh}, format="json")
        assert renovar.status_code == 401
        assert login_app(chofer.usuario.email).status_code == 401  # la anterior ya no sirve

    def test_409_en_viaje(self, api, empresa, chofer):
        chofer.vehiculo_activo, chofer.estado = VehiculoFactory(empresa=empresa), EstadoConductor.EN_VIAJE
        chofer.save()
        respuesta = api.post(url("password", chofer))
        assert respuesta.status_code == 409
        assert respuesta.json()["code"] == "conductor_en_viaje"
        assert not Auditoria.objects.filter(entidad=Entidad.USUARIO).exists()

    def test_de_otra_empresa_404(self, api, otra_empresa):
        ajeno = ConductorFactory(usuario__empresa=otra_empresa)
        assert api.post(url("password", ajeno)).status_code == 404


@pytest.mark.django_db
class TestHabilitacion:
    def test_deshabilitar_cierra_sesiones_y_deja_no_disponible(self, api, empresa, chofer):
        chofer.vehiculo_activo, chofer.estado = VehiculoFactory(empresa=empresa), EstadoConductor.DISPONIBLE
        chofer.save()
        refresh = login_app(chofer.usuario.email).data["refresh"]
        respuesta = api.post(url("deshabilitar", chofer))
        assert respuesta.status_code == 200
        assert (respuesta.json()["activo"], respuesta.json()["estado"]) == (False, "NO_DISPONIBLE")
        renovar = APIClient().post(reverse("auth-app-refresh"), {"refresh": refresh}, format="json")
        assert renovar.status_code == 401
        assert login_app(chofer.usuario.email).json()["code"] == "cuenta_deshabilitada"
        registro = Auditoria.objects.get(entidad=Entidad.USUARIO, accion="DESHABILITAR")
        assert registro.datos_previos == {"activo": True, "estado": "DISPONIBLE"}

    def test_deshabilitar_en_viaje_409(self, api, empresa, chofer):
        chofer.vehiculo_activo, chofer.estado = VehiculoFactory(empresa=empresa), EstadoConductor.EN_VIAJE
        chofer.save()
        assert api.post(url("deshabilitar", chofer)).status_code == 409
        chofer.usuario.refresh_from_db()
        assert chofer.usuario.activo is True

    def test_habilitar_y_repetir_no_audita_dos_veces(self, api, chofer):
        api.post(url("deshabilitar", chofer))
        api.post(url("deshabilitar", chofer))
        assert api.post(url("habilitar", chofer)).json()["activo"] is True
        acciones = list(Auditoria.objects.filter(entidad=Entidad.USUARIO).values_list("accion", flat=True))
        assert acciones == ["HABILITAR", "DESHABILITAR"]
        assert login_app(chofer.usuario.email).status_code == 200


def csv(texto):
    return SimpleUploadedFile("conductores.csv", texto.encode("utf-8"), content_type="text/csv")


@pytest.mark.django_db
class TestImportarConductores:
    ENCABEZADO = "nombre;correo;rut;celular;clase de licencia;vencimiento licencia\n"

    def test_crea_todo_sin_passwords(self, api, empresa):
        vence = (timezone.localdate() + timedelta(days=300)).strftime("%d-%m-%Y")
        texto = self.ENCABEZADO + f"Ana Ríos;ana@x.example;12.345.678-5;9 0000 2001;a2;{vence}\n"
        texto += f"Luis Mora;luis@x.example;15000103-K;+56900002002;A3;{VENCE}\n"
        informe = api.post(IMPORTAR, {"archivo": csv(texto)}, format="multipart").json()
        assert (informe["validas"], informe["con_errores"]) == (2, 0)
        respuesta = api.post(IMPORTAR, {"archivo": csv(texto), "confirmar": True}, format="multipart")
        assert respuesta.status_code == 201
        assert respuesta.json()["creados"] == 2
        creados = Conductor.objects.filter(usuario__empresa=empresa).select_related("usuario")
        assert {c.usuario.email for c in creados} == {"ana@x.example", "luis@x.example"}
        assert not any(c.usuario.has_usable_password() for c in creados)

    def test_repetidos_en_el_archivo_y_existentes(self, api, chofer):
        texto = self.ENCABEZADO + f"Ana;ana@x.example;12345678-5;+56900002001;A2;{VENCE}\n"
        texto += f"Otra;ANA@x.example;{chofer.rut};+56900002002;A2;{VENCE}\n"
        informe = api.post(IMPORTAR, {"archivo": csv(texto), "confirmar": True}, format="multipart")
        assert informe.status_code == 400
        errores = informe.json()["filas"][1]["errores"]
        assert errores["email"] == ["Repetido en el archivo (línea 2)."]
        assert errores["rut"] == ["Este RUT ya está registrado."]
        assert Conductor.objects.count() == 1

    def test_faltan_columnas(self, api):
        respuesta = api.post(
            IMPORTAR, {"archivo": csv("nombre,email\nAna,a@x.example\n")}, format="multipart"
        )
        assert (
            "Faltan columnas: rut, telefono, licencia_clase, licencia_vence" in respuesta.json()["archivo"][0]
        )


@pytest.mark.django_db
def test_un_despachador_con_temporal_tambien_queda_bloqueado(empresa, administrador):
    """El bloqueo es del backend, no de la app: aplica a cualquier usuario con la temporal pendiente."""
    despachador = UsuarioFactory(empresa=empresa, rol=Rol.DESPACHADOR)
    credenciales.asignar_password_temporal(despachador, por=administrador)
    # Con un access real: force_authenticate se saltaría la autenticación.
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(despachador)}")
    respuesta = cliente.get(reverse("viaje-list"))
    assert (respuesta.status_code, respuesta.json()["code"]) == (403, "cambio_password_requerido")
