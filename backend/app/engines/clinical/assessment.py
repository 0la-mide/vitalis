"""VITALIS AI: clinician-facing decision support for one encounter.

Ported from the team's NCS repo (app/services/clinical_ai.py) onto this data model. It combines today's complaint
and vitals (including the referring chemist's readings), earlier visits it is allowed to see, lab values, the
patient's allergies / conditions / medicines / family history (each with where it was recorded), and the team's two
trained risk models. It ranks possible conditions with the evidence for each, raises red flags, shows trends, and
screens common treatments against the record.

It never diagnoses and never gives doses or prescriptions: treatment options are drug names with a reason and a
safety verdict; the doctor writes any prescription and dose.
"""

import math
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from app.engines.clinical import medication_safety as ms
from app.engines.ncs_models import adapter as models

ENGINE_VERSION = "VITALIS-AI-2026.3 (clinical rules from NCS + NCS-SVC-DiabetesV1 + NCS-RandomForest-HeartV1)"
DISCLAIMER = (
    "Clinical decision support only. Likelihoods are qualitative estimates from documented data and must be "
    "confirmed by examination and investigation. VITALIS AI does not diagnose or prescribe: the attending clinician "
    "makes and owns every decision."
)
AGE_FROM_GROUP = {"under5": 3, "child": 8, "teen": 15, "adult": 35, "elderly": 70}

# ---------------------------------------------------------------- input data


@dataclass
class Reading:
    kind: str  # systolic_bp, diastolic_bp, pulse, temp_c, spo2, resp_rate, weight_kg, height_cm, blood_glucose
    value: float
    at: datetime
    facility: str
    today: bool


@dataclass
class LabValue:
    key: str  # hba1c, fbs, rbs, chol, ldl, hdl, triglycerides, hb, creatinine, malaria, wbc
    value: Any
    num: float | None
    unit: str | None
    at: datetime
    facility: str
    test: str
    today: bool


@dataclass
class Record:
    """Everything the engine may read for one encounter, already filtered by who is allowed to see what."""

    sex: str  # female | male | unknown
    pregnant: bool
    age: int | None
    age_source: str  # "date of birth" | "age group (estimated)"
    here: str  # this facility's name
    complaint: str
    readings: list[Reading]
    labs: list[LabValue]
    allergies: list[ms.HistoryItem]
    conditions: list[ms.HistoryItem]
    medications: list[ms.HistoryItem]
    family: list[ms.HistoryItem]  # text = "Mother: Type 2 diabetes"
    prior_visits: int
    prior_facilities: list[str]
    notes: list[tuple[str, str]] = field(default_factory=list)  # (source label, lowercase text) for provenance


LAB_KEYS = [
    ("hba1c", lambda p: "hba1c" in p or "a1c" in p),
    ("fbs", lambda p: "fasting" in p and ("glucose" in p or "sugar" in p)),
    ("rbs", lambda p: "random" in p and ("glucose" in p or "sugar" in p)),
    ("ldl", lambda p: "ldl" in p),
    ("hdl", lambda p: "hdl" in p),
    ("triglycerides", lambda p: "triglyceride" in p),
    ("chol", lambda p: "cholesterol" in p and "ldl" not in p and "hdl" not in p),
    ("hb", lambda p: p in ("hb", "haemoglobin", "hemoglobin") or p.startswith(("haemoglobin", "hemoglobin"))),
    ("creatinine", lambda p: "creatinine" in p),
    ("malaria", lambda p: "malaria" in p or p == "mp"),
    ("wbc", lambda p: "wbc" in p or "white cell" in p),
]


def lab_key(param: str) -> str | None:
    p = param.lower().strip()
    for key, fn in LAB_KEYS:
        if fn(p):
            return key
    return None


def age_from(dob: date | None, group: str | None) -> tuple[int | None, str]:
    if dob:
        t = date.today()
        return t.year - dob.year - ((t.month, t.day) < (dob.month, dob.day)), "date of birth"
    if group in AGE_FROM_GROUP:
        return AGE_FROM_GROUP[group], "age group (estimated)"
    return None, "unknown"


# ---------------------------------------------------------------- helpers


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%d %b %Y") if dt else "date unknown"


def _has(text: str, words: list[str]) -> list[str]:
    return [w for w in words if w in text]


def _likelihood(score: float) -> float:
    return max(0.05, min(0.95, 1 - math.exp(-score / 4.0)))


def _label(p: float) -> str:
    return "High" if p >= 0.7 else "Moderate" if p >= 0.4 else "Low"


def _ev(text: str, source: str, kind: str) -> dict:
    return {"text": text, "source": source, "kind": kind}


# ---------------------------------------------------------------- engine


