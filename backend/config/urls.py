from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.comun.vistas import ConfiguracionPublicaView
from apps.cuentas.apariencia import AparienciaPublicaView, AparienciaView, LogoPublicoView, LogoView
from apps.cuentas.configuracion import ConfiguracionEmpresaView
from apps.integraciones.sugerencias import SugerirDireccionesView


def salud(_request):
    """Comprobación de vida para el monitoreo (UptimeRobot)."""
    return JsonResponse({"estado": "ok"})


urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/salud/", salud, name="salud"),
    path("api/configuracion-publica/", ConfiguracionPublicaView.as_view(), name="configuracion-publica"),
    path("api/auth/", include("apps.cuentas.urls")),
    path("api/", include("apps.reservas.urls")),
    path("api/", include("apps.flota.urls")),
    path("api/", include("apps.aeropuerto.urls")),
    path("api/", include("apps.convenios.urls")),
    path("api/", include("apps.cuentas.usuarios_urls")),
    path("api/app/", include("apps.flota.app_urls")),
    path("api/chat/", include("apps.chat.urls")),
    path("api/configuracion-empresa/", ConfiguracionEmpresaView.as_view(), name="configuracion-empresa"),
    path("api/apariencia/", AparienciaView.as_view(), name="apariencia"),
    path("api/apariencia/logo/", LogoView.as_view(), name="apariencia-logo"),
    path("api/publico/apariencia/<slug:slug>/", AparienciaPublicaView.as_view(), name="apariencia-publica"),
    path(
        "api/publico/apariencia/<slug:slug>/logo/<str:version>/<str:variante>.png",
        LogoPublicoView.as_view(),
        name="apariencia-logo-publico",
    ),
    path("api/direcciones/sugerir/", SugerirDireccionesView.as_view(), name="sugerir-direcciones"),
    path("api/portal/", include("apps.portal.urls")),
    path("api/mi-convenio/", include("apps.convenios.cuenta_urls")),
    path("api/mi-cuenta/", include("apps.reservas.cuenta_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]

if settings.DEBUG:
    urlpatterns += [path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs")]
