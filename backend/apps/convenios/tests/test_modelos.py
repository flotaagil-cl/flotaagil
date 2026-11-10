"""HU-34: el modelo de convenio con estados (DC-35)."""

import pytest

from apps.convenios.models import EstadoConvenio
from apps.reservas.tests.fabricas import ConvenioFactory


@pytest.mark.django_db
def test_aprobado_por_defecto_y_vigente():
    convenio = ConvenioFactory()
    assert (convenio.estado, convenio.activo) == (EstadoConvenio.APROBADO, True)
    assert str(convenio) == convenio.cliente_nombre


@pytest.mark.django_db
@pytest.mark.parametrize("estado", [EstadoConvenio.EN_REVISION, EstadoConvenio.INACTIVO])
def test_solo_aprobado_es_vigente(estado):
    assert ConvenioFactory(estado=estado).activo is False
