"""HU-01 · Panel de indicadores de reservas y vehículos."""

import asyncio
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

from apps.flota.models import ConductorVehiculo, EstadoConductor, PosicionGps
from apps.reservas.models import EstadoViaje
from apps.reservas.tests.fabricas import ConductorFactory, VehiculoFactory, ViajeFactory
from config.asgi import application

URL = reverse("indicadores")
ORIGEN = (b"origin", b"http://localhost:5173")
E = EstadoViaje


def hoy_a_las(hora, minuto=0):
    ahora = timezone.localtime()
    return ahora.replace(hour=hora, minute=minuto, second=0, microsecond=0)


def en_turno(empresa, estado=EstadoConductor.DISPONIBLE, **vehiculo):
    v = VehiculoFactory(empresa=empresa, **vehiculo)
    conductor = ConductorFactory(
        usuario__empresa=empresa, estado=estado, vehiculo_activo=v, consentimiento_gps_en=timezone.now()
    )
    ConductorVehiculo.objects.create(conductor=conductor, vehiculo=v)
    return conductor


def posicion(conductor, hace_s=1):
    return PosicionGps.objects.create(
        conductor=conductor,
        punto=Point(-70.66, -33.45, srid=4326),
        precision_m=7,
        registrada_en=timezone.now() - timedelta(seconds=hace_s),
    )


@pytest.fixture
def api(cliente, despachador):
    cliente.force_authenticate(despachador)
    return cliente


def por_estado(datos):
    return {f["estado"]: f["cantidad"] for f in datos["reservas"]["por_estado"]}


@pytest.mark.django_db
class TestReservas:
    def test_del_dia_por_estado_con_todos_los_estados(self, api, empresa):
        ViajeFactory(empresa=empresa, estado=E.SOLICITADO, recogida_en=hoy_a_las(10))
        ViajeFactory(empresa=empresa, estado=E.SOLICITADO, recogida_en=hoy_a_las(12))
        ViajeFactory(empresa=empresa, estado=E.FINALIZADO, recogida_en=hoy_a_las(8))
        datos = api.get(URL).json()
        conteo = por_estado(datos)
        assert (conteo[E.SOLICITADO], conteo[E.FINALIZADO], conteo[E.EN_CAMINO]) == (2, 1, 0)
        assert set(conteo) == set(E.values)
        assert datos["reservas"]["total"] == 3
        assert datos["fecha"] == timezone.localdate().isoformat()

    def test_excluye_otros_dias(self, api, empresa):
        ViajeFactory(empresa=empresa, recogida_en=hoy_a_las(10) - timedelta(days=1))
        ViajeFactory(empresa=empresa, recogida_en=hoy_a_las(10) + timedelta(days=1))
        assert api.get(URL).json()["reservas"]["total"] == 0

    def test_el_dia_es_el_de_chile_no_el_de_utc(self, api, empresa):
        """A las 23:30 de Chile ya es el día siguiente en UTC."""
        ViajeFactory(empresa=empresa, recogida_en=hoy_a_las(23, 30))
        ViajeFactory(empresa=empresa, recogida_en=hoy_a_las(0, 30))
        assert api.get(URL).json()["reservas"]["total"] == 2

    def test_otra_empresa_no_cuenta(self, api, otra_empresa):
        """RN-13."""
        ViajeFactory(empresa=otra_empresa, recogida_en=hoy_a_las(10))
        en_turno(otra_empresa)
        datos = api.get(URL).json()
        assert datos["reservas"]["total"] == 0
        assert datos["vehiculos"] == {
            "en_linea": 0,
            "en_linea_con_senal": 0,
            "en_linea_sin_senal": 0,
            "fuera_de_linea": 0,
        }


