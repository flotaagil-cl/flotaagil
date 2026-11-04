"""HU-18 · Mi turno: viajes completados del turno actual o del último (DC-26)."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.flota import servicios
from apps.flota.models import Conductor, ConductorVehiculo, EstadoConductor
from apps.reservas.models import Actor, Canal, EstadoViaje, HistorialEstado, MetodoPago, PagoViaje, Viaje
from apps.reservas.tests.fabricas import ConductorFactory, ConvenioFactory, VehiculoFactory, ViajeFactory

TURNO = reverse("app-turno")
MI_TURNO = reverse("app-mi-turno")
E = EstadoViaje


@pytest.fixture
def chofer(empresa):
    conductor = ConductorFactory(usuario__empresa=empresa, consentimiento_gps_en=timezone.now())
    ConductorVehiculo.objects.create(conductor=conductor, vehiculo=VehiculoFactory(empresa=empresa))
    return conductor


@pytest.fixture
def app(cliente, chofer):
    cliente.force_authenticate(chofer.usuario)
    return cliente


def finalizado(conductor, hace_min, *, metodo=MetodoPago.EFECTIVO, monto=10000, **cambios):
    viaje = ViajeFactory(
        empresa=conductor.usuario.empresa, conductor=conductor, estado=E.FINALIZADO, **cambios
    )
    PagoViaje.objects.create(viaje=viaje, metodo=metodo, monto=monto)
    cambio = HistorialEstado.objects.create(
        viaje=viaje, estado_anterior=E.PASAJERO_A_BORDO, estado_nuevo=E.FINALIZADO, actor=Actor.CONDUCTOR
    )
    HistorialEstado.objects.filter(pk=cambio.pk).update(
        creado_en=timezone.now() - timedelta(minutes=hace_min)
    )
    return viaje


def en_turno_desde(conductor, hace_min):
    conductor.estado = EstadoConductor.DISPONIBLE
    conductor.vehiculo_activo = conductor.asociaciones.first().vehiculo
    conductor.turno_inicio = timezone.now() - timedelta(minutes=hace_min)
    conductor.turno_fin = None
    conductor.save()


@pytest.mark.django_db
class TestRegistroDelTurno:
    def test_empezar_guarda_el_inicio_y_limpia_el_fin(self, app, chofer):
        chofer.turno_fin = timezone.now() - timedelta(days=1)
        chofer.save()
        app.post(TURNO, {"estado": "DISPONIBLE"}, format="json")
        chofer.refresh_from_db()
        assert chofer.turno_inicio is not None
        assert chofer.turno_fin is None

    def test_terminar_guarda_el_fin_y_conserva_el_inicio(self, app, chofer):
        app.post(TURNO, {"estado": "DISPONIBLE"}, format="json")
        chofer.refresh_from_db()
        inicio = chofer.turno_inicio
        app.post(TURNO, {"estado": "NO_DISPONIBLE"}, format="json")
        chofer.refresh_from_db()
        assert (chofer.turno_inicio, chofer.turno_fin is not None) == (inicio, True)

    def test_repetir_disponible_no_reinicia_el_turno(self, app, chofer):
        app.post(TURNO, {"estado": "DISPONIBLE"}, format="json")
        chofer.refresh_from_db()
        inicio = chofer.turno_inicio
        app.post(TURNO, {"estado": "DISPONIBLE"}, format="json")
        chofer.refresh_from_db()
        assert chofer.turno_inicio == inicio

    def test_repetir_no_disponible_no_mueve_el_fin(self, app, chofer):
        app.post(TURNO, {"estado": "DISPONIBLE"}, format="json")
        app.post(TURNO, {"estado": "NO_DISPONIBLE"}, format="json")
        chofer.refresh_from_db()
        fin = chofer.turno_fin
        app.post(TURNO, {"estado": "NO_DISPONIBLE"}, format="json")
        chofer.refresh_from_db()
        assert chofer.turno_fin == fin

    def test_un_rechazo_no_empieza_el_turno(self, app, chofer):
        chofer.consentimiento_gps_en = None
        chofer.save()
        assert app.post(TURNO, {"estado": "DISPONIBLE"}, format="json").status_code == 409
        chofer.refresh_from_db()
        assert chofer.turno_inicio is None

    def test_deshabilitar_la_cuenta_cierra_el_turno(self, chofer, administrador):
        en_turno_desde(chofer, 30)
        servicios.cambiar_habilitacion(chofer, habilitar=False, usuario=administrador)
        chofer.refresh_from_db()
        assert chofer.estado == EstadoConductor.NO_DISPONIBLE
        assert chofer.turno_fin is not None


@pytest.mark.django_db
class TestMiTurno:
    def test_sin_turnos(self, app):
        datos = app.get(MI_TURNO).json()
        assert datos == {
            "en_turno": False,
            "inicio": None,
            "fin": None,
            "viajes": [],
            "totales": [],
            "total": 0,
        }

    def test_turno_actual_solo_sus_viajes_en_orden(self, app, chofer, empresa):
        en_turno_desde(chofer, 60)
        finalizado(chofer, 120)  # turno anterior
        segundo = finalizado(chofer, 10, origen_dir="Plaza de Armas", destino_dir="Providencia")
        primero = finalizado(chofer, 50)
        otro = ConductorFactory(usuario__empresa=empresa)
        finalizado(otro, 5)
        datos = app.get(MI_TURNO).json()
        assert datos["en_turno"] is True
        assert [v["id"] for v in datos["viajes"]] == [primero.pk, segundo.pk]
        fila = datos["viajes"][1]
        assert (fila["origen"], fila["destino"], fila["monto"], fila["metodo"]) == (
            "Plaza de Armas",
            "Providencia",
            10000,
            "EFECTIVO",
        )
        assert fila["finalizado_en"]
        assert fila["cerrado_por_central"] is False

    @pytest.mark.parametrize(
        "estado", [E.SOLICITADO, E.ASIGNADO, E.ACEPTADO, E.EN_CAMINO, E.PASAJERO_A_BORDO, E.CANCELADO]
    )
    def test_solo_finalizados(self, app, chofer, estado):
        en_turno_desde(chofer, 60)
        viaje = finalizado(chofer, 5)
        extra = {"motivo_cancelacion": "Sintético"} if estado == E.CANCELADO else {}
        Viaje.objects.filter(pk=viaje.pk).update(estado=estado, **extra)
        assert app.get(MI_TURNO).json()["viajes"] == []

    def test_fuera_de_turno_muestra_el_ultimo(self, app, chofer):
        ahora = timezone.now()
        chofer.turno_inicio, chofer.turno_fin = ahora - timedelta(minutes=100), ahora - timedelta(minutes=40)
        chofer.save()
        finalizado(chofer, 200)  # antes
        dentro = finalizado(chofer, 70)
        finalizado(chofer, 10)  # después: no debería ocurrir, pero no es de este turno
        datos = app.get(MI_TURNO).json()
        assert datos["en_turno"] is False
        assert datos["fin"] is not None
        assert [v["id"] for v in datos["viajes"]] == [dentro.pk]

    def test_totales_por_metodo(self, app, chofer, empresa):
        en_turno_desde(chofer, 60)
        finalizado(chofer, 30, monto=10000)
        finalizado(chofer, 20, monto=5000)
        finalizado(chofer, 15, metodo=MetodoPago.TARJETA, monto=7000)
        finalizado(
            chofer,
            10,
            metodo=MetodoPago.CONVENIO,
            monto=9000,
            canal=Canal.CONVENIO,
            convenio=ConvenioFactory(empresa=empresa),
        )
        datos = app.get(MI_TURNO).json()
        assert datos["totales"] == [
            {"metodo": "EFECTIVO", "viajes": 2, "monto": 15000},
            {"metodo": "TARJETA", "viajes": 1, "monto": 7000},
            {"metodo": "CONVENIO", "viajes": 1, "monto": 9000},
        ]
        assert datos["total"] == 31000

    def test_rol_panel_no_entra(self, cliente, despachador):
        cliente.force_authenticate(despachador)
        assert cliente.get(MI_TURNO).status_code == 403

    def test_sin_sesion(self, cliente):
        assert cliente.get(MI_TURNO).status_code == 401


@pytest.mark.django_db
class TestCierreDeLaCentral:
    def test_aparece_marcado_y_suma_en_los_totales(self, app, chofer, cliente, despachador, empresa):
        """HU-05 de punta a punta: el cierre real del panel aparece en Mi turno."""
        en_turno_desde(chofer, 60)
        normal = finalizado(chofer, 30, monto=1000)
        Conductor.objects.filter(pk=chofer.pk).update(estado=EstadoConductor.EN_VIAJE)
        a_bordo = ViajeFactory(empresa=empresa, conductor=chofer, estado=E.PASAJERO_A_BORDO)
        cliente.force_authenticate(despachador)
        respuesta = cliente.post(
            reverse("viaje-forzar-cierre", args=[a_bordo.pk]),
            {"accion": "CERRAR", "motivo": "Sin señal", "metodo": "EFECTIVO", "monto": 2000},
            format="json",
        )
        assert respuesta.status_code == 200
        cliente.force_authenticate(chofer.usuario)
        datos = cliente.get(MI_TURNO).json()
        marcas = {v["id"]: v["cerrado_por_central"] for v in datos["viajes"]}
        assert marcas == {normal.pk: False, a_bordo.pk: True}
        assert datos["totales"] == [{"metodo": "EFECTIVO", "viajes": 2, "monto": 3000}]
