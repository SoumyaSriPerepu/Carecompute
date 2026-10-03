from pathlib import Path
import pandas as pd
import numpy as np

# ============================================================
# PHASE 9.2.1 — FINAL PRIMARY MODEL TABLE
# ============================================================

RESULTS = Path("results/eligible")
OUT = RESULTS / "publication"
OUT.mkdir(parents=True, exist_ok=True)

INPUT = RESULTS / "final_test_metrics.csv"

print("=" * 80)
print("PHASE 9.2.1 — FINAL PRIMARY MODEL TABLE")
print("=" * 80)

# ------------------------------------------------------------
# 1. LOAD FINAL TEST METRICS
# ------------------------------------------------------------

df = pd.read_csv(INPUT)

print("\nInput:")
print(df.to_string(index=False))

if len(df) != 1:
    raise ValueError(
        f"Expected exactly 1 final-test row, found {len(df)}."
    )

row = df.iloc[0]

# ------------------------------------------------------------
# 2. INTEGRITY CHECKS
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("A — INTEGRITY CHECKS")
print("=" * 80)

tn = int(row["TN"])
fp = int(row["FP"])
fn = int(row["FN"])
tp = int(row["TP"])

n = tn + fp + fn + tp
positives = tp + fn
negatives = tn + fp

print("Test patients:", n)
print("Actual positives:", positives)
print("Actual negatives:", negatives)

print("\nConfusion matrix:")
print("TN:", tn)
print("FP:", fp)
print("FN:", fn)
print("TP:", tp)

checks = {
    "Test size = 15042": n == 15042,
    "FN = 557": fn == 557,
    "TP = 1179": tp == 1179,
    "TN = 7301": tn == 7301,
    "FP = 6005": fp == 6005,
}

for name, passed in checks.items():
    print(
        f"{name}: "
        f"{'PASSED' if passed else 'FAILED'}"
    )

if not all(checks.values()):
    raise ValueError(
        "Primary-model integrity check failed."
    )

# ------------------------------------------------------------
# 3. RECOMPUTE CONFUSION-MATRIX METRICS
# ------------------------------------------------------------

recall_check = tp / (tp + fn)
precision_check = tp / (tp + fp)
specificity_check = tn / (tn + fp)
fnr_check = fn / (fn + tp)

print("\n" + "=" * 80)
print("B — METRIC REPRODUCTION")
print("=" * 80)

metric_checks = {
    "Recall": np.isclose(
        recall_check,
        float(row["Recall"]),
        atol=1e-6,
    ),
    "Precision": np.isclose(
        precision_check,
        float(row["Precision"]),
        atol=1e-6,
    ),
    "Specificity": np.isclose(
        specificity_check,
        float(row["Specificity"]),
        atol=1e-6,
    ),
    "FNR": np.isclose(
        fnr_check,
        float(row["FNR"]),
        atol=1e-6,
    ),
}

for name, passed in metric_checks.items():
    print(
        f"{name}: "
        f"{'PASSED' if passed else 'FAILED'}"
    )

if not all(metric_checks.values()):
    raise ValueError(
        "Stored metrics do not reproduce from confusion matrix."
    )

# ------------------------------------------------------------
# 4. CREATE PUBLICATION TABLE
# ------------------------------------------------------------

table = pd.DataFrame(
    [
        ["Decision threshold", float(row["threshold"])],
        ["AUROC", float(row["AUROC"])],
        ["AUPRC", float(row["AUPRC"])],
        ["Recall (%)", float(row["Recall"]) * 100],
        ["Precision (%)", float(row["Precision"]) * 100],
        ["F1 score", float(row["F1"])],
        ["False-negative rate (%)", float(row["FNR"]) * 100],
        ["Specificity (%)", float(row["Specificity"]) * 100],
        ["Brier score", float(row["Brier"])],
        ["True negatives", tn],
        ["False positives", fp],
        ["False negatives", fn],
        ["True positives", tp],
    ],
    columns=["Metric", "Value"],
)

print("\n" + "=" * 80)
print("C — FINAL PRIMARY MODEL TABLE")
print("=" * 80)

print(table.to_string(index=False))

output_file = OUT / "table_1_primary_model_performance.csv"
table.to_csv(output_file, index=False)

# ------------------------------------------------------------
# 5. CORE VALUES FOR MANUSCRIPT
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("D — MANUSCRIPT VALUES")
print("=" * 80)

print(f"AUROC: {row['AUROC']:.3f}")
print(f"AUPRC: {row['AUPRC']:.3f}")
print(f"Recall: {row['Recall'] * 100:.2f}%")
print(f"Precision: {row['Precision'] * 100:.2f}%")
print(f"FNR: {row['FNR'] * 100:.2f}%")
print(f"Specificity: {row['Specificity'] * 100:.2f}%")
print(f"False negatives: {fn}")
print(f"True positives: {tp}")

print("\n" + "=" * 80)
print("FILE SAVED")
print("=" * 80)

print(output_file)

print("\n" + "=" * 80)
print("PHASE 9.2.1 COMPLETE — PASSED")
print("=" * 80)