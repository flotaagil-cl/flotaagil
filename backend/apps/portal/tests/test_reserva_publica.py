"""HU-51 (CC-22): reserva pública confirmada por correo. CP-47 (formulario) y CP-48 (confirmación)."""

import re
from datetime import timedelta

import pytest
from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.cuentas.tests.fabricas import EmpresaFactory
from apps.reservas import expiracion
from apps.reservas.models import EstadoViaje, HistorialEstado, Pasajero, Viaje

E = EstadoViaje


@pytest.fixture
def base(db):
    return EmpresaFactory(modulo_cuentas=False)


def datos(**cambios):
    d = {
        "nombre": "Paula Pasajera",
        "telefono": "+56900009401",
        "correo": "paula@correo.example",
        "origen_dir": "Av. Providencia 1208, Providencia",
        "destino_dir": "Plaza de Armas, Santiago",
        "recogida_en": (timezone.now() + timedelta(days=3)).isoformat(),
        "sentido": "URBANO",
        "acepta_privacidad": True,
    }
    d.update(cambios)
    return d


def reservar(cliente, empresa, capturar, **cambios):
    with capturar(execute=True):
        return cliente.post(
            reverse("portal-reserva-publica", args=[empresa.slug]), datos(**cambios), format="json"
        )


def token_del_correo() -> str:
    return re.search(r"/confirmar/(\S+)", mail.outbox[-1].body).group(1)


def confirmar(cliente, empresa, token):
    return cliente.post(
        reverse("portal-reserva-confirmar", args=[empresa.slug]), {"token": token}, format="json"
    )


@pytest.mark.django_db
class TestReservaPublica:
    def test_crea_pendiente_y_envia_el_enlace(self, cliente, base, django_capture_on_commit_callbacks):
        respuesta = reservar(cliente, base, django_capture_on_commit_callbacks)
        assert respuesta.status_code == 201, respuesta.data
        viaje = Viaje.objects.get()
        assert (viaje.estado, viaje.contacto_correo, viaje.privacidad_version) == (
            E.PENDIENTE_CONFIRMACION,
            "paula@correo.example",
            settings.AVISO_PRIVACIDAD_VERSION,
        )
        assert viaje.confirmar_hasta == viaje.recogida_en - timedelta(hours=24)
        assert Pasajero.objects.get().privacidad_aceptada_en is not None
        assert mail.outbox[-1].to == ["paula@correo.example"]
        assert "convenio" not in mail.outbox[-1].body.lower()

    def test_con_menos_de_un_dia_el_plazo_es_de_60_min(
        self, cliente, base, django_capture_on_commit_callbacks
    ):
        antes = timezone.now()
        recogida = (antes + timedelta(hours=5)).isoformat()
        reservar(cliente, base, django_capture_on_commit_callbacks, recogida_en=recogida)
        plazo = Viaje.objects.get().confirmar_hasta - antes
        assert timedelta(minutes=59) < plazo < timedelta(minutes=61)

    def test_empresa_sin_convenio_guarda_sus_datos_e_invita(
        self, cliente, base, django_capture_on_commit_callbacks
    ):
        empresa = {"es_empresa": True, "empresa_razon_social": "Minera Sintética S.A."}
        empresa |= {"empresa_rut": "76.543.210-3", "empresa_contacto": "Ana Contacto"}
        assert reservar(cliente, base, django_capture_on_commit_callbacks, **empresa).status_code == 201
        viaje = Viaje.objects.get()
        assert (viaje.empresa_cliente_rut, viaje.convenio) == ("76543210-3", None)
        assert f"/solicitar/{base.slug}/convenio" in mail.outbox[-1].body

    @pytest.mark.parametrize(
        ("cambios", "campo"),
        [
            ({"acepta_privacidad": False}, "acepta_privacidad"),
            ({"correo": "no-es-correo"}, "correo"),
            (
                {
                    "es_empresa": True,
                    "empresa_razon_social": "X",
                    "empresa_rut": "1-1",
                    "empresa_contacto": "Y",
                },
                "empresa_rut",
            ),
            ({"es_empresa": True}, "empresa_razon_social"),
        ],
    )
    def test_validaciones(self, cliente, base, django_capture_on_commit_callbacks, cambios, campo):
        respuesta = reservar(cliente, base, django_capture_on_commit_callbacks, **cambios)
        assert respuesta.status_code == 400
        assert campo in respuesta.data
        assert not Viaje.objects.exists()

    def test_campo_trampa_no_crea_nada(self, cliente, base, django_capture_on_commit_callbacks):
        respuesta = reservar(
            cliente, base, django_capture_on_commit_callbacks, sitio_web="http://spam.example"
        )
        assert respuesta.status_code == 201
        assert not Viaje.objects.exists() and not mail.outbox

    def test_limite_por_correo(self, cliente, base, django_capture_on_commit_callbacks):
        # DC-59 (HU-60): parámetro de la empresa (5 por hora por defecto).
        base.configuracion.reserva_publica_max_correo_hora = 2
        base.configuracion.save()
        for i in range(2):
            assert (
                reservar(
                    cliente, base, django_capture_on_commit_callbacks, telefono=f"+5690000940{i}"
                ).status_code
                == 201
            )
        respuesta = reservar(cliente, base, django_capture_on_commit_callbacks, telefono="+56900009409")
        assert respuesta.status_code == 429
        assert respuesta.data["code"] == "limite_correo"

    def test_limite_por_ip(self, cliente, base, django_capture_on_commit_callbacks):
        base.configuracion.reserva_publica_max_ip_hora = 2
        base.configuracion.save()
        for i in range(2):
            correo = f"p{i}@correo.example"
            assert (
                reservar(cliente, base, django_capture_on_commit_callbacks, correo=correo).status_code == 201
            )
        respuesta = reservar(cliente, base, django_capture_on_commit_callbacks, correo="p9@correo.example")
        assert (respuesta.status_code, respuesta.data["code"]) == (429, "limite_ip")

    def test_valores_por_defecto(self, base):
        config = base.configuracion
        assert (
            config.reserva_publica_max_ip_hora,
            config.reserva_publica_max_correo_hora,
            config.reserva_publica_max_convenio_hora,
            config.cierre_no_confirmada_horas,
        ) == (20, 5, 30, 2)

    def test_con_el_modulo_tambien_se_reserva_sin_cuenta(self, cliente, django_capture_on_commit_callbacks):
        # HU-60: «Reservar sin cuenta» también en las empresas con el módulo; los avisos van por correo.
        con_modulo = EmpresaFactory(modulo_cuentas=True)
        assert reservar(cliente, con_modulo, django_capture_on_commit_callbacks).status_code == 201
        assert f"/solicitar/{con_modulo.slug}/confirmar/" in mail.outbox[-1].body


