import os

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.cuentas.tests.fabricas import EmpresaFactory, UsuarioFactory


@pytest.fixture(autouse=True)
def _cache_de_pruebas(settings):
    """Las pruebas usan otra base de Redis (15) para no borrar la caché del servidor de desarrollo.
    El throttling guarda contadores en la caché: cada prueba parte de cero."""
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0").rsplit("/", 1)[0] + "/15"
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": url,
            "KEY_PREFIX": "pruebas",
        }
    }
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _capa_de_canales_en_memoria(settings):
    """Las pruebas no usan Redis para los WebSocket (HU-02)."""
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


ORIGEN_PANEL = "http://localhost:5173"


@pytest.fixture(autouse=True)
def _origenes_del_panel(settings):
    """El panel de pruebas vive en el origen de desarrollo de Vite."""
    settings.PANEL_ORIGENES = [ORIGEN_PANEL]


@pytest.fixture
def cliente():
    """Cliente sin encabezados de navegador (como curl o la app del conductor)."""
    return APIClient()


@pytest.fixture
def panel():
    """Cliente que se comporta como el navegador del panel: envía Origin en cada petición."""
    return APIClient(HTTP_ORIGIN=ORIGEN_PANEL)


@pytest.fixture
def empresa(db):
    return EmpresaFactory()


@pytest.fixture
def otra_empresa(db):
    return EmpresaFactory()


@pytest.fixture
def despachador(empresa):
    return UsuarioFactory(empresa=empresa, rol="DESPACHADOR")


@pytest.fixture
def administrador(empresa):
    return UsuarioFactory(empresa=empresa, rol="ADMINISTRADOR")


@pytest.fixture
def conductor(empresa):
    return UsuarioFactory(empresa=empresa, rol="CONDUCTOR")


CLAVE_PASAJERO = "Clave-Sintetica-2026"


def cliente_con_cuenta(empresa, *, consentimiento=True, email="ana@correo.example"):
    """Cliente web con sesión de un PASAJERO con cuenta confirmada (teléfono +56900009101).

    Con `consentimiento=False` la cuenta es antigua: no aceptó el aviso de privacidad (DC-44).
    """
    from django.urls import reverse

    from apps.reservas.tests.fabricas import CuentaPasajeroFactory

    cuenta = CuentaPasajeroFactory(
        empresa=empresa,
        pasajero__nombre="Ana Pérez",
        pasajero__telefono="+56900009101",
        usuario__email=email,
        sin_consentimiento=not consentimiento,
    )
    cuenta.usuario.set_password(CLAVE_PASAJERO)
    cuenta.usuario.save()
    web = APIClient(HTTP_ORIGIN=ORIGEN_PANEL)
    respuesta = web.post(reverse("auth-token"), {"email": email, "password": CLAVE_PASAJERO}, format="json")
    if respuesta.status_code != 200:
        pytest.fail(f"El pasajero de prueba no pudo iniciar sesión: {respuesta.status_code} {respuesta.data}")
    web.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return web


@pytest.fixture
def con_cuenta(empresa):
    """HU-40 (CC-18): pasajero con cuenta confirmada y consentimiento (DC-44): solo así se pide."""
    return cliente_con_cuenta(empresa)


@pytest.fixture
def cuenta_antigua(empresa):
    """DC-44: pasajero con cuenta confirmada antes del consentimiento único; debe aceptarlo al ingresar."""
    return cliente_con_cuenta(empresa, consentimiento=False)
