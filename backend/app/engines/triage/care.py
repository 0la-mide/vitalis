"""Care-type selection and plain-language action level."""

from app.engines.triage.data import care_types
from app.engines.triage.red_flags import RedFlagResult
from app.engines.triage.state import TriageState
from app.models.enums import ActionLevel


def care_type_for(
    st: TriageState, rf: RedFlagResult, predictions: list[dict] | None
) -> tuple[str | None, str]:
    """Returns (care_type, source). Order: red flag > model > context > region default."""
    cfg = care_types()
    if rf.primary:
        return rf.primary.care_type, "red_flag"
    overrides = cfg["context_overrides"]
    if st.pregnant:
        for region in reversed(st.regions):
            if region in overrides["pregnant_regions"]:
                return overrides["pregnant_regions"][region], "context"
    if predictions:
        ct = cfg["conditions"].get(predictions[0]["condition_code"])
        if ct:
            if st.is_child and ct in {"general_medical", "infectious_disease", "respiratory"}:
                return overrides["child_care_type"], "model+context"
            return ct, "model"
    if st.is_child and (st.symptoms or st.regions):
        return overrides["child_care_type"], "context"
    if st.regions:
        return cfg["region_defaults"].get(st.regions[-1], "general_medical"), "region_default"
    if st.symptoms:
        return "general_medical", "region_default"
    return None, "none"


def _overall_severity(st: TriageState) -> int:
    sevs = [s.severity for s in st.symptoms if s.severity] + ([st.severity] if st.severity else [])
    return max(sevs, default=0)


def action_level_for(st: TriageState, rf: RedFlagResult, care_type: str | None) -> str | None:
    if rf.fired:
        return ActionLevel.go_now
    if not st.symptoms:
        return None
    sev = _overall_severity(st)
    for rule in care_types()["action_rules"]["rules"]:
        cond = rule["if"]
        if "severity_gte" in cond and sev < cond["severity_gte"]:
            continue
        if "care_type_in" in cond and care_type not in cond["care_type_in"]:
            continue
        if "onset_in" in cond and st.onset not in cond["onset_in"]:
            continue
        return rule["action"]
    return ActionLevel.self_care
