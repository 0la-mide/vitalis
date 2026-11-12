"""Pre-prescription safety check: allergies (incl. cross-reactivity), interactions, condition contraindications.

Ported from the team's NCS repo; the knowledge base is data/medication_safety.json (needs clinical review).
"""

import json
from dataclasses import dataclass, field
from functools import lru_cache

from app.core.config import DATA_DIR


@lru_cache
def kb() -> dict:
    return json.loads((DATA_DIR / "medication_safety.json").read_text())


@dataclass
class HistoryItem:
    text: str
    source: str | None = None  # "Ogun Teaching Hospital (Demo) · 12 Apr 2026"


@dataclass
class SafetyResult:
    verdict: str  # ok | caution | avoid
    alerts: list[dict] = field(default_factory=list)  # {kind, severity, text, source}

    def as_dict(self) -> dict:
        return {"verdict": self.verdict, "alerts": self.alerts, "kb_version": kb()["version"]}


def _norm(s: str) -> str:
    return s.lower().strip()


def check(drug: str, allergies: list[HistoryItem], medications: list[HistoryItem], conditions: list[HistoryItem],
          pregnant: bool = False) -> SafetyResult:
    d = _norm(drug)
    name = d.split(" ")[0]
    alerts: list[dict] = []
    cross = kb()["allergy_cross_reactivity"]
    for a in allergies:
        al = _norm(a.text)
        first = al.split(" ")[0].strip("(),")
        if name and (name in al or first in d):
            alerts.append({"kind": "allergy", "severity": "major", "source": a.source,
                           "text": f"Documented allergy: {a.text}."})
            continue
        for key, members in cross.items():
            if key in al and any(m in d for m in members):
                alerts.append({"kind": "allergy", "severity": "major", "source": a.source,
                               "text": f"Cross-reactivity: {drug.split(' ')[0].title()} shares sensitivity with the documented "
                                       f"allergy to {a.text}."})
                break
    for rule in kb()["interactions"]:
        a, b = rule["a"], rule["b"]
        for x, y in ((a, b), (b, a)):
            if x in d:
                other = next((m for m in medications if y in _norm(m.text)), None)
                if other:
                    alerts.append({"kind": "interaction", "severity": rule["severity"], "source": other.source,
                                   "text": f"Interaction with {other.text}: {rule['detail']}"})
    conds = [_norm(c.text) for c in conditions] + (["pregnant"] if pregnant else [])
    for rule in kb()["condition_contraindications"]:
        if any(any(k in c for k in rule["conditions"]) for c in conds) and any(x in d for x in rule["drugs"]):
            alerts.append({"kind": "condition", "severity": "major" if "pregnan" in rule["conditions"] else "moderate",
                           "source": None, "text": rule["warning"]})
    verdict = "ok"
    if any(x["severity"] == "major" for x in alerts):
        verdict = "avoid"
    elif alerts:
        verdict = "caution"
    return SafetyResult(verdict, alerts)
