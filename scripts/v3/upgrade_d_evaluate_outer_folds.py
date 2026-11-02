"""RescueNet V3 Upgrade D: frozen outer-fold-0 evaluation."""

from pathlib import Path
import argparse
import hashlib
import json

import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument(
    "--fold", type=int, required=True, choices=[1, 2, 3, 4]
)
args = parser.parse_args()
FOLD = args.fold

BASE = Path(f"results/eligible/v3/upgrade_d/pilot_fold{FOLD}")
PROTOCOL = BASE / "matched_budget_protocol.json"
OUTPUT = BASE / "matched_budget_results.csv"
SUMMARY = BASE / "matched_budget_evaluation_summary.json"

for path in (OUTPUT, SUMMARY):
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite: {path}")

protocol = json.loads(PROTOCOL.read_text())

assert protocol["status"] == "FROZEN_BEFORE_OUTCOME_EVALUATION"
assert protocol["outer_fold"] == FOLD
assert protocol["primary_threshold"] == 0.115
assert protocol["model_selection_on_outer_test"] is False

# Verify the exact frozen input files.
for name, expected_hash in protocol["input_sha256"].items():
    actual_hash = hashlib.sha256(
        (BASE / name).read_bytes()
    ).hexdigest()
    assert actual_hash == expected_hash, (
        f"Frozen input changed: {name}"
    )

lr = pd.read_csv(
    BASE / "lr_router_outer_test_scores_LOCKED.csv"
)
mlp = pd.read_csv(
    BASE / "mlp_router_outer_test_scores_LOCKED.csv"
)

assert lr.encounter_id.is_unique
assert mlp.encounter_id.is_unique

assert not any(
    c in lr.columns or c in mlp.columns
    for c in ("actual_30d", "target_30d", "is_false_negative")
)

scores = lr.merge(
    mlp[["encounter_id", "patient_nbr", "mlp_router_score"]],
    on="encounter_id",
    how="inner",
    suffixes=("", "_mlp"),
    validate="one_to_one",
)

assert len(scores) == len(lr) == len(mlp) > 0
assert (
    scores.patient_nbr == scores.patient_nbr_mlp
).all()

# Labels are read ONLY during this final evaluation stage.
labels = pd.read_csv(
    "data/processed/eligible/train.csv",
    usecols=["encounter_id", "patient_nbr", "target_30d"],
)

folds = pd.read_csv(
    "results/eligible/v3/upgrade_d/outer_fold_assignments.csv",
    usecols=["encounter_id", "outer_fold"],
)

labels = labels.merge(
    folds,
    on="encounter_id",
    validate="one_to_one",
)

outer_labels = labels.loc[
    labels.outer_fold == protocol["outer_fold"],
    ["encounter_id", "patient_nbr", "target_30d"],
]

evaluated = scores.merge(
    outer_labels,
    on="encounter_id",
    how="inner",
    suffixes=("", "_label"),
    validate="one_to_one",
)

assert len(evaluated) == len(scores)
assert (
    evaluated.patient_nbr == evaluated.patient_nbr_label
).all()

assert evaluated.encounter_id.is_unique
assert evaluated.target_30d.isin([0, 1]).all()

n = len(evaluated)
fn_total = int(evaluated.target_30d.sum())

assert n > 0
assert fn_total > 0

budgets = protocol["review_budgets"]
assert budgets == [0.05, 0.10, 0.15, 0.20, 0.25]

results = []

for budget in budgets:
    k = round(n * budget)
    random_expected = k * fn_total / n

    results.append({
        "outer_fold": FOLD,
        "budget": budget,
        "method": "random_expected",
        "routing_population": n,
        "false_negatives_total": fn_total,
        "review_count": k,
        "review_fraction": k / n,
        "fn_captured": random_expected,
        "fn_rescue_coverage": random_expected / fn_total,
    })

    for method, score_column in [
        ("logistic_regression_router", "lr_router_score"),
        ("mlp_router", "mlp_router_score"),
    ]:
        ranked = evaluated.sort_values(
            by=[score_column, "encounter_id"],
            ascending=[False, True],
            kind="mergesort",
        )

        selected = ranked.head(k)
        captured = int(selected.target_30d.sum())

        results.append({
            "outer_fold": FOLD,
            "budget": budget,
            "method": method,
            "routing_population": n,
            "false_negatives_total": fn_total,
            "review_count": k,
            "review_fraction": k / n,
            "fn_captured": captured,
            "fn_rescue_coverage": captured / fn_total,
        })

result_df = pd.DataFrame(results)

assert len(result_df) == 15
assert result_df.review_count.gt(0).all()
assert result_df.fn_rescue_coverage.between(0, 1).all()

summary = {
    "project": "RescueNet V3",
    "upgrade": "D",
    "outer_fold": FOLD,
    "evaluation_type": "single_outer_fold_pilot",
    "routing_population": n,
    "false_negatives_total": fn_total,
    "primary_threshold": protocol["primary_threshold"],
    "review_budgets": budgets,
    "comparators": protocol["models"],
    "input_checksums_verified": True,
    "outer_test_labels_accessed_for_evaluation": True,
    "model_selection_performed": False,
    "limitations": [
        "Single outer-fold pilot, not complete five-fold evaluation.",
        "No superiority claim from one fold.",
        "Historical threshold used as fixed reference.",
        "Historical test-set reuse limits confirmatory claims.",
    ],
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
result_df.to_csv(OUTPUT, index=False)
SUMMARY.write_text(json.dumps(summary, indent=2) + "\n")

print("=== UPGRADE D FROZEN OUTER-FOLD EVALUATION ===")
print("Outer fold:", FOLD)
print("Routing population:", n)
print("False negatives:", fn_total)

print("\nFALSE NEGATIVES CAPTURED")
print(
    result_df.pivot(
        index="budget",
        columns="method",
        values="fn_captured",
    ).to_string()
)

print("\nSaved:", OUTPUT)
print("Saved:", SUMMARY)
print("UPGRADE D OUTER-FOLD PILOT EVALUATION: COMPLETE")
