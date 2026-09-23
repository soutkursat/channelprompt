"""Analiz hattı: YouTube verisi → Claude video analizleri → Kanal DNA → Proje talimatı → paket."""
from __future__ import annotations

import base64
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import anthropic

from . import config, prompts
from .bundle import KNOWLEDGE_FILES, build_bundle
from .youtube import (
    Channel,
    Video,
    YouTubeClient,
    download_thumbnail,
    fetch_transcript,
    upload_cadence,
)

Progress = Callable[[str, int], None]

LANGUAGE_NAMES = {
    "tr": "Türkçe", "en": "İngilizce", "de": "Almanca", "es": "İspanyolca", "fr": "Fransızca",
    "pt": "Portekizce", "it": "İtalyanca", "ar": "Arapça", "ru": "Rusça", "hi": "Hintçe",
    "ja": "Japonca", "ko": "Korece", "nl": "Felemenkçe", "pl": "Lehçe", "id": "Endonezce",
}


class AnalysisError(Exception):
    pass


def _media_type(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _image_block(data: bytes) -> dict:
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": _media_type(data), "data": base64.standard_b64encode(data).decode()},
    }


class ClaudeRunner:
    def __init__(self):
        if not config.ANTHROPIC_API_KEY:
            raise AnalysisError("ANTHROPIC_API_KEY tanımlı değil.")
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, max_retries=4)

    def run(self, content: list[dict], max_tokens: int = 32000) -> str:
        with self.client.beta.messages.stream(
            model=config.CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=prompts.ANALYST_SYSTEM,
            thinking={"type": "adaptive"},
            output_config={"effort": config.CLAUDE_EFFORT},
            # Güvenlik sınıflandırıcısı isteği reddederse sunucu tarafında önerilen modele düşer.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": content}],
        ) as stream:
            message = stream.get_final_message()
        if message.stop_reason == "refusal":
            raise AnalysisError("Claude bu isteği işlemeyi reddetti.")
        text = "".join(b.text for b in message.content if b.type == "text").strip()
        if message.stop_reason == "max_tokens":
            text += "\n\n> ⚠️ Çıktı token sınırına ulaştı, son kısım eksik olabilir."
        return text


