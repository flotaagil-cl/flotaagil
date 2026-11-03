from rest_framework.routers import SimpleRouter

from .views import ConductorViewSet, VehiculoViewSet

router = SimpleRouter()
router.register("vehiculos", VehiculoViewSet, basename="vehiculo")
router.register("conductores", ConductorViewSet, basename="conductor")

urlpatterns = router.urls
