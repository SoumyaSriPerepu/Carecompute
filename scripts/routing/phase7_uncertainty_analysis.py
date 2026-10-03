import pandas as pd
import numpy as np
import os


# ============================================================
# PHASE 7.2 — UNCERTAINTY ANALYSIS
#
# Goal:
# Understand the uncertainty distribution BEFORE choosing
# an uncertainty threshold for the agent router.
# ============================================================


# ============================================================
# 1. SETTINGS
# ============================================================

PREDICTIONS_PATH = (
    "results/eligible/test_predictions.csv"
)

OUTPUT_PATH = (
    "results/eligible/"
    "uncertainty_analysis.csv"
)

RISK_THRESHOLD = 0.115


# ============================================================
# 2. LOAD LOCKED TEST PREDICTIONS
# ============================================================

df = pd.read_csv(
    PREDICTIONS_PATH
)

print()
print("=" * 60)
print("PHASE 7 — UNCERTAINTY ANALYSIS")
print("=" * 60)

print(
    "Total encounters:",
    len(df)
)


# ============================================================
# 3. SAFETY CHECK
# ============================================================

required_columns = [
    "encounter_id",
    "actual_30d",
    "calibrated_probability",
    "uncertainty",
    "predicted_30d"
]


for column in required_columns:

    if column not in df.columns:

        raise ValueError(
            f"Missing required column: {column}"
        )


# ============================================================
# 4. BASIC UNCERTAINTY STATISTICS
# ============================================================

print()
print("UNCERTAINTY SUMMARY")
print("-------------------------")

print(
    df["uncertainty"].describe()
)


# ============================================================
# 5. IMPORTANT PERCENTILES
# ============================================================

percentiles = [
    0.50,
    0.60,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
    0.95
]


print()
print("UNCERTAINTY PERCENTILES")
print("-------------------------")


percentile_rows = []


for percentile in percentiles:

    value = df[
        "uncertainty"
    ].quantile(
        percentile
    )

    percentile_rows.append({
        "percentile":
            percentile,

        "uncertainty_threshold":
            value
    })

    print(
        f"{int(percentile * 100)}th percentile:",
        value
    )


# ============================================================
# 6. UNCERTAINTY BY CORRECT / INCORRECT PREDICTION
# ============================================================

df["correct_prediction"] = (
    df["actual_30d"]
    == df["predicted_30d"]
)


print()
print("MEAN UNCERTAINTY")
print("-------------------------")

print(
    "Correct predictions:",
    df.loc[
        df["correct_prediction"],
        "uncertainty"
    ].mean()
)

print(
    "Incorrect predictions:",
    df.loc[
        ~df["correct_prediction"],
        "uncertainty"
    ].mean()
)


# ============================================================
# 7. CREATE CASE TYPES
# ============================================================

def get_case_type(row):

    actual = row[
        "actual_30d"
    ]

    predicted = row[
        "predicted_30d"
    ]

    if actual == 1 and predicted == 1:
        return "TP"

    if actual == 0 and predicted == 0:
        return "TN"

    if actual == 0 and predicted == 1:
        return "FP"

    return "FN"


df["case_type"] = df.apply(
    get_case_type,
    axis=1
)


# ============================================================
# 8. UNCERTAINTY BY CASE TYPE
# ============================================================

case_summary = (
    df.groupby(
        "case_type"
    )["uncertainty"]
    .agg(
        [
            "count",
            "mean",
            "median",
            "min",
            "max"
        ]
    )
)


print()
print("UNCERTAINTY BY CASE TYPE")
print("-------------------------")

print(
    case_summary
)


# ============================================================
# 9. TEST CANDIDATE ROUTING THRESHOLDS
# ============================================================

candidate_percentiles = [
    0.70,
    0.75,
    0.80,
    0.85,
    0.90
]


routing_rows = []


print()
print("CANDIDATE UNCERTAINTY ROUTES")
print("----------------------------")


for percentile in candidate_percentiles:

    threshold = df[
        "uncertainty"
    ].quantile(
        percentile
    )

    uncertain = (
        df["uncertainty"]
        >= threshold
    )

    total_uncertain = int(
        uncertain.sum()
    )

    percent_routed = (
        total_uncertain
        / len(df)
    )

    errors = (
        ~df["correct_prediction"]
    )

    total_errors = int(
        errors.sum()
    )

    errors_captured = int(
        (
            uncertain
            & errors
        ).sum()
    )

    if total_errors > 0:

        error_capture_rate = (
            errors_captured
            / total_errors
        )

    else:

        error_capture_rate = 0


    routing_rows.append({

        "percentile":
            percentile,

        "uncertainty_threshold":
            threshold,

        "patients_to_review":
            total_uncertain,

        "review_rate":
            percent_routed,

        "errors_captured":
            errors_captured,

        "error_capture_rate":
            error_capture_rate
    })


routing_df = pd.DataFrame(
    routing_rows
)


print(
    routing_df.to_string(
        index=False
    )
)


# ============================================================
# 10. SAVE ANALYSIS
# ============================================================

os.makedirs(
    "results/eligible",
    exist_ok=True
)


routing_df.to_csv(
    OUTPUT_PATH,
    index=False
)


print()
print(
    "Saved:",
    os.path.exists(
        OUTPUT_PATH
    )
)

print(
    "File:",
    OUTPUT_PATH
)


print()
print("=" * 60)
print("UNCERTAINTY ANALYSIS COMPLETE")
print("=" * 60)
