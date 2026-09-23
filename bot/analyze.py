"""Step 3: Claude reads each transcript and extracts the review."""
import base64
import json
from typing import Literal, Optional

from pydantic import BaseModel, Field

import transcripts
from config import vdir
from llm import ask


class Rating(BaseModel):
    value: Optional[float] = Field(None, description="Karakteren som tal, fx 7.5. null hvis ingen karakter gives.")
    scale: Optional[float] = Field(None, description="Skalaen, fx 10. null hvis ukendt.")
    raw_quote: Optional[str] = Field(None, description="Den præcise sætning hvor karakteren siges.")
    t: Optional[int] = Field(None, description="Sekund i videoen hvor karakteren gives.")


class SubScore(BaseModel):
    label: str = Field(description="Hvad/hvem der bedømmes, fx 'kød', 'brød', 'sovs', eller en værts navn.")
    value: float
    scale: float


class Quote(BaseModel):
    text: str = Field(description="Kort, ordret citat (max 20 ord) på dansk.")
    t: int = Field(description="Sekund i videoen.")
    speaker: Optional[str] = None


class Review(BaseModel):
    is_review: bool = Field(description="False hvis videoen ikke er en anmeldelse af et spisested (fx teaser).")
    place_name: Optional[str] = None
    address: Optional[str] = Field(None, description="Gade + nr. hvis nævnt i video, titel eller beskrivelse.")
    area: Optional[str] = Field(None, description="Bydel, fx Nørrebro, Vesterbro, Frederiksberg, Amager.")
    city: Optional[str] = Field(None, description="By, fx København, Aarhus, Glostrup.")
    dish: Optional[str] = Field(None, description="Hovedretten der anmeldes, fx 'durum shawarma'.")
    price_dkk: Optional[float] = None
    rating: Rating
    sub_scores: list[SubScore] = []
    verdict_short: Optional[str] = Field(None, description="Dom i max 12 ord, i deres egen tone.")
    summary: Optional[str] = Field(None, description="2-3 sætninger om hvad der skete og hvad de mente.")
    pros: list[str] = []
    cons: list[str] = []
    quotes: list[Quote] = Field(default=[], description="Max 3 sjove eller rammende citater.")
    people: list[str] = Field(default=[], description="Navne på værter/gæster der optræder.")
    mood: Literal["begejstret", "tilfreds", "neutral", "skuffet", "vred", "ukendt"] = "ukendt"
    confidence: float = Field(description="0-1: hvor sikker du er på udtrækket.")


SYSTEM = """Du analyserer videoer fra KebabTV, en dansk YouTube-kanal hvor værterne anmelder kebab-, durum- og shawarmasteder (mest i København).
Du får titel, beskrivelse og en automatisk transskription med tidsstempler i sekunder. Autotekster er ofte fejlstavede: ret åbenlyse fejl i stednavne, men opfind aldrig noget.
Du får også videoens thumbnail. Den har næsten altid kanalens navneskilt med stedets officielle navn og adresse (fx "ROYAL SHAWARMA BAR / RYESGADE 28 - AARHUS C").
Holdet:
- René står foran kameraet og anmelder i ALLE afsnit, også når hans navn ikke siges. Han kalder sig selv "Dr. Dürüm".
- Jeppe filmer og ses aldrig i billedet. Han er fra Aarhus og får "som altid den ene halvdel" af maden. Når René siger "Jeppe", taler han til kameraet.
- Andre navne er gæster eller personale.
- Autoteksterne skriver "dürüm" som "dudum". "Dum dürüm" er kanalens eget godkendelsesstempel: over 8 = "dum dürüm, approved af KebabTV".
Tone:
- Skriv personligt med navne: "René synes brødet er tørt", ikke "anmelderen finder brødet tørt". Brug aldrig "anmelderen", "værten" eller "værterne".
- Hold det kort og i kanalens løse, hjemmelavede tone.
Regler:
- people = alle der ses i billedet: René plus gæster og personale (med navn hvis det siges, ellers fx "Ejeren"). Jeppe skal ALDRIG i people.
- verdict_short: max 12 ord.
- Navn og adresse fra thumbnailens navneskilt vinder over transskriptionen. Skriv navnet med normal stavning (ikke kun versaler).
- Brug kun hvad der faktisk siges eller står. Sæt null når du er i tvivl.
- Karakteren siges ofte højt, fx "jeg giver den et 7-tal" eller "8 ud af 10". Giver flere værter karakter, så brug gennemsnittet som rating og læg hver værts karakter i sub_scores med værtens navn som label.
- Citater skal være ordrette fra transskriptionen, korte, og med korrekt sekund.
- Skriv på dansk."""


def _thumb_block(d) -> list[dict]:
    for ext, mime in (("webp", "image/webp"), ("jpg", "image/jpeg"), ("png", "image/png")):
        p = d / f"video.{ext}"
        if p.exists():
            data = base64.standard_b64encode(p.read_bytes()).decode()
            return [{"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}}]
    return []


def run(video_id: str, force: bool = False) -> dict:
    d = vdir(video_id)
    out = d / "review.json"
    if out.exists() and not force:
        return json.loads(out.read_text("utf-8"))
    info = json.loads((d / "info.json").read_text("utf-8"))
    text = transcripts.as_text(video_id)
    user = (
        f"TITEL: {info['title']}\nUPLOAD: {info.get('upload_date')}\nLÆNGDE: {info.get('duration')}s\n"
        f"BESKRIVELSE:\n{info.get('description') or '(ingen)'}\n\n"
        "TRANSSKRIPTION:\n"
        + (text or "(ingen transskription — brug kun titel og beskrivelse, og sæt lav confidence)")
    )
    review = ask(SYSTEM, user, Review, images=_thumb_block(d)).model_dump()
    review["has_transcript"] = bool(text)
    out.write_text(json.dumps(review, ensure_ascii=False, indent=1), "utf-8")
    return review
