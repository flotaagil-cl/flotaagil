"""HU-35 (CC-16, DC-36): cuenta de pasajero opcional, por empresa. El invitado sigue igual."""

import re
import urllib.parse
from datetime import timedelta

import pytest
from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auditoria.models import Auditoria
from apps.cuentas.models import Rol, Usuario
from apps.reservas.models import (
    Actor,
    Canal,
    CuentaPasajero,
    EstadoViaje,
    HistorialEstado,
    Viaje,
)
from apps.reservas.tests.fabricas import ConductorFactory, PasajeroFactory, ViajeFactory

ORIGEN = "http://localhost:5173"
TELEFONO = "+56900009301"
CLAVE = "Clave-Sintetica-2026"
E = EstadoViaje


def crear_cuenta(cliente, empresa, **cambios):
    datos = {
        "nombre": "Paula Pasajera",
        "telefono": TELEFONO,
        "email": "paula@correo.example",
        "password": CLAVE,
        "acepta_privacidad": True,  # DC-44
    }
    datos.update(cambios)
    return cliente.post(reverse("portal-crear-cuenta", args=[empresa.slug]), datos, format="json")


def whatsapp(cliente, texto, desde=TELEFONO, sid="SM" + "9" * 32):
    """Lo que enviaba Twilio al webhook de entrada. HU-67 (CC-19) retiró el webhook: ya no existe la ruta."""
    datos = {"From": f"whatsapp:{desde}", "Body": texto, "MessageSid": sid}
    return cliente.post(
        "/api/whatsapp/entrante/",
        urllib.parse.urlencode(datos),
        content_type="application/x-www-form-urlencoded",
    )


def entrar(email="paula@correo.example", password=CLAVE):
    web = APIClient(HTTP_ORIGIN=ORIGEN)
    respuesta = web.post(reverse("auth-token"), {"email": email, "password": password}, format="json")
    if respuesta.status_code == 200:
        web.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return web, respuesta


def token_del_correo() -> str:
    """HU-64: el enlace de activación del último correo enviado."""
    return re.search(r"/activar/(\S+)", mail.outbox[-1].body).group(1)


def activar(cliente, empresa, token=None):
    return cliente.post(
        reverse("portal-cuenta-activar", args=[empresa.slug]),
        {"token": token or token_del_correo()},
        format="json",
    )


@pytest.fixture
def activa(cliente, empresa, sin_whatsapp, django_capture_on_commit_callbacks):
    """Cuenta creada y activada con el enlace del correo (HU-64); devuelve el cliente con sesión."""
    with django_capture_on_commit_callbacks(execute=True):
        crear_cuenta(cliente, empresa)
    assert activar(cliente, empresa).status_code == 200
    web, _ = entrar()
    return web


