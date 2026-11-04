"""HU-16 · Estados y pago. CP-15: secuencia y EN_ZONA por geocerca. CP-16: pago obligatorio (RN-10)."""

from datetime import timedelta

import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.gis.geos import Point
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.flota.models import ConductorVehiculo, EstadoConductor
from apps.reservas import ejecucion, estados
from apps.reservas.models import Actor, EstadoViaje, HistorialEstado, PagoViaje
from apps.reservas.tests.fabricas import ConductorFactory, ConvenioFactory, VehiculoFactory, ViajeFactory
from config.asgi import application

ORIGEN = Point(-70.6100, -33.4260, srid=4326)
E = EstadoViaje


@pytest.fixture
def chofer(empresa):
    vehiculo = VehiculoFactory(empresa=empresa)
    conductor = ConductorFactory(
        usuario__empresa=empresa,
        estado=EstadoConductor.EN_VIAJE,
        vehiculo_activo=vehiculo,
        consentimiento_gps_en=timezone.now(),
    )
    ConductorVehiculo.objects.create(conductor=conductor, vehiculo=vehiculo)
    return conductor


def viaje_de(chofer, estado, **cambios):
    viaje = ViajeFactory(
        empresa=chofer.usuario.empresa,
        conductor=chofer,
        vehiculo=chofer.vehiculo_activo,
        estado=estado,
        origen_geo=ORIGEN,
        **cambios,
    )
    HistorialEstado.objects.create(viaje=viaje, estado_nuevo=estado, actor=Actor.DESPACHADOR)
    return viaje


def app(conductor):
    cliente = APIClient()
    cliente.force_authenticate(conductor.usuario)
    return cliente


def url(nombre, viaje):
    return reverse(f"app-{nombre}", args=[viaje.pk])


def posicion(lat, precision=8, segundos=0):
    return {
        "lat": lat,
        "lon": -70.6100,
        "precision_m": precision,
        "registrada_en": (timezone.now() + timedelta(seconds=segundos)).isoformat(),
    }


def enviar(conductor, *posiciones):
    return app(conductor).post(reverse("app-posiciones"), {"posiciones": list(posiciones)}, format="json")


# 0,001° de latitud son unos 111 m.
CERCA = -33.4270  # ~111 m del origen
LEJOS = -33.4300  # ~445 m del origen


