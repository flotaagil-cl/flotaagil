from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.reservas.whatsapp_views import WebhookEntranteView, WebhookEstadoView


def salud(_request):
    """Comprobación de vida para el monitoreo (UptimeRobot)."""
    return JsonResponse({"estado": "ok"})


urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/salud/", salud, name="salud"),
    path("api/auth/", include("apps.cuentas.urls")),
    path("api/", include("apps.reservas.urls")),
    path("api/", include("apps.flota.urls")),
    path("api/", include("apps.aeropuerto.urls")),
    path("api/", include("apps.convenios.urls")),
    path("api/app/", include("apps.flota.app_urls")),
    path("api/whatsapp/entrante/", WebhookEntranteView.as_view(), name="whatsapp-entrante"),
    path("api/whatsapp/estado/", WebhookEstadoView.as_view(), name="whatsapp-estado"),
    path("api/portal/", include("apps.portal.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]

if settings.DEBUG:
    urlpatterns += [path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs")]
