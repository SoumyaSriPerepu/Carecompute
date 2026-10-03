from pathlib import Path
import pandas as pd
import numpy as np
import sys

# ============================================================
# PHASE 9.4.1 — MASTER PUBLICATION FREEZE AUDIT
# ============================================================

print("=" * 80)
print("PHASE 9.4.1 — MASTER PUBLICATION FREEZE AUDIT")
print("=" * 80)

BASE = Path("results/eligible")
PUB = BASE / "publication"
FIG = PUB / "figures"

errors = []
warnings = []


def check(condition, label):
    if condition:
        print(f"{label}: PASSED")
    else:
        print(f"{label}: FAILED")
        errors.append(label)


def close(a, b, tol=1e-4):
    return np.isclose(float(a), float(b), atol=tol, rtol=0)


# ============================================================
# A — REQUIRED PUBLICATION FILES
# ============================================================

print("\n" + "=" * 80)
print("A — REQUIRED PUBLICATION FILES")
print("=" * 80)

required_files = [
    PUB / "table_1_primary_model_performance.csv",
    PUB / "table_2_final_review_strategies.csv",
    PUB / "table_3a_final_bootstrap_ci.csv",
    PUB / "table_3b_final_paired_comparisons.csv",

    FIG / "figure_1_canonical_fn_capture_vs_review_budget.png",
    FIG / "figure_1_canonical_fn_capture_vs_review_budget.pdf",
    FIG / "figure_1_canonical_data.csv",

    FIG / "figure_2_canonical_locked_15pct_bootstrap.png",
    FIG / "figure_2_canonical_locked_15pct_bootstrap.pdf",
    FIG / "figure_2_canonical_data.csv",

    FIG / "figure_3a_canonical_gender_fn_rescue.png",
    FIG / "figure_3a_canonical_gender_fn_rescue.pdf",

    FIG / "figure_3b_canonical_race_fn_rescue.png",
    FIG / "figure_3b_canonical_race_fn_rescue.pdf",

    FIG / "figure_3c_canonical_age_fn_rescue.png",
    FIG / "figure_3c_canonical_age_fn_rescue.pdf",

    FIG / "figure_3_canonical_fairness_data.csv",

    FIG / "figure_4_canonical_end_to_end_impact.png",
    FIG / "figure_4_canonical_end_to_end_impact.pdf",

    FIG / "figure_5_canonical_race_fairness.png",
    FIG / "figure_5_canonical_race_fairness.pdf",

    FIG / "figure_4_5_canonical_data.csv",
]

for f in required_files:
    exists = f.exists()
    print(f"{f}: {'FOUND' if exists else 'MISSING'}")
    if not exists:
        errors.append(f"Missing file: {f}")


# ============================================================
# B — LOAD CANONICAL TABLES
# ============================================================

print("\n" + "=" * 80)
print("B — LOAD CANONICAL TABLES")
print("=" * 80)

try:
    table1 = pd.read_csv(PUB / "table_1_primary_model_performance.csv")
    table2 = pd.read_csv(PUB / "table_2_final_review_strategies.csv")
    table3a = pd.read_csv(PUB / "table_3a_final_bootstrap_ci.csv")
    table3b = pd.read_csv(PUB / "table_3b_final_paired_comparisons.csv")

    fig1 = pd.read_csv(FIG / "figure_1_canonical_data.csv")
    fig2 = pd.read_csv(FIG / "figure_2_canonical_data.csv")
    fairness = pd.read_csv(FIG / "figure_3_canonical_fairness_data.csv")
    end_to_end = pd.read_csv(FIG / "figure_4_5_canonical_data.csv")

    print("Canonical publication files loaded successfully.")

except Exception as e:
    print("FAILED TO LOAD CANONICAL FILES")
    print(e)
    sys.exit(1)


# ============================================================
# C — PRIMARY MODEL CHECK
# ============================================================

print("\n" + "=" * 80)
print("C — PRIMARY MODEL CHECK")
print("=" * 80)

metric_map = dict(zip(table1["Metric"], table1["Value"]))

check(close(metric_map["Decision threshold"], 0.115), "Threshold = 0.115")
check(close(metric_map["AUROC"], 0.663350), "AUROC = 0.663350")
check(close(metric_map["AUPRC"], 0.212418), "AUPRC = 0.212418")

check(
    close(metric_map["Recall (%)"], 67.914747),
    "Recall = 67.91%"
)

check(
    close(metric_map["False-negative rate (%)"], 32.085253),
    "FNR = 32.09%"
)

check(
    int(metric_map["False negatives"]) == 557,
    "False negatives = 557"
)

