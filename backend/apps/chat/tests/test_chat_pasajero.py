"""HU-66 (CC-19): chat conductor ↔ pasajero (CP-54), lectura auditada (CP-55), soporte y emergencia."""

# Las fixtures `activa` y `sin_whatsapp` vienen de las pruebas de HU-65 y se usan como parámetros.
# ruff: noqa: F811

import pytest
from django.urls import reverse

from apps.auditoria.models import Auditoria
from apps.chat import permisos
from apps.chat.models import Conversacion
from apps.cuentas.tests.fabricas import UsuarioFactory
from apps.reservas.models import CuentaPasajero, EstadoViaje, Viaje
from apps.reservas.tests.conftest import sin_whatsapp  # noqa: F401 (fixture)
from apps.reservas.tests.fabricas import ConductorFactory, ViajeFactory
from apps.reservas.tests.test_avisos_pasajero import activa, pedir  # noqa: F401 (fixtures)

E = EstadoViaje
pytestmark = pytest.mark.django_db


@pytest.fixture
def chofer(empresa):
    return ConductorFactory(usuario__empresa=empresa, usuario__nombre="Pedro Soto")


@pytest.fixture
def viaje(activa, chofer):
    """Un viaje pedido por la cuenta y aceptado por el conductor."""
    viaje = pedir(activa)
    Viaje.objects.filter(pk=viaje.pk).update(conductor=chofer, estado=E.ACEPTADO)
    viaje.refresh_from_db()
    return viaje


def abrir(cliente, viaje):
    return cliente.post(reverse("chat-viaje", args=[viaje.pk]))


def escribir(cliente, conversacion_id, texto="Hola", **extra):
    return cliente.post(
        reverse("chat-mensajes", args=[conversacion_id]), {"texto": texto, **extra}, format="json"
    )


class TestVentanaDelViaje:
    """CP-54: conductor y pasajero se escriben de ACEPTADO a PASAJERO_A_BORDO; después, solo lectura."""

    def test_se_escriben_mientras_el_viaje_esta_en_curso(self, activa, cliente, chofer, viaje):
        cliente.force_authenticate(chofer.usuario)
        del_conductor = abrir(cliente, viaje)
        assert del_conductor.status_code == 200, del_conductor.data
        # El conductor ve solo el nombre del pasajero.
        assert (del_conductor.data["tipo"], del_conductor.data["titulo"]) == ("VIAJE", "Paula Pasajera")
        del_pasajero = abrir(activa, viaje)
        assert (del_pasajero.data["id"], del_pasajero.data["titulo"]) == (
            del_conductor.data["id"],
            "Pedro Soto",
        )
        conversacion = del_conductor.data["id"]
        assert escribir(cliente, conversacion, "Voy en camino").status_code == 201
        assert escribir(activa, conversacion, "Estoy en la puerta 3").status_code == 201
        textos = [
            m["texto"] for m in activa.get(reverse("chat-mensajes", args=[conversacion])).data["results"]
        ]
        assert textos == ["Voy en camino", "Estoy en la puerta 3"]
        assert [c["id"] for c in activa.get(reverse("chat-conversaciones")).data] == [conversacion]
        assert sorted(permisos.destinatarios(Conversacion.objects.get(pk=conversacion))) == sorted(
            [chofer.usuario_id, CuentaPasajero.objects.get().usuario_id]
        )

    @pytest.mark.parametrize("estado", [E.FINALIZADO, E.CANCELADO])
    def test_al_terminar_queda_en_solo_lectura(self, activa, cliente, chofer, viaje, estado):
        conversacion = abrir(activa, viaje).data["id"]
        escribir(activa, conversacion, "Gracias")
        Viaje.objects.filter(pk=viaje.pk).update(estado=estado, motivo_cancelacion="x")
        for quien in (activa, cliente):
            if quien is cliente:
                cliente.force_authenticate(chofer.usuario)
            respuesta = escribir(quien, conversacion, "¿Sigues ahí?")
            assert (respuesta.status_code, respuesta.data["code"]) == (403, "solo_lectura")
            assert quien.get(reverse("chat-mensajes", args=[conversacion])).status_code == 200
            assert abrir(quien, viaje).data["puede_escribir"] is False

    def test_antes_de_aceptar_no_hay_chat(self, activa, cliente, chofer, viaje):
        Viaje.objects.filter(pk=viaje.pk).update(estado=E.ASIGNADO)
        assert abrir(activa, viaje).status_code == 404
        cliente.force_authenticate(chofer.usuario)
        assert abrir(cliente, viaje).status_code == 404

    def test_otro_conductor_u_otro_pasajero_no_entran(self, activa, cliente, empresa, viaje):
        cliente.force_authenticate(ConductorFactory(usuario__empresa=empresa).usuario)
        assert abrir(cliente, viaje).status_code == 404
        cliente.force_authenticate(UsuarioFactory(empresa=empresa, rol="PASAJERO"))
        assert abrir(cliente, viaje).status_code == 404
        conversacion = abrir(activa, viaje).data["id"]
        assert cliente.get(reverse("chat-mensajes", args=[conversacion])).status_code == 404

    def test_sin_cuenta_del_pasajero_no_hay_chat(self, cliente, empresa, chofer):
        invitado = ViajeFactory(empresa=empresa, conductor=chofer, estado=E.ACEPTADO)
        cliente.force_authenticate(chofer.usuario)
        respuesta = abrir(cliente, invitado)
        assert (respuesta.status_code, respuesta.data["code"]) == (404, "sin_cuenta")


