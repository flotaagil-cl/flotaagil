"""Manejador de errores global: todo error con solo `detail` lleva además `code`."""

import pytest
from django.urls import reverse

from apps.reservas.models import EstadoViaje
from apps.reservas.tests.fabricas import ViajeFactory


@pytest.mark.django_db
class TestCodigoEnTodaLaApi:
    def test_401_403_404_405_409(self, cliente, empresa, despachador, conductor):
        assert cliente.get(reverse("viaje-list")).json()["code"] == "not_authenticated"
        cliente.force_authenticate(conductor)
        assert cliente.get(reverse("viaje-list")).json()["code"] == "permission_denied"
        cliente.force_authenticate(despachador)
        assert cliente.get(reverse("viaje-detail", args=[999999])).json()["code"] == "not_found"
        viaje = ViajeFactory(empresa=empresa, estado=EstadoViaje.FINALIZADO)
        assert cliente.delete(reverse("viaje-detail", args=[viaje.pk])).json()["code"] == "method_not_allowed"
        conflicto = cliente.post(reverse("viaje-cancelar", args=[viaje.pk]), {"motivo": "x"}, format="json")
        assert (conflicto.status_code, conflicto.json()["code"]) == (409, "conflicto_estado")

    def test_los_400_de_validacion_no_cambian(self, cliente, despachador):
        cliente.force_authenticate(despachador)
        cuerpo = cliente.post(reverse("viaje-list"), {}, format="json").json()
        assert "code" not in cuerpo
        assert "origen_dir" in cuerpo