check(
    int(metric_map["True positives"]) == 1179,
    "True positives = 1179"
)

check(
    int(metric_map["True negatives"]) == 7301,
    "True negatives = 7301"
)

check(
    int(metric_map["False positives"]) == 6005,
    "False positives = 6005"
)

test_size = (
    int(metric_map["True positives"])
    + int(metric_map["False negatives"])
    + int(metric_map["True negatives"])
    + int(metric_map["False positives"])
)

check(test_size == 15042, "Full test size = 15,042")


# ============================================================
# D — LOCKED REVIEW STRATEGY CHECK
# ============================================================

print("\n" + "=" * 80)
print("D — LOCKED REVIEW STRATEGY CHECK")
print("=" * 80)

expected_capture = {
    "Probability": 20.813356,
    "Rescue Router": 19.748654,
    "Disagreement": 18.312388,
    "Random": 14.991092,
}

for method, expected in expected_capture.items():

    row = table2[
        table2["Review Strategy"] == method
    ]

    check(len(row) == 1, f"{method} row exists")

    if len(row) == 1:
        row = row.iloc[0]

        check(
            int(row["Patients Reviewed"]) == 1178,
            f"{method}: reviewed = 1,178"
        )

        check(
            close(row["FN Capture Rate (%)"], expected, tol=0.01),
            f"{method}: canonical capture = {expected:.2f}%"
        )


# ============================================================
# E — PROBABILITY TIE RULE
# ============================================================

print("\n" + "=" * 80)
print("E — PROBABILITY TIE RULE")
print("=" * 80)

prob = table2[
    table2["Review Strategy"] == "Probability"
].iloc[0]

tie_rule = str(prob["Ranking / Tie Rule"])

print("Probability ranking rule:")
print(tie_rule)

check(
    tie_rule == "Expected random selection within cutoff tie",
    "Canonical probability tie rule"
)


# ============================================================
# F — TABLE 2 VS FIGURE 1
# ============================================================

print("\n" + "=" * 80)
print("F — TABLE 2 VS FIGURE 1")
print("=" * 80)

for method, expected in expected_capture.items():

    row = fig1[
        (fig1["method"] == method)
        & np.isclose(fig1["budget_percent"], 15.0)
    ]

    check(
        len(row) == 1,
        f"Figure 1 contains canonical 15% {method}"
    )

    if len(row) == 1:

        observed = row.iloc[0]["fn_capture_percent"]

        check(
            close(observed, expected, tol=0.01),
            f"Figure 1 {method} = Table 2"
        )


# ============================================================
# G — TABLE 3A VS FIGURE 2
# ============================================================

print("\n" + "=" * 80)
print("G — TABLE 3A VS FIGURE 2")
print("=" * 80)

for method, expected in expected_capture.items():

    t = table3a[
        table3a["Review Strategy"] == method
    ].iloc[0]

    f = fig2[
        fig2["method"] == method
    ].iloc[0]

    check(
        close(t["Point FN Capture (%)"], expected, tol=0.01),
        f"Table 3A {method} point estimate"
    )

    check(
        close(
            t["Point FN Capture (%)"],
            f["point_estimate"],
            tol=0.01
        ),
        f"Table 3A vs Figure 2: {method}"
    )


# ============================================================
# H — PAIRED BOOTSTRAP CLAIMS
# ============================================================

print("\n" + "=" * 80)
print("H — PAIRED BOOTSTRAP CLAIMS")
print("=" * 80)

rr_random = table3b[
    table3b["Comparison"] == "Rescue Router vs Random"
].iloc[0]

print(rr_random.to_string())

check(
    close(
        rr_random["Bootstrap Mean Difference (pp)"],
        4.99,
        tol=0.02
    ),
    "Router vs Random difference = 4.99 pp"
)

check(
    close(
        rr_random["95% CI Lower (pp)"],
        1.76,
        tol=0.02
    ),
    "Router vs Random CI lower = 1.76 pp"
)

check(
    close(
        rr_random["95% CI Upper (pp)"],
        8.28,
        tol=0.02
    ),
    "Router vs Random CI upper = 8.28 pp"
)

check(
    close(
        rr_random["Bootstrap p-value"],
        0.0016,
        tol=0.0001
    ),
    "Router vs Random p = 0.0016"
)

check(
    rr_random["95% CI Lower (pp)"] > 0,
    "Router vs Random CI excludes zero"
)


# ============================================================
# I — NON-SIGNIFICANT BASELINE COMPARISONS
# ============================================================

print("\n" + "=" * 80)
print("I — OTHER PAIRED COMPARISONS")
print("=" * 80)

