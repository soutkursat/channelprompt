"""Web uygulaması: kullanıcı verilerini al → arka planda analiz et → sonuç ve ZIP paketi sun.

Yüklenen transkriptler, thumbnail'lar ve sonuçlar hiçbir yere kaydedilmez; yalnızca bellekte tutulur
ve RESULT_TTL_MINUTES sonunda silinir.
"""
from __future__ import annotations

import re
import threading
import time
import traceback
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import UploadFile

from . import config
from .analyzer import AnalysisError, ChannelInput, run_analysis
from .inputs import VideoInput, parse_duration, parse_views

app = FastAPI(title="Kanal Klonlayıcı")
STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")

_lock = threading.Lock()
_jobs: dict[str, dict] = {}
_slots = threading.BoundedSemaphore(config.MAX_CONCURRENT_JOBS)


def _image_type(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return None


def _cleanup() -> None:
    cutoff = time.time() - config.RESULT_TTL_MINUTES * 60
    with _lock:
        for job_id in [j for j, s in _jobs.items() if s.get("finished_at", time.time()) < cutoff]:
            del _jobs[job_id]


def _get_job(job_id: str) -> dict:
    with _lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Analiz bulunamadı ya da süresi doldu.")
    return job


def _worker(job_id: str, channel: ChannelInput, videos: list[VideoInput]) -> None:
    job = _get_job(job_id)

    def progress(message: str, percent: int) -> None:
        job.update(status="running", message=message, percent=percent)

    job.update(message="Sırada bekleniyor…")
    with _slots:
        try:
            result, bundle = run_analysis(channel, videos, progress)
            job.update(status="done", message="Analiz tamamlandı.", percent=100, result=result, bundle=bundle)
        except AnalysisError as e:
            job.update(status="error", message=str(e))
        except Exception as e:  # beklenmeyen hata
            traceback.print_exc()
            job.update(status="error", message=f"Beklenmeyen hata: {e}")
    job["finished_at"] = time.time()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    return html.replace("__ACCESS_REQUIRED__", "true" if config.ACCESS_CODE else "false")


@app.post("/api/analyze")
async def analyze(request: Request) -> JSONResponse:
    _cleanup()
    form = await request.form()

    def field(name: str, limit: int = 5000) -> str:
        value = form.get(name) or ""
        return value.strip()[:limit] if isinstance(value, str) else ""

    if config.ACCESS_CODE and field("access_code") != config.ACCESS_CODE:
        raise HTTPException(403, "Erişim kodu hatalı.")

    channel = ChannelInput(
        url=field("channel_url", 500),
        name=field("channel_name", 200),
        language=field("language", 50),
        notes=field("notes", 3000),
        other_titles=field("other_titles", 10000),
    )

    videos: list[VideoInput] = []
    for i in range(1, config.MAX_VIDEOS + 1):
        title = field(f"title_{i}", 300)
        transcript = field(f"transcript_{i}", config.MAX_TRANSCRIPT_CHARS)
        thumb = form.get(f"thumbnail_{i}")
        has_thumb = isinstance(thumb, UploadFile) and thumb.filename
        if not (title or transcript or has_thumb):
            continue
        if not title or not transcript:
            raise HTTPException(400, f"Video {i}: başlık ve transkript birlikte girilmeli.")
        thumb_bytes, thumb_type = None, "image/jpeg"
        if has_thumb:
            thumb_bytes = await thumb.read(config.MAX_THUMBNAIL_BYTES + 1)
            if len(thumb_bytes) > config.MAX_THUMBNAIL_BYTES:
                raise HTTPException(400, f"Video {i}: thumbnail 5 MB'tan büyük olamaz.")
            thumb_type = _image_type(thumb_bytes)
            if not thumb_type:
                raise HTTPException(400, f"Video {i}: thumbnail JPG, PNG, WEBP veya GIF olmalı.")
        video = VideoInput(
            title=title,
            transcript_raw=transcript,
            views=parse_views(field(f"views_{i}", 30)),
            duration_seconds=parse_duration(field(f"duration_{i}", 20)),
            description=field(f"description_{i}", 5000),
            thumbnail_bytes=thumb_bytes,
            thumbnail_type=thumb_type,
        )
        if video.word_count < 50:
            raise HTTPException(400, f"Video {i}: transkript çok kısa görünüyor (en az 50 kelime).")
        videos.append(video)

    if not videos:
        raise HTTPException(400, "En az bir videonun başlığını ve transkriptini gir.")

    job_id = uuid.uuid4().hex
    with _lock:
        _jobs[job_id] = {"status": "queued", "message": "Sıraya alındı…", "percent": 0, "created_at": time.time(),
                         "channel_title": channel.name or channel.url or "kanal"}
    threading.Thread(target=_worker, args=(job_id, channel, videos), daemon=True).start()
    return JSONResponse({"job_id": job_id})


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> JSONResponse:
    job = _get_job(job_id)
    return JSONResponse({k: job.get(k) for k in ("status", "message", "percent")})


@app.get("/api/jobs/{job_id}/result")
def job_result(job_id: str) -> JSONResponse:
    job = _get_job(job_id)
    if job["status"] != "done":
        raise HTTPException(404, "Sonuç henüz hazır değil.")
    return JSONResponse(job["result"])


@app.get("/api/jobs/{job_id}/download")
def job_download(job_id: str) -> Response:
    job = _get_job(job_id)
    if job["status"] != "done":
        raise HTTPException(404, "Paket henüz hazır değil.")
    name = re.sub(r"[^A-Za-z0-9-]+", "-", job["channel_title"]).strip("-")[:60] or "kanal"
    return Response(
        job["bundle"],
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}-claude-proje-paketi.zip"'},
    )


@app.get("/health")
def health() -> dict:
    return {"ok": True, "anthropic_key": bool(config.ANTHROPIC_API_KEY), "model": config.CLAUDE_MODEL}
