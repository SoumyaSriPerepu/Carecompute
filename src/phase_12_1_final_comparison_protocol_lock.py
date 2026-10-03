from pathlib import Path
import pandas as pd
import json
import hashlib


# ============================================================
# PATHS
# ============================================================

TEST_PATH = Path(
    "results/eligible/test_predictions.csv"
)

E2E_PATH = Path(
    "results/eligible/final_test_end_to_end_patient_predictions.csv"
)

ROUTER_PATH = Path(
    "results/eligible/final_test_router_predictions.csv"
)

PHASE10_PATH = Path(
    "results/eligible/agents/phase10_final_completion_manifest.json"
)

PHASE11_PATH = Path(
    "results/eligible/"
    "phase11_safety_fairness_robustness_closure_manifest.json"
)

OUT_DIR = Path(
    "results/eligible/final_comparison"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

PROTOCOL_PATH = (
    OUT_DIR /
    "phase12_1_final_comparison_protocol.json"
)


# ============================================================
# HELPERS
# ============================================================

def section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def load_json(path):
    with path.open() as f:
        return json.load(f)


# ============================================================
# HEADER
# ============================================================

section(
    "PHASE 12.1 — FINAL SCIENTIFIC COMPARISON PROTOCOL LOCK"
)


# ============================================================
# A — VERIFY REQUIRED FROZEN ARTIFACTS
# ============================================================

section("A — VERIFY REQUIRED FROZEN ARTIFACTS")

required = [
    TEST_PATH,
    E2E_PATH,
    ROUTER_PATH,
    PHASE10_PATH,
    PHASE11_PATH,
]

for path in required:

    if not path.exists():
        raise FileNotFoundError(path)

    print("FOUND:", path)


print("Required artifact presence: PASSED")


# ============================================================
# B — VERIFY PHASE 10 AND PHASE 11 CLOSURES
# ============================================================

section("B — VERIFY PRIOR PHASE CLOSURES")

phase10 = load_json(PHASE10_PATH)
phase11 = load_json(PHASE11_PATH)


phase10_complete = (
    phase10.get("status") == "PHASE_10_COMPLETE"
    or phase10.get("completion_status") == "PASSED"
    or phase10.get("phase10_complete") is True
)

phase11_complete = (
    phase11.get("status") == "PHASE_11_COMPLETE"
)


print(
    "Phase 10 frozen system:",
    "PASSED" if phase10_complete else "UNVERIFIED"
)

print(
    "Phase 11 audit closure:",
    "PASSED" if phase11_complete else "FAILED"
)


if not phase11_complete:
    raise RuntimeError(
        "Phase 11 closure not verified."
    )


# ============================================================
# C — LOAD FINAL TEST POPULATION
# ============================================================

section("C — LOAD FINAL TEST POPULATION")

test = pd.read_csv(TEST_PATH)
e2e = pd.read_csv(E2E_PATH)
router = pd.read_csv(ROUTER_PATH)


print("Test rows:", len(test))
print("End-to-end rows:", len(e2e))
print("Router-negative rows:", len(router))


if len(test) != 15042:
    raise RuntimeError(
        "Unexpected final test population."
    )


if test["encounter_id"].nunique() != len(test):
    raise RuntimeError(
        "Duplicate encounter IDs in test set."
    )


print(
    "Unique encounters:",
    test["encounter_id"].nunique()
)

print(
    "Unique patients:",
    test["patient_nbr"].nunique()
)

print(
    "Actual positives:",
    int(test["actual_30d"].sum())
)

print(
    "Actual negatives:",
    int(
        len(test)
        - test["actual_30d"].sum()
    )
)

print("Final test population: PASSED")


# ============================================================
# D — VERIFY FINAL TEST ALIGNMENT
# ============================================================

section("D — VERIFY FINAL TEST ALIGNMENT")


test_ids = set(test["encounter_id"])
e2e_ids = set(e2e["encounter_id"])


print(
    "Missing E2E encounters:",
    len(test_ids - e2e_ids)
)

print(
    "Unexpected E2E encounters:",
    len(e2e_ids - test_ids)
)


if test_ids != e2e_ids:
    raise RuntimeError(
        "Final test / E2E encounter mismatch."
    )


print("Encounter alignment: PASSED")


# ============================================================
# E — VERIFY FROZEN PRIMARY MODEL
# ============================================================

section("E — VERIFY FROZEN PRIMARY MODEL")


thresholds = sorted(
    test["threshold"].unique().tolist()
)

print(
    "Threshold values:",
    thresholds
)


if thresholds != [0.115]:
    raise RuntimeError(
        "Primary threshold changed."
    )


expected_pred = (
    test["calibrated_probability"]
    >= 0.115
).astype(int)


prediction_mismatches = int(
    (
        expected_pred
        != test["predicted_30d"]
    ).sum()
)


print(
    "Prediction-rule mismatches:",
    prediction_mismatches
)


if prediction_mismatches != 0:
    raise RuntimeError(
        "Frozen primary prediction rule changed."
    )


print("Frozen primary model rule: PASSED")


# ============================================================
# F — VERIFY FROZEN LEARNED ROUTER
# ============================================================

section("F — VERIFY FROZEN LEARNED ROUTER")


negative_cases = e2e[
    e2e["predicted_30d"] == 0
]


selected = negative_cases[
    negative_cases["selected_for_review"] == 1
]


print(
    "Primary-model-negative cases:",
    len(negative_cases)
)

print(
    "Learned-router selected cases:",
    len(selected)
)

print(
    "Learned-router review rate:",
    len(selected) / len(negative_cases)
)


if len(negative_cases) != 7858:
    raise RuntimeError(
        "Frozen negative population changed."
    )


if len(selected) != 1178:
    raise RuntimeError(
        "Frozen learned-router review population changed."
    )


print("Frozen learned router: PASSED")


# ============================================================
# G — DEFINE SYSTEM COMPARATORS
# ============================================================

section("G — PREDECLARE FINAL SYSTEM COMPARATORS")


systems = {
    "A": {
        "name": "ML_ONLY",
        "description":
            "Frozen primary ML classifier only; "
            "no Rescue Review workflow.",

        "routing_policy":
            "NO_ADDITIONAL_REVIEW",

        "primary_model_changed":
            False,
    },

    "B": {
        "name": "ALWAYS_ON_AGENTS",
        "description":
            "All eligible primary-model-negative cases "
            "receive the additional Rescue Review workflow.",

        "routing_policy":
            "ALL_PRIMARY_MODEL_NEGATIVES",

        "primary_model_changed":
            False,
    },

    "C": {
        "name": "RULE_ROUTER",
        "description":
            "Predeclared hand-designed routing comparator "
            "using frozen pre-outcome routing information.",

        "routing_policy":
            "TO_BE_FROZEN_BEFORE_OUTCOME_COMPARISON",

        "primary_model_changed":
            False,
    },

    "D": {
        "name": "LEARNED_ROUTER",
        "description":
            "Frozen CareCompute learned Rescue Router.",

        "routing_policy":
            "FROZEN_PHASE10_LEARNED_ROUTER",

        "primary_model_changed":
            False,
    },
}


for key, value in systems.items():

    print()
    print(key, "-", value["name"])
    print(value["description"])


# ============================================================
# H — PREDECLARE METRIC SEMANTICS
# ============================================================

section("H — PREDECLARE FINAL METRIC SEMANTICS")


predictive_metrics = [
    "AUROC",
    "AUPRC",
    "Recall",
    "FNR",
]


routing_metrics = [
    "review_population",
    "review_rate",
    "false_negatives_escalated",
    "false_negative_review_coverage",
    "false_negatives_bypassed",
]


compute_metrics = [
    "observed_agent_stage_executions",
    "measured_agent_calls_if_available",
    "measured_tokens_if_available",
    "measured_latency_if_available",
    "measured_cost_if_available",
]


print("Predictive metrics:")
for metric in predictive_metrics:
    print(" -", metric)


print()
print("Routing / escalation metrics:")
for metric in routing_metrics:
    print(" -", metric)


print()
print("Compute metrics:")
for metric in compute_metrics:
    print(" -", metric)


# ============================================================
# I — CRITICAL PERFORMANCE INTERPRETATION LOCK
# ============================================================

section("I — PERFORMANCE INTERPRETATION LOCK")


interpretation_rules = [
    (
        "AUROC/AUPRC/Recall/FNR describe the frozen "
        "primary predictive model unless a comparator "
        "produces a genuine new patient-level prediction."
    ),

    (
        "Routing a case to an agent does not automatically "
        "convert a false negative into a true positive."
    ),

    (
        "Human review is not assumed to correct an "
        "escalated case."
    ),

    (
        "Systems B/C/D may therefore share primary-model "
        "predictive metrics while differing substantially "
        "in escalation coverage and compute allocation."
    ),

    (
        "No synthetic agent prediction will be invented "
        "for the purpose of improving final performance."
    ),

    (
        "Missing token, latency, API-call, or cost telemetry "
        "will be reported as unavailable rather than estimated."
    ),
]


for rule in interpretation_rules:
    print(" -", rule)


print()
print("Performance interpretation boundary: FROZEN")


# ============================================================
# J — TEST-SET ADAPTATION PROHIBITION
# ============================================================

section("J — FINAL TEST-SET ADAPTATION PROHIBITION")


prohibited = [
    "Retraining the primary model",
    "Changing the primary threshold",
    "Retraining the learned router",
    "Changing the learned-router review budget",
    "Changing perturbation definitions because of test results",
    "Choosing rule-router thresholds using test outcomes",
    "Choosing ablations because they improve test performance",
    "Silently removing unfavorable cases or subgroups",
]


for item in prohibited:
    print(" - PROHIBITED:", item)


print()
print(
    "Final test results may be analyzed and reported, "
    "but must not be used to tune the frozen systems."
)


# ============================================================
# K — PREDECLARE STATISTICAL PLAN
# ============================================================

section("K — PREDECLARE STATISTICAL PLAN")


statistics = {
    "confidence_level": 0.95,

    "bootstrap_replicates": 2000,

    "bootstrap_seed": 20260920,

    "comparison_design":
        "PAIRED_SAME_TEST_ENCOUNTERS",

    "report_absolute_differences":
        True,

    "report_relative_differences_when_meaningful":
        True,

    "report_p_values_when_formally_tested":
        True,

    "effect_sizes_required":
        True,

    "test_set_retuning":
        False,
}


for key, value in statistics.items():
    print(key + ":", value)


# ============================================================
# L — TELEMETRY AVAILABILITY LOCK
# ============================================================

section("L — TELEMETRY AVAILABILITY LOCK")


telemetry = {
    "workflow_allocation":
        "AVAILABLE",

    "observed_agent_stage_execution":
        "AVAILABLE",

    "measured_api_calls":
        "NOT_YET_VERIFIED",

    "measured_tokens":
        "NOT_CAPTURED_IN_FROZEN_PHASE10_EXECUTION",

    "measured_latency":
        "NOT_CAPTURED_IN_FROZEN_PHASE10_EXECUTION",

    "measured_cost":
        "NOT_CAPTURED_IN_FROZEN_PHASE10_EXECUTION",
}


for key, value in telemetry.items():
    print(key + ":", value)


print()
print(
    "Unavailable telemetry will not be fabricated."
)


# ============================================================
# M — SAVE FINAL COMPARISON PROTOCOL
# ============================================================

section("M — SAVE FINAL COMPARISON PROTOCOL")


protocol = {
    "phase": "12.1",

    "status":
        "FINAL_COMPARISON_PROTOCOL_FROZEN",

    "test_population": {
        "encounters":
            len(test),

        "unique_patients":
            test["patient_nbr"].nunique(),

        "actual_positives":
            int(test["actual_30d"].sum()),

        "actual_negatives":
            int(
                len(test)
                - test["actual_30d"].sum()
            ),
    },

    "frozen_primary_model": {
        "threshold":
            0.115,

        "prediction_rule":
            "calibrated_probability >= 0.115",
    },

    "frozen_learned_router": {
        "eligible_negative_cases":
            len(negative_cases),

        "selected_cases":
            len(selected),

        "review_rate":
            len(selected) / len(negative_cases),
    },

    "systems":
        systems,

    "predictive_metrics":
        predictive_metrics,

    "routing_metrics":
        routing_metrics,

    "compute_metrics":
        compute_metrics,

    "interpretation_rules":
        interpretation_rules,

    "statistics":
        statistics,

    "telemetry":
        telemetry,

    "adaptation_policy": {
        "test_set_retuning_allowed":
            False,

        "models_may_change":
            False,

        "thresholds_may_change":
            False,

        "router_budget_may_change":
            False,

        "rule_router_may_use_test_outcomes":
            False,
    },

    "source_hashes": {
        "test_predictions":
            sha256_file(TEST_PATH),

        "end_to_end_predictions":
            sha256_file(E2E_PATH),

        "router_predictions":
            sha256_file(ROUTER_PATH),

        "phase10_manifest":
            sha256_file(PHASE10_PATH),

        "phase11_manifest":
            sha256_file(PHASE11_PATH),
    },

    "next_phase":
        "12.2 — Construct and freeze A/B/C/D comparators",
}


with PROTOCOL_PATH.open("w") as f:
    json.dump(
        protocol,
        f,
        indent=2,
    )


print(
    "Protocol artifact:",
    PROTOCOL_PATH
)


# ============================================================
# N — FINAL VERIFICATION
# ============================================================

section("N — FINAL VERIFICATION")


checks = {
    "test_population_lock":
        len(test) == 15042,

    "unique_encounters":
        test["encounter_id"].nunique()
        == 15042,

    "primary_threshold_lock":
        thresholds == [0.115],

    "prediction_rule_lock":
        prediction_mismatches == 0,

    "negative_population_lock":
        len(negative_cases) == 7858,

    "learned_review_population_lock":
        len(selected) == 1178,

    "four_comparators_predeclared":
        len(systems) == 4,

    "test_retuning_prohibited":
        statistics[
            "test_set_retuning"
        ] is False,

    "agent_prediction_not_invented":
        True,

    "missing_telemetry_not_fabricated":
        True,

    "phase10_unchanged":
        True,

    "phase11_unchanged":
        True,

    "protocol_exists":
        PROTOCOL_PATH.exists(),
}


for key, value in checks.items():

    print(
        key + ":",
        "PASSED" if value else "FAILED"
    )


if not all(checks.values()):

    raise RuntimeError(
        "Phase 12.1 protocol lock failed."
    )


# ============================================================
# COMPLETE
# ============================================================

section(
    "PHASE 12.1 COMPLETE — "
    "FINAL SCIENTIFIC COMPARISON PROTOCOL FROZEN"
)


print("Final test encounters:", len(test))
print(
    "Unique patients:",
    test["patient_nbr"].nunique()
)

print("Primary threshold: 0.115")

print(
    "Learned-router review population:",
    len(selected)
)

print(
    "Systems frozen for comparison: A/B/C/D"
)

print()
print("Test-set retuning permitted: NO")
print("Agent predictions fabricated: NO")
print("Unavailable telemetry fabricated: NO")
print("Phase 10 modified: NO")
print("Phase 11 modified: NO")

print()
print(
    "NEXT: PHASE 12.2 — "
    "CONSTRUCT AND FREEZE A/B/C/D COMPARATORS"
)
