"""Portal: datos públicos de la empresa (HU-19) y reglas de la solicitud web (CP-07).

Desde HU-40 (CC-18) solo se pide con cuenta: las reglas (anticipación, vuelo, límite por teléfono) se
prueban en `/api/mi-cuenta/solicitudes/`, que usa los mismos servicios que el pedido de convenio.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.aeropuerto.models import Vuelo
from apps.reservas.models import EstadoViaje, Pasajero, Viaje
from apps.reservas.tests.fabricas import PasajeroFactory, ViajeFactory


def url(_empresa=None):
    return reverse("mi-cuenta-solicitudes")


def en_horas(horas: float) -> str:
    return (timezone.now() + timedelta(hours=horas)).isoformat()


def solicitud(**cambios):
    datos = {
        "nombre": "Ana Pérez",
        "telefono": "+56 9 0000 9101",
        "origen_dir": "Av. Providencia 1234, Providencia",
        "destino_dir": "Plaza de Armas, Santiago",
        "recogida_en": en_horas(2),
        "acepta_privacidad": True,
        "acepta_whatsapp": True,
    }
    datos.update(cambios)
    return {k: v for k, v in datos.items() if v is not None}


@pytest.mark.django_db
class TestEmpresaPublica:
    def test_datos_publicos(self, cliente, empresa):
        respuesta = cliente.get(reverse("portal-empresa", args=[empresa.slug]))
        assert respuesta.status_code == 200
        assert respuesta.data == {
            "razon_social": empresa.razon_social,
            "slug": empresa.slug,
            "anticipacion_minima_min": 30,
            "expiracion_verificacion_min": 15,
            "margen_nacional_min": 20,
            "antelacion_vuelo_nacional_min": 120,
            "antelacion_vuelo_internacional_min": 180,
            "capacidad_maxima": 4,
        }

    def test_margen_configurable(self, cliente, empresa):
        empresa.configuracion.margen_nacional_min = 45
        empresa.configuracion.save()
        respuesta = cliente.get(reverse("portal-empresa", args=[empresa.slug]))
        assert respuesta.data["margen_nacional_min"] == 45

    def test_empresa_inexistente_o_inactiva(self, cliente, empresa):
        assert cliente.get(reverse("portal-empresa", args=["no-existe"])).status_code == 404
        empresa.activa = False
        empresa.save()
        assert cliente.get(reverse("portal-empresa", args=[empresa.slug])).status_code == 404


@pytest.mark.django_db
class TestCuentaObligatoria:
    """HU-40 (CC-18): ya no se pide sin cuenta."""

    def test_el_pedido_como_invitado_no_existe(self, cliente, empresa):
        ruta = f"/api/portal/{empresa.slug}/solicitudes/"
        assert cliente.post(ruta, solicitud(), format="json").status_code == 404
        assert not Viaje.objects.exists()

    def test_sin_sesion_no_se_pide(self, cliente, empresa):
        assert cliente.post(url(), solicitud(), format="json").status_code == 401

    def test_con_cuenta_queda_solicitado_sin_verificar(self, con_cuenta, empresa):
        respuesta = con_cuenta.post(url(), solicitud(), format="json")
        assert respuesta.status_code == 201, respuesta.data
        viaje = Viaje.objects.get()
        assert (viaje.estado, viaje.pasajero.telefono) == (EstadoViaje.SOLICITADO, "+56900009101")
        # La declaración del supervisor es solo del convenio (DC-27).
        assert (viaje.autorizacion_avisos_en, viaje.autorizacion_avisos_supervisor) == (None, None)


@pytest.mark.django_db
class TestAnticipacion:
    """DC-10."""

    def test_menos_de_30_minutos(self, con_cuenta, empresa):
        respuesta = con_cuenta.post(url(), solicitud(recogida_en=en_horas(0.25)), format="json")
        assert respuesta.status_code == 400
        assert "30 minutos" in str(respuesta.data["recogida_en"][0])

    def test_configurable_por_empresa(self, con_cuenta, empresa):
        config = empresa.configuracion
        config.anticipacion_minima_min = 10
        config.save()
        assert con_cuenta.post(url(), solicitud(recogida_en=en_horas(0.25)), format="json").status_code == 201

    def test_pasado(self, con_cuenta, empresa):
        assert con_cuenta.post(url(), solicitud(recogida_en=en_horas(-1)), format="json").status_code == 400


@pytest.mark.django_db
class TestAeropuerto:
    def test_vuelo_deduce_desde_el_aeropuerto(self, con_cuenta, empresa):
        llegada = timezone.now() + timedelta(hours=3)
        datos = solicitud(
            origen_dir="Aeropuerto Arturo Merino Benítez",
            vuelo={"numero": "la 123", "hora_llegada": llegada.isoformat()},
        )
        assert con_cuenta.post(url(), datos, format="json").status_code == 201
        viaje = Viaje.objects.get()
        assert viaje.sentido == "DESDE_AEROPUERTO"
        vuelo = Vuelo.objects.get(viaje=viaje)
        assert (vuelo.numero, vuelo.hora_programada) == ("LA 123", llegada)

    def test_sin_recogida_se_calcula_con_el_margen_nacional(self, con_cuenta, empresa):
        """RN-17 y DC-12: llegada + margen nacional (20 min por defecto)."""
        llegada = timezone.now() + timedelta(hours=3)
        datos = solicitud(recogida_en=None, vuelo={"numero": "LA123", "hora_llegada": llegada.isoformat()})
        assert con_cuenta.post(url(), datos, format="json").status_code == 201
        assert Viaje.objects.get().recogida_en == llegada + timedelta(minutes=20)

    def test_recogida_null_equivale_a_no_informada(self, con_cuenta, empresa):
        llegada = timezone.now() + timedelta(hours=3)
        datos = solicitud(vuelo={"numero": "LA123", "hora_llegada": llegada.isoformat()})
        datos["recogida_en"] = None
        assert con_cuenta.post(url(), datos, format="json").status_code == 201
        assert Viaje.objects.get().recogida_en == llegada + timedelta(minutes=20)

    def test_recogida_null_sin_vuelo(self, con_cuenta, empresa):
        datos = solicitud()
        datos["recogida_en"] = None
        respuesta = con_cuenta.post(url(), datos, format="json")
        assert respuesta.status_code == 400
        assert "recogida_en" in respuesta.data

    def test_margen_configurable(self, con_cuenta, empresa):
        config = empresa.configuracion
        config.margen_nacional_min = 45
        config.save()
        llegada = timezone.now() + timedelta(hours=3)
        datos = solicitud(recogida_en=None, vuelo={"numero": "LA123", "hora_llegada": llegada.isoformat()})
        con_cuenta.post(url(), datos, format="json")
        assert Viaje.objects.get().recogida_en == llegada + timedelta(minutes=45)

    def test_si_viene_la_recogida_se_respeta(self, con_cuenta, empresa):
        llegada = timezone.now() + timedelta(hours=3)
        recogida = llegada + timedelta(minutes=50)
        datos = solicitud(
            recogida_en=recogida.isoformat(), vuelo={"numero": "LA123", "hora_llegada": llegada.isoformat()}
        )
        con_cuenta.post(url(), datos, format="json")
        assert Viaje.objects.get().recogida_en == recogida

    def test_pasajero_corrige_el_sentido(self, con_cuenta, empresa):
        datos = solicitud(sentido="HACIA_AEROPUERTO", destino_dir="Aeropuerto SCL")
        assert con_cuenta.post(url(), datos, format="json").status_code == 201
        assert Viaje.objects.get().sentido == "HACIA_AEROPUERTO"
        assert not Vuelo.objects.exists()

    def test_vuelo_hacia_el_aeropuerto_no_se_acepta(self, con_cuenta, empresa):
        datos = solicitud(sentido="HACIA_AEROPUERTO", vuelo={"numero": "LA123", "hora_llegada": en_horas(3)})
        respuesta = con_cuenta.post(url(), datos, format="json")
        assert respuesta.status_code == 400
        assert "vuelo" in respuesta.data

    def test_numero_de_vuelo_invalido(self, con_cuenta, empresa):
        datos = solicitud(vuelo={"numero": "LA-123", "hora_llegada": en_horas(3)})
        assert con_cuenta.post(url(), datos, format="json").status_code == 400


@pytest.mark.django_db
class TestProteccion:
    def test_limite_por_telefono(self, con_cuenta, empresa):
        pasajero = Pasajero.objects.get(telefono="+56900009101")
        for _ in range(3):
            ViajeFactory(empresa=empresa, canal="WEB", estado=EstadoViaje.SOLICITADO, pasajero=pasajero)
        respuesta = con_cuenta.post(url(), solicitud(), format="json")
        assert respuesta.status_code == 429
        assert respuesta.data["code"] == "limite_telefono"
        assert respuesta.data["detail"].startswith("Ya enviaste varias solicitudes con este número.")
        assert Viaje.objects.count() == 3

    def test_el_limite_por_telefono_es_por_empresa(self, con_cuenta, empresa, otra_empresa):
        pasajero = PasajeroFactory(empresa=otra_empresa, telefono="+56900009101")
        for _ in range(3):
            ViajeFactory(empresa=otra_empresa, canal="WEB", pasajero=pasajero)
        assert con_cuenta.post(url(), solicitud(), format="json").status_code == 201

    def test_solicitudes_antiguas_no_cuentan(self, con_cuenta, empresa):
        pasajero = Pasajero.objects.get(telefono="+56900009101")
        for _ in range(3):
            ViajeFactory(empresa=empresa, canal="WEB", pasajero=pasajero)
        Viaje.objects.update(creado_en=timezone.now() - timedelta(minutes=16))
        assert con_cuenta.post(url(), solicitud(), format="json").status_code == 201
