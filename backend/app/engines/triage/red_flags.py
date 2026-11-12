"""Deterministic red-flag rules. No network, no model: must never wait on anything."""

from dataclasses import dataclass

from app.engines.triage.data import red_flags
from app.engines.triage.state import TriageState


@dataclass(frozen=True)
class RedFlagHit:
    rule_id: str
    care_type: str
    message: str


@dataclass(frozen=True)
class RedFlagResult:
    fired: bool
    hits: list[RedFlagHit]
    rules_version: str

    @property
    def primary(self) -> RedFlagHit | None:
        return self.hits[0] if self.hits else None


def _atom(atom: dict, st: TriageState) -> bool:
    if "pregnant" in atom:
        return st.pregnant == atom["pregnant"]
    if "age_group_in" in atom:
        return st.age_group in atom["age_group_in"]
    if "symptom" in atom:
        return atom["symptom"] in st.codes()
    if "symptom_any" in atom:
        return bool(st.codes() & set(atom["symptom_any"]))
    if "severity_gte" in atom:
        for code in atom.get("symptoms", []):
            sev = st.severity_of(code)
            if sev is not None and sev >= atom["severity_gte"]:
                return True
        return False
    if "vital" in atom:
        v = st.vitals.get(atom["vital"])
        if v is None:
            return False
        if "lt" in atom and not v < atom["lt"]:
            return False
        if "gt" in atom and not v > atom["gt"]:
            return False
        return True
    raise ValueError(f"Unknown red-flag atom: {atom}")


def _rule_matches(rule: dict, st: TriageState) -> bool:
    if "all" in rule and not all(_atom(a, st) for a in rule["all"]):
        return False
    if "any" in rule and not any(_atom(a, st) for a in rule["any"]):
        return False
    return "all" in rule or "any" in rule


def _care_type(rule: dict, st: TriageState) -> str:
    if st.pregnant and "care_type_if_pregnant" in rule:
        return rule["care_type_if_pregnant"]
    if st.is_child and "care_type_if_child" in rule:
        return rule["care_type_if_child"]
    return rule["care_type"]


def evaluate(st: TriageState) -> RedFlagResult:
    cfg = red_flags()
    hits = [
        RedFlagHit(rule_id=r["id"], care_type=_care_type(r, st), message=r["message"])
        for r in cfg["rules"]
        if _rule_matches(r, st)
    ]
    return RedFlagResult(fired=bool(hits), hits=hits, rules_version=cfg["version"])
