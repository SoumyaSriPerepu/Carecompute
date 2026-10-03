from pathlib import Path
import pandas as pd
import hashlib
import sys
from datetime import datetime, timezone


# =============================================================================
# PHASE 9.4.2 — FINAL PUBLICATION PACKAGE / MANIFEST
# =============================================================================

print("=" * 80)
print("PHASE 9.4.2 — FINAL PUBLICATION PACKAGE / MANIFEST")
print("=" * 80)


# =============================================================================
# PATHS
# =============================================================================

PUBLICATION_DIR = Path("results/eligible/publication")
FIGURE_DIR = PUBLICATION_DIR / "figures"

MANIFEST_PATH = PUBLICATION_DIR / "publication_manifest.csv"
FROZEN_RESULTS_PATH = PUBLICATION_DIR / "frozen_key_results.csv"
FREEZE_SUMMARY_PATH = PUBLICATION_DIR / "publication_freeze_summary.txt"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def print_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def sha256_file(path):
    """
    Calculate SHA-256 checksum so we can detect accidental
    modification of frozen publication files later.
    """
    sha256 = hashlib.sha256()

    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(block)

    return sha256.hexdigest()


def assert_close(name, observed, expected, tolerance=1e-4):
    passed = abs(float(observed) - float(expected)) <= tolerance

    print(
        f"{name}: observed={float(observed):.6f} "
        f"expected={float(expected):.6f} "
        f"{'PASSED' if passed else 'FAILED'}"
    )

    if not passed:
        raise AssertionError(
            f"{name} failed: observed={observed}, expected={expected}"
        )


# =============================================================================
# REQUIRED PUBLICATION FILES
# =============================================================================

required_files = {

    # -------------------------------------------------------------------------
    # TABLES
    # -------------------------------------------------------------------------

    "Table 1 — Primary model performance":
        PUBLICATION_DIR / "table_1_primary_model_performance.csv",

    "Table 2 — Review strategies":
        PUBLICATION_DIR / "table_2_final_review_strategies.csv",

    "Table 3A — Bootstrap confidence intervals":
        PUBLICATION_DIR / "table_3a_final_bootstrap_ci.csv",

    "Table 3B — Paired bootstrap comparisons":
        PUBLICATION_DIR / "table_3b_final_paired_comparisons.csv",

    # -------------------------------------------------------------------------
    # FIGURE 1
    # -------------------------------------------------------------------------

    "Figure 1 — FN capture vs review budget PNG":
        FIGURE_DIR / "figure_1_canonical_fn_capture_vs_review_budget.png",

    "Figure 1 — FN capture vs review budget PDF":
        FIGURE_DIR / "figure_1_canonical_fn_capture_vs_review_budget.pdf",

    "Figure 1 — Source data":
        FIGURE_DIR / "figure_1_canonical_data.csv",

    # -------------------------------------------------------------------------
    # FIGURE 2
    # -------------------------------------------------------------------------

    "Figure 2 — Locked bootstrap PNG":
        FIGURE_DIR / "figure_2_canonical_locked_15pct_bootstrap.png",

    "Figure 2 — Locked bootstrap PDF":
        FIGURE_DIR / "figure_2_canonical_locked_15pct_bootstrap.pdf",

    "Figure 2 — Source data":
        FIGURE_DIR / "figure_2_canonical_data.csv",

    # -------------------------------------------------------------------------
    # FIGURE 3
    # -------------------------------------------------------------------------

    "Figure 3A — Gender fairness PNG":
        FIGURE_DIR / "figure_3a_canonical_gender_fn_rescue.png",

    "Figure 3A — Gender fairness PDF":
        FIGURE_DIR / "figure_3a_canonical_gender_fn_rescue.pdf",

    "Figure 3B — Race fairness PNG":
        FIGURE_DIR / "figure_3b_canonical_race_fn_rescue.png",

    "Figure 3B — Race fairness PDF":
        FIGURE_DIR / "figure_3b_canonical_race_fn_rescue.pdf",

    "Figure 3C — Age fairness PNG":
        FIGURE_DIR / "figure_3c_canonical_age_fn_rescue.png",

    "Figure 3C — Age fairness PDF":
        FIGURE_DIR / "figure_3c_canonical_age_fn_rescue.pdf",

    "Figure 3 — Fairness source data":
        FIGURE_DIR / "figure_3_canonical_fairness_data.csv",

    # -------------------------------------------------------------------------
    # FIGURE 4
    # -------------------------------------------------------------------------

    "Figure 4 — End-to-end impact PNG":
        FIGURE_DIR / "figure_4_canonical_end_to_end_impact.png",

    "Figure 4 — End-to-end impact PDF":
        FIGURE_DIR / "figure_4_canonical_end_to_end_impact.pdf",

    # -------------------------------------------------------------------------
    # FIGURE 5
    # -------------------------------------------------------------------------

    "Figure 5 — Race fairness impact PNG":
        FIGURE_DIR / "figure_5_canonical_race_fairness.png",

    "Figure 5 — Race fairness impact PDF":
        FIGURE_DIR / "figure_5_canonical_race_fairness.pdf",

    "Figures 4–5 — Source data":
        FIGURE_DIR / "figure_4_5_canonical_data.csv",
}


