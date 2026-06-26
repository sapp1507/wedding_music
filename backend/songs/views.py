import csv
import ipaddress
import json
import re
import socket
from html import unescape
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SongRequest
from .serializers import SongModerationSerializer, SongRequestSerializer


class MetaTagParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
            return
        if tag != "meta":
            return
        key = attrs.get("property") or attrs.get("name")
        content = attrs.get("content")
        if key and content:
            self.meta[key.lower()] = unescape(content.strip())

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


OEMBED_ENDPOINTS = {
    "youtube.com": "https://www.youtube.com/oembed",
    "youtu.be": "https://www.youtube.com/oembed",
    "open.spotify.com": "https://open.spotify.com/oembed",
    "soundcloud.com": "https://soundcloud.com/oembed",
    "music.apple.com": "https://embed.music.apple.com/oembed",
    "podcasts.apple.com": "https://embed.podcasts.apple.com/oembed",
}


def yandex_track_ids(url):
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").removeprefix("www.")
    if hostname not in {"music.yandex.ru", "music.yandex.com"}:
        return None

    match = re.search(r"/album/(?P<album_id>\d+)/track/(?P<track_id>\d+)", parsed.path)
    if not match:
        return None
    return match.groupdict()


def vk_audio_ids(url):
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").removeprefix("www.")
    if hostname not in {"vk.com", "m.vk.com"}:
        return None

    match = re.search(r"/audio(?P<owner_id>-?\d+)_(?P<audio_id>\d+)", parsed.path)
    if not match:
        query_match = re.search(r"(?:^|[?&])z=audio(?P<owner_id>-?\d+)_(?P<audio_id>\d+)", parsed.query)
        match = query_match
    if not match:
        return None
    return match.groupdict()


def fetch_json(url, headers=None):
    validate_public_http_url(url)
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "wedding-music/1.0",
            **(headers or {}),
        },
    )
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_html_meta(url):
    validate_public_http_url(url)
    request = Request(
        url,
        headers={
            "Accept": "text/html",
            "User-Agent": "Mozilla/5.0 wedding-music/1.0",
        },
    )
    with urlopen(request, timeout=5) as response:
        parser = MetaTagParser()
        parser.feed(response.read(300000).decode("utf-8", errors="ignore"))
        return parser.meta, unescape(parser.title.strip())


def oembed_endpoint_for(url):
    hostname = urlparse(url).hostname or ""
    hostname = hostname.removeprefix("www.")
    for domain, endpoint in OEMBED_ENDPOINTS.items():
        if hostname == domain or hostname.endswith(f".{domain}"):
            return f"{endpoint}?{urlencode({'url': url, 'format': 'json'})}"
    return None


def validate_public_http_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only public http/https URLs are supported.")

    try:
        addresses = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise ValueError("Unable to resolve URL hostname.") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise ValueError("Private URLs are not supported.")


def clean_title(value):
    value = re.sub(r"\s+", " ", value or "").strip()
    for suffix in [
        " - YouTube",
        " | YouTube",
        " | Spotify",
        " on Spotify",
        " - SoundCloud",
        " | SoundCloud",
        " - Apple Music",
        " on Apple Music",
        " | VK",
    ]:
        if value.endswith(suffix):
            value = value[: -len(suffix)].strip()
    return value


def is_generic_preview_title(value):
    title = clean_title(value).lower()
    return title in {
        "",
        "vk",
        "vkontakte",
        "вконтакте",
        "вконтакте | вконтакте",
        "вконтакте | добро пожаловать",
        "яндекс музыка — собираем музыку для вас",
    }


def split_artist_and_title(title, author=""):
    title = clean_title(title)
    author = clean_title(author)
    if author and title.lower().startswith(f"{author.lower()} - "):
        title = title[len(author) + 3 :].strip()
    if " - " in title:
        artist, song_title = [part.strip() for part in title.split(" - ", 1)]
        if artist and song_title:
            return artist, song_title
    if " — " in title:
        artist, song_title = [part.strip() for part in title.split(" — ", 1)]
        if artist and song_title:
            return artist, song_title
    if " by " in title:
        song_title, artist = [part.strip() for part in title.rsplit(" by ", 1)]
        if artist and song_title:
            return artist, song_title
    return author, title


