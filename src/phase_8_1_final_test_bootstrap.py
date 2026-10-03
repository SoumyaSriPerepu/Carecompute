import numpy as np
import pandas as pd
from pathlib import Path

# ============================================================
# PHASE 8.1
# FINAL TEST — BOOTSTRAP STATISTICAL COMPARISON
# ============================================================

INPUT_FILE = Path(
    "results/eligible/final_test_router_predictions.csv"
)

OUTPUT_DIR = Path("results/eligible")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LOCKED_BUDGET = 0.15
N_BOOTSTRAPS = 5000
RANDOM_SEED = 42

rng = np.random.default_rng(RANDOM_SEED)

print("=" * 80)
print("PHASE 8.1 — FINAL TEST BOOTSTRAP COMPARISON")
print("=" * 80)

# ============================================================
# 1. LOAD FROZEN FINAL-TEST RESULTS
# ============================================================

df = pd.read_csv(INPUT_FILE)

print("\nDataset shape:", df.shape)

required = [
    "actual_30d",
    "predicted_30d",
    "calibrated_probability",
    "model_disagreement_std",
    "fn_router_probability"
]

missing = [
    c for c in required
    if c not in df.columns
]

assert not missing, (
    f"Missing required columns: {missing}"
)

# final_test_router_predictions.csv should already contain
# only the low-risk population from Phase 7.9.

assert (
    df["predicted_30d"] == 0
).all(), (
    "Input contains patients not classified as low risk."
)

df["router_target"] = (
    df["actual_30d"] == 1
).astype(int)

N = len(df)
TOTAL_FN = int(df["router_target"].sum())

N_REVIEW = int(
    np.floor(N * LOCKED_BUDGET)
)

print("Low-risk test patients:", N)
print("False negatives:", TOTAL_FN)
print("Locked review budget:", LOCKED_BUDGET)
print("Patients reviewed:", N_REVIEW)

# ============================================================
# 2. DEFINE FROZEN REVIEW STRATEGIES
# ============================================================

METHODS = {
    "Probability":
        "calibrated_probability",

    "Disagreement":
        "model_disagreement_std",

    "Rescue Router":
        "fn_router_probability"
}

# ============================================================
# 3. POINT ESTIMATES
# ============================================================

def capture_from_ranked_sample(
    data,
    score_column,
    n_review
):
    ranked = data.sort_values(
        score_column,
        ascending=False
    )

    reviewed = ranked.iloc[
        :n_review
    ]

    captured = int(
        reviewed["router_target"].sum()
    )

    return captured


print("\n" + "=" * 80)
print("ORIGINAL FINAL-TEST POINT ESTIMATES")
print("=" * 80)

point_rows = []

for method, score in METHODS.items():

    captured = capture_from_ranked_sample(
        df,
        score,
        N_REVIEW
    )

    capture_rate = (
        captured / TOTAL_FN
    )

    precision = (
        captured / N_REVIEW
    )

    point_rows.append({
        "method": method,
        "fn_captured": captured,
        "fn_capture_rate":
            capture_rate,
        "review_precision":
            precision
    })

# Random expected point estimate:
# under uniform random review,
# expected FN capture rate equals review fraction.
random_expected_capture = (
    LOCKED_BUDGET
)

random_expected_fn = (
    TOTAL_FN
    * LOCKED_BUDGET
)

random_expected_precision = (
    TOTAL_FN / N
)

point_rows.append({
    "method": "Random",
    "fn_captured":
        random_expected_fn,
    "fn_capture_rate":
        random_expected_capture,
    "review_precision":
        random_expected_precision
})

point_df = pd.DataFrame(
    point_rows
)

print(
    point_df.to_string(
        index=False
    )
)

# ============================================================
# 4. BOOTSTRAP
#
# Resample low-risk patients WITH replacement.
#
# Within each bootstrap sample:
#   - preserve the sample's outcome prevalence
#   - rank the resampled patients again
#   - review 15% of that resampled population
#   - calculate FN capture rate
#
# All methods are evaluated on the SAME bootstrap sample,
# enabling paired comparisons.
# ============================================================

print("\n" + "=" * 80)
print(
    f"RUNNING {N_BOOTSTRAPS} PAIRED BOOTSTRAP ITERATIONS"
)
print("=" * 80)

bootstrap_rows = []

