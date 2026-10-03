import numpy as np
import pandas as pd
from pathlib import Path
from statsmodels.stats.proportion import proportion_confint

# ============================================================
# PHASE 8.2.1
# END-TO-END FAIRNESS / RESIDUAL MISS BURDEN
#
# IMPORTANT:
# "Post-review" results are a WORKFLOW SIMULATION.
# They assume every routed false negative would be correctly
# identified by human review.
# ============================================================

TEST_PRED_FILE = Path(
    "results/eligible/test_predictions.csv"
)

ROUTER_FILE = Path(
    "results/eligible/final_test_router_predictions.csv"
)

PROCESSED_TEST_FILE = Path(
    "data/processed/eligible/test.csv"
)

OUTPUT_DIR = Path("results/eligible")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LOCKED_BUDGET = 0.15

print("=" * 80)
print("PHASE 8.2.1 — END-TO-END FAIRNESS AUDIT")
print("=" * 80)

# ============================================================
# 1. LOAD DATA
# ============================================================

pred = pd.read_csv(TEST_PRED_FILE)
router = pd.read_csv(ROUTER_FILE)
clinical = pd.read_csv(PROCESSED_TEST_FILE)

print("\nPrimary test predictions:", pred.shape)
print("Router predictions:", router.shape)
print("Processed test data:", clinical.shape)

# ============================================================
# 2. VALIDATE REQUIRED COLUMNS
# ============================================================

pred_required = [
    "encounter_id",
    "actual_30d",
    "predicted_30d"
]

router_required = [
    "encounter_id",
    "fn_router_probability"
]

clinical_required = [
    "encounter_id",
    "gender",
    "race",
    "age"
]

for name, frame, required in [
    ("predictions", pred, pred_required),
    ("router", router, router_required),
    ("clinical", clinical, clinical_required)
]:
    missing = [
        c for c in required
        if c not in frame.columns
    ]

    assert not missing, (
        f"{name} missing columns: {missing}"
    )

# ============================================================
# 3. ID INTEGRITY
# ============================================================

assert pred["encounter_id"].is_unique
assert clinical["encounter_id"].is_unique
assert router["encounter_id"].is_unique

assert set(pred["encounter_id"]) == set(
    clinical["encounter_id"]
), "Prediction/clinical encounter IDs do not match."

print("\nEncounter integrity: PASSED")

# ============================================================
# 4. BUILD COMPLETE TEST DATASET
# ============================================================

df = pred.merge(
    clinical[
        [
            "encounter_id",
            "gender",
            "race",
            "age"
        ]
    ],
    on="encounter_id",
    how="left",
    validate="one_to_one"
)

print("Merged full test shape:", df.shape)

# Primary confusion-matrix categories
conditions = [
    (df["actual_30d"] == 0)
    & (df["predicted_30d"] == 0),

    (df["actual_30d"] == 0)
    & (df["predicted_30d"] == 1),

    (df["actual_30d"] == 1)
    & (df["predicted_30d"] == 0),

    (df["actual_30d"] == 1)
    & (df["predicted_30d"] == 1)
]

labels = [
    "TN",
    "FP",
    "FN",
    "TP"
]

df["case_type"] = np.select(
    conditions,
    labels,
    default="ERROR"
)

print("\n" + "=" * 80)
print("PRIMARY MODEL CONFUSION MATRIX")
print("=" * 80)

print(
    df["case_type"]
    .value_counts()
    .reindex(labels)
)

assert (df["case_type"] != "ERROR").all()

# Expected frozen Phase 7.9 counts
assert int((df["case_type"] == "TN").sum()) == 7301
assert int((df["case_type"] == "FP").sum()) == 6005
assert int((df["case_type"] == "FN").sum()) == 557
assert int((df["case_type"] == "TP").sum()) == 1179

# ============================================================
# 5. RECONSTRUCT LOCKED RESCUE SELECTION
# ============================================================

low_risk_router = router.copy()

n_low_risk = len(low_risk_router)

n_review = int(
    np.floor(
        n_low_risk * LOCKED_BUDGET
    )
)

