"""HU-25 · Acceso de convenio con link protegido. CP-26 (RN-07, RN-08)."""

import time
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import Auditoria, Entidad
from apps.convenios import servicios as convenios
from apps.flota.models import EstadoConductor
from apps.portal.convenio_views import COOKIE
from apps.portal.tests.test_portal import solicitud
from apps.reservas import tareas
from apps.reservas.models import Actor, Canal, EstadoViaje, HistorialEstado, MetodoPago, Viaje
from apps.reservas.tests.fabricas import ConvenioFactory
from apps.reservas.tests.test_ejecucion import chofer  # noqa: F401

ORIGEN = "http://panel.example"
CLAVE = "ClaveSintetica23"


@pytest.fixture(autouse=True)
def _origenes(settings):
    settings.PANEL_ORIGENES = [ORIGEN]


@pytest.fixture
def convenio(empresa):
    convenio = ConvenioFactory(empresa=empresa)
    convenio.set_password(CLAVE)
    convenio.save()
    return convenio


def url(nombre, convenio):
    return reverse(f"convenio-{nombre}", args=[convenio.token_link])


def entrar(cliente, convenio, password=CLAVE):
    return cliente.post(url("sesion", convenio), {"password": password}, format="json", HTTP_ORIGIN=ORIGEN)


def pedir(cliente, convenio, **cambios):
    return cliente.post(url("solicitudes", convenio), solicitud(**cambios), format="json", HTTP_ORIGIN=ORIGEN)


@pytest.fixture
def dentro(cliente, convenio):
    assert entrar(cliente, convenio).status_code == 200
    return cliente


@pytest.mark.django_db
class TestLink:
    def test_sin_sesion_pide_contrasena_y_no_revela_el_cliente(self, cliente, convenio, empresa):
        datos = cliente.get(url("acceso", convenio)).json()
        assert datos["sesion_activa"] is False
        assert datos["cliente_nombre"] is None
        assert datos["razon_social"] == empresa.razon_social
        assert convenio.cliente_nombre not in str(datos)

    def test_token_desconocido_404(self, cliente):
        assert cliente.get(reverse("convenio-acceso", args=["x" * 43])).status_code == 404

    def test_convenio_inactivo_404_igual_que_desconocido(self, cliente, convenio):
        """RN-08."""
        convenio.activo = False
        convenio.save()
        assert cliente.get(url("acceso", convenio)).status_code == 404
        assert entrar(cliente, convenio).status_code == 404

    def test_empresa_inactiva_404(self, cliente, convenio, empresa):
        empresa.activa = False
        empresa.save()
        assert cliente.get(url("acceso", convenio)).status_code == 404


@pytest.mark.django_db
class TestContrasena:
    def test_correcta_abre_la_sesion(self, cliente, convenio):
        respuesta = entrar(cliente, convenio)
        assert respuesta.status_code == 200
        assert respuesta.json() == {"cliente_nombre": convenio.cliente_nombre}
        cookie = respuesta.cookies[COOKIE]
        assert cookie["httponly"] is True
        assert cookie["samesite"] == "Strict"
        assert cookie["path"] == "/api/convenio/"
        assert cookie["max-age"] == 2 * 3600
        datos = cliente.get(url("acceso", convenio)).json()
        assert (datos["sesion_activa"], datos["cliente_nombre"]) == (True, convenio.cliente_nombre)

    def test_incorrecta_401_sin_sesion(self, cliente, convenio):
        respuesta = entrar(cliente, convenio, "mala")
        assert respuesta.status_code == 401
        assert respuesta.json()["code"] == "credenciales_invalidas"
        assert COOKIE not in respuesta.cookies
        convenio.refresh_from_db()
        assert convenio.intentos_fallidos == 1

    def test_acertar_reinicia_el_conteo(self, cliente, convenio):
        for _ in range(4):
            entrar(cliente, convenio, "mala")
        assert entrar(cliente, convenio).status_code == 200
        convenio.refresh_from_db()
        assert convenio.intentos_fallidos == 0

    def test_origen_ajeno_403(self, cliente, convenio):
        respuesta = cliente.post(
            url("sesion", convenio), {"password": CLAVE}, format="json", HTTP_ORIGIN="http://otro.example"
        )
        assert respuesta.status_code == 403

    def test_la_contrasena_no_llega_a_la_auditoria(self, cliente, convenio):
        for _ in range(5):
            entrar(cliente, convenio, "ClaveProbadaMala")
        registro = Auditoria.objects.get(accion="BLOQUEO_LINK")
        assert "ClaveProbadaMala" not in str(registro.datos_previos)


