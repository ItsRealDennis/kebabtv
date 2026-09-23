"""Thin wrapper: Claude via Moodly, returning a validated pydantic object."""
import json
import re

import anthropic
from pydantic import BaseModel, ValidationError

from config import LLM_API_KEY, LLM_BASE_URL, MODEL

_client = None
usage_total = {"input": 0, "output": 0, "cache_read": 0}


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not LLM_API_KEY:
            raise SystemExit("Missing key. Set MOODLY_API_KEY first.")
        _client = anthropic.Anthropic(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, max_retries=4, timeout=600)
    return _client


def _track(resp):
    u = resp.usage
    usage_total["input"] += u.input_tokens or 0
    usage_total["output"] += u.output_tokens or 0
    usage_total["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0


def _extract_json(text: str) -> str:
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if m:
        return m.group(1)
    return text[text.find("{"): text.rfind("}") + 1]


def ask(system: str, user: str, schema: type[BaseModel], max_tokens: int = 16000, images: list[dict] | None = None) -> BaseModel:
    """images: Anthropic image blocks placed before the text (e.g. the video thumbnail)."""
    system_blocks = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    # 1) Native structured output.
    try:
        resp = client().messages.parse(
            model=MODEL, max_tokens=max_tokens, system=system_blocks,
            messages=[{"role": "user", "content": [*(images or []), {"type": "text", "text": user}]}], output_format=schema,
        )
        _track(resp)
        if resp.stop_reason == "refusal":
            raise RuntimeError("model refused")
        if resp.parsed_output is not None:
            return resp.parsed_output
    except (anthropic.BadRequestError, anthropic.UnprocessableEntityError, anthropic.InternalServerError, ValidationError, TypeError):
        pass  # gateway may not support structured output; fall back to plain JSON.
    # 2) Plain JSON fallback, validated locally, one retry.
    hint = ("\n\nSvar KUN med gyldig JSON der matcher dette JSON Schema:\n"
            + json.dumps(schema.model_json_schema(), ensure_ascii=False))
    last_err = None
    for _ in range(2):
        resp = client().messages.create(
            model=MODEL, max_tokens=max_tokens, system=system_blocks,
            messages=[{"role": "user", "content": [*(images or []), {"type": "text", "text": user + hint}]}],
        )
        _track(resp)
        text = "".join(b.text for b in resp.content if b.type == "text")
        try:
            return schema.model_validate_json(_extract_json(text))
        except ValidationError as e:
            last_err = e
    raise RuntimeError(f"Could not get valid JSON: {last_err}")