@pytest.mark.django_db
class TestRegistro:
    def test_queda_pendiente_y_envia_el_correo(
        self, cliente, empresa, sin_whatsapp, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = crear_cuenta(cliente, empresa)
        assert respuesta.status_code == 201, respuesta.data
        cuenta = CuentaPasajero.objects.get()
        assert (cuenta.empresa, cuenta.telefono, cuenta.confirmada_en, cuenta.pasajero) == (
            empresa,
            TELEFONO,
            None,
            None,
        )
        assert (cuenta.usuario.rol, cuenta.usuario.activo) == (Rol.PASAJERO, False)
        # DC-61: el enlace va al correo y vale 24 h; no sale ningún WhatsApp (CP-57).
        assert (mail.outbox[0].to, mail.outbox[0].subject) == (["paula@correo.example"], "Activa tu cuenta")
        assert f"/solicitar/{empresa.slug}/activar/" in mail.outbox[0].body
        assert "24 horas" in mail.outbox[0].body
        assert sin_whatsapp.enviados == []

    def test_sin_confirmar_no_entra(self, cliente, empresa, sin_whatsapp):
        crear_cuenta(cliente, empresa)
        _, respuesta = entrar()
        assert (respuesta.status_code, respuesta.data["code"]) == (401, "cuenta_sin_confirmar")

    @pytest.mark.parametrize(
        ("campo", "valor"), [("telefono", "123"), ("email", "x"), ("password", "corta"), ("nombre", " ")]
    )
    def test_valida(self, cliente, empresa, campo, valor):
        assert crear_cuenta(cliente, empresa, **{campo: valor}).status_code == 400
        assert not CuentaPasajero.objects.exists()

    def test_correo_de_otra_cuenta(self, cliente, empresa, despachador):
        respuesta = crear_cuenta(cliente, empresa, email=despachador.email)
        assert respuesta.status_code == 400
        assert "email" in respuesta.data

    def test_repetir_el_registro_pendiente_lo_reemplaza(self, cliente, empresa, sin_whatsapp):
        crear_cuenta(cliente, empresa)
        assert crear_cuenta(cliente, empresa, telefono="+56900009302").status_code == 201
        assert CuentaPasajero.objects.get().telefono == "+56900009302"

    def test_trampa(self, cliente, empresa):
        assert crear_cuenta(cliente, empresa, sitio_web="http://spam.example").status_code == 201
        assert not CuentaPasajero.objects.exists()


@pytest.mark.django_db
class TestActivacion:
    """CP-56 (HU-64, DC-61 y DC-65): activación por el enlace del correo, de 24 h."""

    def test_el_enlace_activa_sin_dar_acceso_a_viajes_de_invitado(
        self, cliente, empresa, django_capture_on_commit_callbacks
    ):
        anterior = PasajeroFactory(empresa=empresa, telefono=TELEFONO)
        ViajeFactory(empresa=empresa, pasajero=anterior)
        with django_capture_on_commit_callbacks(execute=True):
            crear_cuenta(cliente, empresa)
        respuesta = activar(cliente, empresa)
        assert (respuesta.status_code, respuesta.data["activa"]) == (200, True)
        assert respuesta.data["correo"] == "p***@correo.example"
        cuenta = CuentaPasajero.objects.get()
        assert (cuenta.pasajero, cuenta.usuario.activo, cuenta.telefono_verificado) == (anterior, True, False)
        assert Auditoria.objects.filter(accion="ACTIVAR_CUENTA", usuario=cuenta.usuario).exists()
        web, respuesta = entrar()
        assert respuesta.status_code == 200
        # DC-65: un número sin verificar no muestra los viajes de invitado de ese número.
        assert web.get(reverse("mi-cuenta-reservas")).json()["results"] == []
        # Abrir el enlace otra vez no cambia nada.
        assert activar(cliente, empresa).status_code == 200

    def test_enlace_vencido_a_las_24_horas(
        self, cliente, empresa, monkeypatch, django_capture_on_commit_callbacks
    ):
        import time

        with django_capture_on_commit_callbacks(execute=True):
            crear_cuenta(cliente, empresa)
        token = token_del_correo()
        ahora = time.time()
        monkeypatch.setattr("django.core.signing.time.time", lambda: ahora + 23.9 * 3600)
        assert activar(cliente, empresa, token).status_code == 200
        CuentaPasajero.objects.update(confirmada_en=None)
        monkeypatch.setattr("django.core.signing.time.time", lambda: ahora + 24.1 * 3600)
        respuesta = activar(cliente, empresa, token)
        assert (respuesta.status_code, respuesta.data["code"]) == (400, "enlace_vencido")

    def test_enlace_invalido_o_de_otra_empresa(
        self, cliente, empresa, otra_empresa, django_capture_on_commit_callbacks
    ):
        otra_empresa.modulo_cuentas = True
        otra_empresa.save()
        with django_capture_on_commit_callbacks(execute=True):
            crear_cuenta(cliente, empresa)
        for slug, token in ((empresa, "no-es-un-token"), (otra_empresa, token_del_correo())):
            respuesta = activar(cliente, slug, token)
            assert (respuesta.status_code, respuesta.data["code"]) == (400, "enlace_invalido")
        assert CuentaPasajero.objects.get().confirmada_en is None

    def test_reenviar_manda_un_enlace_nuevo(self, cliente, empresa, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            crear_cuenta(cliente, empresa)
            respuesta = cliente.post(
                reverse("portal-cuenta-reenviar", args=[empresa.slug]),
                {"email": "paula@correo.example", "password": CLAVE},
                format="json",
            )
        assert (respuesta.status_code, respuesta.data) == (
            200,
            {"activa": False, "correo": "p***@correo.example"},
        )
        assert len(mail.outbox) == 2
        estado = cliente.post(
            reverse("portal-cuenta-estado", args=[empresa.slug]),
            {"email": "paula@correo.example", "password": CLAVE},
            format="json",
        )
        assert estado.data == {"activa": False, "correo": "p***@correo.example"}

    def test_un_telefono_activo_tiene_una_cuenta_por_empresa(
        self, cliente, empresa, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            crear_cuenta(cliente, empresa)
        activar(cliente, empresa)
        with django_capture_on_commit_callbacks(execute=True):
            crear_cuenta(cliente, empresa, email="otra@correo.example")
        respuesta = activar(cliente, empresa)
        assert (respuesta.status_code, respuesta.data["code"]) == (409, "telefono_en_uso")
        assert CuentaPasajero.objects.filter(confirmada_en__isnull=False).count() == 1

    def test_whatsapp_ya_no_activa(self, cliente, empresa, sin_whatsapp, settings):
        settings.DEBUG = True
        crear_cuenta(cliente, empresa)
        assert whatsapp(cliente, "CONFIRMAR CUENTA").status_code == 404  # CP-57: el webhook ya no existe
        assert CuentaPasajero.objects.get().confirmada_en is None

    def test_al_activar_se_asocian_los_viajes_publicos_confirmados_con_su_correo(
        self, cliente, empresa, django_capture_on_commit_callbacks
    ):
        """DC-65 (validado): mismo correo y confirmados con el enlace del correo; nada por teléfono."""
        from apps.reservas.models import Actor as A

        def publico(correo, actor=A.PASAJERO, telefono="+56900009399"):
            viaje = ViajeFactory(
                empresa=empresa,
                canal=Canal.WEB,
                estado=E.SOLICITADO,
                contacto_correo=correo,
                pasajero=PasajeroFactory(empresa=empresa, telefono=telefono),
            )
            HistorialEstado.objects.create(
                viaje=viaje, estado_anterior=E.PENDIENTE_CONFIRMACION, estado_nuevo=E.SOLICITADO, actor=actor
            )
            return viaje

        propio = publico("PAULA@correo.example")
        por_telefono_del_despacho = publico(
            "paula@correo.example", actor=A.DESPACHADOR, telefono="+56900009398"
        )
        otro_correo = publico("otra@correo.example", telefono="+56900009397")
        mismo_telefono = publico("otra2@correo.example", telefono=TELEFONO)
        with django_capture_on_commit_callbacks(execute=True):
            crear_cuenta(cliente, empresa)
        assert activar(cliente, empresa).status_code == 200
        cuenta = CuentaPasajero.objects.get()
        propio.refresh_from_db()
        assert propio.pasajero == cuenta.pasajero
        registro = Auditoria.objects.get(accion="ACTIVAR_CUENTA")
        assert registro.datos_previos == {"viajes_asociados": [propio.pk]}
        web, _ = entrar()
        visibles = [r["id"] for r in web.get(reverse("mi-cuenta-reservas")).json()["results"]]
        assert visibles == [propio.pk]
        for ajeno in (por_telefono_del_despacho, otro_correo, mismo_telefono):
            assert web.get(reverse("mi-cuenta-reserva", args=[ajeno.pk])).status_code == 404

    def test_cuenta_verificada_antes_ve_sus_viajes_de_invitado(self, activa, empresa):
        """DC-65: las cuentas confirmadas por WhatsApp antes de CC-19 conservan lo que veían."""
        cuenta = CuentaPasajero.objects.get()
        de_invitado = ViajeFactory(empresa=empresa, pasajero=cuenta.pasajero)
        assert activa.get(reverse("mi-cuenta-reservas")).json()["results"] == []
        CuentaPasajero.objects.update(telefono_verificado=True)
        assert [r["id"] for r in activa.get(reverse("mi-cuenta-reservas")).json()["results"]] == [
            de_invitado.pk
        ]


@pytest.mark.django_db
class TestReservas:
    def solicitud(self, **cambios):
        datos = {
            "origen_dir": "Av. Providencia 1234, Providencia",
            "destino_dir": "Plaza de Armas, Santiago",
            "recogida_en": (timezone.now() + timedelta(hours=2)).isoformat(),
            "acepta_privacidad": True,
            "acepta_whatsapp": True,
        }
        datos.update(cambios)
        return datos

    def test_pide_sin_verificar_con_sus_datos(self, activa, sin_whatsapp):
        respuesta = activa.post(
            reverse("mi-cuenta-solicitudes"),
            self.solicitud(nombre="Otro", telefono="+56900000000"),
            format="json",
        )
        assert respuesta.status_code == 201, respuesta.data
        assert (respuesta.data["estado"], respuesta.data["expira_en"]) == ("SOLICITADO", None)
        viaje = Viaje.objects.get()
        assert (viaje.pasajero.telefono, viaje.canal) == (TELEFONO, Canal.WEB)
        historial = HistorialEstado.objects.get(viaje=viaje)
        assert (historial.actor, historial.usuario.email) == (Actor.PASAJERO, "paula@correo.example")

    def test_mantiene_el_limite(self, activa):
        estados = [
            activa.post(reverse("mi-cuenta-solicitudes"), self.solicitud(), format="json").status_code
            for _ in range(4)
        ]
        assert estados == [201, 201, 201, 429]

    def test_ve_su_historial(self, activa):
        activa.post(reverse("mi-cuenta-solicitudes"), self.solicitud(), format="json")
        fila = activa.get(reverse("mi-cuenta-reservas")).json()["results"][0]
        assert fila["cancelable"] is True
        assert [h["estado_nuevo"] for h in fila["historial"]] == ["SOLICITADO"]

    def test_cancela_sin_conductor(self, activa):
        activa.post(reverse("mi-cuenta-solicitudes"), self.solicitud(), format="json")
        viaje = Viaje.objects.get()
        respuesta = activa.post(reverse("mi-cuenta-cancelar", args=[viaje.pk]))
        assert respuesta.status_code == 200
        viaje.refresh_from_db()
        assert (viaje.estado, viaje.origen_cancelacion) == (E.CANCELADO, "PASAJERO")

    @pytest.mark.parametrize("estado", [E.ASIGNADO, E.ACEPTADO, E.EN_CAMINO])
    def test_con_conductor_no_cancela(self, activa, empresa, estado):
        activa.post(reverse("mi-cuenta-solicitudes"), self.solicitud(), format="json")
        viaje = Viaje.objects.get()
        Viaje.objects.filter(pk=viaje.pk).update(
            estado=estado, conductor=ConductorFactory(usuario__empresa=empresa)
        )
        respuesta = activa.post(reverse("mi-cuenta-cancelar", args=[viaje.pk]))
        assert (respuesta.status_code, respuesta.data["code"]) == (409, "con_conductor")

    def test_no_ve_ni_cancela_reservas_ajenas(self, activa, empresa):
        ajena = ViajeFactory(empresa=empresa, estado=E.SOLICITADO)
        assert activa.post(reverse("mi-cuenta-cancelar", args=[ajena.pk])).status_code == 404
        assert activa.get(reverse("mi-cuenta-reservas")).json()["results"] == []

    def test_el_panel_sigue_cerrado(self, activa):
        assert activa.get(reverse("viaje-list")).status_code == 403


@pytest.mark.django_db
class TestRecuperacion:
    def test_envia_el_enlace_y_permite_cambiarla(
        self, activa, cliente, empresa, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            assert (
                cliente.post(
                    reverse("auth-recuperar"), {"email": "paula@correo.example"}, format="json"
                ).status_code
                == 202
            )
        cuerpo = mail.outbox[-1].body  # el primero es el de activación (HU-64)
        enlace = re.search(r"/recuperar/([^/]+)/([^/?\s]+)\?empresa=([a-z0-9-]+)", cuerpo)
        assert enlace and cuerpo.startswith("Hola")
        uid, token, slug = enlace.groups()
        # HU-41: vence en 30 minutos y el enlace lleva la empresa (su marca en la pantalla).
        assert "vence en 30 minutos" in cuerpo and slug == empresa.slug
        nueva = "Otra-Clave-Sintetica-1"
        respuesta = cliente.post(
            reverse("auth-recuperar-confirmar"),
            {"uid": uid, "token": token, "password": nueva},
            format="json",
        )
        assert respuesta.status_code == 204
        assert entrar(password=nueva)[1].status_code == 200
        # el enlace sirve una vez
        otra = cliente.post(
            reverse("auth-recuperar-confirmar"),
            {"uid": uid, "token": token, "password": "Tercera-Clave-1"},
            format="json",
        )
        assert otra.status_code == 400

    def test_no_dice_si_el_correo_existe(self, cliente, despachador):
        for email in ["nadie@correo.example", despachador.email]:
            assert cliente.post(reverse("auth-recuperar"), {"email": email}, format="json").status_code == 202
        assert mail.outbox == []

    def test_token_invalido(self, activa, cliente):
        respuesta = cliente.post(
            reverse("auth-recuperar-confirmar"),
            {"uid": "MQ", "token": "x-y", "password": "Otra-Clave-1"},
            format="json",
        )
        assert respuesta.status_code == 400

    def test_bloqueo_tras_5_intentos(self, activa):
        for _ in range(settings.LOGIN_MAX_INTENTOS):
            entrar(password="mala")
        assert entrar()[1].data["code"] == "cuenta_bloqueada"


@pytest.mark.django_db
class TestEliminar:
    def test_anonimiza_y_conserva_las_reservas(self, activa, empresa):
        # HU-45 (DC-50): con la reserva en curso no se puede eliminar; terminada, sí.
        activa.post(
            reverse("mi-cuenta-solicitudes"),
            TestReservas().solicitud(),
            format="json",
        )
        pasajero = CuentaPasajero.objects.get().pasajero
        assert activa.delete(reverse("mi-cuenta")).status_code == 409
        Viaje.objects.filter(pasajero=pasajero).update(estado=E.FINALIZADO)
        assert activa.delete(reverse("mi-cuenta")).status_code == 204
        assert not CuentaPasajero.objects.exists()
        usuario = Usuario.objects.get(rol=Rol.PASAJERO)
        assert (usuario.has_usable_password(), usuario.activo) == (False, False)
        assert "paula" not in usuario.email
        pasajero.refresh_from_db()
        assert (pasajero.nombre, pasajero.telefono) == ("Pasajero eliminado", None)
        assert Viaje.objects.filter(pasajero=pasajero).count() == 1
        assert entrar()[1].status_code == 401
        assert Auditoria.objects.filter(accion="ELIMINAR_CUENTA").exists()
