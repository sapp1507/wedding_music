from unittest.mock import patch

from django.test import override_settings, SimpleTestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import SongRequest
from .views import preview_song_link, yandex_track_ids


class SongRequestApiTests(APITestCase):
    def test_requires_song_title_or_link(self):
        response = self.client.post(
            reverse("song-list"),
            {"guest_name": "Анна", "artist": "Queen"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_guest_can_create_song_request(self):
        response = self.client.post(
            reverse("song-list"),
            {
                "guest_name": "Анна",
                "song_title": "Dancing Queen",
                "artist": "ABBA",
                "moment": SongRequest.Moment.DANCE,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(SongRequest.objects.count(), 1)
        self.assertFalse(SongRequest.objects.first().approved)

    def test_public_list_only_contains_approved_tracks(self):
        SongRequest.objects.create(
            guest_name="Анна",
            song_title="Hidden",
            approved=False,
        )
        SongRequest.objects.create(
            guest_name="Иван",
            song_title="Visible",
            approved=True,
        )

        response = self.client.get(reverse("song-public"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["song_title"], "Visible")

    @override_settings(SONG_REQUEST_SECRET="secret")
    def test_secret_link_header_is_required_when_configured(self):
        response = self.client.post(
            reverse("song-list"),
            {"guest_name": "Анна", "song_title": "Song"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        response = self.client.post(
            reverse("song-list"),
            {"guest_name": "Анна", "song_title": "Song"},
            HTTP_X_SONG_REQUEST_SECRET="secret",
            format="json",
        )

        self.assertEqual(response.status_code, 201)


class SongLinkPreviewTests(SimpleTestCase):
    def test_yandex_track_ids_from_shared_url(self):
        ids = yandex_track_ids(
            "https://music.yandex.ru/album/5060850/track/2215069"
            "?utm_source=web&utm_medium=copy_link"
        )

        self.assertEqual(ids, {"album_id": "5060850", "track_id": "2215069"})

    @patch("songs.views.validate_public_http_url")
    @patch("songs.views.fetch_json")
    def test_yandex_track_preview_uses_track_api(self, fetch_json, validate_public_http_url):
        fetch_json.return_value = {
            "result": [
                {
                    "title": "Конь",
                    "artists": [{"name": "Любэ"}],
                }
            ]
        }

        preview = preview_song_link(
            "https://music.yandex.ru/album/5060850/track/2215069"
            "?utm_source=web&utm_medium=copy_link"
        )

        self.assertEqual(preview["song_title"], "Конь")
        self.assertEqual(preview["artist"], "Любэ")
        self.assertEqual(preview["source"], "yandex")
        fetch_json.assert_called_once()