# =============================================================================
# A — DIRECTORY CHECK
# =============================================================================

print_section("A — PUBLICATION DIRECTORY CHECK")

if not PUBLICATION_DIR.exists():
    raise FileNotFoundError(
        f"Publication directory does not exist: {PUBLICATION_DIR}"
    )

print(f"Publication directory: {PUBLICATION_DIR}")
print("PASSED")


# =============================================================================
# B — REQUIRED FILE CHECK
# =============================================================================

print_section("B — REQUIRED PUBLICATION FILE CHECK")

missing_files = []

for description, path in required_files.items():

    if path.exists():
        print(f"{description}: FOUND")
    else:
        print(f"{description}: MISSING")
        missing_files.append(path)

if missing_files:

    print("\nMissing files:")

    for path in missing_files:
        print(f" - {path}")

    raise FileNotFoundError(
        "Publication package is incomplete."
    )

print("\nAll required publication files: PASSED")


# =============================================================================
# C — LOAD FINAL CANONICAL TABLES
# =============================================================================

print_section("C — LOAD FINAL CANONICAL TABLES")

table1 = pd.read_csv(
    PUBLICATION_DIR / "table_1_primary_model_performance.csv"
)

table2 = pd.read_csv(
    PUBLICATION_DIR / "table_2_final_review_strategies.csv"
)

table3a = pd.read_csv(
    PUBLICATION_DIR / "table_3a_final_bootstrap_ci.csv"
)

table3b = pd.read_csv(
    PUBLICATION_DIR / "table_3b_final_paired_comparisons.csv"
)

print("Table 1 shape:", table1.shape)
print("Table 2 shape:", table2.shape)
print("Table 3A shape:", table3a.shape)
print("Table 3B shape:", table3b.shape)

print("\nCanonical tables loaded successfully.")


# =============================================================================
# D — FINAL PRIMARY MODEL FREEZE CHECK
# =============================================================================

print_section("D — FINAL PRIMARY MODEL FREEZE CHECK")

metric_lookup = dict(
    zip(
        table1["Metric"],
        table1["Value"]
    )
)

assert_close(
    "Decision threshold",
    metric_lookup["Decision threshold"],
    0.115
)

assert_close(
    "AUROC",
    metric_lookup["AUROC"],
    0.663350
)

assert_close(
    "AUPRC",
    metric_lookup["AUPRC"],
    0.212418
)

assert_close(
    "Recall (%)",
    metric_lookup["Recall (%)"],
    67.914747
)

assert_close(
    "False-negative rate (%)",
    metric_lookup["False-negative rate (%)"],
    32.085253
)

assert_close(
    "False negatives",
    metric_lookup["False negatives"],
    557
)

assert_close(
    "True positives",
    metric_lookup["True positives"],
    1179
)

assert_close(
    "True negatives",
    metric_lookup["True negatives"],
    7301
)

assert_close(
    "False positives",
    metric_lookup["False positives"],
    6005
)


# =============================================================================
# E — FINAL REVIEW STRATEGY FREEZE CHECK
# =============================================================================

