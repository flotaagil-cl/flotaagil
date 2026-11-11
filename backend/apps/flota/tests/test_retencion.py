"""RN-15 (DC-48): la purga diaria borra las posiciones GPS de más de 30 días y conserva las recientes."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.gis.geos import Point
from django.utils import timezone

from apps.flota import tareas
from apps.flota.models import PosicionGps
from apps.flota.retencion import limite, purgar_posiciones
from apps.reservas.tests.fabricas import ConductorFactory


def posicion(conductor, hace):
    return PosicionGps.objects.create(
        conductor=conductor,
        punto=Point(-70.65, -33.44, srid=4326),
        precision_m=5,
        registrada_en=timezone.now() - hace,
    )


@pytest.mark.django_db
class TestPurga:
    def test_borra_solo_las_anteriores_al_limite(self, empresa):
        conductor = ConductorFactory(usuario__empresa=empresa)
        vieja = posicion(conductor, timedelta(days=31))
        muy_vieja = posicion(conductor, timedelta(days=90))
        reciente = posicion(conductor, timedelta(days=29, hours=23))
        hoy = posicion(conductor, timedelta(minutes=1))
        assert purgar_posiciones() == 2
        quedan = set(PosicionGps.objects.values_list("pk", flat=True))
        assert quedan == {reciente.pk, hoy.pk}
        assert vieja.pk not in quedan and muy_vieja.pk not in quedan

    def test_borra_por_lotes(self, empresa):
        conductor = ConductorFactory(usuario__empresa=empresa)
        for minutos in range(7):
            posicion(conductor, timedelta(days=40, minutes=minutos))
        assert purgar_posiciones(lote=3) == 7
        assert not PosicionGps.objects.exists()

    def test_sin_nada_que_borrar(self):
        assert purgar_posiciones() == 0

    def test_el_limite_sale_de_la_configuracion(self, settings):
        ahora = timezone.now()
        settings.RETENCION_POSICIONES_DIAS = 10
        assert limite(ahora) == ahora - timedelta(days=10)

    def test_la_tarea_esta_programada_una_vez_al_dia(self, empresa):
        programa = settings.CELERY_BEAT_SCHEDULE["purgar-posiciones-rn15"]
        assert programa["task"] == "apps.flota.tareas.purgar_posiciones_gps"
        assert (programa["schedule"].hour, programa["schedule"].minute) == ({3}, {17})
        posicion(ConductorFactory(usuario__empresa=empresa), timedelta(days=45))
        assert tareas.purgar_posiciones_gps() == 1
