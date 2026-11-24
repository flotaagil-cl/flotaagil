"""CC-23 (HU-72): clave del convenio y pase con correo + clave en el portal base. CP-58 y CP-59.

La clave se lee del correo solo dentro de la prueba y nunca se imprime: los mensajes de las aserciones no la
incluyen.
"""

import re
from unittest import mock

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import Auditoria
from apps.convenios import servicios as convenios
from apps.convenios.models import Convenio, EstadoConvenio
from apps.cuentas.tests.fabricas import EmpresaFactory, UsuarioFactory
from apps.portal import pase as pases

CONTACTO = "contacto@minera.example"


@pytest.fixture
def base(db):
    return EmpresaFactory(modulo_cuentas=False)


@pytest.fixture
def admin_base(base):
    return UsuarioFactory(empresa=base, rol="ADMINISTRADOR")


def clave_del_correo(correo) -> str:
    """La clave va sola en su línea, con 4 espacios de sangría (`texto_como_pedir`)."""
    encontrada = re.search(r"^ {4}([A-Z0-9]{5}-[A-Z0-9]{5})$", correo.body, re.MULTILINE)
    assert encontrada, "el correo no trae la clave"
    return encontrada.group(1)


def nuevo_convenio(empresa, **cambios) -> Convenio:
    valores = {
        "empresa": empresa,
        "cliente_nombre": "Minera Sintética S.A.",
        "cliente_rut": "76543210-3",
        "estado": EstadoConvenio.EN_REVISION,
        "encargado_nombre": "Ana Contacto",
        "contacto_correo": CONTACTO,
        "correos_autorizados": ["@minera.example", "pedro@otra.example"],
    }
    valores.update(cambios)
    return Convenio.objects.create(**valores)


def aprobar(convenio, admin, capturar) -> str:
    with capturar(execute=True):
        convenios.aprobar(convenio, usuario=admin)
    return clave_del_correo(mail.outbox[-1])


@pytest.fixture
def aprobado(base, admin_base, django_capture_on_commit_callbacks):
    convenio = nuevo_convenio(base)
    clave = aprobar(convenio, admin_base, django_capture_on_commit_callbacks)
    convenio.refresh_from_db()
    mail.outbox.clear()
    return convenio, clave


def pedir_pase(cliente, empresa, correo, clave):
    return cliente.post(
        reverse("portal-convenio-pase", args=[empresa.slug]),
        {"correo": correo, "clave": clave},
        format="json",
    )


@pytest.fixture
def pase(cliente, base, aprobado):
    _, clave = aprobado
    return pedir_pase(cliente, base, "ana@minera.example", clave).data["pase"]


def correos_a(destino):
    return [m for m in mail.outbox if m.to == [destino]]


