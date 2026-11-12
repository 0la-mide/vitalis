import json
from functools import lru_cache

from app.core.config import DATA_DIR


@lru_cache
def symptoms() -> dict:
    return json.loads((DATA_DIR / "symptoms.json").read_text())


@lru_cache
def red_flags() -> dict:
    return json.loads((DATA_DIR / "red_flags.json").read_text())


@lru_cache
def care_types() -> dict:
    return json.loads((DATA_DIR / "care_types.json").read_text())


@lru_cache
def symptom_index() -> dict[str, dict]:
    return {s["code"]: s for s in symptoms()["symptoms"]}


@lru_cache
def region_codes() -> set[str]:
    return {r["code"] for r in symptoms()["regions"]}
