from pathlib import Path
import pandas as pd
import numpy as np


print("=" * 80)
print("PHASE 8.3.5 — FULL-TEST END-TO-END FAIRNESS")
print("=" * 80)


# ============================================================
# FILES
# ============================================================

TEST_DATA_FILE = Path(
    "data/processed/eligible/test.csv"
)

TEST_PREDICTIONS_FILE = Path(
    "results/eligible/test_predictions.csv"
)

ROUTER_FILE = Path(
    "results/eligible/final_test_router_predictions.csv"
)

OUTPUT_FILE = Path(
    "results/eligible/final_test_end_to_end_fairness.csv"
)


# ============================================================
# LOAD
# ============================================================

test_data = pd.read_csv(TEST_DATA_FILE)
pred = pd.read_csv(TEST_PREDICTIONS_FILE)
router = pd.read_csv(ROUTER_FILE)

print("\nProcessed test:", test_data.shape)
print("Predictions:", pred.shape)
print("Router low-risk population:", router.shape)


# ============================================================
# INTEGRITY CHECK
# ============================================================

assert test_data["encounter_id"].is_unique
assert pred["encounter_id"].is_unique
assert router["encounter_id"].is_unique

assert len(test_data) == len(pred)

assert set(test_data["encounter_id"]) == set(pred["encounter_id"])

print("\nEncounter integrity: PASSED")


# ============================================================
# MERGE FULL TEST POPULATION
# ============================================================

demographic_columns = [
    "encounter_id",
    "gender",
    "race",
    "age"
]

full_test = pred.merge(
    test_data[demographic_columns],
    on="encounter_id",
    how="left",
    validate="one_to_one"
)

assert len(full_test) == len(pred)

print("\nMerged full test:", full_test.shape)


# ============================================================
# RECONSTRUCT CASE TYPE
# ============================================================

conditions = [
    (
        (full_test["actual_30d"] == 0)
        &
        (full_test["predicted_30d"] == 0)
    ),
    (
        (full_test["actual_30d"] == 0)
        &
        (full_test["predicted_30d"] == 1)
    ),
    (
        (full_test["actual_30d"] == 1)
        &
        (full_test["predicted_30d"] == 0)
    ),
    (
        (full_test["actual_30d"] == 1)
        &
        (full_test["predicted_30d"] == 1)
    )
]

labels = [
    "TN",
    "FP",
    "FN",
    "TP"
]

full_test["case_type"] = np.select(
    conditions,
    labels,
    default="ERROR"
)

print("\nFull-test confusion matrix:")
print(full_test["case_type"].value_counts())


# ============================================================
# VERIFY AGAINST LOCKED TEST RESULT
# ============================================================

counts = full_test["case_type"].value_counts()

assert counts.get("TN", 0) == 7301
assert counts.get("FP", 0) == 6005
assert counts.get("FN", 0) == 557
assert counts.get("TP", 0) == 1179

print("\nLocked confusion matrix reproduction: PASSED")


# ============================================================
# ADD RESCUE INFORMATION
# ============================================================

rescue_lookup = router[
    [
        "encounter_id",
        "selected_for_review"
    ]
].copy()

full_test = full_test.merge(
    rescue_lookup,
    on="encounter_id",
    how="left",
    validate="one_to_one"
)

# High-risk patients were never candidates for secondary review.
full_test["selected_for_review"] = (
    full_test["selected_for_review"]
    .fillna(0)
    .astype(int)
)

full_test["rescued_fn"] = (
    (full_test["case_type"] == "FN")
    &
    (full_test["selected_for_review"] == 1)
).astype(int)


# ============================================================
# VERIFY RESCUE COUNT
# ============================================================

assert full_test["rescued_fn"].sum() == 110

print(
    "Rescued FN reproduction:",
    full_test["rescued_fn"].sum(),
    "— PASSED"
)


# ============================================================
# OVERALL CHECK
# ============================================================

positive = full_test[
    full_test["actual_30d"] == 1
]

overall_fn = (
    positive["case_type"] == "FN"
).sum()

overall_rescued = (
    positive["rescued_fn"]
).sum()

overall_primary_fnr = (
    overall_fn / len(positive)
)

overall_residual_fnr = (
    (overall_fn - overall_rescued)
    / len(positive)
)

