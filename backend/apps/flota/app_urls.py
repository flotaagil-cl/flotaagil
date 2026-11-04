from django.urls import path

from apps.reservas import app_views as asignaciones

from . import app_api

urlpatterns = [
    path("perfil/", app_api.PerfilView.as_view(), name="app-perfil"),
    path("consentimiento/", app_api.ConsentimientoView.as_view(), name="app-consentimiento"),
    path("posiciones/", app_api.PosicionesView.as_view(), name="app-posiciones"),
    path("turno/", app_api.TurnoView.as_view(), name="app-turno"),
    path("mi-turno/", app_api.MiTurnoView.as_view(), name="app-mi-turno"),
    path("viaje-activo/", app_api.ViajeActivoView.as_view(), name="app-viaje-activo"),
    path("viajes/<int:pk>/en-camino/", asignaciones.EnCaminoView.as_view(), name="app-en-camino"),
    path("viajes/<int:pk>/a-bordo/", asignaciones.ABordoView.as_view(), name="app-a-bordo"),
    path("viajes/<int:pk>/finalizar/", asignaciones.FinalizarView.as_view(), name="app-finalizar"),
    path("asignaciones/<int:pk>/aceptar/", asignaciones.AceptarView.as_view(), name="app-aceptar"),
    path("asignaciones/<int:pk>/rechazar/", asignaciones.RechazarView.as_view(), name="app-rechazar"),
]
