"""Export reproducible V3 LR router scores for subgroup auditing."""

from pathlib import Path
import json

import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

BASE = Path("results/eligible/v3")
OUTPUT = BASE / "router_lr_validation_scores.csv"
BASELINE = BASE / "router_lr_baseline.json"

FEATURES = [
    "calibrated_probability",
    "model_disagreement_std",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
]

train = pd.read_csv(BASE / "router_dev_train.csv")
val = pd.read_csv(BASE / "router_dev_validation.csv")

assert set(train.patient_nbr).isdisjoint(set(val.patient_nbr))
assert val.encounter_id.is_unique
assert train[FEATURES].notna().all().all()
assert val[FEATURES].notna().all().all()

model = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
    ("classifier", LogisticRegression(
        class_weight="balanced",
        max_iter=2000,
        random_state=42,
    )),
])

model.fit(train[FEATURES], train.actual_30d.astype(int))

scores = model.predict_proba(val[FEATURES])[:, 1]

assert np.isfinite(scores).all()

order = np.lexsort(
    (val.encounter_id.to_numpy(), -scores)
)

baseline = json.loads(BASELINE.read_text())

labels = val.actual_30d.to_numpy(dtype=int)

print("=== LR SCORE REPRODUCIBILITY AUDIT ===")

for result in baseline["results"]:
    budget = result["budget"]
    k = int(np.floor(len(val) * budget))
    captured = int(labels[order[:k]].sum())

    assert k == result["review_slots"]
    assert captured == result["fn_captured"]

    print(
        f"{budget:.0%}: "
        f"captured={captured} — MATCH"
    )

if OUTPUT.exists():
    raise FileExistsError(f"Refusing to overwrite: {OUTPUT}")

export = val[[
    "encounter_id",
    "patient_nbr",
    "actual_30d",
]].copy()

export["lr_router_score"] = scores

export.to_csv(OUTPUT, index=False)

print("\nSaved:", OUTPUT)
print("LR SCORE EXPORT: PASS")
