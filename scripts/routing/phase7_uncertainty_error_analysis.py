import pandas as pd
import numpy as np
import os


# ============================================================
# PHASE 7.3 — UNCERTAINTY ERROR ANALYSIS
# ============================================================

INPUT_PATH = (
    "results/eligible/test_predictions.csv"
)

OUTPUT_PATH = (
    "results/eligible/"
    "uncertainty_error_analysis.csv"
)


# ============================================================
# 1. LOAD DATA
# ============================================================

df = pd.read_csv(
    INPUT_PATH
)


# ============================================================
# 2. CREATE CASE TYPE
# ============================================================

def get_case_type(row):

    actual = row["actual_30d"]
    predicted = row["predicted_30d"]

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
# 3. BASIC COUNTS
# ============================================================

total_fp = (
    df["case_type"] == "FP"
).sum()

total_fn = (
    df["case_type"] == "FN"
).sum()

total_errors = (
    df["case_type"].isin(
        ["FP", "FN"]
    )
).sum()


print()
print("=" * 70)
print("PHASE 7.3 — UNCERTAINTY ERROR ANALYSIS")
print("=" * 70)

print()
print("TOTAL ERRORS")
print("-------------------------")

print("False positives:", total_fp)
print("False negatives:", total_fn)
print("Total errors:", total_errors)


# ============================================================
# 4. CANDIDATE THRESHOLDS
# ============================================================

thresholds = sorted(
    df["uncertainty"]
    .unique()
)


# We don't need thousands of almost identical thresholds.
# Use useful candidate levels.

candidate_thresholds = [
    0.10,
    0.15,
    0.20,
    0.23,
    0.272052272052272,
    0.30,
    0.35,
    0.3890954151177199,
    0.4057971014492754,
    0.50
]


results = []


# ============================================================
# 5. TEST EACH THRESHOLD
# ============================================================

for threshold in candidate_thresholds:

    review_mask = (
        df["uncertainty"]
        >= threshold
    )

    reviewed = int(
        review_mask.sum()
    )

    review_rate = (
        reviewed / len(df)
    )


    # --------------------------------------------------------
    # FALSE POSITIVES CAPTURED
    # --------------------------------------------------------

    fp_captured = int(
        (
            review_mask
            & (
                df["case_type"]
                == "FP"
            )
        ).sum()
    )

    if total_fp > 0:

        fp_capture_rate = (
            fp_captured
            / total_fp
        )

    else:

        fp_capture_rate = 0


    # --------------------------------------------------------
    # FALSE NEGATIVES CAPTURED
    # --------------------------------------------------------

    fn_captured = int(
        (
            review_mask
            & (
                df["case_type"]
                == "FN"
            )
        ).sum()
    )

    if total_fn > 0:

        fn_capture_rate = (
            fn_captured
            / total_fn
        )

    else:

        fn_capture_rate = 0


    # --------------------------------------------------------
    # ALL ERRORS
    # --------------------------------------------------------

    errors_captured = (
        fp_captured
        + fn_captured
    )

    if total_errors > 0:

        error_capture_rate = (
            errors_captured
            / total_errors
        )

    else:

        error_capture_rate = 0


    # --------------------------------------------------------
    # REVIEW EFFICIENCY
    #
    # Of all cases sent to review,
    # how many were actually model errors?
    # --------------------------------------------------------

    if reviewed > 0:

        review_error_rate = (
            errors_captured
            / reviewed
        )

    else:

        review_error_rate = 0


    results.append({

        "uncertainty_threshold":
            threshold,

        "patients_reviewed":
            reviewed,

        "review_rate":
            review_rate,

        "fp_captured":
            fp_captured,

        "fp_capture_rate":
            fp_capture_rate,

        "fn_captured":
            fn_captured,

        "fn_capture_rate":
            fn_capture_rate,

        "all_errors_captured":
            errors_captured,

        "all_error_capture_rate":
            error_capture_rate,

        "review_error_rate":
            review_error_rate
    })


# ============================================================
# 6. CREATE TABLE
# ============================================================

results_df = pd.DataFrame(
    results
)


print()
print("THRESHOLD COMPARISON")
print("-------------------------")

print(
    results_df.to_string(
        index=False
    )
)


# ============================================================
# 7. SPECIFIC FALSE-NEGATIVE ANALYSIS
# ============================================================

fn_df = df[
    df["case_type"] == "FN"
].copy()


print()
print("FALSE NEGATIVE UNCERTAINTY")
print("-------------------------")

print(
    fn_df[
        "uncertainty"
    ].describe()
)


print()
print("FALSE NEGATIVE PERCENTILES")
print("-------------------------")

for percentile in [
    0.10,
    0.25,
    0.50,
    0.75,
    0.90,
    0.95
]:

    print(
        f"{int(percentile * 100)}th:",
        fn_df[
            "uncertainty"
        ].quantile(
            percentile
        )
    )


# ============================================================
# 8. CHECK UNCERTAINTY VS RISK
# ============================================================

correlation = (
    df[
        [
            "calibrated_probability",
            "uncertainty"
        ]
    ]
    .corr()
    .iloc[0, 1]
)


print()
print("RISK / UNCERTAINTY RELATIONSHIP")
print("-------------------------")

print(
    "Correlation:",
    correlation
)


# ============================================================
# 9. SAVE
# ============================================================

os.makedirs(
    "results/eligible",
    exist_ok=True
)

results_df.to_csv(
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
print("=" * 70)
print("PHASE 7.3 COMPLETE")
print("=" * 70)
