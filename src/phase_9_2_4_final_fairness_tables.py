from pathlib import Path
import pandas as pd
import numpy as np

# ============================================================
# PHASE 9.2.4 — FINAL FAIRNESS + END-TO-END TABLES
# ============================================================

RESULTS = Path("results/eligible")
PUB = RESULTS / "publication"

FAIRNESS_FILE = RESULTS / "final_test_fairness_subgroup_rates.csv"
E2E_FILE = RESULTS / "final_test_end_to_end_fairness.csv"

OUT_FAIRNESS = PUB / "table_4_final_fn_rescue_fairness.csv"
OUT_E2E = PUB / "table_5_final_end_to_end_fairness.csv"
OUT_SUMMARY = PUB / "table_6_final_fairness_summary.csv"

PUB.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("PHASE 9.2.4 — FINAL FAIRNESS + END-TO-END TABLES")
print("=" * 80)

fair = pd.read_csv(FAIRNESS_FILE)
e2e = pd.read_csv(E2E_FILE)

print("\nFairness input shape:", fair.shape)
print("End-to-end input shape:", e2e.shape)

print("\nFairness features:")
print(fair["feature"].value_counts())

print("\nEnd-to-end features:")
print(e2e["feature"].value_counts())


# ============================================================
# A — BASIC INTEGRITY
# ============================================================

print("\n" + "=" * 80)
print("A — BASIC INTEGRITY")
print("=" * 80)

checks = {
    "Fairness table has 17 rows": len(fair) == 17,
    "End-to-end table has 17 rows": len(e2e) == 17,
    "Gender present": "gender" in set(fair["feature"]),
    "Race present": "race" in set(fair["feature"]),
    "Age present": "age" in set(fair["feature"]),
}

for name, passed in checks.items():
    print(f"{name}: {'PASSED' if passed else 'FAILED'}")

if not all(checks.values()):
    raise ValueError("Basic fairness integrity failed.")


# ============================================================
# B — CONDITIONAL FN RESCUE TABLE
# ============================================================

fair_table = fair.copy()

for col in [
    "fn_rescue_rate",
    "ci_lower",
    "ci_upper",
]:
    fair_table[col] = fair_table[col] * 100

fair_table = fair_table.rename(
    columns={
        "feature": "Feature",
        "group": "Group",
        "total_false_negatives": "False Negatives",
        "rescued_false_negatives": "Rescued False Negatives",
        "missed_false_negatives": "Residual False Negatives",
        "fn_rescue_rate": "FN Rescue Rate (%)",
        "ci_lower": "95% CI Lower (%)",
        "ci_upper": "95% CI Upper (%)",
    }
)

for col in [
    "FN Rescue Rate (%)",
    "95% CI Lower (%)",
    "95% CI Upper (%)",
]:
    fair_table[col] = fair_table[col].round(2)

print("\n" + "=" * 80)
print("B — FINAL TABLE 4: CONDITIONAL FN RESCUE FAIRNESS")
print("=" * 80)

print(fair_table.to_string(index=False))


# ============================================================
# C — END-TO-END FAIRNESS TABLE
# ============================================================

e2e_table = e2e.copy()

percentage_cols = [
    "primary_fnr",
    "simulated_residual_fnr",
    "absolute_fnr_reduction",
    "conditional_fn_rescue_rate",
]

for col in percentage_cols:
    e2e_table[col] = e2e_table[col] * 100

e2e_table = e2e_table.rename(
    columns={
        "feature": "Feature",
        "group": "Group",
        "actual_positives": "Actual Positives",
        "true_positives": "True Positives",
        "false_negatives": "False Negatives",
        "rescued_false_negatives": "Rescued False Negatives",
        "primary_fnr": "Primary FNR (%)",
        "simulated_residual_fnr": "Residual FNR (%)",
        "absolute_fnr_reduction": "Absolute FNR Reduction (pp)",
        "conditional_fn_rescue_rate": "Conditional FN Rescue (%)",
    }
)

for col in [
    "Primary FNR (%)",
    "Residual FNR (%)",
    "Absolute FNR Reduction (pp)",
    "Conditional FN Rescue (%)",
]:
    e2e_table[col] = e2e_table[col].round(2)

print("\n" + "=" * 80)
print("C — FINAL TABLE 5: END-TO-END FAIRNESS")
print("=" * 80)

print(e2e_table.to_string(index=False))


