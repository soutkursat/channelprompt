"""Kullanıcının yüklediği video verileri: başlık, transkript, thumbnail. Hiçbiri diske yazılmaz."""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field

# Zaman damgası olmayan transkriptlerde ilk 30 saniyeyi tahmin etmek için ortalama anlatım hızı.
DEFAULT_WPM = 150

_TS = r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:[.,](\d{1,3}))?"
_CUE_RE = re.compile(rf"^\s*{_TS}\s*-->\s*{_TS}")
_LINE_TS_RE = re.compile(rf"^\s*[\[(]?{_TS}[\])]?\s*[-–:]?\s*(.*)$")


def _to_seconds(h, m, s, ms) -> float:
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + (int(ms.ljust(3, "0")) / 1000 if ms else 0)


def format_seconds(total: float) -> str:
    total = int(total)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def parse_duration(value: str) -> int:
    """'12:34', '1:02:03' veya '754' → saniye. Anlaşılmazsa 0."""
    value = (value or "").strip()
    if re.fullmatch(r"\d+", value):
        return int(value)
    m = re.fullmatch(r"(?:(\d+):)?(\d{1,2}):(\d{2})", value)
    return _to_seconds(m.group(1), m.group(2), m.group(3), None) if m else 0


def parse_views(value: str) -> int:
    value = (value or "").strip().lower().replace(" ", "")
    m = re.fullmatch(r"([\d.,]+)(k|b|bin|m|mn|milyon)?", value)
    if not m:
        return 0
    num, unit = m.groups()
    if unit:
        number = float(num.replace(",", "."))
        return int(number * (1_000 if unit in ("k", "b", "bin") else 1_000_000))
    return int(re.sub(r"[.,]", "", num) or 0)


def parse_transcript(raw: str) -> tuple[list[dict], bool]:
    """SRT / VTT / zaman damgalı satırlar / düz metin → [{start, text}], zaman damgası var mı?"""
    raw = (raw or "").replace("\r\n", "\n").replace("﻿", "").strip()
    if not raw:
        return [], False
    lines = raw.split("\n")

    # SRT / VTT: "00:00:01,000 --> 00:00:04,000" satırlarından sonra metin gelir.
    if any(_CUE_RE.match(line) for line in lines[:50]):
        segments, current, start = [], [], None
        for line in lines + [""]:
            cue = _CUE_RE.match(line)
            if cue:
                start = _to_seconds(*cue.groups()[:4])
                current = []
            elif not line.strip():
                if start is not None and current:
                    segments.append({"start": start, "text": " ".join(current)})
                start, current = None, []
            elif start is not None:
                text = re.sub(r"<[^>]+>", "", line).strip()
                if text and (not current or current[-1] != text):
                    current.append(text)
        return _dedupe(segments), True

    # YouTube'un "Transkripti göster" kopyası: "0:05 metin" veya "0:05" ardından metin satırı.
    timed, pending = [], None
    for line in lines:
        if not line.strip():
            continue
        m = _LINE_TS_RE.match(line)
        if m:
            start = _to_seconds(*m.groups()[:4])
            text = m.group(5).strip()
            if text:
                timed.append({"start": start, "text": text})
                pending = None
            else:
                pending = start
        elif pending is not None:
            timed.append({"start": pending, "text": line.strip()})
            pending = None
        elif timed:
            timed[-1]["text"] += " " + line.strip()
    if len(timed) >= 3 and sum(len(s["text"].split()) for s in timed) > 20:
        return timed, True

    return [{"start": 0.0, "text": " ".join(line.strip() for line in lines if line.strip())}], False


def _dedupe(segments: list[dict]) -> list[dict]:
    """Otomatik altyazılardaki tekrar eden satırları temizler."""
    out: list[dict] = []
    for s in segments:
        if out and s["text"] == out[-1]["text"]:
            continue
        out.append(s)
    return out


@dataclass
class VideoInput:
    title: str
    transcript_raw: str
    views: int = 0
    duration_seconds: int = 0
    description: str = ""
    thumbnail_bytes: bytes | None = None
    thumbnail_type: str = "image/jpeg"
    segments: list[dict] = field(default_factory=list)
    has_timestamps: bool = False

    def __post_init__(self):
        self.segments, self.has_timestamps = parse_transcript(self.transcript_raw)

    @property
    def duration_label(self) -> str:
        return format_seconds(self.duration_seconds) if self.duration_seconds else "bilinmiyor"

    @property
    def text(self) -> str:
        return " ".join(s["text"] for s in self.segments)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    def first_30s(self) -> tuple[str, bool]:
        """İlk 30 saniyenin metni ve bunun tahmini olup olmadığı."""
        if self.has_timestamps:
            return " ".join(s["text"] for s in self.segments if s["start"] < 30), False
        words = self.text.split()
        wpm = self.wpm or DEFAULT_WPM
        return " ".join(words[: round(wpm / 2)]), True

    @property
    def wpm(self) -> int:
        if self.duration_seconds:
            return round(self.word_count / (self.duration_seconds / 60))
        return 0

    def transcript_for_prompt(self) -> str:
        if self.has_timestamps:
            return "\n".join(f"[{format_seconds(s['start'])}] {s['text']}" for s in self.segments)
        return self.text

    def metrics(self) -> dict:
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", self.text) if s.strip()]
        lengths = [len(s.split()) for s in sentences] or [0]
        first, _ = self.first_30s()
        return {
            "kelime_sayisi": self.word_count,
            "dakika_basi_kelime": self.wpm or "süre girilmedi",
            "cumle_sayisi": len(sentences),
            "ortalama_cumle_uzunlugu": round(statistics.mean(lengths), 1),
            "ilk_30sn_kelime": len(first.split()),
            "soru_cumlesi_sayisi": self.text.count("?"),
        }
