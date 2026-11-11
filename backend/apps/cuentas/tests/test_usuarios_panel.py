"""HU-36 (CC-17, DC-37): usuarios del panel."""

import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.auditoria.models import Auditoria, Entidad
from apps.cuentas.models import Rol, Usuario

from .fabricas import CLAVE_PRUEBA, UsuarioFactory

LISTA = reverse("usuario-panel-list")
ORIGEN = "http://localhost:5173"


def detalle(usuario):
    return reverse("usuario-panel-detail", args=[usuario.pk])


def accion(nombre, usuario):
    return reverse(f"usuario-panel-{nombre}", args=[usuario.pk])


@pytest.fixture
def api(cliente, administrador):
    cliente.force_authenticate(administrador)
    return cliente


@pytest.mark.django_db
class TestListado:
    def test_solo_administradores_y_despachadores_de_la_empresa(
        self, api, administrador, despachador, empresa, otra_empresa
    ):
        for rol in (Rol.CONDUCTOR, Rol.CONVENIO, Rol.PASAJERO):
            UsuarioFactory(empresa=empresa, rol=rol)
        UsuarioFactory(empresa=otra_empresa, rol=Rol.DESPACHADOR)
        ids = {u["id"] for u in api.get(LISTA).json()["results"]}
        assert ids == {administrador.pk, despachador.pk}

    def test_despachador_403_y_otra_empresa_404(self, cliente, despachador, api, otra_empresa):
        ajeno = UsuarioFactory(empresa=otra_empresa, rol=Rol.DESPACHADOR)
        assert api.get(detalle(ajeno)).status_code == 404
        assert api.post(accion("desactivar", ajeno)).status_code == 404
        cliente.force_authenticate(despachador)
        assert cliente.get(LISTA).status_code == 403

    def test_un_conductor_no_se_administra_aqui(self, api, empresa):
        conductor = UsuarioFactory(empresa=empresa, rol=Rol.CONDUCTOR)
        assert api.get(detalle(conductor)).status_code == 404


@pytest.mark.django_db
class TestCrear:
    def test_crea_con_temporal_que_obliga_a_cambiarla(self, api, administrador, empresa):
        respuesta = api.post(
            LISTA,
            {"nombre": "Diego Sintético", "email": "Diego@Ejemplo.example", "rol": "DESPACHADOR"},
            format="json",
        )
        assert respuesta.status_code == 201, respuesta.data
        assert respuesta["Cache-Control"] == "no-store"
        usuario = Usuario.objects.get(pk=respuesta.data["id"])
        assert (usuario.email, usuario.empresa, usuario.rol, usuario.debe_cambiar_password) == (
            "diego@ejemplo.example",
            empresa,
            Rol.DESPACHADOR,
            True,
        )
        assert usuario.check_password(respuesta.data["password_temporal"])
        assert respuesta.data["acceso"] == "TEMPORAL"
        acciones = list(
            Auditoria.objects.filter(entidad=Entidad.USUARIO, entidad_id=usuario.pk).values_list(
                "accion", flat=True
            )
        )
        assert sorted(acciones) == ["CREAR", "GENERAR_PASSWORD"]
        assert respuesta.data["password_temporal"] not in str(list(Auditoria.objects.values()))
        # entra y debe cambiarla
        web = APIClient(HTTP_ORIGIN=ORIGEN)
        sesion = web.post(
            reverse("auth-token"),
            {"email": usuario.email, "password": respuesta.data["password_temporal"]},
            format="json",
        )
        web.credentials(HTTP_AUTHORIZATION=f"Bearer {sesion.data['access']}")
        assert web.get(reverse("viaje-list")).data["code"] == "cambio_password_requerido"
        assert usuario.password_temporal_vence is not None

    def test_correo_usado_mensaje_claro(self, api, empresa, otra_empresa):
        UsuarioFactory(empresa=otra_empresa, email="usado@ejemplo.example")
        respuesta = api.post(
            LISTA, {"nombre": "X", "email": "usado@ejemplo.example", "rol": "ADMINISTRADOR"}, format="json"
        )
        assert respuesta.status_code == 400
        assert "único en todo el sistema" in respuesta.data["email"][0]

    @pytest.mark.parametrize("rol", ["CONDUCTOR", "CONVENIO", "PASAJERO", "OTRO"])
    def test_solo_roles_del_panel(self, api, rol):
        assert (
            api.post(
                LISTA, {"nombre": "X", "email": "x@ejemplo.example", "rol": rol}, format="json"
            ).status_code
            == 400
        )