@pytest.mark.django_db
class TestConfirmar:
    def test_confirma_una_sola_vez(self, cliente, base, django_capture_on_commit_callbacks):
        reservar(cliente, base, django_capture_on_commit_callbacks)
        token = token_del_correo()
        respuesta = confirmar(cliente, base, token)
        assert respuesta.status_code == 200, respuesta.data
        viaje = Viaje.objects.get()
        assert viaje.estado == E.SOLICITADO
        assert HistorialEstado.objects.filter(
            viaje=viaje, estado_nuevo=E.SOLICITADO, actor="PASAJERO"
        ).exists()
        assert confirmar(cliente, base, token).status_code == 409

    def test_vencido(self, cliente, base, django_capture_on_commit_callbacks):
        reservar(cliente, base, django_capture_on_commit_callbacks)
        Viaje.objects.update(confirmar_hasta=timezone.now() - timedelta(minutes=1))
        assert confirmar(cliente, base, token_del_correo()).status_code == 410
        assert Viaje.objects.get().estado == E.PENDIENTE_CONFIRMACION

    def test_enlace_alterado_o_de_otra_empresa(self, cliente, base, django_capture_on_commit_callbacks):
        reservar(cliente, base, django_capture_on_commit_callbacks)
        token = token_del_correo()
        assert confirmar(cliente, base, token[:-2] + "xx").status_code == 400
        otra = EmpresaFactory(modulo_cuentas=False)
        assert confirmar(cliente, otra, token).status_code == 400

    def test_la_expiracion_de_15_min_no_la_cancela(self, cliente, base, django_capture_on_commit_callbacks):
        reservar(cliente, base, django_capture_on_commit_callbacks)
        expiracion.expirar_pendientes(ahora=timezone.now() + timedelta(hours=2))
        assert Viaje.objects.get().estado == E.PENDIENTE_CONFIRMACION
