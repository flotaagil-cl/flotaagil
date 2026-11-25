"""CC-27 (HU-77, DC-83 y DC-84): paleta y logo por empresa (CP-71)."""

import io

import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image, ImageDraw

from apps.auditoria.models import Auditoria
from apps.cuentas import logos
from apps.cuentas.models import Empresa, Modulo
from apps.cuentas.paletas import PALETAS, PREDETERMINADA, paleta_de
from apps.cuentas.tests.fabricas import UsuarioFactory

pytestmark = pytest.mark.django_db

URL = reverse("apariencia")
SIN_CAMBIOS = {"paleta": "tiffany", "logo": None, "nombre_marca": "", "iniciales": ""}
URL_LOGO = reverse("apariencia-logo")


@pytest.fixture
def admin(panel, administrador):
    panel.force_authenticate(administrador)
    return panel


def imagen(ancho=600, alto=300, formato="PNG", modo="RGBA", fondo=(0, 0, 0, 0), caja=None, **guardar):
    """Imagen sintética: un rectángulo de color sobre un fondo con márgenes."""
    lienzo = Image.new(modo, (ancho, alto), fondo if modo == "RGBA" else fondo[:3])
    ImageDraw.Draw(lienzo).rectangle(
        caja or (ancho // 4, alto // 4, ancho * 3 // 4, alto * 3 // 4), fill=(20, 80, 160)
    )
    salida = io.BytesIO()
    lienzo.save(salida, format=formato, **guardar)
    return salida.getvalue()


def subir(cliente, contenido, nombre="logo.png"):
    return cliente.post(URL_LOGO, {"logo": SimpleUploadedFile(nombre, contenido)}, format="multipart")


# --- Contraste (WCAG 2.x) ------------------------------------------------------------------------


def _luminancia(color: str) -> float:
    canales = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contraste(a: str, b: str) -> float:
    claro, oscuro = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (claro + 0.05) / (oscuro + 0.05)


@pytest.mark.parametrize("paleta", list(PALETAS.values()), ids=list(PALETAS))
def test_contraste_de_todas_las_paletas(paleta):
    assert _contraste("#ffffff", paleta.oscuro) >= 4.5, "texto blanco sobre el oscuro"
    assert _contraste("#ffffff", paleta.medio) >= 4.5, "texto blanco sobre el medio"
    assert _contraste(paleta.oscuro, paleta.claro) >= 4.5, "oscuro sobre el fondo claro"
    assert _contraste(paleta.medio, "#ffffff") >= 3, "medio sobre blanco"


def test_catalogo_fijo_de_diez_con_tiffany_predeterminada(empresa):
    assert len(PALETAS) == 10 and PREDETERMINADA == "tiffany"
    assert empresa.paleta == "tiffany" and empresa.logo is None
    assert paleta_de("no-existe").clave == "tiffany"


# --- Lectura, paleta y permisos ------------------------------------------------------------------


def test_cambia_la_paleta_con_auditoria_y_restablece(admin, administrador, empresa):
    assert admin.get(URL).json() == SIN_CAMBIOS
    assert admin.patch(URL, {"paleta": "indigo"}, format="json").json()["paleta"] == "indigo"
    admin.patch(URL, {"paleta": "indigo"}, format="json")  # sin cambio no se audita
    registro = Auditoria.objects.get(accion="EDITAR_APARIENCIA")
    assert (registro.usuario, registro.entidad, registro.entidad_id) == (administrador, "EMPRESA", empresa.pk)
    assert registro.datos_previos == {"paleta": "tiffany"}
    assert admin.patch(URL, {"paleta": "tiffany"}, format="json").json()["paleta"] == "tiffany"


@pytest.mark.parametrize("valor", ["#ff0000", "rojo", ""])
def test_solo_paletas_del_catalogo(admin, valor):
    assert admin.patch(URL, {"paleta": valor}, format="json").status_code == 400


@pytest.mark.parametrize("rol", ["DESPACHADOR", "CONDUCTOR", "PASAJERO", "CONVENIO"])
def test_solo_el_administrador_aunque_tenga_todos_los_modulos(panel, empresa, rol):
    usuario = UsuarioFactory(empresa=empresa, rol=rol)
    if rol == "DESPACHADOR":
        usuario.modulos = list(Modulo.values)
        usuario.save()
    panel.force_authenticate(usuario)
    for respuesta in (
        panel.get(URL),
        panel.patch(URL, {"paleta": "indigo"}, format="json"),
        subir(panel, imagen()),
        panel.delete(URL_LOGO),
    ):
        assert respuesta.status_code == 403
    assert Empresa.objects.get(pk=empresa.pk).paleta == "tiffany"


def test_apariencia_no_es_un_modulo_asignable():
    assert not any("APARIENCIA" in valor.upper() for valor in Modulo.values)


def test_cada_administrador_cambia_solo_su_empresa(admin, otra_empresa):
    admin.patch(URL, {"paleta": "violeta"}, format="json")
    assert Empresa.objects.get(pk=otra_empresa.pk).paleta == "tiffany"


# --- Logo ----------------------------------------------------------------------------------------


def _abrir(carpeta, nombre):
    with default_storage.open(logos.ruta(carpeta, nombre)) as archivo:
        resultado = Image.open(io.BytesIO(archivo.read()))
        resultado.load()
    return resultado


def test_sube_recorta_y_genera_las_versiones_en_png(admin, empresa, django_capture_on_commit_callbacks):
    respuesta = subir(admin, imagen(800, 400))
    assert respuesta.status_code == 200, respuesta.data
    empresa.refresh_from_db()
    assert set(respuesta.json()["logo"]) == set(logos.VARIANTES)
    original = _abrir(empresa.logo, "original")
    assert original.size == (401, 201)  # sin los márgenes transparentes
    for variante, medidas in logos.VARIANTES.items():
        version = _abrir(empresa.logo, variante)
        assert (version.format, version.size) == ("PNG", medidas)
    assert Auditoria.objects.get(accion="EDITAR_APARIENCIA").datos_previos == {"logo": None}


def test_quita_metadatos_corrige_orientacion_y_recorta_el_blanco(admin, empresa):
    exif = Image.Exif()
    exif[0x0112] = 6  # rotar 90°
    exif[0x010F] = "Cámara Sintética"
    # 600x900 con fondo blanco: al enderezar queda 900x600.
    contenido = imagen(
        600, 900, formato="JPEG", modo="RGB", fondo=(255, 255, 255), exif=exif.tobytes(), quality=95
    )
    assert subir(admin, contenido, "foto.jpg").status_code == 200
    empresa.refresh_from_db()
    original = _abrir(empresa.logo, "original")
    assert original.width > original.height and original.width < 900
    assert not original.getexif() and "exif" not in original.info


@pytest.mark.parametrize("formato", ["PNG", "JPEG", "WEBP"])
def test_acepta_png_jpg_y_webp(admin, formato):
    modo = "RGB" if formato == "JPEG" else "RGBA"
    assert subir(admin, imagen(formato=formato, modo=modo)).status_code == 200


@pytest.mark.parametrize(
    ("contenido", "nombre", "mensaje"),
    [
        (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="200"></svg>',
            "logo.svg",
            "PNG, JPG o WebP",
        ),
        (b"esto no es una imagen", "logo.png", "no es una imagen"),
        (imagen(formato="GIF", modo="RGB"), "logo.png", "PNG, JPG o WebP"),
        (imagen(200, 100), "logo.png", "al menos 256 px de ancho (mide 200 px)"),
        (b"\x89PNG" + b"0" * (2 * 1024 * 1024), "logo.png", "más de 2 MB"),
        (imagen(600, 300, caja=(0, 0, 0, 0), fondo=(0, 0, 0, 0))[:200], "logo.png", "no es una imagen"),
    ],
    ids=["svg", "texto", "gif", "angosta", "pesada", "truncada"],
)
def test_rechazos_con_mensaje_claro(admin, empresa, contenido, nombre, mensaje):
    respuesta = subir(admin, contenido, nombre)
    assert respuesta.status_code == 400
    assert mensaje in str(respuesta.data["logo"][0])
    empresa.refresh_from_db()
    assert empresa.logo is None and not Auditoria.objects.filter(accion="EDITAR_APARIENCIA").exists()


def test_demasiados_pixeles(admin, monkeypatch):
    monkeypatch.setattr(logos, "MAXIMO_PIXELES", 1000)
    assert "demasiados píxeles" in str(subir(admin, imagen()).data["logo"][0])


def test_imagen_vacia(admin):
    vacia = io.BytesIO()
    Image.new("RGBA", (600, 300), (0, 0, 0, 0)).save(vacia, format="PNG")
    assert "vacía" in str(subir(admin, vacia.getvalue()).data["logo"][0])


def test_sin_archivo(admin):
    assert admin.post(URL_LOGO, {}, format="multipart").status_code == 400


def test_al_reemplazar_o_quitar_se_borran_los_archivos(admin, empresa, django_capture_on_commit_callbacks):
    subir(admin, imagen())
    empresa.refresh_from_db()
    primera = empresa.logo
    with django_capture_on_commit_callbacks(execute=True):
        subir(admin, imagen(700, 300))
    empresa.refresh_from_db()
    assert empresa.logo != primera
    assert not any(default_storage.exists(logos.ruta(primera, n)) for n in logos.ARCHIVOS)
    segunda = empresa.logo
    with django_capture_on_commit_callbacks(execute=True):
        assert admin.delete(URL_LOGO).json()["logo"] is None
    assert not any(default_storage.exists(logos.ruta(segunda, n)) for n in logos.ARCHIVOS)
    admin.delete(URL_LOGO)  # sin logo no se audita
    assert Auditoria.objects.filter(accion="EDITAR_APARIENCIA").count() == 3


def test_si_falla_el_almacenamiento_no_quedan_archivos(monkeypatch):
    guardadas = []
    real = default_storage.save

    def falla_en_la_tercera(nombre, contenido):
        if len(guardadas) == 2:
            raise OSError("disco lleno")
        guardadas.append(nombre)
        return real(nombre, contenido)

    monkeypatch.setattr(default_storage, "save", falla_en_la_tercera)
    with pytest.raises(OSError):
        logos.guardar(1, logos.procesar(imagen()))
    assert not any(default_storage.exists(nombre) for nombre in guardadas)


# --- Nombre de marca e iniciales (CC-21, DC-86, CP-75) -------------------------------------------


def test_guarda_nombre_e_iniciales_normalizados_y_audita_solo_lo_que_cambia(admin, cliente, empresa):
    entrada = {"nombre_marca": "  Andes   Traslados ", "iniciales": "añ1"}
    datos = admin.patch(URL, entrada, format="json").json()
    assert (datos["nombre_marca"], datos["iniciales"], datos["paleta"]) == (
        "Andes Traslados",
        "AÑ1",
        "tiffany",
    )
    registro = Auditoria.objects.get(accion="EDITAR_APARIENCIA")
    assert registro.datos_previos == {"nombre_marca": "", "iniciales": ""}
    admin.patch(URL, {"nombre_marca": "Andes Traslados", "paleta": "cian"}, format="json")
    ultimo = Auditoria.objects.filter(accion="EDITAR_APARIENCIA").order_by("pk").last()
    assert ultimo.datos_previos == {"paleta": "tiffany"}
    cliente.force_authenticate(None)
    publica = cliente.get(reverse("apariencia-publica", args=[empresa.slug])).json()
    assert (publica["nombre_marca"], publica["iniciales"]) == ("Andes Traslados", "AÑ1")


def test_vaciarlos_vuelve_a_lo_anterior(admin):
    admin.patch(URL, {"nombre_marca": "Andes", "iniciales": "TA"}, format="json")
    assert admin.patch(URL, {"nombre_marca": "", "iniciales": ""}, format="json").json() == SIN_CAMBIOS


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("nombre_marca", "x" * 31),
        ("nombre_marca", "Andes\r\nBcc: otro@ejemplo.example"),
        ("nombre_marca", "Andes\u2028Traslados"),
        ("iniciales", "ABCD"),
        ("iniciales", "A B"),
        ("iniciales", "A."),
        ("iniciales", "ßßs"),
    ],
)
def test_rechaza_nombres_e_iniciales_no_validos(admin, empresa, campo, valor):
    respuesta = admin.patch(URL, {campo: valor}, format="json")
    assert respuesta.status_code == 400 and campo in respuesta.json()
    empresa.refresh_from_db()
    assert getattr(empresa, campo) == ""


