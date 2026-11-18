"""DC-68 (CC-19): configuración de la empresa en el panel, solo el administrador, con rangos y auditoría."""

import pytest
from django.urls import reverse

from apps.auditoria.models import Auditoria
from apps.cuentas.configuracion import RANGOS
from apps.cuentas.tests.fabricas import UsuarioFactory

URL = reverse("configuracion-empresa")
pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(panel, administrador):
    panel.force_authenticate(administrador)
    return panel


def test_lee_y_cambia_con_auditoria_de_los_valores_anteriores(admin, administrador, empresa):
    datos = admin.get(URL).data
    assert (datos["telefono_central"], datos["confirmacion_antes_horas"]) == ("", 24)
    respuesta = admin.patch(
        URL,
        {
            "telefono_central": "+56 2 2999 0000",
            "whatsapp_central": "+56999900000",
            "confirmacion_antes_horas": 12,
        },
        format="json",
    )
    assert respuesta.status_code == 200, respuesta.data
    assert (respuesta.data["telefono_central"], respuesta.data["confirmacion_antes_horas"]) == (
        "+56229990000",
        12,
    )
    empresa.configuracion.refresh_from_db()
    assert empresa.configuracion.whatsapp_central == "+56999900000"
    registro = Auditoria.objects.get(accion="EDITAR_CONFIGURACION")
    assert (registro.usuario, registro.entidad, registro.entidad_id) == (administrador, "EMPRESA", empresa.pk)
    assert registro.datos_previos == {
        "telefono_central": "",
        "whatsapp_central": "",
        "confirmacion_antes_horas": 24,
    }
    # Sin cambios no se audita; vaciar un número quita el botón.
    admin.patch(URL, {"confirmacion_antes_horas": 12}, format="json")
    assert Auditoria.objects.filter(accion="EDITAR_CONFIGURACION").count() == 1
    assert admin.patch(URL, {"whatsapp_central": ""}, format="json").data["whatsapp_central"] == ""


@pytest.mark.parametrize("campo", list(RANGOS))
def test_minimos_y_maximos(admin, campo):
    minimo, maximo = RANGOS[campo]
    # Plazo corto al mínimo para que 1 h siga siendo mayor (la regla cruzada tiene su prueba).
    admin.patch(URL, {"confirmacion_plazo_corto_min": 10}, format="json")
    for valor in (minimo - 1, maximo + 1):
        assert admin.patch(URL, {campo: valor}, format="json").status_code == 400
    for valor in (minimo, maximo):
        assert admin.patch(URL, {campo: valor}, format="json").status_code == 200


@pytest.mark.parametrize(
    ("datos", "codigo"),
    [
        ({"confirmacion_antes_horas": 1, "confirmacion_plazo_corto_min": 60}, 400),
        ({"confirmacion_antes_horas": 1, "confirmacion_plazo_corto_min": 59}, 200),
        ({"confirmacion_antes_horas": 2, "confirmacion_plazo_corto_min": 119}, 200),
    ],
)
def test_plazo_corto_menor_que_el_plazo_normal(admin, datos, codigo):
    respuesta = admin.patch(URL, datos, format="json")
    assert respuesta.status_code == codigo, respuesta.data
    if codigo == 400:
        assert "60 min" in str(respuesta.data["confirmacion_plazo_corto_min"][0])


def test_plazo_corto_se_compara_con_el_valor_guardado(admin):
    # Se cambia solo uno de los dos: el otro se toma de la configuración guardada (24 h por defecto).
    assert admin.patch(URL, {"confirmacion_plazo_corto_min": 240}, format="json").status_code == 200
    respuesta = admin.patch(URL, {"confirmacion_antes_horas": 4}, format="json")
    assert respuesta.status_code == 400 and "confirmacion_plazo_corto_min" in respuesta.data


def test_telefono_invalido(admin):
    respuesta = admin.patch(URL, {"telefono_central": "123"}, format="json")
    assert respuesta.status_code == 400 and "telefono_central" in respuesta.data


def test_el_modulo_de_cuentas_no_se_cambia_aqui(admin, empresa):
    modulo = empresa.modulo_cuentas
    admin.patch(URL, {"modulo_cuentas": not modulo}, format="json")
    empresa.refresh_from_db()
    assert empresa.modulo_cuentas == modulo
    assert "modulo_cuentas" not in admin.get(URL).data


@pytest.mark.parametrize("rol", ["DESPACHADOR", "CONDUCTOR", "PASAJERO", "CONVENIO"])
def test_solo_el_administrador(panel, empresa, rol):
    panel.force_authenticate(UsuarioFactory(empresa=empresa, rol=rol))
    assert panel.get(URL).status_code == 403
    assert panel.patch(URL, {"confirmacion_antes_horas": 5}, format="json").status_code == 403


def test_cada_administrador_ve_su_empresa(admin, otra_empresa):
    otra_empresa.configuracion.telefono_central = "+56211110000"
    otra_empresa.configuracion.save()
    assert admin.get(URL).data["telefono_central"] == ""
