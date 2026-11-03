"""Carga inicial de vehículos por CSV (HU-10, CP-01)."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import Auditoria, Entidad
from apps.flota import importacion
from apps.flota.models import Vehiculo
from apps.reservas.tests.fabricas import VehiculoFactory

IMPORTAR = reverse("vehiculo-importar")
ANIO = timezone.localdate().year - 1


def csv(texto: str, codificacion="utf-8") -> SimpleUploadedFile:
    return SimpleUploadedFile("flota.csv", texto.encode(codificacion), content_type="text/csv")


def enviar(api, texto, confirmar=False, **kwargs):
    return api.post(IMPORTAR, {"archivo": csv(texto, **kwargs), "confirmar": confirmar}, format="multipart")


@pytest.fixture
def api(cliente, administrador):
    cliente.force_authenticate(administrador)
    return cliente


VALIDO = f"patente,marca_modelo,anio,capacidad\nBCDF10,Toyota Yaris,{ANIO},4\ngh-jk 20,Hyundai H-1,{ANIO},7\n"


@pytest.mark.django_db
class TestImportar:
    def test_sin_confirmar_solo_informa(self, api):
        respuesta = enviar(api, VALIDO)
        assert respuesta.status_code == 200
        informe = respuesta.json()
        assert (informe["validas"], informe["con_errores"], informe["creados"]) == (2, 0, 0)
        assert [f["linea"] for f in informe["filas"]] == [2, 3]
        assert Vehiculo.objects.count() == 0

    def test_confirmar_crea_todo_en_la_empresa_y_audita(self, api, empresa):
        respuesta = enviar(api, VALIDO, confirmar=True)
        assert respuesta.status_code == 201
        assert respuesta.json()["creados"] == 2
        assert set(Vehiculo.objects.filter(empresa=empresa).values_list("patente", "capacidad")) == {
            ("BCDF10", 4),
            ("GHJK20", 7),
        }
        assert Auditoria.objects.filter(entidad=Entidad.VEHICULO, accion="CREAR").count() == 2

    def test_todo_o_nada(self, api, otra_empresa):
        VehiculoFactory(empresa=otra_empresa, patente="BCDF10")
        texto = VALIDO + f"KLPR30,Kia Rio,1990,4\nGHJK20,Kia Rio,{ANIO},4\n"
        respuesta = enviar(api, texto, confirmar=True)
        assert respuesta.status_code == 400
        informe = respuesta.json()
        assert (informe["validas"], informe["con_errores"], informe["creados"]) == (1, 3, 0)
        errores = {f["linea"]: f["errores"] for f in informe["filas"]}
        assert errores[2] == {"patente": ["Esta patente ya está registrada."]}
        assert errores[3] == {}
        assert list(errores[4]) == ["anio"]
        assert errores[5] == {"patente": ["Repetida en el archivo (línea 3)."]}
        assert Vehiculo.objects.count() == 1

    def test_excel_en_espanol(self, api):
        """Punto y coma, Windows-1252, encabezados con tilde y mayúsculas, sin capacidad y líneas vacías."""
        texto = f"Patente;Marca y modelo;Año\r\nBCDF10;Peugeot 301;{ANIO}\r\n;;\r\n"
        informe = enviar(api, texto, codificacion="cp1252").json()
        assert informe["validas"] == 1
        assert informe["filas"][0]["datos"] == {
            "patente": "BCDF10",
            "marca_modelo": "Peugeot 301",
            "anio": str(ANIO),
        }

    def test_utf8_con_bom(self, api):
        assert enviar(api, "﻿" + VALIDO).json()["validas"] == 2

    @pytest.mark.parametrize(
        ("texto", "mensaje"),
        [
            ("", "vac"),  # Lo rechaza el FileField de DRF.
            ("patente,marca_modelo,anio\n", "solo el encabezado"),
            ("patente,anio\nBCDF10,2020\n", "Faltan columnas: marca_modelo"),
        ],
    )
    def test_archivo_que_no_sirve(self, api, texto, mensaje):
        respuesta = enviar(api, texto)
        assert respuesta.status_code == 400
        assert mensaje in respuesta.json()["archivo"][0]

    def test_limite_de_filas(self, api, monkeypatch):
        monkeypatch.setattr(importacion, "MAX_FILAS", 1)
        assert "más de 1" in enviar(api, VALIDO).json()["archivo"][0]

    def test_limite_de_tamano(self, api, monkeypatch):
        monkeypatch.setattr(importacion, "MAX_BYTES", 10)
        assert "1 MB" in enviar(api, VALIDO).json()["archivo"][0]

    def test_sin_archivo(self, api):
        assert "archivo" in api.post(IMPORTAR, {}, format="multipart").json()

    def test_solo_administrador(self, cliente, despachador):
        cliente.force_authenticate(despachador)
        assert enviar(cliente, VALIDO).status_code == 403
