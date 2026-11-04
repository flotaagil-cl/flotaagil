"""HU-05 · Cierre o anulación forzada de viaje (RN-10, RN-11)."""

import pytest
from django.urls import reverse

from apps.auditoria.models import Auditoria, Entidad
from apps.flota.models import EstadoConductor
from apps.reservas import ejecucion, tareas
from apps.reservas.models import Canal, EstadoViaje, HistorialEstado, OrigenCancelacion, PagoViaje
from apps.reservas.tests.fabricas import ConvenioFactory, ViajeFactory
from apps.reservas.tests.test_ejecucion import chofer, viaje_de  # noqa: F401

E = EstadoViaje


@pytest.fixture
def api(cliente, despachador):
    cliente.force_authenticate(despachador)
    return cliente


def forzar(api, viaje, **cuerpo):
    return api.post(reverse("viaje-forzar-cierre", args=[viaje.pk]), cuerpo, format="json")


ANULAR = {"accion": "ANULAR", "motivo": "El conductor perdió la conexión"}
CERRAR = {"accion": "CERRAR", "motivo": "Sin señal al terminar", "metodo": "EFECTIVO", "monto": 15000}


@pytest.mark.django_db
class TestAnular:
    def test_cancela_y_libera_al_conductor(self, api, chofer, despachador):  # noqa: F811
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        respuesta = forzar(api, viaje, **ANULAR)
        assert respuesta.status_code == 200, respuesta.data
        viaje.refresh_from_db()
        chofer.refresh_from_db()
        assert viaje.estado == E.CANCELADO
        assert viaje.motivo_cancelacion == ANULAR["motivo"]
        assert viaje.origen_cancelacion == OrigenCancelacion.DESPACHADOR
        assert chofer.estado == EstadoConductor.DISPONIBLE
        cambio = HistorialEstado.objects.filter(viaje=viaje).latest("id")
        assert (cambio.estado_anterior, cambio.estado_nuevo, cambio.usuario) == (
            E.PASAJERO_A_BORDO,
            E.CANCELADO,
            despachador,
        )

    def test_queda_en_auditoria_con_el_responsable(self, api, chofer, despachador):  # noqa: F811
        """RN-11."""
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        forzar(api, viaje, **ANULAR)
        registro = Auditoria.objects.get(accion="ANULACION_FORZADA")
        assert (registro.usuario, registro.entidad, registro.entidad_id) == (
            despachador,
            Entidad.VIAJE,
            viaje.pk,
        )
        assert registro.motivo == ANULAR["motivo"]
        assert registro.datos_previos["estado"] == E.PASAJERO_A_BORDO

    @pytest.mark.parametrize("motivo", [None, "", "   "])
    def test_exige_motivo(self, api, chofer, motivo):  # noqa: F811
        """RN-11."""
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        cuerpo = {"accion": "ANULAR", **({} if motivo is None else {"motivo": motivo})}
        respuesta = forzar(api, viaje, **cuerpo)
        assert respuesta.status_code == 400
        assert "motivo" in respuesta.json()
        viaje.refresh_from_db()
        assert viaje.estado == E.PASAJERO_A_BORDO
        assert not Auditoria.objects.exists()

    def test_el_administrador_tambien(self, cliente, administrador, chofer):  # noqa: F811
        cliente.force_authenticate(administrador)
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        assert forzar(cliente, viaje, **ANULAR).status_code == 200
        viaje.refresh_from_db()
        assert viaje.origen_cancelacion == OrigenCancelacion.ADMINISTRADOR


