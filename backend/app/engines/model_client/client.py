"""Adapter for our disease model service. Swapping the model changes only this module.

Contract (stub-0.1): POST {model_url}/predict  {patient, symptoms[{code, region, severity, onset}], vitals}
-> {model_version, predictions[{condition_code, label, likelihood}]}
"""

import logging
import time
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.engines.triage.data import symptom_index
from app.engines.triage.state import TriageState

log = logging.getLogger("vitalis.model")

@dataclass
class ModelResult:
    ok: bool
    model_version: str
    predictions: list[dict]
    latency_ms: int
    request: dict
    error: str | None = None


def build_request(st: TriageState) -> dict:
    idx = symptom_index()
    seen: dict[str, dict] = {}
    for s in st.symptoms:
        meta = idx.get(s.code, {})
        model_code = meta.get("model_code", s.code)
        sev = meta.get("model_severity") or s.severity
        item = {"code": model_code, "region": s.region, "severity": sev, "onset": s.onset}
        prev = seen.get(model_code)
        if not prev or (sev or 0) > (prev.get("severity") or 0):
            seen[model_code] = item
    return {
        "patient": {"age_group": st.age_group, "sex": st.sex, "pregnant": st.pregnant},
        "symptoms": list(seen.values()),
        "vitals": st.vitals,
    }


_client: httpx.AsyncClient | None = None


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient()
    return _client


async def predict(st: TriageState) -> ModelResult:
    s = get_settings()
    req = build_request(st)
    start = time.perf_counter()
    try:
        resp = await _http().post(
            f"{s.model_url}/predict", json=req, timeout=s.model_timeout_ms / 1000
        )
        resp.raise_for_status()
        body = resp.json()
        preds = [
            {
                "condition_code": p["condition_code"],
                "label": p.get("label", p["condition_code"]),
                "likelihood": float(p["likelihood"]),
            }
            for p in body.get("predictions", [])
        ]
        return ModelResult(
            ok=True,
            model_version=str(body.get("model_version", "unknown")),
            predictions=preds,
            latency_ms=int((time.perf_counter() - start) * 1000),
            request=req,
        )
    except Exception as exc:  # noqa: BLE001 - never block the patient on the model
        ms = int((time.perf_counter() - start) * 1000)
        log.warning("model unavailable", extra={"fields": {"error": type(exc).__name__, "ms": ms}})
        return ModelResult(
            ok=False, model_version="unavailable", predictions=[], latency_ms=ms, request=req,
            error=type(exc).__name__,
        )