def _num(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _title_table(videos: list[Video]) -> str:
    return "\n".join(
        f"- {v.title} | {_num(v.views)} | {v.duration_label} | {v.published_at[:10]}" for v in videos
    )


def _video_ctx(channel: Channel, v: Video, rank: int) -> dict:
    return {
        "channel_title": channel.title,
        "rank": rank,
        "title": v.title,
        "url": v.url,
        "views": v.views,
        "likes": v.likes,
        "comments": v.comments,
        "duration": v.duration_label,
        "published_at": v.published_at[:10],
        "tags": ", ".join(v.tags),
        "metrics": json.dumps(v.script_metrics(), ensure_ascii=False),
        "transcript_source": v.transcript_source,
        "transcript_language": v.transcript_language,
        "description": v.description,
        "first_30s": v.first_seconds_text(30),
        "transcript": v.transcript_with_timestamps(),
    }


def _detect_language(channel: Channel, videos: list[Video]) -> str:
    for code in [channel.default_language] + [v.default_language for v in videos] + [v.transcript_language for v in videos]:
        if code:
            return code.split("-")[0].lower()
    return ""


def run_analysis(
    channel_url: str,
    progress: Progress,
    video_type: str = "long",
    content_language: str = "",
) -> tuple[dict, bytes]:
    yt = YouTubeClient()
    claude = ClaudeRunner()

    progress("Kanal bulunuyor…", 3)
    channel_id = yt.resolve_channel_id(channel_url)
    channel = yt.get_channel(channel_id)

    progress(f"'{channel.title}' kanalının en çok izlenen videoları çekiliyor…", 8)
    popular = yt.most_viewed(channel_id, video_type=video_type, limit=config.PATTERN_VIDEO_COUNT)
    if not popular:
        raise AnalysisError("Bu kanalda seçilen türde (uzun video / shorts) video bulunamadı.")
    recent = yt.recent_uploads(channel.uploads_playlist, video_type=video_type, limit=20)
    top = popular[: config.TOP_VIDEO_COUNT]

    lang_hint = _detect_language(channel, top)
    preferred = [l for l in [lang_hint, "en", "tr"] if l]

    progress("Transkriptler ve thumbnail'lar indiriliyor…", 14)
    thumb_videos = popular[: max(config.PATTERN_THUMBNAIL_COUNT, len(top))]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda v: fetch_transcript(v, preferred), top))
        list(pool.map(download_thumbnail, thumb_videos))

    missing = [v.title for v in top if not v.transcript]
    lang_code = content_language or lang_hint or _detect_language(channel, top)
    language_label = LANGUAGE_NAMES.get(lang_code, lang_code or "kanalın dili")

    # 1) Video bazlı derin analiz (paralel)
    progress(f"En çok izlenen {len(top)} video Claude ile analiz ediliyor (script, hook, kurgu, thumbnail)…", 22)

    def analyze(idx_v):
        idx, v = idx_v
        content: list[dict] = []
        if v.thumbnail_bytes:
            content.append(_image_block(v.thumbnail_bytes))
        content.append({"type": "text", "text": prompts.video_analysis_prompt(_video_ctx(channel, v, idx + 1))})
        return claude.run(content, max_tokens=32000)

    with ThreadPoolExecutor(max_workers=5) as pool:
        video_analyses = list(pool.map(analyze, enumerate(top)))

    analyses_md = "\n\n---\n\n".join(
        f"# Video #{i + 1}: {v.title}\n\n{a}" for i, (v, a) in enumerate(zip(top, video_analyses))
    )

    # 2) Kanal DNA raporu
    progress("Kanal DNA raporu çıkarılıyor (başlık, thumbnail, script ve kurgu sistemleri)…", 60)
    cadence = upload_cadence(recent)
    channel_info = "\n".join(
        [
            f"- Kanal: {channel.title} ({channel.handle}) — https://www.youtube.com/channel/{channel.id}",
            f"- Abone: {_num(channel.subscribers)} | Toplam izlenme: {_num(channel.total_views)} | Video sayısı: {channel.video_count}",
            f"- Ülke: {channel.country or '-'} | Açılış: {channel.published_at[:10]} | Tespit edilen dil: {lang_hint or '-'}",
            f"- Kanal anahtar kelimeleri: {channel.keywords or '-'}",
            f"- Kanal açıklaması: {channel.description or '-'}",
        ]
    )
    dna_content: list[dict] = []
    for i, v in enumerate(thumb_videos):
        if v.thumbnail_bytes:
            dna_content.append({"type": "text", "text": f"Thumbnail {i + 1}: \"{v.title}\" — {_num(v.views)} izlenme"})
            dna_content.append(_image_block(v.thumbnail_bytes))
    dna_content.append(
        {
            "type": "text",
            "text": prompts.channel_dna_prompt(
                {
                    "channel_title": channel.title,
                    "top_count": len(top),
                    "thumb_count": sum(1 for v in thumb_videos if v.thumbnail_bytes),
                    "channel_info": channel_info,
                    "cadence": json.dumps(cadence, ensure_ascii=False) if cadence else "(hesaplanamadı)",
                    "top_titles": _title_table(popular),
                    "recent_titles": _title_table(recent),
                    "video_analyses": analyses_md,
                }
            ),
        }
    )
    dna_report = claude.run(dna_content, max_tokens=48000)

    # 3) Claude Projesi talimatı
    progress("Claude Projesi talimatı (adım adım sistem promptu) yazılıyor…", 82)
    knowledge_list = "\n".join(f"- {name}: {desc}" for name, desc in KNOWLEDGE_FILES.items())
    instructions = claude.run(
        [
            {
                "type": "text",
                "text": prompts.instructions_prompt(
                    {
                        "channel_title": channel.title,
                        "dna_report": dna_report,
                        "video_analyses": analyses_md,
                        "knowledge_files": knowledge_list,
                        "content_language": language_label,
                    }
                ),
            }
        ],
        max_tokens=48000,
    )

    progress("Proje paketi hazırlanıyor…", 95)
    result = {
        "channel": {
            "id": channel.id,
            "title": channel.title,
            "handle": channel.handle,
            "subscribers": channel.subscribers,
            "total_views": channel.total_views,
            "video_count": channel.video_count,
            "avatar_url": channel.avatar_url,
            "language": language_label,
        },
        "top_videos": [
            {
                "id": v.id,
                "title": v.title,
                "url": v.url,
                "views": v.views,
                "duration": v.duration_label,
                "thumbnail_url": v.thumbnail_url,
                "has_transcript": bool(v.transcript),
            }
            for v in top
        ],
        "missing_transcripts": missing,
        "instructions": instructions,
        "dna_report": dna_report,
        "video_analyses": analyses_md,
    }
    return result, build_bundle(channel, top, popular, recent, thumb_videos, result)
