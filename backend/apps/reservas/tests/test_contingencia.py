"""HU-32 (CC-15, DC-33): reservas de contingencia (CP-37)."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import Auditoria, Entidad
from apps.flota.models import MotivoTerminoTurno, Turno
from apps.reservas import tareas
from apps.reservas.models import (
    Canal,
    EstadoViaje,
    HistorialEstado,
    MensajeWhatsapp,
    OrigenCancelacion,
    Viaje,
)
from apps.reservas.tests.fabricas import ConductorFactory, VehiculoFactory
from apps.reservas.tests.test_whatsapp import TwilioFalso

URL = reverse("viaje-contingencia")
E = EstadoViaje


def hace(horas: float):
    return timezone.now() - timedelta(hours=horas)


def finalizado(quien, **cambios):
    datos = {
        "folio": "c-0001",
        "pasajero": {"nombre": "Pasajera Sintética", "telefono": "+56900007001"},
        "origen_dir": "Av. Providencia 1234, Providencia",
        "destino_dir": "Plaza de Armas, Santiago",
        "resultado": "FINALIZADO",
        "recogida_en": hace(5).isoformat(),
        "termino_en": hace(4.5).isoformat(),
        "conductor": quien.pk,
        "metodo": "EFECTIVO",
        "monto": 15000,
    }
    datos.update(cambios)
    return datos


def cancelado(**cambios):
    datos = {
        "folio": "C-0002",
        "pasajero": {"nombre": "Pasajero Sintético", "telefono": "+56900007002"},
        "origen_dir": "Av. Providencia 1234, Providencia",
        "destino_dir": "Plaza de Armas, Santiago",
        "resultado": "CANCELADO",
        "recogida_en": hace(3).isoformat(),
        "termino_en": hace(3.2).isoformat(),
        "motivo": "El pasajero no llegó al punto (anotado en papel)",
    }
    datos.update(cambios)
    return datos


@pytest.fixture
def chofer(empresa):
    return ConductorFactory(usuario__empresa=empresa)


@pytest.fixture
def api(cliente, despachador):
    cliente.force_authenticate(despachador)
    return cliente


@pytest.fixture
def twilio(monkeypatch):
    falso = TwilioFalso()
    monkeypatch.setattr(tareas, "obtener_notificador", lambda: falso)
    return falso


@pytest.mark.django_db
class TestCP37:
    def test_finalizado_con_horas_reales_y_pago(self, api, chofer, despachador, twilio):
        respuesta = api.post(URL, finalizado(chofer), format="json")
        assert respuesta.status_code == 201, respuesta.data
        viaje = Viaje.objects.get()
        assert (viaje.canal, viaje.folio_contingencia, viaje.estado) == (
            Canal.CONTINGENCIA,
            "C-0001",
            E.FINALIZADO,
        )
        assert viaje.conductor == chofer
        assert abs(viaje.pago.registrado_en - hace(4.5)) < timedelta(seconds=5)
        assert (viaje.pago.metodo, viaje.pago.monto) == ("EFECTIVO", 15000)
        historial = list(HistorialEstado.objects.filter(viaje=viaje).order_by("creado_en"))
        assert [(h.estado_anterior, h.estado_nuevo) for h in historial] == [
            (None, E.PASAJERO_A_BORDO),
            (E.PASAJERO_A_BORDO, E.FINALIZADO),
        ]
        assert all(h.contingencia and h.usuario == despachador for h in historial)
        assert abs(historial[0].creado_en - hace(5)) < timedelta(seconds=5)
        assert respuesta.data["folio_contingencia"] == "C-0001"
        assert [h["contingencia"] for h in respuesta.data["historial"]] == [True, True]

    def test_cancelado_puede_cancelarse_antes_de_la_hora_pedida(self, api):
        assert api.post(URL, cancelado(termino_en=hace(5).isoformat()), format="json").status_code == 201

    def test_cancelado_con_motivo(self, api, despachador, twilio):
        assert api.post(URL, cancelado(), format="json").status_code == 201
        viaje = Viaje.objects.get()
        assert (viaje.estado, viaje.origen_cancelacion) == (E.CANCELADO, OrigenCancelacion.DESPACHADOR)
        assert not hasattr(viaje, "pago") or viaje.pago is None
        assert HistorialEstado.objects.get(viaje=viaje).estado_nuevo == E.CANCELADO

    def test_sin_avisos_ni_encuesta(self, api, chofer, twilio, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            api.post(URL, finalizado(chofer), format="json")
            api.post(URL, cancelado(), format="json")
        assert twilio.enviados == []
        assert not MensajeWhatsapp.objects.exists()

    def test_queda_en_auditoria(self, api, chofer, despachador):
        api.post(URL, finalizado(chofer), format="json")
        registro = Auditoria.objects.get(entidad=Entidad.VIAJE, accion="RESERVA_CONTINGENCIA")
        assert registro.usuario == despachador
        assert registro.datos_previos["folio"] == "C-0001"

    def test_folio_repetido_en_la_empresa(self, api, chofer):
        assert api.post(URL, finalizado(chofer), format="json").status_code == 201
        repetido = api.post(URL, finalizado(chofer, folio="C-0001"), format="json")
        assert repetido.status_code == 400
        assert "folio" in repetido.data
        assert Viaje.objects.count() == 1

    def test_mismo_folio_en_otra_empresa(self, cliente, api, chofer, otra_empresa):
        from apps.cuentas.tests.fabricas import UsuarioFactory

        api.post(URL, finalizado(chofer), format="json")
        otro = UsuarioFactory(empresa=otra_empresa)
        cliente.force_authenticate(otro)
        assert cliente.post(URL, cancelado(folio="C-0001"), format="json").status_code == 201

    @pytest.mark.parametrize("folio", ["", "con espacio", "x" * 21, None])
    def test_folio_obligatorio_y_con_formato(self, api, folio):
        assert api.post(URL, cancelado(folio=folio), format="json").status_code == 400


@pytest.mark.django_db
class TestHoras:
    def test_hora_futura(self, api, chofer):
        respuesta = api.post(
            URL,
            finalizado(chofer, termino_en=(timezone.now() + timedelta(minutes=5)).isoformat()),
            format="json",
        )
        assert respuesta.status_code == 400
        assert "termino_en" in respuesta.data

    def test_mas_de_7_dias(self, api, chofer):
        respuesta = api.post(
            URL,
            finalizado(chofer, recogida_en=hace(24 * 8).isoformat(), termino_en=hace(24 * 8 - 1).isoformat()),
            format="json",
        )
        assert respuesta.status_code == 400
        assert "recogida_en" in respuesta.data

    def test_el_limite_es_configurable(self, api, chofer, empresa):
        empresa.configuracion.contingencia_max_dias = 10
        empresa.configuracion.save()
        datos = finalizado(
            chofer, recogida_en=hace(24 * 8).isoformat(), termino_en=hace(24 * 8 - 1).isoformat()
        )
        assert api.post(URL, datos, format="json").status_code == 201

    def test_termino_antes_de_la_recogida(self, api, chofer):
        respuesta = api.post(URL, finalizado(chofer, termino_en=hace(6).isoformat()), format="json")
        assert respuesta.status_code == 400
        assert "termino_en" in respuesta.data


@pytest.mark.django_db
class TestDatosObligatorios:
    @pytest.mark.parametrize("campo", ["conductor", "metodo", "monto"])
    def test_finalizado_exige(self, api, chofer, campo):
        respuesta = api.post(URL, finalizado(chofer, **{campo: None}), format="json")
        assert respuesta.status_code == 400
        assert campo in respuesta.data

    def test_cancelado_exige_motivo(self, api):
        assert api.post(URL, cancelado(motivo="  "), format="json").status_code == 400

    def test_conductor_de_otra_empresa(self, api, otra_empresa):
        ajeno = ConductorFactory(usuario__empresa=otra_empresa)
        respuesta = api.post(URL, finalizado(ajeno), format="json")
        assert respuesta.status_code == 400
        assert "conductor" in respuesta.data

    def test_no_se_cobra_al_convenio(self, api, chofer):
        assert api.post(URL, finalizado(chofer, metodo="CONVENIO"), format="json").status_code == 400


@pytest.mark.django_db
class TestTurno:
    def test_toma_el_turno_que_contiene_la_hora_real(self, api, chofer, empresa):
        vehiculo = VehiculoFactory(empresa=empresa)
        turno = Turno.objects.create(
            conductor=chofer,
            vehiculo=vehiculo,
            hora_inicio=hace(8),
            hora_termino=hace(2),
            motivo_termino=MotivoTerminoTurno.CONDUCTOR,
        )
        api.post(URL, finalizado(chofer), format="json")
        viaje = Viaje.objects.get()
        assert (viaje.turno, viaje.vehiculo) == (turno, vehiculo)

    def test_turno_abierto_tambien_cuenta(self, api, chofer):
        turno = Turno.objects.create(conductor=chofer, hora_inicio=hace(6))
        api.post(URL, finalizado(chofer), format="json")
        assert Viaje.objects.get().turno == turno

    def test_sin_turno_queda_sin_turno(self, api, chofer):
        Turno.objects.create(
            conductor=chofer,
            hora_inicio=hace(3),
            hora_termino=hace(1),
            motivo_termino=MotivoTerminoTurno.CONDUCTOR,
        )
        api.post(URL, finalizado(chofer), format="json")
        assert Viaje.objects.get().turno is None


@pytest.mark.django_db
class TestPermisos:
    def test_administrador_tambien(self, cliente, administrador, chofer):
        cliente.force_authenticate(administrador)
        assert cliente.post(URL, finalizado(chofer), format="json").status_code == 201
        assert Viaje.objects.get().historial.first().actor == "ADMINISTRADOR"

    def test_el_conductor_no(self, cliente, conductor):
        cliente.force_authenticate(conductor.usuario if hasattr(conductor, "usuario") else conductor)
        assert cliente.post(URL, cancelado(), format="json").status_code == 403

    def test_el_alta_normal_no_acepta_el_canal(self, api):
        respuesta = api.post(
            reverse("viaje-list"),
            {
                "pasajero": {"nombre": "X", "telefono": "+56900007003"},
                "canal": "CONTINGENCIA",
                "origen_dir": "A",
                "destino_dir": "B",
                "recogida_en": (timezone.now() + timedelta(hours=3)).isoformat(),
            },
            format="json",
        )
        assert respuesta.status_code == 400
        assert "canal" in respuesta.data


@pytest.mark.django_db
class TestReporte:
    def test_conciliacion_por_folio(self, cliente, api, administrador, chofer):
        Turno.objects.create(conductor=chofer, hora_inicio=hace(8))
        api.post(URL, finalizado(chofer, folio="C-0009"), format="json")
        api.post(URL, cancelado(folio="C-0003"), format="json")
        cliente.force_authenticate(administrador)
        datos = cliente.get(
            reverse("reporte", args=["contingencia"]), {"desde": hace(30).date().isoformat()}
        ).json()
        assert [f["folio"] for f in datos["filas"]] == ["C-0003", "C-0009"]
        cancelada, finalizada = datos["filas"]
        assert (cancelada["turno"], cancelada["monto"]) == ("Sin turno", None)
        assert finalizada["turno"].startswith("Turno ")
        assert finalizada["monto"] == 15000
        assert finalizada["ingresado_por"]
        assert datos["totales"]["monto"] == 15000
        assert datos["totales"]["turno"] == "0 sin turno"  # el cancelado no tiene conductor

    def test_cuenta_los_viajes_sin_turno(self, cliente, api, administrador, chofer):
        api.post(URL, finalizado(chofer, folio="C-0010"), format="json")
        cliente.force_authenticate(administrador)
        datos = cliente.get(
            reverse("reporte", args=["contingencia"]), {"desde": hace(30).date().isoformat()}
        ).json()
        assert datos["totales"]["turno"] == "1 sin turno"


@pytest.mark.django_db
class TestConductoresParaElFormulario:
    def test_todos_los_de_la_empresa_para_el_despachador(self, api, chofer, otra_empresa):
        ConductorFactory(usuario__empresa=otra_empresa)
        filas = api.get(reverse("viaje-conductores-contingencia")).json()
        assert filas == [{"id": chofer.pk, "nombre": chofer.usuario.nombre}]

    def test_el_conductor_no(self, cliente, conductor):
        cliente.force_authenticate(conductor.usuario if hasattr(conductor, "usuario") else conductor)
        assert cliente.get(reverse("viaje-conductores-contingencia")).status_code == 403

    def test_la_liquidacion_usa_la_hora_real_de_pago(self, cliente, api, administrador, chofer):
        api.post(
            URL,
            finalizado(chofer, recogida_en=hace(50).isoformat(), termino_en=hace(49).isoformat()),
            format="json",
        )
        cliente.force_authenticate(administrador)
        dia = timezone.localtime(hace(49)).date().isoformat()
        datos = cliente.get(reverse("reporte", args=["liquidacion"]), {"desde": dia, "hasta": dia}).json()
        assert datos["totales"]["total"] == 15000
