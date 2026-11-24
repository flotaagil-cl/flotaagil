"""HU-75 (CC-24, DC-79): módulos activos por despachador.

CP-65: el administrador los configura (auditoría y cierre de sesiones); Usuarios nunca es un módulo.
CP-66: el servidor bloquea las API y los WebSocket de los módulos apagados; el administrador tiene todo.
"""

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.urls import reverse
from rest_framework.test import APIClient

from apps.auditoria.models import Auditoria
from apps.cuentas.models import MODULOS_DESPACHADOR, Modulo, Rol, Usuario
from apps.cuentas.tests.fabricas import CLAVE_PRUEBA, UsuarioFactory
from apps.flota.tests.test_mapa_ws import access
from config.asgi import application

LISTA = reverse("usuario-panel-list")
TODOS = [str(m) for m in Modulo]
DEFECTO = [str(m) for m in MODULOS_DESPACHADOR]

# Una lectura representativa de cada módulo.
LECTURAS = {
    Modulo.MAPA: None,  # solo WebSocket
    Modulo.RESERVAS: reverse("viaje-list"),
    Modulo.VUELOS: reverse("vuelos-de-hoy"),
    Modulo.CHAT: reverse("chat-conversaciones"),
    Modulo.CONVENIOS: reverse("convenio-list"),
    Modulo.VEHICULOS: reverse("vehiculo-list"),
    Modulo.CONDUCTORES: reverse("conductor-list"),
    Modulo.CAJA: reverse("turnos-por-cerrar"),
    Modulo.REPORTES: reverse("reporte-opciones"),
    Modulo.CONFIGURACION: reverse("configuracion-empresa"),
}


def detalle(usuario):
    return reverse("usuario-panel-detail", args=[usuario.pk])


def como(usuario):
    cliente = APIClient()
    cliente.force_authenticate(usuario)
    return cliente


def login_panel(email):
    web = APIClient(HTTP_ORIGIN="http://localhost:5173")
    respuesta = web.post(reverse("auth-token"), {"email": email, "password": CLAVE_PRUEBA}, format="json")
    assert respuesta.status_code == 200
    return web


@pytest.fixture
def api(cliente, administrador):
    cliente.force_authenticate(administrador)
    return cliente


@pytest.mark.django_db
class TestConfigurar:
    def test_por_defecto_los_de_siempre(self, api, despachador, administrador):
        datos = {u["id"]: u["modulos"] for u in api.get(LISTA).json()["results"]}
        assert datos[despachador.pk] == DEFECTO
        assert datos[administrador.pk] == TODOS

    def test_crear_con_modulos(self, api):
        cuerpo = {"nombre": "Despacho Noche", "email": "noche@ejemplo.example", "rol": "DESPACHADOR"}
        respuesta = api.post(LISTA, cuerpo | {"modulos": ["CHAT", "MAPA", "CHAT"]}, format="json")
        assert respuesta.status_code == 201
        assert respuesta.json()["modulos"] == ["MAPA", "CHAT"]  # sin repetidos, en el orden del menú
        assert Usuario.objects.get(email="noche@ejemplo.example").modulos == ["MAPA", "CHAT"]

    def test_dar_y_quitar_audita_y_cierra_sesiones(self, api, despachador):
        web = login_panel(despachador.email)
        nuevos = ["RESERVAS", "CONDUCTORES", "REPORTES"]
        respuesta = api.patch(detalle(despachador), {"modulos": nuevos}, format="json")
        assert respuesta.status_code == 200, respuesta.json()
        assert respuesta.json()["modulos"] == nuevos
        registro = Auditoria.objects.get(accion="EDITAR", entidad_id=despachador.pk)
        assert registro.datos_previos == {"modulos": DEFECTO}
        assert web.post(reverse("auth-refresh")).status_code == 401

    def test_los_mismos_modulos_no_auditan(self, api, despachador):
        assert api.patch(detalle(despachador), {"modulos": DEFECTO}, format="json").status_code == 200
        assert not Auditoria.objects.filter(accion="EDITAR").exists()

    @pytest.mark.parametrize("modulo", ["USUARIOS", "INICIO", "OTRO"])
    def test_usuarios_no_es_un_modulo(self, api, despachador, modulo):
        respuesta = api.patch(detalle(despachador), {"modulos": ["MAPA", modulo]}, format="json")
        assert respuesta.status_code == 400 and "modulos" in respuesta.json()
        assert Usuario.objects.get(pk=despachador.pk).modulos == DEFECTO

    def test_solo_el_administrador(self, despachador):
        despachador.modulos = TODOS
        despachador.save()
        cliente = como(despachador)
        assert cliente.patch(detalle(despachador), {"modulos": TODOS}, format="json").status_code == 403
        assert cliente.get(LISTA).status_code == 403  # Usuarios sigue siendo solo del administrador

    def test_la_sesion_trae_los_modulos(self, despachador, administrador):
        despachador.modulos = ["CHAT"]
        despachador.save()
        assert como(despachador).get(reverse("auth-yo")).json()["modulos"] == ["CHAT"]
        assert como(administrador).get(reverse("auth-yo")).json()["modulos"] == TODOS


