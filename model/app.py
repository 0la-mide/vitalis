"""VITALIS disease-model STUB.

Implements the contract in docs/architecture.md (POST /predict). Returns plausible outputs
from a small hand-written lookup so the demo works before the real model is plugged in.
Not a clinical tool. Synthetic only.
"""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

MODEL_VERSION = "stub-0.1"

app = FastAPI(title="VITALIS model stub", version=MODEL_VERSION)


class PatientCtx(BaseModel):
    age_group: Literal["under5", "child", "teen", "adult", "elderly"] = "adult"
    sex: Literal["female", "male", "unknown"] = "unknown"
    pregnant: bool = False


class SymptomIn(BaseModel):
    code: str
    region: str | None = None
    severity: int | None = Field(default=None, ge=1, le=5)
    onset: str | None = None


class PredictIn(BaseModel):
    patient: PatientCtx
    symptoms: list[SymptomIn]
    vitals: dict[str, float] = {}


class Prediction(BaseModel):
    condition_code: str
    label: str
    likelihood: float


class PredictOut(BaseModel):
    model_version: str
    predictions: list[Prediction]


# (required symptom codes, optional condition, condition_code, label, base likelihood)
RULES: list[tuple[set[str], str | None, str, str, float]] = [
    ({"BLEEDING_VAGINAL"}, "pregnant", "ANTEPARTUM_HAEMORRHAGE", "Antepartum haemorrhage", 0.71),
    ({"ABDOMINAL_PAIN"}, "pregnant", "PRETERM_LABOUR", "Preterm labour", 0.42),
    ({"BLEEDING_VAGINAL"}, None, "ABNORMAL_UTERINE_BLEEDING", "Abnormal uterine bleeding", 0.48),
    ({"CHEST_PAIN"}, None, "ACUTE_CORONARY_SYNDROME", "Acute coronary syndrome", 0.44),
    ({"BREATHING_DIFFICULTY"}, None, "PNEUMONIA", "Pneumonia", 0.41),
    ({"BREATHING_DIFFICULTY"}, None, "ASTHMA_EXACERBATION", "Asthma exacerbation", 0.33),
    ({"COUGH", "FEVER"}, None, "PNEUMONIA", "Pneumonia", 0.52),
    ({"FEVER"}, None, "MALARIA", "Malaria", 0.55),
    ({"FEVER", "HEADACHE"}, None, "MALARIA", "Malaria", 0.63),
    ({"FEVER", "RASH"}, None, "MEASLES", "Measles", 0.31),
    ({"DIARRHOEA"}, None, "GASTROENTERITIS", "Gastroenteritis", 0.58),
    ({"DIARRHOEA", "VOMITING"}, None, "CHOLERA", "Cholera", 0.27),
    ({"SEIZURE"}, None, "EPILEPSY", "Seizure disorder", 0.45),
    ({"SEIZURE", "FEVER"}, "child", "FEBRILE_SEIZURE", "Febrile seizure", 0.52),
    ({"WOUND"}, None, "LACERATION", "Laceration", 0.6),
    ({"CANT_MOVE"}, None, "FRACTURE", "Fracture", 0.47),
    ({"BURN"}, None, "BURN_INJURY", "Burn injury", 0.66),
    ({"HEADACHE"}, None, "TENSION_HEADACHE", "Tension headache", 0.35),
    ({"ABDOMINAL_PAIN"}, None, "APPENDICITIS", "Appendicitis", 0.22),
    ({"ABDOMINAL_PAIN"}, None, "GASTRITIS", "Gastritis", 0.3),
    ({"UNCONSCIOUS"}, None, "ALTERED_CONSCIOUSNESS", "Altered consciousness", 0.5),
]


@app.get("/health")
def health():
    return {"status": "ok", "model_version": MODEL_VERSION}


@app.post("/predict", response_model=PredictOut)
def predict(body: PredictIn) -> PredictOut:
    codes = {s.code for s in body.symptoms}
    max_sev = max((s.severity or 3 for s in body.symptoms), default=3)
    is_child = body.patient.age_group in {"under5", "child"}
    best: dict[str, Prediction] = {}
    for needed, cond, code, label, base in RULES:
        if not needed <= codes:
            continue
        if cond == "pregnant" and not body.patient.pregnant:
            continue
        if cond == "child" and not is_child:
            continue
        lk = min(0.95, base + 0.03 * (max_sev - 3))
        if code not in best or best[code].likelihood < lk:
            best[code] = Prediction(condition_code=code, label=label, likelihood=round(lk, 2))
    preds = sorted(best.values(), key=lambda p: p.likelihood, reverse=True)[:5]
    return PredictOut(model_version=MODEL_VERSION, predictions=preds)
