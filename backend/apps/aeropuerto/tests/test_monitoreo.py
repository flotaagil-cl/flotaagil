"""HU-27 · Monitoreo de vuelo y ajuste de recogida. CP-21 (RN-02, RN-17)."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.aeropuerto import monitoreo, tareas
from apps.aeropuerto.models import EstadoVuelo, Vuelo
from apps.auditoria.models import Auditoria
from apps.integraciones.vuelos import DatosVuelo, VuelosNoDisponibles
from apps.reservas.models import EstadoViaje, Sentido
from apps.reservas.tests.fabricas import ViajeFactory

E = EstadoViaje
V = EstadoVuelo


@pytest.fixture
def api(cliente, despachador):
    cliente.force_authenticate(despachador)
    return cliente


def vuelo_de(empresa, en_min=120, estado=E.SOLICITADO, **cambios):
    llegada = timezone.now() + timedelta(minutes=en_min)
    viaje = ViajeFactory(
        empresa=empresa,
        estado=estado,
        sentido=Sentido.DESDE_AEROPUERTO,
        recogida_en=llegada + timedelta(minutes=20),
    )
    datos = {
        "viaje": viaje,
        "numero": "LA845",
        "fecha": timezone.localdate(llegada),
        "hora_programada": llegada,
    } | cambios
    return Vuelo.objects.create(**datos)


def datos_con(vuelo, cambio_min=0, estado=V.PROGRAMADO, origen=None):
    eta = vuelo.hora_programada + timedelta(minutes=cambio_min)
    return DatosVuelo(vuelo.numero, vuelo.hora_programada, eta, estado, origen)


def consultado_hace(vuelo, minutos):
    Vuelo.objects.filter(pk=vuelo.pk).update(ultima_consulta_en=timezone.now() - timedelta(minutes=minutos))


def pendientes():
    return [v.pk for v in monitoreo.vuelos_por_consultar()]


@pytest.mark.django_db
class TestCuandoConsultar:
    def test_antes_de_3_h_no(self, empresa):
        vuelo_de(empresa, en_min=181)
        assert pendientes() == []

    def test_desde_3_h_antes_si(self, empresa):
        vuelo = vuelo_de(empresa, en_min=179)
        assert pendientes() == [vuelo.pk]

    @pytest.mark.parametrize(("hace", "toca"), [(29, False), (30, True)])
    def test_cada_30_min(self, empresa, hace, toca):
        vuelo = vuelo_de(empresa, en_min=120)
        consultado_hace(vuelo, hace)
        assert (vuelo.pk in pendientes()) is toca

    @pytest.mark.parametrize(("hace", "toca"), [(9, False), (10, True)])
    def test_cada_10_min_en_la_ultima_hora(self, empresa, hace, toca):
        vuelo = vuelo_de(empresa, en_min=59)
        consultado_hace(vuelo, hace)
        assert (vuelo.pk in pendientes()) is toca

    def test_usa_la_eta_y_no_la_hora_programada(self, empresa):
        vuelo = vuelo_de(empresa, en_min=60 * 5)
        Vuelo.objects.filter(pk=vuelo.pk).update(hora_estimada=timezone.now() + timedelta(minutes=30))
        assert pendientes() == [vuelo.pk]

    def test_los_valores_son_por_empresa(self, empresa):
        configuracion = empresa.configuracion
        configuracion.consulta_vuelo_desde_min = 300
        configuracion.consulta_vuelo_cada_min = 5
        configuracion.save()
        vuelo = vuelo_de(empresa, en_min=290)
        consultado_hace(vuelo, 5)
        assert pendientes() == [vuelo.pk]

    @pytest.mark.parametrize("estado", [V.ATERRIZADO, V.CANCELADO, V.DESVIADO])
    def test_estado_final_no_se_consulta(self, empresa, estado):
        vuelo_de(empresa, en_min=30, estado_vuelo=estado)
        assert pendientes() == []

    @pytest.mark.parametrize("estado", [E.FINALIZADO, E.PENDIENTE_CONFIRMACION])
    def test_viaje_que_no_corresponde_no_se_consulta(self, empresa, estado):
        vuelo_de(empresa, en_min=30, estado=estado)
        assert pendientes() == []

    def test_viaje_cancelado_no_se_consulta(self, empresa):
        vuelo = vuelo_de(empresa, en_min=30)
        type(vuelo.viaje).objects.filter(pk=vuelo.viaje_id).update(
            estado=E.CANCELADO, motivo_cancelacion="Prueba", origen_cancelacion="ADMIN"
        )
        assert pendientes() == []

    def test_mucho_despues_de_la_llegada_deja_de_consultar(self, empresa):
        vuelo_de(empresa, en_min=-121)
        assert pendientes() == []

    def test_respeta_el_limite_por_minuto_y_prioriza_al_mas_atrasado(self, empresa, settings):
        settings.VUELOS_CONSULTAS_POR_MINUTO = 2
        reciente = vuelo_de(empresa, en_min=30)
        consultado_hace(reciente, 11)
        atrasado = vuelo_de(empresa, en_min=30)
        consultado_hace(atrasado, 50)
        nunca = vuelo_de(empresa, en_min=30)
        assert pendientes() == [nunca.pk, atrasado.pk]


@pytest.mark.django_db
class TestPropuesta:
    @pytest.mark.parametrize(("cambio", "propone"), [(14, False), (15, True), (-15, True), (-14, False)])
    def test_propone_si_la_eta_cambia_15_min_o_mas(self, empresa, cambio, propone):
        vuelo = vuelo_de(empresa)
        vuelo = monitoreo.aplicar(vuelo.pk, datos_con(vuelo, cambio))
        assert (vuelo.recogida_propuesta is not None) is propone

    def test_nueva_hora_es_eta_mas_margen_nacional(self, empresa):
        """RN-17."""
        vuelo = vuelo_de(empresa)
        resultado = monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 40, origen="SCFA"))
        assert resultado.recogida_propuesta == vuelo.hora_programada + timedelta(minutes=60)
        assert resultado.origen_icao == "SCFA"

    def test_nueva_hora_es_eta_mas_margen_internacional(self, empresa):
        vuelo = vuelo_de(empresa)
        resultado = monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 40, origen="SPJC"))
        assert resultado.recogida_propuesta == vuelo.hora_programada + timedelta(minutes=75)

    @pytest.mark.parametrize(
        ("origen", "internacional"),
        [
            ("SCEL", False),
            ("SCFA", False),
            ("scip", False),  # Isla de Pascua
            ("SPJC", True),
            ("SAEZ", True),
            ("KMIA", True),
            ("", False),
            (None, False),
        ],
    )
    def test_nacional_si_el_icao_empieza_con_sc(self, origen, internacional):
        assert monitoreo.es_internacional(origen) is internacional

    def test_un_dato_nuevo_vacio_no_borra_el_origen_conocido(self, empresa):
        vuelo = vuelo_de(empresa)
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 0, origen="SPJC"))
        assert monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 0)).origen_icao == "SPJC"

    def test_sin_origen_conocido_usa_el_nacional(self, empresa):
        """DC-12."""
        vuelo = vuelo_de(empresa)
        resultado = monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 40))
        assert resultado.recogida_propuesta == vuelo.hora_programada + timedelta(minutes=60)

    def test_los_margenes_y_el_umbral_son_por_empresa(self, empresa):
        configuracion = empresa.configuracion
        configuracion.margen_nacional_min = 5
        configuracion.cambio_eta_min = 30
        configuracion.save()
        vuelo = vuelo_de(empresa)
        assert monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 29)).recogida_propuesta is None
        resultado = monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 30))
        assert resultado.recogida_propuesta == vuelo.hora_programada + timedelta(minutes=35)

    def test_nunca_cambia_la_recogida_sin_confirmar(self, empresa):
        """RN-02."""
        vuelo = vuelo_de(empresa)
        antes = vuelo.viaje.recogida_en
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 60))
        vuelo.viaje.refresh_from_db()
        assert vuelo.viaje.recogida_en == antes

    def test_si_la_eta_vuelve_se_quita_la_propuesta(self, empresa):
        vuelo = vuelo_de(empresa)
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 40))
        resultado = monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 5))
        assert (resultado.recogida_propuesta, resultado.propuesta_en) == (None, None)

    def test_si_la_eta_sigue_cambiando_se_actualiza(self, empresa):
        vuelo = vuelo_de(empresa)
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 40))
        resultado = monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 70))
        assert resultado.recogida_propuesta == vuelo.hora_programada + timedelta(minutes=90)

    def test_si_ya_es_esa_hora_no_propone(self, empresa):
        vuelo = vuelo_de(empresa)
        recogida = vuelo.hora_programada + timedelta(minutes=60)
        type(vuelo.viaje).objects.filter(pk=vuelo.viaje_id).update(recogida_en=recogida)
        assert monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 40)).recogida_propuesta is None

    @pytest.mark.parametrize("estado", [V.CANCELADO, V.DESVIADO])
    def test_vuelo_cancelado_o_desviado_no_propone(self, empresa, estado):
        vuelo = vuelo_de(empresa)
        assert monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 40, estado)).recogida_propuesta is None

    @pytest.mark.parametrize("estado", [E.EN_ZONA, E.PASAJERO_A_BORDO])
    def test_conductor_ya_en_el_lugar_no_propone(self, empresa, estado):
        vuelo = vuelo_de(empresa, estado=estado)
        assert monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 40)).recogida_propuesta is None

    def test_guarda_lo_informado(self, empresa):
        vuelo = vuelo_de(empresa)
        resultado = monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 20, V.DEMORADO))
        assert resultado.estado_vuelo == V.DEMORADO
        assert resultado.hora_estimada == vuelo.hora_programada + timedelta(minutes=20)
        assert resultado.ultima_consulta_en is not None


@pytest.mark.django_db
class TestConfirmar:
    def rutas(self, vuelo):
        return (
            reverse("viaje-confirmar-recogida", args=[vuelo.viaje_id]),
            reverse("viaje-descartar-recogida", args=[vuelo.viaje_id]),
        )

    def con_propuesta(self, empresa, **cambios):
        vuelo = vuelo_de(empresa, **cambios)
        return monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 40))

    def test_confirmar_cambia_la_recogida_y_audita(self, api, empresa, despachador):
        vuelo = self.con_propuesta(empresa)
        anterior = vuelo.viaje.recogida_en
        propuesta = vuelo.recogida_propuesta
        cuerpo = {"recogida_propuesta": propuesta.isoformat()}
        respuesta = api.post(self.rutas(vuelo)[0], cuerpo, format="json")
        assert respuesta.status_code == 200, respuesta.data
        vuelo.refresh_from_db()
        vuelo.viaje.refresh_from_db()
        assert vuelo.viaje.recogida_en == propuesta
        assert vuelo.recogida_propuesta is None
        auditoria = Auditoria.objects.get(accion="AJUSTE_RECOGIDA")
        assert (auditoria.usuario, auditoria.entidad_id) == (despachador, vuelo.viaje_id)
        assert auditoria.datos_previos["recogida_en"] == anterior.isoformat()

    def test_descartar_mantiene_la_recogida_y_audita(self, api, empresa):
        vuelo = self.con_propuesta(empresa)
        anterior = vuelo.viaje.recogida_en
        cuerpo = {"recogida_propuesta": vuelo.recogida_propuesta.isoformat()}
        assert api.post(self.rutas(vuelo)[1], cuerpo, format="json").status_code == 200
        vuelo.refresh_from_db()
        vuelo.viaje.refresh_from_db()
        assert vuelo.viaje.recogida_en == anterior
        assert vuelo.recogida_propuesta is None
        assert Auditoria.objects.filter(accion="DESCARTE_RECOGIDA").exists()

    def test_la_misma_eta_no_se_vuelve_a_proponer(self, api, empresa):
        vuelo = self.con_propuesta(empresa)
        cuerpo = {"recogida_propuesta": vuelo.recogida_propuesta.isoformat()}
        api.post(self.rutas(vuelo)[1], cuerpo, format="json")
        vuelo.refresh_from_db()
        assert monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 40)).recogida_propuesta is None
        # Un cambio nuevo de 15 min o más, respecto de esa ETA, sí.
        assert monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 55)).recogida_propuesta is not None

    def test_si_cambio_mientras_la_miraba_no_confirma(self, api, empresa):
        vuelo = self.con_propuesta(empresa)
        vieja = vuelo.recogida_propuesta.isoformat()
        monitoreo.aplicar(vuelo.pk, datos_con(vuelo, 70))
        respuesta = api.post(self.rutas(vuelo)[0], {"recogida_propuesta": vieja}, format="json")
        assert (respuesta.status_code, respuesta.json()["code"]) == (409, "propuesta_no_vigente")
        vuelo.viaje.refresh_from_db()
        assert vuelo.viaje.recogida_en != vuelo.hora_programada + timedelta(minutes=60)

    def test_sin_propuesta_409(self, api, empresa):
        vuelo = vuelo_de(empresa)
        cuerpo = {"recogida_propuesta": timezone.now().isoformat()}
        assert api.post(self.rutas(vuelo)[0], cuerpo, format="json").status_code == 409

    def test_viaje_que_ya_no_admite_ajuste_409(self, api, empresa):
        vuelo = self.con_propuesta(empresa)
        type(vuelo.viaje).objects.filter(pk=vuelo.viaje_id).update(estado=E.PASAJERO_A_BORDO)
        cuerpo = {"recogida_propuesta": vuelo.recogida_propuesta.isoformat()}
        assert api.post(self.rutas(vuelo)[0], cuerpo, format="json").status_code == 409

    def test_otra_empresa_404(self, api, otra_empresa):
        """RN-13."""
        vuelo = self.con_propuesta(otra_empresa)
        cuerpo = {"recogida_propuesta": vuelo.recogida_propuesta.isoformat()}
        assert api.post(self.rutas(vuelo)[0], cuerpo, format="json").status_code == 404

    def test_el_panel_recibe_la_propuesta(self, api, empresa):
        vuelo = self.con_propuesta(empresa)
        datos = api.get(reverse("viaje-detail", args=[vuelo.viaje_id])).json()["vuelo"]
        assert datos["recogida_propuesta"] is not None
        assert datos["propuesta_en"] is not None


class ConsultorFalso:
    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.consultas = 0

    def consultar(self, numero, hora):
        self.consultas += 1
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


@pytest.mark.django_db
class TestTareas:
    def usar(self, monkeypatch, *respuestas):
        consultor = ConsultorFalso(*respuestas)
        monkeypatch.setattr(tareas, "obtener_consultor_vuelos", lambda: consultor)
        return consultor

    def test_el_barrido_encola_solo_lo_que_toca(self, monkeypatch, empresa):
        vuelo = vuelo_de(empresa, en_min=30)
        vuelo_de(empresa, en_min=600)
        consultor = self.usar(monkeypatch, datos_con(vuelo))
        assert tareas.monitorear_vuelos.delay().get() == 1
        assert consultor.consultas == 1
        vuelo.refresh_from_db()
        assert vuelo.ultima_consulta_en is not None

    def test_reintenta_con_espera_exponencial(self, monkeypatch, empresa):
        vuelo = vuelo_de(empresa, en_min=30)
        consultor = self.usar(
            monkeypatch, VuelosNoDisponibles("x"), VuelosNoDisponibles("x"), datos_con(vuelo, 40)
        )
        esperas = []
        original = tareas.consultar_estado_vuelo.retry

        def retry(*args, countdown=None, **kwargs):
            esperas.append(countdown)
            return original(*args, countdown=countdown, **kwargs)

        monkeypatch.setattr(tareas.consultar_estado_vuelo, "retry", retry)
        tareas.consultar_estado_vuelo.delay(vuelo.pk)
        assert esperas == [30, 60]
        assert consultor.consultas == 3
        vuelo.refresh_from_db()
        assert vuelo.recogida_propuesta is not None

    def test_agotados_los_reintentos_no_rompe_y_lo_registra(self, monkeypatch, empresa, caplog):
        vuelo = vuelo_de(empresa, en_min=30)
        self.usar(monkeypatch, *[VuelosNoDisponibles("x") for _ in range(4)])
        tareas.consultar_estado_vuelo.delay(vuelo.pk)
        assert "sin datos" in caplog.text
        vuelo.refresh_from_db()
        assert vuelo.ultima_consulta_en is None

    def test_no_aparece_en_la_api(self, monkeypatch, empresa, caplog):
        vuelo = vuelo_de(empresa, en_min=30)
        self.usar(monkeypatch, None)
        tareas.consultar_estado_vuelo.delay(vuelo.pk)
        assert "sin datos" in caplog.text

    def test_dos_barridos_seguidos_no_duplican_la_consulta(self, monkeypatch, empresa):
        """Mientras una consulta sigue reintentando, el siguiente barrido no lanza otra."""
        vuelo = vuelo_de(empresa, en_min=30)
        consultor = self.usar(monkeypatch)
        assert tareas.reservar_consulta(vuelo.pk) is True
        assert tareas.monitorear_vuelos.delay().get() == 0
        assert consultor.consultas == 0

    def test_vuelo_borrado_no_rompe(self, monkeypatch):
        consultor = self.usar(monkeypatch)
        tareas.consultar_estado_vuelo.delay(999999)
        assert consultor.consultas == 0

    def test_beat_lo_programa_cada_minuto(self, settings):
        tarea = settings.CELERY_BEAT_SCHEDULE["monitorear-vuelos-hu27"]
        assert (tarea["task"], tarea["schedule"]) == (
            "apps.aeropuerto.tareas.monitorear_vuelos",
            timedelta(seconds=60),
        )
