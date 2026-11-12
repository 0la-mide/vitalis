"""Every red-flag rule fires on its trigger and stays quiet on a near-miss. Pure, no DB or network."""

import pytest

from app.engines.triage.red_flags import evaluate
from app.engines.triage.state import SymptomState, TriageState


def st(*codes, sev=None, **ctx):
    return TriageState(symptoms=[SymptomState(code=c, severity=sev) for c in codes], **ctx)


CASES = [
    ("RF_PREG_HEAVY_BLEEDING", st("BLEEDING_VAGINAL_HEAVY", pregnant=True, sex="female")),
    ("RF_PREG_BLEEDING_WITH_PAIN_OR_DIZZY", st("BLEEDING_VAGINAL_LIGHT", "DIZZY_FAINT", pregnant=True)),
    ("RF_PREG_BLEEDING_WITH_PAIN_OR_DIZZY", st("BLEEDING_VAGINAL_LIGHT", "ABDOMINAL_PAIN", pregnant=True)),
    ("RF_PREG_BLEEDING_SEVERE", st("BLEEDING_VAGINAL_LIGHT", sev=4, pregnant=True)),
    ("RF_BREATHING", st("BREATHING_DIFFICULTY")),
    ("RF_UNCONSCIOUS", st("UNCONSCIOUS")),
    ("RF_SEIZURE", st("SEIZURE")),
    ("RF_CHEST_PAIN_ADULT", st("CHEST_PAIN", age_group="adult")),
    ("RF_SEVERE_INJURY", st("SEVERE_INJURY")),
    ("RF_SEVERE_INJURY", st("WOUND", sev=5)),
    ("RF_CHILD_DANGER_SIGNS", st("NOT_DRINKING", age_group="under5")),
    ("RF_CHILD_DANGER_SIGNS", st("LETHARGIC", age_group="child")),
    ("RF_UNDER5_HIGH_FEVER", st("HIGH_FEVER", age_group="under5")),
    ("RF_VITAL_SPO2_LOW", TriageState(vitals={"spo2": 89})),
    ("RF_VITAL_SBP_LOW", TriageState(vitals={"systolic_bp": 85})),
    ("RF_VITAL_SBP_HIGH", TriageState(vitals={"systolic_bp": 185})),
    ("RF_VITAL_PULSE", TriageState(vitals={"pulse": 140})),
    ("RF_VITAL_PULSE", TriageState(vitals={"pulse": 35})),
    ("RF_VITAL_TEMP", TriageState(vitals={"temp_c": 40.5})),
]


@pytest.mark.parametrize("rule_id,state", CASES)
def test_rule_fires(rule_id, state):
    res = evaluate(state)
    assert res.fired
    assert rule_id in [h.rule_id for h in res.hits]
    assert res.rules_version.startswith("rf-")


NEAR_MISSES = [
    st("BLEEDING_VAGINAL_LIGHT", sev=2, pregnant=True),  # light, not severe, no pain
    st("BLEEDING_VAGINAL_HEAVY", pregnant=False, sex="female"),  # not pregnant
    st("CHEST_PAIN", age_group="child"),  # chest pain rule is adult-only
    st("HIGH_FEVER", age_group="adult"),
    st("WOUND", sev=3),
    st("HEADACHE", sev=5),
    TriageState(vitals={"spo2": 95, "systolic_bp": 120, "pulse": 90, "temp_c": 37.2}),
]


@pytest.mark.parametrize("state", NEAR_MISSES)
def test_near_miss_quiet(state):
    assert not evaluate(state).fired


def test_care_type_overrides():
    assert evaluate(st("SEIZURE", age_group="under5")).primary.care_type == "paediatrics"
    assert evaluate(st("SEIZURE", pregnant=True)).primary.care_type == "obstetrics"
    assert evaluate(st("BLEEDING_VAGINAL_HEAVY", pregnant=True)).primary.care_type == "obstetrics"