# --- Endpoint público y sesión -------------------------------------------------------------------


def test_publico_solo_paleta_y_logo_y_sirve_el_png(admin, cliente, empresa):
    subir(admin, imagen())
    admin.patch(URL, {"paleta": "cian"}, format="json")
    cliente.force_authenticate(None)
    datos = cliente.get(reverse("apariencia-publica", args=[empresa.slug])).json()
    assert set(datos) == set(SIN_CAMBIOS) and datos["paleta"] == "cian"
    respuesta = cliente.get(datos["logo"]["portal"])
    assert respuesta.status_code == 200 and respuesta["Content-Type"] == "image/png"
    assert "immutable" in respuesta["Cache-Control"]
    assert b"".join(respuesta.streaming_content).startswith(b"\x89PNG")


def test_publico_404_para_empresa_inactiva_version_vieja_o_variante_ajena(admin, cliente, empresa):
    subir(admin, imagen())
    empresa.refresh_from_db()
    version = empresa.logo.rsplit("/", 1)[-1]
    ruta = lambda v, n: reverse("apariencia-logo-publico", args=[empresa.slug, v, n])  # noqa: E731
    assert cliente.get(ruta(version, "original")).status_code == 404  # el original no se publica
    assert cliente.get(ruta("0" * 32, "portal")).status_code == 404
    assert cliente.get(reverse("apariencia-publica", args=["no-existe"])).status_code == 404
    Empresa.objects.filter(pk=empresa.pk).update(activa=False)
    assert cliente.get(reverse("apariencia-publica", args=[empresa.slug])).status_code == 404


