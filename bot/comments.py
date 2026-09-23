"""Step 4: what viewers think, per video + channel-wide wishlist."""
import json
from typing import Optional

from pydantic import BaseModel, Field

from config import CACHE, COMMENTS_FOR_ANALYSIS, vdir
from llm import ask


class Theme(BaseModel):
    label: str
    count_estimate: int


class CommentAnalysis(BaseModel):
    positive_pct: int = Field(description="0-100")
    negative_pct: int
    neutral_pct: int
    agrees_with_rating: Optional[bool] = Field(None, description="Er seerne overordnet enige i værternes dom? null hvis uklart.")
    disagreement_note: Optional[str] = Field(None, description="Kort: hvad seerne er uenige om, hvis noget.")
    themes: list[Theme] = Field(default=[], description="Max 5 temaer seerne taler om.")
    requested_places: list[str] = Field(default=[], description="Spisesteder seerne foreslår at de anmelder næste gang. Kun navne.")
    best_comment: Optional[str] = Field(None, description="Den sjoveste/bedste kommentar, ordret, max 30 ord.")
    best_comment_author: Optional[str] = None


class Request(BaseModel):
    name: str
    area: Optional[str] = None
    mentions: int
    already_reviewed: bool


class Wishlist(BaseModel):
    places: list[Request]


SYSTEM = """Du analyserer YouTube-kommentarer til KebabTV (dansk kanal der anmelder kebab, durum og shawarma).
René står foran kameraet (han kalder sig "Dr. Dürüm"). Jeppe filmer og ses aldrig.
Skriv personligt med navne: "René gav 7, men seerne synes..." Brug aldrig "anmelderen", "værten" eller "værterne".
Vær nøgtern. Tæl ikke spam eller kanalens egne svar med. Citér ordret. Svar på dansk."""


def run(video_id: str, review: dict, force: bool = False) -> dict | None:
    d = vdir(video_id)
    out = d / "comments_analysis.json"
    if out.exists() and not force:
        return json.loads(out.read_text("utf-8"))
    comments = json.loads((d / "comments.json").read_text("utf-8"))
    top = [c for c in comments if c.get("parent") in (None, "root") and not c.get("author_is_uploader")]
    top = sorted(top, key=lambda c: c.get("like_count") or 0, reverse=True)[:COMMENTS_FOR_ANALYSIS]
    if not top:
        out.write_text("null", "utf-8")
        return None
    lines = "\n".join(f"- ({c.get('like_count') or 0} likes) {c.get('author')}: {c['text'][:400]}" for c in top)
    rating = review.get("rating") or {}
    user = (
        f"Sted: {review.get('place_name')}. Renés karakter: {rating.get('value')}/{rating.get('scale')}. "
        f"Dom: {review.get('verdict_short')}\n\nKOMMENTARER:\n{lines}"
    )
    res = ask(SYSTEM, user, CommentAnalysis, max_tokens=8000).model_dump()
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
    return res


def wishlist(all_requests: list[str], reviewed: list[str], force: bool = False) -> list[dict]:
    out = CACHE / "wishlist.json"
    if out.exists() and not force:
        return json.loads(out.read_text("utf-8"))
    if not all_requests:
        return []
    user = (
        "Rå liste over steder seerne har foreslået (én linje per forslag, dubletter og stavefejl forekommer):\n"
        + "\n".join(all_requests)
        + "\n\nSteder der allerede ER anmeldt:\n" + "\n".join(sorted(set(reviewed)))
        + "\n\nSlå dubletter og stavevarianter sammen, tæl forekomster, markér om stedet allerede er anmeldt. Sortér efter mentions."
    )
    res = [p.model_dump() for p in ask(SYSTEM, user, Wishlist, max_tokens=8000).places]
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
    return res
