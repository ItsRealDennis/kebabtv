"""Step 1: list every video on the channel and pull metadata, comments, subtitles, thumbnail."""
import json

import yt_dlp

from config import CHANNEL, MAX_COMMENTS, RAW, TABS, vdir


def list_videos() -> list[dict]:
    seen, out = set(), []
    opts = {"extract_flat": True, "quiet": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        for tab in TABS:
            try:
                info = ydl.extract_info(f"{CHANNEL}/{tab}", download=False)
            except yt_dlp.utils.DownloadError:
                continue
            for e in info.get("entries") or []:
                if e.get("id") and e["id"] not in seen:
                    seen.add(e["id"])
                    out.append({"id": e["id"], "title": e.get("title"), "tab": tab})
    (RAW / "_index.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
    return out


def fetch_one(video_id: str, force: bool = False) -> bool:
    d = vdir(video_id)
    if (d / "info.json").exists() and not force:
        return False
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "getcomments": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["da", "da-orig"],
        "sleep_interval_subtitles": 2,
        "ignoreerrors": "only_download",  # a failed subtitle/thumbnail must not kill metadata + comments
        "subtitlesformat": "json3/vtt/best",
        "writethumbnail": True,
        "outtmpl": str(d / "video.%(ext)s"),
        "extractor_args": {"youtube": {
            "max_comments": [str(MAX_COMMENTS), "all", "30", "5"],
            "comment_sort": ["top"],
        }},
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
        if not info:
            raise RuntimeError("yt-dlp returned nothing")
        info = ydl.sanitize_info(info)
    keep = {k: info.get(k) for k in (
        "id", "title", "description", "upload_date", "duration", "view_count",
        "like_count", "comment_count", "tags", "chapters", "thumbnail", "channel_follower_count",
    )}
    (d / "info.json").write_text(json.dumps(keep, ensure_ascii=False, indent=1), "utf-8")
    comments = [
        {k: c.get(k) for k in ("id", "parent", "text", "author", "like_count", "timestamp", "is_pinned", "author_is_uploader")}
        for c in info.get("comments") or []
    ]
    (d / "comments.json").write_text(json.dumps(comments, ensure_ascii=False, indent=1), "utf-8")
    return True
