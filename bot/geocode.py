"""Step 5: address -> lat/lng via OpenStreetMap Nominatim (free, max 1 request/second, cached)."""
import json
import time

import requests

from config import CACHE

_CACHE_FILE = CACHE / "geocode.json"
_cache = json.loads(_CACHE_FILE.read_text("utf-8")) if _CACHE_FILE.exists() else {}
_last = 0.0


def _query(q: str):
    global _last
    if q in _cache:
        return _cache[q]
    wait = 1.1 - (time.time() - _last)
    if wait > 0:
        time.sleep(wait)
    _last = time.time()
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": q, "format": "json", "limit": 1, "countrycodes": "dk"},
        headers={"User-Agent": "KebabTV-fan-map/1.0"},
        timeout=20,
    )
    hit = r.json()[0] if r.ok and r.json() else None
    _cache[q] = {"lat": float(hit["lat"]), "lng": float(hit["lon"])} if hit else None
    _CACHE_FILE.write_text(json.dumps(_cache, ensure_ascii=False, indent=1), "utf-8")
    return _cache[q]


def locate(review: dict):
    city = review.get("city") or "København"
    tries = []
    if review.get("address"):
        tries.append(f"{review['address']}, {city}")
    if review.get("place_name"):
        tries.append(f"{review['place_name']}, {review.get('area') or city}")
    for q in tries:
        hit = _query(q)
        if hit:
            return {**hit, "query": q, "exact": q == tries[0] and bool(review.get("address"))}
    return None
