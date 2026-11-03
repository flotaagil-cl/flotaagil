"""API de flota (HU-10): CP-01 (vehículos) y CP-02 (datos del conductor y asociación conductor-vehículo)."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import Auditoria, Entidad
from apps.cuentas.tests.fabricas import UsuarioFactory
from apps.flota.models import ConductorVehiculo, EstadoConductor, Vehiculo
from apps.reservas.models import EstadoViaje
from apps.reservas.tests.fabricas import ConductorFactory, VehiculoFactory, ViajeFactory

VEHICULOS = reverse("vehiculo-list")
CONDUCTORES = reverse("conductor-list")


def vehiculo_url(vehiculo):
    return reverse("vehiculo-detail", args=[vehiculo.pk])


def conductor_url(conductor):
    return reverse("conductor-detail", args=[conductor.pk])


def asociar_url(conductor):
    return reverse("conductor-asociar", args=[conductor.pk])


def desasociar_url(conductor, vehiculo):
    return reverse("conductor-desasociar", args=[conductor.pk, vehiculo.pk])


def auditorias(entidad, entidad_id):
    return list(
        Auditoria.objects.filter(entidad=entidad, entidad_id=entidad_id).values_list("accion", flat=True)
    )


@pytest.fixture
def api(cliente, administrador):
    cliente.force_authenticate(administrador)
    return cliente


@pytest.fixture
def chofer(empresa):
    return ConductorFactory(usuario__empresa=empresa, usuario__nombre="Pedro Soto")


@pytest.fixture
def auto(empresa):
    return VehiculoFactory(empresa=empresa, patente="BCDF10")


@pytest.mark.django_db
class TestPermisos:
    @pytest.mark.parametrize("rol", ["DESPACHADOR", "CONDUCTOR"])
    def test_solo_administrador(self, cliente, empresa, rol):
        cliente.force_authenticate(UsuarioFactory(empresa=empresa, rol=rol))
        assert cliente.get(VEHICULOS).status_code == 403
        assert cliente.get(CONDUCTORES).status_code == 403

    def test_sin_sesion(self, cliente):
        assert cliente.get(VEHICULOS).status_code == 401

    def test_aislamiento_por_empresa(self, api, otra_empresa):
        """RN-13: lo de otra empresa no aparece y su detalle responde 404."""
        ajeno = VehiculoFactory(empresa=otra_empresa)
        conductor_ajeno = ConductorFactory(usuario__empresa=otra_empresa)
        assert api.get(VEHICULOS).json()["count"] == 0
        assert api.get(CONDUCTORES).json()["count"] == 0
        assert api.get(vehiculo_url(ajeno)).status_code == 404
        assert api.patch(vehiculo_url(ajeno), {"activo": False}, format="json").status_code == 404
        assert api.patch(conductor_url(conductor_ajeno), {"nombre": "X"}, format="json").status_code == 404


@pytest.mark.django_db
class TestVehiculos:
    def test_registrar_normaliza_la_patente(self, api, empresa, administrador):
        anio = timezone.localdate().year - 1
        respuesta = api.post(
            VEHICULOS, {"patente": "bc-df 12", "marca_modelo": " Kia   Rio ", "anio": anio}, format="json"
        )
        assert respuesta.status_code == 201, respuesta.json()
        datos = respuesta.json()
        assert (datos["patente"], datos["marca_modelo"], datos["capacidad"], datos["activo"]) == (
            "BCDF12",
            "Kia Rio",
            4,
            True,
        )
        vehiculo = Vehiculo.objects.get(patente="BCDF12")
        assert vehiculo.empresa == empresa
        assert auditorias(Entidad.VEHICULO, vehiculo.pk) == ["CREAR"]

    @pytest.mark.parametrize(
        ("cambios", "campo"),
        [
            ({"patente": "ABC123"}, "patente"),
            ({"anio": 1990}, "anio"),
            ({"capacidad": 8}, "capacidad"),
            ({"marca_modelo": "  "}, "marca_modelo"),
        ],
    )
    def test_registrar_rechaza(self, api, cambios, campo):
        datos = {"patente": "BCDF12", "marca_modelo": "Kia Rio", "anio": timezone.localdate().year} | cambios
        respuesta = api.post(VEHICULOS, datos, format="json")
        assert respuesta.status_code == 400
        assert campo in respuesta.json()

    def test_patente_repetida_aunque_sea_de_otra_empresa(self, api, otra_empresa):
        VehiculoFactory(empresa=otra_empresa, patente="BCDF12")
        datos = {"patente": "BCDF12", "marca_modelo": "Kia Rio", "anio": timezone.localdate().year}
        respuesta = api.post(VEHICULOS, datos, format="json")
        assert respuesta.status_code == 400
        assert respuesta.json()["patente"] == ["Esta patente ya está registrada."]

    def test_listar_con_filtros_y_conductores(self, api, empresa, chofer, auto):
        VehiculoFactory(empresa=empresa, patente="GHJK20", marca_modelo="Hyundai H-1", activo=False)
        ConductorVehiculo.objects.create(conductor=chofer, vehiculo=auto)
        todos = api.get(VEHICULOS).json()
        assert [v["patente"] for v in todos["results"]] == ["BCDF10", "GHJK20"]
        assert todos["results"][0]["conductores"] == [{"id": chofer.pk, "nombre": "Pedro Soto"}]
        assert [v["patente"] for v in api.get(VEHICULOS, {"activo": "false"}).json()["results"]] == ["GHJK20"]
        assert [v["patente"] for v in api.get(VEHICULOS, {"q": "bcdf-10"}).json()["results"]] == ["BCDF10"]
        assert [v["patente"] for v in api.get(VEHICULOS, {"q": "hyundai"}).json()["results"]] == ["GHJK20"]

    def test_editar_no_cambia_la_patente(self, api, auto):
        respuesta = api.patch(vehiculo_url(auto), {"patente": "ZZZZ99", "capacidad": 5}, format="json")
        assert respuesta.status_code == 200
        auto.refresh_from_db()
        assert (auto.patente, auto.capacidad) == ("BCDF10", 5)
        assert auditorias(Entidad.VEHICULO, auto.pk) == ["EDITAR"]
        assert Auditoria.objects.get(entidad=Entidad.VEHICULO).datos_previos == {"capacidad": 4}

    def test_editar_sin_cambios_no_audita(self, api, auto):
        assert api.patch(vehiculo_url(auto), {"capacidad": 4}, format="json").status_code == 200
        assert auditorias(Entidad.VEHICULO, auto.pk) == []

    def test_desactivar_y_reactivar(self, api, auto):
        assert api.patch(vehiculo_url(auto), {"activo": False}, format="json").json()["activo"] is False
        assert api.patch(vehiculo_url(auto), {"activo": True}, format="json").json()["activo"] is True
        assert auditorias(Entidad.VEHICULO, auto.pk) == ["ACTIVAR", "DESACTIVAR"]

    def test_desactivar_libera_la_declaracion_de_un_conductor_fuera_de_turno(self, api, chofer, auto):
        chofer.vehiculo_activo = auto
        chofer.save()
        assert api.patch(vehiculo_url(auto), {"activo": False}, format="json").status_code == 200
        chofer.refresh_from_db()
        assert chofer.vehiculo_activo is None

    @pytest.mark.parametrize("estado", [EstadoConductor.DISPONIBLE, EstadoConductor.EN_VIAJE])
    def test_no_desactiva_un_vehiculo_en_turno(self, api, chofer, auto, estado):
        chofer.vehiculo_activo, chofer.estado = auto, estado
        chofer.save()
        respuesta = api.patch(vehiculo_url(auto), {"activo": False}, format="json")
        assert respuesta.status_code == 409
        assert respuesta.json()["code"] == "flota_en_uso"
        assert "Pedro Soto" in respuesta.json()["detail"]
        auto.refresh_from_db()
        assert auto.activo is True
        assert auditorias(Entidad.VEHICULO, auto.pk) == []

    def test_no_desactiva_un_vehiculo_con_viaje_en_curso(self, api, empresa, auto):
        ViajeFactory(empresa=empresa, vehiculo=auto, estado=EstadoViaje.EN_CAMINO)
        assert api.patch(vehiculo_url(auto), {"activo": False}, format="json").status_code == 409

    def test_un_viaje_terminado_no_impide_desactivar(self, api, empresa, auto):
        ViajeFactory(empresa=empresa, vehiculo=auto, estado=EstadoViaje.FINALIZADO)
        assert api.patch(vehiculo_url(auto), {"activo": False}, format="json").status_code == 200

    def test_no_hay_borrado(self, api, auto):
        assert api.delete(vehiculo_url(auto)).status_code == 405


@pytest.mark.django_db
class TestConductores:
    def test_listar_y_detalle(self, api, empresa, chofer, auto):
        ConductorVehiculo.objects.create(conductor=chofer, vehiculo=auto)
        ConductorFactory(
            usuario__empresa=empresa, usuario__nombre="Ana Ríos", estado=EstadoConductor.NO_DISPONIBLE
        )
        lista = api.get(CONDUCTORES).json()
        assert [c["nombre"] for c in lista["results"]] == ["Ana Ríos", "Pedro Soto"]
        detalle = api.get(conductor_url(chofer)).json()
        assert detalle["licencia_vigente"] is True
        assert detalle["activo"] is True
        assert detalle["vehiculos"] == [
            {
                "id": auto.pk,
                "patente": "BCDF10",
                "marca_modelo": "Toyota Yaris",
                "activo": True,
                "desde": timezone.localdate().isoformat(),
            }
        ]
        assert [c["nombre"] for c in api.get(CONDUCTORES, {"q": "bcdf"}).json()["results"]] == ["Pedro Soto"]
        assert [c["nombre"] for c in api.get(CONDUCTORES, {"q": chofer.rut}).json()["results"]] == [
            "Pedro Soto"
        ]

    def test_filtros_de_estado_y_cuenta(self, api, empresa, chofer):
        ConductorFactory(usuario__empresa=empresa, usuario__activo=False)
        assert api.get(CONDUCTORES, {"activo": "false"}).json()["count"] == 1
        assert api.get(CONDUCTORES, {"estado": "NO_DISPONIBLE"}).json()["count"] == 2
        assert api.get(CONDUCTORES, {"estado": "DISPONIBLE"}).json()["count"] == 0

    def test_editar_datos_normaliza_y_audita(self, api, chofer):
        vence = timezone.localdate() + timedelta(days=700)
        rut_previo = chofer.rut
        respuesta = api.patch(
            conductor_url(chofer),
            {
                "nombre": "  Pedro   Soto Díaz ",
                "rut": "12.345.678-5",
                "telefono": "+56 9 0000 1234",
                "licencia_clase": "A3",
                "licencia_vence": vence.isoformat(),
            },
            format="json",
        )
        assert respuesta.status_code == 200, respuesta.json()
        datos = respuesta.json()
        assert (datos["nombre"], datos["rut"], datos["telefono"], datos["licencia_clase"]) == (
            "Pedro Soto Díaz",
            "12345678-5",
            "+56900001234",
            "A3",
        )
        registro = Auditoria.objects.get(entidad=Entidad.CONDUCTOR, entidad_id=chofer.pk)
        assert registro.accion == "EDITAR"
        assert registro.datos_previos["nombre"] == "Pedro Soto"
        assert registro.datos_previos["rut"] == rut_previo

    @pytest.mark.parametrize(
        ("cambios", "campo"),
        [
            ({"rut": "12345678-9"}, "rut"),
            ({"telefono": "+56212345678"}, "telefono"),
            ({"licencia_vence": "2020-01-01"}, "licencia_vence"),
            ({"licencia_clase": "B"}, "licencia_clase"),
            ({"nombre": "   "}, "nombre"),
        ],
    )
    def test_editar_rechaza(self, api, chofer, cambios, campo):
        respuesta = api.patch(conductor_url(chofer), cambios, format="json")
        assert respuesta.status_code == 400
        assert campo in respuesta.json()

    def test_rut_repetido(self, api, empresa, chofer):
        otro = ConductorFactory(usuario__empresa=empresa)
        respuesta = api.patch(conductor_url(chofer), {"rut": otro.rut}, format="json")
        assert respuesta.json() == {"rut": ["Este RUT ya está registrado."]}
        # El propio RUT no cuenta como repetido.
        assert api.patch(conductor_url(chofer), {"rut": chofer.rut}, format="json").status_code == 200

    def test_email_y_cuenta_no_se_editan_aqui(self, api, chofer):
        email = chofer.usuario.email
        api.patch(conductor_url(chofer), {"email": "otro@x.example", "activo": False}, format="json")
        chofer.usuario.refresh_from_db()
        assert (chofer.usuario.email, chofer.usuario.activo) == (email, True)


@pytest.mark.django_db
class TestAsociacion:
    def test_asociar_y_quitar(self, api, chofer, auto):
        respuesta = api.post(asociar_url(chofer), {"vehiculo": auto.pk}, format="json")
        assert respuesta.status_code == 201
        assert [v["patente"] for v in respuesta.json()["vehiculos"]] == ["BCDF10"]
        respuesta = api.delete(desasociar_url(chofer, auto))
        assert respuesta.status_code == 200
        assert respuesta.json()["vehiculos"] == []
        assert auditorias(Entidad.CONDUCTOR, chofer.pk) == ["DESASOCIAR_VEHICULO", "ASOCIAR_VEHICULO"]

    def test_un_vehiculo_con_varios_conductores(self, api, empresa, chofer, auto):
        """N:M: un vehículo puede estar asociado a varios conductores (y al revés)."""
        otro = ConductorFactory(usuario__empresa=empresa)
        assert api.post(asociar_url(chofer), {"vehiculo": auto.pk}, format="json").status_code == 201
        assert api.post(asociar_url(otro), {"vehiculo": auto.pk}, format="json").status_code == 201
        assert len(api.get(vehiculo_url(auto)).json()["conductores"]) == 2

    def test_no_asocia_vehiculo_de_otra_empresa(self, api, chofer, otra_empresa):
        ajeno = VehiculoFactory(empresa=otra_empresa)
        respuesta = api.post(asociar_url(chofer), {"vehiculo": ajeno.pk}, format="json")
        assert respuesta.status_code == 400
        assert "vehiculo" in respuesta.json()
        assert api.delete(desasociar_url(chofer, ajeno)).status_code == 404

    def test_no_asocia_inactivo_ni_repetido(self, api, empresa, chofer, auto):
        inactivo = VehiculoFactory(empresa=empresa, activo=False)
        assert api.post(asociar_url(chofer), {"vehiculo": inactivo.pk}, format="json").json() == {
            "vehiculo": ["El vehículo está inactivo."]
        }
        api.post(asociar_url(chofer), {"vehiculo": auto.pk}, format="json")
        assert api.post(asociar_url(chofer), {"vehiculo": auto.pk}, format="json").status_code == 400

    def test_quitar_uno_no_asociado(self, api, chofer, auto):
        assert api.delete(desasociar_url(chofer, auto)).status_code == 400

    def test_quitar_el_declarado_fuera_de_turno_borra_la_declaracion(self, api, chofer, auto):
        ConductorVehiculo.objects.create(conductor=chofer, vehiculo=auto)
        chofer.vehiculo_activo = auto
        chofer.save()
        assert api.delete(desasociar_url(chofer, auto)).json()["vehiculo_activo"] is None

    def test_no_quita_el_declarado_en_turno(self, api, empresa, chofer, auto):
        """RN-05: el conductor Disponible sigue con su vehículo declarado."""
        ConductorVehiculo.objects.create(conductor=chofer, vehiculo=auto)
        chofer.vehiculo_activo, chofer.estado = auto, EstadoConductor.DISPONIBLE
        chofer.save()
        respuesta = api.delete(desasociar_url(chofer, auto))
        assert respuesta.status_code == 409
        assert respuesta.json()["code"] == "flota_en_uso"
        assert ConductorVehiculo.objects.filter(conductor=chofer, vehiculo=auto).exists()
        # Otro vehículo del mismo conductor sí se puede quitar.
        otro = VehiculoFactory(empresa=empresa)
        ConductorVehiculo.objects.create(conductor=chofer, vehiculo=otro)
        assert api.delete(desasociar_url(chofer, otro)).status_code == 200
