"""HU-30 con HU-67 (CC-19): historial de WhatsApp en solo lectura («Historial WhatsApp (canal retirado)»)."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.reservas.models import DireccionMensaje, EstadoEntrega, MensajeWhatsapp, TipoMensaje
from apps.reservas.tests.fabricas import PasajeroFactory, ViajeFactory

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
    """La ruta de respuesta de HU-30 ya no existe: el canal se retiró."""
    return api.post(f"{hilo(pasajero)}mensajes/", {"texto": texto}, format="json")


@pytest.fixture
def api(cliente, despachador):
    cliente.force_authenticate(despachador)
    return cliente


@pytest.fixture
def ana(empresa):
    return PasajeroFactory(empresa=empresa, nombre="Ana Pérez", telefono="+56900009001")


@pytest.mark.django_db
class TestHistorial:
    def test_por_pasajero_con_reserva_vinculada_la_mas_reciente_primero(self, api, ana, empresa):
        otra = PasajeroFactory(empresa=empresa, nombre="Berta Soto")
        ViajeFactory(empresa=empresa, pasajero=ana)
        reciente = ViajeFactory(empresa=empresa, pasajero=ana)
        mensaje(ana, hace_min=30, cuerpo="Antiguo")
        mensaje(ana, S, hace_min=5, cuerpo="Último de Ana")
        mensaje(otra, hace_min=60)
        filas = api.get(BANDEJA).json()["results"]
        assert [f["nombre"] for f in filas] == ["Ana Pérez", "Berta Soto"]
        assert (filas[0]["ultimo_mensaje"], filas[0]["ultima_direccion"]) == ("Último de Ana", S)
        assert filas[0]["reserva"] == {"id": reciente.pk, "estado": reciente.estado}
        assert filas[1]["reserva"] is None
        assert "dentro_ventana" not in filas[0]

    def test_sin_mensajes_no_aparece(self, api, ana):
        assert api.get(BANDEJA).json()["results"] == []

    def test_otra_empresa_no_se_ve(self, api, otra_empresa):
        """RN-13."""
        ajeno = PasajeroFactory(empresa=otra_empresa)
        mensaje(ajeno)
        assert api.get(BANDEJA).json()["results"] == []
        assert api.get(hilo(ajeno)).status_code == 404

    def test_el_administrador_tambien_y_el_conductor_no(self, cliente, administrador, conductor):
        cliente.force_authenticate(administrador)
        assert cliente.get(BANDEJA).status_code == 200
        cliente.force_authenticate(conductor)
        assert cliente.get(BANDEJA).status_code == 403

    def test_en_orden_con_autor_y_estado(self, api, ana, despachador):
        mensaje(ana, hace_min=10, cuerpo="Primero", estado_entrega=EstadoEntrega.DELIVERED)
        mensaje(ana, S, hace_min=5, cuerpo="Segundo", usuario=despachador, estado_entrega=EstadoEntrega.READ)
        datos = api.get(hilo(ana)).json()
        assert [m["cuerpo"] for m in datos["mensajes"]] == ["Primero", "Segundo"]
        assert datos["mensajes"][0]["usuario"] is None
        assert (datos["mensajes"][1]["usuario"], datos["mensajes"][1]["estado_entrega"]) == (
            despachador.nombre,
            EstadoEntrega.READ,
        )

    def test_solo_lectura(self, api, ana):
        """CP-57: ya no se responde por WhatsApp desde el panel; no se crea ningún mensaje."""
        mensaje(ana)
        assert responder(api, ana).status_code in (404, 405)
        assert MensajeWhatsapp.objects.filter(direccion=S).count() == 0
