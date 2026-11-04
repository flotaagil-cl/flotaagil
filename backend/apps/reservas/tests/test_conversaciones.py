"""HU-30 · Chat de WhatsApp desde el panel. CP-27."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from kombu.exceptions import OperationalError as ErrorDeBroker

from apps.reservas import tareas
from apps.reservas.models import DireccionMensaje, EstadoEntrega, MensajeWhatsapp, TipoMensaje
from apps.reservas.tests.fabricas import PasajeroFactory, ViajeFactory
from apps.reservas.tests.test_whatsapp import TwilioFalso, http_error
from apps.reservas.verificacion import procesar_entrante

BANDEJA = reverse("conversacion-list")
R = DireccionMensaje.ENTRANTE
S = DireccionMensaje.SALIENTE


def mensaje(pasajero, direccion=R, *, hace_min=0, cuerpo="Hola", **extra):
    creado = MensajeWhatsapp.objects.create(
        pasajero=pasajero, direccion=direccion, tipo=TipoMensaje.SESION, cuerpo=cuerpo, **extra
    )
    MensajeWhatsapp.objects.filter(pk=creado.pk).update(
        creado_en=timezone.now() - timedelta(minutes=hace_min)
    )
    return creado


def hilo(pasajero):
    return reverse("conversacion-detail", args=[pasajero.pk])


def responder(api, pasajero, texto="Le respondemos"):
    return api.post(reverse("conversacion-responder", args=[pasajero.pk]), {"texto": texto}, format="json")


@pytest.fixture
def api(cliente, despachador):
    cliente.force_authenticate(despachador)
    return cliente


@pytest.fixture
def ana(empresa):
    return PasajeroFactory(empresa=empresa, nombre="Ana Pérez", telefono="+56900009001")


@pytest.mark.django_db
class TestBandeja:
    def test_por_pasajero_con_reserva_vinculada_la_mas_reciente_primero(self, api, ana, empresa):
        otra = PasajeroFactory(empresa=empresa, nombre="Berta Soto")
        ViajeFactory(empresa=empresa, pasajero=ana)
        reciente = ViajeFactory(empresa=empresa, pasajero=ana)
        mensaje(ana, hace_min=30, cuerpo="Antiguo")
        mensaje(ana, S, hace_min=5, cuerpo="Último de Ana")
        mensaje(otra, hace_min=60)
        filas = api.get(BANDEJA).json()["results"]
        assert [f["nombre"] for f in filas] == ["Ana Pérez", "Berta Soto"]
        assert filas[0]["ultimo_mensaje"] == "Último de Ana"
        assert filas[0]["ultima_direccion"] == S
        assert filas[0]["reserva"] == {"id": reciente.pk, "estado": reciente.estado}
        assert filas[1]["reserva"] is None

    def test_sin_mensajes_no_aparece(self, api, ana):
        assert api.get(BANDEJA).json()["results"] == []

    def test_otra_empresa_no_se_ve(self, api, otra_empresa):
        """RN-13."""
        ajeno = PasajeroFactory(empresa=otra_empresa)
        mensaje(ajeno)
        assert api.get(BANDEJA).json()["results"] == []
        assert api.get(hilo(ajeno)).status_code == 404
        assert responder(api, ajeno).status_code == 404

    def test_el_administrador_tambien_y_el_conductor_no(self, cliente, administrador, conductor, ana):
        cliente.force_authenticate(administrador)
        assert cliente.get(BANDEJA).status_code == 200
        cliente.force_authenticate(conductor)
        assert cliente.get(BANDEJA).status_code == 403
        assert responder(cliente, ana).status_code == 403


@pytest.mark.django_db
class TestHilo:
    def test_en_orden_con_autor_y_estado(self, api, ana, despachador):
        mensaje(ana, hace_min=10, cuerpo="Primero", estado_entrega=EstadoEntrega.DELIVERED)
        mensaje(ana, S, hace_min=5, cuerpo="Segundo", usuario=despachador, estado_entrega=EstadoEntrega.READ)
        datos = api.get(hilo(ana)).json()
        assert [m["cuerpo"] for m in datos["mensajes"]] == ["Primero", "Segundo"]
        assert datos["mensajes"][0]["usuario"] is None
        assert datos["mensajes"][1]["usuario"] == despachador.nombre
        assert datos["mensajes"][1]["estado_entrega"] == EstadoEntrega.READ

    def test_el_mensaje_libre_del_webhook_aparece(self, api, ana):
        """El que antes quedaba sin atender (`sin_accion`)."""
        procesar_entrante(
            {"MessageSid": "SMlibre1", "From": f"whatsapp:{ana.telefono}", "Body": "¿Viene pronto?"}
        )
        assert [m["cuerpo"] for m in api.get(hilo(ana)).json()["mensajes"]] == ["¿Viene pronto?"]


@pytest.mark.django_db
class TestVentana:
    @pytest.mark.parametrize(
        ("hace_min", "dentro"),
        [(0, True), (23 * 60 + 59, True), (24 * 60 + 1, False)],
    )
    def test_24_h_desde_el_ultimo_mensaje_del_pasajero(self, api, ana, hace_min, dentro):
        mensaje(ana, hace_min=hace_min)
        datos = api.get(hilo(ana)).json()
        assert datos["dentro_ventana"] is dentro
        assert datos["ventana_hasta"] is not None
        assert responder(api, ana).status_code == (201 if dentro else 409)

    def test_un_mensaje_saliente_no_abre_la_ventana(self, api, ana):
        mensaje(ana, S)
        datos = api.get(hilo(ana)).json()
        assert (datos["dentro_ventana"], datos["ventana_hasta"]) == (False, None)
        respuesta = responder(api, ana)
        assert respuesta.status_code == 409
        assert respuesta.json()["code"] == "fuera_de_ventana"
        assert "PR-11" in respuesta.json()["detail"]
        assert MensajeWhatsapp.objects.filter(pasajero=ana).count() == 1

    def test_el_ultimo_entrante_manda_aunque_haya_salientes_nuevos(self, api, ana):
        mensaje(ana, hace_min=25 * 60)
        mensaje(ana, S, hace_min=1)
        assert api.get(hilo(ana)).json()["dentro_ventana"] is False


@pytest.mark.django_db
class TestResponder:
    def test_queda_registrado_con_el_autor_y_la_reserva(self, api, ana, empresa, despachador, monkeypatch):
        monkeypatch.setattr(tareas.enviar_chat, "delay", lambda *a: None)
        viaje = ViajeFactory(empresa=empresa, pasajero=ana)
        mensaje(ana)
        respuesta = responder(api, ana, "  Vamos en camino  ")
        assert respuesta.status_code == 201, respuesta.data
        creado = MensajeWhatsapp.objects.get(pk=respuesta.json()["id"])
        assert creado.cuerpo == "Vamos en camino"
        assert (creado.direccion, creado.tipo, creado.usuario) == (S, TipoMensaje.SESION, despachador)
        assert (creado.viaje, creado.estado_entrega) == (viaje, EstadoEntrega.QUEUED)

    @pytest.mark.parametrize("texto", ["", "   ", "x" * 1025])
    def test_texto_invalido(self, api, ana, texto):
        mensaje(ana)
        assert responder(api, ana, texto).status_code == 400
        assert MensajeWhatsapp.objects.filter(pasajero=ana, direccion=S).count() == 0

    def test_se_encola_tras_el_commit(self, api, ana, monkeypatch, django_capture_on_commit_callbacks):
        encolados = []
        monkeypatch.setattr(tareas.enviar_chat, "delay", lambda *a: encolados.append(a))
        mensaje(ana)
        with django_capture_on_commit_callbacks(execute=True):
            creado = responder(api, ana).json()
        assert encolados == [(creado["id"],)]

    def test_sin_broker_queda_en_failed(self, api, ana, monkeypatch, django_capture_on_commit_callbacks):
        def caido(*_):
            raise ErrorDeBroker("sin broker")

        monkeypatch.setattr(tareas.enviar_chat, "delay", caido)
        mensaje(ana)
        with django_capture_on_commit_callbacks(execute=True):
            creado = responder(api, ana)
        assert creado.status_code == 201
        assert MensajeWhatsapp.objects.get(pk=creado.json()["id"]).estado_entrega == EstadoEntrega.FAILED


@pytest.mark.django_db
class TestEnvio:
    def preparar(self, ana, monkeypatch, *errores):
        falso = TwilioFalso(*errores)
        monkeypatch.setattr(tareas, "obtener_notificador", lambda: falso)
        return falso, mensaje(ana, S, cuerpo="Hola Ana", estado_entrega=EstadoEntrega.QUEUED)

    def test_envia_texto_libre_y_guarda_el_sid(self, ana, monkeypatch):
        falso, creado = self.preparar(ana, monkeypatch)
        tareas.enviar_chat.run(creado.pk)
        creado.refresh_from_db()
        assert creado.proveedor_sid
        assert creado.estado_entrega == EstadoEntrega.QUEUED  # lo actualiza el webhook de estado
        assert falso.enviados[0]["Body"] == "Hola Ana"
        assert falso.enviados[0]["To"] == f"whatsapp:{ana.telefono}"
        assert "ContentSid" not in falso.enviados[0]
        assert MensajeWhatsapp.objects.filter(pasajero=ana).count() == 1

    def test_repetir_la_tarea_no_lo_envia_dos_veces(self, ana, monkeypatch):
        falso, creado = self.preparar(ana, monkeypatch)
        tareas.enviar_chat.run(creado.pk)
        tareas.enviar_chat.run(creado.pk)
        assert len(falso.enviados) == 1

    def test_un_rechazo_de_twilio_queda_en_failed(self, ana, monkeypatch):
        _, creado = self.preparar(ana, monkeypatch, http_error(400))
        tareas.enviar_chat.run(creado.pk)
        creado.refresh_from_db()
        assert creado.estado_entrega == EstadoEntrega.FAILED
        assert creado.proveedor_sid is None

    def test_el_doble_de_desarrollo_lo_marca_enviado(self, ana, settings):
        creado = mensaje(ana, S, estado_entrega=EstadoEntrega.QUEUED)
        settings.TWILIO_ACCOUNT_SID = ""
        tareas.enviar_chat.run(creado.pk)
        creado.refresh_from_db()
        assert creado.estado_entrega == EstadoEntrega.SENT
        assert creado.proveedor_sid.startswith("DEV-")
