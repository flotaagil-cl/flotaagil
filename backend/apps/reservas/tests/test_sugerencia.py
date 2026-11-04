"""HU-04 · Sugerencia del conductor más apto (urbano). CP-18."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.flota.models import PosicionGps
from apps.reservas.models import (
    Actor,
    Asignacion,
    EstadoViaje,
    HistorialEstado,
    OrigenSugerencia,
    Sentido,
)
from apps.reservas.tests.fabricas import ViajeFactory
from apps.reservas.tests.test_asignacion import asignar_url, disponible

E = EstadoViaje

# El origen de la fábrica es el centro de Santiago (-33.4489). 0,01° de latitud son unos 1,1 km.
A_100_M = -33.4498
A_600_M = -33.4543
A_3_KM = -33.4759
A_3_5_KM = -33.4804


@pytest.fixture
def api(cliente, despachador):
    cliente.force_authenticate(despachador)
    return cliente


@pytest.fixture
def solicitado(empresa):
    return ViajeFactory(empresa=empresa, estado=E.SOLICITADO, sentido=Sentido.URBANO)


def filas(api, viaje):
    return api.get(reverse("viaje-candidatos", args=[viaje.pk])).json()


def nombres(api, viaje):
    return [f["nombre"] for f in filas(api, viaje)]


def termino_viaje(empresa, conductor, hace_horas):
    viaje = ViajeFactory(empresa=empresa, conductor=conductor, estado=E.FINALIZADO)
    registro = HistorialEstado.objects.create(viaje=viaje, estado_nuevo=E.FINALIZADO, actor=Actor.CONDUCTOR)
    HistorialEstado.objects.filter(pk=registro.pk).update(
        creado_en=timezone.now() - timedelta(hours=hace_horas)
    )


def envejecer_posicion(conductor, segundos):
    PosicionGps.objects.filter(conductor=conductor).update(
        registrada_en=timezone.now() - timedelta(seconds=segundos)
    )


@pytest.mark.django_db
class TestOrden:
    def test_por_distancia_si_la_diferencia_es_de_1_km_o_mas(self, api, empresa, solicitado):
        lejos = disponible(empresa, "Lejos", lat=A_3_KM)
        cerca = disponible(empresa, "Cerca", lat=A_100_M)
        termino_viaje(empresa, cerca, hace_horas=0)  # acaba de terminar: igual gana por distancia
        termino_viaje(empresa, lejos, hace_horas=9)
        assert nombres(api, solicitado) == ["Cerca", "Lejos"]

    def test_a_menos_de_1_km_gana_quien_lleva_mas_tiempo_sin_viaje(self, api, empresa, solicitado):
        reciente = disponible(empresa, "Reciente", lat=A_100_M)
        antiguo = disponible(empresa, "Antiguo", lat=A_600_M)
        termino_viaje(empresa, reciente, hace_horas=1)
        termino_viaje(empresa, antiguo, hace_horas=5)
        assert nombres(api, solicitado) == ["Antiguo", "Reciente"]

    def test_sin_viajes_terminados_es_quien_lleva_mas_tiempo(self, api, empresa, solicitado):
        con_viaje = disponible(empresa, "Con viaje", lat=A_100_M)
        disponible(empresa, "Sin viajes", lat=A_600_M)
        termino_viaje(empresa, con_viaje, hace_horas=48)
        datos = filas(api, solicitado)
        assert [f["nombre"] for f in datos] == ["Sin viajes", "Con viaje"]
        assert datos[0]["ultimo_viaje_en"] is None
        assert datos[1]["ultimo_viaje_en"] is not None

    def test_el_empate_se_aplica_por_grupos(self, api, empresa, solicitado):
        cerca_reciente = disponible(empresa, "Cerca reciente", lat=A_100_M)
        cerca_antiguo = disponible(empresa, "Cerca antiguo", lat=A_600_M)
        lejos_reciente = disponible(empresa, "Lejos reciente", lat=A_3_KM)
        lejos_antiguo = disponible(empresa, "Lejos antiguo", lat=A_3_5_KM)
        termino_viaje(empresa, cerca_reciente, 1)
        termino_viaje(empresa, cerca_antiguo, 2)
        termino_viaje(empresa, lejos_reciente, 1)
        termino_viaje(empresa, lejos_antiguo, 2)
        assert nombres(api, solicitado) == [
            "Cerca antiguo",
            "Cerca reciente",
            "Lejos antiguo",
            "Lejos reciente",
        ]


@pytest.mark.django_db
class TestSugerido:
    def test_sugiere_solo_al_primero_y_el_resto_queda_disponible(self, api, empresa, solicitado):
        disponible(empresa, "Cerca", lat=A_100_M)
        disponible(empresa, "Lejos", lat=A_3_KM)
        disponible(empresa, "Sin posición")
        datos = filas(api, solicitado)
        assert [(f["nombre"], f["sugerido"]) for f in datos] == [
            ("Cerca", True),
            ("Lejos", False),
            ("Sin posición", False),
        ]

    def test_posicion_antigua_no_compite(self, api, empresa, solicitado):
        """Una posición de hace media hora no dice dónde está: no le gana a una reciente."""
        antiguo = disponible(empresa, "Antigua", lat=A_100_M)
        disponible(empresa, "Reciente", lat=A_3_KM)
        envejecer_posicion(antiguo, 1800)
        datos = filas(api, solicitado)
        assert [f["nombre"] for f in datos] == ["Reciente", "Antigua"]
        assert datos[0]["sugerido"] is True
        assert datos[1]["confiable"] is False

    def test_posicion_imprecisa_no_compite(self, api, empresa, solicitado):
        impreciso = disponible(empresa, "Imprecisa", lat=A_100_M)
        disponible(empresa, "Precisa", lat=A_3_KM)
        PosicionGps.objects.filter(conductor=impreciso).update(precision_m=101)
        assert nombres(api, solicitado) == ["Precisa", "Imprecisa"]

    def test_sin_posiciones_confiables_no_sugiere(self, api, empresa, solicitado):
        antiguo = disponible(empresa, "Antigua", lat=A_100_M)
        envejecer_posicion(antiguo, 1800)
        disponible(empresa, "Sin posición")
        assert [f["sugerido"] for f in filas(api, solicitado)] == [False, False]

    def test_el_conductor_no_disponible_no_aparece(self, api, empresa, solicitado):
        """RN-01."""
        conductor = disponible(empresa, "Ocupado", lat=A_100_M)
        ViajeFactory(empresa=empresa, conductor=conductor, estado=E.EN_CAMINO)
        assert filas(api, solicitado) == []

    def test_consultar_no_asigna(self, api, empresa, solicitado):
        """RN-02: la sugerencia nunca asigna sin confirmación."""
        disponible(empresa, "Cerca", lat=A_100_M)
        filas(api, solicitado)
        solicitado.refresh_from_db()
        assert solicitado.estado == E.SOLICITADO
        assert solicitado.conductor is None
        assert not Asignacion.objects.exists()

    @pytest.mark.parametrize("sentido", [Sentido.DESDE_AEROPUERTO])
    def test_recogida_en_aeropuerto_no_usa_la_distancia(self, api, empresa, sentido):
        """Se delega en la fila virtual (HU-29)."""
        disponible(empresa, "Cerca", lat=A_100_M)
        viaje = ViajeFactory(empresa=empresa, estado=E.SOLICITADO, sentido=sentido)
        assert [f["sugerido"] for f in filas(api, viaje)] == [False]


@pytest.mark.django_db
class TestOrigenDeLaAsignacion:
    def test_elegir_al_sugerido_queda_como_distancia(self, api, empresa, solicitado):
        cerca = disponible(empresa, "Cerca", lat=A_100_M)
        disponible(empresa, "Lejos", lat=A_3_KM)
        assert api.post(asignar_url(solicitado), {"conductor": cerca.pk}, format="json").status_code == 200
        assert Asignacion.objects.get().origen_sugerencia == OrigenSugerencia.DISTANCIA

    def test_elegir_a_otro_queda_como_manual(self, api, empresa, solicitado):
        disponible(empresa, "Cerca", lat=A_100_M)
        lejos = disponible(empresa, "Lejos", lat=A_3_KM)
        assert api.post(asignar_url(solicitado), {"conductor": lejos.pk}, format="json").status_code == 200
        assert Asignacion.objects.get().origen_sugerencia == OrigenSugerencia.MANUAL

    def test_sin_sugerencia_queda_como_manual(self, api, empresa, solicitado):
        conductor = disponible(empresa, "Sin posición")
        api.post(asignar_url(solicitado), {"conductor": conductor.pk}, format="json")
        assert Asignacion.objects.get().origen_sugerencia == OrigenSugerencia.MANUAL