class TestLecturaDeLaCentral:
    """CP-55: la central lee el chat del viaje en solo lectura y cada lectura queda en auditoría."""

    def test_lectura_auditada_y_sin_escribir(self, activa, cliente, despachador, viaje):
        conversacion = abrir(activa, viaje).data["id"]
        escribir(activa, conversacion, "Estoy en la puerta 3")
        cliente.force_authenticate(despachador)
        assert conversacion not in [c["id"] for c in cliente.get(reverse("chat-conversaciones")).data]
        assert cliente.get(reverse("chat-mensajes", args=[conversacion])).status_code == 404
        assert escribir(cliente, conversacion).status_code == 404
        for _ in range(2):
            lectura = cliente.get(reverse("chat-viaje-lectura", args=[viaje.pk]))
            assert [(m["autor"], m["texto"]) for m in lectura.data["results"]] == [
                ("Paula Pasajera", "Estoy en la puerta 3")
            ]
        registros = Auditoria.objects.filter(accion="LEER_CHAT_VIAJE", entidad="VIAJE", entidad_id=viaje.pk)
        assert list(registros.values_list("usuario", flat=True)) == [despachador.pk, despachador.pk]

    def test_sin_chat_no_audita(self, cliente, despachador, viaje):
        cliente.force_authenticate(despachador)
        assert cliente.get(reverse("chat-viaje-lectura", args=[viaje.pk])).data["results"] == []
        assert not Auditoria.objects.filter(accion="LEER_CHAT_VIAJE").exists()

    def test_solo_el_equipo_de_la_empresa(self, cliente, chofer, otra_empresa, viaje):
        cliente.force_authenticate(chofer.usuario)
        assert cliente.get(reverse("chat-viaje-lectura", args=[viaje.pk])).status_code == 403
        cliente.force_authenticate(UsuarioFactory(empresa=otra_empresa, rol="DESPACHADOR"))
        assert cliente.get(reverse("chat-viaje-lectura", args=[viaje.pk])).status_code == 404


class TestSoporte:
    def test_el_pasajero_escribe_y_el_equipo_responde_como_central(self, activa, cliente, despachador, viaje):
        soporte = activa.post(reverse("chat-soporte"))
        assert (soporte.status_code, soporte.data["titulo"]) == (200, "Soporte")
        conversacion = soporte.data["id"]
        assert activa.post(reverse("chat-soporte")).data["id"] == conversacion  # uno por cuenta
        con_viaje = escribir(activa, conversacion, "Olvidé mi paraguas", viaje=viaje.pk)
        assert con_viaje.data["texto"] == f"[Viaje N.º {viaje.pk}] Olvidé mi paraguas"
        cliente.force_authenticate(despachador)
        fila = next(c for c in cliente.get(reverse("chat-conversaciones")).data if c["id"] == conversacion)
        assert fila["titulo"] == "Soporte · Paula Pasajera"
        assert escribir(cliente, conversacion, "Lo buscamos").status_code == 201
        autores = [
            m["autor"] for m in activa.get(reverse("chat-mensajes", args=[conversacion])).data["results"]
        ]
        assert autores == ["Paula Pasajera", "Central"]

    def test_viaje_ajeno_y_pasajero_sin_modulo(self, activa, cliente, empresa, otra_empresa):
        conversacion = activa.post(reverse("chat-soporte")).data["id"]
        ajeno = ViajeFactory(empresa=empresa)
        respuesta = escribir(activa, conversacion, "x", viaje=ajeno.pk)
        assert respuesta.status_code == 400
        otra_empresa.modulo_cuentas = False
        otra_empresa.save()
        cliente.force_authenticate(UsuarioFactory(empresa=otra_empresa, rol="PASAJERO"))
        assert cliente.post(reverse("chat-soporte")).status_code == 403
        cliente.force_authenticate(UsuarioFactory(empresa=empresa, rol="DESPACHADOR"))
        assert cliente.post(reverse("chat-soporte")).status_code == 403


def test_numeros_de_emergencia_en_mi_cuenta(activa, empresa):
    configuracion = empresa.configuracion
    assert activa.get(reverse("mi-cuenta")).data["central"] == {"telefono": None, "whatsapp": None}
    configuracion.telefono_central, configuracion.whatsapp_central = "+56229990000", "+56999900000"
    configuracion.save()
    assert activa.get(reverse("mi-cuenta")).data["central"] == {
        "telefono": "+56229990000",
        "whatsapp": "+56999900000",
    }
