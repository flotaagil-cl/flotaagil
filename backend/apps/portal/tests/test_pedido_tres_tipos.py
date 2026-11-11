"""HU-39: pedido en tres tipos (desde el aeropuerto, al aeropuerto, en la ciudad) con pasajeros y maletas.

DC-42: VIAJE guarda pasajeros, maletas y el vuelo de salida; antelación configurable por empresa.
DC-43: titular más acompañantes no superan la mayor capacidad de la flota activa, y no se asigna un
vehículo de menor capacidad.
"""

from datetime import date, datetime, time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.integraciones.vuelos import VuelosNoDisponibles
from apps.reservas import servicios as reservas
from apps.reservas.models import EstadoViaje, Viaje
from apps.reservas.tests.fabricas import VehiculoFactory, ViajeFactory
from apps.reservas.tests.test_asignacion import disponible

from .test_portal import en_horas, solicitud

URL = "mi-cuenta-solicitudes"


def pedir(cliente, **cambios):
    return cliente.post(reverse(URL), solicitud(**cambios), format="json")


@pytest.mark.django_db
class TestEnLaCiudad:
    def test_lo_antes_posible_es_ahora_mas_la_anticipacion(self, con_cuenta, empresa):
        antes = timezone.now()
        respuesta = pedir(con_cuenta, recogida_en=None, lo_antes_posible=True)
        assert respuesta.status_code == 201, respuesta.data
        recogida = Viaje.objects.get().recogida_en
        minimo = antes + timedelta(minutes=empresa.configuracion.anticipacion_minima_min)
        assert minimo <= recogida <= minimo + timedelta(minutes=2)
        assert recogida.second == 0

    def test_lo_antes_posible_ignora_la_hora_enviada(self, con_cuenta, empresa):
        assert pedir(con_cuenta, recogida_en=en_horas(-5), lo_antes_posible=True).status_code == 201

    def test_programado_sigue_pidiendo_la_hora(self, con_cuenta):
        respuesta = pedir(con_cuenta, recogida_en=None)
        assert respuesta.status_code == 400
        assert "recogida_en" in respuesta.data

    def test_guarda_pasajeros_y_maletas(self, con_cuenta):
        assert pedir(con_cuenta, pasajeros=3, maletas=4).status_code == 201
        viaje = Viaje.objects.get()
        assert (viaje.pasajeros, viaje.maletas) == (3, 4)

    def test_por_defecto_uno_y_sin_maletas(self, con_cuenta):
        pedir(con_cuenta)
        viaje = Viaje.objects.get()
        assert (viaje.pasajeros, viaje.maletas) == (1, 0)

    @pytest.mark.parametrize(
        "campo,valor", [("pasajeros", 0), ("pasajeros", 8), ("maletas", -1), ("maletas", 21)]
    )
    def test_limites(self, con_cuenta, campo, valor):
        assert pedir(con_cuenta, **{campo: valor}).status_code == 400


@pytest.mark.django_db
class TestAlAeropuerto:
    def salida(self, tipo, horas=10):
        return {"hora": en_horas(horas), "tipo": tipo}

    @pytest.mark.parametrize("tipo,antelacion", [("INTERNACIONAL", 180), ("NACIONAL", 120)])
    def test_recogida_sugerida_segun_el_tipo(self, con_cuenta, tipo, antelacion):
        salida = self.salida(tipo)
        respuesta = pedir(
            con_cuenta,
            sentido="HACIA_AEROPUERTO",
            recogida_en=None,
            vuelo_salida=salida,
            destino_dir="Aeropuerto SCL",
        )
        assert respuesta.status_code == 201, respuesta.data
        viaje = Viaje.objects.get()
        hora = datetime.fromisoformat(salida["hora"])
        assert viaje.recogida_en == hora - timedelta(minutes=antelacion)
        assert (viaje.vuelo_salida_en, viaje.vuelo_salida_tipo) == (hora, tipo)

    def test_antelacion_configurable(self, con_cuenta, empresa):
        empresa.configuracion.antelacion_vuelo_internacional_min = 240
        empresa.configuracion.save()
        salida = self.salida("INTERNACIONAL")
        pedir(con_cuenta, sentido="HACIA_AEROPUERTO", recogida_en=None, vuelo_salida=salida)
        hora = datetime.fromisoformat(salida["hora"])
        assert Viaje.objects.get().recogida_en == hora - timedelta(minutes=240)

    def test_la_recogida_editada_se_respeta(self, con_cuenta):
        recogida = en_horas(5)
        pedir(
            con_cuenta, sentido="HACIA_AEROPUERTO", recogida_en=recogida, vuelo_salida=self.salida("NACIONAL")
        )
        assert Viaje.objects.get().recogida_en == datetime.fromisoformat(recogida)

    def test_sugerida_en_el_pasado_se_rechaza(self, con_cuenta):
        respuesta = pedir(
            con_cuenta,
            sentido="HACIA_AEROPUERTO",
            recogida_en=None,
            vuelo_salida=self.salida("INTERNACIONAL", 2),
        )
        assert respuesta.status_code == 400
        assert "recogida_en" in respuesta.data

    def test_vuelo_de_salida_solo_al_aeropuerto(self, con_cuenta):
        respuesta = pedir(con_cuenta, sentido="URBANO", vuelo_salida=self.salida("NACIONAL"))
        assert respuesta.status_code == 400
        assert "vuelo_salida" in respuesta.data

    def test_tipo_invalido(self, con_cuenta):
        salida = {"hora": en_horas(10), "tipo": "REGIONAL"}
        assert pedir(con_cuenta, sentido="HACIA_AEROPUERTO", vuelo_salida=salida).status_code == 400