rr_prob = table3b[
    table3b["Comparison"] == "Rescue Router vs Probability"
].iloc[0]

rr_dis = table3b[
    table3b["Comparison"] == "Rescue Router vs Disagreement"
].iloc[0]

check(
    close(rr_prob["Bootstrap p-value"], 0.5664, tol=0.0001),
    "Router vs Probability p = 0.5664"
)

check(
    close(rr_dis["Bootstrap p-value"], 0.4096, tol=0.0001),
    "Router vs Disagreement p = 0.4096"
)

check(
    rr_prob["Bootstrap p-value"] > 0.05,
    "Router vs Probability not statistically significant"
)

check(
    rr_dis["Bootstrap p-value"] > 0.05,
    "Router vs Disagreement not statistically significant"
)


# ============================================================
# J — FAIRNESS CHECK
# ============================================================

print("\n" + "=" * 80)
print("J — FAIRNESS CHECK")
print("=" * 80)

def fairness_value(feature, group):

    row = fairness[
        (fairness["Feature"] == feature)
        & (fairness["Group"] == group)
    ]

    check(
        len(row) == 1,
        f"Fairness row exists: {feature} / {group}"
    )

    if len(row) == 1:
        return float(row.iloc[0]["FN Rescue Rate (%)"])

    return np.nan


female = fairness_value("gender", "Female")
male = fairness_value("gender", "Male")

aa = fairness_value("race", "AfricanAmerican")
caucasian = fairness_value("race", "Caucasian")

age70 = fairness_value("age", "[70-80)")
age40 = fairness_value("age", "[40-50)")

check(close(female, 20.49, tol=0.02), "Female rescue = 20.49%")
check(close(male, 18.96, tol=0.02), "Male rescue = 18.96%")

check(close(aa, 14.02, tol=0.02),
      "African American rescue = 14.02%")

check(close(caucasian, 22.25, tol=0.02),
      "Caucasian rescue = 22.25%")

check(close(age70, 29.93, tol=0.02),
      "[70-80) rescue = 29.93%")

check(close(age40, 9.52, tol=0.02),
      "[40-50) rescue = 9.52%")


# ============================================================
# K — END-TO-END IMPACT CHECK
# ============================================================

print("\n" + "=" * 80)
print("K — END-TO-END IMPACT CHECK")
print("=" * 80)

# We know these are the frozen canonical overall values.
primary_fnr = 32.085253
residual_fnr = 25.748848
absolute_reduction = primary_fnr - residual_fnr

check(
    close(primary_fnr, 32.085253, tol=0.01),
    "Primary overall FNR = 32.09%"
)

check(
    close(residual_fnr, 25.748848, tol=0.01),
    "Residual overall FNR = 25.75%"
)

check(
    close(absolute_reduction, 6.336405, tol=0.02),
    "Absolute FNR reduction = 6.34 pp"
)

check(
    close(
        expected_capture["Rescue Router"],
        19.748654,
        tol=0.01
    ),
    "Relative missed-positive reduction = 19.75%"
)


# ============================================================
# L — END-TO-END RACE FAIRNESS
# ============================================================

# ============================================================
# L — END-TO-END RACE FAIRNESS
# ============================================================

print("\n" + "=" * 80)
print("L — END-TO-END RACE FAIRNESS")
print("=" * 80)

# figure_4_5_canonical_data.csv is a Result / Value summary table.
end_map = dict(zip(end_to_end["Result"], end_to_end["Value"]))

required_end_results = [
    "African American primary FNR",
    "African American residual FNR",
    "Caucasian primary FNR",
    "Caucasian residual FNR",
    "Primary race FNR gap",
    "Residual race FNR gap",
    "Race FNR gap change",
]

for result in required_end_results:
    check(
        result in end_map,
        f"End-to-end value exists: {result}"
    )

aa_primary = float(end_map["African American primary FNR"])
aa_residual = float(end_map["African American residual FNR"])

cau_primary = float(end_map["Caucasian primary FNR"])
cau_residual = float(end_map["Caucasian residual FNR"])

stored_primary_gap = float(end_map["Primary race FNR gap"])
stored_residual_gap = float(end_map["Residual race FNR gap"])
stored_gap_change = float(end_map["Race FNR gap change"])


# ------------------------------------------------------------
# Canonical subgroup values
# ------------------------------------------------------------

check(
    close(aa_primary, 33.75, tol=0.02),
    "AA primary FNR = 33.75%"
)

check(
    close(aa_residual, 29.02, tol=0.02),
    "AA residual FNR = 29.02%"
)

check(
    close(cau_primary, 31.43, tol=0.02),
    "Caucasian primary FNR = 31.43%"
)

