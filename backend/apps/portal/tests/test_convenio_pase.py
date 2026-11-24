# ruff: noqa: F811 (las fixtures compartidas se importan de test_clave_convenio)
"""CC-23 (HU-73): reservas de convenio con el pase en el portal base. CP-60 a CP-62.

La clave se lee del correo solo dentro de la prueba y nunca se imprime: los mensajes de las aserciones no la
incluyen.
"""

import re
from datetime import timedelta
from unittest import mock

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.convenios import servicios as convenios
from apps.convenios.models import Convenio
from apps.cuentas.tests.fabricas import EmpresaFactory, UsuarioFactory
from apps.reservas import expiracion
from apps.reservas.models import EstadoViaje, OrigenCancelacion, Pasajero, Viaje

from .test_clave_convenio import (  # noqa: F401 (fixtures)
    CONTACTO,
    admin_base,
    aprobado,
    base,
    correos_a,
    pase,
    pedir_pase,
)
from .test_reserva_publica import datos as datos_reserva

E = EstadoViaje


def reservar(cliente, empresa, capturar, pase, **cambios):
    cuerpo = datos_reserva(
        nombre="Ana Solicitante", correo="ana@minera.example", telefono="+56900009501", pase=pase
    )
    cuerpo.update(cambios)
    with capturar(execute=True):
        return cliente.post(reverse("portal-reserva-publica", args=[empresa.slug]), cuerpo, format="json")


def otra_persona(**cambios):
    d = {
        "para": "OTRO",
        "pasajero_nombre": "Pedro Gerente",
        "pasajero_cargo": "Gerente comercial",
        "pasajero_telefono": "+56900009502",
        "declara_informados": True,
    }
    d.update(cambios)
    return d


def acompanante(n, telefono=True, correo=""):
    return {
        "nombre": f"Acompañante {n}",
        "cargo": "Analista",
        "telefono": f"+5690000960{n}" if telefono else "",
        "correo": correo,
    }


def token_de_confirmacion() -> str:
    cuerpo = correos_a("ana@minera.example")[-1].body
    return re.search(r"/confirmar/(\S+)", cuerpo).group(1)


@pytest.mark.django_db
class TestPaseEnLaReserva:
    """CP-59 en la reserva: un pase vencido o invalidado vuelve a la clave (401)."""

    def test_pase_vencido(self, cliente, base, pase, django_capture_on_commit_callbacks):
        despues = timezone.now().timestamp() + 121 * 60
        with mock.patch("django.core.signing.time.time", return_value=despues):
            respuesta = reservar(cliente, base, django_capture_on_commit_callbacks, pase)
        assert (respuesta.status_code, respuesta.data["code"]) == (401, "pase_vencido")

    @pytest.mark.parametrize("accion", ["regenerar", "revocar", "desactivar", "correo"])
    def test_pase_invalidado(
        self, cliente, base, admin_base, aprobado, pase, accion, django_capture_on_commit_callbacks
    ):
        convenio, _ = aprobado
        if accion == "regenerar":
            convenios.regenerar_clave(convenio, usuario=admin_base)
        elif accion == "revocar":
            convenios.revocar_clave(convenio, usuario=admin_base)
        elif accion == "desactivar":
            convenios.desactivar(convenio, usuario=admin_base)
        else:  # el correo dejó de estar autorizado
            Convenio.objects.filter(pk=convenio.pk).update(correos_autorizados=[])
        respuesta = reservar(cliente, base, django_capture_on_commit_callbacks, pase)
        assert (respuesta.status_code, respuesta.data["code"]) == (401, "pase_invalido")
        assert not Viaje.objects.exists()

    def test_pase_de_otra_empresa_no_sirve(self, cliente, pase, django_capture_on_commit_callbacks):
        # RN-13: la firma es válida, pero el convenio no es de esta empresa.
        otra = EmpresaFactory(modulo_cuentas=False)
        respuesta = reservar(cliente, otra, django_capture_on_commit_callbacks, pase)
        assert (respuesta.status_code, respuesta.data["code"]) == (401, "pase_invalido")

    def test_pase_adulterado(self, cliente, base, pase, django_capture_on_commit_callbacks):
        respuesta = reservar(cliente, base, django_capture_on_commit_callbacks, pase + "x")
        assert respuesta.data["code"] == "pase_invalido"


