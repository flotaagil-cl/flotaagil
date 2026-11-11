from django.urls import path

from . import cuenta_views as vistas

urlpatterns = [
    path("", vistas.MiCuentaView.as_view(), name="mi-cuenta"),
    path("reservas/", vistas.MisReservasView.as_view(), name="mi-cuenta-reservas"),
    path("reservas/<int:pk>/", vistas.TuViajeView.as_view(), name="mi-cuenta-reserva"),
    path("reservas/<int:pk>/cancelar/", vistas.CancelarMiReservaView.as_view(), name="mi-cuenta-cancelar"),
    path("solicitudes/", vistas.SolicitudMiCuentaView.as_view(), name="mi-cuenta-solicitudes"),
    path("privacidad/", vistas.MiPrivacidadView.as_view(), name="mi-cuenta-privacidad"),
]
