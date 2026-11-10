"""HU-31 (CC-12): TURNO, cierre administrativo y CIERRE_CAJA (CP-36)."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import Auditoria, Entidad
from apps.flota.models import CierreCaja, ConductorVehiculo, EstadoConductor, MotivoTerminoTurno, Turno
from apps.reservas.models import Actor, Asignacion, EstadoViaje, HistorialEstado, MetodoPago, PagoViaje
from apps.reservas.tests.fabricas import ConductorFactory, VehiculoFactory, ViajeFactory

E = EstadoViaje
POR_CERRAR = reverse("turnos-por-cerrar")


def cierre_url(turno):
    return reverse("turno-cierre-caja", args=[turno.pk])


@pytest.fixture
def chofer(empresa):
    vehiculo = VehiculoFactory(empresa=empresa)
    conductor = ConductorFactory(
        usuario__empresa=empresa,
        consentimiento_gps_en=timezone.now(),
        estado=EstadoConductor.DISPONIBLE,
        vehiculo_activo=vehiculo,
    )
    ConductorVehiculo.objects.create(conductor=conductor, vehiculo=vehiculo)
    return conductor


def turno_terminado(conductor, *, hace_h=2):
    ahora = timezone.now()
    return Turno.objects.create(
        conductor=conductor,
        vehiculo=conductor.vehiculo_activo,
        hora_inicio=ahora - timedelta(hours=hace_h + 4),
        hora_termino=ahora - timedelta(hours=hace_h),
        motivo_termino=MotivoTerminoTurno.CONDUCTOR,
    )


def pagado(turno, metodo, monto, estado=E.FINALIZADO, **cambios):
    viaje = ViajeFactory(
        empresa=turno.conductor.usuario.empresa,
        conductor=turno.conductor,
        estado=estado,
        turno=turno,
        **cambios,
    )
    if estado == E.FINALIZADO:
        PagoViaje.objects.create(viaje=viaje, metodo=metodo, monto=monto)
    return viaje


@pytest.fixture
def admin_api(cliente, administrador):
    cliente.force_authenticate(administrador)
    return cliente


@pytest.fixture
def turno_48(chofer):
    """48.000 en efectivo registrados (30.000 + 18.000), más tarjeta y convenio que no cuentan."""
    turno = turno_terminado(chofer)
    pagado(turno, MetodoPago.EFECTIVO, 30000)
    pagado(turno, MetodoPago.EFECTIVO, 18000)
    pagado(turno, MetodoPago.TARJETA, 12000)
    pagado(turno, MetodoPago.TRANSFERENCIA, 5000)
    return turno


@pytest.mark.django_db
class TestCP36:
    def test_rinde_lo_registrado(self, admin_api, turno_48, administrador):
        respuesta = admin_api.post(cierre_url(turno_48), {"monto_rendido": 48000}, format="json")
        assert respuesta.status_code == 201, respuesta.data
        assert (respuesta.data["monto_registrado"], respuesta.data["diferencia"]) == (48000, 0)
        assert respuesta.data["observacion"] is None
        assert respuesta.data["responsable"] == administrador.nombre
        auditoria = Auditoria.objects.get(entidad=Entidad.TURNO, entidad_id=turno_48.pk)
        assert auditoria.accion == "CIERRE_CAJA"
        assert auditoria.usuario == administrador
        assert auditoria.datos_previos["diferencia"] == 0

    def test_falta_efectivo_exige_observacion(self, admin_api, turno_48):
        sin = admin_api.post(cierre_url(turno_48), {"monto_rendido": 45000}, format="json")
        assert sin.status_code == 400
        assert "observacion" in sin.data
        assert not CierreCaja.objects.exists()
        con = admin_api.post(
            cierre_url(turno_48),
            {"monto_rendido": 45000, "observacion": "Faltan 3.000: vuelto mal dado (sintético)"},
            format="json",
        )
        assert con.status_code == 201
        assert con.data["diferencia"] == -3000

    def test_no_rinde_nada(self, admin_api, turno_48):
        respuesta = admin_api.post(
            cierre_url(turno_48),
            {"monto_rendido": 0, "observacion": "No se presentó a rendir"},
            format="json",
        )
        assert respuesta.status_code == 201
        assert respuesta.data["diferencia"] == -48000

    def test_sobra_efectivo(self, admin_api, turno_48):
        respuesta = admin_api.post(
            cierre_url(turno_48), {"monto_rendido": 50000, "observacion": "Propina declarada"}, format="json"
        )
        assert respuesta.data["diferencia"] == 2000

    def test_turno_sin_efectivo(self, admin_api, chofer):
        turno = turno_terminado(chofer)
        pagado(turno, MetodoPago.TARJETA, 9000)
        respuesta = admin_api.post(cierre_url(turno), {"monto_rendido": 0}, format="json")
        assert respuesta.status_code == 201
        assert (respuesta.data["monto_registrado"], respuesta.data["diferencia"]) == (0, 0)

    def test_segundo_cierre_409(self, admin_api, turno_48):
        assert (
            admin_api.post(cierre_url(turno_48), {"monto_rendido": 48000}, format="json").status_code == 201
        )
        segundo = admin_api.post(cierre_url(turno_48), {"monto_rendido": 48000}, format="json")
        assert segundo.status_code == 409
        assert segundo.data["code"] == "cierre_repetido"
        assert CierreCaja.objects.count() == 1

    def test_el_registrado_queda_fijo(self, admin_api, turno_48):
        admin_api.post(cierre_url(turno_48), {"monto_rendido": 48000}, format="json")
        pagado(turno_48, MetodoPago.EFECTIVO, 1000)  # un pago posterior no cambia el cierre
        assert CierreCaja.objects.get().monto_registrado == 48000


@pytest.mark.django_db
class TestReglasDelCierre:
    def test_turno_abierto_409(self, admin_api, chofer):
        turno = Turno.objects.create(
            conductor=chofer, vehiculo=chofer.vehiculo_activo, hora_inicio=timezone.now()
        )
        respuesta = admin_api.post(cierre_url(turno), {"monto_rendido": 0}, format="json")
        assert (respuesta.status_code, respuesta.data["code"]) == (409, "turno_abierto")

    def test_con_viaje_en_ejecucion_409(self, admin_api, chofer):
        turno = turno_terminado(chofer)
        pagado(turno, MetodoPago.EFECTIVO, 1000, estado=E.PASAJERO_A_BORDO)
        respuesta = admin_api.post(cierre_url(turno), {"monto_rendido": 0}, format="json")
        assert (respuesta.status_code, respuesta.data["code"]) == (409, "viaje_en_ejecucion")

    def test_viajes_no_finalizados_no_suman(self, admin_api, chofer):
        turno = turno_terminado(chofer)
        pagado(turno, MetodoPago.EFECTIVO, 10000)
        cancelado = pagado(turno, MetodoPago.EFECTIVO, 0, estado=E.CANCELADO, motivo_cancelacion="Sintético")
        assert cancelado.estado == E.CANCELADO
        respuesta = admin_api.post(cierre_url(turno), {"monto_rendido": 10000}, format="json")
        assert respuesta.data["monto_registrado"] == 10000

    @pytest.mark.parametrize("monto", [-1, "abc", None])
    def test_monto_invalido(self, admin_api, turno_48, monto):
        assert (
            admin_api.post(cierre_url(turno_48), {"monto_rendido": monto}, format="json").status_code == 400
        )

    def test_solo_administrador(self, cliente, despachador, turno_48):
        cliente.force_authenticate(despachador)
        assert cliente.post(cierre_url(turno_48), {"monto_rendido": 48000}, format="json").status_code == 403
        assert cliente.get(POR_CERRAR).status_code == 403

    def test_turno_de_otra_empresa_404(self, admin_api, otra_empresa):
        ajeno = ConductorFactory(usuario__empresa=otra_empresa)
        turno = Turno.objects.create(
            conductor=ajeno,
            hora_inicio=timezone.now() - timedelta(hours=3),
            hora_termino=timezone.now(),
            motivo_termino=MotivoTerminoTurno.CONDUCTOR,
        )
        assert admin_api.post(cierre_url(turno), {"monto_rendido": 0}, format="json").status_code == 404


@pytest.mark.django_db
class TestListados:
    def test_por_cerrar(self, admin_api, chofer, turno_48, otra_empresa):
        cerrado = turno_terminado(chofer, hace_h=30)
        CierreCaja.objects.create(
            turno=cerrado, monto_registrado=0, monto_rendido=0, diferencia=0, responsable=chofer.usuario
        )
        Turno.objects.create(conductor=chofer, vehiculo=chofer.vehiculo_activo, hora_inicio=timezone.now())
        ajeno = ConductorFactory(usuario__empresa=otra_empresa)
        Turno.objects.create(
            conductor=ajeno,
            hora_inicio=timezone.now() - timedelta(hours=3),
            hora_termino=timezone.now(),
            motivo_termino=MotivoTerminoTurno.CONDUCTOR,
        )
        datos = admin_api.get(POR_CERRAR).json()
        assert [t["id"] for t in datos] == [turno_48.pk]
        fila = datos[0]
        assert fila["efectivo_registrado"] == 48000
        assert fila["viajes_finalizados"] == 4
        assert fila["con_viaje_en_ejecucion"] is False
        assert fila["patente"] == chofer.vehiculo_activo.patente
        assert fila["conductor"] == chofer.usuario.nombre

    def test_historial_del_conductor(self, admin_api, chofer, turno_48):
        admin_api.post(cierre_url(turno_48), {"monto_rendido": 48000}, format="json")
        abierto = Turno.objects.create(
            conductor=chofer, vehiculo=chofer.vehiculo_activo, hora_inicio=timezone.now()
        )
        datos = admin_api.get(reverse("turnos"), {"conductor": chofer.pk}).json()
        assert [t["id"] for t in datos] == [abierto.pk, turno_48.pk]
        assert datos[0]["cierre_caja"] is None
        assert datos[1]["cierre_caja"]["diferencia"] == 0

    def test_historial_exige_conductor(self, admin_api):
        assert admin_api.get(reverse("turnos")).status_code == 400


@pytest.mark.django_db
class TestCierreAdministrativo:
    def url(self, conductor):
        return reverse("conductor-terminar-turno", args=[conductor.pk])

    def test_termina_el_turno_y_queda_en_auditoria(self, admin_api, chofer, administrador):
        turno = Turno.objects.create(
            conductor=chofer, vehiculo=chofer.vehiculo_activo, hora_inicio=timezone.now()
        )
        respuesta = admin_api.post(self.url(chofer), {"motivo": "Olvidó terminar el turno"}, format="json")
        assert respuesta.status_code == 200, respuesta.data
        chofer.refresh_from_db()
        turno.refresh_from_db()
        assert (chofer.estado, chofer.vehiculo_activo) == (EstadoConductor.NO_DISPONIBLE, None)
        assert turno.motivo_termino == MotivoTerminoTurno.CIERRE_ADMINISTRATIVO
        auditoria = Auditoria.objects.get(entidad=Entidad.TURNO, entidad_id=turno.pk)
        assert (auditoria.accion, auditoria.motivo, auditoria.usuario) == (
            "CIERRE_ADMINISTRATIVO",
            "Olvidó terminar el turno",
            administrador,
        )

    def test_exige_motivo(self, admin_api, chofer):
        Turno.objects.create(conductor=chofer, vehiculo=chofer.vehiculo_activo, hora_inicio=timezone.now())
        assert admin_api.post(self.url(chofer), {"motivo": "  "}, format="json").status_code == 400

    def test_en_viaje_409(self, admin_api, chofer):
        Turno.objects.create(conductor=chofer, vehiculo=chofer.vehiculo_activo, hora_inicio=timezone.now())
        chofer.estado = EstadoConductor.EN_VIAJE
        chofer.save()
        respuesta = admin_api.post(self.url(chofer), {"motivo": "x"}, format="json")
        assert (respuesta.status_code, respuesta.data["code"]) == (409, "en_viaje")

    def test_sin_turno_409(self, admin_api, chofer):
        respuesta = admin_api.post(self.url(chofer), {"motivo": "x"}, format="json")
        assert (respuesta.status_code, respuesta.data["code"]) == (409, "sin_turno")


@pytest.mark.django_db
class TestTurnoDelViaje:
    def test_al_aceptar_el_viaje_guarda_el_turno(self, cliente, chofer, despachador, empresa):
        turno = Turno.objects.create(
            conductor=chofer, vehiculo=chofer.vehiculo_activo, hora_inicio=timezone.now()
        )
        viaje = ViajeFactory(empresa=empresa, estado=E.SOLICITADO)
        HistorialEstado.objects.create(viaje=viaje, estado_nuevo=E.SOLICITADO, actor=Actor.DESPACHADOR)
        cliente.force_authenticate(despachador)
        assert cliente.post(
            reverse("viaje-asignar", args=[viaje.pk]), {"conductor": chofer.pk}, format="json"
        ).status_code in (200, 201)
        viaje.refresh_from_db()
        assert viaje.turno is None  # asignar no basta: puede rechazar
        asignacion = Asignacion.objects.get(viaje=viaje)
        cliente.force_authenticate(chofer.usuario)
        respuesta = cliente.post(reverse("app-aceptar", args=[asignacion.pk]))
        assert respuesta.status_code == 200, respuesta.data
        viaje.refresh_from_db()
        assert viaje.turno == turno

    def test_cierre_forzado_despues_del_turno_queda_en_el_turno(self, cliente, chofer, despachador, empresa):
        """El turno se fija al aceptar: aunque la central cierre el viaje después, suma en ese turno."""
        turno = turno_terminado(chofer)
        chofer.estado = EstadoConductor.EN_VIAJE
        chofer.save()
        a_bordo = ViajeFactory(empresa=empresa, conductor=chofer, estado=E.PASAJERO_A_BORDO, turno=turno)
        nuevo = Turno.objects.create(
            conductor=chofer, vehiculo=chofer.vehiculo_activo, hora_inicio=timezone.now()
        )
        cliente.force_authenticate(despachador)
        respuesta = cliente.post(
            reverse("viaje-forzar-cierre", args=[a_bordo.pk]),
            {"accion": "CERRAR", "motivo": "Sin señal", "metodo": "EFECTIVO", "monto": 7000},
            format="json",
        )
        assert respuesta.status_code == 200
        a_bordo.refresh_from_db()
        assert a_bordo.turno == turno != nuevo
