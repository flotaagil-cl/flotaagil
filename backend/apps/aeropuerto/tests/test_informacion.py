"""HU-69: información de vuelos para el panel y la app (solo lectura de la base)."""

from datetime import datetime, time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.aeropuerto import informacion
from apps.aeropuerto.models import EstadoVuelo, Vuelo
from apps.cuentas.tests.fabricas import UsuarioFactory
from apps.reservas.asignacion import datos_para_la_app
from apps.reservas.models import Asignacion, EstadoViaje, OrigenSugerencia, Sentido, TipoVuelo
from apps.reservas.tests.fabricas import ConductorFactory, ViajeFactory

URL = reverse("vuelos-de-hoy")
pytestmark = pytest.mark.django_db


def hoy_a_las(hora, minuto=0, dias=0):
    dia = timezone.localdate() + timedelta(days=dias)
    return timezone.make_aware(datetime.combine(dia, time(hora, minuto)))


def llegada(empresa, hora, *, dias=0, estado_viaje=EstadoViaje.SOLICITADO, **vuelo):
    programada = hoy_a_las(hora, dias=dias)
    viaje = ViajeFactory(
        empresa=empresa,
        estado=estado_viaje,
        sentido=Sentido.DESDE_AEROPUERTO,
        recogida_en=programada + timedelta(minutes=20),
        motivo_cancelacion="Prueba sintética" if estado_viaje == EstadoViaje.CANCELADO else None,
    )
    datos = {"numero": "LA845", "fecha": programada.date(), "hora_programada": programada} | vuelo
    Vuelo.objects.create(viaje=viaje, **datos)
    return viaje


def salida(empresa, hora, tipo=TipoVuelo.NACIONAL, dias=0):
    despegue = hoy_a_las(hora, dias=dias)
    return ViajeFactory(
        empresa=empresa,
        sentido=Sentido.HACIA_AEROPUERTO,
        recogida_en=despegue - timedelta(hours=3),
        vuelo_salida_en=despegue,
        vuelo_salida_tipo=tipo,
    )


def asignar(viaje, empresa):
    return Asignacion.objects.create(
        viaje=viaje,
        conductor=ConductorFactory(usuario__empresa=empresa),
        despachador=UsuarioFactory(empresa=empresa, rol="DESPACHADOR"),
        origen_sugerencia=OrigenSugerencia.values[0],
        enviada_en=timezone.now(),
    )


@pytest.fixture
def api(panel, despachador):
    panel.force_authenticate(despachador)
    return panel


class TestCalculos:
    @pytest.mark.parametrize(
        ("origen", "estimada_min", "internacional", "margen"),
        [
            (None, None, None, "margen_nacional_min"),  # sin origen: nacional, sin decir que lo es (DC-12)
            ("SCFA", None, False, "margen_nacional_min"),
            ("SAEZ", 40, True, "margen_internacional_min"),
        ],
    )
    def test_recogida_sugerida_con_el_margen(self, empresa, origen, estimada_min, internacional, margen):
        programada = hoy_a_las(12)
        estimada = programada + timedelta(minutes=estimada_min) if estimada_min else None
        viaje = llegada(empresa, 12, origen_icao=origen, hora_estimada=estimada)
        configuracion = empresa.configuracion
        datos = informacion.datos_del_vuelo(viaje.vuelo, configuracion)
        minutos = getattr(configuracion, margen)
        assert datos == {
            "internacional": internacional,
            "margen_min": minutos,
            "recogida_sugerida": (estimada or programada) + timedelta(minutes=minutos),
        }

    @pytest.mark.parametrize(
        ("tipo", "antelacion"),
        [
            (TipoVuelo.NACIONAL, "antelacion_vuelo_nacional_min"),
            (TipoVuelo.INTERNACIONAL, "antelacion_vuelo_internacional_min"),
        ],
    )
    def test_salida_debe_estar_en_el_aeropuerto(self, empresa, tipo, antelacion):
        viaje = salida(empresa, 18, tipo)
        minutos = getattr(empresa.configuracion, antelacion)
        esperado = hoy_a_las(18) - timedelta(minutes=minutos)
        assert informacion.en_aeropuerto_a_las(viaje, empresa.configuracion) == esperado

    def test_la_antelacion_es_la_de_la_empresa(self, empresa):
        empresa.configuracion.antelacion_vuelo_nacional_min = 90
        empresa.configuracion.save()
        viaje = salida(empresa, 18)
        assert informacion.en_aeropuerto_a_las(viaje, empresa.configuracion) == hoy_a_las(16, 30)

    def test_sin_salida_no_hay_hora(self, empresa):
        assert informacion.en_aeropuerto_a_las(llegada(empresa, 12), empresa.configuracion) is None