@pytest.mark.django_db
class TestClaveDelConvenio:
    """CP-58: generación, regeneración y revocación (D1), solo con hash y en auditoría (RN-12)."""

    def test_aprobar_genera_la_clave_y_la_envia_solo_al_contacto(
        self, base, admin_base, django_capture_on_commit_callbacks
    ):
        convenio = nuevo_convenio(base)
        clave = aprobar(convenio, admin_base, django_capture_on_commit_callbacks)
        convenio.refresh_from_db()
        assert mail.outbox[-1].to == [CONTACTO]
        assert convenio.clave_hash and clave not in convenio.clave_hash  # solo el hash
        assert convenio.clave_version == 1 and convenio.clave_generada_en is not None
        assert "Empresa con convenio" in mail.outbox[-1].body
        assert Auditoria.objects.filter(entidad_id=convenio.pk, accion="CAMBIO_CLAVE").exists()

    def test_con_modulo_de_cuentas_no_hay_clave(self, db, django_capture_on_commit_callbacks):
        empresa = EmpresaFactory(modulo_cuentas=True)
        convenio = nuevo_convenio(empresa)
        with django_capture_on_commit_callbacks(execute=True):
            convenios.aprobar(convenio, usuario=UsuarioFactory(empresa=empresa, rol="ADMINISTRADOR"))
        convenio.refresh_from_db()
        assert convenio.clave_hash is None

    def test_el_administrador_regenera_y_la_anterior_deja_de_servir(
        self, cliente, panel, base, admin_base, aprobado, django_capture_on_commit_callbacks
    ):
        convenio, anterior = aprobado
        panel.force_authenticate(admin_base)
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = panel.post(reverse("convenio-regenerar-clave", args=[convenio.pk]))
        assert respuesta.status_code == 200
        assert respuesta.data["clave_vigente"] is True and "clave" not in respuesta.data
        nueva = clave_del_correo(correos_a(CONTACTO)[-1])
        assert nueva != anterior
        assert pedir_pase(cliente, base, CONTACTO, anterior).status_code == 400
        assert pedir_pase(cliente, base, CONTACTO, nueva).status_code == 200

    @pytest.mark.parametrize("accion", ["convenio-regenerar-clave", "convenio-revocar-clave"])
    def test_el_despachador_no_toca_la_clave(self, panel, base, aprobado, accion):
        convenio, _ = aprobado
        panel.force_authenticate(UsuarioFactory(empresa=base, rol="DESPACHADOR"))
        assert panel.post(reverse(accion, args=[convenio.pk])).status_code == 403

    def test_revocar_deja_sin_clave(self, cliente, panel, base, admin_base, aprobado):
        convenio, clave = aprobado
        panel.force_authenticate(admin_base)
        respuesta = panel.post(reverse("convenio-revocar-clave", args=[convenio.pk]))
        assert respuesta.status_code == 200 and respuesta.data["clave_vigente"] is False
        assert pedir_pase(cliente, base, CONTACTO, clave).status_code == 400
        assert Auditoria.objects.filter(entidad_id=convenio.pk, accion="REVOCACION_CLAVE").exists()
        assert panel.post(reverse("convenio-revocar-clave", args=[convenio.pk])).status_code == 409

    def test_desactivar_corta_la_clave_y_al_reactivar_se_genera_otra(
        self, cliente, panel, base, admin_base, aprobado, django_capture_on_commit_callbacks
    ):
        convenio, clave = aprobado
        panel.force_authenticate(admin_base)
        panel.post(reverse("convenio-desactivar", args=[convenio.pk]))
        respuesta = panel.post(reverse("convenio-activar", args=[convenio.pk]))
        assert respuesta.status_code == 200 and respuesta.data["estado"] == EstadoConvenio.APROBADO
        assert respuesta.data["clave_vigente"] is False
        assert pedir_pase(cliente, base, CONTACTO, clave).status_code == 400
        with django_capture_on_commit_callbacks(execute=True):
            panel.post(reverse("convenio-regenerar-clave", args=[convenio.pk]))
        nueva = clave_del_correo(correos_a(CONTACTO)[-1])
        assert pedir_pase(cliente, base, CONTACTO, nueva).status_code == 200

    def test_la_clave_no_queda_en_respuestas_ni_auditoria(self, panel, base, admin_base, aprobado):
        convenio, clave = aprobado
        panel.force_authenticate(admin_base)
        detalle = panel.get(reverse("convenio-detail", args=[convenio.pk])).content.decode()
        auditoria = panel.get(reverse("convenio-auditoria", args=[convenio.pk])).content.decode()
        registros = str(list(Auditoria.objects.values_list("motivo", "datos_previos")))
        for texto in (detalle, auditoria, registros):
            assert clave not in texto and convenios.normalizar_clave(clave) not in texto