ranked_router = low_risk_router.sort_values(
    [
        "fn_router_probability",
        "encounter_id"
    ],
    ascending=[
        False,
        True
    ],
    kind="mergesort"
).copy()

ranked_router["selected_for_review"] = 0

ranked_router.iloc[
    :n_review,
    ranked_router.columns.get_loc(
        "selected_for_review"
    )
] = 1

selection = ranked_router[
    [
        "encounter_id",
        "selected_for_review"
    ]
]

df = df.merge(
    selection,
    on="encounter_id",
    how="left",
    validate="one_to_one"
)

# High-risk patients were not part of rescue routing.
df["selected_for_review"] = (
    df["selected_for_review"]
    .fillna(0)
    .astype(int)
)

rescued_mask = (
    (df["case_type"] == "FN")
    & (df["selected_for_review"] == 1)
)

df["rescued_fn"] = (
    rescued_mask.astype(int)
)

rescued_total = int(
    df["rescued_fn"].sum()
)

print("\n" + "=" * 80)
print("RESCUE LAYER")
print("=" * 80)

print("Low-risk patients:", n_low_risk)
print("Patients reviewed:", n_review)
print("Primary false negatives:", 557)
print("Rescued false negatives:", rescued_total)

assert rescued_total == 110

# ============================================================
# 6. SIMULATED POST-REVIEW ERROR
#
# Assumption:
# Every routed FN is successfully identified by human review.
#
# Therefore:
# residual FN = original FN - rescued FN
# ============================================================

df["residual_fn"] = (
    (
        df["case_type"] == "FN"
    ).astype(int)
    - df["rescued_fn"]
)

assert (
    df["residual_fn"] >= 0
).all()

print(
    "Residual false negatives:",
    int(df["residual_fn"].sum())
)

print(
    "FN reduction:",
    f"{100 * rescued_total / 557:.2f}%"
)

# ============================================================
# 7. WILSON CI
# ============================================================

def wilson_ci(successes, total):

    if total == 0:
        return np.nan, np.nan

    low, high = proportion_confint(
        count=successes,
        nobs=total,
        alpha=0.05,
        method="wilson"
    )

    return low, high


# ============================================================
# 8. SUBGROUP END-TO-END METRICS
#
# For each subgroup:
#
# positives = TP + FN
#
# primary FNR =
#     FN / (TP + FN)
#
# residual miss rate =
#     (FN - rescued FN) / (TP + FN)
#
# rescue rate conditional on FN =
#     rescued FN / FN
# ============================================================

features = [
    "gender",
    "race",
    "age"
]

rows = []

for feature in features:

    temp = df.copy()

    temp[feature] = (
        temp[feature]
        .fillna("Missing")
        .astype(str)
    )

    for group, subset in temp.groupby(feature):

        positives = subset[
            subset["actual_30d"] == 1
        ]

        n_positive = len(positives)

        if n_positive == 0:
            continue

        tp = int(
            (
                positives["case_type"]
                == "TP"
            ).sum()
        )

        fn = int(
            (
                positives["case_type"]
                == "FN"
            ).sum()
        )

        rescued = int(
            positives[
                "rescued_fn"
            ].sum()
        )

        residual_fn = (
            fn - rescued
        )

        primary_fnr = (
            fn / n_positive
        )

        residual_miss_rate = (
            residual_fn / n_positive
        )

        if fn > 0:
            conditional_rescue_rate = (
                rescued / fn
            )
        else:
            conditional_rescue_rate = np.nan

        primary_low, primary_high = (
            wilson_ci(
                fn,
                n_positive
            )
        )

        residual_low, residual_high = (
            wilson_ci(
                residual_fn,
                n_positive
            )
        )

        rows.append({
            "feature": feature,
            "group": group,

            "actual_positive_patients":
                n_positive,

            "true_positives":
                tp,

            "primary_false_negatives":
                fn,

            "rescued_false_negatives":
                rescued,

            "residual_false_negatives":
                residual_fn,

            "primary_fnr":
                primary_fnr,

            "primary_fnr_ci_lower":
                primary_low,

            "primary_fnr_ci_upper":
                primary_high,

            "conditional_fn_rescue_rate":
                conditional_rescue_rate,

            "simulated_residual_miss_rate":
                residual_miss_rate,

            "residual_ci_lower":
                residual_low,

            "residual_ci_upper":
                residual_high,

            "absolute_fnr_reduction":
                primary_fnr
                - residual_miss_rate,

            "relative_fnr_reduction":
                (
                    (
                        primary_fnr
                        - residual_miss_rate
                    )
                    / primary_fnr
                )
                if primary_fnr > 0
                else np.nan
        })


