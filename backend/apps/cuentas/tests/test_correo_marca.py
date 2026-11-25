"""CC-27 (HU-80, CP-74): los correos llevan el logo y los colores de la empresa."""

import io
from unittest import mock

import pytest
from django.core import mail
from PIL import Image

from apps.cuentas import correo_marca, logos, tareas
from apps.cuentas.paletas import paleta_de
from apps.integraciones.correo import CID_LOGO

pytestmark = pytest.mark.django_db


def _con_logo(empresa):
    imagen = Image.new("RGBA", (600, 200), (0, 0, 0, 0))
    imagen.paste((43, 42, 120, 255), (40, 40, 560, 160))
    archivo = io.BytesIO()
    imagen.save(archivo, "PNG")
    empresa.logo = logos.guardar(empresa.pk, logos.procesar(archivo.getvalue()))
    empresa.save(update_fields=["logo"])


def _html(mensaje):
    contenido, tipo = mensaje.alternatives[0]
    assert tipo == "text/html"
    return contenido


class TestCorreoConMarca:
    def test_usa_los_colores_de_la_paleta_y_adjunta_el_logo(self, empresa):
        empresa.paleta = "indigo"
        empresa.save(update_fields=["paleta"])
        _con_logo(empresa)
        texto = "Hola Ana:\n\nTe esperamos."
        tareas.enviar_correo.delay("ana@ejemplo.example", "Confirma", texto, empresa.pk)
        mensaje = mail.outbox[0]
        paleta = paleta_de("indigo")
        html = _html(mensaje)
        for color in (paleta.oscuro, paleta.medio, paleta.claro):
            assert color in html
        assert f'src="cid:{CID_LOGO}"' in html
        assert empresa.razon_social in html
        assert mensaje.body == texto  # el texto plano no cambia
        (imagen,) = mensaje.attachments
        assert imagen["Content-ID"] == f"<{CID_LOGO}>"
        assert imagen.get_content_type() == "image/png"
        with logos.default_storage.open(logos.ruta(empresa.logo, "correo"), "rb") as guardado:
            assert imagen.get_payload(decode=True) == guardado.read()
        assert mensaje.message().get_content_type() == "multipart/related"

    def test_sin_logo_usa_el_de_flotaagil_y_la_paleta_predeterminada(self, empresa):
        tareas.enviar_correo.delay("ana@ejemplo.example", "A", "T", empresa.pk)
        html = _html(mail.outbox[0])
        assert "FlotaÁgil</span>" in html
        assert "cid:" not in html
        assert paleta_de("tiffany").oscuro in html
        assert mail.outbox[0].attachments == []

    def test_cc21_usa_el_nombre_de_marca_y_sin_logo_las_iniciales(self, empresa):
        empresa.nombre_marca, empresa.iniciales = "Andes <Traslados>", "AT"
        empresa.save(update_fields=["nombre_marca", "iniciales"])
        tareas.enviar_correo.delay("ana@ejemplo.example", "A", "T", empresa.pk)
        html = _html(mail.outbox[0])
        assert "AT</span>" in html and "FlotaÁgil</span>" not in html
        assert "Andes &lt;Traslados&gt;" in html and empresa.razon_social not in html

    def test_cc21_el_nombre_visible_cae_en_la_razon_social(self, empresa):
        assert empresa.nombre_visible == empresa.razon_social
        empresa.nombre_marca = "Andes"
        assert empresa.nombre_visible == "Andes"

    def test_si_el_logo_no_se_puede_leer_el_correo_sale_igual(self, empresa):
        empresa.logo = f"logos/{empresa.pk}/no-existe"
        empresa.save(update_fields=["logo"])
        tareas.enviar_correo.delay("ana@ejemplo.example", "A", "T", empresa.pk)
        assert "cid:" not in _html(mail.outbox[0])
        assert mail.outbox[0].attachments == []

    def test_sin_empresa_sale_en_texto_plano(self):
        tareas.enviar_correo.delay("ana@ejemplo.example", "A", "T")
        assert mail.outbox[0].alternatives == []

    def test_escapa_el_texto_y_convierte_los_enlaces(self, empresa):
        texto = "Motivo: <script>alert(1)</script>\n\nAbre:\nhttps://web.example/c?a=1&b=2.\nFin"
        html = correo_marca.html_del_correo(empresa, texto, con_logo=False)
        assert "<script>" not in html and "&lt;script&gt;" in html
        assert 'href="https://web.example/c?a=1&amp;b=2"' in html
        assert "</a>.<br>Fin" in html

    def test_al_confirmar_pasa_la_empresa(self, empresa, django_capture_on_commit_callbacks):
        envio = mock.patch.object(tareas.enviar_correo, "delay")
        with envio as encolado, django_capture_on_commit_callbacks(execute=True):
            tareas.al_confirmar_correo("ana@ejemplo.example", "A", "T", empresa.pk)
        encolado.assert_called_once_with("ana@ejemplo.example", "A", "T", empresa.pk)
