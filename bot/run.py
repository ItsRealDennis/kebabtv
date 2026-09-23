"""Run the whole pipeline. Safe to re-run: finished steps are skipped per video.

  python bot/run.py                 # everything
  python bot/run.py --limit 3       # test on the 3 newest videos
  python bot/run.py --no-llm        # only download + transcripts (no Moodly calls)
  python bot/run.py --force analyze # redo a step (fetch|transcripts|analyze|comments)
"""
import argparse
import json
import re
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding="utf-8")

import analyze
import build_dataset
import comments
import fetch
import geocode
import llm
import transcripts
from config import MODEL, vdir


def stub_review(info: dict, src: str) -> dict:
    """Placeholder until the AI step runs: guess place/area from the title."""
    parts = [p.strip() for p in re.split(r" - | – ", info["title"]) if p.strip()]
    parts = [p for p in parts if not re.search(r"kebab ?tv|anmeldelse", p, re.I)] or parts
    return {"is_review": True, "place_name": parts[0].title() if parts[0].isupper() else parts[0],
            "area": parts[1] if len(parts) > 1 else None, "address": None, "city": None,
            "rating": {}, "quotes": [], "pros": [], "cons": [], "people": [], "stub": True,
            "has_transcript": src not in (None, "none")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--force", action="append", default=[])
    ap.add_argument("--only", help="comma-separated video ids")
    ap.add_argument("--workers", type=int, default=6, help="parallel AI calls")
    a = ap.parse_args()

    print("1/6 Listing channel ...")
    vids = fetch.list_videos()
    if a.only:
        vids = [v for v in vids if v["id"] in a.only.split(",")]
    if a.limit:
        vids = vids[: a.limit]
    print(f"    {len(vids)} videos")

    # Phase A (sequential, YouTube is touchy): download + transcripts.
    ready, failed = [], []
    for i, v in enumerate(vids, 1):
        vid = v["id"]
        tag = f"[{i}/{len(vids)}] {vid}"
        try:
            if fetch.fetch_one(vid, force="fetch" in a.force):
                print(f"{tag} fetched: {v['title']}")
            src = transcripts.build(vid, force="transcripts" in a.force)
            info = json.loads((vdir(vid) / "info.json").read_text("utf-8"))
            ready.append((vid, info, src))
        except Exception as e:
            failed.append(vid)
            print(f"{tag} FAILED: {e}")

    if a.no_llm:
        entries = [{"info": info, "review": stub_review(info, src), "comments_analysis": None, "geo": None}
                   for vid, info, src in ready]
    else:
        # Phase B (parallel): Claude reads transcripts + comments.
        def work(item):
            vid, info, src = item
            review = analyze.run(vid, force="analyze" in a.force)
            ca = comments.run(vid, review, force="comments" in a.force)
            return vid, info, src, review, ca

        results, done = {}, 0
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            futs = {pool.submit(work, item): item[0] for item in ready}
            for fut in as_completed(futs):
                done += 1
                vid = futs[fut]
                try:
                    _, info, src, review, ca = fut.result()
                    results[vid] = (info, review, ca)
                    r = review.get("rating") or {}
                    print(f"[{done}/{len(ready)}] {vid} {review.get('place_name')} -> {r.get('value')}/{r.get('scale')}  (transcript: {src})")
                except Exception as e:
                    failed.append(vid)
                    print(f"[{done}/{len(ready)}] {vid} FAILED: {e}")
                    traceback.print_exc(limit=2)

        # Phase C (sequential, 1 req/s): addresses -> map coordinates.
        print("4/6 Geocoding ...")
        entries = []
        for vid, _, _ in ready:
            if vid not in results:
                continue
            info, review, ca = results[vid]
            geo = geocode.locate(review) if review.get("is_review") else None
            entries.append({"info": info, "review": review, "comments_analysis": ca, "geo": geo})

    if a.no_llm:
        stats = build_dataset.build(entries, [])
        print(f"Wrote placeholder site data for {stats['videos']} videos (no AI yet).")
        return
    print("5/6 Wishlist ...")
    reqs = [p for e in entries for p in ((e["comments_analysis"] or {}).get("requested_places") or [])]
    reviewed = [e["review"]["place_name"] for e in entries if e["review"].get("place_name")]
    wl = comments.wishlist(reqs, reviewed, force="comments" in a.force)
    print("6/6 Writing site data ...")
    stats = build_dataset.build(entries, wl)
    print(json.dumps({k: stats[k] for k in ("videos", "reviews", "places", "avg_score", "with_transcript")}, ensure_ascii=False))
    u = llm.usage_total
    print(f"Tokens this run ({MODEL}): in {u['input']:,}  out {u['output']:,}  cache-read {u['cache_read']:,}")
    if failed:
        print(f"Failed: {', '.join(failed)}  (re-run to retry)")


if __name__ == "__main__":
    main()
