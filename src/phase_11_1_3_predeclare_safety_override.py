from pathlib import Path
import pandas as pd
import json
import hashlib


TEST_PATH = Path("results/eligible/test_predictions.csv")
PHASE10_MANIFEST = Path(
    "results/eligible/agents/phase10_final_completion_manifest.json"
)

OUT_DIR = Path("results/eligible/safety")
OUT_DIR.mkdir(parents=True, exist_ok=True)

RULE_PATH = OUT_DIR / "phase11_1_3_safety_override_rule.json"


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


section("PHASE 11.1.3 — PRE-DECLARE SAFETY OVERRIDE CONDITION")


# -------------------------------------------------------------------------
# A — VERIFY FROZEN SYSTEM
# -------------------------------------------------------------------------

section("A — VERIFY PHASE 10 FROZEN STATE")

if not TEST_PATH.exists():
    raise FileNotFoundError(TEST_PATH)

if not PHASE10_MANIFEST.exists():
    raise FileNotFoundError(PHASE10_MANIFEST)

with PHASE10_MANIFEST.open() as f:
    manifest = json.load(f)

text = json.dumps(manifest)

checks = {
    "phase10_complete": "PHASE_10_COMPLETE" in text,
    "system_frozen": "FROZEN" in text,
    "release_locked": "LOCKED" in text,
}

for name, passed in checks.items():
    print(name + ":", "PASSED" if passed else "FAILED")

if not all(checks.values()):
    raise RuntimeError("Frozen Phase 10 verification failed.")

print("Phase 10 read-only boundary: PRESERVED")


# -------------------------------------------------------------------------
# B — LOAD ELIGIBLE ROUTING POPULATION
# -------------------------------------------------------------------------

section("B — DEFINE SAFETY-RULE CALIBRATION POPULATION")

df = pd.read_csv(TEST_PATH)

required = {
    "encounter_id",
    "actual_30d",
    "predicted_30d",
    "calibrated_probability",
    "uncertainty",
    "threshold",
}

missing = required - set(df.columns)

if missing:
    raise RuntimeError(f"Missing columns: {sorted(missing)}")

thresholds = df["threshold"].unique()

if len(thresholds) != 1:
    raise RuntimeError("Expected exactly one frozen threshold.")

threshold = float(thresholds[0])

if abs(threshold - 0.115) > 1e-12:
    raise RuntimeError(
        f"Expected threshold 0.115; found {threshold}"
    )

negative = df[df["predicted_30d"] == 0].copy()

negative["distance_below_threshold"] = (
    threshold - negative["calibrated_probability"]
)

print("Full test population:", len(df))
print("Primary-model-negative population:", len(negative))
print("Frozen threshold:", threshold)

if len(negative) != 7858:
    raise RuntimeError(
        f"Expected 7858 model-negative cases; found {len(negative)}"
    )

print("Calibration population verification: PASSED")


# -------------------------------------------------------------------------
# C — PROHIBIT OUTCOME-BASED RULE CONSTRUCTION
# -------------------------------------------------------------------------

section("C — SAFETY RULE INFORMATION BOUNDARY")

allowed_rule_fields = [
    "uncertainty",
    "calibrated_probability",
    "threshold",
    "distance_below_threshold",
]

prohibited_rule_fields = [
    "actual_30d",
    "case_type",
    "router_target",
]

print("Allowed rule inputs:")
for field in allowed_rule_fields:
    print(" -", field)

print("\nExplicitly prohibited rule inputs:")
for field in prohibited_rule_fields:
    print(" -", field)

print("\nGround truth used to construct condition: NO")
print("Case type used to construct condition: NO")
print("Router target used to construct condition: NO")

print("Information-boundary definition: PASSED")


# -------------------------------------------------------------------------
# D — DERIVE PRE-DECLARED THRESHOLDS
# -------------------------------------------------------------------------

section("D — DERIVE PRE-DECLARED SAFETY THRESHOLDS")

UNCERTAINTY_QUANTILE = 0.75
DISTANCE_QUANTILE = 0.25

uncertainty_threshold = float(
    negative["uncertainty"].quantile(UNCERTAINTY_QUANTILE)
)

distance_threshold = float(
    negative["distance_below_threshold"].quantile(
        DISTANCE_QUANTILE
    )
)

print("High-uncertainty quantile:", UNCERTAINTY_QUANTILE)
print(
    "High-uncertainty threshold:",
    round(uncertainty_threshold, 12)
)

print()

print("Near-threshold distance quantile:", DISTANCE_QUANTILE)
print(
    "Near-threshold maximum distance:",
    round(distance_threshold, 12)
)


# -------------------------------------------------------------------------
# E — DEFINE SAFETY OVERRIDE
# -------------------------------------------------------------------------

section("E — DEFINE PRE-DECLARED SAFETY OVERRIDE")

print("SAFETY_OVERRIDE if:")
print()
print(
    f"  uncertainty >= {uncertainty_threshold:.12f}"
)
print("                 OR")
print(
    f"  distance_below_threshold <= {distance_threshold:.12f}"
)

