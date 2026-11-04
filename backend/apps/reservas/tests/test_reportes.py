"""HU-06 · Reportes operativos y exportación CSV. CP-25."""

import csv
import io
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad
from apps.reservas.models import (
    Calificacion,
    Canal,
    EstadoViaje,
    MetodoPago,
    OrigenCancelacion,
    PagoViaje,
    Viaje,
)
from apps.reservas.reportes import _texto_csv
from apps.reservas.tests.fabricas import ConductorFactory, ConvenioFactory, ViajeFactory

E = EstadoViaje
HOY = timezone.localdate


def ruta(tipo, sufijo=""):
    return reverse(f"reporte{sufijo}", args=[tipo])


def periodo(hace=0):
    dia = (HOY() - timedelta(days=hace)).isoformat()
    return {"desde": dia, "hasta": dia}


def pedir(api, tipo, **filtros):
    respuesta = api.get(ruta(tipo), {**periodo(), **filtros})
    assert respuesta.status_code == 200, respuesta.content
    return respuesta.json()


def leer_csv(respuesta):
    return list(csv.reader(io.StringIO(respuesta.content.decode("utf-8-sig"), newline=""), delimiter=";"))


def finalizado(empresa, conductor=None, *, metodo=MetodoPago.EFECTIVO, monto=10000, hace=0, **cambios):
    viaje = ViajeFactory(empresa=empresa, conductor=conductor, estado=E.FINALIZADO, **cambios)
    pago = PagoViaje.objects.create(viaje=viaje, metodo=metodo, monto=monto)
    if hace:
        PagoViaje.objects.filter(pk=pago.pk).update(registrado_en=timezone.now() - timedelta(days=hace))
    return viaje


def forzar(viaje, usuario, accion="CIERRE_FORZADO"):
    auditoria.registrar(
        usuario=usuario, entidad=Entidad.VIAJE, entidad_id=viaje.pk, accion=accion, motivo="Sin señal"
    )


def cancelada(empresa, origen=OrigenCancelacion.PASAJERO, **cambios):
    return ViajeFactory(
        empresa=empresa,
        estado=E.CANCELADO,
        motivo_cancelacion="Sintético",
        origen_cancelacion=origen,
        recogida_en=timezone.now(),
        **cambios,
    )


@pytest.fixture
def api(cliente, administrador):
    cliente.force_authenticate(administrador)
    return cliente


@pytest.fixture
def ana(empresa):
    return ConductorFactory(usuario__empresa=empresa, usuario__nombre="Ana Conductora")


@pytest.fixture
def beto(empresa):
    return ConductorFactory(usuario__empresa=empresa, usuario__nombre="Beto Conductor")


@pytest.mark.django_db
class TestLiquidacion:
    def test_por_dia_y_conductor_con_desglose_y_totales(self, api, empresa, ana, beto):
        finalizado(empresa, ana, monto=10000)
        finalizado(empresa, ana, metodo=MetodoPago.TARJETA, monto=7000)
        finalizado(empresa, beto, metodo=MetodoPago.TRANSFERENCIA, monto=5000)
        datos = pedir(api, "liquidacion")
        assert [f["conductor"] for f in datos["filas"]] == ["Ana Conductora", "Beto Conductor"]
        fila = datos["filas"][0]
        assert fila["dia"] == HOY().isoformat()
        assert (fila["viajes"], fila["efectivo"], fila["tarjeta"], fila["total"]) == (2, 10000, 7000, 17000)
        assert (datos["totales"]["viajes"], datos["totales"]["total"]) == (3, 22000)
        assert datos["totales"]["transferencia"] == 5000

    def test_incluye_los_cierres_forzados_identificados(self, api, empresa, ana, administrador):
        """Decisión del PO."""
        finalizado(empresa, ana, monto=10000)
        forzar(finalizado(empresa, ana, monto=3000), administrador)
        fila = pedir(api, "liquidacion")["filas"][0]
        assert (fila["viajes"], fila["total"]) == (2, 13000)
        assert (fila["cierres_forzados"], fila["monto_cierres_forzados"]) == (1, 3000)

    def test_una_fila_por_dia(self, api, empresa, ana):
        finalizado(empresa, ana, monto=1000, hace=2)
        finalizado(empresa, ana, monto=2000, hace=1)
        filtros = {"desde": (HOY() - timedelta(days=2)).isoformat(), "hasta": HOY().isoformat()}
        filas = pedir(api, "liquidacion", **filtros)["filas"]
        assert [f["total"] for f in filas] == [1000, 2000]

    def test_fuera_del_periodo_no_cuenta(self, api, empresa, ana):
        finalizado(empresa, ana, hace=3)
        assert pedir(api, "liquidacion")["filas"] == []

    def test_solo_finalizados(self, api, empresa, ana):
        viaje = finalizado(empresa, ana)
        Viaje.objects.filter(pk=viaje.pk).update(estado=E.PASAJERO_A_BORDO)
        assert pedir(api, "liquidacion")["filas"] == []

    def test_filtra_por_conductor(self, api, empresa, ana, beto):
        finalizado(empresa, ana)
        finalizado(empresa, beto, monto=5000)
        datos = pedir(api, "liquidacion", conductor=beto.pk)
        assert [f["conductor"] for f in datos["filas"]] == ["Beto Conductor"]
        assert datos["totales"]["total"] == 5000