print("\n" + "=" * 80)
print("OVERALL CHECK")
print("=" * 80)

print("Actual positives:", len(positive))
print("FN:", overall_fn)
print("Rescued FN:", overall_rescued)

print(
    f"Primary FNR: "
    f"{overall_primary_fnr * 100:.2f}%"
)

print(
    f"Residual FNR: "
    f"{overall_residual_fnr * 100:.2f}%"
)


# ============================================================
# SUBGROUP ANALYSIS
# ============================================================

rows = []

for feature in [
    "gender",
    "race",
    "age"
]:

    analysis = positive.copy()

    analysis[feature] = (
        analysis[feature]
        .fillna("Missing")
        .astype(str)
    )

    for group, group_df in analysis.groupby(feature):

        n_positive = len(group_df)

        tp = int(
            (group_df["case_type"] == "TP").sum()
        )

        fn = int(
            (group_df["case_type"] == "FN").sum()
        )

        rescued = int(
            group_df["rescued_fn"].sum()
        )

        residual_fn = (
            fn - rescued
        )

        primary_fnr = (
            fn / n_positive
            if n_positive > 0
            else np.nan
        )

        residual_fnr = (
            residual_fn / n_positive
            if n_positive > 0
            else np.nan
        )

        absolute_reduction = (
            primary_fnr - residual_fnr
        )

        conditional_rescue_rate = (
            rescued / fn
            if fn > 0
            else np.nan
        )

        rows.append(
            {
                "feature": feature,
                "group": group,
                "actual_positives": n_positive,
                "true_positives": tp,
                "false_negatives": fn,
                "rescued_false_negatives": rescued,
                "residual_false_negatives": residual_fn,
                "primary_fnr": primary_fnr,
                "simulated_residual_fnr": residual_fnr,
                "absolute_fnr_reduction": absolute_reduction,
                "conditional_fn_rescue_rate":
                    conditional_rescue_rate
            }
        )


result = pd.DataFrame(rows)

result.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# PRINT RESULTS
# ============================================================

for feature in [
    "gender",
    "race",
    "age"
]:

    print("\n" + "=" * 80)
    print(feature.upper())
    print("=" * 80)

    subset = result[
        result["feature"] == feature
    ].copy()

    display = subset[
        [
            "group",
            "actual_positives",
            "true_positives",
            "false_negatives",
            "rescued_false_negatives",
            "primary_fnr",
            "simulated_residual_fnr",
            "absolute_fnr_reduction",
            "conditional_fn_rescue_rate"
        ]
    ].copy()

    for col in [
        "primary_fnr",
        "simulated_residual_fnr",
        "absolute_fnr_reduction",
        "conditional_fn_rescue_rate"
    ]:
        display[col] *= 100

    print(
        display.to_string(
            index=False
        )
    )


# ============================================================
# AFRICAN AMERICAN VS CAUCASIAN
# ============================================================

race_result = result[
    result["feature"] == "race"
].copy()

aa = race_result[
    race_result["group"] == "AfricanAmerican"
]

cauc = race_result[
    race_result["group"] == "Caucasian"
]

if len(aa) == 1 and len(cauc) == 1:

    aa_primary = float(
        aa["primary_fnr"].iloc[0]
    )

    cauc_primary = float(
        cauc["primary_fnr"].iloc[0]
    )

    aa_after = float(
        aa["simulated_residual_fnr"].iloc[0]
    )

    cauc_after = float(
        cauc["simulated_residual_fnr"].iloc[0]
    )

    primary_gap = (
        aa_primary - cauc_primary
    )

    residual_gap = (
        aa_after - cauc_after
    )

    gap_change = (
        residual_gap - primary_gap
    )

    print("\n" + "=" * 80)
    print("AFRICAN AMERICAN VS CAUCASIAN")
    print("=" * 80)

    print(
        f"Primary FNR gap: "
        f"{primary_gap * 100:.2f} pp"
    )

    print(
        f"Simulated residual FNR gap: "
        f"{residual_gap * 100:.2f} pp"
    )

    print(
        f"Gap change: "
        f"{gap_change * 100:+.2f} pp"
    )


print("\n" + "=" * 80)
print("FILE SAVED")
print("=" * 80)

print(OUTPUT_FILE)

print("\n" + "=" * 80)
print("PHASE 8.3.5 COMPLETE")
print("=" * 80)