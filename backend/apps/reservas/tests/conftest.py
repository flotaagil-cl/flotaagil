"""Fixtures compartidos de los avisos por WhatsApp (HU-21 y HU-24)."""

import pytest
from django.utils import timezone

from apps.flota.models import ConductorVehiculo, EstadoConductor
from apps.reservas import tareas
from apps.reservas.tests.fabricas import ConductorFactory, PasajeroFactory, VehiculoFactory
from apps.reservas.tests.test_whatsapp import TwilioFalso


@pytest.fixture
def twilio_avisos(monkeypatch):
    falso = TwilioFalso()
    monkeypatch.setattr(tareas, "obtener_notificador", lambda: falso)
    return falso


@pytest.fixture
def chofer_disponible(empresa):
    vehiculo = VehiculoFactory(empresa=empresa, patente="ABCD12", marca_modelo="Toyota Corolla")
    conductor = ConductorFactory(
        usuario__empresa=empresa,
        usuario__nombre="Muriel Moreno",
        estado=EstadoConductor.DISPONIBLE,
        vehiculo_activo=vehiculo,
        consentimiento_gps_en=timezone.now(),
    )
    ConductorVehiculo.objects.create(conductor=conductor, vehiculo=vehiculo)
    return conductor


@pytest.fixture
def pasajero(empresa):
    return PasajeroFactory(empresa=empresa, nombre="Ana Pérez", telefono="+56900009001")
