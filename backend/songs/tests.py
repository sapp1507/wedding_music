from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import SongRequest


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
