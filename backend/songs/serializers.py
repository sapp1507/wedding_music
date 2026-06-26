from rest_framework import serializers

from .models import SongRequest


class SongRequestSerializer(serializers.ModelSerializer):
    moment_display = serializers.CharField(source="get_moment_display", read_only=True)

    class Meta:
        model = SongRequest
        fields = [
            "id",
            "guest_name",
            "song_title",
            "artist",
            "link",
            "moment",
            "moment_display",
            "comment",
            "approved",
            "created_at",
        ]
        read_only_fields = ["id", "approved", "created_at", "moment_display"]

    def validate(self, attrs):
        song_title = attrs.get("song_title", getattr(self.instance, "song_title", ""))
        link = attrs.get("link", getattr(self.instance, "link", ""))
        if not song_title and not link:
            raise serializers.ValidationError(
                {"song_title": "Укажите название трека или ссылку."}
            )
        return attrs


class SongModerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SongRequest
        fields = ["approved"]
