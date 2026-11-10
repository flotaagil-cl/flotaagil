"""HU-11 y HU-34 (CC-16, DC-35): convenios con autoregistro y aprobación. RN-07, RN-08, RN-12, RN-13."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auditoria.models import Auditoria, Entidad
from apps.convenios.models import Convenio, EstadoConvenio
from apps.cuentas.models import Rol, Usuario
from apps.cuentas.tests.fabricas import CLAVE_PRUEBA, UsuarioFactory
from apps.reservas.models import Actor, Canal, HistorialEstado, Viaje
from apps.reservas.tests.fabricas import ConvenioFactory, ViajeFactory

LISTA = reverse("convenio-list")
RUT = "76543210-3"
ORIGEN = "http://localhost:5173"
CLAVE_NUEVA = "Clave-Sintetica-2026"


def detalle(convenio):
    return reverse("convenio-detail", args=[convenio.pk])


def accion(nombre, convenio):
    return reverse(f"convenio-{nombre}", args=[convenio.pk])


@pytest.fixture
def api(cliente, administrador):
    cliente.force_authenticate(administrador)
    return cliente


def registro(**cambios):
    datos = {
        "cliente_nombre": "Constructora Sintética SpA",
        "cliente_rut": "76.543.210-3",
        "direccion": "Av. Apoquindo 3000, Las Condes",
        "encargado_nombre": "Elena Encargada",
        "email": "elena@constructora.example",
        "encargado_telefono": "+56900008001",
        "password": CLAVE_NUEVA,
    }
    datos.update(cambios)
    return datos


def registrar(cliente, empresa, **cambios):
    return cliente.post(
        reverse("portal-registro-empresa", args=[empresa.slug]), registro(**cambios), format="json"
    )


def con_cuenta(empresa, estado=EstadoConvenio.APROBADO):
    usuario = UsuarioFactory(empresa=empresa, rol=Rol.CONVENIO)
    motivo = "Motivo sintético" if estado == EstadoConvenio.RECHAZADO else None
    return ConvenioFactory(
        empresa=empresa,
        estado=estado,
        usuario=usuario,
        encargado_nombre=usuario.nombre,
        motivo_rechazo=motivo,
    )


def como(usuario):
    cliente = APIClient()
    cliente.force_authenticate(usuario)
    return cliente


@pytest.mark.django_db
class TestRegistro:
    def test_queda_en_revision_con_su_cuenta(self, cliente, empresa):
        respuesta = registrar(cliente, empresa)
        assert respuesta.status_code == 201, respuesta.data
        convenio = Convenio.objects.get()
        assert (convenio.estado, convenio.empresa, convenio.cliente_rut) == (
            EstadoConvenio.EN_REVISION,
            empresa,
            "76543210-3",
        )
        usuario = convenio.usuario
        assert (usuario.rol, usuario.email, usuario.empresa) == (
            Rol.CONVENIO,
            "elena@constructora.example",
            empresa,
        )
        assert usuario.check_password(CLAVE_NUEVA)
        assert Auditoria.objects.get(entidad=Entidad.CONVENIO, entidad_id=convenio.pk).accion == "REGISTRO"

    @pytest.mark.parametrize(
        ("campo", "valor"),
        [
            ("cliente_rut", "76543210-0"),
            ("email", "no-es-correo"),
            ("encargado_telefono", "123"),
            ("direccion", " "),
            ("password", "corta"),
        ],
    )
    def test_valida(self, cliente, empresa, campo, valor):
        respuesta = registrar(cliente, empresa, **{campo: valor})
        assert respuesta.status_code == 400
        assert campo in respuesta.data
        assert not Convenio.objects.exists()

    def test_correo_ya_usado(self, cliente, empresa):
        UsuarioFactory(empresa=empresa, email="elena@constructora.example")
        respuesta = registrar(cliente, empresa)
        assert respuesta.status_code == 400
        assert "email" in respuesta.data
        assert not Convenio.objects.exists()

    def test_trampa_responde_igual_sin_crear(self, cliente, empresa):
        assert registrar(cliente, empresa, sitio_web="http://spam.example").status_code == 201
        assert not Convenio.objects.exists()
        assert not Usuario.objects.filter(rol=Rol.CONVENIO).exists()

    def test_limite_por_ip(self, cliente, empresa, monkeypatch):
        from apps.portal.views import PortalPorMinuto

        monkeypatch.setattr(PortalPorMinuto, "rate", "2/min", raising=False)
        estados = [registrar(cliente, empresa, email=f"e{i}@x.example").status_code for i in range(3)]
        assert estados[-1] == 429

    def test_empresa_inexistente(self, cliente):
        respuesta = cliente.post(
            reverse("portal-registro-empresa", args=["no-existe"]), registro(), format="json"
        )
        assert respuesta.status_code == 404


@pytest.mark.django_db
class TestRevision:
    def test_aprobar_audita_y_avisa_por_correo(
        self, api, empresa, administrador, django_capture_on_commit_callbacks
    ):
        convenio = con_cuenta(empresa, EstadoConvenio.EN_REVISION)
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = api.post(accion("aprobar", convenio))
        assert respuesta.status_code == 200
        assert (respuesta.data["estado"], respuesta.data["revisado_por"]) == (
            "APROBADO",
            administrador.nombre,
        )
        assert Auditoria.objects.filter(
            entidad_id=convenio.pk, accion="APROBACION", usuario=administrador
        ).exists()
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [convenio.usuario.email]
        assert "aprobado" in mail.outbox[0].subject

    def test_rechazar_exige_motivo(self, api, empresa, django_capture_on_commit_callbacks):
        convenio = con_cuenta(empresa, EstadoConvenio.EN_REVISION)
        assert api.post(accion("rechazar", convenio), {"motivo": " "}, format="json").status_code == 400
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = api.post(
                accion("rechazar", convenio), {"motivo": "RUT no corresponde"}, format="json"
            )
        assert (respuesta.data["estado"], respuesta.data["motivo_rechazo"]) == (
            "RECHAZADO",
            "RUT no corresponde",
        )
        registro = Auditoria.objects.get(entidad_id=convenio.pk, accion="RECHAZO")
        assert registro.motivo == "RUT no corresponde"
        assert "RUT no corresponde" in mail.outbox[0].body

    @pytest.mark.parametrize(
        "estado", [EstadoConvenio.APROBADO, EstadoConvenio.RECHAZADO, EstadoConvenio.INACTIVO]
    )
    def test_solo_se_revisa_en_revision(self, api, empresa, estado):
        convenio = con_cuenta(empresa, estado)
        assert api.post(accion("aprobar", convenio)).status_code == 409
        assert api.post(accion("rechazar", convenio), {"motivo": "x"}, format="json").status_code == 409


@pytest.mark.django_db
class TestDesactivar:
    def test_corta_el_acceso_al_instante_sin_tocar_el_historial(self, api, empresa):
        """RN-08: la sesión abierta deja de servir y no puede volver a entrar; sus reservas siguen."""
        convenio = con_cuenta(empresa)
        viaje = ViajeFactory(empresa=empresa, canal=Canal.CONVENIO, convenio=convenio)
        web = APIClient(HTTP_ORIGIN=ORIGEN)
        sesion = web.post(
            reverse("auth-token"), {"email": convenio.usuario.email, "password": CLAVE_PRUEBA}, format="json"
        )
        web.credentials(HTTP_AUTHORIZATION=f"Bearer {sesion.data['access']}")
        assert web.get(reverse("mi-convenio")).status_code == 200
        assert api.post(accion("desactivar", convenio)).data["estado"] == "INACTIVO"
        assert web.get(reverse("mi-convenio")).status_code == 401
        assert web.post(reverse("auth-refresh")).status_code == 401
        nueva = APIClient(HTTP_ORIGIN=ORIGEN).post(
            reverse("auth-token"), {"email": convenio.usuario.email, "password": CLAVE_PRUEBA}, format="json"
        )
        assert nueva.data["code"] == "cuenta_deshabilitada"
        viaje.refresh_from_db()
        assert viaje.convenio == convenio
        assert Auditoria.objects.filter(entidad_id=convenio.pk, accion="DESACTIVACION").exists()

    def test_reactivar_devuelve_el_acceso(self, api, empresa):
        convenio = con_cuenta(empresa)
        api.post(accion("desactivar", convenio))
        assert api.post(accion("activar", convenio)).data["estado"] == "APROBADO"
        convenio.usuario.refresh_from_db()
        assert convenio.usuario.activo is True

    def test_el_panel_no_reserva_con_un_convenio_inactivo(self, cliente, despachador, empresa):
        convenio = ConvenioFactory(empresa=empresa, estado=EstadoConvenio.INACTIVO)
        cliente.force_authenticate(despachador)
        respuesta = cliente.post(
            reverse("viaje-list"),
            {
                "pasajero": {"nombre": "Ana", "telefono": "+56900008002"},
                "canal": "CONVENIO",
                "convenio": convenio.pk,
                "origen_dir": "Av. Providencia 1234, Providencia",
                "destino_dir": "Plaza de Armas, Santiago",
                "recogida_en": (timezone.now() + timedelta(hours=3)).isoformat(),
            },
            format="json",
        )
        assert respuesta.status_code == 400


@pytest.mark.django_db
class TestRestablecer:
    def test_temporal_dc14_y_auditoria(self, api, empresa):
        convenio = con_cuenta(empresa)
        respuesta = api.post(accion("restablecer-password", convenio))
        assert respuesta.status_code == 201
        assert respuesta["Cache-Control"] == "no-store"
        usuario = Usuario.objects.get(pk=convenio.usuario_id)
        assert usuario.debe_cambiar_password is True
        assert usuario.check_password(respuesta.data["password_temporal"])
        assert Auditoria.objects.filter(
            entidad=Entidad.CONVENIO, entidad_id=convenio.pk, accion="CAMBIO_CLAVE"
        ).exists()
        assert respuesta.data["password_temporal"] not in str(list(Auditoria.objects.values()))

    def test_sin_cuenta_409(self, api, empresa):
        assert api.post(accion("restablecer-password", ConvenioFactory(empresa=empresa))).status_code == 409


@pytest.mark.django_db
class TestAdministracion:
    def test_el_administrador_no_crea_convenios(self, api):
        """Decisión del PO (DC-35): los convenios llegan solo por el registro del portal."""
        respuesta = api.post(LISTA, {"cliente_nombre": "Minera", "cliente_rut": RUT}, format="json")
        assert respuesta.status_code == 405
        assert not Convenio.objects.exists()

    def test_sin_cuenta_es_historial_edita_y_desactiva_pero_no_reactiva(self, api, empresa):
        convenio = ConvenioFactory(empresa=empresa)
        assert api.patch(detalle(convenio), {"direccion": "Calle 1"}, format="json").status_code == 200
        assert api.post(accion("desactivar", convenio)).data["estado"] == "INACTIVO"
        respuesta = api.post(accion("activar", convenio))
        assert (respuesta.status_code, respuesta.data["code"]) == (409, "sin_cuenta")

    def test_edita_y_audita_lo_anterior(self, api, empresa):
        convenio = con_cuenta(empresa)
        respuesta = api.patch(
            detalle(convenio), {"direccion": "Nueva 123", "estado": "INACTIVO"}, format="json"
        )
        assert respuesta.data["direccion"] == "Nueva 123"
        assert respuesta.data["estado"] == "APROBADO"  # el estado no se edita aquí
        assert Auditoria.objects.get(entidad_id=convenio.pk, accion="EDICION").datos_previos == {
            "direccion": None
        }

    def test_listado_y_filtro_por_estado(self, api, empresa):
        con_cuenta(empresa, EstadoConvenio.EN_REVISION)
        ConvenioFactory(empresa=empresa)
        filas = api.get(LISTA, {"estado": "EN_REVISION"}).json()["results"]
        assert [(f["estado"], f["tiene_cuenta"]) for f in filas] == [("EN_REVISION", True)]

    def test_solo_el_administrador_y_su_empresa(self, cliente, despachador, empresa, otra_empresa, api):
        assert api.get(detalle(ConvenioFactory(empresa=otra_empresa))).status_code == 404
        cliente.force_authenticate(despachador)
        assert cliente.get(LISTA).status_code == 403


@pytest.mark.django_db
class TestCuentaDelConvenio:
    def solicitud(self, **cambios):
        datos = {
            "nombre": "Pasajero Sintético",
            "telefono": "+56900008003",
            "origen_dir": "Av. Providencia 1234, Providencia",
            "destino_dir": "Plaza de Armas, Santiago",
            "recogida_en": (timezone.now() + timedelta(hours=2)).isoformat(),
            "acepta_privacidad": True,
            "acepta_whatsapp": True,
            "declara_autorizacion": True,
        }
        datos.update(cambios)
        return datos

    def test_aprobado_reserva_sin_verificacion_y_con_la_declaracion_del_usuario(self, empresa):
        convenio = con_cuenta(empresa)
        respuesta = como(convenio.usuario).post(
            reverse("mi-convenio-solicitudes"), self.solicitud(), format="json"
        )
        assert respuesta.status_code == 201, respuesta.data
        assert (respuesta.data["estado"], respuesta.data["expira_en"]) == ("SOLICITADO", None)
        viaje = Viaje.objects.get()
        assert (viaje.canal, viaje.convenio, viaje.autorizacion_avisos_por) == (
            Canal.CONVENIO,
            convenio,
            convenio.usuario,
        )
        assert viaje.autorizacion_avisos_en is not None
        historial = HistorialEstado.objects.get(viaje=viaje)
        assert (historial.actor, historial.usuario) == (Actor.PASAJERO, convenio.usuario)

    def test_exige_la_declaracion(self, empresa):
        convenio = con_cuenta(empresa)
        respuesta = como(convenio.usuario).post(
            reverse("mi-convenio-solicitudes"), self.solicitud(declara_autorizacion=False), format="json"
        )
        assert respuesta.status_code == 400

    @pytest.mark.parametrize("estado", [EstadoConvenio.EN_REVISION, EstadoConvenio.RECHAZADO])
    def test_en_revision_o_rechazado_entra_pero_no_reserva(self, empresa, estado):
        convenio = con_cuenta(empresa, estado)
        cliente = como(convenio.usuario)
        assert cliente.get(reverse("mi-convenio")).data["estado"] == estado
        respuesta = cliente.post(reverse("mi-convenio-solicitudes"), self.solicitud(), format="json")
        assert (respuesta.status_code, respuesta.data["code"]) == (409, "convenio_no_aprobado")
        assert not Viaje.objects.exists()

    def test_ve_solo_sus_reservas(self, empresa):
        convenio = con_cuenta(empresa)
        propia = ViajeFactory(empresa=empresa, canal=Canal.CONVENIO, convenio=convenio)
        ViajeFactory(empresa=empresa, canal=Canal.CONVENIO, convenio=ConvenioFactory(empresa=empresa))
        ViajeFactory(empresa=empresa)
        filas = como(convenio.usuario).get(reverse("mi-convenio-reservas")).json()["results"]
        assert [f["id"] for f in filas] == [propia.pk]

    def test_otros_roles_no_entran(self, empresa, despachador):
        UsuarioFactory(empresa=empresa, rol=Rol.PASAJERO)
        assert como(despachador).get(reverse("mi-convenio")).status_code == 403

    def test_el_link_anterior_ya_no_existe(self, cliente):
        assert cliente.get("/api/convenio/un-token-cualquiera/").status_code == 404

    def test_no_se_puede_entrar_con_la_cuenta_inactiva_aunque_sea_el_rol(self, empresa):
        convenio = con_cuenta(empresa, EstadoConvenio.INACTIVO)
        Usuario.objects.filter(pk=convenio.usuario_id).update(activo=False)
        respuesta = APIClient(HTTP_ORIGIN=ORIGEN).post(
            reverse("auth-token"), {"email": convenio.usuario.email, "password": CLAVE_PRUEBA}, format="json"
        )
        assert respuesta.status_code == 401
        assert settings.LOGIN_MAX_INTENTOS == 5


@pytest.mark.django_db
class TestAuditoriaConsultable:
    """HU-12 · CP-24 (RN-12)."""

    def consultar(self, api, convenio, **parametros):
        return api.get(reverse("convenio-auditoria", args=[convenio.pk]), parametros)

    def test_muestra_quien_que_y_cuando_del_mas_nuevo_al_mas_antiguo(self, api, administrador, empresa):
        convenio = con_cuenta(empresa)
        api.post(accion("desactivar", convenio))
        api.post(accion("activar", convenio))
        filas = self.consultar(api, convenio).json()["results"]
        assert [f["accion"] for f in filas] == ["ACTIVACION", "DESACTIVACION"]
        assert {f["usuario"] for f in filas} == {administrador.nombre}

    def test_no_expone_datos_previos_ni_credenciales(self, api, empresa):
        convenio = con_cuenta(empresa)
        temporal = api.post(accion("restablecer-password", convenio)).data["password_temporal"]
        contenido = self.consultar(api, convenio).content.decode()
        assert temporal not in contenido
        assert "datos_previos" not in contenido

    def test_pagina(self, api, empresa):
        convenio = ConvenioFactory(empresa=empresa)
        for i in range(26):
            api.patch(detalle(convenio), {"direccion": f"Calle {i}"}, format="json")
        primera = self.consultar(api, convenio).json()
        assert (primera["count"], len(primera["results"])) == (26, 25)

    def test_es_de_solo_lectura_y_aislada(self, api, otra_empresa, cliente, despachador, empresa):
        convenio = ConvenioFactory(empresa=empresa)
        assert (
            api.post(reverse("convenio-auditoria", args=[convenio.pk]), {}, format="json").status_code == 405
        )
        assert self.consultar(api, ConvenioFactory(empresa=otra_empresa)).status_code == 404
        cliente.force_authenticate(despachador)
        assert self.consultar(cliente, ConvenioFactory(empresa=empresa)).status_code == 403
