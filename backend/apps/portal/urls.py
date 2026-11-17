from django.urls import path

from . import views

urlpatterns = [
    path("<slug:slug>/", views.EmpresaPortalView.as_view(), name="portal-empresa"),
    path(
        "<slug:slug>/registro-empresa/", views.RegistroEmpresaView.as_view(), name="portal-registro-empresa"
    ),
    path("<slug:slug>/cuenta/", views.CrearCuentaView.as_view(), name="portal-crear-cuenta"),
    # HU-51 (CC-22): reserva pública y su confirmación por correo.
    path("<slug:slug>/reservas/", views.ReservaPublicaView.as_view(), name="portal-reserva-publica"),
    # HU-53 (CC-22): solicitud pública de convenio.
    path("<slug:slug>/convenio/", views.SolicitudConvenioView.as_view(), name="portal-solicitud-convenio"),
    path(
        "<slug:slug>/reservas/confirmar/",
        views.ConfirmarReservaView.as_view(),
        name="portal-reserva-confirmar",
    ),
    path("<slug:slug>/cuenta/estado/", views.EstadoActivacionView.as_view(), name="portal-cuenta-estado"),
    path(
        "<slug:slug>/cuenta/reenviar/", views.ReenviarActivacionView.as_view(), name="portal-cuenta-reenviar"
    ),
]
