"""HU-61 y HU-62 (CC-19): chat de trabajo. Hilo central, directos, grupos, privacidad (CP-53) y antispam."""

import pytest
from django.urls import reverse

from apps.auditoria.models import Auditoria
from apps.chat import views
from apps.chat.models import Conversacion, Mensaje, TipoConversacion
from apps.cuentas.tests.fabricas import UsuarioFactory
from apps.reservas.tests.fabricas import ConductorFactory

T = TipoConversacion
pytestmark = pytest.mark.django_db


@pytest.fixture
def chofer(empresa):
    return ConductorFactory(usuario__empresa=empresa, usuario__nombre="Pedro Soto")


@pytest.fixture
def chofer2(empresa):
    return ConductorFactory(usuario__empresa=empresa, usuario__nombre="Ana Rojas")


def despachador_de(empresa):
    return UsuarioFactory(empresa=empresa, rol="DESPACHADOR")


def como(cliente, usuario):
    cliente.force_authenticate(usuario)
    return cliente


def lista(cliente):
    respuesta = cliente.get(reverse("chat-conversaciones"))
    assert respuesta.status_code == 200, respuesta.data
    return respuesta.data


def escribir(cliente, conversacion_id, texto="Hola", **extra):
    return cliente.post(
        reverse("chat-mensajes", args=[conversacion_id]), {"texto": texto, **extra}, format="json"
    )


def mensajes(cliente, conversacion_id, **query):
    return cliente.get(reverse("chat-mensajes", args=[conversacion_id]), query)


def directo(cliente, otro):
    return cliente.post(reverse("chat-directos"), {"usuario": otro.pk}, format="json")


def grupo(cliente, nombre, *integrantes):
    respuesta = cliente.post(
        reverse("chat-grupos"),
        {"nombre": nombre, "ids_integrantes": [u.pk for u in integrantes]},
        format="json",
    )
    assert respuesta.status_code == 201, respuesta.data
    return respuesta.data["id"]


class TestCentral:
    def test_se_crea_uno_por_conductor_y_el_conductor_lo_ve_como_central(
        self, cliente, despachador, chofer, chofer2
    ):
        equipo = lista(como(cliente, despachador))
        assert sorted(c["titulo"] for c in equipo) == ["Ana Rojas", "Pedro Soto"]
        assert {c["tipo"] for c in equipo} == {T.CENTRAL}
        propio = lista(como(cliente, chofer.usuario))
        assert [(c["tipo"], c["titulo"]) for c in propio] == [(T.CENTRAL, "Central")]
        assert Conversacion.objects.filter(tipo=T.CENTRAL).count() == 2  # No se duplica al volver a listar.

    def test_conductor_inactivo_no_aparece_al_equipo(self, cliente, despachador, chofer):
        chofer.usuario.activo = False
        chofer.usuario.save()
        assert lista(como(cliente, despachador)) == []

    def test_el_equipo_responde_con_autor_y_el_conductor_ve_central(
        self, cliente, despachador, administrador, chofer
    ):
        central = lista(como(cliente, chofer.usuario))[0]["id"]
        assert escribir(cliente, central, "Llego tarde").status_code == 201
        assert escribir(como(cliente, despachador), central, "Ok, aviso al pasajero").status_code == 201
        del_equipo = mensajes(cliente, central).data["results"]
        assert [(m["autor"], m["propio"]) for m in del_equipo] == [
            ("Pedro Soto", False),
            (despachador.nombre, True),
        ]
        del_conductor = mensajes(como(cliente, chofer.usuario), central).data["results"]
        assert [m["autor"] for m in del_conductor] == ["Pedro Soto", "Central"]
        # Otro integrante del equipo también lo ve y tiene ambos sin leer.
        otro = next(c for c in lista(como(cliente, administrador)) if c["id"] == central)
        assert otro["no_leidos"] == 2
        assert otro["ultimo"]["autor"] == despachador.nombre

    def test_no_leidos_y_confirmacion_de_lectura(self, cliente, despachador, chofer):
        central = lista(como(cliente, despachador))[0]["id"]
        primero = escribir(cliente, central, "¿Dónde vas?").data["id"]
        assert mensajes(cliente, central).data["leido_por_otros_hasta"] == 0
        como(cliente, chofer.usuario)
        assert lista(cliente)[0]["no_leidos"] == 1
        assert cliente.post(reverse("chat-leido", args=[central]), {"hasta": primero + 99}).status_code == 204
        assert lista(cliente)[0]["no_leidos"] == 0
        assert mensajes(como(cliente, despachador), central).data["leido_por_otros_hasta"] == primero

    def test_respuesta_rapida_y_limites_del_texto(self, cliente, chofer):
        central = lista(como(cliente, chofer.usuario))[0]["id"]
        rapida = escribir(cliente, central, "", rapida="LLEGUE")
        assert (rapida.status_code, rapida.data["texto"], rapida.data["rapida"]) == (201, "Llegué", "LLEGUE")
        assert escribir(cliente, central, "   ").status_code == 400
        assert escribir(cliente, central, "x" * 1001).status_code == 400
        assert escribir(cliente, central, "x" * 1000).status_code == 201

    def test_historial_paginado(self, cliente, despachador, chofer):
        central = lista(como(cliente, despachador))[0]["id"]
        conversacion = Conversacion.objects.get(pk=central)
        Mensaje.objects.bulk_create(
            [Mensaje(conversacion=conversacion, autor=despachador, texto=f"m{i}") for i in range(35)]
        )
        pagina = mensajes(cliente, central).data
        assert (len(pagina["results"]), pagina["hay_mas"]) == (30, True)
        assert pagina["results"][-1]["texto"] == "m34"
        anterior = mensajes(cliente, central, antes=pagina["results"][0]["id"]).data
        assert ([m["texto"] for m in anterior["results"]], anterior["hay_mas"]) == (
            [f"m{i}" for i in range(5)],
            False,
        )
        assert mensajes(cliente, central, antes="x").status_code == 400

    def test_antispam_por_usuario(self, cliente, chofer, monkeypatch):
        monkeypatch.setattr(views.AntispamChat, "THROTTLE_RATES", {"chat": "2/min"})
        central = lista(como(cliente, chofer.usuario))[0]["id"]
        assert [escribir(cliente, central).status_code for _ in range(3)] == [201, 201, 429]
        assert mensajes(cliente, central).status_code == 200  # Leer no cuenta.


