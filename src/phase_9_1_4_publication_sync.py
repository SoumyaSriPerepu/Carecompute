from pathlib import Path
import pandas as pd
import numpy as np

# ============================================================
# PHASE 9.1.4 — CANONICAL PUBLICATION SYNCHRONIZATION
# ============================================================

RESULTS = Path("results/eligible")
OUT = RESULTS / "publication"
OUT.mkdir(parents=True, exist_ok=True)

LOCKED_FILE = RESULTS / "canonical_locked_15pct_results.csv"
BOOT_FILE = RESULTS / "canonical_bootstrap_confidence_intervals.csv"
PAIR_FILE = RESULTS / "canonical_bootstrap_paired_comparisons.csv"

print("=" * 80)
print("PHASE 9.1.4 — CANONICAL PUBLICATION SYNCHRONIZATION")
print("=" * 80)

# ------------------------------------------------------------
# 1. LOAD CANONICAL FILES
# ------------------------------------------------------------

locked = pd.read_csv(LOCKED_FILE)
boot = pd.read_csv(BOOT_FILE)
paired = pd.read_csv(PAIR_FILE)

print("\nCanonical files loaded successfully.")

print("\nLOCKED RESULTS")
print(locked.to_string(index=False))

print("\nBOOTSTRAP RESULTS")
print(boot.to_string(index=False))

print("\nPAIRED COMPARISONS")
print(paired.to_string(index=False))


# ------------------------------------------------------------
# 2. EXPECTED CANONICAL VALUES
# ------------------------------------------------------------

expected = {
    "Probability": 20.813356,
    "Rescue Router": 19.748654,
    "Disagreement": 18.312388,
    "Random": 14.991092,
}

print("\n" + "=" * 80)
print("A — CANONICAL VALUE CHECK")
print("=" * 80)

all_passed = True

for method, expected_value in expected.items():

    row = locked.loc[locked["method"] == method]

    if len(row) != 1:
        print(f"{method}: FAILED — expected exactly one row")
        all_passed = False
        continue

    observed = float(row.iloc[0]["fn_capture_percent"])

    passed = np.isclose(
        observed,
        expected_value,
        atol=1e-5
    )

    print(
        f"{method:15s} "
        f"observed={observed:.6f}% "
        f"expected={expected_value:.6f}% "
        f"{'PASSED' if passed else 'FAILED'}"
    )

    if not passed:
        all_passed = False


# ------------------------------------------------------------
# 3. PUBLICATION TABLE 2
# Locked 15% operating point
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("B — PUBLICATION TABLE 2")
print("=" * 80)

table2 = locked[
    [
        "method",
        "patients_reviewed",
        "expected_fn_captured",
        "fn_capture_percent",
        "review_precision_percent",
        "tie_rule",
    ]
].copy()

table2 = table2.rename(
    columns={
        "method": "Review Strategy",
        "patients_reviewed": "Patients Reviewed",
        "expected_fn_captured": "Expected FN Captured",
        "fn_capture_percent": "FN Capture Rate (%)",
        "review_precision_percent": "Review Precision (%)",
        "tie_rule": "Ranking / Tie Rule",
    }
)

order = [
    "Probability",
    "Rescue Router",
    "Disagreement",
    "Random",
]

table2["Review Strategy"] = pd.Categorical(
    table2["Review Strategy"],
    categories=order,
    ordered=True,
)

table2 = table2.sort_values("Review Strategy").reset_index(drop=True)

print(table2.to_string(index=False))

table2.to_csv(
    OUT / "table_2_canonical_locked_results.csv",
    index=False
)


# ------------------------------------------------------------
# 4. PUBLICATION TABLE 3A
# Bootstrap confidence intervals
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("C — PUBLICATION TABLE 3A")
print("=" * 80)

table3a = boot.copy()
# Bootstrap file stores rates as proportions.
# Convert to percentages for publication display.
for col in [
    "point_estimate",
    "bootstrap_mean",
    "ci_lower",
    "ci_upper",
]:
    table3a[col] = table3a[col] * 100