def yandex_track_preview(url):
    ids = yandex_track_ids(url)
    if not ids:
        return None

    data = fetch_json(
        "https://api.music.yandex.net/tracks/"
        f"{ids['track_id']}:{ids['album_id']}",
        headers={
            "User-Agent": "YandexMusicAndroid/24022951 wedding-music/1.0",
            "X-Yandex-Music-Client": "YandexMusicAndroid/24022951",
        },
    )
    result = data.get("result", [])
    track = result[0] if isinstance(result, list) and result else result
    if not isinstance(track, dict):
        return {"song_title": "", "artist": "", "source": "yandex"}

    return {
        "song_title": clean_title(track.get("title", "")),
        "artist": ", ".join(
            clean_title(artist.get("name", ""))
            for artist in track.get("artists", [])
            if artist.get("name")
        ),
        "source": "yandex",
    }


def songlink_preview(url):
    data = fetch_json(
        f"https://api.song.link/v1-alpha.1/links?{urlencode({'url': url})}"
    )
    entity_id = data.get("entityUniqueId")
    entities = data.get("entitiesByUniqueId", {})
    entity = entities.get(entity_id)
    if not isinstance(entity, dict):
        entity = next(
            (
                item
                for item in entities.values()
                if isinstance(item, dict) and item.get("type") == "song"
            ),
            {},
        )

    return {
        "song_title": clean_title(entity.get("title", "")),
        "artist": clean_title(entity.get("artistName", "")),
        "source": "songlink",
    }


def vk_track_preview(url):
    ids = vk_audio_ids(url)
    if not ids:
        return None
    if not settings.VK_ACCESS_TOKEN:
        return {"song_title": "", "artist": "", "source": "vk"}

    params = {
        "audios": f"{ids['owner_id']}_{ids['audio_id']}",
        "access_token": settings.VK_ACCESS_TOKEN,
        "v": "5.131",
    }
    data = fetch_json(f"https://api.vk.com/method/audio.getById?{urlencode(params)}")
    if data.get("error"):
        raise ValueError(data["error"].get("error_msg", "VK API error"))
    tracks = data.get("response", [])
    track = tracks[0] if tracks else {}
    return {
        "song_title": clean_title(track.get("title", "")),
        "artist": clean_title(track.get("artist", "")),
        "source": "vk",
    }


def preview_song_link(url):
    validate_public_http_url(url)
    try:
        vk_preview = vk_track_preview(url)
        if vk_preview is not None and (
            vk_preview["song_title"] or vk_preview["artist"]
        ):
            return vk_preview
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        pass

    try:
        yandex_preview = yandex_track_preview(url)
        if yandex_preview is not None and (
            yandex_preview["song_title"] or yandex_preview["artist"]
        ):
            return yandex_preview
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        pass

    endpoint = oembed_endpoint_for(url)
    if endpoint:
        try:
            data = fetch_json(endpoint)
            artist, song_title = split_artist_and_title(
                data.get("title", ""),
                data.get("author_name", ""),
            )
            if song_title or artist:
                return {
                    "song_title": song_title,
                    "artist": artist,
                    "source": "oembed",
                }
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
            pass

    try:
        songlink = songlink_preview(url)
        if songlink["song_title"] or songlink["artist"]:
            return songlink
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        pass

    meta, page_title = fetch_html_meta(url)
    title = (
        meta.get("music:song")
        or meta.get("og:title")
        or meta.get("twitter:title")
        or page_title
    )
    artist = (
        meta.get("music:musician")
        or meta.get("music:creator")
        or meta.get("article:author")
        or meta.get("author")
    )
    artist, song_title = split_artist_and_title(title, artist)
    if is_generic_preview_title(song_title) and not artist:
        return {"song_title": "", "artist": "", "source": "meta"}
    return {
        "song_title": song_title,
        "artist": artist,
        "source": "meta",
    }


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

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.AllowAny],
        url_path="preview-link",
    )
    def preview_link(self, request):
        link = (request.data.get("link") or "").strip()
        serializer = self.get_serializer(data={"guest_name": "preview", "link": link})
        serializer.is_valid(raise_exception=True)
        try:
            preview = preview_song_link(link)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return Response(
                {"detail": "Не удалось определить трек по этой ссылке."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not preview["song_title"] and not preview["artist"]:
            return Response(
                {"detail": "Не удалось найти название или исполнителя на странице."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(preview)

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


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
@ensure_csrf_cookie
def current_user(request):
    user = request.user
    if not user.is_authenticated:
        return Response({"is_authenticated": False, "is_staff": False})
    return Response(
        {
            "is_authenticated": True,
            "is_staff": user.is_staff,
            "username": user.get_username(),
        }
    )


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"detail": "Неверный логин или пароль."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.is_staff:
            return Response(
                {"detail": "У пользователя нет доступа к модерации."},
                status=status.HTTP_403_FORBIDDEN,
            )
        login(request, user)
        return Response(
            {
                "is_authenticated": True,
                "is_staff": user.is_staff,
                "username": user.get_username(),
            }
        )


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Вы вышли."})