@pytest.mark.django_db
class TestSecuencia:
    def test_camino_completo(self, chofer):
        viaje = viaje_de(chofer, E.ACEPTADO, tarifa=15000)
        cliente = app(chofer)
        assert cliente.post(url("en-camino", viaje)).json() == {"viaje": viaje.pk, "estado": "EN_CAMINO"}
        assert enviar(chofer, posicion(CERCA)).status_code == 201
        viaje.refresh_from_db()
        assert viaje.estado == E.EN_ZONA
        assert cliente.post(url("a-bordo", viaje)).json()["estado"] == "PASAJERO_A_BORDO"
        respuesta = cliente.post(
            url("finalizar", viaje), {"metodo": "EFECTIVO", "monto": 15000}, format="json"
        )
        assert respuesta.json()["estado"] == "FINALIZADO"
        chofer.refresh_from_db()
        assert chofer.estado == EstadoConductor.DISPONIBLE
        actores = list(
            HistorialEstado.objects.filter(viaje=viaje).order_by("id").values_list("estado_nuevo", "actor")
        )
        assert actores[1:] == [
            (E.EN_CAMINO, Actor.CONDUCTOR),
            (E.EN_ZONA, Actor.SISTEMA),
            (E.PASAJERO_A_BORDO, Actor.CONDUCTOR),
            (E.FINALIZADO, Actor.CONDUCTOR),
        ]

    @pytest.mark.parametrize(
        ("accion", "estado"),
        [
            ("en-camino", E.EN_CAMINO),
            ("a-bordo", E.ACEPTADO),
            ("a-bordo", E.PASAJERO_A_BORDO),
        ],
    )
    def test_fuera_de_secuencia(self, chofer, accion, estado):
        respuesta = app(chofer).post(url(accion, viaje_de(chofer, estado)))
        assert (respuesta.status_code, respuesta.json()["code"]) == (409, "estado_no_permitido")

    def test_sin_geocerca_el_conductor_igual_puede_seguir(self, chofer):
        """DC-17: con el GPS impreciso no queda bloqueado; el historial muestra que lo indicó él."""
        viaje = viaje_de(chofer, E.EN_CAMINO)
        assert app(chofer).post(url("a-bordo", viaje)).json()["estado"] == "PASAJERO_A_BORDO"
        cambio = HistorialEstado.objects.get(viaje=viaje, estado_nuevo=E.EN_ZONA)
        assert cambio.actor == Actor.CONDUCTOR
        assert cambio.manual is True
        assert cambio.distancia_m is None  # no envió ninguna posición desde que salió

    def test_manual_guarda_la_distancia_de_la_ultima_posicion(self, chofer):
        """DC-20: 0,004° de latitud son unos 445 m."""
        viaje = viaje_de(chofer, E.EN_CAMINO)
        enviar(chofer, posicion(LEJOS - 0.004), posicion(LEJOS, segundos=1))
        app(chofer).post(url("a-bordo", viaje))
        cambio = HistorialEstado.objects.get(viaje=viaje, estado_nuevo=E.EN_ZONA)
        assert cambio.manual is True
        assert 435 <= cambio.distancia_m <= 455

    def test_posicion_de_antes_de_salir_no_cuenta_como_distancia(self, chofer):
        viaje = viaje_de(chofer, E.EN_CAMINO)
        enviar(chofer, posicion(LEJOS, segundos=-120))
        app(chofer).post(url("a-bordo", viaje))
        assert HistorialEstado.objects.get(viaje=viaje, estado_nuevo=E.EN_ZONA).distancia_m is None

    def test_la_geocerca_no_es_manual(self, chofer):
        viaje = viaje_de(chofer, E.EN_CAMINO)
        enviar(chofer, posicion(CERCA))
        cambio = HistorialEstado.objects.get(viaje=viaje, estado_nuevo=E.EN_ZONA)
        assert (cambio.manual, cambio.distancia_m, cambio.actor) == (False, None, Actor.SISTEMA)

    def test_el_panel_recibe_la_trazabilidad(self, chofer, despachador):
        viaje = viaje_de(chofer, E.EN_CAMINO)
        enviar(chofer, posicion(LEJOS))
        app(chofer).post(url("a-bordo", viaje))
        cliente = APIClient()
        cliente.force_authenticate(despachador)
        historial = cliente.get(reverse("viaje-detail", args=[viaje.pk])).data["historial"]
        zona = next(c for c in historial if c["estado_nuevo"] == E.EN_ZONA)
        assert zona["manual"] is True
        assert 435 <= zona["distancia_m"] <= 455

    def test_solo_el_conductor_del_viaje(self, chofer, empresa):
        otro = ConductorFactory(usuario__empresa=empresa)
        viaje = viaje_de(chofer, E.ACEPTADO)
        assert app(otro).post(url("en-camino", viaje)).status_code == 400
        viaje.refresh_from_db()
        assert viaje.estado == E.ACEPTADO

    def test_otros_roles(self, cliente, despachador, chofer):
        cliente.force_authenticate(despachador)
        assert cliente.post(url("en-camino", viaje_de(chofer, E.ACEPTADO))).status_code == 403


