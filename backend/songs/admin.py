import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import (
    GuestRSVP,
    SongRequest,
    WeddingEvent,
    WeddingFAQ,
    WeddingInfoBlock,
    WeddingPage,
)


@admin.action(description="Экспортировать выбранные заявки в CSV")
def export_song_requests_csv(modeladmin, request, queryset):
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
    for song in queryset:
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


@admin.register(SongRequest)
class SongRequestAdmin(admin.ModelAdmin):
    change_list_template = "admin/songs/songrequest/change_list.html"
    list_display = (
        "guest_name",
        "song_title",
        "artist",
        "moment",
        "approved",
        "created_at",
    )
    list_filter = ("approved", "moment", "created_at")
    search_fields = ("guest_name", "song_title", "artist", "link", "comment")
    list_editable = ("approved",)
    readonly_fields = ("created_at",)
    actions = (export_song_requests_csv,)


class WeddingEventInline(admin.TabularInline):
    model = WeddingEvent
    extra = 1
    fields = ("order", "title", "description", "starts_at", "is_visible")


class WeddingFAQInline(admin.TabularInline):
    model = WeddingFAQ
    extra = 1
    fields = ("order", "question", "answer", "is_visible")


class WeddingInfoBlockInline(admin.TabularInline):
    model = WeddingInfoBlock
    extra = 1
    fields = ("order", "title", "body", "link_label", "link_url", "is_visible")


@admin.register(WeddingPage)
class WeddingPageAdmin(admin.ModelAdmin):
    list_display = ("__str__", "wedding_date", "location_name", "updated_at")
    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "groom_name",
                    "bride_name",
                    "wedding_date",
                    "timezone_name",
                    "hero_kicker",
                    "invitation_text",
                )
            },
        ),
        (
            "Место",
            {
                "fields": (
                    "location_title",
                    "location_name",
                    "location_address",
                    "location_map_url",
                )
            },
        ),
        ("Финал", {"fields": ("footer_title", "footer_text")}),
    )
    readonly_fields = ("updated_at",)
    inlines = (WeddingEventInline, WeddingInfoBlockInline, WeddingFAQInline)


@admin.register(GuestRSVP)
class GuestRSVPAdmin(admin.ModelAdmin):
    list_display = (
        "guest_name",
        "attendance",
        "guests_count",
        "phone",
        "created_at",
    )
    list_filter = ("attendance", "created_at")
    search_fields = ("guest_name", "phone", "comment")
    readonly_fields = ("created_at",)