results = pd.DataFrame(rows)

# ============================================================
# 9. PRINT SUBGROUP TABLES
# ============================================================

print("\n" + "=" * 80)
print("END-TO-END SUBGROUP RESULTS")
print("=" * 80)

for feature in features:

    print("\n" + "-" * 80)
    print(feature.upper())
    print("-" * 80)

    display = results[
        results["feature"] == feature
    ].copy()

    percent_cols = [
        "primary_fnr",
        "primary_fnr_ci_lower",
        "primary_fnr_ci_upper",
        "conditional_fn_rescue_rate",
        "simulated_residual_miss_rate",
        "residual_ci_lower",
        "residual_ci_upper",
        "absolute_fnr_reduction",
        "relative_fnr_reduction"
    ]

    for col in percent_cols:
        display[col] = (
            display[col] * 100
        )

    print(
        display.to_string(
            index=False
        )
    )

# ============================================================
# 10. DISPARITY GAP ANALYSIS
#
# Use groups with >=20 actual-positive patients
# to avoid making max/min summaries from tiny groups.
# ============================================================

print("\n" + "=" * 80)
print("DISPARITY GAP ANALYSIS")
print("=" * 80)

gap_rows = []

for feature in features:

    subset = results[
        (
            results["feature"] == feature
        )
        & (
            results[
                "actual_positive_patients"
            ] >= 20
        )
    ].copy()

    if len(subset) < 2:
        continue

    primary_high = subset.loc[
        subset["primary_fnr"].idxmax()
    ]

    primary_low = subset.loc[
        subset["primary_fnr"].idxmin()
    ]

    residual_high = subset.loc[
        subset[
            "simulated_residual_miss_rate"
        ].idxmax()
    ]

    residual_low = subset.loc[
        subset[
            "simulated_residual_miss_rate"
        ].idxmin()
    ]

    primary_gap = (
        primary_high["primary_fnr"]
        - primary_low["primary_fnr"]
    )

    residual_gap = (
        residual_high[
            "simulated_residual_miss_rate"
        ]
        - residual_low[
            "simulated_residual_miss_rate"
        ]
    )

    gap_rows.append({
        "feature": feature,

        "primary_high_group":
            primary_high["group"],

        "primary_high_fnr":
            primary_high["primary_fnr"],

        "primary_low_group":
            primary_low["group"],

        "primary_low_fnr":
            primary_low["primary_fnr"],

        "primary_fnr_gap":
            primary_gap,

        "residual_high_group":
            residual_high["group"],

        "residual_high_rate":
            residual_high[
                "simulated_residual_miss_rate"
            ],

        "residual_low_group":
            residual_low["group"],

        "residual_low_rate":
            residual_low[
                "simulated_residual_miss_rate"
            ],

        "residual_gap":
            residual_gap,

        "gap_change":
            residual_gap
            - primary_gap
    })


gap_df = pd.DataFrame(
    gap_rows
)

gap_display = gap_df.copy()

percentage_columns = [
    "primary_high_fnr",
    "primary_low_fnr",
    "primary_fnr_gap",
    "residual_high_rate",
    "residual_low_rate",
    "residual_gap",
    "gap_change"
]

for col in percentage_columns:
    gap_display[col] = (
        gap_display[col] * 100
    )

print(
    gap_display.to_string(
        index=False
    )
)

# ============================================================
# 11. AFRICAN AMERICAN VS CAUCASIAN SPECIFIC SUMMARY
# ============================================================

print("\n" + "=" * 80)
print("AFRICAN AMERICAN VS CAUCASIAN — END-TO-END")
print("=" * 80)

