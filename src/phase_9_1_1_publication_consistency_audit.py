from pathlib import Path
import pandas as pd
import numpy as np

# ============================================================
# PHASE 9.1.1 — PUBLICATION CONSISTENCY AUDIT
# ============================================================

RESULTS_DIR = Path("results/eligible")
PUB_DIR = RESULTS_DIR / "publication_tables"

LOCKED_BUDGET = 0.15
TOTAL_FALSE_NEGATIVES = 557

print("=" * 80)
print("PHASE 9.1.1 — PUBLICATION CONSISTENCY AUDIT")
print("=" * 80)

# ------------------------------------------------------------
# 1. Load files
# ------------------------------------------------------------

primary_file = RESULTS_DIR / "final_test_router_primary_15pct.csv"
sensitivity_file = RESULTS_DIR / "final_test_router_sensitivity.csv"
bootstrap_point_file = RESULTS_DIR / "final_test_bootstrap_point_estimates.csv"
bootstrap_ci_file = RESULTS_DIR / "final_test_bootstrap_confidence_intervals.csv"
predictions_file = RESULTS_DIR / "final_test_router_predictions.csv"

table2_file = PUB_DIR / "table_2_locked_15pct_review_comparison.csv"
table3a_file = PUB_DIR / "table_3a_bootstrap_confidence_intervals.csv"
table6_file = PUB_DIR / "table_6_key_results_summary.csv"

required_files = [
    primary_file,
    sensitivity_file,
    bootstrap_point_file,
    bootstrap_ci_file,
    predictions_file,
]

for f in required_files:
    if not f.exists():
        raise FileNotFoundError(f"Missing required file: {f}")

primary = pd.read_csv(primary_file)
sensitivity = pd.read_csv(sensitivity_file)
bootstrap_point = pd.read_csv(bootstrap_point_file)
bootstrap_ci = pd.read_csv(bootstrap_ci_file)
pred = pd.read_csv(predictions_file)

print("\nFiles loaded successfully.")

# ------------------------------------------------------------
# 2. Basic integrity
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("A — BASIC TEST INTEGRITY")
print("=" * 80)

fn = pred[
    (pred["actual_30d"] == 1) &
    (pred["predicted_30d"] == 0)
].copy()

print("Low-risk rows:", len(pred))
print("False negatives:", len(fn))

if len(fn) != TOTAL_FALSE_NEGATIVES:
    print(
        f"WARNING: Expected {TOTAL_FALSE_NEGATIVES} false negatives "
        f"but found {len(fn)}."
    )
else:
    print("False-negative count: PASSED")

n_review = int(np.floor(LOCKED_BUDGET * len(pred)))

print("Locked low-risk budget:", LOCKED_BUDGET)
print("Expected patients reviewed:", n_review)

# ------------------------------------------------------------
# 3. Canonical locked-result file
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("B — LOCKED PRIMARY RESULT FILE")
print("=" * 80)

print(primary.to_string(index=False))

# ------------------------------------------------------------
# 4. Sensitivity table at exactly 15%
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("C — SENSITIVITY TABLE AT 15%")
print("=" * 80)

sens15 = sensitivity[
    np.isclose(sensitivity["budget"], LOCKED_BUDGET)
].copy()

print(sens15.to_string(index=False))

# ------------------------------------------------------------
# 5. Bootstrap point estimates
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("D — BOOTSTRAP POINT ESTIMATES")
print("=" * 80)

print(bootstrap_point.to_string(index=False))

# ------------------------------------------------------------
# 6. Direct cross-file comparison
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("E — CROSS-FILE POINT-ESTIMATE COMPARISON")
print("=" * 80)

methods = [
    "Probability",
    "Disagreement",
    "Rescue Router",
    "Random"
]

comparison_rows = []

