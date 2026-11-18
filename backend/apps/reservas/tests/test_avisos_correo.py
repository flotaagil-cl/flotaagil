"""HU-56 (CC-22, DC-55): avisos y encuesta por correo para las empresas sin el módulo de cuentas. CP-52."""

import re

import pytest
from django.core import mail
from django.urls import reverse

from apps.cuentas.tests.fabricas import EmpresaFactory
from apps.reservas import avisos_correo, tareas
from apps.reservas.models import Calificacion, EstadoViaje
from apps.reservas.tests.fabricas import ConductorFactory, VehiculoFactory, ViajeFactory
from apps.reservas.tipos_aviso import (
    AVISO_CONDUCTOR,
    AVISO_CONFIRMACION,
    AVISO_EN_CAMINO,
    AVISO_EN_ZONA,
    AVISO_ENCUESTA,
)

E = EstadoViaje


@pytest.fixture
def base(db):
    return EmpresaFactory(modulo_cuentas=False)


def viaje_base(empresa, **cambios):
    datos = {
        "empresa": empresa,
        "contacto_correo": "paula@correo.example",
        "conductor": ConductorFactory(usuario__empresa=empresa),
        "vehiculo": VehiculoFactory(empresa=empresa, color="gris"),
    }
    datos.update(cambios)
    return ViajeFactory(**datos)


@pytest.mark.django_db
class TestAvisosPorCorreo:
    @pytest.mark.parametrize(
        ("tipo", "asunto"),
        [(AVISO_CONFIRMACION, "confirmada"), (AVISO_ENCUESTA, "¿Cómo fue tu viaje")],
    )
    def test_sin_modulo_van_por_correo_y_no_por_whatsapp(self, base, sin_whatsapp, tipo, asunto):
        viaje = viaje_base(base, estado=E.FINALIZADO)
        tareas.enviar_aviso.delay(viaje.pk, tipo)
        assert sin_whatsapp.enviados == []
        assert mail.outbox[-1].to == ["paula@correo.example"]
        assert asunto in mail.outbox[-1].subject

    def test_conductor_asignado_con_patente_modelo_y_color(self, base, sin_whatsapp):
        viaje = viaje_base(base, estado=E.ACEPTADO)
        tareas.enviar_aviso.delay(viaje.pk, AVISO_CONDUCTOR)
        cuerpo = mail.outbox[-1].body
        assert (
            viaje.vehiculo.patente in cuerpo
            and "color gris" in cuerpo
            and viaje.vehiculo.marca_modelo in cuerpo
        )

    @pytest.mark.parametrize("tipo", [AVISO_EN_CAMINO, AVISO_EN_ZONA])
    def test_en_camino_y_en_zona_no_se_envian(self, base, sin_whatsapp, tipo):
        tareas.enviar_aviso.delay(viaje_base(base, estado=E.EN_CAMINO).pk, tipo)
        assert not mail.outbox and sin_whatsapp.enviados == []

    def test_cancelar_desde_el_panel_avisa_por_correo(
        self, base, panel, django_capture_on_commit_callbacks, sin_whatsapp
    ):
        from apps.cuentas.tests.fabricas import UsuarioFactory

        viaje = ViajeFactory(empresa=base, estado=E.SOLICITADO, contacto_correo="paula@correo.example")
        panel.force_authenticate(UsuarioFactory(empresa=base, rol="DESPACHADOR"))
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = panel.post(
                reverse("viaje-cancelar", args=[viaje.pk]), {"motivo": "Sin flota"}, format="json"
            )
        assert respuesta.status_code == 200
        assert "cancelada" in mail.outbox[-1].subject and "Sin flota" in mail.outbox[-1].body

    def test_con_el_modulo_y_sin_correo_ni_cuenta_no_sale_nada(self, sin_whatsapp, db):
        """CC-19 (HU-67, CP-57): ya no hay WhatsApp; una reserva del panel sin correo no recibe avisos."""
        con_modulo = EmpresaFactory(modulo_cuentas=True)
        viaje = ViajeFactory(empresa=con_modulo, estado=E.SOLICITADO)
        tareas.enviar_aviso.delay(viaje.pk, AVISO_CONFIRMACION)
        tareas.enviar_aviso.delay(viaje.pk, avisos_correo.AVISO_CANCELACION)
        assert sin_whatsapp.enviados == [] and not mail.outbox


@pytest.mark.django_db
class TestEncuestaPorCorreo:
    def enlace(self, viaje):
        tareas.enviar_aviso.delay(viaje.pk, AVISO_ENCUESTA)
        return re.search(r"/encuesta/(\S+)", mail.outbox[-1].body).group(1)

    def calificar(self, cliente, empresa, token, puntaje=5):
        return cliente.post(
            reverse("portal-encuesta", args=[empresa.slug]),
            {"token": token, "puntaje": puntaje},
            format="json",
        )

    def test_registra_la_calificacion_una_vez(self, cliente, base, sin_whatsapp):
        viaje = viaje_base(base, estado=E.FINALIZADO)
        token = self.enlace(viaje)
        assert self.calificar(cliente, base, token, 4).status_code == 201
        assert Calificacion.objects.get(viaje=viaje).puntaje == 4
        assert self.calificar(cliente, base, token, 1).status_code == 409

    def test_enlace_alterado_o_de_otra_empresa(self, cliente, base, sin_whatsapp):
        token = self.enlace(viaje_base(base, estado=E.FINALIZADO))
        assert self.calificar(cliente, base, token[:-2] + "xx").status_code == 400
        assert self.calificar(cliente, EmpresaFactory(modulo_cuentas=False), token).status_code == 400

    def test_puntaje_fuera_de_rango(self, cliente, base, sin_whatsapp):
        token = self.enlace(viaje_base(base, estado=E.FINALIZADO))
        assert self.calificar(cliente, base, token, 6).status_code == 400