@pytest.mark.django_db
class TestReservaConPase:
    """CP-60: para mí y para otra persona, a nombre del solicitante (D7), con sus avisos."""

    def test_para_mi(self, cliente, base, aprobado, pase, django_capture_on_commit_callbacks):
        convenio, clave = aprobado
        respuesta = reservar(
            cliente, base, django_capture_on_commit_callbacks, pase, correo="otro@correo.example"
        )
        assert respuesta.status_code == 201, respuesta.data
        assert respuesta.data["viajes"] == 1
        viaje = Viaje.objects.get()
        assert (viaje.convenio, viaje.canal, viaje.estado, viaje.confirma_convenio) == (
            convenio,
            "CONVENIO",
            E.PENDIENTE_CONFIRMACION,
            False,
        )
        # El correo del pase manda, no el del formulario.
        assert viaje.contacto_correo == "ana@minera.example"
        assert (viaje.solicitante_nombre, viaje.pasajero.nombre) == ("Ana Solicitante", "Ana Solicitante")
        assert viaje.confirmar_hasta == viaje.recogida_en - timedelta(hours=24)
        assert viaje.empresa_cliente_rut is None and viaje.terceros_informados_en is None
        assert Pasajero.objects.get().privacidad_aceptada_en is not None
        confirmacion = correos_a("ana@minera.example")
        assert len(confirmacion) == 1 and "/confirmar/" in confirmacion[0].body
        # Quien pide no es el contacto: el contacto recibe un aviso sin enlace.
        aviso = correos_a(CONTACTO)
        assert len(aviso) == 1 and "/confirmar/" not in aviso[0].body
        assert all(clave not in m.body for m in mail.outbox)

    def test_si_pide_el_contacto_no_recibe_aviso_aparte(
        self, cliente, base, aprobado, django_capture_on_commit_callbacks
    ):
        _, clave = aprobado
        pase = pedir_pase(cliente, base, CONTACTO, clave).data["pase"]
        reservar(cliente, base, django_capture_on_commit_callbacks, pase)
        assert len(correos_a(CONTACTO)) == 1 and "/confirmar/" in correos_a(CONTACTO)[0].body

    def test_para_otra_persona(self, cliente, base, pase, django_capture_on_commit_callbacks):
        respuesta = reservar(
            cliente,
            base,
            django_capture_on_commit_callbacks,
            pase,
            **otra_persona(pasajero_correo="Pedro@Correo.example"),
        )
        assert respuesta.status_code == 201, respuesta.data
        viaje = Viaje.objects.get()
        assert (viaje.pasajero.nombre, viaje.pasajero.telefono) == ("Pedro Gerente", "+56900009502")
        assert (viaje.solicitante_nombre, viaje.solicitante_telefono) == ("Ana Solicitante", "+56900009501")
        assert (viaje.pasajero_cargo, viaje.pasajero_correo) == ("Gerente comercial", "pedro@correo.example")
        assert viaje.terceros_informados_en is not None
        assert viaje.pasajero.privacidad_aceptada_en is None  # solo lo declaró quien pidió
        informativo = correos_a("pedro@correo.example")
        assert len(informativo) == 1 and "/confirmar/" not in informativo[0].body
        assert len(correos_a("ana@minera.example")) == 1  # la confirmación va solo a quien pide

    def test_sin_correo_del_pasajero_no_hay_aviso_informativo(
        self, cliente, base, pase, django_capture_on_commit_callbacks
    ):
        reservar(cliente, base, django_capture_on_commit_callbacks, pase, **otra_persona())
        assert {tuple(m.to) for m in mail.outbox} == {("ana@minera.example",), (CONTACTO,)}

    @pytest.mark.parametrize(
        ("cambios", "campo"),
        [
            ({"pasajero_telefono": ""}, "pasajero_telefono"),
            ({"pasajero_cargo": " "}, "pasajero_cargo"),
            ({"pasajero_nombre": ""}, "pasajero_nombre"),
            ({"declara_informados": False}, "declara_informados"),
        ],
    )
    def test_otra_persona_datos_obligatorios(
        self, cliente, base, pase, cambios, campo, django_capture_on_commit_callbacks
    ):
        respuesta = reservar(
            cliente, base, django_capture_on_commit_callbacks, pase, **otra_persona(**cambios)
        )
        assert respuesta.status_code == 400 and campo in respuesta.data

    def test_con_pase_no_van_rut_ni_razon_social(
        self, cliente, base, pase, django_capture_on_commit_callbacks
    ):
        respuesta = reservar(
            cliente, base, django_capture_on_commit_callbacks, pase, es_empresa=True, empresa_rut="76543210-3"
        )
        assert respuesta.status_code == 400 and "es_empresa" in respuesta.data

    def test_con_modulo_el_pase_no_sirve(self, cliente, pase, django_capture_on_commit_callbacks):
        empresa = EmpresaFactory(modulo_cuentas=True)
        assert reservar(cliente, empresa, django_capture_on_commit_callbacks, pase).status_code == 404


