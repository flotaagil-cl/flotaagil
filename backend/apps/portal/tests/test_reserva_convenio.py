"""HU-54 (CC-22): reserva pública con el RUT de un convenio aprobado. CP-50 y CP-51."""

import re

import pytest
from django.core import mail
from django.urls import reverse

from apps.convenios.models import Convenio, EstadoConvenio
from apps.cuentas.tests.fabricas import EmpresaFactory
from apps.reservas.models import EstadoViaje, Viaje

from .test_reserva_publica import reservar

E = EstadoViaje
EMPRESA_CLIENTE = {
    "es_empresa": True,
    "empresa_razon_social": "Minera Sintética S.A.",
    "empresa_rut": "76543210-3",
    "empresa_contacto": "Ana Contacto",
}


@pytest.fixture
def base(db):
    return EmpresaFactory(modulo_cuentas=False)


@pytest.fixture
def convenio(base):
    return Convenio.objects.create(
        empresa=base,
        cliente_nombre="Minera Sintética S.A.",
        cliente_rut="76543210-3",
        estado=EstadoConvenio.APROBADO,
        contacto_correo="contacto@minera.example",
        correos_autorizados=["@minera.example", "pedro@otra.example"],
    )


def decidir(cliente, empresa, token, decision):
    return cliente.post(
        reverse("portal-reserva-autorizar", args=[empresa.slug]),
        {"token": token, "decision": decision},
        format="json",
    )


def token_de_autorizacion() -> str:
    return re.search(r"/autorizar/(\S+)", mail.outbox[-1].body).group(1)


@pytest.mark.django_db
class TestReservaConvenio:
    @pytest.mark.parametrize("correo", ["paula@minera.example", "Pedro@Otra.example"])
    def test_correo_autorizado_se_asocia_al_convenio(
        self, cliente, base, convenio, correo, django_capture_on_commit_callbacks
    ):
        respuesta = reservar(
            cliente, base, django_capture_on_commit_callbacks, correo=correo, **EMPRESA_CLIENTE
        )
        assert respuesta.status_code == 201, respuesta.data
        viaje = Viaje.objects.get()
        assert (viaje.convenio, viaje.confirma_convenio) == (convenio, False)
        assert mail.outbox[-1].to == [correo.lower()]  # el pasajero confirma con su enlace, como siempre
        assert "/confirmar/" in mail.outbox[-1].body and "convenio" not in mail.outbox[-1].subject.lower()

    def test_correo_no_autorizado_lo_autoriza_el_contacto(
        self, cliente, base, convenio, django_capture_on_commit_callbacks
    ):
        respuesta = reservar(
            cliente, base, django_capture_on_commit_callbacks, correo="x@gmail.example", **EMPRESA_CLIENTE
        )
        assert respuesta.data["confirma_convenio"] is True
        viaje = Viaje.objects.get()
        assert (viaje.convenio, viaje.confirma_convenio, viaje.estado) == (
            convenio,
            True,
            E.PENDIENTE_CONFIRMACION,
        )
        assert mail.outbox[-1].to == ["contacto@minera.example"]
        token = token_de_autorizacion()
        with django_capture_on_commit_callbacks(execute=True):
            assert decidir(cliente, base, token, "autorizar").status_code == 200
        viaje.refresh_from_db()
        assert viaje.estado == E.SOLICITADO
        assert decidir(cliente, base, token, "rechazar").status_code == 409

    def test_el_contacto_rechaza_y_se_avisa_al_solicitante(
        self, cliente, base, convenio, django_capture_on_commit_callbacks
    ):
        reservar(
            cliente, base, django_capture_on_commit_callbacks, correo="x@gmail.example", **EMPRESA_CLIENTE
        )
        with django_capture_on_commit_callbacks(execute=True):
            assert decidir(cliente, base, token_de_autorizacion(), "rechazar").status_code == 200
        viaje = Viaje.objects.get()
        assert viaje.estado == E.CANCELADO
        assert mail.outbox[-1].to == ["x@gmail.example"]
        assert "no autorizó" in mail.outbox[-1].body

    def test_el_pasajero_no_confirma_si_debe_autorizar_el_convenio(
        self, cliente, base, convenio, django_capture_on_commit_callbacks
    ):
        reservar(
            cliente, base, django_capture_on_commit_callbacks, correo="x@gmail.example", **EMPRESA_CLIENTE
        )
        token = token_de_autorizacion()
        # El enlace de autorizar no sirve para confirmar como pasajero (otra sal).
        respuesta = cliente.post(
            reverse("portal-reserva-confirmar", args=[base.slug]), {"token": token}, format="json"
        )
        assert respuesta.status_code == 400

    @pytest.mark.parametrize("estado", [EstadoConvenio.EN_REVISION, EstadoConvenio.INACTIVO])
    def test_convenio_no_aprobado_se_cobra_como_particular(
        self, cliente, base, convenio, estado, django_capture_on_commit_callbacks
    ):
        Convenio.objects.filter(pk=convenio.pk).update(estado=estado)
        reservar(
            cliente,
            base,
            django_capture_on_commit_callbacks,
            correo="paula@minera.example",
            **EMPRESA_CLIENTE,
        )
        assert Viaje.objects.get().convenio is None

    def test_decision_invalida(self, cliente, base, convenio, django_capture_on_commit_callbacks):
        reservar(
            cliente, base, django_capture_on_commit_callbacks, correo="x@gmail.example", **EMPRESA_CLIENTE
        )
        assert decidir(cliente, base, token_de_autorizacion(), "quizas").status_code == 400
