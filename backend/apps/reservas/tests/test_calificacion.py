"""HU-24 · Calificación del servicio (RN-14). Desde CC-19 (HU-67) no hay encuesta por WhatsApp: el pasajero
califica en el portal o con la encuesta por correo (HU-56); aquí, el modelo y la ficha del panel."""

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework.test import APIClient

from apps.reservas.models import Calificacion, EstadoViaje
from apps.reservas.tests.fabricas import ViajeFactory

E = EstadoViaje


def finalizado(chofer, pasajero):
    return ViajeFactory(
        empresa=pasajero.empresa,
        pasajero=pasajero,
        conductor=chofer,
        vehiculo=chofer.vehiculo_activo,
        estado=E.FINALIZADO,
    )


def como(usuario):
    cliente = APIClient()
    cliente.force_authenticate(usuario)
    return cliente


@pytest.mark.django_db
class TestModeloYApi:
    def test_el_puntaje_fuera_de_rango_no_entra(self, chofer_disponible, pasajero):
        viaje = finalizado(chofer_disponible, pasajero)
        for puntaje in (0, 6):
            with pytest.raises(IntegrityError), transaction.atomic():
                Calificacion.objects.create(viaje=viaje, puntaje=puntaje)

    def test_ficha_del_panel(self, despachador, chofer_disponible, pasajero):
        viaje = finalizado(chofer_disponible, pasajero)
        ruta = reverse("viaje-detail", args=[viaje.pk])
        assert como(despachador).get(ruta).data["calificacion"] is None
        Calificacion.objects.create(viaje=viaje, puntaje=4)
        assert como(despachador).get(ruta).data["calificacion"] == 4
