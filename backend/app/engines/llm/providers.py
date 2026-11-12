"""Plain-language narrative for the doctor AI: Gemini → Groq → canned.

The clinical reasoning is the deterministic engine (red flags, conditions, models, medication safety); an LLM may only
rephrase it into a short narrative. External calls happen only when ALLOW_EXTERNAL_LLM=true (synthetic data only).
Output is forced to JSON, validated, and rejected if it contains any dose — the AI never prescribes.
"""

import json
import logging
import re
from dataclasses import dataclass, field

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.core.config import get_settings

log = logging.getLogger("vitalis.llm")

DOSE = re.compile(r"\b\d+(\.\d+)?\s?(mg|mcg|µg|g|ml|mL|units?|iu|IU|tabs?|tablets?)\b", re.IGNORECASE)
PROMPT = (
    "You are writing a short summary for a doctor from a decision-support engine's JSON output. "
    "Use ONLY facts in the JSON. Do not add diagnoses, drugs, numbers or doses that are not in it, "
    "and never include any dose or prescription. Reply with JSON: "
    '{"summary": string (max 90 words), "evidence_for": [string], "evidence_against": [string], '
    '"missing_information": [string], "cautions": [string]}.\n\nENGINE OUTPUT:\n'
)


class NarrativeOut(BaseModel):
    summary: str = Field(max_length=900)
    evidence_for: list[str] = Field(default_factory=list, max_length=8)
    evidence_against: list[str] = Field(default_factory=list, max_length=8)
    missing_information: list[str] = Field(default_factory=list, max_length=8)
    cautions: list[str] = Field(default_factory=list, max_length=8)


@dataclass
class Narrative:
    provider: str  # gemini | groq | canned
    summary: str
    evidence_for: list[str] = field(default_factory=list)
    evidence_against: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    cautions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def canned(output: dict) -> Narrative:
    top = output["conditions"][0] if output["conditions"] else None
    return Narrative(
        provider="canned",
        summary=output["summary"],
        evidence_for=[e["text"] for e in (top["evidence"] if top else [])][:5],
        evidence_against=[e["text"] for e in (top["against"] if top else [])][:3],
        missing_information=output["missing_data"][:5],
        cautions=[f["title"] for f in output["red_flags"]]
        + [f"Avoid {m['drug']}: conflicts with the record" for m in output["medication_options"] if m["safety"] == "avoid"],
    )


def _compact(output: dict) -> str:
    keep = {k: output[k] for k in ("summary", "red_flags", "missing_data")}
    keep["conditions"] = [{k: c[k] for k in ("condition", "likelihood_label", "evidence", "against")}
                          for c in output["conditions"][:3]]
    keep["medication_options"] = [{k: m[k] for k in ("drug", "safety", "alerts")} for m in output["medication_options"]]
    return json.dumps(keep, ensure_ascii=False)[:12000]


def _validate(provider: str, text: str) -> Narrative:
    data = NarrativeOut.model_validate_json(text)
    blob = json.dumps(data.model_dump())
    if DOSE.search(blob):
        raise ValueError("narrative contained a dose")
    return Narrative(provider=provider, **data.model_dump())


async def _gemini(client: httpx.AsyncClient, key: str, output: dict) -> Narrative:
    r = await client.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        params={"key": key},
        json={"contents": [{"parts": [{"text": PROMPT + _compact(output)}]}],
              "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}},
    )
    r.raise_for_status()
    return _validate("gemini", r.json()["candidates"][0]["content"]["parts"][0]["text"])


async def _groq(client: httpx.AsyncClient, key: str, output: dict) -> Narrative:
    r = await client.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": "llama-3.3-70b-versatile", "temperature": 0.2, "response_format": {"type": "json_object"},
              "messages": [{"role": "user", "content": PROMPT + _compact(output)}]},
    )
    r.raise_for_status()
    return _validate("groq", r.json()["choices"][0]["message"]["content"])


async def narrate(output: dict) -> Narrative:
    s = get_settings()
    if s.allow_external_llm:
        async with httpx.AsyncClient(timeout=8.0) as client:
            for name, key, fn in (("gemini", s.gemini_api_key, _gemini), ("groq", s.groq_api_key, _groq)):
                if not key:
                    continue
                try:
                    return await fn(client, key, output)
                except (httpx.HTTPError, KeyError, IndexError, ValidationError, ValueError) as exc:
                    log.warning("llm provider failed", extra={"fields": {"provider": name, "error": type(exc).__name__}})
    return canned(output)
