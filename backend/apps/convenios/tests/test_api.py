"""HU-11 · Administrar convenios con link y contraseña. CP-22 (RN-08, RN-12, RN-13)."""

import json

import pytest
from django.contrib.auth.hashers import check_password
from django.urls import reverse

from apps.auditoria.models import Auditoria, Entidad
from apps.convenios.models import Convenio
from apps.reservas.models import Canal, EstadoViaje
from apps.reservas.tests.fabricas import ConvenioFactory, ViajeFactory

LISTA = reverse("convenio-list")
RUT = "76543210-3"


def detalle(convenio):
    return reverse("convenio-detail", args=[convenio.pk])


def rotar(convenio):
    return reverse("convenio-rotar-password", args=[convenio.pk])


@pytest.fixture
def api(cliente, administrador):
    cliente.force_authenticate(administrador)
    return cliente


def crear(api, **cambios):
    return api.post(
        LISTA, {"cliente_nombre": "Minera Sintética S.A.", "cliente_rut": RUT} | cambios, format="json"
    )


@pytest.mark.django_db
class TestCrear:
    def test_genera_token_de_256_bits_y_contrasena(self, api, empresa):
        respuesta = crear(api)
        assert respuesta.status_code == 201, respuesta.data
        datos = respuesta.json()
        convenio = Convenio.objects.get(pk=datos["id"])
        assert convenio.empresa == empresa
        assert len(datos["token_link"]) == 43
        assert datos["token_link"] == convenio.token_link
        assert len(datos["password"]) >= 12
        assert convenio.check_password(datos["password"])
        assert datos["activo"] is True
        assert datos["reservas"] == 0

    def test_cada_convenio_tiene_su_token_y_su_contrasena(self, api):
        uno, otro = crear(api).json(), crear(api).json()
        assert uno["token_link"] != otro["token_link"]
        assert uno["password"] != otro["password"]

    def test_la_contrasena_solo_se_guarda_con_hash(self, api):
        datos = crear(api).json()
        convenio = Convenio.objects.get(pk=datos["id"])
        assert datos["password"] not in convenio.password_hash
        assert convenio.password_hash.startswith("pbkdf2_sha256$")

    def test_la_contrasena_no_se_vuelve_a_entregar(self, api):
        datos = crear(api).json()
        convenio = Convenio.objects.get(pk=datos["id"])
        assert "password" not in api.get(detalle(convenio)).json()
        assert "password_hash" not in api.get(detalle(convenio)).json()

    def test_normaliza_el_rut(self, api):
        assert crear(api, cliente_rut="76.543.210-3").json()["cliente_rut"] == RUT

    @pytest.mark.parametrize(
        ("cambios", "campo"),
        [
            ({"cliente_rut": "76543210-4"}, "cliente_rut"),
            ({"cliente_rut": "abc"}, "cliente_rut"),
            ({"cliente_nombre": "   "}, "cliente_nombre"),
        ],
    )
    def test_valida(self, api, cambios, campo):
        respuesta = crear(api, **cambios)
        assert respuesta.status_code == 400
        assert campo in respuesta.json()
        assert not Convenio.objects.exists()

    def test_queda_en_auditoria_sin_la_contrasena(self, api, administrador):
        datos = crear(api).json()
        registro = Auditoria.objects.get(entidad=Entidad.CONVENIO, accion="CREACION")
        assert (registro.usuario, registro.entidad_id) == (administrador, datos["id"])
        assert datos["password"] not in json.dumps(registro.datos_previos)


@pytest.mark.django_db
class TestRotar:
    def test_la_nueva_sirve_y_la_anterior_no(self, api):
        creado = crear(api).json()
        convenio = Convenio.objects.get(pk=creado["id"])
        respuesta = api.post(rotar(convenio))
        assert respuesta.status_code == 200
        nueva = respuesta.json()["password"]
        convenio.refresh_from_db()
        assert convenio.check_password(nueva)
        assert not convenio.check_password(creado["password"])

    def test_no_cambia_el_token(self, api):
        creado = crear(api).json()
        convenio = Convenio.objects.get(pk=creado["id"])
        api.post(rotar(convenio))
        convenio.refresh_from_db()
        assert convenio.token_link == creado["token_link"]

    def test_queda_en_auditoria_inmutable_sin_hashes(self, api, empresa, administrador):
        """RN-12."""
        convenio = ConvenioFactory(empresa=empresa)
        previo = convenio.password_hash
        api.post(rotar(convenio))
        registro = Auditoria.objects.get(entidad=Entidad.CONVENIO, accion="CAMBIO_CLAVE")
        assert (registro.usuario, registro.entidad_id) == (administrador, convenio.pk)
        assert previo not in json.dumps(registro.datos_previos)


