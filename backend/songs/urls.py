from rest_framework.routers import DefaultRouter

from .views import SongRequestViewSet


router = DefaultRouter()
router.register("songs", SongRequestViewSet, basename="song")

urlpatterns = router.urls
