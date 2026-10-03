import numpy as np
import pandas as pd
from pathlib import Path

# ============================================================
# PHASE 7.7
# Rescue Router Error / Patient Characterization Analysis
# ============================================================

INPUT_FILE = Path(
    "results/eligible/fn_rescue_router_predictions.csv"
)

OUTPUT_DIR = Path("results/eligible")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BUDGET = 0.15

df = pd.read_csv(INPUT_FILE)

print("=" * 75)
print("PHASE 7.7 — RESCUE ROUTER ERROR ANALYSIS")
print("=" * 75)

print("\nLow-risk population:", len(df))
print("False negatives:", int(df["router_target"].sum()))

# ------------------------------------------------------------
# Rank patients by Rescue Router
# ------------------------------------------------------------

n_review = int(np.floor(len(df) * BUDGET))

df = df.sort_values(
    "fn_router_probability",
    ascending=False
).reset_index(drop=True)

df["selected_for_review"] = 0
df.loc[:n_review - 1, "selected_for_review"] = 1

print("\nReview budget:", BUDGET)
print("Patients reviewed:", n_review)

# ------------------------------------------------------------
# Define analysis groups
# ------------------------------------------------------------

conditions = [
    (
        (df["router_target"] == 1)
        & (df["selected_for_review"] == 1)
    ),
    (
        (df["router_target"] == 1)
        & (df["selected_for_review"] == 0)
    ),
    (
        (df["router_target"] == 0)
        & (df["selected_for_review"] == 1)
    ),
    (
        (df["router_target"] == 0)
        & (df["selected_for_review"] == 0)
    )
]

labels = [
    "Rescued_FN",
    "Missed_FN",
    "Unnecessary_Review",
    "Correctly_Not_Reviewed"
]

df["rescue_group"] = np.select(
    conditions,
    labels,
    default="Unknown"
)

# ------------------------------------------------------------
# Group counts
# ------------------------------------------------------------

counts = (
    df["rescue_group"]
    .value_counts()
    .rename_axis("group")
    .reset_index(name="n")
)

counts["percent"] = (
    counts["n"] / len(df) * 100
)

print("\n" + "=" * 75)
print("GROUP COUNTS")
print("=" * 75)

print(counts.to_string(index=False))

# ------------------------------------------------------------
# Numerical variables
# ------------------------------------------------------------

numeric_features = [
    "calibrated_probability",
    "raw_probability",
    "probability_uncertainty",
    "boundary_distance",
    "boundary_uncertainty",
    "model_disagreement_std",
    "model_disagreement_range",
    "number_inpatient",
    "number_emergency",
    "number_outpatient",
    "number_diagnoses",
    "time_in_hospital",
    "fn_router_probability"
]

numeric_summary = (
    df.groupby("rescue_group")[numeric_features]
    .agg(["mean", "median", "std"])
)

print("\n" + "=" * 75)
print("NUMERIC CHARACTERISTICS")
print("=" * 75)

print(numeric_summary.to_string())

# ------------------------------------------------------------
# Focus specifically on rescued vs missed FNs
# ------------------------------------------------------------

fn_df = df[df["router_target"] == 1].copy()

rescued = fn_df[
    fn_df["selected_for_review"] == 1
]

missed = fn_df[
    fn_df["selected_for_review"] == 0
]

comparison_rows = []

for feature in numeric_features:

    comparison_rows.append({
        "feature": feature,
        "rescued_mean": rescued[feature].mean(),
        "missed_mean": missed[feature].mean(),
        "difference":
            rescued[feature].mean()
            - missed[feature].mean(),
        "rescued_median": rescued[feature].median(),
        "missed_median": missed[feature].median()
    })

comparison = pd.DataFrame(comparison_rows)

print("\n" + "=" * 75)
print("RESCUED FN VS MISSED FN")
print("=" * 75)

print(comparison.to_string(index=False))

# ------------------------------------------------------------
# Categorical characteristics
# ------------------------------------------------------------

categorical_features = [
    "age",
    "gender",
    "race"
]

categorical_tables = []

for feature in categorical_features:

    temp = pd.crosstab(
        fn_df[feature],
        fn_df["selected_for_review"],
        normalize="columns"
    ) * 100

    temp = temp.reset_index()

    temp = temp.rename(
        columns={
            0: "missed_percent",
            1: "rescued_percent"
        }
    )

    temp["feature"] = feature

    categorical_tables.append(temp)

categorical_summary = pd.concat(
    categorical_tables,
    ignore_index=True
)

print("\n" + "=" * 75)
print("CATEGORICAL CHARACTERISTICS — FALSE NEGATIVES")
print("=" * 75)

print(categorical_summary.to_string(index=False))

# ------------------------------------------------------------
# Router probability distribution
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("ROUTER SCORE DISTRIBUTION")
print("=" * 75)

print(
    fn_df.groupby("rescue_group")[
        "fn_router_probability"
    ].describe().to_string()
)

# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

df.to_csv(
    OUTPUT_DIR / "rescue_error_analysis_patients.csv",
    index=False
)

counts.to_csv(
    OUTPUT_DIR / "rescue_error_group_counts.csv",
    index=False
)

comparison.to_csv(
    OUTPUT_DIR / "rescued_vs_missed_fn.csv",
    index=False
)

categorical_summary.to_csv(
    OUTPUT_DIR / "rescued_vs_missed_fn_categorical.csv",
    index=False
)

print("\n" + "=" * 75)
print("FILES SAVED")
print("=" * 75)

print(
    "results/eligible/"
    "rescue_error_analysis_patients.csv"
)

print(
    "results/eligible/"
    "rescue_error_group_counts.csv"
)

print(
    "results/eligible/"
    "rescued_vs_missed_fn.csv"
)

print(
    "results/eligible/"
    "rescued_vs_missed_fn_categorical.csv"
)

print("\n" + "=" * 75)
print("PHASE 7.7 COMPLETE")
print("=" * 75)