@pytest.mark.django_db
class TestFacturacion:
    def test_por_convenio_con_desglose(self, api, empresa, ana):
        uno = ConvenioFactory(empresa=empresa, cliente_nombre="Minera Norte", cliente_rut="76543210-3")
        otro = ConvenioFactory(empresa=empresa, cliente_nombre="Banco Sur")
        finalizado(empresa, ana, metodo=MetodoPago.CONVENIO, monto=9000, canal=Canal.CONVENIO, convenio=uno)
        finalizado(empresa, ana, monto=1000, canal=Canal.CONVENIO, convenio=uno)
        finalizado(empresa, ana, metodo=MetodoPago.CONVENIO, monto=4000, canal=Canal.CONVENIO, convenio=otro)
        finalizado(empresa, ana, monto=500)  # Sin convenio: no se factura.
        datos = pedir(api, "facturacion")
        assert [f["cliente"] for f in datos["filas"]] == ["Banco Sur", "Minera Norte"]
        fila = datos["filas"][1]
        assert (fila["rut"], fila["cliente"]) == ("76543210-3", "Minera Norte")
        assert (fila["viajes"], fila["convenio"], fila["total"]) == (2, 9000, 10000)
        assert fila["efectivo"] == 1000
        assert datos["totales"]["total"] == 14000

    def test_el_metodo_convenio_no_pisa_el_nombre(self, api, empresa, ana):
        """La columna del método y la del cliente se llaman igual."""
        convenio = ConvenioFactory(empresa=empresa, cliente_nombre="Minera Norte")
        finalizado(
            empresa, ana, metodo=MetodoPago.CONVENIO, monto=9000, canal=Canal.CONVENIO, convenio=convenio
        )
        datos = pedir(api, "facturacion")
        claves = [c["clave"] for c in datos["columnas"]]
        assert len(claves) == len(set(claves))

    def test_filtra_por_convenio(self, api, empresa, ana):
        uno = ConvenioFactory(empresa=empresa, cliente_nombre="Minera Norte")
        otro = ConvenioFactory(empresa=empresa, cliente_nombre="Banco Sur")
        finalizado(empresa, ana, canal=Canal.CONVENIO, convenio=uno)
        finalizado(empresa, ana, canal=Canal.CONVENIO, convenio=otro)
        assert [f["cliente"] for f in pedir(api, "facturacion", convenio=otro.pk)["filas"]] == ["Banco Sur"]