for method in methods:

    p = primary[primary["method"] == method]
    s = sens15[sens15["method"] == method]
    b = bootstrap_point[bootstrap_point["method"] == method]

    row = {
        "method": method,
        "primary_fn_captured": (
            float(p["fn_captured"].iloc[0]) if len(p) else np.nan
        ),
        "primary_capture_rate": (
            float(p["fn_capture_rate"].iloc[0]) if len(p) else np.nan
        ),
        "sensitivity_fn_captured": (
            float(s["fn_captured"].iloc[0]) if len(s) else np.nan
        ),
        "sensitivity_capture_rate": (
            float(s["fn_capture_rate"].iloc[0]) if len(s) else np.nan
        ),
        "bootstrap_fn_captured": (
            float(b["fn_captured"].iloc[0]) if len(b) else np.nan
        ),
        "bootstrap_capture_rate": (
            float(b["fn_capture_rate"].iloc[0]) if len(b) else np.nan
        ),
    }

    comparison_rows.append(row)

comparison = pd.DataFrame(comparison_rows)

comparison["primary_vs_sensitivity_match"] = np.isclose(
    comparison["primary_capture_rate"],
    comparison["sensitivity_capture_rate"],
    atol=1e-10,
    equal_nan=True,
)

comparison["primary_vs_bootstrap_match"] = np.isclose(
    comparison["primary_capture_rate"],
    comparison["bootstrap_capture_rate"],
    atol=1e-10,
    equal_nan=True,
)

print(comparison.to_string(index=False))

# ------------------------------------------------------------
# 7. Reproduce router selection directly
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("F — DIRECT ROUTER REPRODUCTION")
print("=" * 80)

router_sorted = pred.sort_values(
    ["fn_router_probability", "encounter_id"],
    ascending=[False, True],
).head(n_review)

router_fn = int(
    (
        (router_sorted["actual_30d"] == 1) &
        (router_sorted["predicted_30d"] == 0)
    ).sum()
)

router_rate = router_fn / len(fn)

print("Router reviewed:", len(router_sorted))
print("Router FN captured:", router_fn)
print(f"Router FN capture rate: {router_rate:.6f} ({router_rate*100:.2f}%)")

# ------------------------------------------------------------
# 8. Reproduce disagreement ranking
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("G — DIRECT DISAGREEMENT REPRODUCTION")
print("=" * 80)

dis_sorted = pred.sort_values(
    ["disagreement_score", "encounter_id"],
    ascending=[False, True],
).head(n_review)

dis_fn = int(
    (
        (dis_sorted["actual_30d"] == 1) &
        (dis_sorted["predicted_30d"] == 0)
    ).sum()
)

dis_rate = dis_fn / len(fn)

print("Disagreement reviewed:", len(dis_sorted))
print("Disagreement FN captured:", dis_fn)
print(
    f"Disagreement FN capture rate: "
    f"{dis_rate:.6f} ({dis_rate*100:.2f}%)"
)

# ------------------------------------------------------------
# 9. Probability tie audit
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("H — PROBABILITY RANKING TIE AUDIT")
print("=" * 80)

score = "probability_score"

sorted_prob = pred.sort_values(
    [score, "encounter_id"],
    ascending=[False, True],
).reset_index(drop=True)

cutoff = sorted_prob.loc[n_review - 1, score]

above = pred[pred[score] > cutoff].copy()
ties = pred[np.isclose(pred[score], cutoff, atol=1e-12)].copy()

slots_remaining = n_review - len(above)

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

print("Probability cutoff:", cutoff)
print("Patients strictly above cutoff:", len(above))
print("Patients tied at cutoff:", len(ties))
print("Review slots remaining within tie:", slots_remaining)
print("FNs strictly above cutoff:", above_fn)
print("FNs among all tied patients:", tie_fn)

# ------------------------------------------------------------
# 10. Deterministic probability tie-breaks
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("I — DETERMINISTIC PROBABILITY TIE-BREAKS")
print("=" * 80)

prob_asc = pred.sort_values(
    [score, "encounter_id"],
    ascending=[False, True],
).head(n_review)

prob_desc = pred.sort_values(
    [score, "encounter_id"],
    ascending=[False, False],
).head(n_review)

prob_asc_fn = int(
    (
        (prob_asc["actual_30d"] == 1) &
        (prob_asc["predicted_30d"] == 0)
    ).sum()
)

