from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import AlertaVueloViewSet, ConsultarVuelosAhoraView, VuelosDeHoyView

router = SimpleRouter()
router.register("alertas", AlertaVueloViewSet, basename="alerta")

urlpatterns = [
    path("vuelos-de-hoy/", VuelosDeHoyView.as_view(), name="vuelos-de-hoy"),
    path("vuelos-de-hoy/consultar/", ConsultarVuelosAhoraView.as_view(), name="vuelos-de-hoy-consultar"),
    *router.urls,
]