@pytest.mark.django_db
class TestBloqueoEnElServidor:
    @pytest.mark.parametrize("modulo", [m for m, ruta in LECTURAS.items() if ruta])
    def test_solo_con_el_modulo(self, despachador, modulo):
        ruta = LECTURAS[modulo]
        despachador.modulos = []
        despachador.save()
        assert como(despachador).get(ruta).status_code == 403
        despachador.modulos = [str(modulo)]
        despachador.save()
        assert como(despachador).get(ruta).status_code == 200

    def test_el_administrador_tiene_todo(self, administrador):
        cliente = como(administrador)
        for ruta in filter(None, LECTURAS.values()):
            assert cliente.get(ruta).status_code == 200, ruta

    def test_sin_modulos_le_queda_inicio(self, despachador):
        despachador.modulos = []
        despachador.save()
        assert como(despachador).get(reverse("indicadores")).status_code == 200

    def test_el_conductor_sigue_con_su_chat(self, empresa):
        conductor = UsuarioFactory(empresa=empresa, rol=Rol.CONDUCTOR, modulos=[])
        assert como(conductor).get(reverse("chat-conversaciones")).status_code == 200

    def test_con_conductores_puede_buscar_vehiculos_pero_no_editarlos(self, despachador, empresa):
        from apps.reservas.tests.fabricas import VehiculoFactory

        vehiculo = VehiculoFactory(empresa=empresa)
        despachador.modulos = ["CONDUCTORES"]
        despachador.save()
        cliente = como(despachador)
        assert cliente.get(reverse("vehiculo-list")).status_code == 200
        ficha = reverse("vehiculo-detail", args=[vehiculo.pk])
        assert cliente.patch(ficha, {"activo": False}, format="json").status_code == 403


def _conecta(usuario, ruta) -> int | None:
    """Abre el WebSocket con el access del usuario. None si acepta; el código de cierre si no."""

    async def probar():
        comunicador = WebsocketCommunicator(
            application,
            ruta,
            headers=[(b"origin", b"http://localhost:5173")],
            subprotocols=["flotaagil", access(usuario)],
        )
        conectado, codigo = await comunicador.connect()
        await comunicador.disconnect()
        return None if conectado else codigo

    return async_to_sync(probar)()


@pytest.mark.django_db(transaction=True)
class TestWebSocket:
    def test_mapa_con_mapa_o_conductores(self, despachador):
        despachador.modulos = ["RESERVAS"]
        despachador.save()
        assert _conecta(despachador, "/ws/mapa/") == 4403
        for modulos in (["MAPA"], ["CONDUCTORES"]):
            despachador.modulos = modulos
            despachador.save()
            assert _conecta(despachador, "/ws/mapa/") is None

    def test_chat_con_chat(self, despachador):
        despachador.modulos = ["RESERVAS"]
        despachador.save()
        assert _conecta(despachador, "/ws/chat/") == 4403
        despachador.modulos = ["CHAT"]
        despachador.save()
        assert _conecta(despachador, "/ws/chat/") is None

    def test_el_administrador_siempre(self, administrador):
        assert _conecta(administrador, "/ws/mapa/") is None
        assert _conecta(administrador, "/ws/chat/") is None
