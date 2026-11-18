"""Fixtures compartidos de las reservas.

Desde CC-19 (HU-67) no hay cliente de WhatsApp. El fixture `twilio` queda como guarda de CP-57: `enviados`
lista los mensajes salientes de WhatsApp registrados durante la prueba, que deben ser cero.
"""

import pytest
from django.utils import timezone

from apps.flota.models import ConductorVehiculo, EstadoConductor
from apps.reservas.models import DireccionMensaje, MensajeWhatsapp
from apps.reservas.tests.fabricas import ConductorFactory, PasajeroFactory, VehiculoFactory


class SinWhatsapp:
    def __init__(self):
        self.antes = set(MensajeWhatsapp.objects.values_list("pk", flat=True))

    @property
    def enviados(self) -> list[dict]:
        nuevos = MensajeWhatsapp.objects.filter(direccion=DireccionMensaje.SALIENTE).exclude(
            pk__in=self.antes
        )
        return list(nuevos.values("pk", "cuerpo"))


@pytest.fixture
def twilio(db):
    return SinWhatsapp()


@pytest.fixture
def twilio_avisos(twilio):
    return twilio


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
