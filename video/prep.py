"""Gather images for the promo video and synthesize an original soundtrack.

Timeline (30 fps) must match src/timeline.ts.
"""
import json
import shutil
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
SITE = ROOT.parent / "site"
PUB = ROOT / "public"
PUB.mkdir(exist_ok=True)

FPS = 30
T = json.loads((ROOT / "src" / "timeline.json").read_text("utf-8"))

# ---------- images + data ----------
places = json.loads((SITE / "src/data/places.json").read_text("utf-8"))
videos = {v["id"]: v for v in json.loads((SITE / "src/data/videos.json").read_text("utf-8"))}


def thumb(vid):
    src = next((SITE / "public/thumbs").glob(f"{vid}.*"))
    dst = PUB / f"t-{vid}{src.suffix}"
    shutil.copy(src, dst)
    return dst.name


kbh = [p for p in places if p["score"] is not None and (p["city"] or "").startswith("København")]
top3 = kbh[:3]
top_ids = {p["latest"] for p in top3}
# Zap through a spread of other episodes with real scores.
zap_pool = [v for v in videos.values() if v["score"] is not None and v["id"] not in top_ids]
zap_pool.sort(key=lambda v: v["date"] or "", reverse=True)
zaps = zap_pool[:: max(1, len(zap_pool) // T["zapCount"])][: T["zapCount"]]

data = {
    "episodes": len(videos),
    "places": len(places),
    "zaps": [{"thumb": thumb(v["id"]), "score": v["score"], "name": v["review"].get("place_name") or ""} for v in zaps],
    "top3": [{
        "thumb": thumb(p["latest"]), "score": p["score"], "name": p["name"],
        "sub": p["address"] or p["area"] or "",
        "verdict": videos[p["latest"]]["review"].get("verdict_short") or "",
    } for p in top3],
}
(ROOT / "src" / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")

for f in ["durum.webp", "stamp-dum-durum.webp", "pin.webp", "slogan.webp"]:
    shutil.copy(SITE / "public/assets" / f, PUB / f)
shutil.copy(SITE / "public/logo.jpg", PUB / "logo.jpg")
shutil.copy(ROOT.parent / ".playwright-mcp/video-hitlist-full.png", PUB / "hitlist-full.png")
shutil.copy(ROOT.parent / "screenshots/04-kortet.png", PUB / "map.png")
shutil.copy(ROOT.parent / "screenshots/08-mobil-anmeldelse.png", PUB / "review-mobile.png")

# ---------- soundtrack ----------
SR = 44100
total = T["total"] / FPS
out = np.zeros(int(SR * total) + SR)
rng = np.random.default_rng(7)


def at(frame):
    return int(frame / FPS * SR)


def add(sig, frame, gain=1.0):
    i = at(frame)
    j = min(len(out), i + len(sig))
    out[i:j] += sig[: j - i] * gain


def env(n, attack=0.002, decay=0.15):
    t = np.arange(n) / SR
    return np.minimum(1, t / attack) * np.exp(-t / decay)


def kick():
    n = int(SR * 0.35); t = np.arange(n) / SR
    f = 50 + 110 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.12)


def hat():
    n = int(SR * 0.05)
    s = rng.standard_normal(n); s = np.diff(s, prepend=0)
    return s * env(n, 0.0005, 0.012) * 0.35


def snare():
    n = int(SR * 0.22); t = np.arange(n) / SR
    return (rng.standard_normal(n) * 0.6 + np.sin(2 * np.pi * 190 * t) * 0.5) * env(n, 0.001, 0.07)


def bass(freq, dur):
    n = int(SR * dur); t = np.arange(n) / SR
    s = np.sign(np.sin(2 * np.pi * freq * t)) * 0.5 + np.sin(2 * np.pi * freq * t) * 0.5
    return s * env(n, 0.004, dur * 0.6) * 0.35


def static(dur):
    n = int(SR * dur)
    return rng.standard_normal(n) * np.hanning(n) ** 0.3 * 0.35


def whoosh(dur=0.45, up=True):
    n = int(SR * dur)
    s = rng.standard_normal(n)
    # crude sweep: moving average window shrinking/growing
    k = np.linspace(40, 3, n) if up else np.linspace(3, 40, n)
    y = np.array([s[max(0, i - int(k[i])):i + 1].mean() for i in range(0, n)])
    return y * np.hanning(n) * 1.4


def boom():
    n = int(SR * 0.9); t = np.arange(n) / SR
    f = 40 + 90 * np.exp(-t * 10)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) + rng.standard_normal(n) * 0.15 * np.exp(-t * 20)) * env(n, 0.001, 0.35)


def chime():
    n = int(SR * 1.2); t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * t) for f in (784, 988, 1175)) / 3 * env(n, 0.005, 0.5) * 0.5


# Hook: static, then three slams on the words.
add(static(8 / FPS), 0, 1.0)
for f in T["hookWords"]:
    add(boom(), f, 0.8); add(snare(), f, 0.5)

# Groove from the zap section to the end card (120 bpm = beat every 15 frames).
notes = [55, 55, 65.4, 49]
for i, f in enumerate(range(T["zapStart"], T["endStart"], 15)):
    add(kick(), f, 0.9)
    add(hat(), f + 7.5, 1.0)
    if i % 2 == 1:
        add(snare(), f, 0.55)
    add(bass(notes[(i // 4) % 4], 0.45), f, 1.0)

# Channel-change static on every zap.
for k in range(T["zapCount"]):
    add(static(3 / FPS), T["zapStart"] + k * T["zapEvery"], 0.8)

for f in (T["phoneStart"], T["mapStart"], T["topStart"]):
    add(whoosh(), f - 8, 0.9)
for k, f in enumerate(T["topHits"]):
    add(boom(), f, 0.7 + 0.2 * k)
add(boom(), T["stampAt"], 1.2); add(snare(), T["stampAt"], 0.8)
add(chime(), T["endStart"], 1.0)

out = out[: at(T["total"])]
out = np.tanh(out * 1.2) * 0.85                     # glue + limit
stereo = (np.column_stack([out, out]) * 32767).astype(np.int16)
with wave.open(str(PUB / "soundtrack.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(stereo.tobytes())
print("zaps:", len(data["zaps"]), "top3:", [p["name"] for p in data["top3"]], "audio s:", round(len(out) / SR, 1))