@pytest.mark.django_db
class TestVehiculos:
    """CP-61: mismo vehículo (capacidad, DC-43) o vehículos separados con `grupo` y un solo enlace (D6)."""

    def test_mismo_vehiculo_con_acompanantes(self, cliente, base, pase, django_capture_on_commit_callbacks):
        respuesta = reservar(
            cliente,
            base,
            django_capture_on_commit_callbacks,
            pase,
            declara_informados=True,
            acompanantes=[acompanante(1, telefono=False), acompanante(2, correo="dos@correo.example")],
        )
        assert respuesta.status_code == 201, respuesta.data
        viaje = Viaje.objects.get()
        assert (viaje.pasajeros, viaje.grupo) == (3, None)
        assert [a["nombre"] for a in viaje.acompanantes] == ["Acompañante 1", "Acompañante 2"]
        assert viaje.acompanantes[0]["telefono"] == ""  # opcional en el mismo vehículo
        assert len(correos_a("dos@correo.example")) == 1

    def test_mismo_vehiculo_sobre_la_capacidad(self, cliente, base, pase, django_capture_on_commit_callbacks):
        # Sin vehículos la capacidad es 4 (DC-43): 1 + 4 acompañantes no caben.
        respuesta = reservar(
            cliente,
            base,
            django_capture_on_commit_callbacks,
            pase,
            declara_informados=True,
            acompanantes=[acompanante(n) for n in range(1, 5)],
        )
        assert respuesta.status_code == 400
        assert "Vehículos separados" in str(respuesta.data["acompanantes"])
        assert not Viaje.objects.exists()

    def test_acompanantes_exigen_la_declaracion(
        self, cliente, base, pase, django_capture_on_commit_callbacks
    ):
        respuesta = reservar(
            cliente, base, django_capture_on_commit_callbacks, pase, acompanantes=[acompanante(1)]
        )
        assert respuesta.status_code == 400 and "declara_informados" in respuesta.data

    def test_separados_exige_telefono_por_persona(
        self, cliente, base, pase, django_capture_on_commit_callbacks
    ):
        respuesta = reservar(
            cliente,
            base,
            django_capture_on_commit_callbacks,
            pase,
            vehiculos="SEPARADOS",
            declara_informados=True,
            acompanantes=[acompanante(1), acompanante(2, telefono=False)],
        )
        assert respuesta.status_code == 400
        assert respuesta.data["acompanantes"][1]["telefono"]

    def separados(self, cliente, base, pase, capturar, n=2, **cambios):
        return reservar(
            cliente,
            base,
            capturar,
            pase,
            vehiculos="SEPARADOS",
            declara_informados=True,
            acompanantes=[acompanante(i) for i in range(1, n + 1)],
            **cambios,
        )

    def test_separados_crea_un_viaje_por_persona(
        self, cliente, base, aprobado, pase, django_capture_on_commit_callbacks
    ):
        convenio, _ = aprobado
        respuesta = self.separados(cliente, base, pase, django_capture_on_commit_callbacks)
        assert respuesta.status_code == 201, respuesta.data
        assert respuesta.data["viajes"] == 3
        viajes = list(Viaje.objects.order_by("pk"))
        assert len(viajes) == 3 and len({v.grupo for v in viajes}) == 1 and viajes[0].grupo
        assert [v.pasajero.nombre for v in viajes] == ["Ana Solicitante", "Acompañante 1", "Acompañante 2"]
        assert {v.solicitante_nombre for v in viajes} == {"Ana Solicitante"}
        assert {(v.pasajeros, v.convenio_id, v.recogida_en) for v in viajes} == {
            (1, convenio.pk, viajes[0].recogida_en)
        }
        assert all(v.acompanantes == [] for v in viajes)
        assert len(correos_a("ana@minera.example")) == 1  # un solo correo con un solo enlace

    def test_separados_es_atomico(self, cliente, base, pase, django_capture_on_commit_callbacks):
        from apps.reservas import servicios as reservas

        original = reservas.crear_viaje
        llamadas = []

        def falla_al_tercero(**kwargs):
            llamadas.append(1)
            if len(llamadas) == 3:
                raise RuntimeError("falla simulada")
            return original(**kwargs)

        with (
            mock.patch.object(reservas, "crear_viaje", side_effect=falla_al_tercero),
            pytest.raises(RuntimeError),
        ):
            self.separados(cliente, base, pase, django_capture_on_commit_callbacks)
        assert not Viaje.objects.exists() and not mail.outbox

    def test_tope_de_personas_por_solicitud(self, cliente, base, pase, django_capture_on_commit_callbacks):
        base.configuracion.convenio_max_personas = 2
        base.configuracion.save()
        respuesta = self.separados(cliente, base, pase, django_capture_on_commit_callbacks)
        assert respuesta.status_code == 400 and "2 personas" in str(respuesta.data["acompanantes"])

    def test_un_enlace_confirma_todo_el_grupo_menos_los_cancelados(
        self, cliente, base, pase, django_capture_on_commit_callbacks
    ):
        from apps.reservas import estados

        from .test_reserva_publica import confirmar

        self.separados(cliente, base, pase, django_capture_on_commit_callbacks)
        _, _, tercero = Viaje.objects.order_by("pk")
        estados.transicionar(
            tercero, E.CANCELADO, desde=E.PENDIENTE_CONFIRMACION, actor="SISTEMA", motivo_cancelacion="Prueba"
        )
        respuesta = confirmar(cliente, base, token_de_confirmacion())
        assert respuesta.status_code == 200, respuesta.data
        estados_finales = list(Viaje.objects.order_by("pk").values_list("estado", flat=True))
        assert estados_finales == [E.SOLICITADO, E.SOLICITADO, E.CANCELADO]
        assert confirmar(cliente, base, token_de_confirmacion()).status_code == 409  # una sola vez

    def test_el_limite_por_correo_cuenta_solicitudes(
        self, cliente, base, pase, django_capture_on_commit_callbacks
    ):
        base.configuracion.reserva_publica_max_convenio_hora = 2
        base.configuracion.save()
        assert self.separados(cliente, base, pase, django_capture_on_commit_callbacks).status_code == 201
        assert reservar(cliente, base, django_capture_on_commit_callbacks, pase).status_code == 201
        tercera = reservar(cliente, base, django_capture_on_commit_callbacks, pase)
        assert (tercera.status_code, tercera.data["code"]) == (429, "limite_correo")


