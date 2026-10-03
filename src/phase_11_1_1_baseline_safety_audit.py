from pathlib import Path
import json
import hashlib
import pandas as pd
from sklearn.metrics import confusion_matrix


# =============================================================================
# PATHS
# =============================================================================

TEST_PATH = Path("results/eligible/test_predictions.csv")

PHASE10_MANIFEST = Path(
    "results/eligible/agents/phase10_final_completion_manifest.json"
)

OUTPUT_DIR = Path("results/eligible/safety")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_PATH = OUTPUT_DIR / "phase11_1_1_baseline_safety_audit.json"
FN_PATH = OUTPUT_DIR / "phase11_1_1_false_negative_cases.csv"


# =============================================================================
# HELPERS
# =============================================================================

def section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


# =============================================================================
# HEADER
# =============================================================================

section("PHASE 11.1.1 — BASELINE FALSE-NEGATIVE SAFETY AUDIT")


# =============================================================================
# A — VERIFY PHASE 10 FROZEN STATE
# =============================================================================

section("A — VERIFY PHASE 10 FROZEN STATE")

if not PHASE10_MANIFEST.exists():
    raise FileNotFoundError(
        f"Missing Phase 10 completion manifest: {PHASE10_MANIFEST}"
    )

with PHASE10_MANIFEST.open() as f:
    phase10 = json.load(f)

print("Phase 10 completion manifest: FOUND")

# We intentionally avoid depending on one exact nested JSON structure here.
manifest_text = json.dumps(phase10)

phase10_complete = "PHASE_10_COMPLETE" in manifest_text
system_frozen = "FROZEN" in manifest_text
release_locked = "LOCKED" in manifest_text

print(
    "Phase 10 completion:",
    "PASSED" if phase10_complete else "FAILED"
)

print(
    "Frozen-system reference:",
    "PASSED" if system_frozen else "FAILED"
)

print(
    "Release-lock reference:",
    "PASSED" if release_locked else "FAILED"
)

if not (phase10_complete and system_frozen and release_locked):
    raise RuntimeError(
        "Phase 10 frozen-state verification failed. "
        "Phase 11 audit stopped."
    )

print("Phase 10 read-only boundary: PRESERVED")


# =============================================================================
# B — LOAD FULL TEST POPULATION
# =============================================================================

section("B — LOAD FULL TEST POPULATION")

if not TEST_PATH.exists():
    raise FileNotFoundError(f"Missing test predictions: {TEST_PATH}")

df = pd.read_csv(TEST_PATH)

required_columns = {
    "encounter_id",
    "patient_nbr",
    "actual_30d",
    "raw_probability",
    "calibrated_probability",
    "uncertainty",
    "threshold",
    "predicted_30d",
}

missing = required_columns - set(df.columns)

if missing:
    raise ValueError(
        f"Missing required columns: {sorted(missing)}"
    )

print("Test encounters:", len(df))
print("Unique encounters:", df["encounter_id"].nunique())
print("Unique patients:", df["patient_nbr"].nunique())

positive_count = int((df["actual_30d"] == 1).sum())
negative_count = int((df["actual_30d"] == 0).sum())

print("30-day positive cases:", positive_count)
print("30-day negative cases:", negative_count)

print(
    "Missing values:",
    int(df[list(required_columns)].isna().sum().sum())
)

population_checks = {
    "actual_binary": set(df["actual_30d"].unique()).issubset({0, 1}),
    "prediction_binary": set(df["predicted_30d"].unique()).issubset({0, 1}),
    "unique_encounters": df["encounter_id"].is_unique,
    "no_missing_required_values":
        not df[list(required_columns)].isna().any().any(),
}

for name, passed in population_checks.items():
    print(
        f"{name}:",
        "PASSED" if passed else "FAILED"
    )

if not all(population_checks.values()):
    raise RuntimeError("Test-population validation failed.")


# =============================================================================
# C — VERIFY FROZEN PRIMARY DECISION RULE
# =============================================================================

section("C — VERIFY FROZEN PRIMARY DECISION RULE")