@pytest.mark.django_db
class TestVehiculos:
    def test_en_linea_y_fuera_de_linea(self, api, empresa):
        posicion(en_turno(empresa))
        en_turno(empresa, EstadoConductor.EN_VIAJE)
        VehiculoFactory(empresa=empresa)
        assert api.get(URL).json()["vehiculos"] == {
            "en_linea": 2,
            "en_linea_con_senal": 1,
            "en_linea_sin_senal": 1,
            "fuera_de_linea": 1,
        }

    @pytest.mark.parametrize(("hace_s", "con_senal"), [(5, 1), (59, 1), (61, 0), (3600, 0)])
    def test_con_senal_hasta_60_s_desde_la_ultima_posicion(self, api, empresa, hace_s, con_senal):
        """El mismo criterio de HU-02."""
        posicion(en_turno(empresa), hace_s=hace_s)
        vehiculos = api.get(URL).json()["vehiculos"]
        assert (vehiculos["en_linea_con_senal"], vehiculos["en_linea_sin_senal"]) == (
            con_senal,
            1 - con_senal,
        )

    def test_sin_ninguna_posicion_no_tiene_senal(self, api, empresa):
        en_turno(empresa)
        vehiculos = api.get(URL).json()["vehiculos"]
        assert (vehiculos["en_linea_con_senal"], vehiculos["en_linea_sin_senal"]) == (0, 1)

    def test_vale_la_ultima_posicion(self, api, empresa):
        conductor = en_turno(empresa)
        posicion(conductor, hace_s=3600)
        posicion(conductor, hace_s=5)
        assert api.get(URL).json()["vehiculos"]["en_linea_con_senal"] == 1

    def test_el_limite_es_configurable(self, api, empresa, settings):
        settings.POSICION_CONFIABLE_SEGUNDOS = 600
        posicion(en_turno(empresa), hace_s=300)
        assert api.get(URL).json()["vehiculos"]["en_linea_con_senal"] == 1

    def test_inactivo_no_cuenta(self, api, empresa):
        VehiculoFactory(empresa=empresa, activo=False)
        vehiculos = api.get(URL).json()["vehiculos"]
        assert (vehiculos["en_linea"], vehiculos["fuera_de_linea"]) == (0, 0)

    def test_conductor_no_disponible_deja_el_vehiculo_fuera(self, api, empresa):
        conductor = en_turno(empresa)
        conductor.estado = EstadoConductor.NO_DISPONIBLE
        conductor.vehiculo_activo = None
        conductor.save()
        vehiculos = api.get(URL).json()["vehiculos"]
        assert (vehiculos["en_linea"], vehiculos["fuera_de_linea"]) == (0, 1)

    def test_cuenta_deshabilitada_no_cuenta(self, api, empresa):
        conductor = en_turno(empresa)
        conductor.usuario.activo = False
        conductor.usuario.save()
        vehiculos = api.get(URL).json()["vehiculos"]
        assert (vehiculos["en_linea"], vehiculos["fuera_de_linea"]) == (0, 1)


@pytest.mark.django_db
class TestPermisos:
    def test_administrador_si_conductor_no_anonimo_no(self, cliente, administrador, conductor):
        assert cliente.get(URL).status_code == 401
        cliente.force_authenticate(conductor)
        assert cliente.get(URL).status_code == 403
        cliente.force_authenticate(administrador)
        assert cliente.get(URL).status_code == 200


def comunicador(token, origen=ORIGEN):
    return WebsocketCommunicator(
        application,
        "/ws/indicadores/",
        headers=[origen] if origen else [],
        subprotocols=["flotaagil", token] if token else [],
    )


@database_sync_to_async
def como(usuario, metodo, ruta, datos=None):
    api = APIClient()
    api.force_authenticate(usuario)
    return getattr(api, metodo)(ruta, datos or {}, format="json").status_code


