"""Step 2: turn subtitle files into one clean transcript.json per video: [{"t": seconds, "text": ...}]."""
import json
import re

from config import vdir


def _from_json3(path) -> list[dict]:
    data = json.loads(path.read_text("utf-8"))
    out = []
    for ev in data.get("events", []):
        text = "".join(s.get("utf8", "") for s in ev.get("segs") or []).strip()
        if text and text != "\n":
            out.append({"t": round(ev.get("tStartMs", 0) / 1000, 1), "text": text.replace("\n", " ")})
    return out


def _from_vtt(path) -> list[dict]:
    out, t = [], 0.0
    for line in path.read_text("utf-8").splitlines():
        m = re.match(r"(\d+):(\d+):(\d+)\.(\d+) -->", line)
        if m:
            h, mi, s, _ = map(int, m.groups())
            t = h * 3600 + mi * 60 + s
        elif line.strip() and "-->" not in line and not line.startswith(("WEBVTT", "Kind:", "Language:")):
            text = re.sub(r"<[^>]+>", "", line).strip()
            if text and (not out or out[-1]["text"] != text):
                out.append({"t": float(t), "text": text})
    return out


def _from_api(video_id: str) -> list[dict] | None:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        fetched = YouTubeTranscriptApi().fetch(video_id, languages=["da", "en"])
        return [{"t": round(s.start, 1), "text": s.text.replace("\n", " ")} for s in fetched.snippets]
    except Exception:
        return None


def build(video_id: str, force: bool = False) -> str:
    d = vdir(video_id)
    out_path = d / "transcript.json"
    if out_path.exists() and not force:
        return json.loads(out_path.read_text("utf-8"))["source"]
    segs, source = None, None
    # Prefer manual Danish, then auto Danish, then English.
    for pattern in ("video.da.json3", "video.da-orig.json3", "video.da.vtt", "video.da-orig.vtt", "video.en.json3", "video.en.vtt"):
        p = d / pattern
        if p.exists():
            segs = _from_json3(p) if p.suffix == ".json3" else _from_vtt(p)
            source = pattern
            if segs:
                break
    if not segs:
        segs = _from_api(video_id)
        source = "transcript-api" if segs else None
    out_path.write_text(json.dumps({"source": source, "segments": segs or []}, ensure_ascii=False), "utf-8")
    return source or "none"


def as_text(video_id: str) -> str:
    data = json.loads((vdir(video_id) / "transcript.json").read_text("utf-8"))
    return "\n".join(f"[{int(s['t'])}s] {s['text']}" for s in data["segments"])
