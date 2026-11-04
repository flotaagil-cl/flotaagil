"""HU-29 · Fila virtual del aeropuerto. CP-19: ingreso y orden. CP-20: salida y propuesta (RN-16)."""

from datetime import timedelta

import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.gis.geos import Polygon
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.aeropuerto import fila, tareas
from apps.aeropuerto.models import FilaAeropuerto, Geocerca, MotivoSalidaFila
from apps.cuentas.tests.fabricas import EmpresaFactory
from apps.flota.models import ConductorVehiculo, EstadoConductor, PosicionGps
from apps.reservas.models import Asignacion, EstadoViaje, OrigenSugerencia, Sentido
from apps.reservas.tests.fabricas import ConductorFactory, VehiculoFactory, ViajeFactory
from config.asgi import application

DENTRO = (-33.393, -70.785)
FUERA = (-33.45, -70.66)
M = MotivoSalidaFila


@pytest.fixture
def zona(empresa):
    return Geocerca.objects.create(
        empresa=empresa,
        nombre="Aeropuerto SCL",
        poligono=Polygon(
            ((-70.82, -33.42), (-70.76, -33.42), (-70.76, -33.37), (-70.82, -33.37), (-70.82, -33.42)),
            srid=4326,
        ),
    )


def conductor_de(empresa, nombre="Pedro Soto", **cambios):
    vehiculo = VehiculoFactory(empresa=empresa)
    conductor = ConductorFactory(
        usuario__empresa=empresa,
        usuario__nombre=nombre,
        estado=EstadoConductor.DISPONIBLE,
        vehiculo_activo=vehiculo,
        consentimiento_gps_en=timezone.now(),
        **cambios,
    )
    ConductorVehiculo.objects.create(conductor=conductor, vehiculo=vehiculo)
    return conductor


def app(conductor):
    cliente = APIClient()
    cliente.force_authenticate(conductor.usuario)
    return cliente


def enviar(conductor, lugar=DENTRO, precision=8, hace_s=0):
    cuerpo = {
        "posiciones": [
            {
                "lat": lugar[0],
                "lon": lugar[1],
                "precision_m": precision,
                "registrada_en": (timezone.now() - timedelta(seconds=hace_s)).isoformat(),
            }
        ]
    }
    respuesta = app(conductor).post(reverse("app-posiciones"), cuerpo, format="json")
    assert respuesta.status_code == 201, respuesta.data


def en_fila(conductor):
    return fila.abiertas().filter(conductor=conductor).exists()


def envejecer(conductor, minutos):
    """Como si todo lo de este conductor hubiera pasado hace `minutos`."""
    delta = timedelta(minutes=minutos)
    for posicion in PosicionGps.objects.filter(conductor=conductor):
        PosicionGps.objects.filter(pk=posicion.pk).update(registrada_en=posicion.registrada_en - delta)
    for entrada in fila.abiertas().filter(conductor=conductor):
        FilaAeropuerto.objects.filter(pk=entrada.pk).update(ingreso_en=entrada.ingreso_en - delta)


@pytest.mark.django_db
class TestIngreso:
    def test_entra_al_llegar_estando_disponible(self, empresa, zona):
        conductor = conductor_de(empresa)
        enviar(conductor)
        entrada = fila.abiertas().get(conductor=conductor)
        assert entrada.geocerca == zona
        assert entrada.salida_en is None

    def test_fuera_de_la_zona_no_entra(self, empresa, zona):
        conductor = conductor_de(empresa)
        enviar(conductor, FUERA)
        assert not en_fila(conductor)

    def test_gps_impreciso_no_entra(self, empresa, zona):
        conductor = conductor_de(empresa)
        enviar(conductor, precision=51)
        assert not en_fila(conductor)

    def test_no_disponible_no_entra(self, empresa, zona):
        conductor = conductor_de(empresa)
        type(conductor).objects.filter(pk=conductor.pk).update(estado=EstadoConductor.EN_VIAJE)
        enviar(conductor)
        assert not en_fila(conductor)

    def test_con_viaje_en_ejecucion_no_entra(self, empresa, zona):
        conductor = conductor_de(empresa)
        ViajeFactory(empresa=empresa, conductor=conductor, estado=EstadoViaje.ASIGNADO)
        enviar(conductor)
        assert not en_fila(conductor)

    def test_seguir_dentro_no_duplica_ni_pierde_el_lugar(self, empresa, zona):
        conductor = conductor_de(empresa)
        enviar(conductor, hace_s=60)
        ingreso = fila.abiertas().get(conductor=conductor).ingreso_en
        enviar(conductor)
        assert fila.abiertas().get(conductor=conductor).ingreso_en == ingreso

    def test_una_posicion_atrasada_no_da_un_lugar_viejo(self, empresa, zona):
        conductor = conductor_de(empresa)
        enviar(conductor, hace_s=11 * 60)
        assert not en_fila(conductor)

    def test_la_geocerca_de_otra_empresa_no_cuenta(self, empresa, zona):
        """RN-13."""
        otra = EmpresaFactory()
        conductor = conductor_de(otra)
        enviar(conductor)
        assert not en_fila(conductor)

    def test_una_entrada_abierta_por_conductor(self, empresa, zona):
        conductor = conductor_de(empresa)
        FilaAeropuerto.objects.create(geocerca=zona, conductor=conductor)
        with pytest.raises(IntegrityError), transaction.atomic():
            FilaAeropuerto.objects.create(geocerca=zona, conductor=conductor)


