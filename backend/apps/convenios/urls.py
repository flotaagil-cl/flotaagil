from rest_framework.routers import SimpleRouter

from .views import ConvenioViewSet

router = SimpleRouter()
router.register("convenios", ConvenioViewSet, basename="convenio")

urlpatterns = router.urls
