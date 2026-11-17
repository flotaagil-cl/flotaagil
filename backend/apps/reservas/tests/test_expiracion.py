"""RN-06 con CC-22 (HU-52, DC-53): las solicitudes vencidas quedan «Sin confirmar» y no se cancelan. CP-49."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import Auditoria
from apps.reservas import expiracion
from apps.reservas.models import EstadoViaje, HistorialEstado, Viaje

from .fabricas import ViajeFactory

E = EstadoViaje


def pendiente(empresa, minutos_atras: float = 0, confirmar_hasta=None):
    viaje = ViajeFactory(empresa=empresa, canal="WEB", estado=E.PENDIENTE_CONFIRMACION)
    Viaje.objects.filter(pk=viaje.pk).update(
        creado_en=timezone.now() - timedelta(minutes=minutos_atras), confirmar_hasta=confirmar_hasta
    )
    viaje.refresh_from_db()
    return viaje


@pytest.mark.django_db
class TestSinConfirmar:
    def test_no_se_cancelan_y_quedan_sin_confirmar(self, empresa):
        ahora = timezone.now()
        publica_vencida = pendiente(empresa, confirmar_hasta=ahora - timedelta(minutes=1))
        publica_vigente = pendiente(empresa, confirmar_hasta=ahora + timedelta(hours=3))
        anterior_vencida = pendiente(empresa, minutos_atras=16)  # 15 min por defecto (DC-02)
        anterior_vigente = pendiente(empresa, minutos_atras=5)
        assert set(expiracion.sin_confirmar()) == {publica_vencida, anterior_vencida}
        assert expiracion.expirar_pendientes() == 2
        assert not Viaje.objects.filter(estado=E.CANCELADO).exists()
        assert expiracion.es_sin_confirmar(publica_vencida) and not expiracion.es_sin_confirmar(
            publica_vigente
        )
        assert not expiracion.es_sin_confirmar(anterior_vigente)

    def test_plazo_anterior_configurable_por_empresa(self, empresa):
        empresa.configuracion.expiracion_verificacion_min = 60
        empresa.configuracion.save()
        assert not expiracion.sin_confirmar().filter(pk=pendiente(empresa, minutos_atras=30).pk).exists()

    def test_otros_estados_no_cuentan(self, empresa):
        ViajeFactory(empresa=empresa, estado=E.SOLICITADO)
        assert expiracion.expirar_pendientes() == 0


@pytest.mark.django_db
class TestPanel:
    def test_filtro_indicador_y_marca(self, panel, despachador, empresa):
        vencida = pendiente(empresa, confirmar_hasta=timezone.now() - timedelta(minutes=1))
        pendiente(empresa, confirmar_hasta=timezone.now() + timedelta(hours=3))
        panel.force_authenticate(despachador)
        lista = panel.get(reverse("viaje-list"), {"sin_confirmar": "true"}).data["results"]
        assert [v["id"] for v in lista] == [vencida.pk]
        assert lista[0]["sin_confirmar"] is True
        assert panel.get(reverse("indicadores")).data["sin_confirmar"] == 1

    def test_confirmar_por_telefono_queda_auditado(self, panel, despachador, empresa):
        viaje = pendiente(empresa, confirmar_hasta=timezone.now() - timedelta(minutes=1))
        panel.force_authenticate(despachador)
        respuesta = panel.post(reverse("viaje-confirmar-telefono", args=[viaje.pk]))
        assert respuesta.status_code == 200, respuesta.data
        assert respuesta.data["estado"] == E.SOLICITADO
        assert HistorialEstado.objects.filter(
            viaje=viaje, estado_nuevo=E.SOLICITADO, usuario=despachador
        ).exists()
        assert Auditoria.objects.filter(
            accion="CONFIRMAR_POR_TELEFONO", entidad_id=viaje.pk, usuario=despachador
        ).exists()
        assert panel.post(reverse("viaje-confirmar-telefono", args=[viaje.pk])).status_code == 409

    def test_conductor_no_confirma(self, panel, conductor, empresa):
        viaje = pendiente(empresa, confirmar_hasta=timezone.now() - timedelta(minutes=1))
        panel.force_authenticate(conductor)
        assert panel.post(reverse("viaje-confirmar-telefono", args=[viaje.pk])).status_code == 403


def test_comando(empresa, capsys):
    pendiente(empresa, minutos_atras=16)
    call_command("expirar_pendientes")
    assert "Solicitudes sin confirmar: 1" in capsys.readouterr().out
