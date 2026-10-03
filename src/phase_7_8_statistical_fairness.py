import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import mannwhitneyu, chi2_contingency, fisher_exact
from statsmodels.stats.proportion import proportion_confint

# ============================================================
# PHASE 7.8
# Statistical Characterization + Fairness Analysis
# ============================================================

INPUT_FILE = Path(
    "results/eligible/rescue_error_analysis_patients.csv"
)

OUTPUT_DIR = Path("results/eligible")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALPHA = 0.05

print("=" * 78)
print("PHASE 7.8 — STATISTICAL CHARACTERIZATION + FAIRNESS")
print("=" * 78)

# ------------------------------------------------------------
# Load Phase 7.7 patient-level results
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

fn_df = df[df["router_target"] == 1].copy()

rescued = fn_df[
    fn_df["selected_for_review"] == 1
].copy()

missed = fn_df[
    fn_df["selected_for_review"] == 0
].copy()

print("\nTotal low-risk patients:", len(df))
print("Total false negatives:", len(fn_df))
print("Rescued false negatives:", len(rescued))
print("Missed false negatives:", len(missed))

print(
    "Overall FN rescue rate:",
    f"{len(rescued) / len(fn_df):.4f}",
    f"({100 * len(rescued) / len(fn_df):.2f}%)"
)

# ============================================================
# PART A
# RESCUED FN VS MISSED FN — STATISTICAL TESTS
# ============================================================

print("\n" + "=" * 78)
print("PART A — RESCUED FN VS MISSED FN")
print("=" * 78)

numeric_features = [
    "calibrated_probability",
    "model_disagreement_std",
    "number_inpatient",
    "number_emergency",
    "number_outpatient",
    "number_diagnoses",
    "time_in_hospital"
]


def rank_biserial_from_u(u, n1, n2):
    """
    Rank-biserial correlation derived from Mann-Whitney U.

    Positive value:
        rescued group tends to have larger values.

    Negative value:
        missed group tends to have larger values.
    """
    return (2 * u) / (n1 * n2) - 1


stat_rows = []

for feature in numeric_features:

    rescued_values = (
        rescued[feature]
        .dropna()
        .astype(float)
    )

    missed_values = (
        missed[feature]
        .dropna()
        .astype(float)
    )

    u_stat, p_value = mannwhitneyu(
        rescued_values,
        missed_values,
        alternative="two-sided"
    )

    effect_size = rank_biserial_from_u(
        u_stat,
        len(rescued_values),
        len(missed_values)
    )

    stat_rows.append({
        "feature": feature,

        "rescued_n": len(rescued_values),
        "missed_n": len(missed_values),

        "rescued_mean": rescued_values.mean(),
        "missed_mean": missed_values.mean(),

        "rescued_median": rescued_values.median(),
        "missed_median": missed_values.median(),

        "mean_difference":
            rescued_values.mean()
            - missed_values.mean(),

        "mann_whitney_u": u_stat,
        "p_value": p_value,

        "rank_biserial_effect":
            effect_size
    })


stats_df = pd.DataFrame(stat_rows)

# ------------------------------------------------------------
# Multiple-comparison correction
# Benjamini-Hochberg FDR
# ------------------------------------------------------------

stats_df = stats_df.sort_values(
    "p_value"
).reset_index(drop=True)

m = len(stats_df)

stats_df["bh_rank"] = np.arange(1, m + 1)

stats_df["bh_adjusted_p"] = (
    stats_df["p_value"]
    * m
    / stats_df["bh_rank"]
)

# Enforce monotonic BH adjusted p-values
stats_df["bh_adjusted_p"] = (
    stats_df["bh_adjusted_p"]
    [::-1]
    .cummin()
    [::-1]
    .clip(upper=1.0)
)

stats_df["significant_fdr_0.05"] = (
    stats_df["bh_adjusted_p"] < ALPHA
)

print("\nStatistical comparison:")
print(stats_df.to_string(index=False))


# ============================================================
# PART B
# SUBGROUP FN RESCUE RATES
# ============================================================

print("\n" + "=" * 78)
print("PART B — SUBGROUP FALSE-NEGATIVE RESCUE RATES")
print("=" * 78)

demographic_features = [
    "gender",
    "race",
    "age"
]

fairness_rows = []

for feature in demographic_features:

    print("\n" + "-" * 78)
    print(feature.upper())
    print("-" * 78)

    groups = (
        fn_df[feature]
        .dropna()
        .unique()
    )

    for group in sorted(groups):

        subgroup = fn_df[
            fn_df[feature] == group
        ]

        total_fn = len(subgroup)

        rescued_fn = int(
            subgroup["selected_for_review"].sum()
        )

        missed_fn = total_fn - rescued_fn

        rescue_rate = (
            rescued_fn / total_fn
            if total_fn > 0
            else np.nan
        )

        # Wilson confidence interval
        ci_low, ci_high = proportion_confint(
            count=rescued_fn,
            nobs=total_fn,
            alpha=0.05,
            method="wilson"
        )

        fairness_rows.append({
            "feature": feature,
            "group": group,
            "total_false_negatives": total_fn,
            "rescued_false_negatives": rescued_fn,
            "missed_false_negatives": missed_fn,
            "fn_rescue_rate": rescue_rate,
            "ci_lower": ci_low,
            "ci_upper": ci_high
        })


