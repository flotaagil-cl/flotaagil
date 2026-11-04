from django.urls import path
from rest_framework.routers import SimpleRouter

from .conversaciones import ConversacionViewSet
from .indicadores import IndicadoresView
from .views import ViajeViewSet

router = SimpleRouter()
router.register("viajes", ViajeViewSet, basename="viaje")
router.register("conversaciones", ConversacionViewSet, basename="conversacion")

urlpatterns = [path("indicadores/", IndicadoresView.as_view(), name="indicadores"), *router.urls]
