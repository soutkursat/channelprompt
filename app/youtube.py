"""YouTube veri toplama: kanal çözümleme, en çok izlenen videolar, altyazılar, thumbnail'lar."""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import parse_qs, unquote, urlparse

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

from . import config

API = "https://www.googleapis.com/youtube/v3"


class YouTubeError(Exception):
    pass


@dataclass
class Video:
    id: str
    title: str
    description: str
    published_at: str
    duration_seconds: int
    views: int
    likes: int
    comments: int
    tags: list[str]
    thumbnail_url: str
    default_language: str = ""
    transcript: list[dict] = field(default_factory=list)  # [{start, duration, text}]
    transcript_language: str = ""
    transcript_source: str = ""
    thumbnail_bytes: bytes | None = None

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.id}"

    @property
    def duration_label(self) -> str:
        return format_seconds(self.duration_seconds)

    @property
    def transcript_text(self) -> str:
        return " ".join(s["text"] for s in self.transcript)

    def transcript_with_timestamps(self) -> str:
        return "\n".join(f"[{format_seconds(s['start'])}] {s['text']}" for s in self.transcript)

    def first_seconds_text(self, seconds: int = 30) -> str:
        return " ".join(s["text"] for s in self.transcript if s["start"] < seconds)

    def script_metrics(self) -> dict:
        text = self.transcript_text
        words = len(text.split())
        minutes = max(self.duration_seconds / 60, 0.01)
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        sentence_lengths = [len(s.split()) for s in sentences] or [0]
        first30 = self.first_seconds_text(30)
        return {
            "kelime_sayisi": words,
            "dakika_basi_kelime": round(words / minutes) if words else 0,
            "cumle_sayisi": len(sentences),
            "ortalama_cumle_uzunlugu": round(statistics.mean(sentence_lengths), 1),
            "ilk_30sn_kelime": len(first30.split()),
            "soru_cumlesi_sayisi": text.count("?"),
        }


@dataclass
class Channel:
    id: str
    title: str
    handle: str
    description: str
    country: str
    published_at: str
    subscribers: int
    total_views: int
    video_count: int
    keywords: str
    avatar_url: str
    banner_url: str
    uploads_playlist: str
    default_language: str = ""


def format_seconds(total: float) -> str:
    total = int(total)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def parse_iso_duration(value: str) -> int:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


class YouTubeClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or config.YOUTUBE_API_KEY
        if not self.api_key:
            raise YouTubeError("YOUTUBE_API_KEY tanımlı değil.")
        self.session = requests.Session()

    def _get(self, endpoint: str, **params) -> dict:
        params["key"] = self.api_key
        r = self.session.get(f"{API}/{endpoint}", params=params, timeout=30)
        if r.status_code != 200:
            try:
                msg = r.json()["error"]["message"]
            except Exception:
                msg = r.text[:300]
            raise YouTubeError(f"YouTube API hatası ({endpoint}): {msg}")
        return r.json()

    # ---------- Kanal çözümleme ----------
    def resolve_channel_id(self, url: str) -> str:
        url = url.strip()
        if url.startswith("@"):
            return self._by_handle(url)
        if re.fullmatch(r"UC[\w-]{22}", url):
            return url
        if not url.startswith("http"):
            url = "https://" + url
        parsed = urlparse(url)
        path = unquote(parsed.path).rstrip("/")
        host = parsed.netloc.lower()

        if "youtu.be" in host:
            return self._channel_of_video(path.strip("/"))
        if m := re.match(r"^/channel/(UC[\w-]{22})", path):
            return m.group(1)
        if m := re.match(r"^/(@[^/]+)", path):
            return self._by_handle(m.group(1))
        if path == "/watch":
            vid = parse_qs(parsed.query).get("v", [""])[0]
            return self._channel_of_video(vid)
        if m := re.match(r"^/(?:shorts|live|embed)/([\w-]{11})", path):
            return self._channel_of_video(m.group(1))
        if m := re.match(r"^/user/([^/]+)", path):
            data = self._get("channels", part="id", forUsername=m.group(1))
            if data.get("items"):
                return data["items"][0]["id"]
            return self._search_channel(m.group(1))
        if m := re.match(r"^/c/([^/]+)", path) or re.match(r"^/([^/]+)$", path):
            name = m.group(1)
            try:
                return self._by_handle("@" + name)
            except YouTubeError:
                return self._search_channel(name)
        raise YouTubeError("Kanal linki anlaşılamadı. Örnek: https://www.youtube.com/@kanaladi")

    def _by_handle(self, handle: str) -> str:
        data = self._get("channels", part="id", forHandle=handle)
        if not data.get("items"):
            raise YouTubeError(f"{handle} kanalı bulunamadı.")
        return data["items"][0]["id"]

    def _channel_of_video(self, video_id: str) -> str:
        data = self._get("videos", part="snippet", id=video_id)
        if not data.get("items"):
            raise YouTubeError("Linkteki video bulunamadı.")
        return data["items"][0]["snippet"]["channelId"]

    def _search_channel(self, query: str) -> str:
        data = self._get("search", part="snippet", q=query, type="channel", maxResults=1)
        if not data.get("items"):
            raise YouTubeError(f"'{query}' kanalı bulunamadı.")
        return data["items"][0]["snippet"]["channelId"]

    # ---------- Kanal ve videolar ----------
    def get_channel(self, channel_id: str) -> Channel:
        data = self._get(
            "channels",
            part="snippet,statistics,brandingSettings,contentDetails",
            id=channel_id,
        )
        if not data.get("items"):
            raise YouTubeError("Kanal bulunamadı.")
        it = data["items"][0]
        sn, st = it["snippet"], it.get("statistics", {})
        br = it.get("brandingSettings", {})
        thumbs = sn.get("thumbnails", {})
        return Channel(
            id=channel_id,
            title=sn.get("title", ""),
            handle=sn.get("customUrl", ""),
            description=sn.get("description", ""),
            country=sn.get("country", ""),
            published_at=sn.get("publishedAt", ""),
            subscribers=int(st.get("subscriberCount", 0) or 0),
            total_views=int(st.get("viewCount", 0) or 0),
            video_count=int(st.get("videoCount", 0) or 0),
            keywords=br.get("channel", {}).get("keywords", ""),
            avatar_url=(thumbs.get("high") or thumbs.get("default") or {}).get("url", ""),
            banner_url=br.get("image", {}).get("bannerExternalUrl", ""),
            uploads_playlist=it["contentDetails"]["relatedPlaylists"]["uploads"],
            default_language=sn.get("defaultLanguage", "") or br.get("channel", {}).get("defaultLanguage", ""),
        )

    def _video_details(self, ids: list[str]) -> list[Video]:
        videos: list[Video] = []
        for i in range(0, len(ids), 50):
            data = self._get(
                "videos", part="snippet,statistics,contentDetails", id=",".join(ids[i : i + 50])
            )
            for it in data.get("items", []):
                sn, st = it["snippet"], it.get("statistics", {})
                th = sn.get("thumbnails", {})
                best = next(
                    (th[k]["url"] for k in ("maxres", "standard", "high", "medium", "default") if k in th),
                    "",
                )
                videos.append(
                    Video(
                        id=it["id"],
                        title=sn.get("title", ""),
                        description=sn.get("description", ""),
                        published_at=sn.get("publishedAt", ""),
                        duration_seconds=parse_iso_duration(it["contentDetails"].get("duration", "")),
                        views=int(st.get("viewCount", 0) or 0),
                        likes=int(st.get("likeCount", 0) or 0),
                        comments=int(st.get("commentCount", 0) or 0),
                        tags=sn.get("tags", []),
                        thumbnail_url=best,
                        default_language=sn.get("defaultAudioLanguage", "") or sn.get("defaultLanguage", ""),
                    )
                )
        return videos

    def _matches_type(self, v: Video, video_type: str) -> bool:
        if v.duration_seconds == 0:  # canlı yayın / premiere
            return False
        is_short = v.duration_seconds <= config.SHORTS_MAX_SECONDS
        if video_type == "shorts":
            return is_short
        if video_type == "long":
            return not is_short
        return True

    def most_viewed(self, channel_id: str, video_type: str = "long", limit: int = 30) -> list[Video]:
        """Kanalın en çok izlenen videoları (gerçek izlenme sayısına göre sıralı)."""
        ids: list[str] = []
        page_token = None
        for _ in range(2):  # en fazla 100 aday
            params = dict(part="id", channelId=channel_id, order="viewCount", type="video", maxResults=50)
            if page_token:
                params["pageToken"] = page_token
            data = self._get("search", **params)
            ids += [it["id"]["videoId"] for it in data.get("items", [])]
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        videos = [v for v in self._video_details(ids) if self._matches_type(v, video_type)]
        videos.sort(key=lambda v: v.views, reverse=True)
        return videos[:limit]

    def recent_uploads(self, playlist_id: str, video_type: str = "long", limit: int = 20) -> list[Video]:
        ids: list[str] = []
        page_token = None
        for _ in range(2):
            params = dict(part="contentDetails", playlistId=playlist_id, maxResults=50)
            if page_token:
                params["pageToken"] = page_token
            data = self._get("playlistItems", **params)
            ids += [it["contentDetails"]["videoId"] for it in data.get("items", [])]
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        videos = [v for v in self._video_details(ids) if self._matches_type(v, video_type)]
        videos.sort(key=lambda v: v.published_at, reverse=True)
        return videos[:limit]


