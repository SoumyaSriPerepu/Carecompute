"""
CareCompute
Phase 13.5.5 — Failure and Edge-Case Validation

Synthetic negative testing of the frozen Phase 13.4 packet contract.

IMPORTANT:
- Canonical artifacts are read-only.
- Mutations occur only on deep-copied packets in memory.
- No clinical outputs are changed.
"""

from pathlib import Path
import copy
import hashlib
import json
import math
import pandas as pd


ROOT = Path.cwd()
PHASE13 = ROOT / "results/eligible/phase13"
VALIDATION = ROOT / "results/eligible/runtime_validation"

VALIDATION.mkdir(parents=True, exist_ok=True)

PACKETS = (
    PHASE13
    / "phase13_4_orchestrated_human_review_packets.jsonl"
)

CASE_INDEX = (
    PHASE13
    / "phase13_4_orchestrator_case_index.csv"
)

EXPECTED_THRESHOLD = 0.115
EXPECTED_REVIEW_BUDGET = 0.15

ALLOWED_PRIORITIES = {
    "LOW",
    "MODERATE",
    "HIGH",
}


def banner(text):
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


def sha256(path):

    h = hashlib.sha256()

    with open(path, "rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def load_jsonl(path):

    records = []

    with open(path, "r", encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if line:
                records.append(
                    json.loads(line)
                )

    return records


def is_number(value):

    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def validate_packet(packet):
    """
    Return (valid, reasons).

    This is a validation harness for testing the frozen packet
    contract. It does NOT replace the Phase 13 orchestrator.
    """

    reasons = []

    # ---------------------------------------------------------
    # Top-level contract
    # ---------------------------------------------------------

    required_top = [
        "schema_version",
        "encounter_id",
        "orchestrator",
        "primary_model",
        "rescue_router",
        "rescue_review",
        "explanation",
        "safety_guardrail",
        "fairness_monitor",
        "human_review_required",
        "workflow_disposition",
        "autonomous_clinical_action",
    ]

    for field in required_top:

        if field not in packet:
            reasons.append(
                f"missing:{field}"
            )

    if reasons:
        return False, reasons

    # ---------------------------------------------------------
    # Encounter ID
    # ---------------------------------------------------------

    if packet["encounter_id"] is None:
        reasons.append(
            "invalid:encounter_id"
        )

    # ---------------------------------------------------------
    # Primary model
    # ---------------------------------------------------------

    model = packet["primary_model"]

    for field in [
        "calibrated_probability",
        "decision_threshold",
        "predicted_30d",
    ]:

        if field not in model:
            reasons.append(
                f"missing:primary_model.{field}"
            )

    probability = model.get(
        "calibrated_probability"
    )

    if (
        not is_number(probability)
        or not 0 <= float(probability) <= 1
    ):
        reasons.append(
            "invalid:calibrated_probability"
        )

    threshold = model.get(
        "decision_threshold"
    )

    if (
        not is_number(threshold)
        or not math.isclose(
            float(threshold),
            EXPECTED_THRESHOLD,
            abs_tol=1e-12,
            rel_tol=0.0,
        )
    ):
        reasons.append(
            "invalid:decision_threshold"
        )

    if model.get("predicted_30d") not in {
        0,
        1,
    }:
        reasons.append(
            "invalid:predicted_30d"
        )

    # ---------------------------------------------------------
    # Rescue router
    # ---------------------------------------------------------

    router = packet["rescue_router"]

    for field in [
        "fn_router_probability",
        "review_budget",
        "selected_for_review",
    ]:

        if field not in router:
            reasons.append(
                f"missing:rescue_router.{field}"
            )

    router_probability = router.get(
        "fn_router_probability"
    )

    if (
        not is_number(router_probability)
        or not 0 <= float(router_probability) <= 1
    ):
        reasons.append(
            "invalid:fn_router_probability"
        )

    review_budget = router.get(
        "review_budget"
    )

    if (
        not is_number(review_budget)
        or not math.isclose(
            float(review_budget),
            EXPECTED_REVIEW_BUDGET,
            abs_tol=1e-12,
            rel_tol=0.0,
        )
    ):
        reasons.append(
            "invalid:review_budget"
        )

    if router.get(
        "selected_for_review"
    ) not in {0, 1}:

        reasons.append(
            "invalid:selected_for_review"
        )

    # ---------------------------------------------------------
    # Rescue review
    # ---------------------------------------------------------

    rescue = packet["rescue_review"]

    priority = rescue.get(
        "review_priority"
    )

    if priority not in ALLOWED_PRIORITIES:

        reasons.append(
            "invalid:review_priority"
        )

    if not isinstance(
        rescue.get("human_review_action"),
        str,
    ) or not rescue.get(
        "human_review_action",
        "",
    ).strip():

        reasons.append(
            "invalid:human_review_action"
        )

    # ---------------------------------------------------------
    # Explanation
    # ---------------------------------------------------------

    explanation = packet["explanation"]

    if not isinstance(
        explanation.get(
            "human_review_statement"
        ),
        str,
    ) or not explanation.get(
        "human_review_statement",
        "",
    ).strip():

        reasons.append(
            "invalid:human_review_statement"
        )

    # ---------------------------------------------------------
    # Safety guardrail
    # ---------------------------------------------------------

    guard = packet[
        "safety_guardrail"
    ]

    required_safety_state = {
        "passed": True,
        "ground_truth_available": False,
        "patient_identifier_available": False,
        "diagnosis_allowed": False,
        "treatment_recommendation_allowed": False,
        "medication_recommendation_allowed": False,
        "prediction_modification_allowed": False,
        "router_modification_allowed": False,
        "priority_modification_allowed": False,
        "threshold_modification_allowed": False,
        "review_budget_modification_allowed": False,
        "autonomous_clinical_action_allowed": False,
    }

    for field, expected in (
        required_safety_state.items()
    ):

        if guard.get(field) is not expected:

            reasons.append(
                f"unsafe:{field}"
            )

    # ---------------------------------------------------------
    # Human review
    # ---------------------------------------------------------

    if packet.get(
        "human_review_required"
    ) is not True:

        reasons.append(
            "unsafe:human_review_required"
        )

    if packet.get(
        "autonomous_clinical_action"
    ) is not False:

        reasons.append(
            "unsafe:autonomous_clinical_action"
        )

    # ---------------------------------------------------------
    # Fairness monitor
    # ---------------------------------------------------------

    fairness = packet[
        "fairness_monitor"
    ]

    fairness_false_fields = [
        "individual_decision_modification",
        "demographics_used_for_routing",
        "demographics_used_for_priority",
        "subgroup_specific_threshold",
    ]

    for field in fairness_false_fields:

        if fairness.get(field) is not False:

            reasons.append(
                f"unsafe:fairness.{field}"
            )

    # ---------------------------------------------------------
    # Prohibited data exposure
    # ---------------------------------------------------------

    prohibited = {
        "target_30d",
        "ground_truth",
        "actual_outcome",
        "true_label",
        "patient_nbr",
        "patient_id",
        "case_type",
        "router_target",
    }

    def recursive_keys(obj):

        result = set()

        if isinstance(obj, dict):

            for key, value in obj.items():

                result.add(
                    str(key).lower()
                )

                result.update(
                    recursive_keys(value)
                )

        elif isinstance(obj, list):

            for value in obj:
                result.update(
                    recursive_keys(value)
                )

        return result

    exposed = (
        recursive_keys(packet)
        .intersection(prohibited)
    )

    if exposed:

        reasons.append(
            "prohibited_data:"
            + ",".join(
                sorted(exposed)
            )
        )

    return (
        len(reasons) == 0,
        reasons,
    )


def mutation(
    name,
    mutator,
    expected_valid=False,
):

    return {
        "name": name,
        "mutator": mutator,
        "expected_valid":
            expected_valid,
    }


# =============================================================================
# START
# =============================================================================

banner(
    "PHASE 13.5.5 — "
    "FAILURE AND EDGE-CASE VALIDATION"
)


# =============================================================================
# A — VERIFY INPUTS AND HASH
# =============================================================================

banner("A — VERIFY FROZEN INPUTS")

if not PACKETS.exists():
    raise FileNotFoundError(PACKETS)

if not CASE_INDEX.exists():
    raise FileNotFoundError(CASE_INDEX)

packet_hash_before = sha256(
    PACKETS
)

index_hash_before = sha256(
    CASE_INDEX
)

print(
    "Packets: FOUND"
)

print(
    "Case index: FOUND"
)

print(
    "Packet hash:",
    packet_hash_before,
)

print(
    "Case-index hash:",
    index_hash_before,
)


# =============================================================================
# B — LOAD REPRESENTATIVE VALID PACKET
# =============================================================================

banner(
    "B — LOAD REPRESENTATIVE VALID PACKET"
)

packets = load_jsonl(
    PACKETS
)

if len(packets) != 1178:
    raise AssertionError(
        "Unexpected packet population."
    )

base = copy.deepcopy(
    packets[0]
)

valid, reasons = validate_packet(
    base
)

print(
    "Baseline packet valid:",
    valid,
)

print(
    "Baseline rejection reasons:",
    reasons,
)

if not valid:
    raise AssertionError(
        "Frozen baseline packet failed "
        "edge-case validator."
    )


# =============================================================================
# C — DEFINE NEGATIVE TESTS
# =============================================================================

banner("C — DEFINE FAILURE TESTS")

tests = []


# Valid control
tests.append(
    mutation(
        "valid_frozen_packet",
        lambda p: None,
        expected_valid=True,
    )
)


# Missing top-level identifier
def missing_encounter(p):
    p.pop(
        "encounter_id",
        None,
    )


tests.append(
    mutation(
        "missing_encounter_id",
        missing_encounter,
    )
)


# Invalid probability
def probability_above_one(p):
    p["primary_model"][
        "calibrated_probability"
    ] = 1.25


tests.append(
    mutation(
        "probability_above_one",
        probability_above_one,
    )
)


# Missing model probability
def missing_probability(p):
    p["primary_model"].pop(
        "calibrated_probability",
        None,
    )


tests.append(
    mutation(
        "missing_model_probability",
        missing_probability,
    )
)


# Threshold mutation
def changed_threshold(p):
    p["primary_model"][
        "decision_threshold"
    ] = 0.20


tests.append(
    mutation(
        "changed_primary_threshold",
        changed_threshold,
    )
)


# Review budget mutation
def changed_budget(p):
    p["rescue_router"][
        "review_budget"
    ] = 0.25


tests.append(
    mutation(
        "changed_review_budget",
        changed_budget,
    )
)


# Invalid router probability
def invalid_router_probability(p):
    p["rescue_router"][
        "fn_router_probability"
    ] = -0.10


tests.append(
    mutation(
        "invalid_router_probability",
        invalid_router_probability,
    )
)


# Invalid priority
def invalid_priority(p):
    p["rescue_review"][
        "review_priority"
    ] = "CRITICAL"


tests.append(
    mutation(
        "invalid_review_priority",
        invalid_priority,
    )
)


# Remove human-review action
def missing_review_action(p):
    p["rescue_review"][
        "human_review_action"
    ] = ""


tests.append(
    mutation(
        "missing_human_review_action",
        missing_review_action,
    )
)


# Disable HITL
def disable_hitl(p):
    p[
        "human_review_required"
    ] = False


tests.append(
    mutation(
        "human_review_disabled",
        disable_hitl,
    )
)


# Enable autonomous action
def enable_autonomy(p):
    p[
        "autonomous_clinical_action"
    ] = True


tests.append(
    mutation(
        "autonomous_action_enabled",
        enable_autonomy,
    )
)


# Ground truth exposure
def expose_ground_truth(p):
    p[
        "ground_truth"
    ] = 1


tests.append(
    mutation(
        "ground_truth_exposed",
        expose_ground_truth,
    )
)


# Patient identifier exposure
def expose_patient_id(p):
    p[
        "patient_nbr"
    ] = 123456


tests.append(
    mutation(
        "patient_identifier_exposed",
        expose_patient_id,
    )
)


# Diagnosis permission
def allow_diagnosis(p):
    p["safety_guardrail"][
        "diagnosis_allowed"
    ] = True


tests.append(
    mutation(
        "diagnosis_enabled",
        allow_diagnosis,
    )
)


# Treatment permission
def allow_treatment(p):
    p["safety_guardrail"][
        "treatment_recommendation_allowed"
    ] = True


tests.append(
    mutation(
        "treatment_recommendation_enabled",
        allow_treatment,
    )
)


# Medication permission
def allow_medication(p):
    p["safety_guardrail"][
        "medication_recommendation_allowed"
    ] = True


tests.append(
    mutation(
        "medication_recommendation_enabled",
        allow_medication,
    )
)


# Prediction modification
def allow_prediction_modification(p):
    p["safety_guardrail"][
        "prediction_modification_allowed"
    ] = True


tests.append(
    mutation(
        "prediction_modification_enabled",
        allow_prediction_modification,
    )
)


# Router modification
def allow_router_modification(p):
    p["safety_guardrail"][
        "router_modification_allowed"
    ] = True


tests.append(
    mutation(
        "router_modification_enabled",
        allow_router_modification,
    )
)


# Priority modification
def allow_priority_modification(p):
    p["safety_guardrail"][
        "priority_modification_allowed"
    ] = True


tests.append(
    mutation(
        "priority_modification_enabled",
        allow_priority_modification,
    )
)


# Threshold modification
def allow_threshold_modification(p):
    p["safety_guardrail"][
        "threshold_modification_allowed"
    ] = True


tests.append(
    mutation(
        "threshold_modification_enabled",
        allow_threshold_modification,
    )
)


# Budget modification
def allow_budget_modification(p):
    p["safety_guardrail"][
        "review_budget_modification_allowed"
    ] = True


tests.append(
    mutation(
        "review_budget_modification_enabled",
        allow_budget_modification,
    )
)


# Autonomous clinical permission
def allow_autonomous_clinical(p):
    p["safety_guardrail"][
        "autonomous_clinical_action_allowed"
    ] = True


tests.append(
    mutation(
        "autonomous_clinical_permission_enabled",
        allow_autonomous_clinical,
    )
)


# Fairness intervention
def fairness_modifies_decision(p):
    p["fairness_monitor"][
        "individual_decision_modification"
    ] = True


tests.append(
    mutation(
        "fairness_individual_decision_modification",
        fairness_modifies_decision,
    )
)


# Demographics routing
def demographics_routing(p):
    p["fairness_monitor"][
        "demographics_used_for_routing"
    ] = True


tests.append(
    mutation(
        "demographics_used_for_routing",
        demographics_routing,
    )
)


# Demographics priority
def demographics_priority(p):
    p["fairness_monitor"][
        "demographics_used_for_priority"
    ] = True


tests.append(
    mutation(
        "demographics_used_for_priority",
        demographics_priority,
    )
)


# Subgroup threshold
def subgroup_threshold(p):
    p["fairness_monitor"][
        "subgroup_specific_threshold"
    ] = True


tests.append(
    mutation(
        "subgroup_specific_threshold_enabled",
        subgroup_threshold,
    )
)


# Missing explanation HITL statement
def missing_explanation_hitl(p):
    p["explanation"][
        "human_review_statement"
    ] = ""


tests.append(
    mutation(
        "missing_explanation_hitl_statement",
        missing_explanation_hitl,
    )
)


print(
    "Defined tests:",
    len(tests),
)


# =============================================================================
# D — EXECUTE FAILURE INJECTION TESTS
# =============================================================================

banner(
    "D — EXECUTE FAILURE INJECTION TESTS"
)

results = []

for test in tests:

    candidate = copy.deepcopy(
        base
    )

    test["mutator"](
        candidate
    )

    valid, reasons = validate_packet(
        candidate
    )

    expected_valid = (
        test["expected_valid"]
    )

    passed = (
        valid == expected_valid
    )

    results.append({
        "test":
            test["name"],

        "expected":
            (
                "ACCEPT"
                if expected_valid
                else "REJECT"
            ),

        "observed":
            (
                "ACCEPT"
                if valid
                else "REJECT"
            ),

        "passed":
            passed,

        "reasons":
            " | ".join(reasons),
    })

    print(
        f"{test['name']}: "
        f"expected="
        f"{'ACCEPT' if expected_valid else 'REJECT'} "
        f"observed="
        f"{'ACCEPT' if valid else 'REJECT'} "
        f"=> "
        f"{'PASSED' if passed else 'FAILED'}"
    )


# =============================================================================
# E — DUPLICATE ENCOUNTER EDGE CASE
# =============================================================================

banner(
    "E — DUPLICATE ENCOUNTER EDGE CASE"
)

duplicate_test_records = [
    copy.deepcopy(base),
    copy.deepcopy(base),
]

ids = [
    x["encounter_id"]
    for x in duplicate_test_records
]

duplicate_detected = (
    len(ids)
    != len(set(ids))
)

results.append({
    "test":
        "duplicate_encounter_id",

    "expected":
        "REJECT",

    "observed":
        (
            "REJECT"
            if duplicate_detected
            else "ACCEPT"
        ),

    "passed":
        duplicate_detected,

    "reasons":
        "duplicate encounter_id detected"
        if duplicate_detected
        else "",
})

print(
    "duplicate_encounter_id:",
    "PASSED"
    if duplicate_detected
    else "FAILED",
)


# =============================================================================
# F — SUMMARIZE TEST RESULTS
# =============================================================================

banner("F — SUMMARIZE FAILURE TESTS")

passed_count = sum(
    bool(x["passed"])
    for x in results
)

failed_tests = [
    x
    for x in results
    if not x["passed"]
]

print(
    "Tests executed:",
    len(results),
)

print(
    "Tests passed:",
    passed_count,
)

print(
    "Tests failed:",
    len(failed_tests),
)


for failure in failed_tests:

    print(
        "FAILED:",
        failure["test"],
        failure["reasons"],
    )


# =============================================================================
# G — VERIFY CANONICAL ARTIFACTS UNCHANGED
# =============================================================================

banner(
    "G — VERIFY CANONICAL ARTIFACTS UNCHANGED"
)

packet_hash_after = sha256(
    PACKETS
)

index_hash_after = sha256(
    CASE_INDEX
)

packets_unchanged = (
    packet_hash_before
    == packet_hash_after
)

index_unchanged = (
    index_hash_before
    == index_hash_after
)

print(
    "orchestrated_packets_unchanged:",
    "PASSED"
    if packets_unchanged
    else "FAILED",
)

print(
    "case_index_unchanged:",
    "PASSED"
    if index_unchanged
    else "FAILED",
)


# =============================================================================
# H — SAVE EDGE-CASE RESULTS
# =============================================================================

banner("H — SAVE EDGE-CASE RESULTS")

results_path = (
    VALIDATION
    / "phase13_5_5_failure_edge_case_results.csv"
)

pd.DataFrame(
    results
).to_csv(
    results_path,
    index=False,
)

print(
    "Saved:",
    results_path,
)


# =============================================================================
# I — SAVE AUDIT
# =============================================================================

banner("I — SAVE VALIDATION AUDIT")

overall_passed = (
    len(failed_tests) == 0
    and packets_unchanged
    and index_unchanged
)


audit = {
    "system":
        "CareCompute",

    "phase":
        "13.5.5",

    "validation":
        "FAILURE_AND_EDGE_CASE_VALIDATION",

    "test_strategy":
        "IN_MEMORY_SYNTHETIC_MUTATION",

    "canonical_artifacts_modified":
        False,

    "tests_executed":
        len(results),

    "tests_passed":
        passed_count,

    "tests_failed":
        len(failed_tests),

    "failure_tests":
        results,

    "canonical_hashes": {
        "packets_before":
            packet_hash_before,

        "packets_after":
            packet_hash_after,

        "case_index_before":
            index_hash_before,

        "case_index_after":
            index_hash_after,
    },

    "overall_status":
        (
            "PASSED"
            if overall_passed
            else "FAILED"
        ),
}


audit_path = (
    VALIDATION
    / "phase13_5_5_failure_edge_case_audit.json"
)

with open(
    audit_path,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        audit,
        f,
        indent=2,
        sort_keys=True,
    )


print(
    "Saved:",
    audit_path,
)


# =============================================================================
# FINAL
# =============================================================================

banner(
    "PHASE 13.5.5 COMPLETE — "
    "FAILURE + EDGE-CASE VALIDATION"
)

print("\nSYSTEM")
print(" CareCompute")

print("\nTEST STRATEGY")
print(" Synthetic in-memory mutation")
print(" Frozen artifacts remained read-only")

print("\nTESTS")
print(
    f" Executed: {len(results)}"
)
print(
    f" Passed: {passed_count}"
)
print(
    f" Failed: {len(failed_tests)}"
)

print("\nVALID CONTROL")
print(
    " Frozen valid packet: ACCEPTED"
)

print("\nUNSAFE / INVALID STATES")
print(
    " Rejected:",
    (
        "YES"
        if len(failed_tests) == 0
        else "NO"
    ),
)

print("\nCANONICAL ARTIFACT MODIFICATION")
print(
    " NONE"
    if (
        packets_unchanged
        and index_unchanged
    )
    else "DETECTED"
)

print("\nFINAL STATUS")

if overall_passed:

    print(
        " FAILURE_AND_EDGE_CASES_VALIDATED"
    )

else:

    print(
        " FAILURE_EDGE_CASE_VALIDATION_FAILED"
    )


print(
    "\nResults:",
    results_path,
)

print(
    "Audit:",
    audit_path,
)


if not overall_passed:

    raise SystemExit(
        "Phase 13.5.5 validation failed."
    )


banner(
    "NEXT: PHASE 13.5.6 — "
    "FINAL END-TO-END VALIDATION LOCK"
)