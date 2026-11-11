from rest_framework.routers import SimpleRouter

from .usuarios_views import UsuarioPanelViewSet

router = SimpleRouter()
router.register("usuarios", UsuarioPanelViewSet, basename="usuario-panel")

urlpatterns = router.urls
