from django.urls import path

from . import app_api

urlpatterns = [
    path("perfil/", app_api.PerfilView.as_view(), name="app-perfil"),
    path("consentimiento/", app_api.ConsentimientoView.as_view(), name="app-consentimiento"),
    path("posiciones/", app_api.PosicionesView.as_view(), name="app-posiciones"),
    path("turno/", app_api.TurnoView.as_view(), name="app-turno"),
]
