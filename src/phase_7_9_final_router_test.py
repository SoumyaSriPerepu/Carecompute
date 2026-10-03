import numpy as np
import pandas as pd
import joblib
from pathlib import Path

# ============================================================
# PHASE 7.9
# FROZEN RESCUE ROUTER — FINAL TEST EVALUATION
# ============================================================

PRED_FILE = Path(
    "results/eligible/test_predictions.csv"
)

DISAGREEMENT_FILE = Path(
    "results/eligible/model_disagreement_predictions.csv"
)

PROCESSED_TEST_FILE = Path(
    "data/processed/eligible/test.csv"
)

ROUTER_FILE = Path(
    "src/models/saved/eligible/router/fn_rescue_router.joblib"
)

OUTPUT_DIR = Path("results/eligible")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# LOCKED operating point
# Selected before final rescue evaluation
# ------------------------------------------------------------

PRIMARY_BUDGET = 0.15

# Also report sensitivity analysis, but DO NOT choose a new
# operating point based on final-test performance.
SENSITIVITY_BUDGETS = [
    0.05,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.40,
    0.50
]

RANDOM_SEED = 42
N_RANDOM_REPEATS = 5000

rng = np.random.default_rng(RANDOM_SEED)

print("=" * 80)
print("PHASE 7.9 — FROZEN RESCUE ROUTER FINAL TEST")
print("=" * 80)

# ============================================================
# 1. LOAD DATA
# ============================================================

pred = pd.read_csv(PRED_FILE)
disagreement = pd.read_csv(DISAGREEMENT_FILE)
clinical = pd.read_csv(PROCESSED_TEST_FILE)

router = joblib.load(ROUTER_FILE)

print("\nTest predictions:", pred.shape)
print("Disagreement data:", disagreement.shape)
print("Processed test data:", clinical.shape)

print("\nFrozen router:")
print(router)

# ============================================================
# 2. INTEGRITY CHECKS
# ============================================================

assert pred["encounter_id"].is_unique
assert disagreement["encounter_id"].is_unique
assert clinical["encounter_id"].is_unique

assert set(pred["encounter_id"]) == set(
    disagreement["encounter_id"]
), "Prediction/disagreement encounter IDs do not match."

assert set(pred["encounter_id"]) == set(
    clinical["encounter_id"]
), "Prediction/clinical encounter IDs do not match."

print("\nEncounter integrity checks: PASSED")

# ============================================================
# 3. MERGE TEST FEATURES
# ============================================================

disagreement_small = disagreement[
    [
        "encounter_id",
        "model_disagreement_std",
        "model_disagreement_range"
    ]
].copy()

clinical_small = clinical[
    [
        "encounter_id",
        "number_diagnoses",
        "number_outpatient",
        "number_emergency",
        "number_inpatient",
        "time_in_hospital",
        "age",
        "gender",
        "race"
    ]
].copy()

test = pred.merge(
    disagreement_small,
    on="encounter_id",
    how="left",
    validate="one_to_one"
)

test = test.merge(
    clinical_small,
    on="encounter_id",
    how="left",
    validate="one_to_one"
)

assert len(test) == len(pred)

print("Merged test shape:", test.shape)

# ============================================================
# 4. VERIFY PRIMARY TEST CONFUSION MATRIX
# ============================================================

test["case_type"] = np.select(
    [
        (test["actual_30d"] == 1)
        & (test["predicted_30d"] == 1),

        (test["actual_30d"] == 0)
        & (test["predicted_30d"] == 0),

        (test["actual_30d"] == 0)
        & (test["predicted_30d"] == 1),

        (test["actual_30d"] == 1)
        & (test["predicted_30d"] == 0),
    ],
    [
        "TP",
        "TN",
        "FP",
        "FN"
    ],
    default="Unknown"
)

case_counts = test["case_type"].value_counts()

print("\n" + "=" * 80)
print("PRIMARY TEST CONFUSION MATRIX CHECK")
print("=" * 80)

print(case_counts)

assert case_counts.get("FN", 0) == 557, (
    "Expected 557 test false negatives."
)

# ============================================================
# 5. SELECT LOW-RISK TEST PATIENTS
# ============================================================

low_risk = test[
    test["predicted_30d"] == 0
].copy()

low_risk["router_target"] = (
    low_risk["actual_30d"] == 1
).astype(int)

total_test_fn = int(
    low_risk["router_target"].sum()
)

print("\n" + "=" * 80)
print("LOW-RISK TEST POPULATION")
print("=" * 80)

