from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import AlertaVueloViewSet, VuelosDeHoyView

router = SimpleRouter()
router.register("alertas", AlertaVueloViewSet, basename="alerta")

urlpatterns = [
    path("vuelos-de-hoy/", VuelosDeHoyView.as_view(), name="vuelos-de-hoy"),
    *router.urls,
]