# ============================================================
# D — KEY GENDER RESULTS
# ============================================================

print("\n" + "=" * 80)
print("D — GENDER FAIRNESS")
print("=" * 80)

gender = fair[fair["feature"] == "gender"].copy()

female = gender[gender["group"] == "Female"].iloc[0]
male = gender[gender["group"] == "Male"].iloc[0]

female_rate = female["fn_rescue_rate"] * 100
male_rate = male["fn_rescue_rate"] * 100

gender_gap = female_rate - male_rate

print(f"Female FN rescue: {female_rate:.2f}%")
print(f"Male FN rescue: {male_rate:.2f}%")
print(f"Female - Male gap: {gender_gap:.2f} pp")

print("Expected Fisher p-value from Phase 8.2: 0.6713")


# ============================================================
# E — KEY RACE RESULTS
# ============================================================

print("\n" + "=" * 80)
print("E — RACE FAIRNESS")
print("=" * 80)

race = fair[fair["feature"] == "race"].copy()

aa = race[race["group"] == "AfricanAmerican"].iloc[0]
cauc = race[race["group"] == "Caucasian"].iloc[0]

aa_rate = aa["fn_rescue_rate"] * 100
cauc_rate = cauc["fn_rescue_rate"] * 100

race_gap = aa_rate - cauc_rate

print(
    f"African American FN rescue: "
    f"{aa_rate:.2f}%"
)

print(
    f"Caucasian FN rescue: "
    f"{cauc_rate:.2f}%"
)

print(
    f"African American - Caucasian gap: "
    f"{race_gap:.2f} pp"
)

print("Expected Fisher p-value from Phase 8.2: 0.0617")


# ============================================================
# F — KEY AGE RESULTS
# ============================================================

print("\n" + "=" * 80)
print("F — AGE FAIRNESS")
print("=" * 80)

age = fair[fair["feature"] == "age"].copy()

# Only use reasonably populated FN groups for descriptive extremes.
stable_age = age[
    age["total_false_negatives"] >= 20
].copy()

highest_age = stable_age.loc[
    stable_age["fn_rescue_rate"].idxmax()
]

lowest_age = stable_age.loc[
    stable_age["fn_rescue_rate"].idxmin()
]

age_gap = (
    highest_age["fn_rescue_rate"]
    - lowest_age["fn_rescue_rate"]
) * 100

print(
    "Highest stable age-group rescue:",
    highest_age["group"],
    f"{highest_age['fn_rescue_rate'] * 100:.2f}%"
)

print(
    "Lowest stable age-group rescue:",
    lowest_age["group"],
    f"{lowest_age['fn_rescue_rate'] * 100:.2f}%"
)

print(f"Stable age rescue gap: {age_gap:.2f} pp")

print("Expected age association p-value: 0.0085")
print("Expected Spearman p-value: 0.0007")


# ============================================================
# G — END-TO-END AFRICAN AMERICAN VS CAUCASIAN
# ============================================================

print("\n" + "=" * 80)
print("G — END-TO-END RACE IMPACT")
print("=" * 80)

race_e2e = e2e[e2e["feature"] == "race"].copy()

aa_e2e = race_e2e[
    race_e2e["group"] == "AfricanAmerican"
].iloc[0]

cauc_e2e = race_e2e[
    race_e2e["group"] == "Caucasian"
].iloc[0]

aa_primary = aa_e2e["primary_fnr"] * 100
aa_residual = aa_e2e["simulated_residual_fnr"] * 100

cauc_primary = cauc_e2e["primary_fnr"] * 100
cauc_residual = cauc_e2e["simulated_residual_fnr"] * 100

primary_gap = aa_primary - cauc_primary
residual_gap = aa_residual - cauc_residual
gap_change = residual_gap - primary_gap

print("African American:")
print(f"  Primary FNR: {aa_primary:.2f}%")
print(f"  Residual FNR: {aa_residual:.2f}%")

print()

print("Caucasian:")
print(f"  Primary FNR: {cauc_primary:.2f}%")
print(f"  Residual FNR: {cauc_residual:.2f}%")

print()

print(f"Primary FNR gap: {primary_gap:.2f} pp")
print(f"Residual FNR gap: {residual_gap:.2f} pp")
print(f"Gap change: {gap_change:+.2f} pp")


# ============================================================
# H — OVERALL END-TO-END IMPACT
# ============================================================

