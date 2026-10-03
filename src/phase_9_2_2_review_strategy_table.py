from pathlib import Path
import pandas as pd
import numpy as np

# ============================================================
# PHASE 9.2.2 — FINAL CANONICAL REVIEW-STRATEGY TABLE
# ============================================================

RESULTS = Path("results/eligible")
PUB = RESULTS / "publication"

INPUT = RESULTS / "canonical_locked_15pct_results.csv"
OUTPUT = PUB / "table_2_final_review_strategies.csv"

PUB.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("PHASE 9.2.2 — FINAL CANONICAL REVIEW-STRATEGY TABLE")
print("=" * 80)

df = pd.read_csv(INPUT)

print("\nInput:")
print(df.to_string(index=False))


# ------------------------------------------------------------
# A. BASIC INTEGRITY
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("A — BASIC INTEGRITY")
print("=" * 80)

expected_methods = {
    "Probability",
    "Rescue Router",
    "Disagreement",
    "Random",
}

observed_methods = set(df["method"])

checks = {
    "Exactly four strategies": len(df) == 4,
    "Expected strategies present":
        observed_methods == expected_methods,
    "All review 1,178 patients":
        (df["patients_reviewed"] == 1178).all(),
}

for name, passed in checks.items():
    print(f"{name}: {'PASSED' if passed else 'FAILED'}")

if not all(checks.values()):
    raise ValueError("Basic integrity check failed.")


# ------------------------------------------------------------
# B. CANONICAL VALUE CHECK
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("B — CANONICAL VALUE CHECK")
print("=" * 80)

expected_capture = {
    "Probability": 20.813356,
    "Rescue Router": 19.748654,
    "Disagreement": 18.312388,
    "Random": 14.991092,
}

for method, expected in expected_capture.items():

    observed = float(
        df.loc[
            df["method"] == method,
            "fn_capture_percent"
        ].iloc[0]
    )

    passed = np.isclose(
        observed,
        expected,
        atol=1e-5
    )

    print(
        f"{method:15s} "
        f"{observed:.6f}% "
        f"{'PASSED' if passed else 'FAILED'}"
    )

    if not passed:
        raise ValueError(
            f"Canonical value mismatch for {method}"
        )


# ------------------------------------------------------------
# C. BUILD FINAL TABLE
# ------------------------------------------------------------

order = [
    "Probability",
    "Rescue Router",
    "Disagreement",
    "Random",
]

table = df.copy()

table["method"] = pd.Categorical(
    table["method"],
    categories=order,
    ordered=True,
)

table = table.sort_values("method").reset_index(drop=True)

table = table[
    [
        "method",
        "patients_reviewed",
        "expected_fn_captured",
        "fn_capture_percent",
        "review_precision_percent",
        "tie_rule",
    ]
]

table = table.rename(
    columns={
        "method": "Review Strategy",
        "patients_reviewed": "Patients Reviewed",
        "expected_fn_captured": "FN Captured",
        "fn_capture_percent": "FN Capture Rate (%)",
        "review_precision_percent": "Review Precision (%)",
        "tie_rule": "Ranking / Tie Rule",
    }
)

# Publication-friendly rounding
table["FN Captured"] = table["FN Captured"].round(2)
table["FN Capture Rate (%)"] = (
    table["FN Capture Rate (%)"].round(2)
)
table["Review Precision (%)"] = (
    table["Review Precision (%)"].round(2)
)

print("\n" + "=" * 80)
print("C — FINAL TABLE 2")
print("=" * 80)

print(table.to_string(index=False))


# ------------------------------------------------------------
# D. EFFECT RELATIVE TO RANDOM
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("D — EFFECT RELATIVE TO RANDOM")
print("=" * 80)

def get_capture(method):
    return float(
        df.loc[
            df["method"] == method,
            "fn_capture_percent"
        ].iloc[0]
    )

router = get_capture("Rescue Router")
probability = get_capture("Probability")
disagreement = get_capture("Disagreement")
random = get_capture("Random")

router_gain = router - random
router_lift = router / random

probability_gain = probability - random
disagreement_gain = disagreement - random

print(
    f"Probability vs random: "
    f"+{probability_gain:.2f} pp"
)

print(
    f"Rescue Router vs random: "
    f"+{router_gain:.2f} pp"
)

print(
    f"Disagreement vs random: "
    f"+{disagreement_gain:.2f} pp"
)

print(
    f"Rescue Router lift over random: "
    f"{router_lift:.3f}x"
)


# ------------------------------------------------------------
# E. IMPORTANT TIE CHECK
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("E — PROBABILITY TIE RULE CHECK")
print("=" * 80)

prob_row = df.loc[
    df["method"] == "Probability"
].iloc[0]

prob_rule = str(prob_row["tie_rule"])

correct_tie_rule = (
    "Expected random selection within cutoff tie"
)

tie_passed = prob_rule == correct_tie_rule

print("Probability rule:", prob_rule)

print(
    "Canonical probability tie rule:",
    "PASSED" if tie_passed else "FAILED"
)

if not tie_passed:
    raise ValueError(
        "Probability tie rule is not canonical."
    )


# ------------------------------------------------------------
# F. SAVE
# ------------------------------------------------------------

table.to_csv(OUTPUT, index=False)

print("\n" + "=" * 80)
print("F — MANUSCRIPT VALUES")
print("=" * 80)

print(f"Probability:    {probability:.2f}%")
print(f"Rescue Router:  {router:.2f}%")
print(f"Disagreement:   {disagreement:.2f}%")
print(f"Random:         {random:.2f}%")

print()
print(
    f"Router absolute gain over random: "
    f"{router_gain:.2f} pp"
)

print(
    f"Router lift over random: "
    f"{router_lift:.3f}x"
)

print("\n" + "=" * 80)
print("FILE SAVED")
print("=" * 80)

print(OUTPUT)

print("\n" + "=" * 80)
print("PHASE 9.2.2 COMPLETE — PASSED")
print("=" * 80)