race_results = results[
    results["feature"] == "race"
].set_index("group")

for group in [
    "AfricanAmerican",
    "Caucasian"
]:

    if group not in race_results.index:
        continue

    r = race_results.loc[group]

    print(f"\n{group}")

    print(
        "Actual positives:",
        int(
            r["actual_positive_patients"]
        )
    )

    print(
        "Primary FNs:",
        int(
            r["primary_false_negatives"]
        )
    )

    print(
        "Rescued FNs:",
        int(
            r["rescued_false_negatives"]
        )
    )

    print(
        "Residual FNs:",
        int(
            r["residual_false_negatives"]
        )
    )

    print(
        "Primary FNR:",
        f"{r['primary_fnr'] * 100:.2f}%"
    )

    print(
        "Conditional rescue:",
        f"{r['conditional_fn_rescue_rate'] * 100:.2f}%"
    )

    print(
        "Simulated residual miss rate:",
        f"{r['simulated_residual_miss_rate'] * 100:.2f}%"
    )

if (
    "AfricanAmerican"
    in race_results.index
    and "Caucasian"
    in race_results.index
):

    aa = race_results.loc[
        "AfricanAmerican"
    ]

    cauc = race_results.loc[
        "Caucasian"
    ]

    primary_gap = (
        aa["primary_fnr"]
        - cauc["primary_fnr"]
    )

    residual_gap = (
        aa[
            "simulated_residual_miss_rate"
        ]
        - cauc[
            "simulated_residual_miss_rate"
        ]
    )

    print(
        "\nAA - Caucasian primary FNR gap:",
        f"{primary_gap * 100:.2f}",
        "percentage points"
    )

    print(
        "AA - Caucasian simulated residual gap:",
        f"{residual_gap * 100:.2f}",
        "percentage points"
    )

    print(
        "Gap change:",
        f"{(residual_gap - primary_gap) * 100:.2f}",
        "percentage points"
    )

# ============================================================
# 12. OVERALL SYSTEM EFFECT
# ============================================================

print("\n" + "=" * 80)
print("OVERALL WORKFLOW SIMULATION")
print("=" * 80)

positive_total = int(
    (df["actual_30d"] == 1).sum()
)

primary_fn_total = int(
    (df["case_type"] == "FN").sum()
)

residual_fn_total = int(
    df["residual_fn"].sum()
)

primary_fnr = (
    primary_fn_total
    / positive_total
)

residual_rate = (
    residual_fn_total
    / positive_total
)

print(
    "Actual-positive patients:",
    positive_total
)

print(
    "Primary false negatives:",
    primary_fn_total
)

print(
    "Primary FNR:",
    f"{primary_fnr * 100:.2f}%"
)

print(
    "Rescued FNs under simulation:",
    rescued_total
)

print(
    "Residual FNs:",
    residual_fn_total
)

print(
    "Simulated residual miss rate:",
    f"{residual_rate * 100:.2f}%"
)

print(
    "Absolute reduction:",
    f"{(primary_fnr - residual_rate) * 100:.2f}",
    "percentage points"
)

print(
    "Relative reduction:",
    f"{100 * (primary_fnr - residual_rate) / primary_fnr:.2f}%"
)

print(
    "\nIMPORTANT:"
)

print(
    "Post-review values are simulated under the assumption "
    "that every routed FN is successfully identified during review."
)

# ============================================================
# 13. SAVE
# ============================================================

results_file = (
    OUTPUT_DIR
    / "final_test_end_to_end_fairness.csv"
)

gap_file = (
    OUTPUT_DIR
    / "final_test_end_to_end_disparity_gaps.csv"
)

patient_file = (
    OUTPUT_DIR
    / "final_test_end_to_end_patient_predictions.csv"
)

results.to_csv(
    results_file,
    index=False
)

gap_df.to_csv(
    gap_file,
    index=False
)

df.to_csv(
    patient_file,
    index=False
)

print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print(results_file)
print(gap_file)
print(patient_file)

print("\n" + "=" * 80)
print("PHASE 8.2.1 COMPLETE")
print("=" * 80)