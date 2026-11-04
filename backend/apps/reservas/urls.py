from rest_framework.routers import SimpleRouter

from .conversaciones import ConversacionViewSet
from .views import ViajeViewSet

router = SimpleRouter()
router.register("viajes", ViajeViewSet, basename="viaje")
router.register("conversaciones", ConversacionViewSet, basename="conversacion")

urlpatterns = router.urls
