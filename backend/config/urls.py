from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.csrf import ensure_csrf_cookie

from songs.views import LoginView, LogoutView, current_user, share_links


@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"detail": "CSRF cookie set"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/csrf/", csrf),
    path("api/auth/me/", current_user),
    path("api/auth/login/", LoginView.as_view()),
    path("api/auth/logout/", LogoutView.as_view()),
    path("api/share-links/", share_links),
    path("api/", include("songs.urls")),
]