table3a = table3a.rename(
    columns={
        "method": "Review Strategy",
        "point_estimate": "Point FN Capture (%)",
        "bootstrap_mean": "Bootstrap Mean (%)",
        "ci_lower": "95% CI Lower (%)",
        "ci_upper": "95% CI Upper (%)",
    }
)

table3a["Review Strategy"] = pd.Categorical(
    table3a["Review Strategy"],
    categories=order,
    ordered=True,
)

table3a = table3a.sort_values(
    "Review Strategy"
).reset_index(drop=True)

print(table3a.to_string(index=False))

table3a.to_csv(
    OUT / "table_3a_canonical_bootstrap_ci.csv",
    index=False
)


# ------------------------------------------------------------
# 5. PUBLICATION TABLE 3B
# Paired bootstrap comparisons
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("D — PUBLICATION TABLE 3B")
print("=" * 80)

table3b = paired.copy()

# Convert proportion differences to percentage points
for col in [
    "mean_difference",
    "ci_lower",
    "ci_upper",
]:
    table3b[col] = table3b[col] * 100

# Convert probabilities to percentages for display
for col in [
    "probability_a_better",
    "probability_equal",
    "probability_a_worse",
]:
    table3b[col] = table3b[col] * 100

rename_map = {
    "comparison": "Comparison",
    "mean_difference": "Bootstrap Mean Difference (pp)",
    "ci_lower": "95% CI Lower (pp)",
    "ci_upper": "95% CI Upper (pp)",
    "bootstrap_p_value": "Bootstrap p-value",
    "probability_a_better": "P(A Better) (%)",
    "probability_equal": "P(Equal) (%)",
    "probability_a_worse": "P(A Worse) (%)",
}

table3b = table3b.rename(columns=rename_map)

print(table3b.to_string(index=False))

table3b.to_csv(
    OUT / "table_3b_canonical_paired_bootstrap.csv",
    index=False
)


# ------------------------------------------------------------
# 6. KEY RESULT SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("E — CANONICAL KEY RESULT SUMMARY")
print("=" * 80)

def locked_value(method, column):
    return float(
        locked.loc[
            locked["method"] == method,
            column
        ].iloc[0]
    )


router_capture = locked_value(
    "Rescue Router",
    "fn_capture_percent"
)

prob_capture = locked_value(
    "Probability",
    "fn_capture_percent"
)

dis_capture = locked_value(
    "Disagreement",
    "fn_capture_percent"
)

random_capture = locked_value(
    "Random",
    "fn_capture_percent"
)

router_gain = router_capture - random_capture
router_lift = router_capture / random_capture


def comparison_row(name):
    row = paired.loc[
        paired["comparison"] == name
    ]

    if len(row) != 1:
        raise ValueError(
            f"Expected one paired comparison for: {name}"
        )

    return row.iloc[0]


router_random = comparison_row(
    "Rescue Router vs Random"
)

router_probability = comparison_row(
    "Rescue Router vs Probability"
)

router_disagreement = comparison_row(
    "Rescue Router vs Disagreement"
)


summary = pd.DataFrame(
    [
        {
            "Result": "Probability FN capture at locked 15%",
            "Value": prob_capture,
            "Unit": "%",
        },
        {
            "Result": "Rescue Router FN capture at locked 15%",
            "Value": router_capture,
            "Unit": "%",
        },
        {
            "Result": "Disagreement FN capture at locked 15%",
            "Value": dis_capture,
            "Unit": "%",
        },
        {
            "Result": "Random expected FN capture at locked 15%",
            "Value": random_capture,
            "Unit": "%",
        },
        {
            "Result": "Router absolute gain over random",
            "Value": router_gain,
            "Unit": "percentage points",
        },
        {
            "Result": "Router lift over random",
            "Value": router_lift,
            "Unit": "x",
        },
        {
            "Result": "Router vs random bootstrap p-value",
            "Value": float(
                router_random["bootstrap_p_value"]
            ),
            "Unit": "p-value",
        },
        {
            "Result": "Router vs probability bootstrap p-value",
            "Value": float(
                router_probability["bootstrap_p_value"]
            ),
            "Unit": "p-value",
        },
        {
            "Result": "Router vs disagreement bootstrap p-value",
            "Value": float(
                router_disagreement["bootstrap_p_value"]
            ),
            "Unit": "p-value",
        },
    ]
)

