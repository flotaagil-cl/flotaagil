from django.urls import path

from . import views

urlpatterns = [
    path("<slug:slug>/", views.EmpresaPortalView.as_view(), name="portal-empresa"),
    path("<slug:slug>/solicitudes/", views.SolicitudPortalView.as_view(), name="portal-solicitudes"),
    path(
        "<slug:slug>/registro-empresa/", views.RegistroEmpresaView.as_view(), name="portal-registro-empresa"
    ),
    path("<slug:slug>/cuenta/", views.CrearCuentaView.as_view(), name="portal-crear-cuenta"),
]