print("Low-risk patients:", len(low_risk))
print("False negatives:", total_test_fn)
print(
    "FN prevalence:",
    f"{total_test_fn / len(low_risk):.4f}",
    f"({100 * total_test_fn / len(low_risk):.2f}%)"
)

# ============================================================
# 6. APPLY FROZEN RESCUE ROUTER
# ============================================================

router_features = list(
    router.feature_names_in_
)

print("\nFrozen router features:")
for feature in router_features:
    print(" -", feature)

missing = [
    f for f in router_features
    if f not in low_risk.columns
]

assert not missing, (
    f"Missing router features: {missing}"
)

X_router = low_risk[
    router_features
].copy()

# IMPORTANT:
# No fit() occurs here.
# This is the previously saved frozen pipeline.
low_risk["fn_router_probability"] = (
    router.predict_proba(X_router)[:, 1]
)

print("\nFrozen router successfully applied.")

print(
    "Router probability range:",
    low_risk["fn_router_probability"].min(),
    "to",
    low_risk["fn_router_probability"].max()
)

# ============================================================
# 7. DEFINE RANKING METHODS
# ============================================================

# Higher score = review first

low_risk["probability_score"] = (
    low_risk["calibrated_probability"]
)

low_risk["disagreement_score"] = (
    low_risk["model_disagreement_std"]
)

methods = {
    "Probability": "probability_score",
    "Disagreement": "disagreement_score",
    "Rescue Router": "fn_router_probability"
}

# ============================================================
# 8. EVALUATION FUNCTION
# ============================================================

def evaluate_ranking(data, score_col, budget):

    n_review = max(
        1,
        int(np.floor(len(data) * budget))
    )

    ranked = data.sort_values(
        score_col,
        ascending=False
    )

    reviewed = ranked.iloc[:n_review]

    fn_captured = int(
        reviewed["router_target"].sum()
    )

    fn_capture_rate = (
        fn_captured / total_test_fn
        if total_test_fn > 0
        else np.nan
    )

    review_precision = (
        fn_captured / n_review
    )

    overall_test_review_rate = (
        n_review / len(test)
    )

    return {
        "patients_reviewed": n_review,
        "overall_test_review_rate":
            overall_test_review_rate,
        "fn_captured": fn_captured,
        "fn_capture_rate":
            fn_capture_rate,
        "review_precision":
            review_precision
    }

# ============================================================
# 9. RANDOM BASELINE
# ============================================================

def random_baseline(data, budget):

    n_review = max(
        1,
        int(np.floor(len(data) * budget))
    )

    captures = np.empty(
        N_RANDOM_REPEATS,
        dtype=float
    )

    indices = np.arange(len(data))
    targets = data["router_target"].to_numpy()

    for i in range(N_RANDOM_REPEATS):

        selected = rng.choice(
            indices,
            size=n_review,
            replace=False
        )

        captures[i] = targets[selected].sum()

    mean_captured = captures.mean()

    return {
        "patients_reviewed": n_review,
        "overall_test_review_rate":
            n_review / len(test),

        "fn_captured":
            mean_captured,

        "fn_capture_rate":
            mean_captured / total_test_fn,

        "review_precision":
            mean_captured / n_review,

        "capture_ci_lower":
            np.percentile(captures, 2.5)
            / total_test_fn,

        "capture_ci_upper":
            np.percentile(captures, 97.5)
            / total_test_fn
    }

# ============================================================
# 10. PRIMARY LOCKED 15% TEST RESULT
# ============================================================

print("\n" + "=" * 80)
print("PRIMARY LOCKED TEST RESULT — 15% LOW-RISK REVIEW BUDGET")
print("=" * 80)

primary_rows = []

for method, score_col in methods.items():

    result = evaluate_ranking(
        low_risk,
        score_col,
        PRIMARY_BUDGET
    )

    result["method"] = method
    result["budget"] = PRIMARY_BUDGET

    primary_rows.append(result)

random_result = random_baseline(
    low_risk,
    PRIMARY_BUDGET
)

random_result["method"] = "Random"
random_result["budget"] = PRIMARY_BUDGET

primary_rows.append(random_result)

primary_df = pd.DataFrame(primary_rows)

primary_df = primary_df[
    [
        "method",
        "budget",
        "patients_reviewed",
        "overall_test_review_rate",
        "fn_captured",
        "fn_capture_rate",
        "review_precision"
    ]
]

print(primary_df.to_string(index=False))

# ============================================================
# 11. RESCUE ROUTER LIFT OVER RANDOM
# ============================================================