@pytest.mark.django_db
class TestBloqueo:
    def bloquear(self, cliente, convenio):
        return [entrar(cliente, convenio, "mala").status_code for _ in range(5)]

    def test_al_quinto_intento_bloquea_y_audita(self, cliente, convenio, empresa):
        estados = self.bloquear(cliente, convenio)
        assert estados == [401, 401, 401, 401, 423]
        convenio.refresh_from_db()
        duracion = convenio.bloqueado_hasta - timezone.now()
        assert timedelta(minutes=14) < duracion <= timedelta(minutes=15)
        registro = Auditoria.objects.get(accion="BLOQUEO_LINK")
        assert (registro.entidad, registro.entidad_id) == (Entidad.CONVENIO, convenio.pk)
        assert (registro.empresa, registro.usuario) == (empresa, None)

    def test_bloqueado_rechaza_hasta_la_correcta(self, cliente, convenio):
        self.bloquear(cliente, convenio)
        respuesta = entrar(cliente, convenio)
        assert respuesta.status_code == 423
        assert respuesta.json()["code"] == "convenio_bloqueado"
        assert COOKIE not in respuesta.cookies
        assert Auditoria.objects.filter(accion="BLOQUEO_LINK").count() == 1

    def test_duracion_configurable(self, cliente, convenio, settings):
        settings.CONVENIO_BLOQUEO = timedelta(minutes=40)
        self.bloquear(cliente, convenio)
        convenio.refresh_from_db()
        assert convenio.bloqueado_hasta - timezone.now() > timedelta(minutes=39)

    def test_vencido_parte_de_cero(self, cliente, convenio):
        self.bloquear(cliente, convenio)
        type(convenio).objects.filter(pk=convenio.pk).update(
            bloqueado_hasta=timezone.now() - timedelta(seconds=1)
        )
        assert entrar(cliente, convenio, "mala").status_code == 401
        convenio.refresh_from_db()
        assert (convenio.intentos_fallidos, convenio.bloqueado_hasta) == (1, None)
        assert entrar(cliente, convenio).status_code == 200

    def test_es_por_convenio(self, cliente, convenio, empresa):
        otro = ConvenioFactory(empresa=empresa)
        otro.set_password(CLAVE)
        otro.save()
        self.bloquear(cliente, convenio)
        assert entrar(cliente, otro).status_code == 200

    def test_rotar_la_contrasena_lo_levanta(self, cliente, convenio, administrador):
        self.bloquear(cliente, convenio)
        nueva = convenios.rotar_password(convenio, usuario=administrador)
        assert entrar(cliente, convenio, nueva).status_code == 200

    def test_se_ve_en_la_auditoria_del_panel(self, cliente, convenio, administrador):
        self.bloquear(cliente, convenio)
        cliente.force_authenticate(administrador)
        filas = cliente.get(reverse("convenio-auditoria", args=[convenio.pk])).json()["results"]
        assert [(f["accion"], f["usuario"]) for f in filas] == [("BLOQUEO_LINK", None)]


@pytest.mark.django_db
class TestSesion:
    def test_vence_por_inactividad(self, dentro, convenio, settings):
        settings.CONVENIO_SESION = timedelta(seconds=-1)
        assert dentro.get(url("acceso", convenio)).json()["sesion_activa"] is False
        respuesta = pedir(dentro, convenio)
        assert respuesta.status_code == 401
        assert respuesta.json()["code"] == "sesion_convenio_vencida"
        assert not Viaje.objects.exists()

    def test_el_uso_la_renueva(self, dentro, convenio, monkeypatch):
        """Vence por inactividad, no desde el ingreso: con uso a la 1,5 h sigue viva a las 3 h."""
        inicio = time.time()
        monkeypatch.setattr("django.core.signing.time.time", lambda: inicio + 1.5 * 3600)
        respuesta = dentro.get(url("acceso", convenio))
        assert respuesta.json()["sesion_activa"] is True
        assert respuesta.cookies[COOKIE]["max-age"] == 2 * 3600
        monkeypatch.setattr("django.core.signing.time.time", lambda: inicio + 3 * 3600)
        assert dentro.get(url("acceso", convenio)).json()["sesion_activa"] is True

    def test_sin_uso_vence_a_las_dos_horas(self, dentro, convenio, monkeypatch):
        inicio = time.time()
        monkeypatch.setattr("django.core.signing.time.time", lambda: inicio + 2 * 3600 + 5)
        assert dentro.get(url("acceso", convenio)).json()["sesion_activa"] is False

    def test_duracion_configurable(self, cliente, convenio, settings):
        settings.CONVENIO_SESION = timedelta(minutes=30)
        assert entrar(cliente, convenio).cookies[COOKIE]["max-age"] == 1800

    def test_sin_sesion_no_reserva(self, cliente, convenio):
        assert pedir(cliente, convenio).status_code == 401
        assert not Viaje.objects.exists()

    def test_cookie_alterada(self, dentro, convenio):
        dentro.cookies[COOKIE] = dentro.cookies[COOKIE].value + "x"
        assert pedir(dentro, convenio).status_code == 401

    def test_no_sirve_para_otro_convenio(self, dentro, empresa):
        otro = ConvenioFactory(empresa=empresa)
        assert pedir(dentro, otro).status_code == 401

    def test_rotar_la_contrasena_la_invalida(self, dentro, convenio, administrador):
        convenios.rotar_password(convenio, usuario=administrador)
        assert pedir(dentro, convenio).status_code == 401

    def test_desactivar_invalida_al_instante(self, dentro, convenio, administrador):
        """RN-08, con una sesión ya abierta."""
        assert pedir(dentro, convenio).status_code == 201
        convenios.editar(convenio, {"activo": False}, usuario=administrador)
        assert pedir(dentro, convenio).status_code == 404
        assert dentro.get(url("acceso", convenio)).status_code == 404
        assert Viaje.objects.filter(convenio=convenio).count() == 1  # No afecta el historial.

    def test_salir_borra_la_cookie(self, dentro, convenio):
        respuesta = dentro.post(url("salir", convenio), HTTP_ORIGIN=ORIGEN)
        assert respuesta.status_code == 204
        assert respuesta.cookies[COOKIE]["max-age"] == 0
        assert dentro.get(url("acceso", convenio)).json()["sesion_activa"] is False


