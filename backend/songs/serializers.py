from rest_framework import serializers

from .models import (
    GuestRSVP,
    ImportantAnnouncement,
    SiteVisit,
    SongRequest,
    WeddingEvent,
    WeddingFAQ,
    WeddingInfoBlock,
    WeddingPage,
)


class WeddingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeddingEvent
        fields = ["id", "title", "description", "starts_at", "order"]


class WeddingFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeddingFAQ
        fields = ["id", "question", "answer", "order"]


class WeddingInfoBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeddingInfoBlock
        fields = ["id", "title", "body", "link_label", "link_url", "order"]


class WeddingPageSerializer(serializers.ModelSerializer):
    events = serializers.SerializerMethodField()
    faqs = serializers.SerializerMethodField()
    info_blocks = serializers.SerializerMethodField()

    class Meta:
        model = WeddingPage
        fields = [
            "id",
            "groom_name",
            "bride_name",
            "wedding_date",
            "timezone_name",
            "hero_kicker",
            "invitation_text",
            "location_title",
            "location_name",
            "location_address",
            "location_map_url",
            "footer_title",
            "footer_text",
            "events",
            "faqs",
            "info_blocks",
        ]

    def get_events(self, obj):
        return WeddingEventSerializer(
            obj.events.filter(is_visible=True),
            many=True,
        ).data

    def get_faqs(self, obj):
        return WeddingFAQSerializer(
            obj.faqs.filter(is_visible=True),
            many=True,
        ).data

    def get_info_blocks(self, obj):
        return WeddingInfoBlockSerializer(
            obj.info_blocks.filter(is_visible=True),
            many=True,
        ).data


class GuestRSVPSerializer(serializers.ModelSerializer):
    attendance_display = serializers.CharField(
        source="get_attendance_display",
        read_only=True,
    )

    class Meta:
        model = GuestRSVP
        fields = [
            "id",
            "guest_name",
            "attendance",
            "attendance_display",
            "guests_count",
            "phone",
            "comment",
            "created_at",
        ]
        read_only_fields = ["id", "attendance_display", "created_at"]

    def validate_guests_count(self, value):
        if value < 1:
            raise serializers.ValidationError("Укажите хотя бы одного гостя.")
        if value > 10:
            raise serializers.ValidationError("Для большой компании напишите комментарий.")
        return value


class ImportantAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportantAnnouncement
        fields = ["id", "title", "body", "view_count", "created_at", "updated_at"]
        read_only_fields = fields


class SiteVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteVisit
        fields = ["visitor_id", "last_path"]
        extra_kwargs = {"visitor_id": {"validators": []}}

    def validate_visitor_id(self, value):
        value = (value or "").strip()
        if len(value) < 8:
            raise serializers.ValidationError("Некорректный ID посетителя.")
        if len(value) > 64:
            raise serializers.ValidationError("Слишком длинный ID посетителя.")
        return value


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
