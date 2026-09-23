"""Öğrencinin Claude Projesi'ne yükleyeceği ZIP paketini bellekte üretir."""
from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime, timezone

from .inputs import VideoInput

# Proje bilgi dosyaları: talimat promptu bu adlarla referans verir.
KNOWLEDGE_FILES = {
    "KANAL_DNA_RAPORU.md": "Kanalın konsept, fikir filtresi, başlık sistemi, thumbnail sistemi, script blueprint'i, "
    "kurgu/prodüksiyon reçetesi ve SEO stratejisi.",
    "VIDEO_ANALIZLERI.md": "En çok izlenen videoların tek tek derin analizi (ilk 30 saniye hook anatomisi, beat sheet, "
    "retention araçları, ton, kurgu, başlık ve thumbnail çözümlemesi).",
    "ORNEK_SCRIPTLER.md": "En çok izlenen videoların tam transkriptleri: ton, ritim ve yapı için referans scriptler.",
    "BASLIK_KUTUPHANESI.md": "Analiz edilen videoların başlıkları, izlenmeleri, süreleri, açıklamaları ve kanalın diğer başlıkları.",
    "Thumbnail görselleri (01_....jpg, 02_....jpg …) + THUMBNAIL_REFERANS.md": "Başarılı videoların thumbnail "
    "görselleri ve hangi görselin hangi videoya ait olduğu.",
}

_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}


def _slug(text: str, n: int = 40) -> str:
    s = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    return re.sub(r"[\s_-]+", "-", s)[:n].strip("-") or "video"


def _num(n: int) -> str:
    return f"{n:,}".replace(",", ".") if n else "-"


def _library(label: str, videos: list[VideoInput], other_titles: str) -> str:
    out = [f"# Başlık Kütüphanesi — {label}\n", "## Analiz edilen başarılı videolar\n",
           "| # | Başlık | İzlenme | Süre |", "|---|---|---|---|"]
    for i, v in enumerate(videos, 1):
        out.append(f"| {i} | {v.title.replace('|', '/')} | {_num(v.views)} | {v.duration_label} |")
    if other_titles.strip():
        out.append("\n## Kanalın diğer başlıkları\n")
        out += [f"- {t.strip()}" for t in other_titles.splitlines() if t.strip()]
    described = [v for v in videos if v.description.strip()]
    if described:
        out.append("\n## Video açıklamaları\n")
        for v in described:
            out.append(f"### {v.title}\n")
            out.append("```text\n" + v.description.strip() + "\n```\n")
    return "\n".join(out) + "\n"


def _scripts(videos: list[VideoInput]) -> str:
    out = ["# Örnek Scriptler (başarılı videoların transkriptleri)\n"]
    for i, v in enumerate(videos, 1):
        m = v.metrics()
        first, estimated = v.first_30s()
        out.append(f"\n## {i}. {v.title}\n")
        out.append(f"- İzlenme: {_num(v.views)} · Süre: {v.duration_label}")
        out.append(
            f"- Kelime: {m['kelime_sayisi']} · Dakika başı kelime: {m['dakika_basi_kelime']} · "
            f"Ort. cümle uzunluğu: {m['ortalama_cumle_uzunlugu']} kelime\n"
        )
        out.append("### İlk 30 saniye" + (" (tahmini)" if estimated else "") + "\n")
        out.append("> " + first + "\n")
        out.append("### Tam transkript\n")
        out.append(v.transcript_for_prompt())
    return "\n".join(out) + "\n"


def _setup_guide(label: str, thumb_count: int) -> str:
    names = ["KANAL_DNA_RAPORU.md", "VIDEO_ANALIZLERI.md", "ORNEK_SCRIPTLER.md", "BASLIK_KUTUPHANESI.md"]
    if thumb_count:
        names.append("THUMBNAIL_REFERANS.md")
    files = "\n".join(f"   - `{name}`" for name in names)
    thumbs = (f"3. `thumbnails/` klasöründeki {thumb_count} görseli de aynı yere yükle (referans thumbnail'lar).\n"
              if thumb_count else "")
    return f"""# Kurulum Rehberi — {label} Formülü

Bu paket **{label}** analizinden üretildi ({datetime.now(timezone.utc):%Y-%m-%d}).
Aşağıdaki adımlarla Claude'da kanalını yönetecek projeyi 5 dakikada kurarsın.

## 1. Projeyi oluştur
1. https://claude.ai → sol menüden **Projects** → **Create project**.
2. Proje adı: `{label} Formülü — Kanalım` (istediğin adı verebilirsin).

## 2. Talimatı yükle
1. Proje sayfasında **Instructions** → **Edit**.
2. `01_PROJE_TALIMATI.md` dosyasının **tüm içeriğini** kopyalayıp yapıştır → **Save**.

## 3. Bilgi dosyalarını yükle (Project knowledge)
1. Proje sayfasında **Files / Project knowledge** → **+** → **Upload from device**.
2. Şu dosyaları yükle:
{files}
{thumbs}
## 4. Kullanmaya başla
1. Projede yeni bir sohbet aç ve **"Merhaba, başlayalım"** yaz.
2. Claude kanal konseptini özetleyip 5 video fikri sunar.
3. Bir fikir seç → script → başlıklar → thumbnail hook'ları → (istersen) kapak tasarımı → SEO açıklaması.
4. Kısa komutlar: `/fikir`, `/script`, `/baslik`, `/thumbnail`, `/kapak`, `/seo`, `/paket`, `/revize`.

## İpuçları
- Her yeni video için projede **yeni bir sohbet** aç. Talimat ve dosyalar her sohbette otomatik kullanılır.
- Kendi videolarının performansını zamanla projeye not olarak eklersen Claude formülü sana göre ince ayarlar.
- Formülü kopyala, cümleleri değil: scriptler her zaman özgün olmalı.
"""


def build_bundle(label: str, videos: list[VideoInput], result: dict, other_titles: str = "") -> bytes:
    buf = io.BytesIO()
    thumb_ref = [f"# Thumbnail Referansları — {label}\n", "| Dosya | Video başlığı | İzlenme |", "|---|---|---|"]
    thumb_count = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for i, v in enumerate(videos, 1):
            if not v.thumbnail_bytes:
                continue
            name = f"{i:02d}_{_slug(v.title)}.{_EXT.get(v.thumbnail_type, 'jpg')}"
            z.writestr(f"thumbnails/{name}", v.thumbnail_bytes)
            thumb_ref.append(f"| `{name}` | {v.title.replace('|', '/')} | {_num(v.views)} |")
            thumb_count += 1

        z.writestr("00_KURULUM_REHBERI.md", _setup_guide(label, thumb_count))
        z.writestr("01_PROJE_TALIMATI.md", result["instructions"])
        z.writestr("KANAL_DNA_RAPORU.md", result["dna_report"])
        z.writestr("VIDEO_ANALIZLERI.md", result["video_analyses"])
        z.writestr("ORNEK_SCRIPTLER.md", _scripts(videos))
        z.writestr("BASLIK_KUTUPHANESI.md", _library(label, videos, other_titles))
        if thumb_count:
            z.writestr("THUMBNAIL_REFERANS.md", "\n".join(thumb_ref) + "\n")
    return buf.getvalue()
