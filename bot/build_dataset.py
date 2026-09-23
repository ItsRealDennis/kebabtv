"""Step 6: merge everything into the JSON files the website reads."""
import json
import re
import shutil
import unicodedata
from collections import Counter

from config import RAW, SITE_DATA, SITE_THUMBS, vdir


def slugify(s: str) -> str:
    s = s.lower().replace("æ", "ae").replace("ø", "oe").replace("å", "aa")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "sted"


def score10(review: dict):
    r = review.get("rating") or {}
    if r.get("value") is None:
        return None
    scale = r.get("scale") or 10
    return round(r["value"] / scale * 10, 1)


def _thumb(video_id: str):
    d = vdir(video_id)
    for ext in ("jpg", "webp", "png"):
        src = d / f"video.{ext}"
        if src.exists():
            shutil.copy(src, SITE_THUMBS / f"{video_id}.{ext}")
            return f"/thumbs/{video_id}.{ext}"
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


def build(entries: list[dict], wishlist: list[dict]):
    videos = []
    for e in entries:
        info, review, ca, geo = e["info"], e["review"], e.get("comments_analysis"), e.get("geo")
        videos.append({
            "id": info["id"],
            "title": info["title"],
            "date": info.get("upload_date"),
            "duration": info.get("duration"),
            "views": info.get("view_count"),
            "likes": info.get("like_count"),
            "comments": info.get("comment_count"),
            "thumb": _thumb(info["id"]),
            "chapters": info.get("chapters"),
            "review": review,
            "score": score10(review),
            "viewers": ca,
            "geo": geo,
        })
    videos.sort(key=lambda v: v["date"] or "", reverse=True)

    # One place can have several videos (revisits). Group by name + area.
    places: dict[str, dict] = {}
    for v in videos:
        r = v["review"]
        if not r.get("is_review") or not r.get("place_name"):
            continue
        key = slugify(f"{r['place_name']} {r.get('area') or ''}")
        p = places.setdefault(key, {
            "slug": key, "name": r["place_name"], "address": r.get("address"),
            "area": r.get("area"), "city": r.get("city"), "geo": v["geo"], "videos": [],
        })
        p["videos"].append(v["id"])
        p["address"] = p["address"] or r.get("address")
        p["geo"] = p["geo"] or v["geo"]
    for p in places.values():
        vs = [v for v in videos if v["id"] in p["videos"]]
        scores = [v["score"] for v in vs if v["score"] is not None]
        p["score"] = round(sum(scores) / len(scores), 1) if scores else None
        p["latest"] = vs[0]["id"]
        p["prices"] = [v["review"]["price_dkk"] for v in vs if v["review"].get("price_dkk")]
        for v in vs:
            v["place"] = p["slug"]

    scored = [v for v in videos if v["score"] is not None]
    people = Counter(n for v in videos for n in v["review"].get("people") or [])
    stats = {
        "videos": len(videos),
        "reviews": sum(1 for v in videos if v["review"].get("is_review")),
        "places": len(places),
        "total_views": sum(v["views"] or 0 for v in videos),
        "total_comments": sum(v["comments"] or 0 for v in videos),
        "avg_score": round(sum(v["score"] for v in scored) / len(scored), 2) if scored else None,
        "areas": Counter(p["area"] or "Ukendt" for p in places.values()).most_common(),
        "people": people.most_common(20),
        "with_transcript": sum(1 for v in videos if v["review"].get("has_transcript")),
    }

    def dump(name, obj):
        (SITE_DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), "utf-8")

    dump("videos.json", videos)
    dump("places.json", sorted(places.values(), key=lambda p: -(p["score"] or -1)))
    dump("stats.json", stats)
    dump("wishlist.json", wishlist)
    return stats