# ---------- Altyazı ----------
def _transcript_api() -> YouTubeTranscriptApi:
    if config.YT_PROXY_URL:
        return YouTubeTranscriptApi(
            proxy_config=GenericProxyConfig(http_url=config.YT_PROXY_URL, https_url=config.YT_PROXY_URL)
        )
    return YouTubeTranscriptApi()


def fetch_transcript(video: Video, preferred_langs: list[str]) -> None:
    """Videonun altyazısını video.transcript içine yazar. Başarısız olursa boş bırakır."""
    try:
        tlist = _transcript_api().list(video.id)
        transcripts = list(tlist)
        chosen = None
        # 1) tercih edilen dillerde manuel, 2) tercih edilen dillerde otomatik, 3) herhangi biri
        for lang in preferred_langs:
            chosen = next((t for t in transcripts if t.language_code.startswith(lang) and not t.is_generated), None)
            if chosen:
                break
        if not chosen:
            for lang in preferred_langs:
                chosen = next((t for t in transcripts if t.language_code.startswith(lang)), None)
                if chosen:
                    break
        if not chosen and transcripts:
            chosen = next((t for t in transcripts if not t.is_generated), transcripts[0])
        if chosen:
            fetched = chosen.fetch()
            video.transcript = [
                {"start": s.start, "duration": s.duration, "text": s.text.replace("\n", " ").strip()}
                for s in fetched
                if s.text.strip()
            ]
            video.transcript_language = chosen.language_code
            video.transcript_source = "youtube" + (" (otomatik)" if chosen.is_generated else "")
            return
    except Exception:
        pass

    if config.SUPADATA_API_KEY:
        try:
            r = requests.get(
                "https://api.supadata.ai/v1/youtube/transcript",
                params={"videoId": video.id},
                headers={"x-api-key": config.SUPADATA_API_KEY},
                timeout=60,
            )
            if r.status_code == 200:
                data = r.json()
                video.transcript = [
                    {
                        "start": c.get("offset", 0) / 1000,
                        "duration": c.get("duration", 0) / 1000,
                        "text": c.get("text", "").strip(),
                    }
                    for c in data.get("content", [])
                    if c.get("text", "").strip()
                ]
                video.transcript_language = data.get("lang", "")
                video.transcript_source = "supadata"
        except Exception:
            pass


def download_thumbnail(video: Video) -> None:
    urls = [video.thumbnail_url, f"https://i.ytimg.com/vi/{video.id}/hqdefault.jpg"]
    for url in urls:
        if not url:
            continue
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200 and r.content:
                video.thumbnail_bytes = r.content
                return
        except Exception:
            continue


def upload_cadence(videos: list[Video]) -> dict:
    """Son yüklemelerden yayın sıklığı, gün ve saat dağılımı."""
    dates = sorted(
        (datetime.fromisoformat(v.published_at.replace("Z", "+00:00")) for v in videos if v.published_at),
        reverse=True,
    )
    if len(dates) < 2:
        return {}
    gaps = [(dates[i] - dates[i + 1]).total_seconds() / 86400 for i in range(len(dates) - 1)]
    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    day_counts: dict[str, int] = {}
    hour_counts: dict[int, int] = {}
    for d in dates:
        day_counts[days[d.weekday()]] = day_counts.get(days[d.weekday()], 0) + 1
        hour_counts[d.hour] = hour_counts.get(d.hour, 0) + 1
    return {
        "ortalama_gun_arasi": round(statistics.mean(gaps), 1),
        "medyan_gun_arasi": round(statistics.median(gaps), 1),
        "haftalik_video": round(7 / statistics.mean(gaps), 2) if statistics.mean(gaps) else None,
        "gun_dagilimi": day_counts,
        "saat_dagilimi_utc": dict(sorted(hour_counts.items())),
        "incelenen_video": len(dates),
    }