def test_la_sesion_trae_la_apariencia_de_su_empresa(empresa):
    from apps.cuentas.serializers import EmpresaResumenSerializer

    assert EmpresaResumenSerializer(empresa).data["apariencia"] == SIN_CAMBIOS


def test_datos_demo_deja_dos_apariencias_sin_pisar_los_cambios(settings, django_capture_on_commit_callbacks):
    settings.DEBUG = True
    from django.core.management import call_command

    call_command("datos_demo", password="clave-demo-123")
    andes = Empresa.objects.get(slug="transportes-andes")
    taxi = Empresa.objects.get(slug="taxi-pacifico")
    assert (andes.paleta, bool(andes.logo)) == ("indigo", True)
    assert (taxi.paleta, taxi.logo) == ("tiffany", None)
    assert (andes.nombre_marca, andes.iniciales) == ("Andes Demo", "")
    assert (taxi.nombre_marca, taxi.iniciales) == ("", "TP")
    assert default_storage.exists(logos.ruta(andes.logo, "portal"))
    # Si el administrador ya la cambió, volver a cargar los datos no la pisa.
    Empresa.objects.filter(pk=andes.pk).update(paleta="grafito")
    call_command("datos_demo", password="clave-demo-123")
    assert Empresa.objects.get(pk=andes.pk).paleta == "grafito"