@pytest.mark.django_db
class TestGeocerca:
    def test_lejos_no_marca(self, chofer):
        viaje = viaje_de(chofer, E.EN_CAMINO)
        enviar(chofer, posicion(LEJOS))
        viaje.refresh_from_db()
        assert viaje.estado == E.EN_CAMINO

    def test_imprecisa_no_marca(self, chofer):
        """PoC H-3, A7: posiciones de ±88 a ±1400 m al iniciar bajo techo."""
        viaje = viaje_de(chofer, E.EN_CAMINO)
        enviar(chofer, posicion(CERCA, precision=51))
        viaje.refresh_from_db()
        assert viaje.estado == E.EN_CAMINO

    def test_la_precision_es_configurable_por_empresa(self, chofer):
        configuracion = chofer.usuario.empresa.configuracion
        configuracion.precision_geocerca_m = 60
        configuracion.save()
        viaje = viaje_de(chofer, E.EN_CAMINO)
        enviar(chofer, posicion(CERCA, precision=51))
        viaje.refresh_from_db()
        assert viaje.estado == E.EN_ZONA

    def test_posicion_anterior_a_salir_no_marca(self, chofer):
        viaje = viaje_de(chofer, E.EN_CAMINO)
        enviar(chofer, posicion(CERCA, segundos=-120))
        viaje.refresh_from_db()
        assert viaje.estado == E.EN_CAMINO

    def test_en_un_lote_basta_una(self, chofer):
        viaje = viaje_de(chofer, E.EN_CAMINO)
        enviar(chofer, posicion(LEJOS), posicion(CERCA, segundos=1))
        viaje.refresh_from_db()
        assert viaje.estado == E.EN_ZONA

    def test_aceptado_no_marca(self, chofer):
        viaje = viaje_de(chofer, E.ACEPTADO)
        enviar(chofer, posicion(CERCA))
        viaje.refresh_from_db()
        assert viaje.estado == E.ACEPTADO

    def test_radio_de_150_m(self):
        assert ejecucion.RADIO_ZONA_M == 150


@pytest.mark.django_db
class TestPago:
    @pytest.mark.parametrize(
        "cuerpo",
        [
            {},
            {"metodo": "EFECTIVO"},
            {"monto": 1000},
            {"metodo": "BITCOIN", "monto": 1000},
            {"metodo": "EFECTIVO", "monto": -1},
            {"metodo": "EFECTIVO", "monto": 500001},
        ],
    )
    def test_metodo_y_monto_obligatorios(self, chofer, cuerpo):
        """RN-10."""
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        assert app(chofer).post(url("finalizar", viaje), cuerpo, format="json").status_code == 400
        viaje.refresh_from_db()
        assert viaje.estado == E.PASAJERO_A_BORDO
        assert not PagoViaje.objects.exists()

    def test_registra_el_pago(self, chofer):
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        app(chofer).post(url("finalizar", viaje), {"metodo": "TARJETA", "monto": 500000}, format="json")
        pago = PagoViaje.objects.get(viaje=viaje)
        assert (pago.metodo, pago.monto, pago.corregido_por) == ("TARJETA", 500000, None)

    def test_monto_cero_es_valido(self, chofer):
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        cuerpo = {"metodo": "EFECTIVO", "monto": 0}
        assert app(chofer).post(url("finalizar", viaje), cuerpo, format="json").status_code == 200

    def test_convenio_solo_en_viajes_de_convenio(self, chofer):
        sin_convenio = viaje_de(chofer, E.PASAJERO_A_BORDO)
        cuerpo = {"metodo": "CONVENIO", "monto": 1000}
        assert "metodo" in app(chofer).post(url("finalizar", sin_convenio), cuerpo, format="json").json()
        convenio = ConvenioFactory(empresa=chofer.usuario.empresa)
        con_convenio = viaje_de(chofer, E.PASAJERO_A_BORDO, canal="CONVENIO", convenio=convenio)
        assert app(chofer).post(url("finalizar", con_convenio), cuerpo, format="json").status_code == 200

    def test_no_finaliza_antes_de_tiempo_ni_dos_veces(self, chofer):
        cuerpo = {"metodo": "EFECTIVO", "monto": 1000}
        assert (
            app(chofer).post(url("finalizar", viaje_de(chofer, E.EN_ZONA)), cuerpo, format="json").status_code
            == 409
        )
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        app(chofer).post(url("finalizar", viaje), cuerpo, format="json")
        assert app(chofer).post(url("finalizar", viaje), cuerpo, format="json").status_code == 409
        assert PagoViaje.objects.filter(viaje=viaje).count() == 1

    def test_no_se_puede_finalizar_sin_pasar_por_el_servicio(self, chofer):
        """FINALIZADO solo se alcanza desde PASAJERO_A_BORDO, por la máquina de estados."""
        assert not estados.es_valida(E.EN_ZONA, E.FINALIZADO)


