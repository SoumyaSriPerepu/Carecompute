from pathlib import Path
import pandas as pd
import numpy as np

# ============================================================
# PHASE 9.2.3 — FINAL BOOTSTRAP STATISTICAL TABLES
# ============================================================

RESULTS = Path("results/eligible")
PUB = RESULTS / "publication"

CI_FILE = RESULTS / "canonical_bootstrap_confidence_intervals.csv"
PAIR_FILE = RESULTS / "canonical_bootstrap_paired_comparisons.csv"

OUT_CI = PUB / "table_3a_final_bootstrap_ci.csv"
OUT_PAIR = PUB / "table_3b_final_paired_comparisons.csv"

PUB.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("PHASE 9.2.3 — FINAL BOOTSTRAP STATISTICAL TABLES")
print("=" * 80)

ci = pd.read_csv(CI_FILE)
pair = pd.read_csv(PAIR_FILE)

print("\nBootstrap CI input:")
print(ci.to_string(index=False))

print("\nPaired comparison input:")
print(pair.to_string(index=False))


# ============================================================
# A — INTEGRITY CHECK
# ============================================================

print("\n" + "=" * 80)
print("A — INTEGRITY CHECK")
print("=" * 80)

expected_methods = {
    "Probability",
    "Rescue Router",
    "Disagreement",
    "Random",
}

checks = {
    "Four bootstrap strategies": len(ci) == 4,
    "Expected strategies present":
        set(ci["method"]) == expected_methods,
    "Four paired comparisons": len(pair) == 4,
}

for name, passed in checks.items():
    print(f"{name}: {'PASSED' if passed else 'FAILED'}")

if not all(checks.values()):
    raise ValueError("Bootstrap integrity check failed.")


# ============================================================
# B — CANONICAL POINT ESTIMATE CHECK
# ============================================================

print("\n" + "=" * 80)
print("B — CANONICAL POINT ESTIMATE CHECK")
print("=" * 80)

expected_points = {
    "Probability": 0.20813356,
    "Rescue Router": 0.19748654,
    "Disagreement": 0.18312388,
    "Random": 0.14991092,
}

for method, expected in expected_points.items():

    observed = float(
        ci.loc[
            ci["method"] == method,
            "point_estimate"
        ].iloc[0]
    )

    passed = np.isclose(
        observed,
        expected,
        atol=1e-6
    )

    print(
        f"{method:15s} "
        f"observed={observed:.6f} "
        f"expected={expected:.6f} "
        f"{'PASSED' if passed else 'FAILED'}"
    )

    if not passed:
        raise ValueError(
            f"Point estimate mismatch for {method}"
        )


# ============================================================
# C — FINAL TABLE 3A
# ============================================================

order = [
    "Probability",
    "Rescue Router",
    "Disagreement",
    "Random",
]

ci_table = ci.copy()

ci_table["method"] = pd.Categorical(
    ci_table["method"],
    categories=order,
    ordered=True
)

ci_table = ci_table.sort_values("method").reset_index(drop=True)

for col in [
    "point_estimate",
    "bootstrap_mean",
    "ci_lower",
    "ci_upper",
]:
    ci_table[col] = ci_table[col] * 100

ci_table = ci_table.rename(
    columns={
        "method": "Review Strategy",
        "point_estimate": "Point FN Capture (%)",
        "bootstrap_mean": "Bootstrap Mean (%)",
        "ci_lower": "95% CI Lower (%)",
        "ci_upper": "95% CI Upper (%)",
    }
)

for col in [
    "Point FN Capture (%)",
    "Bootstrap Mean (%)",
    "95% CI Lower (%)",
    "95% CI Upper (%)",
]:
    ci_table[col] = ci_table[col].round(2)

print("\n" + "=" * 80)
print("C — FINAL TABLE 3A")
print("=" * 80)

print(ci_table.to_string(index=False))


# ============================================================
# D — FINAL TABLE 3B
# ============================================================