class ConsultorCaido:
    def consultar(self, numero, llegada_informada):
        raise VuelosNoDisponibles("sin respuesta")


@pytest.mark.django_db
class TestDesdeElAeropuerto:
    def manana(self) -> date:
        return timezone.localdate() + timedelta(days=1)

    def test_con_numero_y_fecha_la_hora_la_da_la_api(self, con_cuenta, empresa):
        respuesta = pedir(
            con_cuenta,
            recogida_en=None,
            origen_dir="Aeropuerto de Santiago (SCL)",
            vuelo={"numero": "LA845", "fecha": self.manana().isoformat()},
        )
        assert respuesta.status_code == 201, respuesta.data
        viaje = Viaje.objects.get()
        # El consultor de desarrollo devuelve la hora consultada (mediodía de ese día).
        llegada = timezone.make_aware(datetime.combine(self.manana(), time(12)))
        assert viaje.recogida_en == llegada + timedelta(minutes=empresa.configuracion.margen_nacional_min)
        assert viaje.sentido == "DESDE_AEROPUERTO"

    def test_sin_respuesta_de_la_api_pide_la_hora(self, con_cuenta, monkeypatch):
        monkeypatch.setattr(reservas, "obtener_consultor_vuelos", ConsultorCaido)
        respuesta = pedir(
            con_cuenta, recogida_en=None, vuelo={"numero": "LA845", "fecha": self.manana().isoformat()}
        )
        assert respuesta.status_code == 400
        assert "hora de llegada" in str(respuesta.data["vuelo"]["hora_llegada"][0])
        assert not Viaje.objects.exists()

    def test_sin_fecha_ni_hora(self, con_cuenta):
        respuesta = pedir(con_cuenta, recogida_en=None, vuelo={"numero": "LA845"})
        assert respuesta.status_code == 400
        assert "fecha" in respuesta.data["vuelo"]


@pytest.mark.django_db
class TestCapacidad:
    def test_la_empresa_publica_su_capacidad_maxima(self, cliente, empresa):
        ruta = reverse("portal-empresa", args=[empresa.slug])
        assert cliente.get(ruta).data["capacidad_maxima"] is None
        VehiculoFactory(empresa=empresa, capacidad=4)
        VehiculoFactory(empresa=empresa, capacidad=7, activo=False)
        VehiculoFactory(empresa=empresa, capacidad=6)
        datos = cliente.get(ruta).data
        assert datos["capacidad_maxima"] == 6
        assert (datos["antelacion_vuelo_nacional_min"], datos["antelacion_vuelo_internacional_min"]) == (
            120,
            180,
        )

    def test_no_supera_la_mayor_capacidad_activa(self, con_cuenta, empresa):
        VehiculoFactory(empresa=empresa, capacidad=4)
        VehiculoFactory(empresa=empresa, capacidad=7, activo=False)
        respuesta = pedir(con_cuenta, pasajeros=5)
        assert respuesta.status_code == 400
        assert "hasta 4 pasajeros" in str(respuesta.data["pasajeros"][0])
        assert pedir(con_cuenta, pasajeros=4).status_code == 201

    def test_sin_vehiculos_activos_no_limita(self, con_cuenta):
        assert pedir(con_cuenta, pasajeros=6).status_code == 201

    def test_al_asignar_exige_la_capacidad_del_vehiculo(self, cliente, despachador, empresa):
        cliente.force_authenticate(despachador)
        viaje = ViajeFactory(empresa=empresa, estado=EstadoViaje.SOLICITADO, pasajeros=5)
        chico = disponible(empresa, nombre="Pedro Soto")
        chico.vehiculo_activo.capacidad = 4
        chico.vehiculo_activo.save()
        grande = disponible(empresa, nombre="Rosa Díaz")
        grande.vehiculo_activo.capacidad = 6
        grande.vehiculo_activo.save()
        candidatos = cliente.get(reverse("viaje-candidatos", args=[viaje.pk])).json()
        assert [c["id"] for c in candidatos] == [grande.pk]
        respuesta = cliente.post(
            reverse("viaje-asignar", args=[viaje.pk]), {"conductor": chico.pk}, format="json"
        )
        assert respuesta.status_code == 409, respuesta.data
        assert "lleva hasta 4 pasajeros" in respuesta.json()["detail"]
        viaje.refresh_from_db()
        assert viaje.estado == EstadoViaje.SOLICITADO
        assert (
            cliente.post(
                reverse("viaje-asignar", args=[viaje.pk]), {"conductor": grande.pk}, format="json"
            ).status_code
            == 200
        )

    def test_el_panel_ve_los_datos_nuevos(self, cliente, despachador, empresa):
        cliente.force_authenticate(despachador)
        ViajeFactory(empresa=empresa, pasajeros=2, maletas=3)
        fila = cliente.get(reverse("viaje-list")).json()["results"][0]
        assert (fila["pasajeros"], fila["maletas"], fila["vuelo_salida_en"], fila["vuelo_salida_tipo"]) == (
            2,
            3,
            None,
            None,
        )