prob_desc_fn = int(
    (
        (prob_desc["actual_30d"] == 1) &
        (prob_desc["predicted_30d"] == 0)
    ).sum()
)

prob_asc_rate = prob_asc_fn / len(fn)
prob_desc_rate = prob_desc_fn / len(fn)

print(
    f"Encounter ID ascending: "
    f"{prob_asc_fn} FNs = {prob_asc_rate*100:.2f}%"
)

print(
    f"Encounter ID descending: "
    f"{prob_desc_fn} FNs = {prob_desc_rate*100:.2f}%"
)

# ------------------------------------------------------------
# 11. Expected random tie resolution
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("J — EXPECTED PROBABILITY PERFORMANCE UNDER RANDOM TIE RESOLUTION")
print("=" * 80)

if len(ties) > 0:

    expected_tied_fn = slots_remaining * (tie_fn / len(ties))
    expected_total_fn = above_fn + expected_tied_fn
    expected_rate = expected_total_fn / len(fn)

    print("Expected tied FNs selected:", expected_tied_fn)
    print("Expected total FNs captured:", expected_total_fn)
    print(
        f"Expected FN capture rate: "
        f"{expected_rate:.6f} ({expected_rate*100:.2f}%)"
    )

else:
    expected_total_fn = np.nan
    expected_rate = np.nan

    print("No probability ties detected.")

# ------------------------------------------------------------
# 12. Check publication tables
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("K — PUBLICATION TABLE CHECK")
print("=" * 80)

if table2_file.exists():

    table2 = pd.read_csv(table2_file)

    print("\nTABLE 2:")
    print(table2.to_string(index=False))

else:
    print("Table 2 not found.")

if table3a_file.exists():

    table3a = pd.read_csv(table3a_file)

    print("\nTABLE 3A:")
    print(table3a.to_string(index=False))

else:
    print("Table 3A not found.")

if table6_file.exists():

    table6 = pd.read_csv(table6_file)

    print("\nTABLE 6:")
    print(table6.to_string(index=False))

else:
    print("Table 6 not found.")

# ------------------------------------------------------------
# 13. Audit flags
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("L — AUDIT FLAGS")
print("=" * 80)

issues = []

for _, row in comparison.iterrows():

    method = row["method"]

    if not row["primary_vs_sensitivity_match"]:

        issues.append(
            f"{method}: primary locked result does not match "
            f"15% sensitivity result."
        )

    if not row["primary_vs_bootstrap_match"]:

        issues.append(
            f"{method}: bootstrap point estimate does not match "
            f"primary locked result."
        )

if issues:

    print("INCONSISTENCIES FOUND:\n")

    for issue in issues:
        print(" -", issue)

else:

    print("All point estimates are consistent.")

# ------------------------------------------------------------
# 14. Interpretation
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("M — RECOMMENDED REPORTING RULE")
print("=" * 80)

print(
    """
1. The frozen Rescue Router result must remain unchanged.

2. The locked operating point is 15% of the LOW-RISK population,
   corresponding to 1,178 reviewed patients.

3. Rescue Router and Disagreement should use deterministic rankings.

4. Probability ranking contains a large cutoff tie.
   Therefore, a probability result can depend on arbitrary row ordering
   unless a tie-handling rule is explicitly defined.

5. For publication, do NOT silently choose the most favorable
   probability tie resolution.

6. The preferred probability baseline should use either:

   A) a pre-specified deterministic tie-break rule, OR

   B) expected performance under random selection among patients tied
      at the cutoff.

7. Bootstrap point estimates, figures, tables, and text must all use
   exactly the same probability-ranking rule.
"""
)

# ------------------------------------------------------------
# 15. Save audit
# ------------------------------------------------------------

audit_file = RESULTS_DIR / "publication_consistency_audit.csv"

comparison.to_csv(audit_file, index=False)

print("=" * 80)
print("FILE SAVED")
print("=" * 80)

print(audit_file)

print("\n" + "=" * 80)
print("PHASE 9.1.1 COMPLETE")
print("=" * 80)