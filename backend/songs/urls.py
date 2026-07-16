from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    SongRequestViewSet,
    active_announcement,
    create_rsvp,
    mark_announcement_viewed,
    record_visit,
    site_stats,
    wedding_page,
)


router = DefaultRouter()
router.register("songs", SongRequestViewSet, basename="song")

urlpatterns = [
    path("announcement/", active_announcement),
    path("announcement/<int:pk>/view/", mark_announcement_viewed),
    path("visits/", record_visit),
    path("site-stats/", site_stats),
    path("wedding-page/", wedding_page),
    path("rsvp/", create_rsvp),
]
urlpatterns += router.urls
