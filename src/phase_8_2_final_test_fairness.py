import numpy as np
import pandas as pd
from pathlib import Path

from scipy.stats import (
    fisher_exact,
    chi2_contingency,
    spearmanr
)

from statsmodels.stats.proportion import (
    proportion_confint
)

# ============================================================
# PHASE 8.2
# FINAL TEST FAIRNESS AUDIT
# Frozen Rescue Router — Locked 15% Budget
# ============================================================

INPUT_FILE = Path(
    "results/eligible/final_test_router_predictions.csv"
)

OUTPUT_DIR = Path("results/eligible")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LOCKED_BUDGET = 0.15

print("=" * 80)
print("PHASE 8.2 — FINAL TEST FAIRNESS AUDIT")
print("=" * 80)

# ============================================================
# 1. LOAD FINAL TEST ROUTER PREDICTIONS
# ============================================================

df = pd.read_csv(INPUT_FILE)

print("\nDataset shape:", df.shape)

required = [
    "encounter_id",
    "actual_30d",
    "predicted_30d",
    "fn_router_probability",
    "gender",
    "race",
    "age"
]

missing = [
    c for c in required
    if c not in df.columns
]

assert not missing, (
    f"Missing required columns: {missing}"
)

assert (
    df["predicted_30d"] == 0
).all(), (
    "Input should contain only low-risk patients."
)

# False-negative indicator
df["router_target"] = (
    df["actual_30d"] == 1
).astype(int)

N = len(df)
TOTAL_FN = int(
    df["router_target"].sum()
)

N_REVIEW = int(
    np.floor(
        N * LOCKED_BUDGET
    )
)

print("Low-risk test patients:", N)
print("Total false negatives:", TOTAL_FN)
print("Locked review budget:", LOCKED_BUDGET)
print("Patients reviewed:", N_REVIEW)

# ============================================================
# 2. RECONSTRUCT FROZEN ROUTER SELECTION
# ============================================================

# Router score is continuous enough that tie ambiguity
# should be minimal, but encounter_id is included as a
# deterministic secondary key for reproducibility.