rescue_row = primary_df[
    primary_df["method"] == "Rescue Router"
].iloc[0]

random_row = primary_df[
    primary_df["method"] == "Random"
].iloc[0]

lift_over_random = (
    rescue_row["fn_capture_rate"]
    / random_row["fn_capture_rate"]
)

absolute_gain = (
    rescue_row["fn_capture_rate"]
    - random_row["fn_capture_rate"]
)

print("\n" + "=" * 80)
print("PRIMARY RESCUE ROUTER EFFECT")
print("=" * 80)

print(
    "FN capture:",
    f"{rescue_row['fn_capture_rate']:.4f}",
    f"({rescue_row['fn_capture_rate'] * 100:.2f}%)"
)

print(
    "Random FN capture:",
    f"{random_row['fn_capture_rate']:.4f}",
    f"({random_row['fn_capture_rate'] * 100:.2f}%)"
)

print(
    "Absolute gain over random:",
    f"{absolute_gain:.4f}",
    f"({absolute_gain * 100:.2f} percentage points)"
)

print(
    "Lift over random:",
    f"{lift_over_random:.3f}x"
)

# ============================================================
# 12. SENSITIVITY ANALYSIS
# ============================================================

print("\n" + "=" * 80)
print("SENSITIVITY ANALYSIS")
print("=" * 80)

sensitivity_rows = []

for budget in SENSITIVITY_BUDGETS:

    for method, score_col in methods.items():

        result = evaluate_ranking(
            low_risk,
            score_col,
            budget
        )

        result["method"] = method
        result["budget"] = budget

        sensitivity_rows.append(result)

    random_result = random_baseline(
        low_risk,
        budget
    )

    random_result["method"] = "Random"
    random_result["budget"] = budget

    sensitivity_rows.append(
        random_result
    )

sensitivity_df = pd.DataFrame(
    sensitivity_rows
)

print(
    sensitivity_df[
        [
            "budget",
            "method",
            "patients_reviewed",
            "fn_captured",
            "fn_capture_rate",
            "review_precision"
        ]
    ].to_string(index=False)
)

# ============================================================
# 13. TEST SUBGROUP RESULTS AT LOCKED 15%
# ============================================================

n_primary_review = int(
    np.floor(
        len(low_risk)
        * PRIMARY_BUDGET
    )
)

ranked_rescue = low_risk.sort_values(
    "fn_router_probability",
    ascending=False
).copy()

ranked_rescue["selected_for_review"] = 0

ranked_rescue.iloc[
    :n_primary_review,
    ranked_rescue.columns.get_loc(
        "selected_for_review"
    )
] = 1

fn_test = ranked_rescue[
    ranked_rescue["router_target"] == 1
].copy()

subgroup_rows = []

for feature in [
    "gender",
    "race",
    "age"
]:

    for group, subset in fn_test.groupby(
        feature,
        dropna=False
    ):

        total_group_fn = len(subset)

        rescued_group_fn = int(
            subset[
                "selected_for_review"
            ].sum()
        )

        subgroup_rows.append({
            "feature": feature,
            "group": group,
            "total_false_negatives":
                total_group_fn,
            "rescued_false_negatives":
                rescued_group_fn,
            "fn_rescue_rate":
                rescued_group_fn
                / total_group_fn
        })

subgroup_df = pd.DataFrame(
    subgroup_rows
)

print("\n" + "=" * 80)
print("TEST SUBGROUP FN RESCUE — LOCKED 15%")
print("=" * 80)

print(
    subgroup_df.to_string(
        index=False
    )
)

# ============================================================
# 14. SAVE EVERYTHING
# ============================================================

primary_file = (
    OUTPUT_DIR
    / "final_test_router_primary_15pct.csv"
)

sensitivity_file = (
    OUTPUT_DIR
    / "final_test_router_sensitivity.csv"
)

patient_file = (
    OUTPUT_DIR
    / "final_test_router_predictions.csv"
)

subgroup_file = (
    OUTPUT_DIR
    / "final_test_router_subgroups.csv"
)

primary_df.to_csv(
    primary_file,
    index=False
)

sensitivity_df.to_csv(
    sensitivity_file,
    index=False
)

ranked_rescue.to_csv(
    patient_file,
    index=False
)

subgroup_df.to_csv(
    subgroup_file,
    index=False
)

print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print(primary_file)
print(sensitivity_file)
print(patient_file)
print(subgroup_file)

print("\n" + "=" * 80)
print("PHASE 7.9 COMPLETE — FROZEN TEST EVALUATION")
print("=" * 80)