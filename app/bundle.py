"""Öğrencinin Claude Projesi'ne yükleyeceği ZIP paketini üretir."""
from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime, timezone

from .youtube import Channel, Video

# Proje bilgi dosyaları: talimat promptu bu adlarla referans verir.
KNOWLEDGE_FILES = {
    "KANAL_DNA_RAPORU.md": "Kanalın konsept, fikir filtresi, başlık sistemi, thumbnail sistemi, script blueprint'i, "
    "kurgu/prodüksiyon reçetesi ve SEO stratejisi.",
    "VIDEO_ANALIZLERI.md": "En çok izlenen videoların tek tek derin analizi (ilk 30 saniye hook anatomisi, beat sheet, "
    "retention araçları, ton, kurgu, başlık ve thumbnail çözümlemesi).",
    "ORNEK_SCRIPTLER.md": "En çok izlenen videoların tam, zaman damgalı transkriptleri — ton, ritim ve yapı için "
    "referans scriptler.",
    "BASLIK_VE_METRIK_KUTUPHANESI.md": "Kanalın en çok izlenen ve son yüklenen videolarının başlıkları, izlenmeleri, "
    "süreleri, etiketleri ve açıklamaları.",
    "Thumbnail görselleri (01_....jpg, 02_....jpg …) + THUMBNAIL_REFERANS.md": "Kanalın en çok izlenen videolarının thumbnail görselleri ve "
    "hangi görselin hangi videoya ait olduğu.",
}


def _slug(text: str, n: int = 40) -> str:
    s = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    return re.sub(r"[\s_-]+", "-", s)[:n].strip("-") or "video"