class TestVuelosDeHoy:
    def test_lista_los_del_dia_de_su_empresa_en_orden(self, api, empresa, otra_empresa):
        tarde = llegada(empresa, 15, hora_estimada=hoy_a_las(15, 40), estado_vuelo=EstadoVuelo.DEMORADO)
        temprano = salida(empresa, 9)
        cancelado = llegada(empresa, 11, estado_vuelo=EstadoVuelo.CANCELADO)
        llegada(empresa, 10, dias=1)  # mañana
        salida(empresa, 10, dias=-1)  # ayer
        llegada(empresa, 13, estado_viaje=EstadoViaje.CANCELADO)  # viaje cancelado
        ViajeFactory(empresa=empresa, recogida_en=hoy_a_las(12))  # urbano
        llegada(otra_empresa, 12)  # RN-13
        datos = api.get(URL).json()
        assert datos["fecha"] == timezone.localdate().isoformat()
        assert [v["id"] for v in datos["viajes"]] == [temprano.pk, cancelado.pk, tarde.pk]
        assert datos["contadores"] == {
            "demorados": 1,
            "cancelados_o_desviados": 1,
            "sin_conductor": 3,
            "propuestas_pendientes": 0,
        }

    def test_filtros_por_tipo_y_estado_sin_cambiar_los_contadores(self, api, empresa):
        demorado = llegada(empresa, 15, estado_vuelo=EstadoVuelo.DEMORADO, recogida_propuesta=hoy_a_las(16))
        a_tiempo = llegada(empresa, 12)
        de_salida = salida(empresa, 9)
        ids = lambda consulta: [v["id"] for v in api.get(URL, consulta).json()["viajes"]]  # noqa: E731
        assert ids({"tipo": "llegadas"}) == [a_tiempo.pk, demorado.pk]
        assert ids({"tipo": "salidas"}) == [de_salida.pk]
        assert ids({"estado": "DEMORADO"}) == [demorado.pk]
        assert api.get(URL, {"tipo": "salidas"}).json()["contadores"]["propuestas_pendientes"] == 1

    def test_campos_calculados_en_cada_viaje(self, api, empresa):
        llegada(empresa, 12, origen_icao="SAEZ")
        salida(empresa, 20, TipoVuelo.INTERNACIONAL)
        viajes = api.get(URL).json()["viajes"]
        configuracion = empresa.configuracion
        assert viajes[0]["vuelo"]["internacional"] is True
        assert viajes[0]["vuelo"]["margen_min"] == configuracion.margen_internacional_min
        assert viajes[0]["en_aeropuerto_a_las"] is None
        esperado = hoy_a_las(20) - timedelta(minutes=configuracion.antelacion_vuelo_internacional_min)
        assert viajes[1]["vuelo"] is None
        assert viajes[1]["en_aeropuerto_a_las"] == timezone.localtime(esperado).isoformat()

    def test_conductor_asignado_no_cuenta_como_sin_conductor(self, api, empresa):
        viaje = llegada(empresa, 12)
        viaje.conductor = ConductorFactory(usuario__empresa=empresa)
        viaje.save()
        assert api.get(URL).json()["contadores"]["sin_conductor"] == 0

    @pytest.mark.parametrize("consulta", [{"tipo": "todas"}, {"estado": "ATRASADO"}])
    def test_parametros_invalidos(self, api, consulta):
        assert api.get(URL, consulta).status_code == 400

    def test_el_administrador_tambien(self, panel, administrador, empresa):
        panel.force_authenticate(administrador)
        assert panel.get(URL).status_code == 200

    @pytest.mark.parametrize("rol", ["CONDUCTOR", "PASAJERO", "CONVENIO"])
    def test_otros_roles_no(self, panel, empresa, rol):
        panel.force_authenticate(UsuarioFactory(empresa=empresa, rol=rol))
        assert panel.get(URL).status_code == 403

    def test_sin_sesion(self, panel):
        assert panel.get(URL).status_code == 401


class TestApp:
    def test_la_asignacion_lleva_el_estado_del_vuelo(self, empresa):
        viaje = llegada(empresa, 12, estado_vuelo=EstadoVuelo.DEMORADO, hora_estimada=hoy_a_las(12, 40))
        asignacion = asignar(viaje, empresa)
        datos = datos_para_la_app(asignacion)
        assert datos["vuelo"]["estado_vuelo"] == "DEMORADO"
        assert datos["en_aeropuerto_a_las"] is None

    def test_la_asignacion_de_una_salida_dice_la_hora_en_el_aeropuerto(self, empresa):
        viaje = salida(empresa, 18)
        asignacion = asignar(viaje, empresa)
        minutos = empresa.configuracion.antelacion_vuelo_nacional_min
        esperado = hoy_a_las(18) - timedelta(minutes=minutos)
        assert datos_para_la_app(asignacion)["en_aeropuerto_a_las"] == esperado.isoformat()

    @pytest.mark.parametrize("es_salida", [False, True])
    def test_viaje_activo_con_el_vuelo(self, cliente, empresa, es_salida):
        chofer = ConductorFactory(usuario__empresa=empresa)
        viaje = (
            salida(empresa, 18) if es_salida else llegada(empresa, 12, estado_vuelo=EstadoVuelo.ATERRIZADO)
        )
        viaje.conductor, viaje.estado = chofer, EstadoViaje.ACEPTADO
        viaje.save()
        cliente.force_authenticate(chofer.usuario)
        datos = cliente.get(reverse("app-viaje-activo")).json()["viaje"]
        if es_salida:
            assert datos["detalle_vuelo"] is None and datos["en_aeropuerto_a_las"]
        else:
            assert datos["detalle_vuelo"]["estado_vuelo"] == "ATERRIZADO"
            assert datos["en_aeropuerto_a_las"] is None