print(summary.to_string(index=False))

summary.to_csv(
    OUT / "canonical_key_results.csv",
    index=False
)


# ------------------------------------------------------------
# 7. PUBLICATION-READY TEXT VALUES
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("F — PUBLICATION-READY RESULTS")
print("=" * 80)

print(
    f"""
Locked operating point:
15% of the low-risk population.

Probability:
FN capture = {prob_capture:.2f}%

Rescue Router:
FN capture = {router_capture:.2f}%

Disagreement:
FN capture = {dis_capture:.2f}%

Random expectation:
FN capture = {random_capture:.2f}%

Rescue Router vs Random:
Absolute gain = {router_gain:.2f} percentage points
Lift = {router_lift:.3f}x
95% CI for difference =
[{router_random['ci_lower'] * 100:.2f},
 {router_random['ci_upper'] * 100:.2f}] pp
p = {router_random['bootstrap_p_value']:.4f}

Rescue Router vs Probability:
p = {router_probability['bootstrap_p_value']:.4f}

Rescue Router vs Disagreement:
p = {router_disagreement['bootstrap_p_value']:.4f}
"""
)


# ------------------------------------------------------------
# 8. FINAL CONSISTENCY ASSERTIONS
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("G — FINAL CONSISTENCY ASSERTIONS")
print("=" * 80)

checks = []

# Locked values
for method, expected_value in expected.items():

    observed = locked_value(
        method,
        "fn_capture_percent"
    )

    checks.append(
        (
            f"{method} canonical locked value",
            np.isclose(
                observed,
                expected_value,
                atol=1e-5
            )
        )
    )


# Bootstrap point estimates must match canonical locked results
for method in order:

    locked_point = locked_value(
        method,
        "fn_capture_percent"
    )

    boot_row = boot.loc[
        boot["method"] == method
    ]

    if len(boot_row) != 1:
        checks.append(
            (
                f"{method} bootstrap row exists",
                False
            )
        )
        continue

    boot_point = float(
    boot_row.iloc[0]["point_estimate"]
    ) * 100

    checks.append(
    (
        f"{method} bootstrap point matches locked",
        np.isclose(
            locked_point,
            boot_point,
            atol=1e-5
        )
    )
)


# Router effect
checks.append(
    (
        "Router > random",
        router_capture > random_capture
    )
)

checks.append(
    (
        "Router-vs-random CI excludes zero",
        (
            float(router_random["ci_lower"]) > 0
            and
            float(router_random["ci_upper"]) > 0
        )
    )
)

checks.append(
    (
        "Router-vs-random p < 0.05",
        float(
            router_random["bootstrap_p_value"]
        ) < 0.05
    )
)


failed = []

for name, passed in checks:

    print(
        f"{name}: "
        f"{'PASSED' if passed else 'FAILED'}"
    )

    if not passed:
        failed.append(name)


# ------------------------------------------------------------
# 9. FINAL STATUS
# ------------------------------------------------------------

print("\n" + "=" * 80)

if all_passed and len(failed) == 0:

    print(
        "PUBLICATION CONSISTENCY STATUS: PASSED"
    )

    print(
        "Canonical locked and bootstrap results are synchronized."
    )

else:

    print(
        "PUBLICATION CONSISTENCY STATUS: FAILED"
    )

    print("\nProblems:")

    for item in failed:
        print(" -", item)

print("=" * 80)


print("\nFILES SAVED")
print("=" * 80)

for f in sorted(OUT.glob("*.csv")):
    print(f)

print("\n" + "=" * 80)
print("PHASE 9.1.4 COMPLETE")
print("=" * 80)