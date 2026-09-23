"""Ortam değişkenlerinden okunan ayarlar."""
import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Analiz modeli. Varsayılan: Claude Opus 5.
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5")
# low | medium | high | xhigh | max
CLAUDE_EFFORT = os.getenv("CLAUDE_EFFORT", "high")

# Öğrenci erişim kodu. Boş bırakılırsa herkes kullanabilir.
ACCESS_CODE = os.getenv("ACCESS_CODE", "")

# Sonuçlar yalnızca bellekte tutulur ve bu süre sonunda silinir (dakika).
RESULT_TTL_MINUTES = int(os.getenv("RESULT_TTL_MINUTES", "120"))
# Aynı anda çalışabilecek analiz sayısı.
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "3"))

MAX_VIDEOS = 5
MAX_THUMBNAIL_BYTES = 5 * 1024 * 1024
MAX_TRANSCRIPT_CHARS = 200_000