@pytest.mark.django_db
class TestPase:
    """CP-59: correo + clave → pase; mismo error para todo fallo; límites, bloqueo y revalidación."""

    @pytest.mark.parametrize("correo", [CONTACTO, "Paula@Minera.example", "pedro@otra.example"])
    def test_contacto_o_autorizado_recibe_el_pase(self, cliente, base, aprobado, correo):
        _, clave = aprobado
        respuesta = pedir_pase(cliente, base, correo, clave)
        assert respuesta.status_code == 200
        assert respuesta.data["cliente_nombre"] == "Minera Sintética S.A."
        assert respuesta.data["correo"].endswith("***@" + correo.split("@")[1].lower())
        assert respuesta["Cache-Control"] == "no-store"

    def test_la_clave_se_acepta_sin_guion_y_en_minusculas(self, cliente, base, aprobado):
        _, clave = aprobado
        assert pedir_pase(cliente, base, CONTACTO, clave.replace("-", "").lower()).status_code == 200

    def test_mismo_error_para_clave_mala_y_correo_no_autorizado(self, cliente, base, aprobado):
        _, clave = aprobado
        mala = pedir_pase(cliente, base, CONTACTO, "AAAAA-BBBBB")
        ajeno = pedir_pase(cliente, base, "x@gmail.example", clave)
        assert mala.status_code == ajeno.status_code == 400
        assert mala.data == ajeno.data and mala.data["code"] == "clave_invalida"

    @pytest.mark.parametrize(
        "estado", [EstadoConvenio.EN_REVISION, EstadoConvenio.RECHAZADO, EstadoConvenio.INACTIVO]
    )
    def test_convenio_no_aprobado(self, cliente, base, aprobado, estado):
        convenio, clave = aprobado
        Convenio.objects.filter(pk=convenio.pk).update(estado=estado, motivo_rechazo="Sintético")
        assert pedir_pase(cliente, base, CONTACTO, clave).data["code"] == "clave_invalida"

    def test_con_modulo_de_cuentas_no_existe(self, cliente, db):
        empresa = EmpresaFactory(modulo_cuentas=True)
        assert pedir_pase(cliente, empresa, CONTACTO, "AAAAA-BBBBB").status_code == 404

    def test_bloqueo_tras_fallos_seguidos(self, cliente, base, aprobado):
        convenio, clave = aprobado
        base.configuracion.convenio_pase_max_fallos = 3
        base.configuracion.save()
        for _ in range(3):
            assert pedir_pase(cliente, base, CONTACTO, "AAAAA-BBBBB").status_code == 400
        bloqueado = pedir_pase(cliente, base, CONTACTO, clave)
        assert (bloqueado.status_code, bloqueado.data["code"]) == (429, "clave_bloqueada")
        registro = Auditoria.objects.get(entidad_id=convenio.pk, accion="BLOQUEO_CLAVE")
        assert registro.usuario is None
        assert pedir_pase(cliente, base, "pedro@otra.example", clave).status_code == 200  # otro correo

    def test_limite_por_ip(self, cliente, base, aprobado):
        _, clave = aprobado
        base.configuracion.reserva_publica_max_ip_hora = 2
        base.configuracion.save()
        for _ in range(2):
            pedir_pase(cliente, base, CONTACTO, clave)
        assert pedir_pase(cliente, base, CONTACTO, clave).data["code"] == "limite_ip"

    def test_pase_vencido(self, base, pase):
        despues = timezone.now().timestamp() + 121 * 60
        with (
            mock.patch("django.core.signing.time.time", return_value=despues),
            pytest.raises(pases.PaseVencido),
        ):
            pases.validar(base, pase)

    @pytest.mark.parametrize("accion", ["regenerar", "revocar", "desactivar", "correo"])
    def test_pase_invalidado(self, base, admin_base, aprobado, pase, accion):
        convenio, _ = aprobado
        if accion == "regenerar":
            convenios.regenerar_clave(convenio, usuario=admin_base)
        elif accion == "revocar":
            convenios.revocar_clave(convenio, usuario=admin_base)
        elif accion == "desactivar":
            convenios.desactivar(convenio, usuario=admin_base)
        else:  # el correo dejó de estar autorizado
            Convenio.objects.filter(pk=convenio.pk).update(correos_autorizados=[])
        with pytest.raises(pases.PaseInvalido):
            pases.validar(base, pase)

    def test_pase_vigente_devuelve_convenio_y_correo(self, base, aprobado, pase):
        convenio, _ = aprobado
        assert pases.validar(base, pase) == (convenio, "ana@minera.example")

    def test_pase_de_otra_empresa_no_sirve(self, pase):
        # RN-13: la firma es válida, pero el convenio no es de esta empresa.
        with pytest.raises(pases.PaseInvalido):
            pases.validar(EmpresaFactory(modulo_cuentas=False), pase)

    def test_pase_adulterado(self, base, pase):
        with pytest.raises(pases.PaseInvalido):
            pases.validar(base, pase + "x")