class TestDirectos:
    def test_entre_conductores_y_sin_duplicar(self, cliente, chofer, chofer2):
        como(cliente, chofer.usuario)
        creado = directo(cliente, chofer2.usuario)
        assert (creado.status_code, creado.data["titulo"]) == (201, "Ana Rojas")
        existente = directo(como(cliente, chofer2.usuario), chofer.usuario)
        assert (existente.status_code, existente.data["id"], existente.data["titulo"]) == (
            200,
            creado.data["id"],
            "Pedro Soto",
        )

    def test_personal_de_la_empresa_sin_pasajeros_ni_otras_empresas(
        self, cliente, despachador, chofer, otra_empresa
    ):
        UsuarioFactory(empresa=despachador.empresa, rol="PASAJERO")
        ajeno = UsuarioFactory(empresa=otra_empresa, rol="DESPACHADOR")
        personal = como(cliente, chofer.usuario).get(reverse("chat-personal")).data
        assert [p["id"] for p in personal] == [despachador.pk]
        assert directo(cliente, ajeno).status_code == 404
        assert directo(cliente, chofer.usuario).status_code == 404  # Consigo mismo no.


class TestPrivacidad:
    """CP-53: el administrador no lee directos ni grupos ajenos; modera solo con metadatos."""

    def test_administrador_no_lee_directos_ni_grupos_ajenos(
        self, cliente, administrador, despachador, chofer
    ):
        conversacion = directo(como(cliente, despachador), chofer.usuario).data["id"]
        escribir(cliente, conversacion, "Privado")
        id_grupo = grupo(cliente, "Turno noche", chofer.usuario)
        escribir(cliente, id_grupo, "También privado")
        como(cliente, administrador)
        visibles = {c["id"] for c in lista(cliente)}
        assert conversacion not in visibles and id_grupo not in visibles
        for pk in (conversacion, id_grupo):
            assert mensajes(cliente, pk).status_code == 404
            assert escribir(cliente, pk).status_code == 404
            assert cliente.get(reverse("chat-conversacion", args=[pk])).status_code == 404
            assert cliente.post(reverse("chat-leido", args=[pk]), {"hasta": 1}).status_code == 404
        moderacion = cliente.get(reverse("chat-moderacion")).data
        assert [g["nombre"] for g in moderacion] == ["Turno noche"]
        assert set(moderacion[0]) == {
            "id",
            "nombre",
            "integrantes",
            "creado_por",
            "creado_en",
            "ultimo_mensaje_en",
        }
        assert "privado" not in str(moderacion).lower()

    @pytest.mark.parametrize("rol", ["DESPACHADOR", "CONDUCTOR"])
    def test_moderacion_solo_administrador(self, cliente, empresa, rol):
        assert (
            como(cliente, UsuarioFactory(empresa=empresa, rol=rol))
            .get(reverse("chat-moderacion"))
            .status_code
            == 403
        )

    def test_clientes_finales_fuera_del_chat_de_trabajo(self, cliente, empresa, chofer):
        lista(como(cliente, despachador_de(empresa)))  # crea el hilo central del conductor
        como(cliente, UsuarioFactory(empresa=empresa, rol="CONVENIO"))
        assert cliente.get(reverse("chat-conversaciones")).status_code == 403
        # HU-66: el pasajero con módulo entra al chat, pero solo a sus viajes y su soporte.
        como(cliente, UsuarioFactory(empresa=empresa, rol="PASAJERO"))
        assert lista(cliente) == []
        assert cliente.get(reverse("chat-personal")).status_code == 403
        assert (
            cliente.post(reverse("chat-directos"), {"usuario": chofer.usuario.pk}, format="json").status_code
            == 403
        )

    def test_otra_empresa_no_existe(self, cliente, chofer, otra_empresa):
        central = lista(como(cliente, chofer.usuario))[0]["id"]
        ajeno = UsuarioFactory(empresa=otra_empresa, rol="ADMINISTRADOR")
        como(cliente, ajeno)
        assert lista(cliente) == []
        assert mensajes(cliente, central).status_code == 404

    def test_conductor_no_lee_el_central_de_otro(self, cliente, chofer, chofer2):
        ajeno = lista(como(cliente, chofer2.usuario))[0]["id"]
        assert mensajes(como(cliente, chofer.usuario), ajeno).status_code == 404