pair_table = pair.copy()

# Convert differences/probabilities from proportions to percentages.
pair_table["mean_difference"] *= 100
pair_table["ci_lower"] *= 100
pair_table["ci_upper"] *= 100

pair_table["probability_a_better"] *= 100
pair_table["probability_equal"] *= 100
pair_table["probability_a_worse"] *= 100

pair_table = pair_table.rename(
    columns={
        "comparison": "Comparison",
        "mean_difference":
            "Bootstrap Mean Difference (pp)",
        "ci_lower": "95% CI Lower (pp)",
        "ci_upper": "95% CI Upper (pp)",
        "bootstrap_p_value": "Bootstrap p-value",
        "probability_a_better": "P(A Better) (%)",
        "probability_equal": "P(Equal) (%)",
        "probability_a_worse": "P(A Worse) (%)",
    }
)

round_2 = [
    "Bootstrap Mean Difference (pp)",
    "95% CI Lower (pp)",
    "95% CI Upper (pp)",
    "P(A Better) (%)",
    "P(Equal) (%)",
    "P(A Worse) (%)",
]

for col in round_2:
    pair_table[col] = pair_table[col].round(2)

pair_table["Bootstrap p-value"] = (
    pair_table["Bootstrap p-value"].round(4)
)

print("\n" + "=" * 80)
print("D — FINAL TABLE 3B")
print("=" * 80)

print(pair_table.to_string(index=False))


# ============================================================
# E — KEY STATISTICAL CLAIM CHECK
# ============================================================

print("\n" + "=" * 80)
print("E — KEY STATISTICAL CLAIM CHECK")
print("=" * 80)

def comparison_row(name):
    return pair.loc[
        pair["comparison"] == name
    ].iloc[0]


router_random = comparison_row(
    "Rescue Router vs Random"
)

router_prob = comparison_row(
    "Rescue Router vs Probability"
)

router_dis = comparison_row(
    "Rescue Router vs Disagreement"
)

rr_diff = float(router_random["mean_difference"])
rr_low = float(router_random["ci_lower"])
rr_high = float(router_random["ci_upper"])
rr_p = float(router_random["bootstrap_p_value"])

rp_p = float(router_prob["bootstrap_p_value"])
rd_p = float(router_dis["bootstrap_p_value"])

checks = {
    "Router > random":
        rr_diff > 0,

    "Router-random CI excludes zero":
        rr_low > 0,

    "Router-random p < 0.05":
        rr_p < 0.05,

    "Router vs probability not significant":
        rp_p >= 0.05,

    "Router vs disagreement not significant":
        rd_p >= 0.05,
}

for name, passed in checks.items():
    print(f"{name}: {'PASSED' if passed else 'FAILED'}")

if not all(checks.values()):
    raise ValueError(
        "Key statistical claim check failed."
    )


# ============================================================
# F — MANUSCRIPT STATISTICAL VALUES
# ============================================================

print("\n" + "=" * 80)
print("F — MANUSCRIPT STATISTICAL VALUES")
print("=" * 80)

print("Rescue Router vs Random:")
print(
    f"Difference = {rr_diff * 100:.2f} pp"
)
print(
    f"95% CI = "
    f"[{rr_low * 100:.2f}, "
    f"{rr_high * 100:.2f}] pp"
)
print(f"p = {rr_p:.4f}")

print()

print("Rescue Router vs Probability:")
print(f"p = {rp_p:.4f}")

print()

print("Rescue Router vs Disagreement:")
print(f"p = {rd_p:.4f}")


# ============================================================
# G — SAVE FINAL TABLES
# ============================================================

ci_table.to_csv(
    OUT_CI,
    index=False
)

pair_table.to_csv(
    OUT_PAIR,
    index=False
)

print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print(OUT_CI)
print(OUT_PAIR)

print("\n" + "=" * 80)
print("PHASE 9.2.3 COMPLETE — PASSED")
print("=" * 80)