fairness_df = pd.DataFrame(
    fairness_rows
)

for feature in demographic_features:

    print(
        "\n",
        fairness_df[
            fairness_df["feature"] == feature
        ].to_string(index=False)
    )


# ============================================================
# PART C
# TEST WHETHER RESCUE STATUS DIFFERS BY DEMOGRAPHIC GROUP
# ============================================================

print("\n" + "=" * 78)
print("PART C — DEMOGRAPHIC ASSOCIATION TESTS")
print("=" * 78)

association_rows = []

for feature in demographic_features:

    temp = fn_df[
        [feature, "selected_for_review"]
    ].dropna()

    contingency = pd.crosstab(
        temp[feature],
        temp["selected_for_review"]
    )

    # Remove groups with no observations
    contingency = contingency.loc[
        contingency.sum(axis=1) > 0
    ]

    print("\n", feature.upper())
    print(contingency)

    # --------------------------------------------------------
    # Gender:
    # 2x2 table → Fisher's exact test
    # --------------------------------------------------------

    if contingency.shape == (2, 2):

        odds_ratio, p_value = fisher_exact(
            contingency.values
        )

        test_used = "Fisher exact"

        association_rows.append({
            "feature": feature,
            "test": test_used,
            "statistic": odds_ratio,
            "p_value": p_value
        })

        print(
            "\nTest:",
            test_used
        )

        print(
            "Odds ratio:",
            odds_ratio
        )

        print(
            "p-value:",
            p_value
        )

    # --------------------------------------------------------
    # More than two groups:
    # Chi-square association test
    # --------------------------------------------------------

    else:

        chi2, p_value, dof, expected = (
            chi2_contingency(
                contingency.values
            )
        )

        test_used = "Chi-square"

        association_rows.append({
            "feature": feature,
            "test": test_used,
            "statistic": chi2,
            "degrees_of_freedom": dof,
            "p_value": p_value
        })

        print(
            "\nTest:",
            test_used
        )

        print(
            "Chi-square:",
            chi2
        )

        print(
            "Degrees of freedom:",
            dof
        )

        print(
            "p-value:",
            p_value
        )

        # Warn if expected counts are small
        small_expected = (
            expected < 5
        ).sum()

        print(
            "Expected cells < 5:",
            small_expected
        )


association_df = pd.DataFrame(
    association_rows
)


# ============================================================
# PART D
# OVERALL FAIRNESS SUMMARY
# ============================================================

print("\n" + "=" * 78)
print("PART D — FAIRNESS SUMMARY")
print("=" * 78)

for feature in demographic_features:

    subset = fairness_df[
        fairness_df["feature"] == feature
    ].copy()

    # Avoid interpreting tiny groups too strongly
    stable = subset[
        subset["total_false_negatives"] >= 20
    ]

    print("\n", feature.upper())

    if len(stable) == 0:
        print(
            "No subgroup has >=20 false negatives."
        )
        continue

    highest = stable.loc[
        stable["fn_rescue_rate"].idxmax()
    ]

    lowest = stable.loc[
        stable["fn_rescue_rate"].idxmin()
    ]

    gap = (
        highest["fn_rescue_rate"]
        - lowest["fn_rescue_rate"]
    )

    print(
        "Highest rescue rate:",
        highest["group"],
        f"{highest['fn_rescue_rate']:.4f}"
    )

    print(
        "Lowest rescue rate:",
        lowest["group"],
        f"{lowest['fn_rescue_rate']:.4f}"
    )

    print(
        "Absolute gap:",
        f"{gap:.4f}",
        f"({gap * 100:.2f} percentage points)"
    )


# ============================================================
# SAVE RESULTS
# ============================================================

stats_file = (
    OUTPUT_DIR
    / "rescued_vs_missed_fn_statistical_tests.csv"
)

fairness_file = (
    OUTPUT_DIR
    / "fn_rescue_subgroup_rates.csv"
)

association_file = (
    OUTPUT_DIR
    / "fn_rescue_demographic_association_tests.csv"
)

stats_df.to_csv(
    stats_file,
    index=False
)

fairness_df.to_csv(
    fairness_file,
    index=False
)

association_df.to_csv(
    association_file,
    index=False
)


print("\n" + "=" * 78)
print("FILES SAVED")
print("=" * 78)

print(stats_file)
print(fairness_file)
print(association_file)

print("\n" + "=" * 78)
print("PHASE 7.8 COMPLETE")
print("=" * 78)