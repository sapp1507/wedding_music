import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import SongRequest


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