indices = np.arange(N)

for b in range(N_BOOTSTRAPS):

    sampled_indices = rng.choice(
        indices,
        size=N,
        replace=True
    )

    sample = df.iloc[
        sampled_indices
    ].copy()

    sample_fn = int(
        sample["router_target"].sum()
    )

    # Extremely unlikely, but protect against
    # a bootstrap sample containing zero FNs.
    if sample_fn == 0:
        continue

    sample_n_review = int(
        np.floor(
            len(sample)
            * LOCKED_BUDGET
        )
    )

    row = {
        "bootstrap_iteration": b,
        "sample_false_negatives":
            sample_fn
    }

    for method, score in METHODS.items():

        captured = (
            capture_from_ranked_sample(
                sample,
                score,
                sample_n_review
            )
        )

        row[
            f"{method}_capture"
        ] = (
            captured / sample_fn
        )

    # For random review, expected capture rate
    # is the exact review fraction in this sample.
    row["Random_capture"] = (
        sample_n_review
        / len(sample)
    )

    bootstrap_rows.append(row)

    if (b + 1) % 500 == 0:
        print(
            f"Completed {b + 1}/{N_BOOTSTRAPS}"
        )

bootstrap_df = pd.DataFrame(
    bootstrap_rows
)

# ============================================================
# 5. 95% BOOTSTRAP CONFIDENCE INTERVALS
# ============================================================

print("\n" + "=" * 80)
print("BOOTSTRAP 95% CONFIDENCE INTERVALS")
print("=" * 80)

ci_rows = []

for method in [
    "Probability",
    "Disagreement",
    "Rescue Router"
]:

    values = bootstrap_df[
        f"{method}_capture"
    ].to_numpy()

    point = point_df.loc[
        point_df["method"] == method,
        "fn_capture_rate"
    ].iloc[0]

    ci_rows.append({
        "method": method,
        "point_estimate": point,
        "bootstrap_mean":
            np.mean(values),
        "ci_lower":
            np.percentile(
                values,
                2.5
            ),
        "ci_upper":
            np.percentile(
                values,
                97.5
            )
    })

# Random is fixed expectation under random review.
ci_rows.append({
    "method": "Random",
    "point_estimate":
        LOCKED_BUDGET,
    "bootstrap_mean":
        LOCKED_BUDGET,
    "ci_lower":
        LOCKED_BUDGET,
    "ci_upper":
        LOCKED_BUDGET
})

ci_df = pd.DataFrame(
    ci_rows
)

display_ci = ci_df.copy()

for c in [
    "point_estimate",
    "bootstrap_mean",
    "ci_lower",
    "ci_upper"
]:
    display_ci[c] = (
        display_ci[c] * 100
    )

print(
    display_ci.to_string(
        index=False
    )
)

# ============================================================
# 6. PAIRED COMPARISONS
# ============================================================

print("\n" + "=" * 80)
print("PAIRED BOOTSTRAP COMPARISONS")
print("=" * 80)

comparisons = [
    (
        "Rescue Router",
        "Probability"
    ),
    (
        "Rescue Router",
        "Disagreement"
    ),
    (
        "Probability",
        "Disagreement"
    )
]

comparison_rows = []

for method_a, method_b in comparisons:

    a = bootstrap_df[
        f"{method_a}_capture"
    ].to_numpy()

    b = bootstrap_df[
        f"{method_b}_capture"
    ].to_numpy()

    diff = a - b

    ci_low = np.percentile(
        diff,
        2.5
    )

    ci_high = np.percentile(
        diff,
        97.5
    )

    # Two-sided bootstrap sign-style p-value
    p_lower = np.mean(
        diff <= 0
    )

    p_upper = np.mean(
        diff >= 0
    )

    p_value = min(
        1.0,
        2 * min(
            p_lower,
            p_upper
        )
    )

    comparison_rows.append({
        "comparison":
            f"{method_a} vs {method_b}",

        "mean_difference":
            np.mean(diff),

        "ci_lower":
            ci_low,

        "ci_upper":
            ci_high,

        "bootstrap_p_value":
            p_value,

        "probability_a_better":
            np.mean(diff > 0),

        "probability_equal":
            np.mean(diff == 0),

        "probability_a_worse":
            np.mean(diff < 0)
    })

comparison_df = pd.DataFrame(
    comparison_rows
)

