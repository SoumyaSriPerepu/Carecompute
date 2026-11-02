"""RescueNet V3 Upgrade D: outer-fold-0 primary/calibration pilot."""

from pathlib import Path
import argparse

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import GroupShuffleSplit

from primary_crossfit import build_models, FEATURE_EXCLUSIONS

parser = argparse.ArgumentParser()
parser.add_argument("--fold", type=int, required=True, choices=[1, 2, 3, 4])
args = parser.parse_args()
FOLD = args.fold

TRAIN = Path("data/processed/eligible/train.csv")
FOLDS = Path("results/eligible/v3/upgrade_d/outer_fold_assignments.csv")
OUT = Path(f"results/eligible/v3/upgrade_d/pilot_fold{FOLD}")

OUTPUTS = {
    "router": OUT / "router_development_predictions.csv",
    "test": OUT / "outer_test_predictions_LOCKED.csv",
}

for path in OUTPUTS.values():
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite: {path}")

df = pd.read_csv(TRAIN, low_memory=False)
folds = pd.read_csv(FOLDS)

assert df.encounter_id.is_unique
assert folds.encounter_id.is_unique

df = df.merge(
    folds[["encounter_id", "outer_fold"]],
    on="encounter_id",
    validate="one_to_one",
)

outer_dev = df[df.outer_fold != FOLD].copy()
outer_test = df[df.outer_fold == FOLD].copy()

s1 = GroupShuffleSplit(
    n_splits=1, train_size=0.60, random_state=42
)
fit_idx, rest_idx = next(
    s1.split(outer_dev, outer_dev.target_30d, outer_dev.patient_nbr)
)
primary_fit = outer_dev.iloc[fit_idx]
remaining = outer_dev.iloc[rest_idx]

s2 = GroupShuffleSplit(
    n_splits=1, train_size=0.50, random_state=43
)
cal_idx, router_idx = next(
    s2.split(remaining, remaining.target_30d, remaining.patient_nbr)
)
calibration = remaining.iloc[cal_idx]
router_dev = remaining.iloc[router_idx]

parts = [primary_fit, calibration, router_dev, outer_test]
for i in range(len(parts)):
    for j in range(i + 1, len(parts)):
        assert set(parts[i].patient_nbr).isdisjoint(
            set(parts[j].patient_nbr)
        )

features = [
    c for c in primary_fit.columns
    if c not in FEATURE_EXCLUSIONS + ["outer_fold"]
]

X_fit = primary_fit[features]
y_fit = primary_fit.target_30d.astype(int)

models = build_models(X_fit)

print(f"=== UPGRADE D PRIMARY PILOT: OUTER FOLD {FOLD} ===")
print("Primary fit:", len(primary_fit))
print("Calibration:", len(calibration))
print("Router development:", len(router_dev))
print("Outer test:", len(outer_test))

for name, model in models.items():
    print(f"Training {name}...", flush=True)
    model.fit(X_fit, y_fit)
    print(f"{name}: COMPLETE", flush=True)

print("Fitting isotonic calibrator...", flush=True)
cal_raw = models["gb"].predict_proba(calibration[features])[:, 1]

calibrator = IsotonicRegression(out_of_bounds="clip")
calibrator.fit(
    cal_raw,
    calibration.target_30d.astype(int),
)

def generate_predictions(part, include_labels):
    probabilities = {
        name: model.predict_proba(part[features])[:, 1]
        for name, model in models.items()
    }

    matrix = np.column_stack([
        probabilities["lr"],
        probabilities["rf"],
        probabilities["gb"],
    ])

    result = pd.DataFrame({
        "encounter_id": part.encounter_id.to_numpy(),
        "patient_nbr": part.patient_nbr.to_numpy(),
        "lr_raw_probability": probabilities["lr"],
        "rf_raw_probability": probabilities["rf"],
        "gb_raw_probability": probabilities["gb"],
        "calibrated_probability": calibrator.predict(
            probabilities["gb"]
        ),
        "model_disagreement_std": matrix.std(axis=1),
        "number_diagnoses": part.number_diagnoses.to_numpy(),
        "number_outpatient": part.number_outpatient.to_numpy(),
        "number_emergency": part.number_emergency.to_numpy(),
    })

    if include_labels:
        result["actual_30d"] = part.target_30d.to_numpy()

    for col in [
        "lr_raw_probability",
        "rf_raw_probability",
        "gb_raw_probability",
        "calibrated_probability",
        "model_disagreement_std",
    ]:
        assert np.isfinite(result[col]).all()

    return result

router_predictions = generate_predictions(
    router_dev, include_labels=True
)
test_predictions = generate_predictions(
    outer_test, include_labels=False
)

OUT.mkdir(parents=True, exist_ok=True)

router_predictions.to_csv(OUTPUTS["router"], index=False)
test_predictions.to_csv(OUTPUTS["test"], index=False)

print("\nRouter-development predictions:", len(router_predictions))
print("Outer-test predictions:", len(test_predictions))
print("Outer-test labels exported: NO")
print("Saved:", OUT)
print("UPGRADE D PRIMARY PILOT: COMPLETE")
