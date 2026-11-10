from django.urls import path

from . import cuenta_views as vistas

urlpatterns = [
    path("", vistas.MiConvenioView.as_view(), name="mi-convenio"),
    path("solicitudes/", vistas.SolicitudMiConvenioView.as_view(), name="mi-convenio-solicitudes"),
    path("reservas/", vistas.ReservasMiConvenioView.as_view(), name="mi-convenio-reservas"),
]
