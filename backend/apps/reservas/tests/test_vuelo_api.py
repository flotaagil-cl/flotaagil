"""HU-26 · CP-11: registrar el número de vuelo con consulta inicial a la API de vuelos (panel y portal)."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.aeropuerto.models import EstadoVuelo, Vuelo
from apps.integraciones.vuelos import DatosVuelo, VuelosNoDisponibles
from apps.reservas import servicios
from apps.reservas.models import Sentido, Viaje
from apps.reservas.tests.fabricas import ViajeFactory

LISTA = reverse("viaje-list")


class ConsultorFalso:
    """Devuelve la llegada «corregida» (+10 min), None (no existe) o falla (sin datos)."""

    def __init__(self, modo="corrige"):
        self.modo = modo
        self.consultas = []

    def consultar(self, numero, llegada_informada):
        self.consultas.append((numero, llegada_informada))
        if self.modo == "no_existe":
            return None
        if self.modo == "sin_datos":
            raise VuelosNoDisponibles("sin datos")
        return DatosVuelo(
            numero.replace(" ", ""),
            llegada_informada + timedelta(minutes=10),
            llegada_informada + timedelta(minutes=25),
            EstadoVuelo.DEMORADO,
        )


@pytest.fixture
def consultor(monkeypatch):
    falso = ConsultorFalso()
    monkeypatch.setattr(servicios, "obtener_consultor_vuelos", lambda: falso)
    return falso


@pytest.fixture
def api(cliente, despachador):
    cliente.force_authenticate(despachador)
    return cliente


def llegada(horas=4):
    return (timezone.now() + timedelta(hours=horas)).replace(microsecond=0)


def reserva(hora, numero="la 123"):
    return {
        "pasajero": {"nombre": "Ana Pérez", "telefono": "+56900009001"},
        "sentido": "DESDE_AEROPUERTO",
        "origen_dir": "Aeropuerto Arturo Merino Benítez",
        "destino_dir": "Plaza de Armas, Santiago",
        "recogida_en": (hora + timedelta(minutes=30)).isoformat(),
        "vuelo": {"numero": numero, "hora_programada": hora.isoformat()},
    }


@pytest.mark.django_db
class TestPanel:
    def test_guarda_la_hora_de_la_api_y_su_estado(self, api, consultor):
        hora = llegada()
        respuesta = api.post(LISTA, reserva(hora), format="json")
        assert respuesta.status_code == 201, respuesta.data
        vuelo = Vuelo.objects.get(viaje_id=respuesta.data["id"])
        assert vuelo.hora_programada == hora + timedelta(minutes=10)  # corregida (DC-06)
        assert vuelo.hora_estimada == hora + timedelta(minutes=25)
        assert vuelo.estado_vuelo == EstadoVuelo.DEMORADO
        assert vuelo.ultima_consulta_en is not None
        assert consultor.consultas == [("LA 123", hora)]

    def test_vuelo_inexistente_400_en_el_numero(self, api, consultor):
        consultor.modo = "no_existe"
        hora = llegada()
        respuesta = api.post(LISTA, reserva(hora), format="json")
        assert respuesta.status_code == 400
        mensaje = respuesta.json()["vuelo"]["numero"][0]
        assert mensaje.startswith("No encontramos el vuelo LA 123 con llegada a SCL el ")
        assert not Viaje.objects.exists()

    def test_sin_datos_de_la_api_se_guarda_sin_verificar(self, api, consultor):
        consultor.modo = "sin_datos"
        hora = llegada()
        respuesta = api.post(LISTA, reserva(hora), format="json")
        assert respuesta.status_code == 201
        vuelo = Vuelo.objects.get(viaje_id=respuesta.data["id"])
        assert (vuelo.hora_programada, vuelo.ultima_consulta_en) == (hora, None)

    def test_editar_con_otro_vuelo_lo_verifica(self, api, despachador, consultor):
        viaje = ViajeFactory(empresa=despachador.empresa, sentido=Sentido.DESDE_AEROPUERTO)
        hora = llegada(5)
        respuesta = api.patch(
            reverse("viaje-detail", args=[viaje.pk]),
            {"vuelo": {"numero": "H2 456", "hora_programada": hora.isoformat()}},
            format="json",
        )
        assert respuesta.status_code == 200, respuesta.data
        assert Vuelo.objects.get(viaje=viaje).hora_programada == hora + timedelta(minutes=10)

    def test_editar_otro_campo_no_vuelve_a_consultar(self, api, despachador, consultor):
        hora = llegada()
        creada = api.post(LISTA, reserva(hora), format="json").data
        api.patch(reverse("viaje-detail", args=[creada["id"]]), {"tarifa": 20000}, format="json")
        assert len(consultor.consultas) == 1

    def test_consultor_de_desarrollo_por_defecto(self, api, settings):
        settings.FLIGHTAWARE_API_KEY = ""
        assert api.post(LISTA, reserva(llegada(), numero="ZZ 999"), format="json").status_code == 400
        respuesta = api.post(LISTA, reserva(llegada()), format="json")
        assert Vuelo.objects.get(viaje_id=respuesta.data["id"]).ultima_consulta_en is not None


@pytest.mark.django_db
class TestPortal:
    def solicitud(self, hora, numero="LA123"):
        return {
            "nombre": "Ana Pérez",
            "telefono": "+56900009001",
            "origen_dir": "Aeropuerto Arturo Merino Benítez",
            "destino_dir": "Plaza de Armas, Santiago",
            "vuelo": {"numero": numero, "hora_llegada": hora.isoformat()},
            "acepta_privacidad": True,
            "acepta_whatsapp": True,
        }

    def test_la_recogida_se_calcula_con_la_llegada_confirmada(self, con_cuenta, empresa, consultor):
        """RN-17 con la hora de la API: llegada corregida + margen nacional."""
        hora = llegada()
        # HU-40: el pedido web es con cuenta.
        respuesta = con_cuenta.post(reverse("mi-cuenta-solicitudes"), self.solicitud(hora), format="json")
        assert respuesta.status_code == 201, respuesta.json()
        viaje = Viaje.objects.get()
        margen = timedelta(minutes=empresa.configuracion.margen_nacional_min)
        assert viaje.recogida_en == hora + timedelta(minutes=10) + margen
        assert viaje.vuelo.ultima_consulta_en is not None

    def test_vuelo_inexistente(self, con_cuenta, empresa, consultor):
        consultor.modo = "no_existe"
        respuesta = con_cuenta.post(
            reverse("mi-cuenta-solicitudes"), self.solicitud(llegada()), format="json"
        )
        assert respuesta.status_code == 400
        assert "No encontramos el vuelo LA123" in respuesta.json()["vuelo"]["numero"][0]
        assert not Viaje.objects.exists()
