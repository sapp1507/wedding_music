from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"detail": "CSRF cookie set"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/csrf/", csrf),
    path("api/", include("songs.urls")),
]
