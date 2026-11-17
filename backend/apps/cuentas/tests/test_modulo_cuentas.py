"""HU-50 (CC-22, DC-51): módulo de cuentas por empresa. CP-46."""

import pytest
from django.contrib.admin.sites import site
from django.test import RequestFactory
from django.urls import reverse

from apps.cuentas.models import Empresa, Rol
from apps.cuentas.tests.fabricas import EmpresaFactory, UsuarioFactory

CLAVE = "Clave-Sintetica-2026"


@pytest.fixture
def base(db):
    return EmpresaFactory(modulo_cuentas=False)


def test_por_defecto_sin_modulo(db):
    empresa = Empresa.objects.create(rut="76000123-4", razon_social="Nueva SpA", slug="nueva")
    empresa.refresh_from_db()
    assert empresa.modulo_cuentas is False


@pytest.mark.parametrize(
    "nombre",
    ["portal-crear-cuenta", "portal-registro-empresa", "portal-cuenta-estado", "portal-cuenta-reenviar"],
)
def test_sin_modulo_los_formularios_de_cuenta_no_existen(cliente, base, nombre):
    assert cliente.post(reverse(nombre, args=[base.slug]), {}, format="json").status_code == 404


def test_el_portal_informa_el_modo(cliente, base):
    con = EmpresaFactory(modulo_cuentas=True)
    assert cliente.get(reverse("portal-empresa", args=[base.slug])).data["modulo_cuentas"] is False
    assert cliente.get(reverse("portal-empresa", args=[con.slug])).data["modulo_cuentas"] is True


@pytest.mark.parametrize("rol", [Rol.PASAJERO, Rol.CONVENIO])
def test_sin_modulo_no_ingresan_los_clientes(panel, base, rol):
    usuario = UsuarioFactory(empresa=base, rol=rol)
    usuario.set_password(CLAVE)
    usuario.save()
    respuesta = panel.post(reverse("auth-token"), {"email": usuario.email, "password": CLAVE}, format="json")
    assert respuesta.status_code == 403
    assert respuesta.data["code"] == "modulo_no_disponible" or "modulo_no_disponible" in str(respuesta.data)


@pytest.mark.parametrize(("rol", "ruta"), [(Rol.PASAJERO, "mi-cuenta"), (Rol.CONVENIO, "mi-convenio")])
def test_sin_modulo_los_endpoints_de_cuenta_responden_404(panel, base, rol, ruta):
    panel.force_authenticate(UsuarioFactory(empresa=base, rol=rol))
    assert panel.get(reverse(ruta)).status_code == 404


def test_el_panel_sigue_funcionando_sin_modulo(panel, base):
    usuario = UsuarioFactory(empresa=base, rol=Rol.DESPACHADOR)
    usuario.set_password(CLAVE)
    usuario.save()
    respuesta = panel.post(reverse("auth-token"), {"email": usuario.email, "password": CLAVE}, format="json")
    assert respuesta.status_code == 200
    assert respuesta.data["usuario"]["empresa"]["modulo_cuentas"] is False


@pytest.mark.parametrize(("superusuario", "editable"), [(True, True), (False, False)])
def test_solo_el_superusuario_cambia_el_modulo(base, superusuario, editable):
    peticion = RequestFactory().get("/")
    peticion.user = UsuarioFactory(
        empresa=base, rol=Rol.ADMINISTRADOR, is_staff=True, is_superuser=superusuario
    )
    solo_lectura = site._registry[Empresa].get_readonly_fields(peticion, base)
    assert ("modulo_cuentas" not in solo_lectura) is editable