@pytest.mark.django_db
class TestOrden:
    def test_orden_de_ingreso_a_la_geocerca(self, empresa, zona):
        primero, segundo, tercero = (conductor_de(empresa, n) for n in ("Uno", "Dos", "Tres"))
        enviar(primero, hace_s=120)
        enviar(segundo, hace_s=60)
        enviar(tercero)
        assert fila.posiciones_en_fila(empresa.pk) == {primero.pk: 1, segundo.pk: 2, tercero.pk: 3}

    def test_al_salir_el_primero_todos_avanzan(self, empresa, zona):
        primero, segundo = conductor_de(empresa, "Uno"), conductor_de(empresa, "Dos")
        enviar(primero, hace_s=60)
        enviar(segundo)
        assert fila.salir(primero, M.ASIGNADO) is True
        assert fila.posiciones_en_fila(empresa.pk) == {segundo.pk: 1}

    def test_el_conductor_ve_su_lugar(self, empresa, zona):
        """RN-16."""
        primero, segundo = conductor_de(empresa, "Uno"), conductor_de(empresa, "Dos")
        enviar(primero, hace_s=60)
        enviar(segundo)
        datos = app(segundo).get(reverse("app-perfil")).json()["fila"]
        assert (datos["posicion"], datos["total"], datos["zona"]) == (2, 2, "Aeropuerto SCL")
        assert app(conductor_de(empresa, "Otro")).get(reverse("app-perfil")).json()["fila"] is None


@pytest.mark.django_db
class TestSalida:
    def test_tras_el_tiempo_fuera_de_la_zona(self, empresa, zona):
        conductor = conductor_de(empresa)
        enviar(conductor)
        envejecer(conductor, 11)
        enviar(conductor, FUERA)
        assert fila.revisar() == 1
        entrada = FilaAeropuerto.objects.get(conductor=conductor)
        assert entrada.motivo_salida == M.FUERA_ZONA
        assert entrada.salida_en is not None

    def test_salir_un_momento_no_hace_perder_el_lugar(self, empresa, zona):
        conductor = conductor_de(empresa)
        enviar(conductor)
        envejecer(conductor, 9)
        enviar(conductor, FUERA)
        assert fila.revisar() == 0
        assert en_fila(conductor)

    def test_sigue_dentro_con_posiciones_recientes(self, empresa, zona):
        conductor = conductor_de(empresa)
        enviar(conductor)
        envejecer(conductor, 30)
        enviar(conductor)
        assert fila.revisar() == 0
        assert en_fila(conductor)

    def test_sin_senal_tambien_sale(self, empresa, zona):
        """DC-21: no se puede confirmar que siga en la zona."""
        conductor = conductor_de(empresa)
        enviar(conductor)
        envejecer(conductor, 11)
        assert fila.revisar() == 1
        assert FilaAeropuerto.objects.get(conductor=conductor).motivo_salida == M.FUERA_ZONA

    def test_la_tolerancia_es_configurable_por_empresa(self, empresa, zona):
        configuracion = empresa.configuracion
        configuracion.tolerancia_fila_min = 30
        configuracion.save()
        conductor = conductor_de(empresa)
        enviar(conductor)
        envejecer(conductor, 11)
        assert fila.revisar() == 0

    def test_al_pasar_a_no_disponible(self, empresa, zona):
        conductor = conductor_de(empresa)
        enviar(conductor)
        respuesta = app(conductor).post(reverse("app-turno"), {"estado": "NO_DISPONIBLE"}, format="json")
        assert respuesta.status_code == 200
        assert FilaAeropuerto.objects.get(conductor=conductor).motivo_salida == M.NO_DISPONIBLE

    def test_la_revision_saca_a_quien_cambio_de_estado_por_otra_via(self, empresa, zona):
        conductor = conductor_de(empresa)
        enviar(conductor)
        type(conductor).objects.filter(pk=conductor.pk).update(estado=EstadoConductor.NO_DISPONIBLE)
        assert tareas.revisar_fila.delay().get() == 1
        assert FilaAeropuerto.objects.get(conductor=conductor).motivo_salida == M.NO_DISPONIBLE

    def test_la_revision_no_repite_efectos(self, empresa, zona):
        conductor = conductor_de(empresa)
        enviar(conductor)
        envejecer(conductor, 11)
        assert fila.revisar() == 1
        assert fila.revisar() == 0


