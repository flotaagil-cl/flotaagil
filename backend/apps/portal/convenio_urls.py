from django.urls import path

from . import convenio_views as views

urlpatterns = [
    path("<str:token>/", views.AccesoConvenioView.as_view(), name="convenio-acceso"),
    path("<str:token>/sesion/", views.SesionConvenioView.as_view(), name="convenio-sesion"),
    path("<str:token>/salir/", views.SalirConvenioView.as_view(), name="convenio-salir"),
    path("<str:token>/solicitudes/", views.SolicitudConvenioView.as_view(), name="convenio-solicitudes"),
]