print_section("E — FINAL REVIEW STRATEGY FREEZE CHECK")

expected_review_results = {
    "Probability": 20.81,
    "Rescue Router": 19.75,
    "Disagreement": 18.31,
    "Random": 14.99,
}

for method, expected_value in expected_review_results.items():

    row = table2[
        table2["Review Strategy"] == method
    ]

    if len(row) != 1:
        raise AssertionError(
            f"Expected exactly one row for {method}"
        )

    observed = row.iloc[0]["FN Capture Rate (%)"]

    assert_close(
    f"{method} FN capture",
    observed,
    expected_value,
    tolerance=0.005
)

    reviewed = row.iloc[0]["Patients Reviewed"]

    assert_close(
        f"{method} patients reviewed",
        reviewed,
        1178
    )


# =============================================================================
# F — PROBABILITY TIE RULE FREEZE
# =============================================================================

print_section("F — PROBABILITY TIE RULE FREEZE")

probability_row = table2[
    table2["Review Strategy"] == "Probability"
].iloc[0]

tie_rule = str(
    probability_row["Ranking / Tie Rule"]
)

expected_tie_rule = (
    "Expected random selection within cutoff tie"
)

print("Observed tie rule:")
print(tie_rule)

if tie_rule != expected_tie_rule:
    raise AssertionError(
        "Probability tie rule has changed."
    )

print("\nProbability tie rule: PASSED")


# =============================================================================
# G — FINAL BOOTSTRAP FREEZE CHECK
# =============================================================================

print_section("G — FINAL BOOTSTRAP FREEZE CHECK")

expected_bootstrap = {
    "Probability": 20.81,
    "Rescue Router": 19.75,
    "Disagreement": 18.31,
    "Random": 14.99,
}

for method, expected_value in expected_bootstrap.items():

    row = table3a[
        table3a["Review Strategy"] == method
    ]

    if len(row) != 1:
        raise AssertionError(
            f"Missing bootstrap row for {method}"
        )

    observed = row.iloc[0]["Point FN Capture (%)"]

    assert_close(
    f"{method} bootstrap point",
    observed,
    expected_value,
    tolerance=0.005
)


# =============================================================================
# H — KEY PAIRED BOOTSTRAP CLAIMS
# =============================================================================

print_section("H — KEY PAIRED BOOTSTRAP CLAIMS")

router_random = table3b[
    table3b["Comparison"] == "Rescue Router vs Random"
]

if len(router_random) != 1:
    raise AssertionError(
        "Router vs Random comparison missing."
    )

router_random = router_random.iloc[0]

assert_close(
    "Router vs Random mean difference (pp)",
    router_random["Bootstrap Mean Difference (pp)"],
    4.99,
    tolerance=0.01
)

assert_close(
    "Router vs Random CI lower",
    router_random["95% CI Lower (pp)"],
    1.76,
    tolerance=0.01
)

assert_close(
    "Router vs Random CI upper",
    router_random["95% CI Upper (pp)"],
    8.28,
    tolerance=0.01
)

assert_close(
    "Router vs Random p-value",
    router_random["Bootstrap p-value"],
    0.0016
)

if router_random["95% CI Lower (pp)"] <= 0:
    raise AssertionError(
        "Router vs Random confidence interval includes zero."
    )

print("\nRouter vs Random statistical claim: PASSED")


# =============================================================================
# I — CREATE PUBLICATION MANIFEST
# =============================================================================

print_section("I — CREATE PUBLICATION MANIFEST")

manifest_rows = []

for description, path in required_files.items():

    file_type = path.suffix.lower().replace(".", "")

    manifest_rows.append(
        {
            "artifact": description,
            "relative_path": str(path),
            "file_type": file_type,
            "file_size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "status": "FROZEN",
        }
    )

manifest = pd.DataFrame(manifest_rows)

manifest.to_csv(
    MANIFEST_PATH,
    index=False
)

print(manifest[
    [
        "artifact",
        "file_type",
        "status"
    ]
].to_string(index=False))

print("\nManifest entries:", len(manifest))


# =============================================================================
# J — CREATE FROZEN KEY RESULT FILE
# =============================================================================