@pytest.mark.django_db
class TestPropuesta:
    @pytest.fixture
    def api(self, cliente, despachador):
        cliente.force_authenticate(despachador)
        return cliente

    @pytest.fixture
    def recogida(self, empresa):
        return ViajeFactory(empresa=empresa, estado=EstadoViaje.SOLICITADO, sentido=Sentido.DESDE_AEROPUERTO)

    def filas(self, api, viaje):
        return api.get(reverse("viaje-candidatos", args=[viaje.pk])).json()

    def test_propone_al_primero_de_la_fila(self, api, empresa, zona, recogida):
        """RN-16, aunque otro esté más cerca."""
        conductor_de(empresa, "Sin fila")
        primero, segundo = conductor_de(empresa, "Primero"), conductor_de(empresa, "Segundo")
        enviar(primero, hace_s=120)
        enviar(segundo, hace_s=60)
        datos = self.filas(api, recogida)
        assert [(f["nombre"], f["posicion_fila"], f["sugerido"]) for f in datos] == [
            ("Primero", 1, True),
            ("Segundo", 2, False),
            ("Sin fila", None, False),
        ]

    def test_sin_fila_no_sugiere(self, api, empresa, zona, recogida):
        conductor_de(empresa, "Sin fila")
        assert [f["sugerido"] for f in self.filas(api, recogida)] == [False]

    def test_viaje_urbano_no_usa_la_fila(self, api, empresa, zona):
        viaje = ViajeFactory(empresa=empresa, estado=EstadoViaje.SOLICITADO, sentido=Sentido.URBANO)
        conductor = conductor_de(empresa, "En fila")
        enviar(conductor)
        filas = self.filas(api, viaje)
        assert filas[0]["posicion_fila"] == 1

    def test_al_ser_asignado_sale_y_queda_el_origen(self, api, empresa, zona, recogida):
        primero, segundo = conductor_de(empresa, "Primero"), conductor_de(empresa, "Segundo")
        enviar(primero, hace_s=60)
        enviar(segundo)
        url = reverse("viaje-asignar", args=[recogida.pk])
        assert api.post(url, {"conductor": primero.pk}, format="json").status_code == 200
        assert Asignacion.objects.get().origen_sugerencia == OrigenSugerencia.FILA
        assert FilaAeropuerto.objects.get(conductor=primero).motivo_salida == M.ASIGNADO
        assert fila.posiciones_en_fila(empresa.pk) == {segundo.pk: 1}

    def test_saltarse_la_fila_queda_manual(self, api, empresa, zona, recogida):
        """RN-02: el despachador decide."""
        primero, segundo = conductor_de(empresa, "Primero"), conductor_de(empresa, "Segundo")
        enviar(primero, hace_s=60)
        enviar(segundo)
        url = reverse("viaje-asignar", args=[recogida.pk])
        assert api.post(url, {"conductor": segundo.pk}, format="json").status_code == 200
        assert Asignacion.objects.get().origen_sugerencia == OrigenSugerencia.MANUAL
        assert en_fila(primero)

    def test_si_rechaza_vuelve_al_final(self, api, empresa, zona, recogida):
        """DC-21."""
        primero, segundo = conductor_de(empresa, "Primero"), conductor_de(empresa, "Segundo")
        enviar(primero, hace_s=60)
        enviar(segundo)
        api.post(reverse("viaje-asignar", args=[recogida.pk]), {"conductor": primero.pk}, format="json")
        app(primero).post(reverse("app-rechazar", args=[Asignacion.objects.get().pk]))
        enviar(primero)
        assert fila.posiciones_en_fila(empresa.pk) == {segundo.pk: 1, primero.pk: 2}


@pytest.mark.django_db(transaction=True)
def test_quien_sale_tambien_se_entera(empresa, zona):
    """Ya no está en la fila, pero su app debe dejar de mostrarla."""
    conductor = conductor_de(empresa)
    token = str(AccessToken.for_user(conductor.usuario))
    enviar(conductor)

    @database_sync_to_async
    def sale():
        with transaction.atomic():
            fila.salir(conductor, M.FUERA_ZONA)

    async def prueba():
        com = WebsocketCommunicator(application, "/ws/conductor/", subprotocols=["flotaagil", token])
        await com.connect()
        await sale()
        mensaje = await com.receive_json_from(timeout=2)
        await com.disconnect()
        return mensaje

    assert async_to_sync(prueba)() == {"tipo": "fila"}


@pytest.mark.django_db(transaction=True)
def test_la_app_se_entera_cuando_cambia_la_fila(empresa, zona):
    primero, segundo = conductor_de(empresa, "Primero"), conductor_de(empresa, "Segundo")
    token = str(AccessToken.for_user(segundo.usuario))

    @database_sync_to_async
    def entra(conductor, hace_s=0):
        enviar(conductor, hace_s=hace_s)

    @database_sync_to_async
    def sale(conductor):
        with transaction.atomic():
            fila.salir(conductor, M.ASIGNADO)

    async def prueba():
        com = WebsocketCommunicator(application, "/ws/conductor/", subprotocols=["flotaagil", token])
        await com.connect()
        await entra(primero, 60)
        await entra(segundo)
        entro = await com.receive_json_from(timeout=2)
        await sale(primero)
        avanzo = await com.receive_json_from(timeout=2)
        await com.disconnect()
        return entro, avanzo

    assert async_to_sync(prueba)() == ({"tipo": "fila"}, {"tipo": "fila"})