class Assessment:
    def __init__(self, r: Record):
        self.r = r
        self.text = r.complaint.lower()
        self.trace: list[str] = []
        self.missing: list[str] = []
        self.vitals: dict[str, float] = {}
        self.today_src: dict[str, str] = {}
        for x in sorted(r.readings, key=lambda x: x.at):
            if x.today:
                self.vitals[x.kind] = x.value
                self.today_src[x.kind] = x.facility
        self.hist: dict[str, list[Reading]] = {}
        for x in sorted(r.readings, key=lambda x: x.at):
            self.hist.setdefault(x.kind, []).append(x)
        self.labs: dict[str, list[LabValue]] = {}
        for lv in sorted(r.labs, key=lambda x: x.at):
            self.labs.setdefault(lv.key, []).append(lv)
        self.conds = [c.text.lower() for c in r.conditions]
        self.meds = [m.text.lower() for m in r.medications]

    # ---- provenance
    def src_today(self, what: str = "vitals") -> str:
        return f"Today · {self.r.here} ({what})"

    def src_lab(self, lab: LabValue) -> str:
        return f"Today · {lab.facility} (lab)" if lab.today else f"{lab.facility} · {_fmt(lab.at)} (lab)"

    def provenance(self, item: str) -> str | None:
        for h in [*self.r.conditions, *self.r.medications, *self.r.allergies]:
            if item.lower()[:6] in h.text.lower():
                return h.source
        word = re.split(r"[\s(/,]+", item.lower().strip())[0]
        for src, blob in self.r.notes:
            if word and word in blob:
                return src
        return None

    def latest_lab(self, key: str) -> LabValue | None:
        vals = [x for x in self.labs.get(key, []) if x.num is not None]
        return vals[-1] if vals else None

    def last_value(self, kind: str) -> float | None:
        if kind in self.vitals:
            return self.vitals[kind]
        h = self.hist.get(kind)
        return h[-1].value if h else None

    def bmi(self) -> float | None:
        w, h = self.last_value("weight_kg"), self.last_value("height_cm")
        return round(w / ((h / 100) ** 2), 1) if w and h else None

    def glucose_now(self) -> tuple[float, str] | None:
        if "blood_glucose" in self.vitals:
            return self.vitals["blood_glucose"], self.src_today("point-of-care glucose")
        for key in ("rbs", "fbs"):
            lab = self.latest_lab(key)
            if lab and lab.num is not None:
                return lab.num, self.src_lab(lab)
        return None

    def family_with(self, words: list[str]) -> list[ms.HistoryItem]:
        return [f for f in self.r.family if any(w in f.text.lower() for w in words)]

    # ---- trends
    def trends(self) -> list[dict]:
        out = []
        for key, label, unit, delta in [("systolic_bp", "Systolic blood pressure", "mmHg", 8),
                                        ("diastolic_bp", "Diastolic blood pressure", "mmHg", 6),
                                        ("weight_kg", "Body weight", "kg", 2),
                                        ("blood_glucose", "Blood glucose (point of care)", "mg/dL", 20)]:
            pts = self.hist.get(key, [])
            if len(pts) >= 2:
                first, last = pts[0].value, pts[-1].value
                direction = "rising" if last - first >= delta else "falling" if first - last >= delta else "stable"
                facs = {p.facility for p in pts}
                out.append({"metric": key, "label": label, "unit": unit, "direction": direction,
                            "points": [{"date": p.at.isoformat(), "value": p.value, "facility": p.facility} for p in pts],
                            "text": f"{label} {direction}: " + " → ".join(f"{p.value:g}" for p in pts)
                                    + f" {unit} across {len(facs)} facilit{'y' if len(facs) == 1 else 'ies'}"})
        for key, label, unit, delta in [("fbs", "Fasting blood glucose", "mg/dL", 10), ("hba1c", "HbA1c", "%", 0.3),
                                        ("chol", "Total cholesterol", "mg/dL", 15)]:
            pts = [x for x in self.labs.get(key, []) if x.num is not None]
            if len(pts) >= 2:
                first, last = pts[0].num, pts[-1].num
                direction = "rising" if last - first >= delta else "falling" if first - last >= delta else "stable"
                out.append({"metric": key, "label": label, "unit": unit, "direction": direction,
                            "points": [{"date": p.at.isoformat(), "value": p.num, "facility": p.facility} for p in pts],
                            "text": f"{label} {direction}: " + " → ".join(f"{p.num:g}" for p in pts) + f" {unit}"})
        return out

    # ---- the team's ML models
    def run_diabetes_model(self) -> dict | None:
        g = self.glucose_now()
        if not g or self.r.age is None:
            self.missing.append("No blood glucose: the team's diabetes model was not run (record a point-of-care glucose).")
            return None
        dbp, bmi = self.vitals.get("diastolic_bp"), self.bmi()
        first_degree = [f for f in self.family_with(["diabetes"])
                        if any(k in f.text.lower() for k in ("mother", "father", "sister", "brother", "son",
                                                             "daughter", "sibling", "child"))]
        n_fam = len(self.family_with(["diabetes"]))
        dpf = round(min(1.5, 0.25 + 0.35 * len(first_degree) + 0.15 * (n_fam - len(first_degree))), 2)
        age_src = "record" if self.r.age_source == "date of birth" else "assumed"
        inputs = [
            {"feature": "Glucose", "label": "Plasma glucose", "value": g[0], "source": "measured", "detail": g[1]},
            {"feature": "BloodPressure", "label": "Diastolic BP", "value": dbp or 72.0,
             "source": "measured" if dbp else "assumed", "detail": self.src_today() if dbp else "Not recorded: population mean"},
            {"feature": "BMI", "label": "Body-mass index", "value": bmi or 27.0, "source": "derived" if bmi else "assumed",
             "detail": "Weight ÷ height² from the record" if bmi else "Not recorded: population mean"},
            {"feature": "Age", "label": "Age", "value": self.r.age, "source": age_src, "detail": self.r.age_source},
            {"feature": "DiabetesPedigreeFunction", "label": "Family diabetes risk", "value": dpf, "source": "derived",
             "detail": f"{n_fam} relative(s) with diabetes in family history"},
            {"feature": "Pregnancies", "label": "Pregnancies", "value": 0, "source": "assumed", "detail": "Not recorded"},
            {"feature": "SkinThickness", "label": "Skin-fold thickness", "value": 0, "source": "imputed",
             "detail": "Not measured: imputed by the model pipeline"},
            {"feature": "Insulin", "label": "Serum insulin", "value": 0, "source": "imputed",
             "detail": "Not measured: imputed by the model pipeline"},
        ]
        try:
            res = models.predict_diabetes({i["feature"]: i["value"] for i in inputs})
        except models.ModelUnavailable as exc:
            self.trace.append(f"Team diabetes model unavailable ({exc}); continuing with clinical rules.")
            return None
        measured = sum(1 for i in inputs if i["source"] in ("measured", "derived", "record"))
        self.trace.append(f"Ran the team's diabetes model ({res['model_version']}) on {measured}/8 documented inputs "
                          f"→ {models.band(res['probability']).lower()} band.")
        return {"key": "diabetes", "name": "Type 2 diabetes risk", "model_version": res["model_version"],
                "algorithm": "Support Vector Classifier, trained by the VITALIS team (Pima diabetes dataset)",
                "probability": res["probability"], "band": models.band(res["probability"]),
                "inputs": inputs, "measured_inputs": measured, "total_inputs": len(inputs),
                "note": "Not a calibrated probability. Not yet validated on Nigerian patients."}

    def run_heart_model(self) -> dict | None:
        sbp = self.vitals.get("systolic_bp")
        if not sbp or self.r.age is None:
            return None
        chol, fbs, g = self.latest_lab("chol"), self.latest_lab("fbs"), self.glucose_now()
        chest = bool(_has(self.text, ["chest pain", "chest tightness", "angina"]))
        age_src = "record" if self.r.age_source == "date of birth" else "assumed"
        inputs = [
            {"feature": "age", "label": "Age", "value": self.r.age, "source": age_src, "detail": self.r.age_source},
            {"feature": "sex", "label": "Sex", "value": 0 if self.r.sex == "female" else 1, "source": "record",
             "detail": self.r.sex},
            {"feature": "trestbps", "label": "Resting systolic BP", "value": sbp, "source": "measured",
             "detail": self.src_today()},
            {"feature": "chol", "label": "Serum cholesterol", "value": chol.num if chol else 200.0,
             "source": "measured" if chol else "assumed",
             "detail": self.src_lab(chol) if chol else "No lipid profile on record: population mean"},
            {"feature": "fbs", "label": "Fasting glucose > 120 mg/dL",
             "value": 1 if (fbs and fbs.num and fbs.num > 120) or (g and g[0] > 200) else 0,
             "source": "measured" if (fbs or g) else "assumed",
             "detail": self.src_lab(fbs) if fbs else (g[1] if g else "Not recorded")},
            {"feature": "cp", "label": "Chest pain type", "value": 1 if chest else 0, "source": "derived",
             "detail": "From the presenting complaint"},
            {"feature": "thalach", "label": "Max heart rate", "value": float(220 - self.r.age), "source": "assumed",
             "detail": "No exercise test: age-predicted maximum"},
            {"feature": "restecg", "label": "Resting ECG", "value": 0, "source": "assumed", "detail": "ECG not on record"},
            {"feature": "exang", "label": "Exercise angina", "value": 0, "source": "assumed", "detail": "No exercise test"},
            {"feature": "oldpeak", "label": "ST depression", "value": 0.0, "source": "assumed", "detail": "No exercise ECG"},
            {"feature": "slope", "label": "ST slope", "value": 2, "source": "assumed", "detail": "No exercise ECG"},
            {"feature": "ca", "label": "Vessels on fluoroscopy", "value": 0, "source": "assumed", "detail": "No angiography"},
            {"feature": "thal", "label": "Thallium scan", "value": 2, "source": "assumed", "detail": "Not performed"},
        ]
        try:
            res = models.predict_heart({i["feature"]: i["value"] for i in inputs})
        except models.ModelUnavailable as exc:
            self.trace.append(f"Team heart model unavailable ({exc}).")
            return None
        measured = sum(1 for i in inputs if i["source"] in ("measured", "derived", "record"))
        self.trace.append(f"Ran the team's cardiovascular screen ({res['model_version']}) on {measured}/13 documented "
                          "inputs (screening only).")
        return {"key": "heart", "name": "Cardiovascular disease screen", "model_version": res["model_version"],
                "algorithm": "Random Forest, trained by the VITALIS team (UCI heart disease dataset)",
                "probability": res["probability"], "band": models.band(res["probability"]),
                "inputs": inputs, "measured_inputs": measured, "total_inputs": len(inputs),
                "note": "Several exercise-test inputs are not available outside a cardiology work-up, so this is "
                        "indicative only. An ECG and lipid profile improve it."}

    # ---- red flags (clinician view; patient triage has its own rules)
    def red_flags(self) -> list[dict]:
        v, flags = self.vitals, []
        sbp, dbp = v.get("systolic_bp"), v.get("diastolic_bp")
        bp = f"{sbp:g}/{dbp:g}" if sbp and dbp else f"{sbp or dbp:g}" if (sbp or dbp) else ""
        organ = _has(self.text, ["blurred vision", "visual", "severe headache", "headache", "chest pain", "confusion",
                                 "weakness", "breathless", "shortness of breath", "nosebleed"])
        if (sbp and sbp >= 180) or (dbp and dbp >= 120):
            flags.append({"severity": "critical", "title": "Severe hypertension", "detail": f"BP {bp} mmHg.",
                          "action": "Repeat BP after 5 min rest; assess urgently for hypertensive emergency."})
        elif ((sbp and sbp >= 160) or (dbp and dbp >= 100)) and organ:
            flags.append({"severity": "high", "title": "Markedly raised BP with possible target-organ symptoms",
                          "detail": f"BP {bp} mmHg with {', '.join(organ[:3])}.",
                          "action": "Same-visit review: fundoscopy, urine protein, ECG and creatinine."})
        if v.get("spo2") is not None and v["spo2"] < 92:
            flags.append({"severity": "critical", "title": "Hypoxaemia", "detail": f"SpO₂ {v['spo2']:g}%.",
                          "action": "Oxygen; assess airway and breathing now."})
        if v.get("temp_c") is not None and v["temp_c"] >= 39.5:
            flags.append({"severity": "high", "title": "High fever", "detail": f"{v['temp_c']:g} °C.",
                          "action": "Screen for sepsis and severe malaria."})
        if v.get("pulse") is not None and (v["pulse"] >= 130 or v["pulse"] < 40):
            flags.append({"severity": "critical", "title": "Critical heart rate", "detail": f"{v['pulse']:g} bpm.",
                          "action": "ECG and immediate review."})
        if v.get("resp_rate") is not None and v["resp_rate"] >= 30:
            flags.append({"severity": "critical", "title": "Severe tachypnoea", "detail": f"RR {v['resp_rate']:g}/min.",
                          "action": "Immediate respiratory assessment."})
        g = v.get("blood_glucose")
        if g is not None and g >= 300:
            flags.append({"severity": "high", "title": "Severe hyperglycaemia", "detail": f"Glucose {g:g} mg/dL.",
                          "action": "Check ketones and hydration (exclude DKA/HHS)."})
        if g is not None and g < 70:
            flags.append({"severity": "critical", "title": "Hypoglycaemia", "detail": f"Glucose {g:g} mg/dL.",
                          "action": "Give glucose now; recheck in 15 minutes."})
        if self.r.pregnant and sbp and dbp and (sbp >= 140 or dbp >= 90):
            flags.append({"severity": "critical", "title": "Raised BP in pregnancy",
                          "detail": f"BP {bp} mmHg in a pregnant woman.",
                          "action": "Assess for pre-eclampsia: urine protein, symptoms, obstetric review now."})
        return flags

    # ---- conditions
    def _hypertension(self) -> dict | None:
        sbp, dbp = self.vitals.get("systolic_bp"), self.vitals.get("diastolic_bp")
        score, ev, against = 0.0, [], []
        if sbp and dbp:
            if sbp >= 160 or dbp >= 100:
                score += 3.5
                ev.append(_ev(f"BP {sbp:g}/{dbp:g} mmHg today: stage 2 range", self.src_today(), "current"))
            elif sbp >= 140 or dbp >= 90:
                score += 2.0
                ev.append(_ev(f"BP {sbp:g}/{dbp:g} mmHg today: stage 1 range", self.src_today(), "current"))
            else:
                against.append(_ev(f"BP {sbp:g}/{dbp:g} mmHg today is within target", self.src_today(), "current"))
        prior_high = [x for x in self.hist.get("systolic_bp", []) if x.value >= 140 and not x.today]
        if prior_high:
            score += min(3.0, 1.0 * len(prior_high))
            ev.append(_ev(f"Raised systolic BP on {len(prior_high)} earlier visit(s): "
                          + ", ".join(f"{x.value:g} ({x.facility}, {_fmt(x.at)})" for x in prior_high),
                          "VITALIS record", "history"))
        on_tx = [m.text for m in self.r.medications if any(k in m.text.lower() for k in [
            "amlodipine", "lisinopril", "losartan", "nifedipine", "hydrochlorothiazide", "atenolol", "methyldopa",
            "ramipril", "telmisartan"])]
        if any("hypertension" in c for c in self.conds):
            score += 1.0
            ev.append(_ev("Hypertension already on the problem list", self.provenance("hypertension") or "Record",
                          "history"))
        if on_tx and sbp and sbp >= 140:
            score += 1.0
            ev.append(_ev(f"BP above target despite {', '.join(on_tx)}", self.provenance(on_tx[0]) or "Medicines",
                          "history"))
        for f in self.family_with(["hypertension", "stroke"]):
            score += 0.5
            ev.append(_ev(f"Family: {f.text}", f.source or "Family history", "family"))
        bmi = self.bmi()
        if bmi and bmi >= 30:
            score += 0.5
            ev.append(_ev(f"BMI {bmi} kg/m² (obesity)", self.src_today("weight & height"), "current"))
        if score < 2:
            return None
        stage2 = bool(sbp and (sbp >= 160 or (dbp or 0) >= 100))
        name = ("Uncontrolled stage 2 hypertension" if on_tx and stage2 else
                "Stage 2 hypertension" if stage2 else "Hypertension")
        if _has(self.text, ["blurred vision", "visual"]) and sbp and sbp >= 160:
            name += ": exclude hypertensive urgency / retinopathy"
        return {"key": "hypertension", "condition": name, "score": score, "evidence": ev, "against": against,
                "recommended_investigations": ["Repeat BP after 5 min rest", "Fundoscopy", "Urinalysis",
                                               "Electrolytes, urea, creatinine", "ECG", "Lipid profile"],
                "management_considerations": ["Confirm adherence to current antihypertensive",
                                              "Optimise or add a second agent per guideline",
                                              "Salt reduction, weight, activity", "Review in 2–4 weeks with home BP"],
                "guideline": "WHO 2021 Hypertension Guideline · NICE NG136"}

    def _diabetes(self, ml: dict | None) -> dict | None:
        score, ev, against = 0.0, [], []
        known = any("diabetes" in c and "pre" not in c for c in self.conds)
        g = self.glucose_now()
        osmotic = _has(self.text, ["thirst", "frequent urination", "passing urine often", "weight loss", "tired",
                                   "fatigue", "blurred vision", "weak"])
        if g:
            if g[0] >= 200:
                score += 3.0
                ev.append(_ev(f"Glucose {g[0]:g} mg/dL (≥ 200)", g[1], "current"))
            elif g[0] >= 140:
                score += 1.5
                ev.append(_ev(f"Glucose {g[0]:g} mg/dL (elevated)", g[1], "current"))
            else:
                against.append(_ev(f"Glucose {g[0]:g} mg/dL is not elevated", g[1], "current"))
        if osmotic:
            score += 1.5
            ev.append(_ev("Classic symptoms reported: " + ", ".join(osmotic), self.src_today("complaint"), "current"))
        if g and g[0] >= 200 and osmotic:
            score += 1.0
            ev.append(_ev("Symptoms + random glucose ≥ 200 mg/dL meet the WHO threshold, pending confirmation",
                          "WHO diagnostic criteria", "rule"))
        for lab in self.labs.get("hba1c", []):
            if lab.num is None:
                continue
            if lab.num >= 6.5:
                score += 3.0
                ev.append(_ev(f"HbA1c {lab.num:g}% (diabetic range)", self.src_lab(lab), "lab"))
            elif lab.num >= 5.7:
                score += 1.5
                ev.append(_ev(f"HbA1c {lab.num:g}% (prediabetes range)", self.src_lab(lab), "lab"))
        fbs = [x for x in self.labs.get("fbs", []) if x.num is not None]
        raised = [x for x in fbs if x.num >= 100]
        if raised:
            score += 0.8 * len(raised)
            ev.append(_ev("Fasting glucose " + " → ".join(f"{x.num:g}" for x in fbs) + " mg/dL (above 100)",
                          " / ".join(sorted({x.facility for x in fbs})), "lab"))
        for f in self.family_with(["diabetes"]):
            score += 0.7
            ev.append(_ev(f"Family: {f.text}", f.source or "Family history", "family"))
        bmi = self.bmi()
        if bmi and bmi >= 30:
            score += 0.5
            ev.append(_ev(f"BMI {bmi} kg/m²", self.src_today("weight & height"), "current"))
        if self.r.age and self.r.age >= 45:
            score += 0.3
        if ml:
            ev.append(_ev(f"Team diabetes model: {ml['band'].lower()} risk band", ml["model_version"], "ml"))
        if score < 2 and not known:
            return None
        name = ("Type 2 diabetes: assess glycaemic control" if known else
                "Type 2 diabetes mellitus (probable new diagnosis)" if score >= 6 else
                "Impaired glucose regulation / prediabetes")
        return {"key": "diabetes", "condition": name, "score": score, "evidence": ev, "against": against,
                "ml_probability": ml["probability"] if ml else None,
                "recommended_investigations": ["HbA1c", "Fasting plasma glucose", "Urinalysis", "Creatinine / eGFR",
                                               "Lipid profile"],
                "management_considerations": ["Confirm with HbA1c or repeat fasting glucose",
                                              "Diet and activity counselling",
                                              "If confirmed: first-line oral therapy per guideline, renal function first",
                                              "Retinal and foot screening"],
                "guideline": "WHO 2019 Diabetes Classification · ADA Standards of Care 2026"}

    def _dyslipidaemia(self) -> dict | None:
        chol, ldl = self.latest_lab("chol"), self.latest_lab("ldl")
        score, ev = 0.0, []
        if chol and chol.num >= 200:
            score += 2.0 if chol.num >= 240 else 1.2
            ev.append(_ev(f"Total cholesterol {chol.num:g} mg/dL", self.src_lab(chol), "lab"))
        if ldl and ldl.num >= 130:
            score += 2.0 if ldl.num >= 160 else 1.0
            ev.append(_ev(f"LDL cholesterol {ldl.num:g} mg/dL", self.src_lab(ldl), "lab"))
        if score < 2:
            return None
        return {"key": "dyslipidaemia", "condition": "Dyslipidaemia (raised cardiovascular risk)", "score": score,
                "evidence": ev, "against": [],
                "recommended_investigations": ["Repeat fasting lipid profile", "10-year cardiovascular risk"],
                "management_considerations": ["Lifestyle modification", "Consider a statin given combined risk"],
                "guideline": "WHO HEARTS · NICE NG238"}

    def _malaria(self) -> dict | None:
        fever = _has(self.text, ["fever", "hot body", "very hot body", "chills", "rigors", "body ache", "malaise"])
        temp = self.vitals.get("temp_c")
        score, ev, against = 0.0, [], []
        if fever:
            score += 2.0
            ev.append(_ev("Febrile symptoms: " + ", ".join(fever), self.src_today("complaint"), "current"))
        if temp is not None:
            if temp >= 37.8:
                score += 2.0
                ev.append(_ev(f"Temperature {temp:g} °C", self.src_today(), "current"))
            else:
                against.append(_ev(f"Afebrile today ({temp:g} °C)", self.src_today(), "current"))
        positive_today = [x for x in self.labs.get("malaria", []) if str(x.value).lower().startswith("pos") and x.today]
        if positive_today:
            # Parasitological confirmation is the strongest evidence (not in the NCS original, which only used past tests).
            score += 3.0
            ev.append(_ev(f"{positive_today[-1].test}: positive", self.src_lab(positive_today[-1]), "lab"))
        prior = [x for x in self.labs.get("malaria", []) if str(x.value).lower().startswith("pos") and not x.today]
        if prior and fever:
            score += 0.5
            ev.append(_ev(f"Earlier positive malaria test ({prior[-1].facility}, {_fmt(prior[-1].at)})", "Record",
                          "history"))
        if score < 2.5:
            return None
        return {"key": "malaria", "condition": "Malaria (P. falciparum, endemic setting)", "score": score,
                "evidence": ev, "against": against,
                "recommended_investigations": ["Malaria RDT", "Thick & thin blood film", "Full blood count"],
                "management_considerations": ["Treat only confirmed malaria", "Check for severe-malaria criteria"],
                "guideline": "WHO Malaria Guidelines 2025 · Nigeria National Malaria Treatment Guidelines"}

    def _respiratory(self) -> dict | None:
        sx = _has(self.text, ["cough", "sputum", "breathless", "shortness of breath", "hard to breathe", "wheeze"])
        if not sx:
            return None
        score, ev = 2.0, [_ev("Respiratory symptoms: " + ", ".join(sx), self.src_today("complaint"), "current")]
        spo2, rr, temp = self.vitals.get("spo2"), self.vitals.get("resp_rate"), self.vitals.get("temp_c")
        if spo2 is not None and spo2 < 94:
            score += 1.5
            ev.append(_ev(f"SpO₂ {spo2:g}%", self.src_today(), "current"))
        if rr is not None and rr > 22:
            score += 1.0
            ev.append(_ev(f"Respiratory rate {rr:g}/min", self.src_today(), "current"))
        if temp is not None and temp >= 37.8:
            score += 1.0
            ev.append(_ev(f"Fever {temp:g} °C", self.src_today(), "current"))
        asthma = any("asthma" in c for c in self.conds)
        name = ("Acute asthma exacerbation" if asthma and _has(self.text, ["wheeze", "breathless", "hard to breathe"])
                else "Lower respiratory tract infection / community-acquired pneumonia")
        return {"key": "respiratory", "condition": name, "score": score, "evidence": ev, "against": [],
                "recommended_investigations": ["Chest X-ray", "Full blood count", "Peak flow (if asthmatic)"],
                "management_considerations": ["Assess severity (CURB-65 / asthma severity)", "Oxygen if SpO₂ < 94%"],
                "guideline": "WHO IMAI · BTS/SIGN Asthma"}

    # ---- treatment options: drug names + reasons + safety verdict. No doses (the doctor prescribes).
    MED_OPTIONS = {
        "hypertension": [("Amlodipine", "Calcium-channel blocker", True),
                         ("Lisinopril", "ACE inhibitor: preferred add-on when diabetes is suspected (renal protection)", False),
                         ("Hydrochlorothiazide", "Thiazide diuretic: common second-line agent", False)],
        "diabetes": [("Metformin", "First-line oral agent once confirmed and eGFR is adequate", False)],
        "dyslipidaemia": [("Atorvastatin", "Moderate-intensity statin for combined risk", False),
                          ("Simvastatin", "Alternative statin", False)],
        "malaria": [("Artemether-lumefantrine", "WHO first-line ACT for uncomplicated falciparum malaria", False)],
        "respiratory": [("Amoxicillin", "First-line for non-severe community-acquired pneumonia", False),
                        ("Salbutamol inhaler", "Short-acting bronchodilator", False)],
    }

    def medication_options(self, keys: list[str]) -> list[dict]:
        out = []
        for key in keys:
            for drug, why, optimise in self.MED_OPTIONS.get(key, []):
                already = any(drug.lower() in m for m in self.meds)
                if optimise != already:
                    continue  # optimisation only for current drugs, new starts only for others
                res = ms.check(drug, self.r.allergies, self.r.medications, self.r.conditions, self.r.pregnant)
                alerts = [a["text"] + (f" Recorded at {a['source']}." if a.get("source") else "") for a in res.alerts]
                verdict = res.verdict
                if drug in ("Metformin", "Lisinopril") and not self.latest_lab("creatinine"):
                    alerts.append("Check renal function (creatinine/eGFR) first.")
                    verdict = "caution" if verdict == "ok" else verdict
                out.append({"drug": drug + (" (optimise current dose)" if optimise else ""), "for_condition": key,
                            "rationale": why, "safety": verdict, "alerts": alerts})
        return out

    # ---- main
    def run(self) -> dict:
        r = self.r
        self.trace.append(f"Loaded {r.prior_visits} earlier visit(s)"
                          + (f" at {', '.join(r.prior_facilities)}" if r.prior_facilities else "")
                          + " and the referral that brought the patient in.")
        n_vit, n_lab = len(r.readings), len(r.labs)
        self.trace.append(f"Read {n_vit} vital-sign readings and {n_lab} lab values; {len(r.family)} family-history "
                          f"entries.")
        self.trace.append(f"Cross-referenced {len(r.allergies)} allergy(ies) and {len(r.medications)} current "
                          "medicine(s) recorded across the network.")
        trends = self.trends()
        for t in trends:
            if t["direction"] == "rising":
                self.trace.append(f"Detected trend: {t['text']}.")
        flags = self.red_flags()
        self.trace.append(f"Red-flag screen: {len(flags)} alert(s)." if flags else "Red-flag screen: no emergency criteria met.")
        ml_d, ml_h = self.run_diabetes_model(), self.run_heart_model()
        conds = [c for c in (self._hypertension(), self._diabetes(ml_d), self._dyslipidaemia(), self._malaria(),
                             self._respiratory()) if c]
        for c in conds:
            p = _likelihood(c.pop("score"))
            if c.get("ml_probability") is not None:
                p = 0.65 * p + 0.35 * c["ml_probability"]
            c.pop("ml_probability", None)
            c["likelihood"] = round(p, 2)
            c["likelihood_label"] = _label(p)
        conds.sort(key=lambda c: c["likelihood"], reverse=True)
        if not conds:
            conds = [{"key": "nonspecific", "condition": "Non-specific presentation: clinical evaluation required",
                      "likelihood": 0.3, "likelihood_label": "Low", "evidence": [], "against": [],
                      "recommended_investigations": ["Full blood count", "Urinalysis", "Malaria RDT"],
                      "management_considerations": ["Detailed history and examination"], "guideline": "—"}]
        for i, c in enumerate(conds, 1):
            c["rank"] = i
        self.trace.append(f"Ranked {len(conds)} possible condition(s) by documented evidence.")
        meds = self.medication_options([c["key"] for c in conds])
        avoid = [m for m in meds if m["safety"] == "avoid"]
        self.trace.append(f"Screened {len(meds)} treatment option(s) against allergies and medicines: "
                          f"{len(avoid)} to avoid.")
        for k, label in [("systolic_bp", "Blood pressure"), ("pulse", "Pulse"), ("temp_c", "Temperature"),
                         ("spo2", "SpO₂"), ("weight_kg", "Weight")]:
            if k not in self.vitals:
                self.missing.append(f"{label} not recorded at this visit.")
        if not self.latest_lab("creatinine"):
            self.missing.append("No renal function (creatinine/eGFR) on record: needed before an ACE inhibitor or metformin.")
        if r.age_source != "date of birth":
            self.missing.append("Exact age unknown: the models used an estimate from the age group.")

        v = self.vitals
        bits = []
        if "systolic_bp" in v and "diastolic_bp" in v:
            bits.append(f"BP {v['systolic_bp']:g}/{v['diastolic_bp']:g}")
        if "blood_glucose" in v:
            bits.append(f"glucose {v['blood_glucose']:g} mg/dL")
        if "temp_c" in v:
            bits.append(f"T {v['temp_c']:g} °C")
        if "spo2" in v:
            bits.append(f"SpO₂ {v['spo2']:g}%")
        if self.bmi():
            bits.append(f"BMI {self.bmi()}")
        who = (f"{r.age}-year-old" if r.age_source == "date of birth" else "Adult" if (r.age or 0) >= 18 else "Young") \
            + f" {r.sex if r.sex != 'unknown' else 'patient'}" + (" (pregnant)" if r.pregnant else "")
        summary = (who
                   + (f" with {', '.join(c.text for c in r.conditions)}" if r.conditions else "")
                   + (f", on {', '.join(m.text for m in r.medications)}" if r.medications else "")
                   + f". {r.prior_visits} earlier visit(s) on record. "
                   + (f"Presents with: {r.complaint}. " if r.complaint else "")
                   + (f"Today: {', '.join(bits)}. " if bits else "")
                   + f"Top consideration: {conds[0]['condition']} ({conds[0]['likelihood_label'].lower()} likelihood)."
                   + (f" {len(avoid)} commonly used option(s) conflict with this patient's record." if avoid else ""))
        return {
            "engine_version": ENGINE_VERSION,
            "generated_at": datetime.now(UTC).isoformat(),
            "data_coverage": {"prior_visits": r.prior_visits, "facilities": r.prior_facilities, "vital_readings": n_vit,
                              "lab_values": n_lab, "family_history_entries": len(r.family)},
            "analysis_trace": self.trace,
            "summary": summary,
            "red_flags": flags,
            "conditions": conds,
            "trends": trends,
            "ml_models": [m for m in (ml_d, ml_h) if m],
            "medication_options": meds,
            "missing_data": self.missing,
            "safety_disclaimer": DISCLAIMER,
        }
