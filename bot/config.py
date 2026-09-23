import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CACHE = ROOT / "data" / "cache"
SITE_DATA = ROOT / "site" / "src" / "data"
SITE_THUMBS = ROOT / "site" / "public" / "thumbs"

CHANNEL = "https://www.youtube.com/@KEBABTVKBH"
TABS = ["videos", "shorts"]

MAX_COMMENTS = 300          # per video, sorted by "top"
COMMENTS_FOR_ANALYSIS = 200

# Load ../.env (KEY=value lines) without overriding real env vars.
_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text("utf-8").splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"'))

# LLM gateway: Moodly (speaks the Anthropic Messages API).
LLM_BASE_URL = os.environ.get("KEBAB_LLM_BASE_URL", "https://moodlyai.app")
LLM_API_KEY = (os.environ.get("MOODLY_API_KEY")
               or os.environ.get("ANTHROPIC_AUTH_TOKEN")
               or os.environ.get("ANTHROPIC_API_KEY"))
MODEL = os.environ.get("KEBAB_MODEL", "claude-opus-5")

for p in (RAW, CACHE, SITE_DATA, SITE_THUMBS):
    p.mkdir(parents=True, exist_ok=True)


def vdir(video_id: str) -> Path:
    d = RAW / video_id
    d.mkdir(parents=True, exist_ok=True)
    return d
