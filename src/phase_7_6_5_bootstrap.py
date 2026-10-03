import numpy as np
import pandas as pd
from pathlib import Path

# ============================================================
# PHASE 7.6.5
# Bootstrap robustness analysis for false-negative rescue
# ============================================================

INPUT_FILE = Path("results/eligible/fn_rescue_router_predictions.csv")
OUTPUT_DIR = Path("results/eligible")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

N_BOOTSTRAPS = 5000
RANDOM_SEED = 42

BUDGETS = [0.10, 0.15, 0.20, 0.25]

rng = np.random.default_rng(RANDOM_SEED)

# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print("=" * 75)
print("PHASE 7.6.5 — BOOTSTRAP ROBUSTNESS")
print("=" * 75)

print("\nDataset shape:", df.shape)
print("False negatives:", int(df["router_target"].sum()))
print("Low-risk patients:", len(df))

# ------------------------------------------------------------
# Ranking methods
# Higher score = review first
# ------------------------------------------------------------

methods = {
    "Probability": "calibrated_probability",
    "Boundary": "boundary_uncertainty",
    "Disagreement": "model_disagreement_std",
    "Rescue Router": "fn_router_probability",
}

# ------------------------------------------------------------
# Check Probability vs Boundary ranking
# ------------------------------------------------------------

prob_rank = df["calibrated_probability"].rank(
    method="average",
    ascending=False
)

boundary_rank = df["boundary_uncertainty"].rank(
    method="average",
    ascending=False
)

rank_corr = prob_rank.corr(boundary_rank, method="spearman")

print("\n" + "=" * 75)
print("PROBABILITY VS BOUNDARY CHECK")
print("=" * 75)

print("Spearman rank correlation:", rank_corr)

# ------------------------------------------------------------
# Function: FN capture rate
# ------------------------------------------------------------

def capture_rate(data, score_col, budget):
    """
    Rank low-risk patients by score and calculate the fraction
    of all false negatives captured within the review budget.
    """

    n_review = max(1, int(np.floor(len(data) * budget)))

    ranked = data.sort_values(
        score_col,
        ascending=False
    )

    reviewed = ranked.iloc[:n_review]

    total_fn = data["router_target"].sum()

    if total_fn == 0:
        return np.nan

    fn_captured = reviewed["router_target"].sum()

    return fn_captured / total_fn


# ------------------------------------------------------------
# Original point estimates
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("ORIGINAL POINT ESTIMATES")
print("=" * 75)

original_rows = []

for budget in BUDGETS:

    print(f"\nReview budget: {budget:.0%}")

    for method, score_col in methods.items():

        rate = capture_rate(
            df,
            score_col,
            budget
        )

        original_rows.append({
            "budget": budget,
            "method": method,
            "fn_capture_rate": rate
        })

        print(
            f"{method:15s}: "
            f"{rate:.4f} ({rate * 100:.2f}%)"
        )

original_df = pd.DataFrame(original_rows)

# ------------------------------------------------------------
# Bootstrap
# ------------------------------------------------------------

print("\n" + "=" * 75)
print(f"RUNNING {N_BOOTSTRAPS} BOOTSTRAP ITERATIONS")
print("=" * 75)

bootstrap_results = []

n = len(df)

for b in range(N_BOOTSTRAPS):

    indices = rng.integers(
        0,
        n,
        size=n
    )

    sample = df.iloc[indices].copy()

    # Skip bootstrap samples with no FN
    if sample["router_target"].sum() == 0:
        continue

    for budget in BUDGETS:

        row = {
            "iteration": b,
            "budget": budget
        }

        for method, score_col in methods.items():

            row[method] = capture_rate(
                sample,
                score_col,
                budget
            )

        bootstrap_results.append(row)

    if (b + 1) % 500 == 0:
        print(
            f"Completed {b + 1}/{N_BOOTSTRAPS}"
        )

boot_df = pd.DataFrame(bootstrap_results)

# ------------------------------------------------------------
# Confidence intervals for each method
# ------------------------------------------------------------

summary_rows = []

for budget in BUDGETS:

    subset = boot_df[
        boot_df["budget"] == budget
    ]

    for method in methods:

        values = subset[method].dropna()

        original_value = original_df[
            (original_df["budget"] == budget)
            & (original_df["method"] == method)
        ]["fn_capture_rate"].iloc[0]

        lower = np.percentile(values, 2.5)
        upper = np.percentile(values, 97.5)

        summary_rows.append({
            "budget": budget,
            "method": method,
            "point_estimate": original_value,
            "ci_lower": lower,
            "ci_upper": upper
        })

summary_df = pd.DataFrame(summary_rows)

# ------------------------------------------------------------
# Paired Rescue Router comparisons
# ------------------------------------------------------------

comparison_rows = []

baselines = [
    "Probability",
    "Boundary",
    "Disagreement"
]

for budget in BUDGETS:

    subset = boot_df[
        boot_df["budget"] == budget
    ]

    for baseline in baselines:

        differences = (
            subset["Rescue Router"]
            - subset[baseline]
        ).dropna()

        mean_difference = differences.mean()

        lower = np.percentile(
            differences,
            2.5
        )

        upper = np.percentile(
            differences,
            97.5
        )

        # Bootstrap probability that Rescue Router
        # is no better than baseline
        p_value = 2 * min(
            np.mean(differences <= 0),
            np.mean(differences >= 0)
        )

        p_value = min(p_value, 1.0)

        comparison_rows.append({
            "budget": budget,
            "comparison":
                f"Rescue Router vs {baseline}",
            "mean_difference":
                mean_difference,
            "ci_lower":
                lower,
            "ci_upper":
                upper,
            "bootstrap_p_value":
                p_value
        })

comparison_df = pd.DataFrame(
    comparison_rows
)

# ------------------------------------------------------------
# Save results
# ------------------------------------------------------------

summary_file = (
    OUTPUT_DIR
    / "router_bootstrap_confidence_intervals.csv"
)

comparison_file = (
    OUTPUT_DIR
    / "router_bootstrap_comparisons.csv"
)

raw_file = (
    OUTPUT_DIR
    / "router_bootstrap_raw.csv"
)

summary_df.to_csv(
    summary_file,
    index=False
)

comparison_df.to_csv(
    comparison_file,
    index=False
)

boot_df.to_csv(
    raw_file,
    index=False
)

# ------------------------------------------------------------
# Display
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("BOOTSTRAP 95% CONFIDENCE INTERVALS")
print("=" * 75)

display_summary = summary_df.copy()

for col in [
    "point_estimate",
    "ci_lower",
    "ci_upper"
]:
    display_summary[col] = (
        display_summary[col] * 100
    )

print(
    display_summary.to_string(
        index=False
    )
)

print("\n" + "=" * 75)
print("RESCUE ROUTER — PAIRED COMPARISONS")
print("=" * 75)

display_comparison = comparison_df.copy()

for col in [
    "mean_difference",
    "ci_lower",
    "ci_upper"
]:
    display_comparison[col] = (
        display_comparison[col] * 100
    )

print(
    display_comparison.to_string(
        index=False
    )
)

print("\n" + "=" * 75)
print("FILES SAVED")
print("=" * 75)

print(summary_file)
print(comparison_file)
print(raw_file)

print("\n" + "=" * 75)
print("PHASE 7.6.5 COMPLETE")
print("=" * 75)