print_section("J — CREATE FROZEN KEY RESULT FILE")

frozen_results = pd.DataFrame(
    [
        ["Full test population", 15042, "patients"],
        ["Low-risk population", 7858, "patients"],
        ["Locked low-risk review budget", 15.00, "%"],
        ["Patients reviewed", 1178, "patients"],

        ["Decision threshold", 0.115, "probability"],
        ["Primary model AUROC", 0.663350, "AUROC"],
        ["Primary model AUPRC", 0.212418, "AUPRC"],
        ["Primary model recall", 67.914747, "%"],
        ["Primary model precision", 16.411470, "%"],
        ["Primary model FNR", 32.085253, "%"],
        ["Primary model specificity", 54.869983, "%"],

        ["False negatives", 557, "patients"],
        ["True positives", 1179, "patients"],
        ["True negatives", 7301, "patients"],
        ["False positives", 6005, "patients"],

        ["Probability FN capture", 20.813356, "%"],
        ["Rescue Router FN capture", 19.748654, "%"],
        ["Disagreement FN capture", 18.312388, "%"],
        ["Random expected FN capture", 14.991092, "%"],

        ["Router absolute gain over random", 4.757562, "percentage points"],
        ["Router lift over random", 1.317359, "x"],

        ["Router vs Random bootstrap difference", 4.99, "percentage points"],
        ["Router vs Random CI lower", 1.76, "percentage points"],
        ["Router vs Random CI upper", 8.28, "percentage points"],
        ["Router vs Random p-value", 0.0016, "p-value"],

        ["Router vs Probability p-value", 0.5664, "p-value"],
        ["Router vs Disagreement p-value", 0.4096, "p-value"],

        ["Female FN rescue", 20.49, "%"],
        ["Male FN rescue", 18.96, "%"],

        ["African American FN rescue", 14.02, "%"],
        ["Caucasian FN rescue", 22.25, "%"],
        ["AA-Caucasian conditional rescue gap", -8.23, "percentage points"],

        ["Age 70-80 FN rescue", 29.93, "%"],
        ["Age 40-50 FN rescue", 9.52, "%"],

        ["Primary overall FNR", 32.085253, "%"],
        ["Residual overall FNR", 25.748848, "%"],
        ["Absolute FNR reduction", 6.336406, "percentage points"],
        ["Relative missed-positive reduction", 19.748654, "%"],

        ["African American primary FNR", 33.75, "%"],
        ["African American residual FNR", 29.02, "%"],
        ["Caucasian primary FNR", 31.43, "%"],
        ["Caucasian residual FNR", 24.44, "%"],

        ["Primary race FNR gap", 2.32, "percentage points"],
        ["Residual race FNR gap", 4.58, "percentage points"],
        ["Race FNR gap change", 2.26, "percentage points"],
    ],
    columns=[
        "Result",
        "Value",
        "Unit"
    ]
)

frozen_results.to_csv(
    FROZEN_RESULTS_PATH,
    index=False
)

print(frozen_results.to_string(index=False))


# =============================================================================
# K — CREATE HUMAN-READABLE FREEZE SUMMARY
# =============================================================================

print_section("K — CREATE PUBLICATION FREEZE SUMMARY")

freeze_time = datetime.now(timezone.utc).isoformat()

