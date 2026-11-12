"""The VITALIS team's trained risk models (from the NCS repo): diabetes (SVC) and heart disease (Random Forest).

Loading a .joblib file unpickles it, which can run code. So before loading we
  1. check the file's SHA-256 against the pinned hash, and
  2. unpickle through an allowlist that only accepts sklearn / numpy / joblib classes and the team's one helper.
If anything fails, callers get ModelUnavailable and the doctor screen carries on with clinical rules only.
"""

import hashlib
import logging
import sys
import threading
import types
import warnings
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import BACKEND_DIR, get_settings

log = logging.getLogger("vitalis.ncs_models")

MODEL_DIR = BACKEND_DIR / "ml_models"
PINNED = {
    "diabetes_prediction_pipeline.joblib": "32b9723f9a08cd7ea9f243ee877a343582bb6ff309998e671bff8ebd966d6194",
    "heart_disease_prediction_pipeline.joblib": "eb5eb079dd3295edde1040c6bc953d98018ffb9e548c009d5517702867e117fb",
}
ALLOWED_PREFIXES = ("sklearn.", "numpy", "joblib.", "scipy.")
ALLOWED_EXACT = {("src.common.preprocessing_util", "replace_zeros_with_nan"), ("builtins", "slice"),
                 ("builtins", "set"), ("builtins", "frozenset"), ("builtins", "dict"), ("builtins", "list"),
                 ("builtins", "tuple"), ("builtins", "object"), ("collections", "OrderedDict"),
                 ("copyreg", "_reconstructor")}

DIABETES_VERSION = "NCS-SVC-DiabetesV1"
HEART_VERSION = "NCS-RandomForest-HeartV1"


class ModelUnavailable(Exception):
    pass


def _install_helper_module() -> None:
    """The diabetes pipeline references the team's helper `src.common.preprocessing_util.replace_zeros_with_nan`."""
    if "src.common.preprocessing_util" in sys.modules:
        return
    src, common, util = (types.ModuleType(n) for n in ("src", "src.common", "src.common.preprocessing_util"))
    util.replace_zeros_with_nan = lambda X: np.where(X == 0, np.nan, X)  # type: ignore[attr-defined]
    sys.modules.update({"src": src, "src.common": common, "src.common.preprocessing_util": util})


_lock = threading.Lock()
_cache: dict[str, Any] = {}


def _safe_load(name: str) -> Any:
    import joblib.numpy_pickle as jnp

    path = Path(get_settings().ncs_model_dir or MODEL_DIR) / name
    if not path.exists():
        raise ModelUnavailable(f"{name} not found")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != PINNED[name]:
        raise ModelUnavailable(f"{name} failed its integrity check")
    _install_helper_module()

    original = jnp.NumpyUnpickler.find_class

    def guarded(self, module: str, cls: str):
        if module.startswith(ALLOWED_PREFIXES) or (module, cls) in ALLOWED_EXACT:
            return original(self, module, cls)
        raise ModelUnavailable(f"model file tried to load {module}.{cls}")

    jnp.NumpyUnpickler.find_class = guarded
    try:
        import joblib

        model = joblib.load(path)
    finally:
        jnp.NumpyUnpickler.find_class = original
    # Single-row inference is faster without thread fan-out.
    inner = getattr(model, "named_steps", {}).get("model")
    if inner is not None and hasattr(inner, "n_jobs"):
        inner.n_jobs = 1
    return model


def _model(name: str) -> Any:
    if not get_settings().enable_ncs_models:
        raise ModelUnavailable("models disabled by configuration")
    with _lock:
        if name not in _cache:
            try:
                _cache[name] = _safe_load(name)
            except ModelUnavailable:
                raise
            except Exception as exc:  # version mismatch, corrupt file, ...
                raise ModelUnavailable(f"{name}: {type(exc).__name__}") from exc
        return _cache[name]


def _frame(model: Any, features: dict[str, float]):
    import pandas as pd

    cols = list(getattr(model, "feature_names_in_", features.keys()))
    missing = [c for c in cols if c not in features]
    if missing:
        raise ModelUnavailable(f"missing model features: {missing}")
    return pd.DataFrame([[features[c] for c in cols]], columns=cols)


def band(probability: float) -> str:
    """Models are not calibrated for this population: show a qualitative band, never a percentage."""
    return "High" if probability >= 0.6 else "Moderate" if probability >= 0.3 else "Low"


def predict_diabetes(features: dict[str, float]) -> dict[str, Any]:
    """Features: Pregnancies, Glucose, BloodPressure, SkinThickness, Insulin, BMI, DiabetesPedigreeFunction, Age."""
    m = _model("diabetes_prediction_pipeline.joblib")
    df = _frame(m, features)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # their pipeline drops column names internally
        p = float(m.predict_proba(df)[0][1])
        pred = int(m.predict(df)[0])
    return {"probability": round(p, 4), "prediction": pred, "model_version": DIABETES_VERSION}


def predict_heart(features: dict[str, float]) -> dict[str, Any]:
    """Features: age, sex, cp, trestbps, chol, fbs, restecg, thalach, exang, oldpeak, slope, ca, thal."""
    m = _model("heart_disease_prediction_pipeline.joblib")
    p = float(m.predict_proba(_frame(m, features))[0][1])
    return {"probability": round(p, 4), "prediction": int(p > 0.5), "model_version": HEART_VERSION}


def warm_up() -> None:
    for name in PINNED:
        try:
            _model(name)
        except ModelUnavailable as exc:
            log.warning("ncs model unavailable", extra={"fields": {"model": name, "reason": str(exc)}})
