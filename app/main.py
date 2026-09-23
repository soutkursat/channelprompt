"""Web uygulaması: kanal linki al → arka planda analiz et → sonuç ve ZIP paketi sun."""
from __future__ import annotations

import json
import re
import threading
import time
import traceback
import uuid
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from . import config
from .analyzer import AnalysisError, run_analysis
from .youtube import YouTubeError

app = FastAPI(title="Kanal Klonlayıcı")
STATIC = Path(__file__).parent / "static"
JOBS_DIR = config.DATA_DIR / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()
_jobs: dict[str, dict] = {}


def _job_dir(job_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise HTTPException(404, "Geçersiz iş numarası.")
    return JOBS_DIR / job_id


def _save_state(job_id: str, state: dict) -> None:
    with _lock:
        _jobs[job_id] = state
    (_job_dir(job_id) / "state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def _load_state(job_id: str) -> dict:
    with _lock:
        if job_id in _jobs:
            return _jobs[job_id]
    path = _job_dir(job_id) / "state.json"
    if not path.exists():
        raise HTTPException(404, "Analiz bulunamadı.")
    return json.loads(path.read_text(encoding="utf-8"))


def _worker(job_id: str, url: str, video_type: str, language: str) -> None:
    state = _load_state(job_id)

    def progress(message: str, percent: int) -> None:
        state.update(status="running", message=message, percent=percent)
        _save_state(job_id, state)

    try:
        result, bundle = run_analysis(url, progress, video_type=video_type, content_language=language)
        (_job_dir(job_id) / "result.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        (_job_dir(job_id) / "paket.zip").write_bytes(bundle)
        state.update(status="done", message="Analiz tamamlandı.", percent=100, channel_title=result["channel"]["title"])
    except (YouTubeError, AnalysisError) as e:
        state.update(status="error", message=str(e))
    except Exception as e:  # beklenmeyen hata
        traceback.print_exc()
        state.update(status="error", message=f"Beklenmeyen hata: {e}")
    state["finished_at"] = time.time()
    _save_state(job_id, state)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    return html.replace("__ACCESS_REQUIRED__", "true" if config.ACCESS_CODE else "false")


@app.post("/api/analyze")
def analyze(
    url: str = Form(...),
    video_type: str = Form("long"),
    language: str = Form(""),
    access_code: str = Form(""),
) -> JSONResponse:
    if config.ACCESS_CODE and access_code.strip() != config.ACCESS_CODE:
        raise HTTPException(403, "Erişim kodu hatalı.")
    if video_type not in {"long", "shorts", "all"}:
        raise HTTPException(400, "Geçersiz video türü.")
    if not url.strip():
        raise HTTPException(400, "Kanal linki gerekli.")
    job_id = uuid.uuid4().hex
    _job_dir(job_id).mkdir(parents=True)
    _save_state(
        job_id,
        {"id": job_id, "status": "queued", "message": "Sıraya alındı…", "percent": 0, "url": url.strip(),
         "created_at": time.time()},
    )
    threading.Thread(target=_worker, args=(job_id, url.strip(), video_type, language.strip().lower()),
                     daemon=True).start()
    return JSONResponse({"job_id": job_id})


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> JSONResponse:
    return JSONResponse(_load_state(job_id))


@app.get("/api/jobs/{job_id}/result")
def job_result(job_id: str) -> Response:
    path = _job_dir(job_id) / "result.json"
    if not path.exists():
        raise HTTPException(404, "Sonuç henüz hazır değil.")
    return Response(path.read_text(encoding="utf-8"), media_type="application/json")


@app.get("/api/jobs/{job_id}/download")
def job_download(job_id: str) -> FileResponse:
    path = _job_dir(job_id) / "paket.zip"
    if not path.exists():
        raise HTTPException(404, "Paket henüz hazır değil.")
    state = _load_state(job_id)
    name = re.sub(r"[^\w-]+", "-", state.get("channel_title", "kanal"), flags=re.UNICODE).strip("-") or "kanal"
    return FileResponse(path, media_type="application/zip", filename=f"{name}-claude-proje-paketi.zip")


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "youtube_key": bool(config.YOUTUBE_API_KEY),
        "anthropic_key": bool(config.ANTHROPIC_API_KEY),
        "model": config.CLAUDE_MODEL,
    }
