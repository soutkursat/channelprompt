"""Analiz hattı: kullanıcı verileri → Claude video analizleri → Kanal DNA → Proje talimatı → paket."""
from __future__ import annotations

import base64
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

import anthropic

from . import config, prompts
from .bundle import KNOWLEDGE_FILES, build_bundle
from .inputs import VideoInput

Progress = Callable[[str, int], None]


class AnalysisError(Exception):
    pass


@dataclass
class ChannelInput:
    url: str
    name: str
    language: str
    notes: str
    other_titles: str


def _image_block(v: VideoInput) -> dict:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": v.thumbnail_type,
            "data": base64.standard_b64encode(v.thumbnail_bytes).decode(),
        },
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
    return f"{n:,}".replace(",", ".") if n else "bilinmiyor"


def _channel_label(ch: ChannelInput) -> str:
    return ch.name or ch.url or "Analiz edilen kanal"


def _video_ctx(ch: ChannelInput, v: VideoInput, rank: int) -> dict:
    first, estimated = v.first_30s()
    return {
        "channel_title": _channel_label(ch),
        "rank": rank,
        "title": v.title,
        "views": _num(v.views),
        "duration": v.duration_label,
        "has_thumbnail": bool(v.thumbnail_bytes),
        "metrics": json.dumps(v.metrics(), ensure_ascii=False),
        "timestamps": v.has_timestamps,
        "description": v.description,
        "first_30s": first,
        "first_30s_estimated": estimated,
        "transcript": v.transcript_for_prompt(),
    }


def run_analysis(ch: ChannelInput, videos: list[VideoInput], progress: Progress) -> tuple[dict, bytes]:
    claude = ClaudeRunner()
    label = _channel_label(ch)
    language = ch.language or "analiz edilen kanalın dili (transkriptlerin dili)"

    # 1) Video bazlı derin analiz (paralel)
    progress(f"{len(videos)} video Claude ile analiz ediliyor (hook, script yapısı, kurgu, başlık, thumbnail)…", 8)

    def analyze(idx_v):
        idx, v = idx_v
        content: list[dict] = []
        if v.thumbnail_bytes:
            content.append(_image_block(v))
        content.append({"type": "text", "text": prompts.video_analysis_prompt(_video_ctx(ch, v, idx + 1))})
        return claude.run(content, max_tokens=32000)

    with ThreadPoolExecutor(max_workers=5) as pool:
        video_analyses = list(pool.map(analyze, enumerate(videos)))

    analyses_md = "\n\n---\n\n".join(
        f"# Video #{i + 1}: {v.title}\n\n{a}" for i, (v, a) in enumerate(zip(videos, video_analyses))
    )

    # 2) Kanal DNA raporu
    progress("Kanal DNA raporu çıkarılıyor (başlık, thumbnail, script ve kurgu sistemleri)…", 55)
    channel_info = "\n".join(
        [
            f"- Kanal: {label}" + (f" — {ch.url}" if ch.url and ch.url != label else ""),
            f"- İçerik dili: {language}",
            f"- Kullanıcının notları: {ch.notes or '-'}",
        ]
    )
    video_table = "\n".join(
        f"- {v.title} | izlenme: {_num(v.views)} | süre: {v.duration_label}" for v in videos
    )
    dna_content: list[dict] = []
    for i, v in enumerate(videos):
        if v.thumbnail_bytes:
            dna_content.append({"type": "text", "text": f"Thumbnail {i + 1}: \"{v.title}\""})
            dna_content.append(_image_block(v))
    dna_content.append(
        {
            "type": "text",
            "text": prompts.channel_dna_prompt(
                {
                    "channel_title": label,
                    "top_count": len(videos),
                    "thumb_count": sum(1 for v in videos if v.thumbnail_bytes),
                    "channel_info": channel_info,
                    "top_titles": video_table,
                    "other_titles": ch.other_titles.strip() or "(girilmedi)",
                    "video_analyses": analyses_md,
                }
            ),
        }
    )
    dna_report = claude.run(dna_content, max_tokens=48000)

    # 3) Claude Projesi talimatı
    progress("Claude Projesi talimatı (adım adım sistem promptu) yazılıyor…", 80)
    knowledge_list = "\n".join(f"- {name}: {desc}" for name, desc in KNOWLEDGE_FILES.items())
    instructions = claude.run(
        [
            {
                "type": "text",
                "text": prompts.instructions_prompt(
                    {
                        "channel_title": label,
                        "dna_report": dna_report,
                        "video_analyses": analyses_md,
                        "knowledge_files": knowledge_list,
                        "content_language": language,
                    }
                ),
            }
        ],
        max_tokens=48000,
    )

    progress("Proje paketi hazırlanıyor…", 95)
    result = {
        "channel": {"title": label, "url": ch.url, "language": language},
        "videos": [
            {
                "title": v.title,
                "views": v.views,
                "duration": v.duration_label,
                "words": v.word_count,
                "has_thumbnail": bool(v.thumbnail_bytes),
                "has_timestamps": v.has_timestamps,
            }
            for v in videos
        ],
        "instructions": instructions,
        "dna_report": dna_report,
        "video_analyses": analyses_md,
    }
    return result, build_bundle(label, videos, result, ch.other_titles)