@pytest.mark.django_db
class TestReserva:
    def test_queda_solicitado_con_el_convenio(self, dentro, convenio):
        """RN-07."""
        respuesta = pedir(dentro, convenio)
        assert respuesta.status_code == 201, respuesta.data
        assert respuesta.json()["estado"] == EstadoViaje.SOLICITADO
        assert "expira_en" not in respuesta.json()
        viaje = Viaje.objects.get()
        assert (viaje.estado, viaje.canal, viaje.convenio) == (
            EstadoViaje.SOLICITADO,
            Canal.CONVENIO,
            convenio,
        )
        assert viaje.empresa == convenio.empresa
        inicial = HistorialEstado.objects.get(viaje=viaje)
        assert (inicial.estado_nuevo, inicial.actor) == (EstadoViaje.SOLICITADO, Actor.PASAJERO)

    def test_no_pide_verificacion_y_avisa_la_confirmacion(
        self, dentro, convenio, monkeypatch, django_capture_on_commit_callbacks
    ):
        verificaciones, avisos = [], []
        monkeypatch.setattr(tareas.enviar_verificacion, "delay", lambda *a: verificaciones.append(a))
        monkeypatch.setattr(tareas.enviar_aviso, "delay", lambda *a: avisos.append(a))
        with django_capture_on_commit_callbacks(execute=True):
            assert pedir(dentro, convenio).status_code == 201
        viaje = Viaje.objects.get()
        assert verificaciones == []
        assert [a[0] for a in avisos] == [viaje.pk]

    def test_no_expira_por_verificacion(self, dentro, convenio):
        """RN-06 no aplica."""
        pedir(dentro, convenio)
        Viaje.objects.update(creado_en=timezone.now() - timedelta(hours=1))
        tareas.expirar_solicitudes()
        assert Viaje.objects.get().estado == EstadoViaje.SOLICITADO

    def test_valida_como_el_portal(self, dentro, convenio):
        assert "telefono" in pedir(dentro, convenio, telefono="123").json()
        assert "acepta_privacidad" in pedir(dentro, convenio, acepta_privacidad=False).json()
        assert not Viaje.objects.exists()

    def test_aparece_en_el_panel_de_su_empresa(self, dentro, convenio, administrador):
        pedir(dentro, convenio)
        dentro.force_authenticate(administrador)
        fila = dentro.get(reverse("viaje-list")).json()["results"][0]
        assert fila["convenio"]["id"] == convenio.pk

    def test_admite_el_metodo_convenio(self, dentro, convenio, chofer):  # noqa: F811
        pedir(dentro, convenio)
        viaje = Viaje.objects.get()
        Viaje.objects.filter(pk=viaje.pk).update(
            estado=EstadoViaje.PASAJERO_A_BORDO, conductor=chofer, vehiculo=chofer.vehiculo_activo
        )
        dentro.force_authenticate(chofer.usuario)
        respuesta = dentro.post(
            reverse("app-finalizar", args=[viaje.pk]),
            {"metodo": MetodoPago.CONVENIO, "monto": 15000},
            format="json",
        )
        assert respuesta.status_code == 200, respuesta.data
        chofer.refresh_from_db()
        assert chofer.estado == EstadoConductor.DISPONIBLE