print("\n" + "=" * 80)
print("H — OVERALL END-TO-END IMPACT")
print("=" * 80)

TP = 1179
FN = 557
RESCUED = 110

actual_positive = TP + FN
residual_fn = FN - RESCUED

primary_fnr = FN / actual_positive
residual_fnr = residual_fn / actual_positive

absolute_reduction = (
    primary_fnr - residual_fnr
)

relative_reduction = RESCUED / FN

print(f"Actual positives: {actual_positive}")
print(f"Primary false negatives: {FN}")
print(f"Rescued false negatives: {RESCUED}")
print(f"Residual false negatives: {residual_fn}")

print(f"Primary FNR: {primary_fnr * 100:.2f}%")
print(f"Residual FNR: {residual_fnr * 100:.2f}%")

print(
    f"Absolute FNR reduction: "
    f"{absolute_reduction * 100:.2f} pp"
)

print(
    f"Relative reduction in missed positives: "
    f"{relative_reduction * 100:.2f}%"
)


# ============================================================
# I — PUBLICATION SUMMARY TABLE
# ============================================================

summary = pd.DataFrame(
    [
        [
            "Overall conditional FN rescue",
            19.748654,
            "%"
        ],
        [
            "Female conditional FN rescue",
            female_rate,
            "%"
        ],
        [
            "Male conditional FN rescue",
            male_rate,
            "%"
        ],
        [
            "Female - Male rescue gap",
            gender_gap,
            "pp"
        ],
        [
            "African American conditional FN rescue",
            aa_rate,
            "%"
        ],
        [
            "Caucasian conditional FN rescue",
            cauc_rate,
            "%"
        ],
        [
            "African American - Caucasian rescue gap",
            race_gap,
            "pp"
        ],
        [
            "Primary overall FNR",
            primary_fnr * 100,
            "%"
        ],
        [
            "Residual overall FNR",
            residual_fnr * 100,
            "%"
        ],
        [
            "Absolute overall FNR reduction",
            absolute_reduction * 100,
            "pp"
        ],
        [
            "Relative reduction in missed positives",
            relative_reduction * 100,
            "%"
        ],
        [
            "Primary African American-Caucasian FNR gap",
            primary_gap,
            "pp"
        ],
        [
            "Residual African American-Caucasian FNR gap",
            residual_gap,
            "pp"
        ],
        [
            "Race FNR gap change",
            gap_change,
            "pp"
        ],
    ],
    columns=[
        "Result",
        "Value",
        "Unit",
    ]
)

summary["Value"] = summary["Value"].round(2)

print("\n" + "=" * 80)
print("I — FINAL FAIRNESS SUMMARY")
print("=" * 80)

print(summary.to_string(index=False))


# ============================================================
# J — CRITICAL CONSISTENCY ASSERTIONS
# ============================================================

print("\n" + "=" * 80)
print("J — CRITICAL CONSISTENCY ASSERTIONS")
print("=" * 80)

checks = {
    "Female rescue = 20.49%":
        np.isclose(female_rate, 20.486111, atol=0.01),

    "Male rescue = 18.96%":
        np.isclose(male_rate, 18.959108, atol=0.01),

    "African American rescue = 14.02%":
        np.isclose(aa_rate, 14.018692, atol=0.01),

    "Caucasian rescue = 22.25%":
        np.isclose(cauc_rate, 22.248804, atol=0.01),

    "Overall primary FNR = 32.09%":
        np.isclose(primary_fnr * 100, 32.085253, atol=0.01),

    "Overall residual FNR = 25.75%":
        np.isclose(residual_fnr * 100, 25.748848, atol=0.01),

    "Rescued FN = 110":
        RESCUED == 110,
}

for name, passed in checks.items():
    print(f"{name}: {'PASSED' if passed else 'FAILED'}")

if not all(checks.values()):
    raise ValueError(
        "Final fairness consistency check failed."
    )


# ============================================================
# K — SAVE
# ============================================================

fair_table.to_csv(
    OUT_FAIRNESS,
    index=False
)

e2e_table.to_csv(
    OUT_E2E,
    index=False
)

summary.to_csv(
    OUT_SUMMARY,
    index=False
)

print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print(OUT_FAIRNESS)
print(OUT_E2E)
print(OUT_SUMMARY)

print("\n" + "=" * 80)
print("PHASE 9.2.4 COMPLETE — PASSED")
print("=" * 80)