ranked = df.sort_values(
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

ranked["selected_for_review"] = 0

ranked.iloc[
    :N_REVIEW,
    ranked.columns.get_loc(
        "selected_for_review"
    )
] = 1

fn = ranked[
    ranked["router_target"] == 1
].copy()

rescued_total = int(
    fn["selected_for_review"].sum()
)

print("\n" + "=" * 80)
print("LOCKED TEST OPERATING POINT")
print("=" * 80)

print("False negatives:", TOTAL_FN)
print("Rescued false negatives:", rescued_total)

print(
    "Overall FN rescue rate:",
    f"{rescued_total / TOTAL_FN:.4f}",
    f"({100 * rescued_total / TOTAL_FN:.2f}%)"
)

# Integrity check against Phase 7.9
assert rescued_total == 110, (
    "Expected 110 rescued FNs from frozen Phase 7.9 result."
)

# ============================================================
# 3. WILSON CONFIDENCE INTERVAL HELPER
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
# 4. SUBGROUP RESCUE RATES
# ============================================================

print("\n" + "=" * 80)
print("SUBGROUP FALSE-NEGATIVE RESCUE RATES")
print("=" * 80)

features = [
    "gender",
    "race",
    "age"
]

subgroup_rows = []

for feature in features:

    temp = fn.copy()

    # Preserve missing demographic values explicitly
    temp[feature] = (
        temp[feature]
        .fillna("Missing")
        .astype(str)
    )

    for group, subset in temp.groupby(
        feature
    ):

        total_fn = len(subset)

        rescued_fn = int(
            subset[
                "selected_for_review"
            ].sum()
        )

        missed_fn = (
            total_fn
            - rescued_fn
        )

        rescue_rate = (
            rescued_fn
            / total_fn
        )

        ci_low, ci_high = wilson_ci(
            rescued_fn,
            total_fn
        )

        subgroup_rows.append({
            "feature": feature,
            "group": group,

            "total_false_negatives":
                total_fn,

            "rescued_false_negatives":
                rescued_fn,

            "missed_false_negatives":
                missed_fn,

            "fn_rescue_rate":
                rescue_rate,

            "ci_lower":
                ci_low,

            "ci_upper":
                ci_high
        })


subgroup_df = pd.DataFrame(
    subgroup_rows
)

for feature in features:

    print("\n" + "-" * 80)
    print(feature.upper())
    print("-" * 80)

    display = subgroup_df[
        subgroup_df["feature"] == feature
    ].copy()

    for col in [
        "fn_rescue_rate",
        "ci_lower",
        "ci_upper"
    ]:
        display[col] = (
            display[col] * 100
        )

    print(
        display.to_string(
            index=False
        )
    )

# ============================================================
# 5. GENDER — FEMALE VS MALE
# ============================================================

print("\n" + "=" * 80)
print("GENDER COMPARISON")
print("=" * 80)

gender_fn = fn[
    fn["gender"].isin(
        ["Female", "Male"]
    )
].copy()

gender_table = pd.crosstab(
    gender_fn["gender"],
    gender_fn["selected_for_review"]
)

print("\nContingency table:")
print(gender_table)

if (
    "Female" in gender_table.index
    and "Male" in gender_table.index
    and 0 in gender_table.columns
    and 1 in gender_table.columns
):

    female_missed = int(
        gender_table.loc[
            "Female", 0
        ]
    )

    female_rescued = int(
        gender_table.loc[
            "Female", 1
        ]
    )

    male_missed = int(
        gender_table.loc[
            "Male", 0
        ]
    )

    male_rescued = int(
        gender_table.loc[
            "Male", 1
        ]
    )

    table = np.array([
        [
            female_rescued,
            female_missed
        ],
        [
            male_rescued,
            male_missed
        ]
    ])

    odds_ratio, p_value = (
        fisher_exact(table)
    )

    female_rate = (
        female_rescued
        / (
            female_rescued
            + female_missed
        )
    )

    male_rate = (
        male_rescued
        / (
            male_rescued
            + male_missed
        )
    )

    gender_gap = (
        female_rate
        - male_rate
    )

    print(
        "\nFemale rescue rate:",
        f"{female_rate * 100:.2f}%"
    )

    print(
        "Male rescue rate:",
        f"{male_rate * 100:.2f}%"
    )

    print(
        "Female - Male gap:",
        f"{gender_gap * 100:.2f}",
        "percentage points"
    )

    print(
        "Fisher odds ratio:",
        odds_ratio
    )

    print(
        "Fisher p-value:",
        p_value
    )

# ============================================================
# 6. RACE — OVERALL ASSOCIATION
# ============================================================

print("\n" + "=" * 80)
print("RACE — OVERALL ASSOCIATION")
print("=" * 80)

race_fn = fn.copy()

race_fn["race"] = (
    race_fn["race"]
    .fillna("Missing")
    .astype(str)
)

race_table = pd.crosstab(
    race_fn["race"],
    race_fn["selected_for_review"]
)

print("\nContingency table:")
print(race_table)

chi2, race_p, dof, expected = (
    chi2_contingency(
        race_table.values
    )
)

print("\nChi-square:", chi2)
print("Degrees of freedom:", dof)
print("p-value:", race_p)

print(
    "Expected cells < 5:",
    int(
        (expected < 5).sum()
    )
)

print(
    "Minimum expected count:",
    expected.min()
)

# ============================================================
# 7. PRIMARY RACE COMPARISON
# AFRICAN AMERICAN VS CAUCASIAN
# ============================================================

print("\n" + "=" * 80)
print("RACE — AFRICAN AMERICAN VS CAUCASIAN")
print("=" * 80)

race_pair = race_fn[
    race_fn["race"].isin(
        [
            "AfricanAmerican",
            "Caucasian"
        ]
    )
].copy()

aa = race_pair[
    race_pair["race"]
    == "AfricanAmerican"
]

cauc = race_pair[
    race_pair["race"]
    == "Caucasian"
]

aa_total = len(aa)
aa_rescued = int(
    aa[
        "selected_for_review"
    ].sum()
)

cauc_total = len(cauc)
cauc_rescued = int(
    cauc[
        "selected_for_review"
    ].sum()
)

aa_rate = (
    aa_rescued / aa_total
)

cauc_rate = (
    cauc_rescued
    / cauc_total
)

race_gap = (
    aa_rate
    - cauc_rate
)

race_table_pair = np.array([
    [
        aa_rescued,
        aa_total - aa_rescued
    ],
    [
        cauc_rescued,
        cauc_total - cauc_rescued
    ]
])

race_or, race_pair_p = (
    fisher_exact(
        race_table_pair
    )
)

aa_ci = wilson_ci(
    aa_rescued,
    aa_total
)

cauc_ci = wilson_ci(
    cauc_rescued,
    cauc_total
)

print(
    "African American:",
    f"{aa_rescued}/{aa_total}",
    f"= {aa_rate * 100:.2f}%"
)

print(
    "95% CI:",
    f"[{aa_ci[0] * 100:.2f}, "
    f"{aa_ci[1] * 100:.2f}]"
)

print(
    "\nCaucasian:",
    f"{cauc_rescued}/{cauc_total}",
    f"= {cauc_rate * 100:.2f}%"
)

print(
    "95% CI:",
    f"[{cauc_ci[0] * 100:.2f}, "
    f"{cauc_ci[1] * 100:.2f}]"
)

print(
    "\nAfrican American - Caucasian gap:",
    f"{race_gap * 100:.2f}",
    "percentage points"
)

print(
    "Fisher odds ratio:",
    race_or
)

print(
    "Fisher p-value:",
    race_pair_p
)

# ============================================================
# 8. AGE ANALYSIS
# ============================================================

print("\n" + "=" * 80)
print("AGE ANALYSIS")
print("=" * 80)

age_order = [
    "[0-10)",
    "[10-20)",
    "[20-30)",
    "[30-40)",
    "[40-50)",
    "[50-60)",
    "[60-70)",
    "[70-80)",
    "[80-90)",
    "[90-100)"
]

age_midpoints = {
    "[0-10)": 5,
    "[10-20)": 15,
    "[20-30)": 25,
    "[30-40)": 35,
    "[40-50)": 45,
    "[50-60)": 55,
    "[60-70)": 65,
    "[70-80)": 75,
    "[80-90)": 85,
    "[90-100)": 95
}

age_fn = fn[
    fn["age"].isin(
        age_order
    )
].copy()

age_table = pd.crosstab(
    age_fn["age"],
    age_fn["selected_for_review"]
)

age_table = age_table.reindex(
    [
        a for a in age_order
        if a in age_table.index
    ]
)

print("\nAge contingency table:")
print(age_table)

age_chi2, age_p, age_dof, age_expected = (
    chi2_contingency(
        age_table.values
    )
)

print(
    "\nChi-square:",
    age_chi2
)

print(
    "Degrees of freedom:",
    age_dof
)

print(
    "p-value:",
    age_p
)

print(
    "Expected cells < 5:",
    int(
        (age_expected < 5).sum()
    )
)

# ------------------------------------------------------------
# Spearman age trend
#
# Patient-level analysis:
# age midpoint vs review selection among false negatives.
# ------------------------------------------------------------

age_fn["age_midpoint"] = (
    age_fn["age"]
    .map(age_midpoints)
)

rho, age_trend_p = spearmanr(
    age_fn["age_midpoint"],
    age_fn["selected_for_review"]
)

print(
    "\nSpearman age-selection correlation:",
    rho
)

print(
    "Spearman p-value:",
    age_trend_p
)

# ============================================================
# 9. STABLE-GROUP GAP SUMMARY
#
# Only groups with >=20 false negatives are used
# for descriptive max-min gaps.
# ============================================================

print("\n" + "=" * 80)
print("STABLE SUBGROUP GAP SUMMARY")
print("=" * 80)

gap_rows = []

for feature in features:

    subset = subgroup_df[
        subgroup_df["feature"]
        == feature
    ].copy()

    stable = subset[
        subset[
            "total_false_negatives"
        ] >= 20
    ].copy()

    if len(stable) < 2:
        continue

    highest = stable.loc[
        stable[
            "fn_rescue_rate"
        ].idxmax()
    ]

    lowest = stable.loc[
        stable[
            "fn_rescue_rate"
        ].idxmin()
    ]

    gap = (
        highest[
            "fn_rescue_rate"
        ]
        - lowest[
            "fn_rescue_rate"
        ]
    )

    gap_rows.append({
        "feature": feature,

        "highest_group":
            highest["group"],

        "highest_rate":
            highest[
                "fn_rescue_rate"
            ],

        "lowest_group":
            lowest["group"],

        "lowest_rate":
            lowest[
                "fn_rescue_rate"
            ],

        "absolute_gap":
            gap
    })


gap_df = pd.DataFrame(
    gap_rows
)

display_gap = gap_df.copy()

for c in [
    "highest_rate",
    "lowest_rate",
    "absolute_gap"
]:
    display_gap[c] = (
        display_gap[c] * 100
    )

print(
    display_gap.to_string(
        index=False
    )
)

# ============================================================
# 10. SAVE SUMMARY TESTS
# ============================================================

summary_rows = []

summary_rows.append({
    "comparison":
        "Female vs Male",

    "group_1_rate":
        female_rate,

    "group_2_rate":
        male_rate,

    "absolute_difference":
        gender_gap,

    "odds_ratio":
        odds_ratio,

    "p_value":
        p_value,

    "test":
        "Fisher exact"
})

summary_rows.append({
    "comparison":
        "AfricanAmerican vs Caucasian",

    "group_1_rate":
        aa_rate,

    "group_2_rate":
        cauc_rate,

    "absolute_difference":
        race_gap,

    "odds_ratio":
        race_or,

    "p_value":
        race_pair_p,

    "test":
        "Fisher exact"
})

summary_rows.append({
    "comparison":
        "Race overall",

    "group_1_rate":
        np.nan,

    "group_2_rate":
        np.nan,

    "absolute_difference":
        np.nan,

    "odds_ratio":
        np.nan,

    "p_value":
        race_p,

    "test":
        "Chi-square"
})

summary_rows.append({
    "comparison":
        "Age overall",

    "group_1_rate":
        np.nan,

    "group_2_rate":
        np.nan,

    "absolute_difference":
        np.nan,

    "odds_ratio":
        np.nan,

    "p_value":
        age_p,

    "test":
        "Chi-square"
})

summary_rows.append({
    "comparison":
        "Age trend",

    "group_1_rate":
        np.nan,

    "group_2_rate":
        np.nan,

    "absolute_difference":
        rho,

    "odds_ratio":
        np.nan,

    "p_value":
        age_trend_p,

    "test":
        "Spearman"
})

summary_df = pd.DataFrame(
    summary_rows
)

# ============================================================
# 11. SAVE FILES
# ============================================================

subgroup_file = (
    OUTPUT_DIR
    / "final_test_fairness_subgroup_rates.csv"
)

summary_file = (
    OUTPUT_DIR
    / "final_test_fairness_statistical_tests.csv"
)

gap_file = (
    OUTPUT_DIR
    / "final_test_fairness_gap_summary.csv"
)

subgroup_df.to_csv(
    subgroup_file,
    index=False
)

summary_df.to_csv(
    summary_file,
    index=False
)

gap_df.to_csv(
    gap_file,
    index=False
)

print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print(subgroup_file)
print(summary_file)
print(gap_file)

print("\n" + "=" * 80)
print("PHASE 8.2 COMPLETE")
print("=" * 80)