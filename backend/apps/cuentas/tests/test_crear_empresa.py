"""DC-38: comando crear_empresa para dar de alta a un cliente nuevo."""

import re
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.test import override_settings

from apps.aeropuerto.models import Geocerca
from apps.auditoria.models import Auditoria
from apps.cuentas.models import ConfiguracionEmpresa, Empresa, Rol, Usuario

from .fabricas import EmpresaFactory, UsuarioFactory

BASE = {
    "rut": "76.543.210-3",
    "razon_social": "Taxis Sintéticos SpA",
    "slug": "taxis-sinteticos",
    "admin_email": "Admin@Taxis-Sinteticos.example",
    "admin_nombre": "Administradora Sintética",
}


def crear(**cambios):
    datos = {**BASE, "plan": Empresa._meta.get_field("plan").default, **cambios}
    salida = StringIO()
    argumentos = []
    for clave, valor in datos.items():
        if valor is True:
            argumentos.append(f"--{clave.replace('_', '-')}")
        elif valor is not None:
            argumentos += [f"--{clave.replace('_', '-')}", valor]
    call_command("crear_empresa", *argumentos, stdout=salida)
    return salida.getvalue()


@pytest.mark.django_db
class TestCrearEmpresa:
    @override_settings(DEBUG=False)
    def test_crea_todo_y_muestra_la_temporal_una_vez(self):
        salida = crear()
        empresa = Empresa.objects.get(slug="taxis-sinteticos")
        assert empresa.rut == "76543210-3"
        assert ConfiguracionEmpresa.objects.filter(empresa=empresa).exists()
        admin = Usuario.objects.get(empresa=empresa)
        assert (admin.rol, admin.email, admin.debe_cambiar_password) == (
            Rol.ADMINISTRADOR,
            "admin@taxis-sinteticos.example",
            True,
        )
        assert admin.password_temporal_vence is not None
        temporal = re.search(r"se muestra una sola vez\): (\S+)", salida).group(1)
        assert admin.check_password(temporal)
        assert not Geocerca.objects.filter(empresa=empresa).exists()
        registro = Auditoria.objects.get(accion="ALTA_EMPRESA")
        assert (registro.usuario, registro.empresa_id) == (None, empresa.pk)
        assert temporal not in str(registro.datos_previos)

    def test_con_geocerca_scl(self):
        crear(geocerca_scl=True)
        assert Geocerca.objects.filter(empresa__slug="taxis-sinteticos").count() == 1

    @pytest.mark.parametrize(
        ("cambios", "mensaje"),
        [
            ({"rut": "76543210-0"}, "RUT"),
            ({"slug": "Con Espacios"}, "slug"),
            ({"admin_email": "no-es-correo"}, "correo"),
            ({"razon_social": "  "}, "razón social"),
        ],
    )
    def test_datos_invalidos_no_crean_nada(self, cambios, mensaje):
        with pytest.raises(CommandError, match=mensaje):
            crear(**cambios)
        assert not Empresa.objects.filter(slug="taxis-sinteticos").exists()
        assert not Usuario.objects.filter(email="admin@taxis-sinteticos.example").exists()

    @pytest.mark.parametrize("repetido", ["rut", "slug", "correo"])
    def test_repetidos_no_crean_nada(self, repetido):
        if repetido == "rut":
            EmpresaFactory(rut="76543210-3")
        elif repetido == "slug":
            EmpresaFactory(slug="taxis-sinteticos")
        else:
            UsuarioFactory(email="admin@taxis-sinteticos.example")
        antes = (Empresa.objects.count(), Usuario.objects.count())
        with pytest.raises(CommandError, match="No se creó nada"):
            crear()
        assert (Empresa.objects.count(), Usuario.objects.count()) == antes

    def test_plan_fuera_del_dominio(self):
        with pytest.raises(CommandError):
            crear(plan="ORO")
