from unittest.mock import patch
from urllib.error import HTTPError

from django.contrib.auth import get_user_model
from django.test import override_settings, SimpleTestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import SongRequest
from .views import preview_song_link, vk_audio_ids, vk_track_preview, yandex_track_ids


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

    @override_settings(SONG_REQUEST_SECRET="secret")
    def test_staff_can_update_and_delete_when_secret_is_configured(self):
        user = get_user_model().objects.create_user(
            username="admin",
            password="password",
            is_staff=True,
        )
        song = SongRequest.objects.create(
            guest_name="Анна",
            link="https://example.com/track",
        )
        self.client.force_authenticate(user=user)

        response = self.client.patch(
            reverse("song-detail", args=[song.id]),
            {"song_title": "Song", "artist": "Artist"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        song.refresh_from_db()
        self.assertEqual(song.song_title, "Song")
        self.assertEqual(song.artist, "Artist")

        response = self.client.delete(reverse("song-detail", args=[song.id]))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(SongRequest.objects.filter(id=song.id).exists())

    @override_settings(PUBLIC_URL="https://music.example.com", SONG_REQUEST_SECRET="secret")
    def test_staff_can_get_share_links(self):
        user = get_user_model().objects.create_user(
            username="admin",
            password="password",
            is_staff=True,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/share-links/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["dj_url"], "https://music.example.com/dj")
        self.assertEqual(
            response.data["request_url"],
            "https://music.example.com/?secret=secret",
        )
        self.assertTrue(response.data["has_secret"])


class SongLinkPreviewTests(SimpleTestCase):
    def test_vk_audio_ids_from_shared_url(self):
        ids = vk_audio_ids("https://vk.com/audio-2001652521_86652521")

        self.assertEqual(ids, {"owner_id": "-2001652521", "audio_id": "86652521"})

    @override_settings(VK_ACCESS_TOKEN="vk-token")
    @patch("songs.views.fetch_json")
    def test_vk_track_preview_uses_vk_api(self, fetch_json):
        fetch_json.return_value = {
            "response": [
                {
                    "title": "Сквозь",
                    "artist": "Борисов Павел",
                }
            ]
        }

        preview = vk_track_preview("https://vk.com/audio-2001652521_86652521")

        self.assertEqual(preview["song_title"], "Сквозь")
        self.assertEqual(preview["artist"], "Борисов Павел")
        self.assertEqual(preview["source"], "vk")
        fetch_json.assert_called_once()

    @override_settings(VK_ACCESS_TOKEN="")
    def test_vk_track_preview_without_token_is_empty(self):
        preview = vk_track_preview("https://vk.com/audio-2001652521_86652521")

        self.assertEqual(preview, {"song_title": "", "artist": "", "source": "vk"})

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

    @patch("songs.views.validate_public_http_url")
    @patch("songs.views.fetch_json")
    def test_yandex_track_preview_falls_back_to_songlink(self, fetch_json, validate_public_http_url):
        fetch_json.side_effect = [
            HTTPError(
                "https://api.music.yandex.net/tracks/2215069:5060850",
                451,
                "Unavailable For Legal Reasons",
                {},
                None,
            ),
            {
                "entityUniqueId": "YANDEX_SONG::2215069",
                "entitiesByUniqueId": {
                    "YANDEX_SONG::2215069": {
                        "type": "song",
                        "title": "Конь",
                        "artistName": "Николай Расторгуев",
                    }
                },
            },
        ]

        preview = preview_song_link(
            "https://music.yandex.ru/album/5060850/track/2215069"
            "?utm_source=web&utm_medium=copy_link"
        )

        self.assertEqual(preview["song_title"], "Конь")
        self.assertEqual(preview["artist"], "Николай Расторгуев")
        self.assertEqual(preview["source"], "songlink")
        self.assertEqual(fetch_json.call_count, 2)
