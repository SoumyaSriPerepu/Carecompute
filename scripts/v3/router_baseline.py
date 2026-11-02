"""RescueNet V3 exploratory logistic-regression router baseline."""

from pathlib import Path
import json

import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

BASE = Path("results/eligible/v3")
TRAIN = BASE / "router_dev_train.csv"
VAL = BASE / "router_dev_validation.csv"
OUTPUT = BASE / "router_lr_baseline.json"

FEATURES = [
    "calibrated_probability",
    "model_disagreement_std",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
]

BUDGETS = [0.05, 0.10, 0.15, 0.20, 0.25]

train = pd.read_csv(TRAIN)
val = pd.read_csv(VAL)

assert set(train.patient_nbr).isdisjoint(set(val.patient_nbr))
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

model.fit(
    train[FEATURES],
    train["actual_30d"].astype(int),
)

scores = model.predict_proba(val[FEATURES])[:, 1]
labels = val["actual_30d"].to_numpy(dtype=int)

# Highest score first; ascending encounter ID breaks ties.
order = np.lexsort((val["encounter_id"].to_numpy(), -scores))

total_fn = int(labels.sum())
results = []

print("=== V3 EXPLORATORY LR ROUTER BASELINE ===")
print("Validation encounters:", len(val))
print("False negatives:", total_fn)

for budget in BUDGETS:
    k = int(np.floor(len(val) * budget))
    selected = order[:k]
    captured = int(labels[selected].sum())

    result = {
        "budget": budget,
        "review_slots": k,
        "fn_captured": captured,
        "fn_coverage": captured / total_fn,
        "review_precision": captured / k,
    }
    results.append(result)

    print(
        f"{budget:.0%}: "
        f"reviews={k}, "
        f"FN_captured={captured}, "
        f"FN_coverage={result['fn_coverage']:.4f}, "
        f"precision={result['review_precision']:.4f}"
    )

if OUTPUT.exists():
    raise FileExistsError(f"Refusing to overwrite: {OUTPUT}")

OUTPUT.write_text(json.dumps({
    "status": "EXPLORATORY_NOT_INDEPENDENT",
    "train_encounters": len(train),
    "validation_encounters": len(val),
    "validation_false_negatives": total_fn,
    "features": FEATURES,
    "results": results,
}, indent=2))

print("Saved:", OUTPUT)
print("EXPLORATORY BASELINE: PASS")
