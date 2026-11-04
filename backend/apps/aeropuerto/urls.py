from rest_framework.routers import SimpleRouter

from .views import AlertaVueloViewSet

router = SimpleRouter()
router.register("alertas", AlertaVueloViewSet, basename="alerta")

urlpatterns = router.urls