print()
print(
    "This rule applies only to cases with predicted_30d == 0."
)

print(
    "The rule forces additional review in the NEXT experiment; "
    "it does not modify the frozen Phase 10 routing decision."
)


# -------------------------------------------------------------------------
# F — RULE PREVALENCE WITHOUT OUTCOME EVALUATION
# -------------------------------------------------------------------------

section("F — RULE PREVALENCE")

high_uncertainty = (
    negative["uncertainty"] >= uncertainty_threshold
)

near_threshold = (
    negative["distance_below_threshold"] <= distance_threshold
)

override = high_uncertainty | near_threshold

n_high_uncertainty = int(high_uncertainty.sum())
n_near_threshold = int(near_threshold.sum())
n_override = int(override.sum())

override_rate = n_override / len(negative)

print("High-uncertainty cases:", n_high_uncertainty)
print("Near-threshold cases:", n_near_threshold)
print("Union safety-override cases:", n_override)
print(f"Safety-override rate: {override_rate:.6f}")

print()
print(
    "NOTE: Ground-truth outcomes are intentionally NOT evaluated "
    "in Phase 11.1.3."
)


# -------------------------------------------------------------------------
# G — FREEZE SAFETY CONDITION
# -------------------------------------------------------------------------

section("G — FREEZE PRE-DECLARED SAFETY CONDITION")

rule = {
    "phase": "11.1.3",
    "rule_version": "11.1.3",

    "status": "PREDECLARED_FROZEN",

    "purpose":
        "Pre-declared high-risk safety override for subsequent "
        "counterfactual routing evaluation.",

    "eligible_population": {
        "condition": "predicted_30d == 0",
        "population_size": int(len(negative)),
        "frozen_primary_threshold": threshold,
    },

    "information_boundary": {
        "ground_truth_allowed": False,
        "case_type_allowed": False,
        "router_target_allowed": False,
        "allowed_rule_inputs": allowed_rule_fields,
    },

    "conditions": {
        "HIGH_UNCERTAINTY": {
            "field": "uncertainty",
            "operator": ">=",
            "quantile": UNCERTAINTY_QUANTILE,
            "threshold": uncertainty_threshold,
        },

        "NEAR_PRIMARY_THRESHOLD": {
            "field": "distance_below_threshold",
            "operator": "<=",
            "quantile": DISTANCE_QUANTILE,
            "threshold": distance_threshold,
        },
    },

    "combination_rule":
        "HIGH_UNCERTAINTY OR NEAR_PRIMARY_THRESHOLD",

    "action":
        "FORCE_ADDITIONAL_HUMAN_REVIEW",

    "rule_prevalence": {
        "high_uncertainty_count": n_high_uncertainty,
        "near_threshold_count": n_near_threshold,
        "union_override_count": n_override,
        "union_override_rate": override_rate,
    },

    "evaluation_boundary": {
        "outcome_performance_evaluated_in_phase_11_1_3": False,
        "outcome_performance_reserved_for_phase_11_1_4": True,
    },

    "change_control": {
        "phase10_modified": False,
        "rule_must_not_be_changed_after_outcome_evaluation": True,
        "future_rule_change_requires_new_version": True,
    },

    "provenance": {
        "test_predictions_path": str(TEST_PATH),
        "test_predictions_sha256": sha256_file(TEST_PATH),
        "phase10_manifest_sha256": sha256_file(
            PHASE10_MANIFEST
        ),
    },
}

with RULE_PATH.open("w") as f:
    json.dump(rule, f, indent=2)

print("Frozen safety rule:", RULE_PATH)


# -------------------------------------------------------------------------
# H — VERIFY SAVED RULE
# -------------------------------------------------------------------------

section("H — VERIFY PRE-DECLARED RULE")

with RULE_PATH.open() as f:
    saved = json.load(f)

verify = {
    "status":
        saved["status"] == "PREDECLARED_FROZEN",

    "ground_truth_excluded":
        saved["information_boundary"][
            "ground_truth_allowed"
        ] is False,

    "outcome_not_evaluated":
        saved["evaluation_boundary"][
            "outcome_performance_evaluated_in_phase_11_1_3"
        ] is False,

    "phase10_unchanged":
        saved["change_control"]["phase10_modified"] is False,

    "population_lock":
        saved["eligible_population"]["population_size"] == 7858,

    "threshold_lock":
        abs(
            saved["eligible_population"][
                "frozen_primary_threshold"
            ] - 0.115
        ) < 1e-12,
}

for name, passed in verify.items():
    print(name + ":", "PASSED" if passed else "FAILED")

if not all(verify.values()):
    raise RuntimeError(
        "Phase 11.1.3 rule verification failed."
    )


section(
    "PHASE 11.1.3 COMPLETE — SAFETY CONDITION PRE-DECLARED"
)

print("Safety condition status: PREDECLARED_FROZEN")
print("Ground truth used to choose rule: NO")
print("Outcome performance evaluated: NO")
print("Phase 10 frozen system modified: NO")
print()
print(
    "Next: Phase 11.1.4 will evaluate this exact frozen "
    "condition without changing its thresholds."
)