@pytest.mark.django_db
class TestCerrar:
    def test_finaliza_con_el_pago_y_libera_al_conductor(self, api, chofer):  # noqa: F811
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        assert forzar(api, viaje, **CERRAR).status_code == 200
        viaje.refresh_from_db()
        chofer.refresh_from_db()
        pago = PagoViaje.objects.get(viaje=viaje)
        assert viaje.estado == E.FINALIZADO
        assert (pago.metodo, pago.monto) == ("EFECTIVO", 15000)
        assert chofer.estado == EstadoConductor.DISPONIBLE

    def test_queda_en_auditoria_con_el_responsable_y_el_pago(self, api, chofer, despachador):  # noqa: F811
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        forzar(api, viaje, **CERRAR)
        registro = Auditoria.objects.get(accion="CIERRE_FORZADO")
        assert (registro.usuario, registro.entidad_id, registro.motivo) == (
            despachador,
            viaje.pk,
            CERRAR["motivo"],
        )
        assert registro.datos_previos == {"estado": E.PASAJERO_A_BORDO, "metodo": "EFECTIVO", "monto": 15000}

    @pytest.mark.parametrize(
        ("quitar", "campo"),
        [("motivo", "motivo"), ("metodo", "metodo"), ("monto", "monto")],
    )
    def test_exige_motivo_metodo_y_monto(self, api, chofer, quitar, campo):  # noqa: F811
        """RN-10 y RN-11."""
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        cuerpo = {k: v for k, v in CERRAR.items() if k != quitar}
        respuesta = forzar(api, viaje, **cuerpo)
        assert respuesta.status_code == 400
        assert campo in respuesta.json()
        viaje.refresh_from_db()
        assert viaje.estado == E.PASAJERO_A_BORDO
        assert not PagoViaje.objects.exists()

    @pytest.mark.parametrize("monto", [-1, 500001])
    def test_monto_en_rango(self, api, chofer, monto):  # noqa: F811
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        assert forzar(api, viaje, **{**CERRAR, "monto": monto}).status_code == 400

    def test_convenio_solo_en_viajes_de_convenio(self, api, chofer):  # noqa: F811
        sin_convenio = viaje_de(chofer, E.PASAJERO_A_BORDO)
        cuerpo = {**CERRAR, "metodo": "CONVENIO"}
        respuesta = forzar(api, sin_convenio, **cuerpo)
        assert respuesta.status_code == 400
        assert "metodo" in respuesta.json()
        sin_convenio.refresh_from_db()
        assert sin_convenio.estado == E.PASAJERO_A_BORDO
        convenio = ConvenioFactory(empresa=chofer.usuario.empresa)
        con_convenio = viaje_de(chofer, E.PASAJERO_A_BORDO, canal=Canal.CONVENIO, convenio=convenio)
        assert forzar(api, con_convenio, **cuerpo).status_code == 200

    def test_no_envia_la_encuesta(self, api, chofer, monkeypatch, django_capture_on_commit_callbacks):  # noqa: F811
        """Fue un caso anómalo, y el pasajero no dio por terminado nada."""
        llamadas = []
        monkeypatch.setattr(tareas.enviar_aviso, "delay", lambda *a: llamadas.append(a))
        with django_capture_on_commit_callbacks(execute=True):
            forzar(api, viaje_de(chofer, E.PASAJERO_A_BORDO), **CERRAR)
        assert llamadas == []


@pytest.mark.django_db
class TestCuandoYQuien:
    @pytest.mark.parametrize(
        "estado",
        [E.SOLICITADO, E.ASIGNADO, E.ACEPTADO, E.EN_CAMINO, E.EN_ZONA, E.FINALIZADO],
    )
    @pytest.mark.parametrize("cuerpo", [ANULAR, CERRAR])
    def test_solo_con_el_pasajero_a_bordo(self, api, chofer, estado, cuerpo):  # noqa: F811
        viaje = viaje_de(chofer, estado)
        respuesta = forzar(api, viaje, **cuerpo)
        assert respuesta.status_code == 409
        viaje.refresh_from_db()
        assert viaje.estado == estado
        assert not Auditoria.objects.exists()
        assert not PagoViaje.objects.exists()

    def test_dos_veces_no_repite(self, api, chofer):  # noqa: F811
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        assert forzar(api, viaje, **CERRAR).status_code == 200
        assert forzar(api, viaje, **CERRAR).status_code == 409
        assert PagoViaje.objects.filter(viaje=viaje).count() == 1
        assert Auditoria.objects.filter(accion="CIERRE_FORZADO").count() == 1

    def test_otra_empresa_404(self, api, otra_empresa):
        """RN-13."""
        viaje = ViajeFactory(empresa=otra_empresa, estado=E.SOLICITADO)
        assert forzar(api, viaje, **ANULAR).status_code == 404

    def test_el_conductor_no_puede(self, cliente, conductor, chofer):  # noqa: F811
        cliente.force_authenticate(conductor)
        assert forzar(cliente, viaje_de(chofer, E.PASAJERO_A_BORDO), **ANULAR).status_code == 403

    def test_accion_invalida(self, api, chofer):  # noqa: F811
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        assert forzar(api, viaje, accion="OTRA", motivo="x").status_code == 400

    def test_la_app_del_conductor_se_entera(
        self,
        api,
        chofer,  # noqa: F811
        monkeypatch,
        django_capture_on_commit_callbacks,
    ):
        avisos = []
        monkeypatch.setattr(ejecucion, "avisar_viaje_actualizado", lambda c, v: avisos.append((c, v)))
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        with django_capture_on_commit_callbacks(execute=True):
            forzar(api, viaje, **CERRAR)
        assert avisos == [(chofer.pk, viaje.pk)]


@pytest.mark.django_db
class TestFicha:
    def ficha(self, api, viaje):
        return api.get(reverse("viaje-detail", args=[viaje.pk])).json()

    def test_muestra_el_cierre_forzado_con_el_responsable(self, api, chofer, despachador):  # noqa: F811
        viaje = viaje_de(chofer, E.PASAJERO_A_BORDO)
        assert self.ficha(api, viaje)["cierre_forzado"] is None
        forzar(api, viaje, **CERRAR)
        datos = self.ficha(api, viaje)["cierre_forzado"]
        assert (datos["accion"], datos["motivo"], datos["usuario"]) == (
            "CIERRE_FORZADO",
            CERRAR["motivo"],
            despachador.nombre,
        )

    def test_un_viaje_normal_no_lo_muestra(self, api, chofer):  # noqa: F811
        assert self.ficha(api, viaje_de(chofer, E.FINALIZADO))["cierre_forzado"] is None
