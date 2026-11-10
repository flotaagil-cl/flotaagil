from django.urls import path
from rest_framework.routers import SimpleRouter

from .turnos_views import CierreCajaView, TurnosPorCerrarView, TurnosView
from .views import ConductorViewSet, VehiculoViewSet

router = SimpleRouter()
router.register("vehiculos", VehiculoViewSet, basename="vehiculo")
router.register("conductores", ConductorViewSet, basename="conductor")

urlpatterns = [
    *router.urls,
    path("turnos/", TurnosView.as_view(), name="turnos"),
    path("turnos/por-cerrar/", TurnosPorCerrarView.as_view(), name="turnos-por-cerrar"),
    path("turnos/<int:pk>/cierre-caja/", CierreCajaView.as_view(), name="turno-cierre-caja"),
]
