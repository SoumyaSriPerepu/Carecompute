import pandas as pd
import numpy as np
import os


# ============================================================
# PHASE 7.6.2 — ROUTER SIGNAL ANALYSIS
# ============================================================

INPUT_PATH = "results/eligible/router_validation.csv"

OUTPUT_PATH = (
    "results/eligible/router_signal_analysis.csv"
)


print("=" * 70)
print("PHASE 7.6.2 — ROUTER SIGNAL ANALYSIS")
print("=" * 70)


# ============================================================
# 1. LOAD ROUTER DATA
# ============================================================

df = pd.read_csv(
    INPUT_PATH,
    low_memory=False
)


print()
print("Validation encounters:", len(df))


# ============================================================
# 2. CREATE ERROR INDICATORS
# ============================================================

df["is_error"] = (
    df["case_type"].isin(["FP", "FN"])
).astype(int)

df["is_false_negative"] = (
    df["case_type"] == "FN"
).astype(int)

df["is_false_positive"] = (
    df["case_type"] == "FP"
).astype(int)


# ============================================================
# 3. SIGNALS TO ANALYZE
# ============================================================

signals = [
    "calibrated_probability",
    "probability_uncertainty",
    "boundary_distance",
    "boundary_uncertainty",
    "model_disagreement_std",
    "model_disagreement_range",
    "number_inpatient",
    "number_emergency",
    "number_outpatient",
    "number_diagnoses",
    "time_in_hospital"
]


# ============================================================
# 4. MEAN SIGNAL BY CASE TYPE
# ============================================================

print()
print("MEAN SIGNALS BY CASE TYPE")
print("-" * 70)

case_means = (
    df.groupby("case_type")[signals]
    .mean()
    .T
)

print(
    case_means.to_string()
)


# ============================================================
# 5. MEDIAN SIGNAL BY CASE TYPE
# ============================================================

print()
print("MEDIAN SIGNALS BY CASE TYPE")
print("-" * 70)

case_medians = (
    df.groupby("case_type")[signals]
    .median()
    .T
)

print(
    case_medians.to_string()
)


# ============================================================
# 6. CORRELATION WITH ERRORS
#
# These are descriptive correlations.
# We are NOT claiming causality.
# ============================================================

rows = []

for signal in signals:

    error_corr = df[
        [signal, "is_error"]
    ].corr().iloc[0, 1]

    fn_corr = df[
        [signal, "is_false_negative"]
    ].corr().iloc[0, 1]

    fp_corr = df[
        [signal, "is_false_positive"]
    ].corr().iloc[0, 1]

    rows.append({

        "signal":
            signal,

        "error_correlation":
            error_corr,

        "false_negative_correlation":
            fn_corr,

        "false_positive_correlation":
            fp_corr
    })


correlation_df = pd.DataFrame(
    rows
)


# ============================================================
# 7. PRINT CORRELATIONS
# ============================================================

print()
print("SIGNAL / ERROR CORRELATIONS")
print("-" * 70)

print(
    correlation_df
    .sort_values(
        "false_negative_correlation",
        ascending=False
    )
    .to_string(
        index=False
    )
)


# ============================================================
# 8. FN VS TN
#
# This is especially important.
#
# Both FN and TN were predicted LOW risk.
# We want to know what distinguishes the dangerous misses
# (FN) from correctly low-risk cases (TN).
# ============================================================

low_prediction_cases = df[
    df["case_type"].isin(
        ["FN", "TN"]
    )
].copy()


print()
print("FN VS TN — MEAN SIGNALS")
print("-" * 70)

fn_tn_means = (
    low_prediction_cases
    .groupby("case_type")[signals]
    .mean()
    .T
)

print(
    fn_tn_means.to_string()
)


# ============================================================
# 9. STANDARDIZED FN/TN DIFFERENCE
#
# Positive:
# FN has a larger value than TN.
#
# Negative:
# FN has a smaller value than TN.
# ============================================================

difference_rows = []


for signal in signals:

    fn_values = low_prediction_cases.loc[
        low_prediction_cases["case_type"] == "FN",
        signal
    ]

    tn_values = low_prediction_cases.loc[
        low_prediction_cases["case_type"] == "TN",
        signal
    ]


    fn_mean = fn_values.mean()
    tn_mean = tn_values.mean()


    pooled_std = np.sqrt(
        (
            fn_values.var()
            +
            tn_values.var()
        )
        / 2
    )


    if pooled_std > 0:

        standardized_difference = (
            (fn_mean - tn_mean)
            / pooled_std
        )

    else:

        standardized_difference = 0


    difference_rows.append({

        "signal":
            signal,

        "fn_mean":
            fn_mean,

        "tn_mean":
            tn_mean,

        "fn_minus_tn":
            fn_mean - tn_mean,

        "standardized_difference":
            standardized_difference
    })


difference_df = pd.DataFrame(
    difference_rows
)


difference_df[
    "absolute_standardized_difference"
] = np.abs(
    difference_df[
        "standardized_difference"
    ]
)


difference_df = (
    difference_df
    .sort_values(
        "absolute_standardized_difference",
        ascending=False
    )
)


print()
print("FN VS TN — STANDARDIZED DIFFERENCE")
print("-" * 70)

print(
    difference_df.to_string(
        index=False
    )
)


# ============================================================
# 10. SAVE COMBINED ANALYSIS
# ============================================================

output = difference_df.merge(
    correlation_df,
    on="signal",
    how="left"
)


os.makedirs(
    "results/eligible",
    exist_ok=True
)


output.to_csv(
    OUTPUT_PATH,
    index=False
)


print()
print("FILE SAVED")
print("-" * 70)

print(
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
print("PHASE 7.6.2 COMPLETE")
print("=" * 70)