display_comparison = (
    comparison_df.copy()
)

for c in [
    "mean_difference",
    "ci_lower",
    "ci_upper",
    "probability_a_better",
    "probability_equal",
    "probability_a_worse"
]:
    display_comparison[c] = (
        display_comparison[c] * 100
    )

print(
    display_comparison.to_string(
        index=False
    )
)

# ============================================================
# 7. ROUTER VS RANDOM
#
# Since expected random capture = 15%, estimate the
# bootstrap distribution of router improvement over
# that prespecified random expectation.
# ============================================================

print("\n" + "=" * 80)
print("RESCUE ROUTER VS RANDOM EXPECTATION")
print("=" * 80)

router_values = bootstrap_df[
    "Rescue Router_capture"
].to_numpy()

random_fraction = (
    N_REVIEW / N
)

router_random_diff = (
    router_values
    - random_fraction
)

rr_ci_low = np.percentile(
    router_random_diff,
    2.5
)

rr_ci_high = np.percentile(
    router_random_diff,
    97.5
)

p_lower = np.mean(
    router_random_diff <= 0
)

p_upper = np.mean(
    router_random_diff >= 0
)

rr_p = min(
    1.0,
    2 * min(
        p_lower,
        p_upper
    )
)

router_point = point_df.loc[
    point_df["method"]
    == "Rescue Router",
    "fn_capture_rate"
].iloc[0]

point_difference = (
    router_point
    - random_fraction
)

print(
    "Router point capture:",
    f"{router_point * 100:.2f}%"
)

print(
    "Random expectation:",
    f"{random_fraction * 100:.2f}%"
)

print(
    "Point difference:",
    f"{point_difference * 100:.2f}",
    "percentage points"
)

print(
    "Bootstrap difference 95% CI:",
    f"[{rr_ci_low * 100:.2f}, "
    f"{rr_ci_high * 100:.2f}]"
)

print(
    "Bootstrap p-value:",
    rr_p
)

print(
    "Bootstrap probability router > random:",
    f"{np.mean(router_random_diff > 0) * 100:.2f}%"
)

# ============================================================
# 8. ROUTER LIFT DISTRIBUTION
# ============================================================

router_lift = (
    router_values
    / random_fraction
)

lift_point = (
    router_point
    / random_fraction
)

lift_low = np.percentile(
    router_lift,
    2.5
)

lift_high = np.percentile(
    router_lift,
    97.5
)

print("\nRouter lift over random:")
print(
    "Point estimate:",
    f"{lift_point:.3f}x"
)

print(
    "95% bootstrap CI:",
    f"[{lift_low:.3f}, "
    f"{lift_high:.3f}]"
)

# ============================================================
# 9. SAVE RESULTS
# ============================================================

point_file = (
    OUTPUT_DIR
    / "final_test_bootstrap_point_estimates.csv"
)

ci_file = (
    OUTPUT_DIR
    / "final_test_bootstrap_confidence_intervals.csv"
)

comparison_file = (
    OUTPUT_DIR
    / "final_test_bootstrap_paired_comparisons.csv"
)

raw_file = (
    OUTPUT_DIR
    / "final_test_bootstrap_raw.csv"
)

router_random_file = (
    OUTPUT_DIR
    / "final_test_router_vs_random_bootstrap.csv"
)

point_df.to_csv(
    point_file,
    index=False
)

ci_df.to_csv(
    ci_file,
    index=False
)

comparison_df.to_csv(
    comparison_file,
    index=False
)

bootstrap_df.to_csv(
    raw_file,
    index=False
)

pd.DataFrame({
    "metric": [
        "router_capture",
        "random_expected_capture",
        "absolute_difference",
        "difference_ci_lower",
        "difference_ci_upper",
        "bootstrap_p_value",
        "lift_over_random",
        "lift_ci_lower",
        "lift_ci_upper"
    ],
    "value": [
        router_point,
        random_fraction,
        point_difference,
        rr_ci_low,
        rr_ci_high,
        rr_p,
        lift_point,
        lift_low,
        lift_high
    ]
}).to_csv(
    router_random_file,
    index=False
)

print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print(point_file)
print(ci_file)
print(comparison_file)
print(raw_file)
print(router_random_file)

print("\n" + "=" * 80)
print("PHASE 8.1 COMPLETE")
print("=" * 80)