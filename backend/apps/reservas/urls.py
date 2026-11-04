from django.urls import path
from rest_framework.routers import SimpleRouter

from .conversaciones import ConversacionViewSet
from .indicadores import IndicadoresView
from .reportes import OpcionesReporteView, ReporteCsvView, ReporteView
from .views import ViajeViewSet

router = SimpleRouter()
router.register("viajes", ViajeViewSet, basename="viaje")
router.register("conversaciones", ConversacionViewSet, basename="conversacion")

urlpatterns = [
    path("indicadores/", IndicadoresView.as_view(), name="indicadores"),
    path("reportes/opciones/", OpcionesReporteView.as_view(), name="reporte-opciones"),
    path("reportes/<slug:tipo>/", ReporteView.as_view(), name="reporte"),
    path("reportes/<slug:tipo>/csv/", ReporteCsvView.as_view(), name="reporte-csv"),
    *router.urls,
]
