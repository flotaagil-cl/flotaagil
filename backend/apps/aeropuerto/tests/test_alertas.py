"""HU-28 · Alertas de demora, cancelación o desvío. CP-21."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.aeropuerto import monitoreo, tareas
from apps.aeropuerto.models import AlertaVuelo, EstadoVuelo, TipoAlertaVuelo
from apps.aeropuerto.tests.test_monitoreo import ConsultorFalso, datos_con, vuelo_de
from apps.integraciones.vuelos import VuelosNoDisponibles

V = EstadoVuelo
T = TipoAlertaVuelo
LISTA = reverse("alerta-list")


@pytest.fixture
def api(cliente, despachador):
    cliente.force_authenticate(despachador)
    return cliente


def tipos():
    return [a.tipo for a in AlertaVuelo.objects.order_by("id")]


def atender_todas(usuario):
    AlertaVuelo.objects.filter(atendida_en__isnull=True).update(
        atendida_en=timezone.now(), atendida_por=usuario
    )


@pytest.mark.django_db
class TestGeneracion:
    def test_cambio_de_eta_de_15_min_o_mas(self, empresa):
        vuelo = vuelo_de(empresa)
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 15, V.DEMORADO))
        alerta = AlertaVuelo.objects.get()
        assert alerta.tipo == T.ETA_CAMBIADA
        assert alerta.viaje == vuelo.viaje
        assert alerta.empresa == empresa
        assert "LA845 ahora llega" in alerta.detalle

    def test_cambio_menor_no_alerta(self, empresa):
        vuelo = vuelo_de(empresa)
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 14, V.DEMORADO))
        assert tipos() == []

    def test_el_umbral_es_por_empresa(self, empresa):
        configuracion = empresa.configuracion
        configuracion.cambio_eta_min = 30
        configuracion.save()
        vuelo = vuelo_de(empresa)
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 29, V.DEMORADO))
        assert tipos() == []

    @pytest.mark.parametrize(
        ("estado", "tipo"), [(V.CANCELADO, T.VUELO_CANCELADO), (V.DESVIADO, T.VUELO_DESVIADO)]
    )
    def test_cancelado_o_desviado(self, empresa, estado, tipo):
        vuelo = vuelo_de(empresa)
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 0, estado))
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 0, estado))
        assert tipos() == [tipo]

    def test_mientras_no_se_atiende_se_actualiza_y_no_se_acumula(self, empresa):
        vuelo = vuelo_de(empresa)
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 20))
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 60))
        alerta = AlertaVuelo.objects.get()
        assert alerta.eta == vuelo.hora_programada + timedelta(minutes=60)

    def test_atendida_no_se_repite_con_la_misma_eta(self, empresa, despachador):
        vuelo = vuelo_de(empresa)
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 20))
        atender_todas(despachador)
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 25))
        assert len(tipos()) == 1

    def test_atendida_avisa_otra_vez_si_vuelve_a_moverse(self, empresa, despachador):
        vuelo = vuelo_de(empresa)
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 20))
        atender_todas(despachador)
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 35))
        assert tipos() == [T.ETA_CAMBIADA, T.ETA_CAMBIADA]


@pytest.mark.django_db
class TestSinDatos:
    def usar(self, monkeypatch, *respuestas):
        consultor = ConsultorFalso(*respuestas)
        monkeypatch.setattr(tareas, "obtener_consultor_vuelos", lambda: consultor)

    def test_api_caida_tras_los_reintentos(self, monkeypatch, empresa):
        vuelo = vuelo_de(empresa, en_min=30)
        self.usar(monkeypatch, *[VuelosNoDisponibles("x") for _ in range(4)])
        tareas.consultar_estado_vuelo.delay(vuelo.pk)
        assert tipos() == [T.SIN_DATOS]

    def test_un_fallo_que_se_recupera_no_alerta(self, monkeypatch, empresa):
        vuelo = vuelo_de(empresa, en_min=30)
        self.usar(monkeypatch, VuelosNoDisponibles("x"), datos_con(vuelo))
        tareas.consultar_estado_vuelo.delay(vuelo.pk)
        assert tipos() == []

    def test_no_aparece_en_la_api(self, monkeypatch, empresa):
        vuelo = vuelo_de(empresa, en_min=30)
        self.usar(monkeypatch, None)
        tareas.consultar_estado_vuelo.delay(vuelo.pk)
        assert tipos() == [T.SIN_DATOS]

    def test_no_se_repite_mientras_siga_sin_datos(self, monkeypatch, empresa, despachador):
        vuelo = vuelo_de(empresa, en_min=30)
        self.usar(monkeypatch, None, None, None)
        tareas.consultar_estado_vuelo.delay(vuelo.pk)
        tareas.consultar_estado_vuelo.delay(vuelo.pk)
        atender_todas(despachador)
        tareas.consultar_estado_vuelo.delay(vuelo.pk)
        assert tipos() == [T.SIN_DATOS]

    def test_si_la_api_vuelve_se_resuelve_sola(self, monkeypatch, empresa):
        vuelo = vuelo_de(empresa, en_min=30)
        self.usar(monkeypatch, None, datos_con(vuelo))
        tareas.consultar_estado_vuelo.delay(vuelo.pk)
        tareas.consultar_estado_vuelo.delay(vuelo.pk)
        alerta = AlertaVuelo.objects.get()
        assert alerta.atendida_en is not None
        assert alerta.atendida_por is None

    def test_si_vuelve_y_cae_de_nuevo_avisa_otra_vez(self, monkeypatch, empresa):
        vuelo = vuelo_de(empresa, en_min=30)
        self.usar(monkeypatch, None, datos_con(vuelo), None)
        for _ in range(3):
            tareas.consultar_estado_vuelo.delay(vuelo.pk)
        assert tipos() == [T.SIN_DATOS, T.SIN_DATOS]


@pytest.mark.django_db
class TestApi:
    def con_alerta(self, empresa, estado=V.CANCELADO):
        vuelo = vuelo_de(empresa)
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 0, estado))
        return AlertaVuelo.objects.get(viaje=vuelo.viaje)

    def test_lista_el_registro_con_lo_atendido(self, api, empresa, despachador):
        atendida = self.con_alerta(empresa)
        api.post(reverse("alerta-atender", args=[atendida.pk]))
        pendiente = self.con_alerta(empresa, V.DESVIADO)
        todas = api.get(LISTA).json()["results"]
        assert [a["id"] for a in todas] == [pendiente.pk, atendida.pk]
        assert todas[1]["atendida_por"] == despachador.nombre
        solo = api.get(LISTA, {"pendientes": "true"}).json()["results"]
        assert [a["id"] for a in solo] == [pendiente.pk]

    def test_atender_registra_quien_y_cuando(self, api, empresa, despachador):
        alerta = self.con_alerta(empresa)
        assert api.post(reverse("alerta-atender", args=[alerta.pk])).status_code == 200
        alerta.refresh_from_db()
        assert alerta.atendida_por == despachador
        assert alerta.atendida_en is not None

    def test_atender_dos_veces_conserva_el_primero(self, api, empresa, despachador, cliente):
        alerta = self.con_alerta(empresa)
        api.post(reverse("alerta-atender", args=[alerta.pk]))
        momento = AlertaVuelo.objects.get(pk=alerta.pk).atendida_en
        api.post(reverse("alerta-atender", args=[alerta.pk]))
        assert AlertaVuelo.objects.get(pk=alerta.pk).atendida_en == momento

    def test_otra_empresa_no_ve_ni_atiende(self, api, otra_empresa):
        """RN-13."""
        alerta = self.con_alerta(otra_empresa)
        assert api.get(LISTA).json()["results"] == []
        assert api.post(reverse("alerta-atender", args=[alerta.pk])).status_code == 404

    def test_otros_roles_403(self, cliente, conductor):
        cliente.force_authenticate(conductor)
        assert cliente.get(LISTA).status_code == 403

    def test_marca_la_reserva_afectada(self, api, empresa):
        vuelo = vuelo_de(empresa)
        ruta = reverse("viaje-detail", args=[vuelo.viaje_id])
        assert api.get(ruta).json()["alerta_vuelo"] is None
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 0, V.CANCELADO))
        assert api.get(ruta).json()["alerta_vuelo"] == T.VUELO_CANCELADO
        fila = next(v for v in api.get(reverse("viaje-list")).json()["results"] if v["id"] == vuelo.viaje_id)
        assert fila["alerta_vuelo"] == T.VUELO_CANCELADO
        api.post(reverse("alerta-atender", args=[AlertaVuelo.objects.get().pk]))
        assert api.get(ruta).json()["alerta_vuelo"] is None

    def test_el_listado_no_hace_una_consulta_por_fila(self, api, empresa, django_assert_max_num_queries):
        for _ in range(5):
            vuelo = vuelo_de(empresa)
            monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 0, V.CANCELADO))
        with django_assert_max_num_queries(8):
            api.get(reverse("viaje-list"))

    def test_decidir_la_recogida_atiende_la_alerta_del_cambio(self, api, empresa, despachador):
        vuelo = vuelo_de(empresa)
        vuelo = monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 40))
        cuerpo = {"recogida_propuesta": vuelo.recogida_propuesta.isoformat()}
        api.post(reverse("viaje-confirmar-recogida", args=[vuelo.viaje_id]), cuerpo, format="json")
        alerta = AlertaVuelo.objects.get()
        assert alerta.atendida_por == despachador
