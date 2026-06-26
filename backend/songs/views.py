import csv

from django.conf import settings
from django.http import HttpResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import SongRequest
from .serializers import SongModerationSerializer, SongRequestSerializer


class HasRequestSecretOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not settings.SONG_REQUEST_SECRET:
            return True
        return request.headers.get("X-Song-Request-Secret") == settings.SONG_REQUEST_SECRET


class IsAdminOrCreateOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if view.action == "create":
            return True
        if view.action in ["retrieve", "moments", "public"]:
            return True
        return bool(request.user and request.user.is_staff)


class SongRequestViewSet(viewsets.ModelViewSet):
    queryset = SongRequest.objects.all()
    serializer_class = SongRequestSerializer
    permission_classes = [HasRequestSecretOrReadOnly, IsAdminOrCreateOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in ["public", "retrieve"]:
            return queryset.filter(approved=True)
        return queryset

    def get_serializer_class(self):
        if self.action == "approve":
            return SongModerationSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def moments(self, request):
        return Response(
            [{"value": value, "label": label} for value, label in SongRequest.Moment.choices]
        )

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def public(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        song = self.get_object()
        serializer = self.get_serializer(song, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(SongRequestSerializer(song).data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAdminUser])
    def export(self, request):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="song_requests.csv"'
        response.write("\ufeff")

        writer = csv.writer(response)
        writer.writerow(
            [
                "guest_name",
                "song_title",
                "artist",
                "link",
                "moment",
                "comment",
                "approved",
                "created_at",
            ]
        )
        for song in self.get_queryset():
            writer.writerow(
                [
                    song.guest_name,
                    song.song_title,
                    song.artist,
                    song.link,
                    song.get_moment_display(),
                    song.comment,
                    song.approved,
                    song.created_at.isoformat(),
                ]
            )

        return response

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "message": "Спасибо! Мы добавили трек в список ❤",
                "request": serializer.data,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )
