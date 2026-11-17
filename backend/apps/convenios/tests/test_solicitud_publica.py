"""HU-53 (CC-22, DC-54, DC-55): solicitud pública de convenio y su revisión en el panel."""

import pytest
from django.core import mail
from django.urls import reverse

from apps.auditoria.models import Auditoria
from apps.convenios.models import Convenio, EstadoConvenio
from apps.cuentas.tests.fabricas import EmpresaFactory, UsuarioFactory


@pytest.fixture
def base(db):
    return EmpresaFactory(modulo_cuentas=False)


def datos(**cambios):
    d = {
        "cliente_nombre": "Minera Sintética S.A.",
        "cliente_rut": "76.543.210-3",
        "direccion": "Av. Apoquindo 3000, Las Condes",
        "contacto_nombre": "Ana Contacto",
        "contacto_correo": "Ana@Minera.example",
        "contacto_telefono": "+56900009601",
        "viajes_estimados_mes": 40,
        "correos_autorizados": ["@minera.example", "Pedro@Otra.example"],
    }
    d.update(cambios)
    return d


def solicitar(cliente, empresa, **cambios):
    return cliente.post(
        reverse("portal-solicitud-convenio", args=[empresa.slug]), datos(**cambios), format="json"
    )


@pytest.mark.django_db
class TestSolicitudPublica:
    def test_crea_el_convenio_en_revision_sin_cuenta(self, cliente, base):
        assert solicitar(cliente, base).status_code == 201
        convenio = Convenio.objects.get()
        assert (convenio.estado, convenio.usuario, convenio.cliente_rut) == (
            EstadoConvenio.EN_REVISION,
            None,
            "76543210-3",
        )
        assert (convenio.contacto_correo, convenio.viajes_estimados_mes) == ("ana@minera.example", 40)
        assert convenio.correos_autorizados == ["@minera.example", "pedro@otra.example"]
        assert Auditoria.objects.filter(accion="SOLICITUD_PUBLICA", entidad_id=convenio.pk).exists()

    @pytest.mark.parametrize(
        ("cambios", "campo"),
        [
            ({"cliente_rut": "1-1"}, "cliente_rut"),
            ({"contacto_correo": "x"}, "contacto_correo"),
            ({"correos_autorizados": ["no-es-correo"]}, "correos_autorizados"),
            ({"viajes_estimados_mes": 0}, "viajes_estimados_mes"),
        ],
    )
    def test_validaciones(self, cliente, base, cambios, campo):
        respuesta = solicitar(cliente, base, **cambios)
        assert respuesta.status_code == 400
        assert campo in respuesta.data

    def test_campo_trampa(self, cliente, base):
        assert solicitar(cliente, base, sitio_web="http://spam.example").status_code == 201
        assert not Convenio.objects.exists()

    def test_con_el_modulo_se_usa_el_registro_con_cuenta(self, cliente):
        assert solicitar(cliente, EmpresaFactory(modulo_cuentas=True)).status_code == 404


@pytest.mark.django_db
class TestRevisionEnElPanel:
    @pytest.mark.parametrize("rol", ["ADMINISTRADOR", "DESPACHADOR"])
    def test_aprueba_editando_los_correos_y_avisa(
        self, cliente, panel, base, rol, django_capture_on_commit_callbacks
    ):
        solicitar(cliente, base)
        convenio = Convenio.objects.get()
        usuario = UsuarioFactory(empresa=base, rol=rol)
        panel.force_authenticate(usuario)
        assert panel.get(reverse("convenio-list")).status_code == 200
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = panel.post(
                reverse("convenio-aprobar", args=[convenio.pk]),
                {"correos_autorizados": ["@minera.example"]},
                format="json",
            )
        assert respuesta.status_code == 200, respuesta.data
        convenio.refresh_from_db()
        assert (convenio.estado, convenio.correos_autorizados) == (
            EstadoConvenio.APROBADO,
            ["@minera.example"],
        )
        assert mail.outbox[-1].to == ["ana@minera.example"]
        assert "aprob" in mail.outbox[-1].subject

    def test_rechaza_con_motivo_y_avisa(self, cliente, panel, base, django_capture_on_commit_callbacks):
        solicitar(cliente, base)
        convenio = Convenio.objects.get()
        panel.force_authenticate(UsuarioFactory(empresa=base, rol="DESPACHADOR"))
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = panel.post(
                reverse("convenio-rechazar", args=[convenio.pk]),
                {"motivo": "Sin volumen suficiente"},
                format="json",
            )
        assert respuesta.status_code == 200
        assert "Sin volumen suficiente" in mail.outbox[-1].body

    def test_el_despachador_no_desactiva(self, cliente, panel, base):
        solicitar(cliente, base)
        convenio = Convenio.objects.get()
        panel.force_authenticate(UsuarioFactory(empresa=base, rol="DESPACHADOR"))
        assert panel.post(reverse("convenio-desactivar", args=[convenio.pk])).status_code == 403
