from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# PHASE 9.1.2 — CANONICAL LOCKED TEST RESULTS
# ============================================================

RESULTS_DIR = Path("results/eligible")

INPUT_FILE = RESULTS_DIR / "final_test_router_predictions.csv"
OUTPUT_FILE = RESULTS_DIR / "canonical_locked_15pct_results.csv"

LOCKED_BUDGET = 0.15


print("=" * 80)
print("PHASE 9.1.2 — CANONICAL LOCKED TEST RESULTS")
print("=" * 80)


# ------------------------------------------------------------
# Load frozen final-test predictions
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print("\nInput shape:", df.shape)


# ------------------------------------------------------------
# Identify false negatives
# ------------------------------------------------------------

fn_mask = (
    (df["actual_30d"] == 1) &
    (df["predicted_30d"] == 0)
)

total_fn = int(fn_mask.sum())

n_patients = len(df)
n_review = int(np.floor(LOCKED_BUDGET * n_patients))

print("Low-risk test patients:", n_patients)
print("False negatives:", total_fn)
print("Locked budget:", LOCKED_BUDGET)
print("Patients reviewed:", n_review)


# ============================================================
# 1. RESCUE ROUTER
# ============================================================

router = (
    df.sort_values(
        ["fn_router_probability", "encounter_id"],
        ascending=[False, True]
    )
    .head(n_review)
)

router_fn = int(
    (
        (router["actual_30d"] == 1) &
        (router["predicted_30d"] == 0)
    ).sum()
)

router_capture = router_fn / total_fn
router_precision = router_fn / n_review


# ============================================================
# 2. DISAGREEMENT
# ============================================================

disagreement = (
    df.sort_values(
        ["disagreement_score", "encounter_id"],
        ascending=[False, True]
    )
    .head(n_review)
)

disagreement_fn = int(
    (
        (disagreement["actual_30d"] == 1) &
        (disagreement["predicted_30d"] == 0)
    ).sum()
)

disagreement_capture = disagreement_fn / total_fn
disagreement_precision = disagreement_fn / n_review


# ============================================================
# 3. PROBABILITY — EXPECTED RANDOM TIE HANDLING
# ============================================================

score = "probability_score"

ordered = df.sort_values(
    score,
    ascending=False
).reset_index(drop=True)

cutoff = ordered.loc[n_review - 1, score]

above = df[df[score] > cutoff].copy()

ties = df[
    np.isclose(
        df[score],
        cutoff,
        atol=1e-12,
        rtol=0
    )
].copy()

slots_in_tie = n_review - len(above)

above_fn = int(
    (
        (above["actual_30d"] == 1) &
        (above["predicted_30d"] == 0)
    ).sum()
)

tie_fn = int(
    (
        (ties["actual_30d"] == 1) &
        (ties["predicted_30d"] == 0)
    ).sum()
)

expected_tie_fn = (
    slots_in_tie * tie_fn / len(ties)
)

probability_expected_fn = (
    above_fn + expected_tie_fn
)

probability_capture = (
    probability_expected_fn / total_fn
)

probability_precision = (
    probability_expected_fn / n_review
)


# ============================================================
# 4. RANDOM EXPECTATION
# ============================================================

# Under uniform random review of exactly n_review patients,
# expected FN capture equals the sampling fraction.

random_expected_fn = (
    n_review * total_fn / n_patients
)

random_capture = (
    random_expected_fn / total_fn
)

random_precision = (
    total_fn / n_patients
)


# ============================================================
# BUILD CANONICAL TABLE
# ============================================================

rows = [

    {
        "method": "Probability",
        "tie_rule": "Expected random selection within cutoff tie",
        "patients_reviewed": n_review,
        "expected_fn_captured": probability_expected_fn,
        "fn_capture_rate": probability_capture,
        "review_precision": probability_precision,
    },

    {
        "method": "Rescue Router",
        "tie_rule": "Deterministic score ranking",
        "patients_reviewed": n_review,
        "expected_fn_captured": router_fn,
        "fn_capture_rate": router_capture,
        "review_precision": router_precision,
    },

    {
        "method": "Disagreement",
        "tie_rule": "Deterministic score ranking",
        "patients_reviewed": n_review,
        "expected_fn_captured": disagreement_fn,
        "fn_capture_rate": disagreement_capture,
        "review_precision": disagreement_precision,
    },

    {
        "method": "Random",
        "tie_rule": "Analytical expectation",
        "patients_reviewed": n_review,
        "expected_fn_captured": random_expected_fn,
        "fn_capture_rate": random_capture,
        "review_precision": random_precision,
    }
]

canonical = pd.DataFrame(rows)

canonical["fn_capture_percent"] = (
    canonical["fn_capture_rate"] * 100
)

canonical["review_precision_percent"] = (
    canonical["review_precision"] * 100
)


# ============================================================
# OUTPUT
# ============================================================

print("\n" + "=" * 80)
print("CANONICAL LOCKED 15% RESULTS")
print("=" * 80)

display_cols = [
    "method",
    "patients_reviewed",
    "expected_fn_captured",
    "fn_capture_percent",
    "review_precision_percent",
    "tie_rule",
]

print(
    canonical[display_cols].to_string(
        index=False
    )
)


# ------------------------------------------------------------
# Probability tie diagnostics
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("PROBABILITY TIE DIAGNOSTICS")
print("=" * 80)

print("Cutoff probability:", cutoff)
print("Patients strictly above cutoff:", len(above))
print("Patients tied at cutoff:", len(ties))
print("Slots available within tie:", slots_in_tie)

print("FNs strictly above cutoff:", above_fn)
print("FNs among tied patients:", tie_fn)

print(
    "Expected FNs selected from tie:",
    expected_tie_fn
)

print(
    "Expected total probability FNs:",
    probability_expected_fn
)


# ------------------------------------------------------------
# Router vs random
# ------------------------------------------------------------

router_gain = (
    router_capture - random_capture
)

router_lift = (
    router_capture / random_capture
)

print("\n" + "=" * 80)
print("RESCUE ROUTER EFFECT")
print("=" * 80)

print(
    f"Router FN capture: "
    f"{router_capture*100:.2f}%"
)

print(
    f"Random expected capture: "
    f"{random_capture*100:.2f}%"
)

print(
    f"Absolute gain: "
    f"{router_gain*100:.2f} percentage points"
)

print(
    f"Lift over random: "
    f"{router_lift:.3f}x"
)


# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

canonical.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n" + "=" * 80)
print("FILE SAVED")
print("=" * 80)

print(OUTPUT_FILE)

print("\n" + "=" * 80)
print("PHASE 9.1.2 COMPLETE")
print("=" * 80)