@pytest.mark.django_db
class TestPlazosYCierre:
    """CP-62: el plazo de DC-53 (24 h o 60 min), «Sin confirmar» y cierre NO_CONFIRMADA (DC-59)."""

    def test_con_menos_de_un_dia_el_plazo_es_de_60_min(
        self, cliente, base, pase, django_capture_on_commit_callbacks
    ):
        antes = timezone.now()
        recogida = (antes + timedelta(hours=5)).isoformat()
        reservar(cliente, base, django_capture_on_commit_callbacks, pase, recogida_en=recogida)
        plazo = Viaje.objects.get().confirmar_hasta - antes
        assert timedelta(minutes=59) < plazo < timedelta(minutes=61)

    def test_enlace_vencido_del_grupo(self, cliente, base, pase, django_capture_on_commit_callbacks):
        from .test_reserva_publica import confirmar

        TestVehiculos().separados(cliente, base, pase, django_capture_on_commit_callbacks, n=1)
        Viaje.objects.update(confirmar_hasta=timezone.now() - timedelta(minutes=1))
        assert confirmar(cliente, base, token_de_confirmacion()).status_code == 410

    def test_sin_confirmar_se_cierran_todos_como_no_confirmada(
        self, cliente, base, pase, django_capture_on_commit_callbacks
    ):
        TestVehiculos().separados(cliente, base, pase, django_capture_on_commit_callbacks, n=1)
        viajes = Viaje.objects.all()
        assert all(expiracion.es_sin_confirmar(v, ahora=v.confirmar_hasta) for v in viajes)
        despues = viajes[0].recogida_en + timedelta(hours=3)
        assert expiracion.cerrar_no_confirmadas(ahora=despues) == 2
        assert set(Viaje.objects.values_list("estado", "origen_cancelacion")) == {
            (E.CANCELADO, OrigenCancelacion.NO_CONFIRMADA)
        }