def _num(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _library(channel: Channel, popular: list[Video], recent: list[Video]) -> str:
    out = [f"# Başlık ve Metrik Kütüphanesi — {channel.title}\n"]
    out.append(
        f"Abone: {_num(channel.subscribers)} · Toplam izlenme: {_num(channel.total_views)} · "
        f"Video sayısı: {channel.video_count}\n"
    )
    for heading, videos in (("En çok izlenen videolar", popular), ("Son yüklenen videolar", recent)):
        out.append(f"\n## {heading}\n")
        out.append("| # | Başlık | İzlenme | Süre | Tarih |\n|---|---|---|---|---|")
        for i, v in enumerate(videos, 1):
            title = v.title.replace("|", "/")
            out.append(f"| {i} | [{title}]({v.url}) | {_num(v.views)} | {v.duration_label} | {v.published_at[:10]} |")
    out.append("\n## Detaylar: etiketler ve açıklamalar (en çok izlenenler)\n")
    for i, v in enumerate(popular[:15], 1):
        out.append(f"### {i}. {v.title}\n")
        out.append(f"- İzlenme: {_num(v.views)} · Beğeni: {_num(v.likes)} · Yorum: {_num(v.comments)}")
        out.append(f"- Etiketler: {', '.join(v.tags) if v.tags else '(yok)'}\n")
        out.append("```text\n" + (v.description or "(açıklama yok)") + "\n```\n")
    return "\n".join(out)


def _scripts(top: list[Video]) -> str:
    out = ["# Örnek Scriptler (en çok izlenen videoların transkriptleri)\n"]
    for i, v in enumerate(top, 1):
        out.append(f"\n## {i}. {v.title}\n")
        out.append(f"- URL: {v.url}\n- İzlenme: {_num(v.views)} · Süre: {v.duration_label}")
        out.append(f"- Transkript kaynağı: {v.transcript_source or 'alınamadı'} ({v.transcript_language or '-'})")
        m = v.script_metrics()
        out.append(
            f"- Kelime: {m['kelime_sayisi']} · Dakika başı kelime: {m['dakika_basi_kelime']} · "
            f"Ort. cümle uzunluğu: {m['ortalama_cumle_uzunlugu']} kelime\n"
        )
        if v.transcript:
            out.append("### İlk 30 saniye\n")
            out.append("> " + v.first_seconds_text(30) + "\n")
            out.append("### Tam transkript\n")
            out.append(v.transcript_with_timestamps())
        else:
            out.append("_Bu video için transkript alınamadı._")
    return "\n".join(out)


def _setup_guide(channel: Channel, thumb_files: list[str]) -> str:
    files = "\n".join(f"   - `{name}`" for name in [
        "KANAL_DNA_RAPORU.md",
        "VIDEO_ANALIZLERI.md",
        "ORNEK_SCRIPTLER.md",
        "BASLIK_VE_METRIK_KUTUPHANESI.md",
        "THUMBNAIL_REFERANS.md",
    ])
    return f"""# Kurulum Rehberi — {channel.title} Kanal Klonu

Bu paket, **{channel.title}** kanalının analizinden üretildi ({datetime.now(timezone.utc):%Y-%m-%d}).
Aşağıdaki adımlarla Claude'da kanalını yönetecek projeyi 5 dakikada kurarsın.

## 1. Projeyi oluştur
1. https://claude.ai adresine gir → sol menüden **Projects** → **Create project**.
2. Proje adı: `{channel.title} Formülü — Kanalım` (istediğin adı verebilirsin).

## 2. Talimatı yükle
1. Proje sayfasında **Instructions** (Proje talimatları) → **Edit**.
2. `01_PROJE_TALIMATI.md` dosyasının **tüm içeriğini** kopyalayıp yapıştır → **Save**.

## 3. Bilgi dosyalarını yükle (Project knowledge)
1. Proje sayfasında **Files / Project knowledge** → **+** → **Upload from device**.
2. Şu dosyaları yükle:
{files}
3. `thumbnails/` klasöründeki {len(thumb_files)} görseli de aynı yere yükle (referans thumbnail'lar).

## 4. Kullanmaya başla
1. Projenin içinde yeni bir sohbet aç ve **"Merhaba, başlayalım"** yaz.
2. Claude sana kanal konseptini özetleyip 5 video fikri sunacak.
3. Bir fikir seç → script → başlıklar → thumbnail hook'ları → (istersen) kapak tasarımı → SEO açıklaması.
4. Kısa komutlar: `/fikir`, `/script`, `/baslik`, `/thumbnail`, `/kapak`, `/seo`, `/paket`, `/revize` (talimatta açıklanıyor).

## İpuçları
- Her yeni video için projede **yeni bir sohbet** aç; bilgi dosyaları ve talimat her sohbette otomatik kullanılır.
- Kendi performans verilerini (hangi videon tuttu) zamanla projeye not olarak eklersen Claude formülü sana göre de ince ayarlar.
- Rakip kanalın formülünü kopyala, cümlelerini değil: scriptler her zaman özgün olmalı.
"""


def build_bundle(
    channel: Channel,
    top: list[Video],
    popular: list[Video],
    recent: list[Video],
    thumb_videos: list[Video],
    result: dict,
) -> bytes:
    buf = io.BytesIO()
    thumb_files: list[str] = []
    thumb_ref = [f"# Thumbnail Referansları — {channel.title}\n",
                 "Görseller izlenme sırasına göre numaralandırılmıştır.\n",
                 "| Dosya | Video başlığı | İzlenme |", "|---|---|---|"]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for i, v in enumerate(thumb_videos, 1):
            if not v.thumbnail_bytes:
                continue
            name = f"thumbnails/{i:02d}_{_slug(v.title)}.jpg"
            z.writestr(name, v.thumbnail_bytes)
            thumb_files.append(name)
            thumb_ref.append(f"| `{name.split('/')[-1]}` | {v.title.replace('|', '/')} | {_num(v.views)} |")

        z.writestr("00_KURULUM_REHBERI.md", _setup_guide(channel, thumb_files))
        z.writestr("01_PROJE_TALIMATI.md", result["instructions"])
        z.writestr("KANAL_DNA_RAPORU.md", result["dna_report"])
        z.writestr("VIDEO_ANALIZLERI.md", result["video_analyses"])
        z.writestr("ORNEK_SCRIPTLER.md", _scripts(top))
        z.writestr("BASLIK_VE_METRIK_KUTUPHANESI.md", _library(channel, popular, recent))
        z.writestr("THUMBNAIL_REFERANS.md", "\n".join(thumb_ref) + "\n")
    return buf.getvalue()
