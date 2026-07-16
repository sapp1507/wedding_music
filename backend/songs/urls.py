from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import SongRequestViewSet, create_rsvp, wedding_page


router = DefaultRouter()
router.register("songs", SongRequestViewSet, basename="song")

urlpatterns = [
    path("wedding-page/", wedding_page),
    path("rsvp/", create_rsvp),
]
urlpatterns += router.urls