@pytest.mark.django_db
class TestEditar:
    def test_edita_nombre_y_rol_y_audita(self, api, despachador):
        respuesta = api.patch(
            detalle(despachador), {"nombre": "Nuevo Nombre", "rol": "ADMINISTRADOR"}, format="json"
        )
        assert (respuesta.data["nombre"], respuesta.data["rol"]) == ("Nuevo Nombre", "ADMINISTRADOR")
        registro = Auditoria.objects.get(entidad_id=despachador.pk, accion="EDITAR")
        assert registro.datos_previos["rol"] == "DESPACHADOR"

    def test_cambiar_el_rol_cierra_sus_sesiones(self, api, despachador):
        web = APIClient(HTTP_ORIGIN=ORIGEN)
        web.post(reverse("auth-token"), {"email": despachador.email, "password": CLAVE_PRUEBA}, format="json")
        api.patch(detalle(despachador), {"rol": "ADMINISTRADOR"}, format="json")
        assert web.post(reverse("auth-refresh")).status_code == 401

    def test_no_se_quita_el_rol_a_si_mismo(self, api, administrador, empresa):
        UsuarioFactory(empresa=empresa, rol=Rol.ADMINISTRADOR)
        respuesta = api.patch(detalle(administrador), {"rol": "DESPACHADOR"}, format="json")
        assert (respuesta.status_code, respuesta.data["code"]) == (409, "propio_rol")

    def test_puede_cambiar_su_nombre(self, api, administrador):
        assert api.patch(detalle(administrador), {"nombre": "Otro"}, format="json").status_code == 200

    def test_no_deja_a_la_empresa_sin_administrador(self, cliente, empresa):
        """Un segundo administrador inactivo no cuenta: el único activo no puede pasar a despachador."""
        unico = UsuarioFactory(empresa=empresa, rol=Rol.ADMINISTRADOR)
        otro = UsuarioFactory(empresa=empresa, rol=Rol.ADMINISTRADOR, activo=False)
        cliente.force_authenticate(otro)
        respuesta = cliente.patch(detalle(unico), {"rol": "DESPACHADOR"}, format="json")
        assert (respuesta.status_code, respuesta.data["code"]) == (409, "ultimo_administrador")


@pytest.mark.django_db
class TestDesactivar:
    def test_revoca_sus_sesiones_al_instante(self, api, despachador):
        web = APIClient(HTTP_ORIGIN=ORIGEN)
        sesion = web.post(
            reverse("auth-token"), {"email": despachador.email, "password": CLAVE_PRUEBA}, format="json"
        )
        web.credentials(HTTP_AUTHORIZATION=f"Bearer {sesion.data['access']}")
        assert web.get(reverse("viaje-list")).status_code == 200
        assert api.post(accion("desactivar", despachador)).data["activo"] is False
        assert web.get(reverse("viaje-list")).status_code == 401
        assert web.post(reverse("auth-refresh")).status_code == 401
        assert Auditoria.objects.filter(entidad_id=despachador.pk, accion="DESHABILITAR").exists()

    def test_activar(self, api, despachador):
        api.post(accion("desactivar", despachador))
        assert api.post(accion("activar", despachador)).data["activo"] is True

    def test_no_se_desactiva_a_si_mismo(self, api, administrador, empresa):
        UsuarioFactory(empresa=empresa, rol=Rol.ADMINISTRADOR)
        respuesta = api.post(accion("desactivar", administrador))
        assert (respuesta.status_code, respuesta.data["code"]) == (409, "propia_cuenta")

    def test_ultimo_administrador_activo(self, api, empresa):
        segundo = UsuarioFactory(empresa=empresa, rol=Rol.ADMINISTRADOR)
        assert api.post(accion("desactivar", segundo)).status_code == 200
        # ahora el administrador de la sesión es el único: otro no podría desactivarlo
        assert Usuario.objects.filter(empresa=empresa, rol=Rol.ADMINISTRADOR, activo=True).count() == 1


@pytest.mark.django_db
class TestRestablecer:
    def test_temporal_dc14(self, api, despachador):
        respuesta = api.post(accion("password", despachador))
        assert respuesta.status_code == 201
        assert respuesta["Cache-Control"] == "no-store"
        despachador.refresh_from_db()
        assert despachador.debe_cambiar_password is True
        assert despachador.check_password(respuesta.data["password_temporal"])
        assert Auditoria.objects.filter(entidad_id=despachador.pk, accion="RESTABLECER_PASSWORD").exists()

    def test_bloqueo_tras_5_intentos_se_levanta_al_restablecer(self, api, despachador):
        web = APIClient(HTTP_ORIGIN=ORIGEN)
        for _ in range(settings.LOGIN_MAX_INTENTOS):
            web.post(reverse("auth-token"), {"email": despachador.email, "password": "mala"}, format="json")
        temporal = api.post(accion("password", despachador)).data["password_temporal"]
        assert (
            web.post(
                reverse("auth-token"), {"email": despachador.email, "password": temporal}, format="json"
            ).status_code
            == 200
        )