@pytest.mark.django_db
class TestPanelYApp:
    """CP-62: el panel ve al solicitante y los acompañantes; la app del conductor, solo los nombres."""

    def test_el_panel_muestra_solicitante_y_acompanantes(
        self, cliente, panel, base, pase, django_capture_on_commit_callbacks
    ):
        reservar(
            cliente,
            base,
            django_capture_on_commit_callbacks,
            pase,
            acompanantes=[acompanante(1)],
            **otra_persona(),
        )
        panel.force_authenticate(UsuarioFactory(empresa=base, rol="DESPACHADOR"))
        viaje = Viaje.objects.get()
        datos = panel.get(reverse("viaje-detail", args=[viaje.pk])).data
        assert (datos["solicitante_nombre"], datos["pasajero_cargo"]) == (
            "Ana Solicitante",
            "Gerente comercial",
        )
        assert datos["acompanantes"][0]["nombre"] == "Acompañante 1"

    def test_la_app_ve_solo_los_nombres(self, cliente, base, pase, django_capture_on_commit_callbacks):
        from apps.reservas.tests.fabricas import ConductorFactory

        reservar(
            cliente,
            base,
            django_capture_on_commit_callbacks,
            pase,
            acompanantes=[acompanante(1)],
            **otra_persona(),
        )
        chofer = ConductorFactory(usuario__empresa=base)
        Viaje.objects.update(conductor=chofer, estado=E.ACEPTADO)
        cliente.force_authenticate(chofer.usuario)
        respuesta = cliente.get(reverse("app-viaje-activo"))
        datos = respuesta.json()["viaje"]
        assert (datos["pasajero"], datos["acompanantes"]) == ("Pedro Gerente", ["Acompañante 1"])
        cuerpo = respuesta.content.decode()
        for oculto in ("+56900009502", "+56900009601", "Gerente comercial", "Analista", "telefono", "cargo"):
            assert oculto not in cuerpo


@pytest.mark.django_db
def test_el_panel_filtra_por_grupo(cliente, panel, base, pase, django_capture_on_commit_callbacks):
    """CP-62: el despacho ve juntos los viajes de una misma solicitud (vehículos separados)."""
    TestVehiculos().separados(cliente, base, pase, django_capture_on_commit_callbacks, n=1)
    reservar(cliente, base, django_capture_on_commit_callbacks, pase)  # otra solicitud, sin grupo
    grupo = Viaje.objects.exclude(grupo=None).first().grupo
    panel.force_authenticate(UsuarioFactory(empresa=base, rol="DESPACHADOR"))
    respuesta = panel.get(reverse("viaje-list"), {"grupo": str(grupo)})
    assert respuesta.status_code == 200
    assert {v["grupo"] for v in respuesta.data["results"]} == {str(grupo)}
    assert respuesta.data["count"] == 2