@pytest.mark.django_db
class TestCancelaciones:
    def test_tasa_por_origen(self, api, empresa):
        cancelada(empresa, OrigenCancelacion.PASAJERO)
        cancelada(empresa, OrigenCancelacion.PASAJERO)
        cancelada(empresa, OrigenCancelacion.DESPACHADOR)
        for _ in range(5):
            ViajeFactory(empresa=empresa, recogida_en=timezone.now())
        datos = pedir(api, "cancelaciones")
        filas = {f["origen"]: (f["cantidad"], f["tasa"]) for f in datos["filas"]}
        assert filas["Pasajero"] == (2, 25.0)
        assert filas["Despachador"] == (1, 12.5)
        assert filas["Administrador"] == (0, 0.0)
        assert (datos["totales"]["cantidad"], datos["totales"]["tasa"]) == (3, 37.5)
        assert "8 reservas" in datos["totales"]["origen"]

    def test_sin_reservas_no_divide_por_cero(self, api):
        assert pedir(api, "cancelaciones")["totales"]["tasa"] == 0.0


@pytest.mark.django_db
class TestHistorial:
    def test_con_pago_forzado_y_calificacion(self, api, empresa, ana, administrador):
        viaje = finalizado(empresa, ana, metodo=MetodoPago.TARJETA, monto=8000, recogida_en=timezone.now())
        forzar(viaje, administrador)
        Calificacion.objects.create(viaje=viaje, puntaje=5)
        anulado = cancelada(empresa, OrigenCancelacion.DESPACHADOR)
        forzar(anulado, administrador, "ANULACION_FORZADA")
        filas = {f["id"]: f for f in pedir(api, "historial")["filas"]}
        fila = filas[viaje.pk]
        assert (fila["estado"], fila["conductor"], fila["metodo"], fila["monto"]) == (
            "Finalizado",
            "Ana Conductora",
            "Tarjeta",
            8000,
        )
        assert (fila["forzado"], fila["calificacion"]) == ("Cierre forzado", 5)  # HU-24
        assert (filas[anulado.pk]["forzado"], filas[anulado.pk]["monto"]) == ("Anulación forzada", None)

    def test_pagina_con_totales_del_periodo(self, api, empresa, ana):
        for _ in range(26):
            finalizado(empresa, ana, monto=100, recogida_en=timezone.now())
        datos = pedir(api, "historial")
        assert (len(datos["filas"]), datos["count"]) == (25, 26)
        assert datos["next"]
        assert datos["totales"] == {"id": 26, "monto": 2600}
        assert len(pedir(api, "historial", page=2)["filas"]) == 1


@pytest.mark.django_db
class TestCsv:
    def test_mismas_columnas_filas_y_totales(self, api, empresa, ana, administrador):
        finalizado(empresa, ana, monto=10000)
        forzar(finalizado(empresa, ana, monto=3000), administrador)
        respuesta = api.get(ruta("liquidacion", "-csv"), periodo())
        assert respuesta.status_code == 200
        assert respuesta["Content-Type"].startswith("text/csv")
        assert f"liquidacion-{HOY().isoformat()}" in respuesta["Content-Disposition"]
        filas = leer_csv(respuesta)
        assert filas[0][:3] == ["Día", "Conductor", "Viajes"]
        assert filas[0][-2:] == ["Cierres forzados", "Monto de cierres forzados"]
        assert filas[1][0] == HOY().strftime("%d-%m-%Y")
        assert filas[1][1:3] == ["Ana Conductora", "2"]
        assert filas[1][-2:] == ["1", "3000"]
        assert filas[-1][1] == "Total"
        assert len(filas) == 3

    def test_abre_en_excel_con_acentos(self, api, empresa, ana):
        finalizado(empresa, ana)
        contenido = api.get(ruta("liquidacion", "-csv"), periodo()).content
        assert contenido.startswith(b"\xef\xbb\xbf")
        assert "Día".encode() in contenido

    def test_el_historial_sale_completo_sin_paginar(self, api, empresa, ana):
        for _ in range(26):
            finalizado(empresa, ana, recogida_en=timezone.now())
        filas = leer_csv(api.get(ruta("historial", "-csv"), periodo()))
        assert len(filas) == 28  # Encabezado, 26 viajes y totales.
        assert filas[-1][0] == "26"

    def test_neutraliza_formulas(self, api, empresa, ana):
        """Un dato escrito por un tercero no debe ejecutarse al abrir el archivo."""
        viaje = finalizado(empresa, ana, recogida_en=timezone.now())
        viaje.pasajero.nombre = '=HYPERLINK("http://x.example")'
        viaje.pasajero.save()
        filas = leer_csv(api.get(ruta("historial", "-csv"), periodo()))
        assert filas[1][3].startswith("'=")

    @pytest.mark.parametrize(
        ("valor", "tipo", "esperado"),
        [
            (None, "texto", ""),
            ("Ana", "texto", "Ana"),
            ("+569", "texto", "'+569"),
            ("-1", "texto", "'-1"),
            ("@x", "texto", "'@x"),
            (12.5, "porcentaje", "12,5"),
            (15000, "pesos", "15000"),
        ],
    )
    def test_texto(self, valor, tipo, esperado):
        assert _texto_csv(valor, tipo) == esperado

    def test_respeta_los_filtros(self, api, empresa, ana, beto):
        finalizado(empresa, ana)
        finalizado(empresa, beto)
        filas = leer_csv(api.get(ruta("liquidacion", "-csv"), {**periodo(), "conductor": beto.pk}))
        assert [f[1] for f in filas[1:]] == ["Beto Conductor", "Total"]


