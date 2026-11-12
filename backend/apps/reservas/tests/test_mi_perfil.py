"""HU-45 (DC-50): «Mi perfil» del pasajero, WhatsApp nuevo por confirmar y eliminación de la cuenta.

Eliminar anonimiza: USUARIO inactivo y sin clave, PASAJERO «Pasajero eliminado» con teléfono NULL y
mensajes sin contenido. VIAJE, PAGO_VIAJE, HISTORIAL_ESTADO y AUDITORIA se conservan. Con teléfono NULL,
ni los envíos de WhatsApp ni los reportes fallan.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import Auditoria
from apps.cuentas.models import Rol, Usuario
from apps.integraciones.notificaciones import AVISO_CONFIRMACION
from apps.reservas import cuentas_pasajero, tareas
from apps.reservas.models import (
    CuentaPasajero,
    DireccionMensaje,
    EstadoEntrega,
    EstadoViaje,
    HistorialEstado,
    MensajeWhatsapp,
    MetodoPago,
    PagoViaje,
    Pasajero,
    TipoMensaje,
    Viaje,
)
from apps.reservas.tests.fabricas import PasajeroFactory, ViajeFactory
from apps.reservas.tests.test_cuenta_pasajero import CLAVE, TELEFONO, crear_cuenta, entrar, whatsapp
from apps.reservas.tests.test_whatsapp import TwilioFalso

E = EstadoViaje
NUEVO = "+56900009302"
PERFIL = reverse("mi-cuenta")


@pytest.fixture
def twilio(monkeypatch):
    falso = TwilioFalso()
    monkeypatch.setattr(tareas, "obtener_notificador", lambda: falso)
    return falso


@pytest.fixture
def activa(cliente, empresa, twilio, settings, django_capture_on_commit_callbacks):
    """Cuenta creada y confirmada por WhatsApp (como en HU-35); devuelve el cliente con sesión."""
    settings.DEBUG = True
    with django_capture_on_commit_callbacks(execute=True):
        crear_cuenta(cliente, empresa)
        whatsapp(cliente, "Confirmar cuenta")
    web, _ = entrar()
    return web


def cuenta():
    return CuentaPasajero.objects.select_related("pasajero", "usuario").get()


def enviados_a(twilio, telefono):
    return [d.get("Body") for d in twilio.enviados if d["To"] == f"whatsapp:{telefono}"]


@pytest.mark.django_db
class TestVerPerfil:
    def test_datos_del_perfil(self, activa):
        datos = activa.get(PERFIL).data
        assert (datos["nombre"], datos["email"], datos["telefono"]) == (
            "Paula Pasajera",
            "paula@correo.example",
            TELEFONO,
        )
        assert datos["telefono_pendiente"] is None
        assert datos["pasajero_desde"] is not None
        assert datos["password_cambiada_en"] is None

    def test_fecha_del_ultimo_cambio_de_clave(self, activa):
        respuesta = activa.post(
            reverse("auth-password"),
            {"password_actual": CLAVE, "password_nueva": "Otra-Clave-Sintetica-2026"},
            format="json",
        )
        assert respuesta.status_code in (200, 204), respuesta.data
        assert activa.get(PERFIL).data["password_cambiada_en"] is not None

    def test_solo_el_pasajero(self, panel, despachador):
        panel.force_authenticate(despachador)
        assert panel.get(PERFIL).status_code == 403
        assert panel.patch(PERFIL, {"nombre": "X"}, format="json").status_code == 403


@pytest.mark.django_db
class TestEditarPerfil:
    def test_nombre_en_cuenta_pasajero_y_usuario(self, activa):
        respuesta = activa.patch(PERFIL, {"nombre": "  Paula Andrea Pasajera "}, format="json")
        assert respuesta.status_code == 200, respuesta.data
        assert respuesta.data["nombre"] == "Paula Andrea Pasajera"
        c = cuenta()
        assert (c.nombre, c.pasajero.nombre, c.usuario.nombre) == ("Paula Andrea Pasajera",) * 3
        registro = Auditoria.objects.get(accion="EDITAR_PERFIL")
        # Solo qué cambió: el nombre anterior no queda en la auditoría.
        assert registro.datos_previos == {"campos": ["nombre"]}

    def test_nombre_vacio(self, activa):
        respuesta = activa.patch(PERFIL, {"nombre": "   "}, format="json")
        assert respuesta.status_code == 400
        assert cuenta().nombre == "Paula Pasajera"

    def test_el_correo_no_se_cambia(self, activa):
        respuesta = activa.patch(PERFIL, {"email": "otra@correo.example"}, format="json")
        assert respuesta.status_code == 200
        assert cuenta().usuario.email == "paula@correo.example"

    def test_whatsapp_nuevo_queda_pendiente(self, activa, twilio, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = activa.patch(PERFIL, {"telefono": "+56 9 0000 9302"}, format="json")
        assert respuesta.status_code == 200, respuesta.data
        assert (respuesta.data["telefono"], respuesta.data["telefono_pendiente"]) == (TELEFONO, NUEVO)
        c = cuenta()
        assert (c.telefono, c.pasajero.telefono, c.telefono_pendiente) == (TELEFONO, TELEFONO, NUEVO)
        assert any("CONFIRMAR CUENTA" in texto for texto in enviados_a(twilio, NUEVO))
        # Mientras tanto la cuenta sigue activa: puede pedir y ver sus reservas.
        assert activa.get(reverse("mi-cuenta-reservas")).status_code == 200

    def test_al_confirmar_cambia_y_conserva_el_historial(
        self, activa, cliente, empresa, twilio, django_capture_on_commit_callbacks
    ):
        viaje = ViajeFactory(empresa=empresa, pasajero=cuenta().pasajero, estado=E.FINALIZADO)
        with django_capture_on_commit_callbacks(execute=True):
            activa.patch(PERFIL, {"telefono": NUEVO}, format="json")
        invitado = Pasajero.objects.get(empresa=empresa, telefono=NUEVO)
        anterior = ViajeFactory(empresa=empresa, pasajero=invitado, estado=E.FINALIZADO)
        with django_capture_on_commit_callbacks(execute=True):
            whatsapp(cliente, "Confirmar cuenta", desde=NUEVO, sid="SM" + "8" * 32)
        c = cuenta()
        assert (c.telefono, c.telefono_pendiente, c.pasajero.telefono) == (NUEVO, None, NUEVO)
        assert c.pasajero.verificado_en is not None
        # El invitado del número nuevo era la misma persona: su viaje pasa a la cuenta y él se borra.
        assert not Pasajero.objects.filter(pk=invitado.pk).exists()
        assert set(Viaje.objects.filter(pasajero=c.pasajero)) == {viaje, anterior}
        assert any("Desde ahora" in texto for texto in enviados_a(twilio, NUEVO))
        assert Auditoria.objects.filter(accion="CONFIRMAR_TELEFONO").exists()

    def test_sin_confirmar_a_tiempo_se_descarta(
        self, activa, cliente, empresa, twilio, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            activa.patch(PERFIL, {"telefono": NUEVO}, format="json")
        minutos = empresa.configuracion.expiracion_verificacion_min
        CuentaPasajero.objects.update(telefono_pendiente_en=timezone.now() - timedelta(minutes=minutos + 1))
        assert activa.get(PERFIL).data["telefono_pendiente"] is None
        with django_capture_on_commit_callbacks(execute=True):
            whatsapp(cliente, "Confirmar cuenta", desde=NUEVO, sid="SM" + "7" * 32)
        assert cuenta().telefono == TELEFONO

    def test_volver_al_numero_actual_descarta_el_pendiente(
        self, activa, twilio, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            activa.patch(PERFIL, {"telefono": NUEVO}, format="json")
        respuesta = activa.patch(PERFIL, {"telefono": TELEFONO}, format="json")
        assert respuesta.data["telefono_pendiente"] is None
        assert cuenta().telefono_pendiente is None

    def test_whatsapp_de_otra_cuenta(
        self, activa, cliente, empresa, twilio, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            crear_cuenta(cliente, empresa, email="otra@correo.example", telefono=NUEVO)
            whatsapp(cliente, "Confirmar cuenta", desde=NUEVO, sid="SM" + "6" * 32)
        respuesta = activa.patch(PERFIL, {"telefono": NUEVO}, format="json")
        assert respuesta.status_code == 409
        assert respuesta.data["code"] == "telefono_en_uso" or "telefono_en_uso" in str(respuesta.data)

    def test_telefono_invalido(self, activa):
        assert activa.patch(PERFIL, {"telefono": "12"}, format="json").status_code == 400


def con_historial(empresa, pasajero, estado=E.FINALIZADO):
    """Viaje con pago, historial y mensajes, para ver qué se conserva."""
    viaje = ViajeFactory(empresa=empresa, pasajero=pasajero, estado=estado)
    HistorialEstado.objects.create(
        viaje=viaje, estado_anterior=E.SOLICITADO, estado_nuevo=estado, actor="SISTEMA"
    )
    if estado == E.FINALIZADO:
        PagoViaje.objects.create(viaje=viaje, metodo=MetodoPago.values[0], monto=15000)
    for direccion in (DireccionMensaje.SALIENTE, DireccionMensaje.ENTRANTE):
        MensajeWhatsapp.objects.create(
            pasajero=pasajero,
            viaje=viaje,
            direccion=direccion,
            tipo=TipoMensaje.SESION,
            cuerpo="Hola, soy Paula Pasajera, mi número es +56900009301",
            estado_entrega=EstadoEntrega.DELIVERED,
        )
    return viaje


@pytest.mark.django_db
class TestEliminarCuenta:
    def test_anonimiza_y_conserva_lo_contable(self, activa, empresa):
        c = cuenta()
        pasajero, usuario = c.pasajero, c.usuario
        viaje = con_historial(empresa, pasajero)
        campos = ("tipo", "estado_entrega", "creado_en")
        mensajes = list(MensajeWhatsapp.objects.filter(pasajero=pasajero).values(*campos))

        assert activa.delete(PERFIL).status_code == 204

        assert not CuentaPasajero.objects.exists()
        usuario.refresh_from_db()
        assert (usuario.activo, usuario.has_usable_password(), usuario.email, usuario.rol) == (
            False,
            False,
            f"eliminado-{usuario.pk}@invalid",
            Rol.PASAJERO,
        )
        assert entrar()[1].status_code == 401
        pasajero.refresh_from_db()
        assert (pasajero.nombre, pasajero.telefono) == ("Pasajero eliminado", None)
        assert set(MensajeWhatsapp.objects.filter(pasajero=pasajero).values_list("cuerpo", flat=True)) == {
            "[eliminado]"
        }
        assert list(MensajeWhatsapp.objects.filter(pasajero=pasajero).values(*campos)) == mensajes
        assert Viaje.objects.filter(pk=viaje.pk, pasajero=pasajero).exists()
        assert PagoViaje.objects.filter(viaje=viaje).exists()
        assert HistorialEstado.objects.filter(viaje=viaje).exists()
        registro = Auditoria.objects.get(accion="ELIMINAR_CUENTA")
        assert (registro.motivo, registro.entidad_id) == ("Cuenta eliminada por el titular", usuario.pk)
        # Ningún registro de auditoría guarda el correo, el nombre ni el teléfono del titular.
        for fila in Auditoria.objects.values("motivo", "datos_previos"):
            texto = str(fila)
            assert "paula" not in texto.lower() and TELEFONO not in texto

    def test_la_unicidad_sigue_para_los_telefonos_no_nulos(self, activa, empresa):
        assert activa.delete(PERFIL).status_code == 204
        otro = PasajeroFactory(empresa=empresa, telefono=None, nombre="Otro eliminado")
        assert Pasajero.objects.filter(empresa=empresa, telefono__isnull=True).count() == 2
        PasajeroFactory(empresa=empresa, telefono=TELEFONO)  # el número quedó libre
        assert otro.pk

    @pytest.mark.parametrize("estado", cuentas_pasajero.VIAJE_ACTIVO)
    def test_con_viaje_activo_no_se_elimina(self, activa, empresa, estado):
        ViajeFactory(empresa=empresa, pasajero=cuenta().pasajero, estado=estado)
        respuesta = activa.delete(PERFIL)
        assert respuesta.status_code == 409
        assert "viaje_activo" in str(respuesta.data) or respuesta.data.get("code") == "viaje_activo"
        assert cuenta().usuario.activo
        assert not Auditoria.objects.filter(accion="ELIMINAR_CUENTA").exists()

    @pytest.mark.parametrize("estado", [E.FINALIZADO, E.CANCELADO, E.PENDIENTE_CONFIRMACION])
    def test_sin_viaje_activo_se_elimina(self, activa, empresa, estado):
        extra = {}
        if estado == E.CANCELADO:
            extra = {"motivo_cancelacion": "Cancelada por el pasajero.", "origen_cancelacion": "PASAJERO"}
        ViajeFactory(empresa=empresa, pasajero=cuenta().pasajero, estado=estado, **extra)
        assert activa.delete(PERFIL).status_code == 204


@pytest.fixture
def eliminado(empresa):
    """Pasajero de una cuenta eliminada, con un viaje finalizado y mensajes."""
    pasajero = PasajeroFactory(empresa=empresa, nombre="Pasajero eliminado", telefono=None)
    return con_historial(empresa, pasajero)


@pytest.mark.django_db
class TestSinTelefono:
    """DC-50: con `telefono` NULL, los envíos se omiten (sin error ni reintento) y los reportes responden."""

    def test_avisos_y_respuestas_se_omiten(self, eliminado, twilio):
        tareas.enviar_aviso.delay(eliminado.pk, AVISO_CONFIRMACION)
        tareas.enviar_verificacion.delay(eliminado.pk, timezone.now().isoformat())
        tareas.enviar_respuesta.delay(eliminado.pasajero_id, eliminado.pk, "Hola")
        assert twilio.enviados == []

    def test_chat_queda_fallido(self, eliminado, twilio):
        mensaje = MensajeWhatsapp.objects.create(
            pasajero=eliminado.pasajero,
            viaje=eliminado,
            direccion=DireccionMensaje.SALIENTE,
            tipo=TipoMensaje.SESION,
            cuerpo="¿Dónde lo espero?",
            estado_entrega=EstadoEntrega.QUEUED,
        )
        tareas.enviar_chat.delay(mensaje.pk)
        mensaje.refresh_from_db()
        assert mensaje.estado_entrega == EstadoEntrega.FAILED
        assert twilio.enviados == []

    def test_panel_y_reportes(self, eliminado, panel, administrador):
        panel.force_authenticate(administrador)
        lista = panel.get(reverse("viaje-list"))
        assert lista.status_code == 200
        ficha = panel.get(reverse("viaje-detail", args=[eliminado.pk]))
        assert ficha.status_code == 200
        assert (ficha.data["pasajero"]["nombre"], ficha.data["pasajero"]["telefono"]) == (
            "Pasajero eliminado",
            None,
        )
        desde = (timezone.now() - timedelta(days=60)).date().isoformat()
        for tipo in ("historial", "cancelaciones", "liquidacion"):
            assert panel.get(reverse("reporte", args=[tipo]), {"desde": desde}).status_code == 200
            assert panel.get(reverse("reporte-csv", args=[tipo]), {"desde": desde}).status_code == 200
        assert panel.get(reverse("viaje-list"), {"q": "eliminado"}).status_code == 200

    def test_whatsapp_de_un_numero_desconocido(self, eliminado, cliente, settings):
        settings.DEBUG = True
        respuesta = whatsapp(cliente, "Hola", desde="+56900009399", sid="SM" + "5" * 32)
        assert respuesta.status_code == 200

    def test_usuario_eliminado_no_es_rol_valido_para_ingresar(self, activa):
        activa.delete(PERFIL)
        assert not Usuario.objects.filter(rol=Rol.PASAJERO, activo=True).exists()
