"""Exploratory V3 budget-preserving safety-priority evaluation."""

from pathlib import Path
import json
import numpy as np
import pandas as pd

BASE = Path("results/eligible/v3")
OUTPUT = BASE / "router_safety_priority_exploratory.json"

BUDGETS = [0.05, 0.10, 0.15, 0.20, 0.25]
PRIMARY_THRESHOLD = 0.115

train = pd.read_csv(BASE / "router_dev_train.csv")
val = pd.read_csv(BASE / "router_dev_validation.csv")
scores = pd.read_csv(BASE / "router_lr_validation_scores.csv")

assert train.encounter_id.is_unique
assert val.encounter_id.is_unique
assert scores.encounter_id.is_unique

assert set(val.encounter_id) == set(scores.encounter_id)

df = val.merge(
    scores[["encounter_id", "lr_router_score"]],
    on="encounter_id",
    how="left",
    validate="one_to_one",
)

assert df.lr_router_score.notna().all()
assert set(train.patient_nbr).isdisjoint(set(df.patient_nbr))

required = [
    "model_disagreement_std",
    "calibrated_probability",
    "actual_30d",
]
assert train[required].notna().all().all()
assert df[required].notna().all().all()

uncertainty_cutoff = float(
    train.model_disagreement_std.quantile(0.75)
)

distance_cutoff = float(
    (PRIMARY_THRESHOLD - train.calibrated_probability).quantile(0.25)
)

uncertainty = df.model_disagreement_std.to_numpy()
distance = PRIMARY_THRESHOLD - df.calibrated_probability.to_numpy()

safety_flag = (
    (uncertainty >= uncertainty_cutoff)
    | (distance <= distance_cutoff)
)

score = df.lr_router_score.to_numpy()
encounter_id = df.encounter_id.to_numpy()
labels = df.actual_30d.to_numpy(dtype=int)

assert set(np.unique(labels)).issubset({0, 1})

baseline_order = np.lexsort((encounter_id, -score))
safety_order = np.lexsort((
    encounter_id,
    -score,
    -safety_flag.astype(int),
))

results = []

print("=== V3 SAFETY-PRIORITY EVALUATION ===")
print("Validation encounters:", len(df))
print("Safety flagged:", int(safety_flag.sum()))
print("Training uncertainty cutoff:", uncertainty_cutoff)
print("Training distance cutoff:", distance_cutoff)

for budget in BUDGETS:
    k = int(np.floor(len(df) * budget))

    baseline_selected = baseline_order[:k]
    safety_selected = safety_order[:k]

    baseline_fn = int(labels[baseline_selected].sum())
    safety_fn = int(labels[safety_selected].sum())

    assert len(baseline_selected) == k
    assert len(safety_selected) == k
    assert len(set(safety_selected)) == k

    result = {
        "budget": budget,
        "review_count": k,
        "baseline_fn_captured": baseline_fn,
        "safety_fn_captured": safety_fn,
        "fn_difference": safety_fn - baseline_fn,
        "safety_flagged_selected": int(
            safety_flag[safety_selected].sum()
        ),
    }

    results.append(result)

    print(
        f"{budget:.0%}: reviews={k}, "
        f"LR_FN={baseline_fn}, "
        f"Safety_FN={safety_fn}, "
        f"Difference={safety_fn-baseline_fn:+d}"
    )

expected_baseline = [46, 88, 143, 192, 245]
assert [
    r["baseline_fn_captured"] for r in results
] == expected_baseline, "Baseline reproduction failed"

assert not OUTPUT.exists(), f"Refusing to overwrite {OUTPUT}"

OUTPUT.write_text(json.dumps({
    "status": "EXPLORATORY_NOT_CLINICALLY_VALIDATED",
    "policy": "safety_flag_first_then_lr_score",
    "thresholds_source": "router_dev_train_only",
    "uncertainty_cutoff": uncertainty_cutoff,
    "distance_cutoff": distance_cutoff,
    "validation_safety_flag_count": int(safety_flag.sum()),
    "results": results,
}, indent=2))

print("Saved:", OUTPUT)
print("SAFETY PRIORITY BUDGET AUDIT: PASS")