@pytest.mark.django_db
class TestEstado:
    def test_desactivar_no_borra_el_historial(self, api, empresa):
        """RN-08."""
        convenio = ConvenioFactory(empresa=empresa)
        viaje = ViajeFactory(
            empresa=empresa, canal=Canal.CONVENIO, convenio=convenio, estado=EstadoViaje.SOLICITADO
        )
        respuesta = api.patch(detalle(convenio), {"activo": False}, format="json")
        assert respuesta.status_code == 200, respuesta.data
        assert respuesta.json()["activo"] is False
        assert respuesta.json()["reservas"] == 1
        viaje.refresh_from_db()
        assert viaje.convenio == convenio
        assert viaje.estado == EstadoViaje.SOLICITADO
        assert Auditoria.objects.filter(entidad=Entidad.CONVENIO, accion="DESACTIVACION").count() == 1

    def test_reactivar_conserva_el_link(self, api, empresa):
        convenio = ConvenioFactory(empresa=empresa, activo=False)
        token = convenio.token_link
        api.patch(detalle(convenio), {"activo": True}, format="json")
        convenio.refresh_from_db()
        assert (convenio.activo, convenio.token_link) == (True, token)
        assert Auditoria.objects.filter(accion="ACTIVACION").count() == 1

    def test_un_convenio_inactivo_no_admite_reservas_nuevas(self, cliente, despachador, empresa):
        """RN-08, con la validación que ya existía en el panel."""
        convenio = ConvenioFactory(empresa=empresa, activo=False)
        cliente.force_authenticate(despachador)
        cuerpo = {
            "pasajero": {"nombre": "Ana Pérez", "telefono": "+56900009001"},
            "canal": "CONVENIO",
            "convenio": convenio.pk,
            "origen_dir": "Plaza de Armas, Santiago",
            "destino_dir": "Av. Providencia 1234",
            "recogida_en": "2030-01-01T12:00:00Z",
        }
        respuesta = cliente.post(reverse("viaje-list"), cuerpo, format="json")
        assert respuesta.status_code == 400
        assert "convenio" in respuesta.json()

    def test_sin_cambios_no_audita(self, api, empresa):
        convenio = ConvenioFactory(empresa=empresa)
        api.patch(
            detalle(convenio), {"activo": True, "cliente_nombre": convenio.cliente_nombre}, format="json"
        )
        assert not Auditoria.objects.exists()


@pytest.mark.django_db
class TestEditar:
    def test_edita_y_audita_lo_anterior(self, api, empresa):
        convenio = ConvenioFactory(empresa=empresa, cliente_nombre="Antes S.A.")
        respuesta = api.patch(detalle(convenio), {"cliente_nombre": " Después S.A. "}, format="json")
        assert respuesta.json()["cliente_nombre"] == "Después S.A."
        registro = Auditoria.objects.get(accion="EDICION")
        assert registro.datos_previos == {"cliente_nombre": "Antes S.A."}

    def test_no_se_puede_tocar_el_token_ni_la_empresa(self, api, empresa, otra_empresa):
        convenio = ConvenioFactory(empresa=empresa)
        token = convenio.token_link
        api.patch(detalle(convenio), {"token_link": "x" * 43, "empresa": otra_empresa.pk}, format="json")
        convenio.refresh_from_db()
        assert (convenio.token_link, convenio.empresa) == (token, empresa)

    def test_valida(self, api, empresa):
        convenio = ConvenioFactory(empresa=empresa)
        assert api.patch(detalle(convenio), {"cliente_rut": "1-1"}, format="json").status_code == 400


@pytest.mark.django_db
class TestListado:
    def test_con_volumen_de_reservas(self, api, empresa):
        con, sin = (
            ConvenioFactory(empresa=empresa, cliente_nombre="A"),
            ConvenioFactory(empresa=empresa, cliente_nombre="B"),
        )
        for _ in range(3):
            ViajeFactory(empresa=empresa, canal=Canal.CONVENIO, convenio=con)
        filas = api.get(LISTA).json()["results"]
        assert [(f["id"], f["reservas"]) for f in filas] == [(con.pk, 3), (sin.pk, 0)]

    def test_el_listado_no_expone_el_token(self, api, empresa):
        ConvenioFactory(empresa=empresa)
        assert "token_link" not in api.get(LISTA).json()["results"][0]

    def test_filtra_por_estado_y_busqueda(self, api, empresa):
        activo = ConvenioFactory(empresa=empresa, cliente_nombre="Minera Norte", cliente_rut=RUT)
        ConvenioFactory(empresa=empresa, cliente_nombre="Banco Sur", activo=False)
        assert [f["id"] for f in api.get(LISTA, {"activo": "true"}).json()["results"]] == [activo.pk]
        assert [f["id"] for f in api.get(LISTA, {"q": "minera"}).json()["results"]] == [activo.pk]
        assert [f["id"] for f in api.get(LISTA, {"q": "76543"}).json()["results"]] == [activo.pk]
        assert len(api.get(LISTA, {"q": "   "}).json()["results"]) == 2