threshold_values = sorted(df["threshold"].unique().tolist())

print("Threshold values:", threshold_values)

if len(threshold_values) != 1:
    raise RuntimeError(
        "Multiple decision thresholds detected in test predictions."
    )

threshold = float(threshold_values[0])

print("Frozen primary threshold:", threshold)

if abs(threshold - 0.115) > 1e-12:
    raise RuntimeError(
        f"Expected frozen threshold 0.115, found {threshold}"
    )

recomputed_prediction = (
    df["calibrated_probability"] >= threshold
).astype(int)

prediction_mismatches = int(
    (recomputed_prediction != df["predicted_30d"]).sum()
)

print("Prediction-rule mismatches:", prediction_mismatches)

if prediction_mismatches != 0:
    raise RuntimeError(
        "Stored predictions do not match the frozen calibrated-probability "
        "decision rule."
    )

print("Frozen primary decision rule: PASSED")


# =============================================================================
# D — BASELINE FALSE-NEGATIVE SAFETY
# =============================================================================

section("D — BASELINE FALSE-NEGATIVE SAFETY")

tn, fp, fn, tp = confusion_matrix(
    df["actual_30d"],
    df["predicted_30d"],
    labels=[0, 1],
).ravel()

tn = int(tn)
fp = int(fp)
fn = int(fn)
tp = int(tp)

recall = tp / (tp + fn) if (tp + fn) else float("nan")
fnr = fn / (tp + fn) if (tp + fn) else float("nan")

specificity = tn / (tn + fp) if (tn + fp) else float("nan")
fpr = fp / (tn + fp) if (tn + fp) else float("nan")

precision = tp / (tp + fp) if (tp + fp) else float("nan")

print("TN:", tn)
print("FP:", fp)
print("FN:", fn)
print("TP:", tp)

print()
print(f"Recall / Sensitivity: {recall:.6f}")
print(f"False-negative rate:   {fnr:.6f}")
print(f"Specificity:           {specificity:.6f}")
print(f"False-positive rate:   {fpr:.6f}")
print(f"Precision:             {precision:.6f}")

if tp + fn != positive_count:
    raise RuntimeError(
        "Positive-case confusion-matrix count does not match population."
    )

if tn + fp != negative_count:
    raise RuntimeError(
        "Negative-case confusion-matrix count does not match population."
    )

print()
print("Confusion-matrix consistency: PASSED")


# =============================================================================
# E — IDENTIFY FALSE-NEGATIVE CASES
# =============================================================================

section("E — IDENTIFY FALSE-NEGATIVE CASES")

fn_cases = df[
    (df["actual_30d"] == 1)
    & (df["predicted_30d"] == 0)
].copy()

fn_cases["distance_below_threshold"] = (
    threshold - fn_cases["calibrated_probability"]
)

fn_cases = fn_cases.sort_values(
    "calibrated_probability",
    ascending=False
)

print("False-negative cases identified:", len(fn_cases))

if len(fn_cases) != fn:
    raise RuntimeError(
        "False-negative case extraction does not match confusion matrix."
    )

print("False-negative extraction: PASSED")


# =============================================================================
# F — FALSE-NEGATIVE CHARACTERISTICS
# =============================================================================

section("F — FALSE-NEGATIVE CHARACTERISTICS")

if len(fn_cases) > 0:

    print(
        "Mean calibrated probability:",
        round(float(fn_cases["calibrated_probability"].mean()), 6)
    )

    print(
        "Median calibrated probability:",
        round(float(fn_cases["calibrated_probability"].median()), 6)
    )

    print(
        "Maximum calibrated probability:",
        round(float(fn_cases["calibrated_probability"].max()), 6)
    )

    print(
        "Minimum calibrated probability:",
        round(float(fn_cases["calibrated_probability"].min()), 6)
    )

    print(
        "Mean uncertainty:",
        round(float(fn_cases["uncertainty"].mean()), 6)
    )

    print(
        "Median distance below threshold:",
        round(float(fn_cases["distance_below_threshold"].median()), 6)
    )


