"""Ortam değişkenlerinden okunan ayarlar."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Analiz modeli. Varsayılan: Claude Opus 5.
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5")
# low | medium | high | xhigh | max
CLAUDE_EFFORT = os.getenv("CLAUDE_EFFORT", "high")

# Öğrenci erişim kodu. Boş bırakılırsa herkes kullanabilir.
ACCESS_CODE = os.getenv("ACCESS_CODE", "")

# YouTube bulut sunucu IP'lerinden altyazı çekmeyi engelleyebilir.
# Gerekirse bir proxy (ör. http://user:pass@host:port) tanımlayın.
YT_PROXY_URL = os.getenv("YT_PROXY_URL", "")
# İsteğe bağlı yedek altyazı servisi (https://supadata.ai).
SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY", "")

TOP_VIDEO_COUNT = int(os.getenv("TOP_VIDEO_COUNT", "5"))
# Kanal geneli başlık / thumbnail desen analizi için kaç video kullanılacak.
PATTERN_VIDEO_COUNT = int(os.getenv("PATTERN_VIDEO_COUNT", "30"))
PATTERN_THUMBNAIL_COUNT = int(os.getenv("PATTERN_THUMBNAIL_COUNT", "12"))
# Bu sürenin (saniye) altındaki videolar Shorts kabul edilir.
SHORTS_MAX_SECONDS = int(os.getenv("SHORTS_MAX_SECONDS", "180"))
