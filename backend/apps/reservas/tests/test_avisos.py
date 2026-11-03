"""HU-21 · Avisos por WhatsApp. CP-16 y CP-17: avisos en cada etapa; cancelación solo sin conductor."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.flota.models import ConductorVehiculo, EstadoConductor
from apps.integraciones import notificaciones
from apps.integraciones.notificaciones import (
    AVISO_CONDUCTOR,
    AVISO_CONFIRMACION,
    AVISO_EN_CAMINO,
    AVISO_EN_ZONA,
    NotificadorDesarrollo,
    NotificadorTwilio,
    obtener_notificador,
    texto_aviso,
)
from apps.reservas import avisos, servicios, verificacion
from apps.reservas.models import (
    Actor,
    DireccionMensaje,
    EstadoEntrega,
    EstadoViaje,
    HistorialEstado,
    MensajeWhatsapp,
    OrigenCancelacion,
    TipoMensaje,
)
from apps.reservas.tests.fabricas import ConductorFactory, PasajeroFactory, VehiculoFactory, ViajeFactory
from apps.reservas.tests.test_api import reserva
from apps.reservas.tests.test_ejecucion import CERCA, ORIGEN, posicion
from apps.reservas.tests.test_whatsapp import TwilioFalso, entrante, http_error

E = EstadoViaje


@pytest.fixture
def twilio(monkeypatch):
    falso = TwilioFalso()
    monkeypatch.setattr(avisos, "obtener_notificador", lambda: falso)
    monkeypatch.setattr(verificacion, "obtener_notificador", lambda: falso)
    return falso


@pytest.fixture
def chofer(empresa):
    vehiculo = VehiculoFactory(empresa=empresa, patente="ABCD12", marca_modelo="Toyota Corolla")
    conductor = ConductorFactory(
        usuario__empresa=empresa,
        usuario__nombre="Muriel Moreno",
        estado=EstadoConductor.DISPONIBLE,
        vehiculo_activo=vehiculo,
        consentimiento_gps_en=timezone.now(),
    )
    ConductorVehiculo.objects.create(conductor=conductor, vehiculo=vehiculo)
    return conductor


@pytest.fixture
def pasajero(empresa):
    return PasajeroFactory(empresa=empresa, nombre="Ana Pérez", telefono="+56900009001")


def viaje_con(chofer, pasajero, estado, **cambios):
    viaje = ViajeFactory(
        empresa=pasajero.empresa,
        pasajero=pasajero,
        conductor=chofer,
        vehiculo=chofer.vehiculo_activo,
        estado=estado,
        origen_geo=ORIGEN,
        origen_dir="Plaza de Armas, Santiago",
        **cambios,
    )
    HistorialEstado.objects.create(viaje=viaje, estado_nuevo=estado, actor=Actor.DESPACHADOR)
    return viaje


def como(usuario):
    cliente = APIClient()
    cliente.force_authenticate(usuario)
    return cliente


@pytest.mark.django_db
class TestEtapas:
    def test_confirmacion_al_crear_en_el_panel(self, twilio, despachador, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = como(despachador).post(reverse("viaje-list"), reserva(), format="json")
        assert respuesta.status_code == 201, respuesta.data
        assert len(twilio.enviados) == 1
        assert "confirmó tu viaje" in twilio.enviados[0]["Body"]
        assert "responde Cancelar" in twilio.enviados[0]["Body"]

    def test_conductor_al_aceptar_y_no_al_asignar(
        self, twilio, despachador, chofer, pasajero, django_capture_on_commit_callbacks
    ):
        viaje = ViajeFactory(empresa=pasajero.empresa, pasajero=pasajero, estado=E.SOLICITADO)
        HistorialEstado.objects.create(viaje=viaje, estado_nuevo=E.SOLICITADO, actor=Actor.DESPACHADOR)
        with django_capture_on_commit_callbacks(execute=True):
            asignada = como(despachador).post(
                reverse("viaje-asignar", args=[viaje.pk]), {"conductor": chofer.pk}, format="json"
            )
        assert asignada.status_code == 200, asignada.data
        assert twilio.enviados == []
        asignacion = viaje.asignaciones.get()
        with django_capture_on_commit_callbacks(execute=True):
            como(chofer.usuario).post(reverse("app-aceptar", args=[asignacion.pk]))
        cuerpo = twilio.enviados[0]["Body"]
        assert "Muriel Moreno" in cuerpo
        assert "Toyota Corolla" in cuerpo
        assert "ABCD12" in cuerpo

    def test_rechazo_no_avisa(
        self, twilio, despachador, chofer, pasajero, django_capture_on_commit_callbacks
    ):
        viaje = ViajeFactory(empresa=pasajero.empresa, pasajero=pasajero, estado=E.SOLICITADO)
        HistorialEstado.objects.create(viaje=viaje, estado_nuevo=E.SOLICITADO, actor=Actor.DESPACHADOR)
        como(despachador).post(
            reverse("viaje-asignar", args=[viaje.pk]), {"conductor": chofer.pk}, format="json"
        )
        with django_capture_on_commit_callbacks(execute=True):
            como(chofer.usuario).post(reverse("app-rechazar", args=[viaje.asignaciones.get().pk]))
        assert twilio.enviados == []

    def test_en_camino(self, twilio, chofer, pasajero, django_capture_on_commit_callbacks):
        viaje = viaje_con(chofer, pasajero, E.ACEPTADO)
        with django_capture_on_commit_callbacks(execute=True):
            como(chofer.usuario).post(reverse("app-en-camino", args=[viaje.pk]))
        assert "Muriel Moreno va en camino" in twilio.enviados[0]["Body"]
        assert "Plaza de Armas" in twilio.enviados[0]["Body"]

    def test_tu_vehiculo_te_espera_con_la_geocerca(
        self, twilio, chofer, pasajero, django_capture_on_commit_callbacks
    ):
        viaje = viaje_con(chofer, pasajero, E.EN_CAMINO)
        chofer.estado = EstadoConductor.EN_VIAJE
        chofer.save()
        with django_capture_on_commit_callbacks(execute=True):
            como(chofer.usuario).post(
                reverse("app-posiciones"), {"posiciones": [posicion(CERCA)]}, format="json"
            )
        viaje.refresh_from_db()
        assert viaje.estado == E.EN_ZONA
        assert len(twilio.enviados) == 1
        assert "Tu vehículo te espera" in twilio.enviados[0]["Body"]
        assert "ABCD12" in twilio.enviados[0]["Body"]

    def test_sin_geocerca_no_dice_que_te_espera(
        self, twilio, chofer, pasajero, django_capture_on_commit_callbacks
    ):
        """DC-17: si lo indicó el conductor, el pasajero ya subió."""
        viaje = viaje_con(chofer, pasajero, E.EN_CAMINO)
        with django_capture_on_commit_callbacks(execute=True):
            como(chofer.usuario).post(reverse("app-a-bordo", args=[viaje.pk]))
        assert twilio.enviados == []

    def test_transicion_rechazada_no_avisa(
        self, twilio, chofer, pasajero, django_capture_on_commit_callbacks
    ):
        viaje = viaje_con(chofer, pasajero, E.EN_ZONA)
        with django_capture_on_commit_callbacks(execute=True):
            assert como(chofer.usuario).post(reverse("app-en-camino", args=[viaje.pk])).status_code == 409
        assert twilio.enviados == []

    def test_crear_viaje_sin_pasar_por_el_panel_no_avisa(
        self, twilio, empresa, despachador, django_capture_on_commit_callbacks
    ):
        """Los datos de demostración usan `crear_viaje` directamente: no deben enviar WhatsApp."""
        datos = reserva()
        datos["recogida_en"] = timezone.now() + timedelta(days=1)
        with django_capture_on_commit_callbacks(execute=True):
            servicios.crear_viaje(
                empresa=empresa,
                datos={k: v for k, v in datos.items() if k != "canal"},
                canal="TELEFONO",
                estado_inicial=E.SOLICITADO,
                actor=Actor.DESPACHADOR,
                usuario=despachador,
            )
        assert twilio.enviados == []


@pytest.mark.django_db
class TestEnvio:
    def test_con_plantilla_usa_content_api(self, chofer, pasajero):
        viaje = viaje_con(chofer, pasajero, E.EN_CAMINO)
        twilio = TwilioFalso()
        twilio.plantillas_aviso = {AVISO_EN_CAMINO: "HX" + "2" * 32}
        twilio.avisar(viaje, AVISO_EN_CAMINO)
        datos = twilio.enviados[0]
        assert datos["ContentSid"] == "HX" + "2" * 32
        assert "Body" not in datos
        assert MensajeWhatsapp.objects.get(viaje=viaje).tipo == TipoMensaje.PLANTILLA

    def test_sin_plantilla_va_como_texto(self, chofer, pasajero):
        viaje = viaje_con(chofer, pasajero, E.EN_CAMINO)
        twilio = TwilioFalso()
        twilio.avisar(viaje, AVISO_EN_CAMINO)
        assert "ContentSid" not in twilio.enviados[0]
        mensaje = MensajeWhatsapp.objects.get(viaje=viaje)
        assert (mensaje.tipo, mensaje.direccion) == (TipoMensaje.SESION, DireccionMensaje.SALIENTE)

    def test_twilio_caido_no_revierte_el_estado(
        self, monkeypatch, chofer, pasajero, django_capture_on_commit_callbacks
    ):
        falso = TwilioFalso(http_error(503), http_error(503), http_error(503))
        monkeypatch.setattr(avisos, "obtener_notificador", lambda: falso)
        viaje = viaje_con(chofer, pasajero, E.ACEPTADO)
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = como(chofer.usuario).post(reverse("app-en-camino", args=[viaje.pk]))
        assert respuesta.status_code == 200
        viaje.refresh_from_db()
        assert viaje.estado == E.EN_CAMINO
        assert MensajeWhatsapp.objects.get(viaje=viaje).estado_entrega == EstadoEntrega.FAILED

    def test_un_error_inesperado_tampoco(
        self, monkeypatch, chofer, pasajero, django_capture_on_commit_callbacks
    ):
        def falla(*_):
            raise RuntimeError("inesperado")

        monkeypatch.setattr(avisos, "_enviar", falla)
        viaje = viaje_con(chofer, pasajero, E.ACEPTADO)
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = como(chofer.usuario).post(reverse("app-en-camino", args=[viaje.pk]))
        assert respuesta.status_code == 200

    def test_desarrollo_registra_sin_el_numero_en_el_log(self, chofer, pasajero, caplog):
        viaje = viaje_con(chofer, pasajero, E.EN_CAMINO)
        with caplog.at_level("INFO"):
            NotificadorDesarrollo().avisar(viaje, AVISO_EN_ZONA)
        assert MensajeWhatsapp.objects.filter(viaje=viaje, tipo=TipoMensaje.SESION).count() == 1
        assert pasajero.telefono not in caplog.text

    def test_elige_las_plantillas_de_la_configuracion(self, settings):
        settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN = "AC1", "t"
        settings.TWILIO_WHATSAPP_FROM, settings.WHATSAPP_URL_BASE = "+14155238886", "https://x.example"
        settings.TWILIO_PLANTILLA_AVISO_EN_ZONA = "HX9"
        notificador = obtener_notificador()
        assert isinstance(notificador, NotificadorTwilio)
        assert notificador.plantillas_aviso[AVISO_EN_ZONA] == "HX9"

    def test_cada_aviso_tiene_texto(self, chofer, pasajero):
        viaje = viaje_con(chofer, pasajero, E.EN_CAMINO)
        for tipo in (AVISO_CONFIRMACION, AVISO_CONDUCTOR, AVISO_EN_CAMINO, AVISO_EN_ZONA):
            cuerpo, variables = texto_aviso(viaje, tipo)
            assert all(valor in cuerpo for valor in variables.values())
        with pytest.raises(ValueError, match="desconocido"):
            notificaciones.texto_aviso(viaje, "otro")


@pytest.mark.django_db
class TestCancelarPorWhatsapp:
    """RN-09: solo sin conductor asignado."""

    def test_sin_conductor_cancela(self, twilio, pasajero):
        viaje = ViajeFactory(empresa=pasajero.empresa, pasajero=pasajero, estado=E.SOLICITADO)
        assert verificacion.procesar_entrante(entrante(viaje, payload="cancelar")) == "cancelada"
        viaje.refresh_from_db()
        assert viaje.estado == E.CANCELADO
        assert viaje.origen_cancelacion == OrigenCancelacion.PASAJERO
        assert "RN-09" in viaje.motivo_cancelacion
        cambio = HistorialEstado.objects.get(viaje=viaje, estado_nuevo=E.CANCELADO)
        assert cambio.actor == Actor.PASAJERO
        assert "quedó cancelada" in twilio.enviados[-1]["Body"]

    @pytest.mark.parametrize("estado", [E.ASIGNADO, E.ACEPTADO, E.EN_CAMINO, E.EN_ZONA, E.PASAJERO_A_BORDO])
    def test_con_conductor_no_cancela(self, twilio, chofer, pasajero, estado):
        viaje = viaje_con(chofer, pasajero, estado)
        assert verificacion.procesar_entrante(entrante(viaje, payload="cancelar")) == "con_conductor"
        viaje.refresh_from_db()
        assert viaje.estado == estado
        assert "ya tiene conductor" in twilio.enviados[-1]["Body"]

    def test_lo_asignan_en_el_mismo_instante(self, twilio, chofer, pasajero, monkeypatch):
        viaje = ViajeFactory(empresa=pasajero.empresa, pasajero=pasajero, estado=E.SOLICITADO)
        original = verificacion.estados.transicionar

        def asignar_antes(v, *args, **kwargs):
            type(v).objects.filter(pk=v.pk).update(
                estado=E.ASIGNADO, conductor=chofer, vehiculo=chofer.vehiculo_activo
            )
            return original(v, *args, **kwargs)

        monkeypatch.setattr(verificacion.estados, "transicionar", asignar_antes)
        assert verificacion.procesar_entrante(entrante(viaje, payload="cancelar")) == "con_conductor"

    def test_un_no_suelto_no_cancela_un_viaje_confirmado(self, twilio, pasajero):
        viaje = ViajeFactory(empresa=pasajero.empresa, pasajero=pasajero, estado=E.SOLICITADO)
        datos = entrante(viaje, payload="", Body="No")
        assert verificacion.procesar_entrante(datos) == "sin_accion"
        viaje.refresh_from_db()
        assert viaje.estado == E.SOLICITADO

    def test_con_varias_reservas_y_sin_referencia_no_adivina(self, twilio, pasajero):
        viajes = [
            ViajeFactory(
                empresa=pasajero.empresa,
                pasajero=pasajero,
                estado=E.SOLICITADO,
                recogida_en=timezone.now() + timedelta(days=dias),
            )
            for dias in (1, 2)
        ]
        assert verificacion.procesar_entrante(entrante(viajes[0], payload="cancelar")) == "varias"
        for viaje in viajes:
            viaje.refresh_from_db()
            assert viaje.estado == E.SOLICITADO

    def test_con_varias_reservas_cancela_la_citada(
        self, twilio, chofer, pasajero, django_capture_on_commit_callbacks
    ):
        citada = ViajeFactory(empresa=pasajero.empresa, pasajero=pasajero, estado=E.SOLICITADO)
        otra = ViajeFactory(empresa=pasajero.empresa, pasajero=pasajero, estado=E.SOLICITADO)
        twilio.avisar(citada, AVISO_CONFIRMACION)
        sid = MensajeWhatsapp.objects.get(viaje=citada).proveedor_sid
        assert (
            verificacion.procesar_entrante(entrante(citada, payload="cancelar", original=sid)) == "cancelada"
        )
        citada.refresh_from_db()
        otra.refresh_from_db()
        assert (citada.estado, otra.estado) == (E.CANCELADO, E.SOLICITADO)

    def test_confirmar_de_nuevo(self, twilio, pasajero):
        viaje = ViajeFactory(empresa=pasajero.empresa, pasajero=pasajero, estado=E.SOLICITADO)
        assert verificacion.procesar_entrante(entrante(viaje)) == "ya_confirmada"
        assert "ya está confirmado" in twilio.enviados[-1]["Body"]

    def test_viaje_terminado(self, twilio, chofer, pasajero):
        viaje = viaje_con(chofer, pasajero, E.FINALIZADO)
        sid_original = "SMoriginal"
        MensajeWhatsapp.objects.create(
            pasajero=pasajero,
            viaje=viaje,
            direccion=DireccionMensaje.SALIENTE,
            tipo=TipoMensaje.SESION,
            cuerpo="x",
            proveedor_sid=sid_original,
        )
        datos = entrante(viaje, payload="cancelar", original=sid_original)
        assert verificacion.procesar_entrante(datos) == "no_vigente"