@pytest.mark.django_db(transaction=True)
class TestAvisoEnVivo:
    def escuchar(self, usuario, accion):
        async def prueba():
            ws = comunicador(str(AccessToken.for_user(usuario)))
            conectado, _ = await ws.connect()
            assert conectado
            assert await ws.receive_json_from() == {"tipo": "inicial"}
            await accion()
            mensaje = await ws.receive_json_from(timeout=5)
            await ws.disconnect()
            return mensaje

        return async_to_sync(prueba)()

    def test_sin_token_cierra_4401(self):
        async def prueba():
            return await comunicador(None).connect()

        assert async_to_sync(prueba)() == (False, 4401)

    def test_conductor_cierra_4403(self, empresa):
        token = str(AccessToken.for_user(ConductorFactory(usuario__empresa=empresa).usuario))

        async def prueba():
            return await comunicador(token).connect()

        assert async_to_sync(prueba)() == (False, 4403)

    def test_origen_ajeno_no_conecta(self, despachador):
        async def prueba():
            ws = comunicador(str(AccessToken.for_user(despachador)), (b"origin", b"http://otro.example"))
            return (await ws.connect())[0]

        assert async_to_sync(prueba)() is False

    def test_con_el_access_vencido_cierra_4401_y_no_avisa(self, despachador, empresa):
        """El panel renueva y se reconecta."""
        viaje = ViajeFactory(empresa=empresa)
        token = AccessToken.for_user(despachador)
        token.set_exp(lifetime=timedelta(seconds=1))

        async def prueba():
            ws = comunicador(str(token))
            await ws.connect()
            await ws.receive_json_from()
            await asyncio.sleep(1.1)
            ruta = reverse("viaje-cancelar", args=[viaje.pk])
            assert await como(despachador, "post", ruta, {"motivo": "Prueba"}) == 200
            return await ws.receive_output(timeout=5)

        assert async_to_sync(prueba)() == {"type": "websocket.close", "code": 4401}

    def test_crear_una_reserva_avisa(self, despachador):
        cuerpo = {
            "pasajero": {"nombre": "Ana", "telefono": "+56900009001"},
            "canal": "TELEFONO",
            "origen_dir": "Plaza de Armas, Santiago",
            "destino_dir": "Av. Providencia 1234, Providencia",
            "recogida_en": (timezone.now() + timedelta(hours=2)).isoformat(),
        }

        async def accion():
            assert await como(despachador, "post", reverse("viaje-list"), cuerpo) == 201

        assert self.escuchar(despachador, accion) == {"tipo": "cambio"}

    def test_cancelar_una_reserva_avisa(self, despachador, empresa):
        viaje = ViajeFactory(empresa=empresa)

        async def accion():
            ruta = reverse("viaje-cancelar", args=[viaje.pk])
            assert await como(despachador, "post", ruta, {"motivo": "Prueba"}) == 200

        assert self.escuchar(despachador, accion) == {"tipo": "cambio"}

    def test_empezar_el_turno_avisa(self, despachador, empresa):
        conductor = ConductorFactory(usuario__empresa=empresa, consentimiento_gps_en=timezone.now())
        ConductorVehiculo.objects.create(conductor=conductor, vehiculo=VehiculoFactory(empresa=empresa))

        async def accion():
            ruta = reverse("app-turno")
            assert await como(conductor.usuario, "post", ruta, {"estado": "DISPONIBLE"}) == 200

        assert self.escuchar(despachador, accion) == {"tipo": "cambio"}

    def test_desactivar_un_vehiculo_avisa(self, administrador, empresa):
        vehiculo = VehiculoFactory(empresa=empresa)

        async def accion():
            ruta = reverse("vehiculo-detail", args=[vehiculo.pk])
            assert await como(administrador, "patch", ruta, {"activo": False}) == 200

        assert self.escuchar(administrador, accion) == {"tipo": "cambio"}

    def test_otra_empresa_no_avisa(self, despachador, otra_empresa):
        from apps.cuentas.tests.fabricas import UsuarioFactory

        viaje = ViajeFactory(empresa=otra_empresa)
        ajeno = UsuarioFactory(empresa=otra_empresa, rol="DESPACHADOR")

        async def prueba():
            ws = comunicador(str(AccessToken.for_user(despachador)))
            await ws.connect()
            await ws.receive_json_from()
            ruta = reverse("viaje-cancelar", args=[viaje.pk])
            assert await como(ajeno, "post", ruta, {"motivo": "Prueba"}) == 200
            nada = await ws.receive_nothing(timeout=0.5)
            await ws.disconnect()
            return nada

        assert async_to_sync(prueba)() is True

    def enviar_posicion_y_escuchar(self, despachador, conductor):
        cuerpo = {
            "posiciones": [
                {
                    "lat": -33.45,
                    "lon": -70.66,
                    "precision_m": 7,
                    "registrada_en": (timezone.now() - timedelta(seconds=1)).isoformat(),
                }
            ]
        }

        async def prueba():
            ws = comunicador(str(AccessToken.for_user(despachador)))
            await ws.connect()
            await ws.receive_json_from()
            assert await como(conductor.usuario, "post", reverse("app-posiciones"), cuerpo) == 201
            nada = await ws.receive_nothing(timeout=0.5)
            await ws.disconnect()
            return nada

        return async_to_sync(prueba)()

    def test_una_posicion_con_senal_vigente_no_avisa(self, despachador, empresa):
        conductor = en_turno(empresa)
        posicion(conductor, hace_s=10)
        assert self.enviar_posicion_y_escuchar(despachador, conductor) is True

    def test_recuperar_la_senal_avisa(self, despachador, empresa):
        conductor = en_turno(empresa)
        posicion(conductor, hace_s=120)
        assert self.enviar_posicion_y_escuchar(despachador, conductor) is False

    def test_la_primera_posicion_del_conductor_avisa(self, despachador, empresa):
        assert self.enviar_posicion_y_escuchar(despachador, en_turno(empresa)) is False