@pytest.mark.django_db
class TestPermisos:
    def test_otra_empresa_no_existe(self, api, otra_empresa):
        """RN-13."""
        ajeno = ConvenioFactory(empresa=otra_empresa)
        assert api.get(LISTA).json()["results"] == []
        assert api.get(detalle(ajeno)).status_code == 404
        assert api.patch(detalle(ajeno), {"activo": False}, format="json").status_code == 404
        assert api.post(rotar(ajeno)).status_code == 404
        hash_previo = ajeno.password_hash
        ajeno.refresh_from_db()
        assert ajeno.password_hash == hash_previo
        assert ajeno.activo is True

    def test_solo_el_administrador(self, cliente, despachador, empresa):
        convenio = ConvenioFactory(empresa=empresa)
        cliente.force_authenticate(despachador)
        assert cliente.get(LISTA).status_code == 403
        assert cliente.post(rotar(convenio)).status_code == 403
        assert cliente.post(LISTA, {}, format="json").status_code == 403

    def test_sin_sesion(self, cliente):
        assert cliente.get(LISTA).status_code == 401

    def test_la_contrasena_del_modelo_sigue_verificable(self, api):
        datos = crear(api).json()
        convenio = Convenio.objects.get(pk=datos["id"])
        assert check_password(datos["password"], convenio.password_hash)


@pytest.mark.django_db
class TestAuditoriaConsultable:
    """HU-12 · CP-24 (RN-12)."""

    def consultar(self, api, convenio, **parametros):
        return api.get(reverse("convenio-auditoria", args=[convenio.pk]), parametros)

    def test_muestra_quien_que_y_cuando_del_mas_nuevo_al_mas_antiguo(self, api, administrador):
        convenio = Convenio.objects.get(pk=crear(api).json()["id"])
        api.post(rotar(convenio))
        api.patch(detalle(convenio), {"activo": False}, format="json")
        api.patch(detalle(convenio), {"activo": True}, format="json")
        respuesta = self.consultar(api, convenio)
        assert respuesta.status_code == 200
        filas = respuesta.json()["results"]
        assert [f["accion"] for f in filas] == ["ACTIVACION", "DESACTIVACION", "CAMBIO_CLAVE", "CREACION"]
        assert {f["usuario"] for f in filas} == {administrador.nombre}
        assert all(f["creado_en"] for f in filas)

    def test_no_expone_datos_previos_ni_credenciales(self, api):
        creado = crear(api).json()
        convenio = Convenio.objects.get(pk=creado["id"])
        api.patch(detalle(convenio), {"cliente_nombre": "Otro nombre"}, format="json")
        contenido = self.consultar(api, convenio).content.decode()
        assert creado["password"] not in contenido
        assert convenio.password_hash not in contenido
        assert convenio.token_link not in contenido
        assert "datos_previos" not in contenido

    def test_solo_los_de_ese_convenio(self, api):
        uno = Convenio.objects.get(pk=crear(api).json()["id"])
        otro = Convenio.objects.get(pk=crear(api, cliente_nombre="Otro").json()["id"])
        api.post(rotar(otro))
        assert [f["accion"] for f in self.consultar(api, uno).json()["results"]] == ["CREACION"]

    def test_pagina(self, api):
        convenio = Convenio.objects.get(pk=crear(api).json()["id"])
        for _ in range(25):
            api.post(rotar(convenio))
        primera = self.consultar(api, convenio).json()
        assert (primera["count"], len(primera["results"])) == (26, 25)
        assert len(self.consultar(api, convenio, page=2).json()["results"]) == 1

    def test_es_de_solo_lectura(self, api):
        convenio = Convenio.objects.get(pk=crear(api).json()["id"])
        ruta = reverse("convenio-auditoria", args=[convenio.pk])
        assert api.post(ruta, {}, format="json").status_code == 405
        assert api.delete(ruta).status_code == 405
        assert api.patch(ruta, {}, format="json").status_code == 405

    def test_otra_empresa_404(self, api, otra_empresa):
        """RN-13."""
        assert self.consultar(api, ConvenioFactory(empresa=otra_empresa)).status_code == 404

    def test_despachador_403(self, cliente, despachador, empresa):
        cliente.force_authenticate(despachador)
        assert self.consultar(cliente, ConvenioFactory(empresa=empresa)).status_code == 403