@pytest.mark.django_db
class TestAcceso:
    @pytest.mark.parametrize("tipo", ["liquidacion", "facturacion", "cancelaciones", "historial"])
    def test_otra_empresa_no_aparece(self, api, otra_empresa, tipo):
        """RN-13."""
        ajeno = ConductorFactory(usuario__empresa=otra_empresa)
        convenio = ConvenioFactory(empresa=otra_empresa)
        finalizado(otra_empresa, ajeno, canal=Canal.CONVENIO, convenio=convenio, recogida_en=timezone.now())
        cancelada(otra_empresa)
        for filtros in ({}, {"conductor": ajeno.pk}, {"convenio": convenio.pk}):
            datos = pedir(api, tipo, **filtros)
            assert [f for f in datos["filas"] if f.get("cantidad", 1)] == []

    def test_opciones_solo_de_su_empresa(self, api, empresa, ana, otra_empresa):
        ConductorFactory(usuario__empresa=otra_empresa)
        ConvenioFactory(empresa=otra_empresa)
        convenio = ConvenioFactory(empresa=empresa, cliente_nombre="Minera Norte")
        datos = api.get(reverse("reporte-opciones")).json()
        assert datos["conductores"] == [{"id": ana.pk, "nombre": "Ana Conductora"}]
        assert datos["convenios"] == [{"id": convenio.pk, "nombre": "Minera Norte"}]

    @pytest.mark.parametrize("sufijo", ["", "-csv"])
    def test_solo_el_administrador(self, cliente, despachador, conductor, sufijo):
        assert cliente.get(ruta("liquidacion", sufijo)).status_code == 401
        cliente.force_authenticate(despachador)
        assert cliente.get(ruta("liquidacion", sufijo)).status_code == 403
        cliente.force_authenticate(conductor)
        assert cliente.get(ruta("liquidacion", sufijo)).status_code == 403

    def test_despachador_sin_opciones(self, cliente, despachador):
        cliente.force_authenticate(despachador)
        assert cliente.get(reverse("reporte-opciones")).status_code == 403

    @pytest.mark.parametrize("sufijo", ["", "-csv"])
    def test_tipo_desconocido_404(self, api, sufijo):
        assert api.get(ruta("otro", sufijo)).status_code == 404

    def test_sin_fechas_usa_hoy(self, api, empresa, ana):
        finalizado(empresa, ana)
        assert len(api.get(ruta("liquidacion")).json()["filas"]) == 1

    def test_fechas_invalidas(self, api):
        hoy = HOY()
        ayer = hoy - timedelta(days=1)
        respuesta = api.get(ruta("liquidacion"), {"desde": hoy.isoformat(), "hasta": ayer.isoformat()})
        assert respuesta.status_code == 400
        assert "desde" in respuesta.json()
        assert api.get(ruta("liquidacion"), {"desde": "no-es-fecha"}).status_code == 400