class TestGrupos:
    def test_integrantes_gestionan_y_el_administrador_modera_con_auditoria(
        self, cliente, administrador, despachador, chofer, chofer2
    ):
        id_grupo = grupo(como(cliente, chofer.usuario), "Aeropuerto", chofer2.usuario)
        como(cliente, chofer2.usuario)
        assert (
            cliente.patch(reverse("chat-grupo", args=[id_grupo]), {"nombre": "Aeropuerto SCL"}).status_code
            == 200
        )
        agregado = cliente.post(reverse("chat-integrantes", args=[id_grupo]), {"usuario": despachador.pk})
        assert [i["nombre"] for i in agregado.data["integrantes"]] == sorted(
            [chofer.usuario.nombre, chofer2.usuario.nombre, despachador.nombre]
        )
        assert not Auditoria.objects.exists()  # Los integrantes no dejan auditoría al gestionar.
        # Quitar a otro: solo quien lo creó o el administrador.
        quitar = reverse("chat-integrante", args=[id_grupo, despachador.pk])
        assert cliente.delete(quitar).status_code == 403
        como(cliente, administrador)
        assert (
            cliente.post(
                reverse("chat-integrantes", args=[id_grupo]), {"usuario": administrador.pk}
            ).status_code
            == 403
        )
        assert (
            cliente.patch(reverse("chat-grupo", args=[id_grupo]), {"nombre": "Moderado"}).status_code == 200
        )
        assert cliente.delete(quitar).status_code == 204
        acciones = list(Auditoria.objects.order_by("pk").values_list("accion", "usuario", "entidad"))
        assert acciones == [
            ("MODERAR_RENOMBRAR_GRUPO", administrador.pk, "CONVERSACION"),
            ("MODERAR_QUITAR_INTEGRANTE", administrador.pk, "CONVERSACION"),
        ]
        assert mensajes(cliente, id_grupo).status_code == 404  # Moderar no da lectura.

    def test_borrar_solo_creador_o_administrador(self, cliente, administrador, chofer, chofer2, despachador):
        id_grupo = grupo(como(cliente, chofer.usuario), "Noche", chofer2.usuario)
        assert (
            como(cliente, chofer2.usuario).delete(reverse("chat-grupo", args=[id_grupo])).status_code == 403
        )
        assert como(cliente, chofer.usuario).delete(reverse("chat-grupo", args=[id_grupo])).status_code == 204
        assert id_grupo not in {c["id"] for c in lista(cliente)}
        assert mensajes(cliente, id_grupo).status_code == 404
        otro = grupo(como(cliente, despachador), "Día", chofer.usuario)
        assert como(cliente, administrador).delete(reverse("chat-grupo", args=[otro])).status_code == 204
        assert list(Auditoria.objects.order_by("pk").values_list("accion", "usuario")) == [
            ("BORRAR_GRUPO", chofer.usuario.pk),
            ("MODERAR_BORRAR_GRUPO", administrador.pk),
        ]
        assert como(cliente, administrador).get(reverse("chat-moderacion")).data == []

    def test_salir_del_grupo_y_validaciones(self, cliente, empresa, chofer, chofer2, otra_empresa):
        como(cliente, chofer.usuario)
        assert (
            cliente.post(
                reverse("chat-grupos"),
                {"nombre": " ", "ids_integrantes": [chofer2.usuario.pk]},
                format="json",
            ).status_code
            == 400
        )
        assert (
            cliente.post(
                reverse("chat-grupos"),
                {"nombre": "Solo", "ids_integrantes": [chofer.usuario.pk]},
                format="json",
            ).status_code
            == 400
        )
        ajeno = UsuarioFactory(empresa=otra_empresa, rol="CONDUCTOR")
        assert (
            cliente.post(
                reverse("chat-grupos"), {"nombre": "X", "ids_integrantes": [ajeno.pk]}, format="json"
            ).status_code
            == 400
        )
        id_grupo = grupo(cliente, "Ruta costa", chofer2.usuario)
        como(cliente, chofer2.usuario)
        assert (
            cliente.delete(reverse("chat-integrante", args=[id_grupo, chofer2.usuario.pk])).status_code == 204
        )
        assert mensajes(cliente, id_grupo).status_code == 404
        assert cliente.get(reverse("chat-grupo", args=[id_grupo])).status_code == 404