summary = f"""
CARECOMPUTE — PUBLICATION FREEZE SUMMARY
========================================

Freeze timestamp (UTC):
{freeze_time}

STATUS:
FROZEN

FULL TEST POPULATION:
15,042 patients

LOW-RISK POPULATION:
7,858 patients

LOCKED REVIEW OPERATING POINT:
15% of low-risk population
1,178 patients reviewed

PRIMARY MODEL
-------------
Decision threshold: 0.115
AUROC: 0.663350
AUPRC: 0.212418
Recall: 67.91%
Precision: 16.41%
False-negative rate: 32.09%

Confusion matrix:
TN = 7,301
FP = 6,005
FN = 557
TP = 1,179

CANONICAL REVIEW STRATEGIES
---------------------------
Probability:
20.81% FN capture
Tie handling:
Expected random selection within cutoff tie

Rescue Router:
19.75% FN capture
Deterministic score ranking

Disagreement:
18.31% FN capture
Deterministic score ranking

Random:
14.99% expected FN capture

RESCUE ROUTER VS RANDOM
-----------------------
Absolute locked gain:
4.76 percentage points

Lift:
1.317x

Paired bootstrap mean difference:
4.99 percentage points

95% CI:
[1.76, 8.28] percentage points

p-value:
0.0016

Probability router > random:
99.92%

END-TO-END PERFECT-REVIEW SIMULATION
------------------------------------
Primary FNR:
32.09%

Residual FNR:
25.75%

Absolute FNR reduction:
6.34 percentage points

Relative reduction in missed positives:
19.75%

FAIRNESS FINDINGS
-----------------
Female conditional FN rescue:
20.49%

Male conditional FN rescue:
18.96%

African American conditional FN rescue:
14.02%

Caucasian conditional FN rescue:
22.25%

African American - Caucasian rescue gap:
-8.23 percentage points

African American primary FNR:
33.75%

African American residual FNR:
29.02%

Caucasian primary FNR:
31.43%

Caucasian residual FNR:
24.44%

Primary race FNR gap:
2.32 percentage points

Residual race FNR gap:
4.58 percentage points

Gap change:
+2.26 percentage points


PUBLICATION FREEZE RULES
========================

1. Do not retrain the frozen primary model for the current manuscript.

2. Do not change the locked decision threshold of 0.115.

3. Do not change the locked review budget of 15% of the low-risk
   population.

4. Do not change the canonical probability tie-handling rule.

5. Do not replace canonical test results with more favorable
   alternative tie resolutions.

6. Do not modify final test labels or use the final test set for
   additional model selection.

7. New AI-agent experiments must consume the frozen model outputs
   without changing these frozen publication results.

8. Cloud deployment must preserve the frozen inference and rescue
   logic unless explicitly treated as a new experiment/version.

9. Fairness findings must be reported transparently, including the
   observed widening of the African American–Caucasian residual FNR
   gap in the perfect-review simulation.

10. Any future model version must receive a new version identifier
    and must not overwrite this publication package.


NEXT DEVELOPMENT STAGE
======================

PHASE 10 — CARECOMPUTE AI AGENT SYSTEM

The frozen ML system becomes an input to the agent layer.

The AI-agent layer must not autonomously diagnose patients or modify
ground-truth outcomes. It will support human review by summarizing,
explaining, prioritizing, and monitoring cases.

"""

with open(
    FREEZE_SUMMARY_PATH,
    "w",
    encoding="utf-8"
) as f:
    f.write(summary.strip() + "\n")

print(summary)


# =============================================================================
# L — VERIFY OUTPUT FILES
# =============================================================================

print_section("L — VERIFY GENERATED FREEZE FILES")

generated_files = [
    MANIFEST_PATH,
    FROZEN_RESULTS_PATH,
    FREEZE_SUMMARY_PATH,
]

for path in generated_files:

    if not path.exists():
        raise FileNotFoundError(
            f"Failed to create {path}"
        )

    if path.stat().st_size == 0:
        raise AssertionError(
            f"Generated file is empty: {path}"
        )

    print(
        f"{path}: CREATED "
        f"({path.stat().st_size:,} bytes)"
    )


# =============================================================================
# M — FINAL STATUS
# =============================================================================

print_section("M — FINAL STATUS")

print("Publication artifacts verified.")
print("Canonical numerical results verified.")
print("Probability tie rule verified.")
print("Bootstrap statistical claims verified.")
print("SHA-256 hashes generated.")
print("Frozen result registry generated.")
print("Publication freeze summary generated.")

print("\n" + "=" * 80)
print("PHASE 9.4.2 COMPLETE — PASSED")
print("=" * 80)

print("\nCARECOMPUTE ML EVALUATION PIPELINE: FROZEN")
print("NEXT PHASE: PHASE 10 — AI AGENT SYSTEM")

print("\nFILES SAVED")
print("-" * 80)
print(MANIFEST_PATH)
print(FROZEN_RESULTS_PATH)
print(FREEZE_SUMMARY_PATH)

sys.exit(0)