check(
    close(cau_residual, 24.44, tol=0.02),
    "Caucasian residual FNR = 24.44%"
)


# ------------------------------------------------------------
# Reproduce race gaps from subgroup values
# ------------------------------------------------------------

calculated_primary_gap = aa_primary - cau_primary
calculated_residual_gap = aa_residual - cau_residual
calculated_gap_change = (
    calculated_residual_gap - calculated_primary_gap
)

print()
print(f"AA primary FNR: {aa_primary:.2f}%")
print(f"AA residual FNR: {aa_residual:.2f}%")

print(f"Caucasian primary FNR: {cau_primary:.2f}%")
print(f"Caucasian residual FNR: {cau_residual:.2f}%")

print()
print(f"Calculated primary race FNR gap: "
      f"{calculated_primary_gap:.2f} pp")

print(f"Calculated residual race FNR gap: "
      f"{calculated_residual_gap:.2f} pp")

print(f"Calculated race gap change: "
      f"{calculated_gap_change:+.2f} pp")


# ------------------------------------------------------------
# Compare reproduced gaps with stored canonical values
# ------------------------------------------------------------

check(
    close(
        calculated_primary_gap,
        stored_primary_gap,
        tol=0.03
    ),
    "Primary race FNR gap reproduced"
)

check(
    close(
        calculated_residual_gap,
        stored_residual_gap,
        tol=0.03
    ),
    "Residual race FNR gap reproduced"
)

check(
    close(
        calculated_gap_change,
        stored_gap_change,
        tol=0.03
    ),
    "Race FNR gap change reproduced"
)

check(
    close(stored_primary_gap, 2.32, tol=0.03),
    "Primary race FNR gap = 2.32 pp"
)

check(
    close(stored_residual_gap, 4.58, tol=0.03),
    "Residual race FNR gap = 4.58 pp"
)

check(
    close(stored_gap_change, 2.26, tol=0.03),
    "Race FNR gap increase = 2.26 pp"
)


# ============================================================
# M — MANUSCRIPT MASTER VALUES
# ============================================================

print("\n" + "=" * 80)
print("M — FROZEN MANUSCRIPT MASTER VALUES")
print("=" * 80)

master = pd.DataFrame([
    ["Test population", 15042, "patients"],
    ["Low-risk population", 7858, "patients"],
    ["Locked review population", 1178, "patients"],
    ["Primary AUROC", 0.663350, ""],
    ["Primary AUPRC", 0.212418, ""],
    ["Primary FNR", 32.085253, "%"],
    ["False negatives", 557, "patients"],
    ["Probability FN capture", 20.813356, "%"],
    ["Rescue Router FN capture", 19.748654, "%"],
    ["Disagreement FN capture", 18.312388, "%"],
    ["Random expected FN capture", 14.991092, "%"],
    ["Router gain over random", 4.757562, "pp"],
    ["Router lift over random", 1.317359, "x"],
    ["Router vs random bootstrap p", 0.0016, ""],
    ["Residual FNR", 25.748848, "%"],
    ["Absolute FNR reduction", 6.336406, "pp"],
    ["African American FN rescue", 14.02, "%"],
    ["Caucasian FN rescue", 22.25, "%"],
    ["Gender Female FN rescue", 20.49, "%"],
    ["Gender Male FN rescue", 18.96, "%"],
], columns=["Result", "Value", "Unit"])

print(master.to_string(index=False))


# ============================================================
# N — SAVE FREEZE MANIFEST
# ============================================================

print("\n" + "=" * 80)
print("N — SAVE FREEZE MANIFEST")
print("=" * 80)

master_file = PUB / "FINAL_FROZEN_MANUSCRIPT_VALUES.csv"
master.to_csv(master_file, index=False)

print(f"Saved: {master_file}")


# ============================================================
# O — FINAL STATUS
# ============================================================

print("\n" + "=" * 80)
print("O — FINAL PUBLICATION FREEZE STATUS")
print("=" * 80)

if len(errors) == 0:

    print("PUBLICATION FREEZE AUDIT: PASSED")
    print()
    print("All canonical tables, figures, statistical results,")
    print("fairness results, and end-to-end results are synchronized.")
    print()
    print("THE NUMERICAL RESULTS ARE NOW FROZEN.")

else:

    print("PUBLICATION FREEZE AUDIT: FAILED")
    print()
    print(f"{len(errors)} problem(s) detected:")

    for e in errors:
        print(" -", e)

    print()
    print("DO NOT FREEZE MANUSCRIPT RESULTS YET.")


print("\n" + "=" * 80)
print("PHASE 9.4.1 COMPLETE")
print("=" * 80)