@pytest.mark.django_db
class TestCancelarViajeEnCurso:
    def test_libera_al_conductor(self, chofer, cliente, despachador):
        viaje = viaje_de(chofer, E.EN_CAMINO)
        cliente.force_authenticate(despachador)
        respuesta = cliente.post(
            reverse("viaje-cancelar", args=[viaje.pk]), {"motivo": "Pasajero avisó"}, format="json"
        )
        assert respuesta.status_code == 200
        chofer.refresh_from_db()
        assert chofer.estado == EstadoConductor.DISPONIBLE

    def test_viaje_activo_incluye_tarifa_y_convenio(self, chofer):
        viaje_de(chofer, E.ACEPTADO, tarifa=15000)
        datos = app(chofer).get(reverse("app-viaje-activo")).json()["viaje"]
        assert (datos["tarifa"], datos["convenio"]) == (15000, False)


@pytest.mark.django_db(transaction=True)
def test_la_app_se_entera_de_en_zona_y_de_la_cancelacion(chofer, despachador):
    viaje = viaje_de(chofer, E.EN_CAMINO)
    token = str(AccessToken.for_user(chofer.usuario))

    @database_sync_to_async
    def llegar():
        enviar(chofer, posicion(CERCA))

    @database_sync_to_async
    def cancelar():
        cliente = APIClient()
        cliente.force_authenticate(despachador)
        return cliente.post(
            reverse("viaje-cancelar", args=[viaje.pk]), {"motivo": "x"}, format="json"
        ).status_code

    async def prueba():
        com = WebsocketCommunicator(application, "/ws/conductor/", subprotocols=["flotaagil", token])
        await com.connect()
        await llegar()
        zona = await com.receive_json_from(timeout=2)
        estado = await cancelar()
        cancelado = await com.receive_json_from(timeout=2)
        await com.disconnect()
        return zona, estado, cancelado

    zona, estado, cancelado = async_to_sync(prueba)()
    assert zona == {"tipo": "viaje", "viaje": viaje.pk}
    assert estado == 200
    assert cancelado == {"tipo": "viaje", "viaje": viaje.pk}


@pytest.mark.django_db(transaction=True)
def test_la_app_se_entera_por_el_canal_de_cada_accion(chofer):
    """Si la respuesta de la API se pierde, la app se corrige con este evento (fix/app-peticiones)."""
    viaje = viaje_de(chofer, E.ACEPTADO)
    token = str(AccessToken.for_user(chofer.usuario))

    @database_sync_to_async
    def accion(nombre, cuerpo=None):
        return app(chofer).post(url(nombre, viaje), cuerpo, format="json").status_code

    async def prueba():
        com = WebsocketCommunicator(application, "/ws/conductor/", subprotocols=["flotaagil", token])
        await com.connect()
        recibidos = []
        pagos = {"metodo": "EFECTIVO", "monto": 1000}
        for nombre, cuerpo in (("en-camino", None), ("a-bordo", None), ("finalizar", pagos)):
            assert await accion(nombre, cuerpo) == 200
            recibidos.append(await com.receive_json_from(timeout=2))
        await com.disconnect()
        return recibidos

    assert async_to_sync(prueba)() == [{"tipo": "viaje", "viaje": viaje.pk}] * 3