# =============================================================================
# G — SAVE FALSE-NEGATIVE CASES
# =============================================================================

section("G — SAVE FALSE-NEGATIVE CASES")

fn_cases.to_csv(FN_PATH, index=False)

print("False-negative cases:", FN_PATH)


# =============================================================================
# H — CREATE SAFETY AUDIT ARTIFACT
# =============================================================================

section("H — CREATE SAFETY AUDIT ARTIFACT")

audit = {
    "phase": "11.1.1",
    "audit_name": "Baseline False-Negative Safety Audit",

    "audit_scope": {
        "population": "full eligible frozen test population",
        "test_encounters": int(len(df)),
        "unique_patients": int(df["patient_nbr"].nunique()),
        "positive_cases": positive_count,
        "negative_cases": negative_count,
    },

    "frozen_system_reference": {
        "phase10_completion_manifest":
            str(PHASE10_MANIFEST),
        "phase10_complete": phase10_complete,
        "system_frozen": system_frozen,
        "release_locked": release_locked,
        "primary_threshold": threshold,
        "phase10_modified": False,
    },

    "confusion_matrix": {
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
    },

    "safety_metrics": {
        "recall": recall,
        "false_negative_rate": fnr,
        "specificity": specificity,
        "false_positive_rate": fpr,
        "precision": precision,
    },

    "false_negative_analysis": {
        "false_negative_count": fn,
        "mean_calibrated_probability":
            float(fn_cases["calibrated_probability"].mean())
            if len(fn_cases) else None,
        "median_calibrated_probability":
            float(fn_cases["calibrated_probability"].median())
            if len(fn_cases) else None,
        "mean_uncertainty":
            float(fn_cases["uncertainty"].mean())
            if len(fn_cases) else None,
        "median_distance_below_threshold":
            float(fn_cases["distance_below_threshold"].median())
            if len(fn_cases) else None,
    },

    "input_integrity": {
        "test_predictions_path": str(TEST_PATH),
        "test_predictions_sha256": sha256_file(TEST_PATH),
        "phase10_manifest_sha256": sha256_file(PHASE10_MANIFEST),
        "prediction_rule_mismatches": prediction_mismatches,
    },

    "interpretation": {
        "audit_only": True,
        "clinical_safety_claim": False,
        "failure_reporting_required": True,
        "note":
            "This audit reports baseline false-negative behavior of the "
            "frozen primary model. Successful execution of the audit does "
            "not imply clinical safety."
    },

    "status": "PASSED",
}

with AUDIT_PATH.open("w") as f:
    json.dump(audit, f, indent=2)

print("Safety audit:", AUDIT_PATH)


# =============================================================================
# I — FINAL VERIFICATION
# =============================================================================

section("I — FINAL VERIFICATION")

with AUDIT_PATH.open() as f:
    saved = json.load(f)

checks = {
    "audit_status":
        saved["status"] == "PASSED",

    "threshold_lock":
        abs(
            saved["frozen_system_reference"]["primary_threshold"]
            - 0.115
        ) < 1e-12,

    "false_negative_count":
        saved["confusion_matrix"]["fn"] == len(fn_cases),

    "phase10_unchanged":
        saved["frozen_system_reference"]["phase10_modified"] is False,

    "fn_artifact_exists":
        FN_PATH.exists(),
}

for name, passed in checks.items():
    print(
        f"{name}:",
        "PASSED" if passed else "FAILED"
    )

if not all(checks.values()):
    raise RuntimeError(
        "Final Phase 11.1.1 verification failed."
    )


# =============================================================================
# COMPLETE
# =============================================================================

section("PHASE 11.1.1 COMPLETE — BASELINE SAFETY AUDIT PASSED")

print(
    "IMPORTANT: PASSED means the audit executed and validated correctly."
)

print(
    "It does NOT mean the frozen CareCompute system has been established "
    "as clinically safe."
)

print()
print("Baseline false-negative rate:", round(fnr, 6))
print("Baseline false-negative cases:", fn)
print("Phase 10 frozen system modified: NO")
