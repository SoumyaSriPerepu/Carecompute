"""
CareCompute
Phase 13.5.6 — Final End-to-End Validation Lock

Closure phase for Phase 13.5.

This script:
1. Verifies all Phase 13.5 validation artifacts.
2. Verifies their final PASS states.
3. Verifies key frozen Phase 13 artifacts.
4. Captures provenance hashes.
5. Creates the final Phase 13.5 validation lock.

No model, router, agent, threshold, priority, fairness decision,
or clinical output is modified.
"""

from pathlib import Path
import hashlib
import json


ROOT = Path.cwd().resolve()

PHASE13 = (
    ROOT
    / "results"
    / "eligible"
    / "phase13"
)

VALIDATION = (
    ROOT
    / "results"
    / "eligible"
    / "runtime_validation"
)

VALIDATION.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# REQUIRED VALIDATION ARTIFACTS
# =============================================================================

VALIDATION_ARTIFACTS = {
    "13.5.1_summary":
        VALIDATION
        / "phase13_5_1_end_to_end_execution_summary.json",

    "13.5.1_audit":
        VALIDATION
        / "phase13_5_1_end_to_end_execution_audit.json",

    "13.5.2_audit":
        VALIDATION
        / "phase13_5_2_cross_component_contract_audit.json",

    "13.5.2_mismatches":
        VALIDATION
        / "phase13_5_2_contract_mismatches.csv",

    "13.5.3_audit":
        VALIDATION
        / "phase13_5_3_safety_hitl_audit.json",

    "13.5.3_violations":
        VALIDATION
        / "phase13_5_3_safety_hitl_violations.csv",

    "13.5.4_audit":
        VALIDATION
        / "phase13_5_4_determinism_replay_audit.json",

    "13.5.4_hash_comparison":
        VALIDATION
        / "phase13_5_4_replay_hash_comparison.csv",

    "13.5.4_replay_log":
        VALIDATION
        / "phase13_5_4_replay_execution_log.json",

    "13.5.5_audit":
        VALIDATION
        / "phase13_5_5_failure_edge_case_audit.json",

    "13.5.5_results":
        VALIDATION
        / "phase13_5_5_failure_edge_case_results.csv",
}


# =============================================================================
# FROZEN SYSTEM ARTIFACTS
# =============================================================================

FROZEN_ARTIFACTS = {
    "architecture":
        PHASE13
        / "phase13_1_integrated_agent_architecture.json",

    "runtime":
        PHASE13
        / "phase13_2_agent_eligible_runtime.csv",

    "runtime_manifest":
        PHASE13
        / "phase13_2_frozen_runtime_manifest.json",

    "contexts":
        PHASE13
        / "phase13_3_patient_contexts.csv",

    "rescue_outputs":
        PHASE13
        / "phase13_3_rescue_review_outputs.csv",

    "explanation_outputs":
        PHASE13
        / "phase13_3_explanation_outputs.csv",

    "agent_packets":
        PHASE13
        / "phase13_3_agent_runtime_packets.jsonl",

    "agent_audit":
        PHASE13
        / "phase13_3_agent_runtime_audit.json",

    "orchestrated_packets":
        PHASE13
        / "phase13_4_orchestrated_human_review_packets.jsonl",

    "case_index":
        PHASE13
        / "phase13_4_orchestrator_case_index.csv",

    "fairness_monitor":
        PHASE13
        / "phase13_4_fairness_monitor_snapshot.json",

    "orchestrator_audit":
        PHASE13
        / "phase13_4_orchestrator_audit.json",

    "orchestrator_manifest":
        PHASE13
        / "phase13_4_integrated_orchestrator_manifest.json",
}


EXPECTED_POPULATION = 1178
EXPECTED_THRESHOLD = 0.115
EXPECTED_REVIEW_BUDGET = 0.15


# =============================================================================
# HELPERS
# =============================================================================

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


def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def passed(condition, name, audit):

    status = (
        "PASSED"
        if bool(condition)
        else "FAILED"
    )

    audit[name] = status

    print(
        f"{name}: {status}"
    )

    if status == "FAILED":

        raise AssertionError(
            f"{name} FAILED"
        )


def json_status_is_passed(obj):

    candidates = [
        obj.get("overall_status"),
        obj.get("final_status"),
        obj.get("status"),
    ]

    normalized = {
        str(x).strip().upper()
        for x in candidates
        if x is not None
    }

    return bool(
        normalized.intersection({
            "PASSED",
            "END_TO_END_EXECUTION_VALIDATED",
            "CROSS_COMPONENT_CONTRACTS_VALIDATED",
            "SAFETY_AND_HITL_VALIDATED",
            "DETERMINISM_AND_REPLAY_VALIDATED",
            "FAILURE_AND_EDGE_CASES_VALIDATED",
        })
    )


# =============================================================================
# START
# =============================================================================

banner(
    "PHASE 13.5.6 — "
    "FINAL END-TO-END VALIDATION LOCK"
)

audit = {}


# =============================================================================
# A — VERIFY ALL PHASE 13.5 ARTIFACTS
# =============================================================================

banner(
    "A — VERIFY PHASE 13.5 VALIDATION ARTIFACTS"
)

for name, path in VALIDATION_ARTIFACTS.items():

    print(
        f"{name}: "
        f"{'FOUND' if path.exists() else 'MISSING'}"
    )

passed(
    all(
        path.exists()
        for path in VALIDATION_ARTIFACTS.values()
    ),
    "all_validation_artifacts_present",
    audit,
)


# =============================================================================
# B — VERIFY PHASE 13.5.1
# =============================================================================

banner(
    "B — VERIFY PHASE 13.5.1 "
    "END-TO-END EXECUTION"
)

audit_1351 = load_json(
    VALIDATION_ARTIFACTS[
        "13.5.1_audit"
    ]
)

summary_1351 = load_json(
    VALIDATION_ARTIFACTS[
        "13.5.1_summary"
    ]
)

checks_1351 = audit_1351.get(
    "checks",
    audit_1351,
)

failed_1351 = [
    key
    for key, value in checks_1351.items()
    if isinstance(value, str)
    and value.upper() == "FAILED"
]

print(
    "Failed checks:",
    failed_1351,
)

passed(
    len(failed_1351) == 0,
    "phase13_5_1_execution_validated",
    audit,
)


# =============================================================================
# C — VERIFY PHASE 13.5.2
# =============================================================================

banner(
    "C — VERIFY PHASE 13.5.2 "
    "CROSS-COMPONENT CONTRACTS"
)

audit_1352 = load_json(
    VALIDATION_ARTIFACTS[
        "13.5.2_audit"
    ]
)

passed(
    json_status_is_passed(
        audit_1352
    )
    or (
        audit_1352.get(
            "total_mismatches"
        ) == 0
    ),
    "phase13_5_2_contracts_validated",
    audit,
)


# =============================================================================
# D — VERIFY PHASE 13.5.3
# =============================================================================

banner(
    "D — VERIFY PHASE 13.5.3 "
    "SAFETY + HITL"
)

audit_1353 = load_json(
    VALIDATION_ARTIFACTS[
        "13.5.3_audit"
    ]
)

print(
    "Total violations:",
    audit_1353.get(
        "total_violations"
    ),
)

passed(
    audit_1353.get(
        "total_violations"
    ) == 0
    and audit_1353.get(
        "overall_status"
    ) == "PASSED",
    "phase13_5_3_safety_hitl_validated",
    audit,
)


# =============================================================================
# E — VERIFY PHASE 13.5.4
# =============================================================================

banner(
    "E — VERIFY PHASE 13.5.4 "
    "DETERMINISM + REPLAY"
)

audit_1354 = load_json(
    VALIDATION_ARTIFACTS[
        "13.5.4_audit"
    ]
)

print(
    "Exact matches:",
    audit_1354.get(
        "exact_match_count"
    ),
    "/",
    audit_1354.get(
        "expected_match_count"
    ),
)

passed(
    audit_1354.get(
        "overall_status"
    ) == "PASSED"
    and audit_1354.get(
        "exact_match_count"
    )
    == audit_1354.get(
        "expected_match_count"
    )
    and audit_1354.get(
        "exact_match_count"
    ) == 9,
    "phase13_5_4_determinism_validated",
    audit,
)


# =============================================================================
# F — VERIFY PHASE 13.5.5
# =============================================================================

banner(
    "F — VERIFY PHASE 13.5.5 "
    "FAILURE + EDGE CASES"
)

audit_1355 = load_json(
    VALIDATION_ARTIFACTS[
        "13.5.5_audit"
    ]
)

print(
    "Tests executed:",
    audit_1355.get(
        "tests_executed"
    ),
)

print(
    "Tests passed:",
    audit_1355.get(
        "tests_passed"
    ),
)

print(
    "Tests failed:",
    audit_1355.get(
        "tests_failed"
    ),
)

passed(
    audit_1355.get(
        "overall_status"
    ) == "PASSED"
    and audit_1355.get(
        "tests_executed"
    ) == 28
    and audit_1355.get(
        "tests_passed"
    ) == 28
    and audit_1355.get(
        "tests_failed"
    ) == 0,
    "phase13_5_5_failure_testing_validated",
    audit,
)


# =============================================================================
# G — VERIFY FROZEN SYSTEM ARTIFACTS
# =============================================================================

banner(
    "G — VERIFY FROZEN PHASE 13 SYSTEM"
)

for name, path in FROZEN_ARTIFACTS.items():

    print(
        f"{name}: "
        f"{'FOUND' if path.exists() else 'MISSING'}"
    )

passed(
    all(
        path.exists()
        for path in FROZEN_ARTIFACTS.values()
    ),
    "frozen_phase13_artifacts_present",
    audit,
)


# =============================================================================
# H — CAPTURE FROZEN SYSTEM HASHES
# =============================================================================

banner(
    "H — CAPTURE FROZEN SYSTEM HASHES"
)

system_hashes = {}

for name, path in FROZEN_ARTIFACTS.items():

    digest = sha256(
        path
    )

    system_hashes[name] = {
        "path":
            str(
                path.relative_to(ROOT)
            ),

        "sha256":
            digest,
    }

    print(
        system_hashes[name]["path"],
        "->",
        digest,
    )


# =============================================================================
# I — CAPTURE VALIDATION EVIDENCE HASHES
# =============================================================================

banner(
    "I — CAPTURE VALIDATION EVIDENCE HASHES"
)

validation_hashes = {}

for name, path in (
    VALIDATION_ARTIFACTS.items()
):

    digest = sha256(
        path
    )

    validation_hashes[name] = {
        "path":
            str(
                path.relative_to(ROOT)
            ),

        "sha256":
            digest,
    }

    print(
        validation_hashes[name]["path"],
        "->",
        digest,
    )


# =============================================================================
# J — VERIFY CORE LOCKED VALUES
# =============================================================================

banner(
    "J — VERIFY CORE LOCKED VALUES"
)

orchestrator_manifest = load_json(
    FROZEN_ARTIFACTS[
        "orchestrator_manifest"
    ]
)

manifest_text = json.dumps(
    orchestrator_manifest,
    sort_keys=True,
)

passed(
    str(EXPECTED_POPULATION)
    in manifest_text,
    "population_lock_1178",
    audit,
)

passed(
    str(EXPECTED_THRESHOLD)
    in manifest_text,
    "primary_threshold_lock_0_115",
    audit,
)

passed(
    str(EXPECTED_REVIEW_BUDGET)
    in manifest_text,
    "review_budget_lock_0_15",
    audit,
)


# =============================================================================
# K — VERIFY FINAL SAFETY STATE
# =============================================================================

banner(
    "K — VERIFY FINAL SAFETY STATE"
)

passed(
    audit_1353.get(
        "total_violations"
    ) == 0,
    "zero_safety_hitl_violations",
    audit,
)

passed(
    audit_1355.get(
        "tests_failed"
    ) == 0,
    "zero_failure_test_failures",
    audit,
)

passed(
    audit_1354.get(
        "exact_match_count"
    ) == 9,
    "deterministic_replay_9_of_9",
    audit,
)


# =============================================================================
# L — CREATE PHASE 13.5 VALIDATION LOCK
# =============================================================================

banner(
    "L — CREATE PHASE 13.5 VALIDATION LOCK"
)

overall_passed = all(
    value == "PASSED"
    for value in audit.values()
)

lock = {
    "system":
        "CareCompute",

    "phase":
        "13.5.6",

    "lock_name":
        "FINAL_END_TO_END_VALIDATION_LOCK",

    "system_variant":
        "System D — Learned Router",

    "runtime_mode":
        "FROZEN_HUMAN_IN_THE_LOOP",

    "population":
        EXPECTED_POPULATION,

    "frozen_parameters": {
        "primary_threshold":
            EXPECTED_THRESHOLD,

        "review_budget":
            EXPECTED_REVIEW_BUDGET,
    },

    "validation_chain": {
        "13.5.1":
            "END_TO_END_EXECUTION_VALIDATED",

        "13.5.2":
            "CROSS_COMPONENT_CONTRACTS_VALIDATED",

        "13.5.3":
            "SAFETY_AND_HITL_VALIDATED",

        "13.5.4":
            "DETERMINISM_AND_REPLAY_VALIDATED",

        "13.5.5":
            "FAILURE_AND_EDGE_CASES_VALIDATED",
    },

    "validation_evidence": {
        "deterministic_exact_matches":
            "9/9",

        "failure_edge_tests":
            "28/28",

        "safety_hitl_violations":
            0,

        "contract_mismatches":
            0,

        "canonical_artifact_modification":
            False,
    },

    "safety_state": {
        "human_review_required":
            True,

        "autonomous_clinical_action":
            False,

        "ground_truth_exposed":
            False,

        "patient_identifier_exposed":
            False,

        "diagnosis_allowed":
            False,

        "treatment_recommendation_allowed":
            False,

        "medication_recommendation_allowed":
            False,

        "prediction_modification_allowed":
            False,

        "router_modification_allowed":
            False,

        "priority_modification_allowed":
            False,

        "threshold_modification_allowed":
            False,

        "review_budget_modification_allowed":
            False,
    },

    "fairness_state": {
        "monitor_mode":
            "READ_ONLY",

        "individual_decision_modification":
            False,

        "demographics_used_for_routing":
            False,

        "demographics_used_for_priority":
            False,

        "subgroup_specific_threshold":
            False,
    },

    "system_artifact_hashes":
        system_hashes,

    "validation_evidence_hashes":
        validation_hashes,

    "checks":
        audit,

    "phase13_5_status":
        (
            "VALIDATED_AND_LOCKED"
            if overall_passed
            else "FAILED"
        ),

    "ready_for_phase13_6":
        overall_passed,
}


LOCK_PATH = (
    VALIDATION
    / "phase13_5_6_final_end_to_end_validation_lock.json"
)

with open(
    LOCK_PATH,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        lock,
        f,
        indent=2,
        sort_keys=True,
    )

print(
    "Saved:",
    LOCK_PATH,
)


# =============================================================================
# M — HASH FINAL LOCK
# =============================================================================

banner(
    "M — HASH FINAL VALIDATION LOCK"
)

lock_hash = sha256(
    LOCK_PATH
)

print(
    LOCK_PATH.relative_to(ROOT),
    "->",
    lock_hash,
)


# =============================================================================
# N — CREATE CLOSURE AUDIT
# =============================================================================

banner(
    "N — CREATE PHASE 13.5 CLOSURE AUDIT"
)

closure = {
    "system":
        "CareCompute",

    "phase":
        "13.5.6",

    "validation_lock":
        str(
            LOCK_PATH.relative_to(ROOT)
        ),

    "validation_lock_sha256":
        lock_hash,

    "phase13_5_status":
        (
            "VALIDATED_AND_LOCKED"
            if overall_passed
            else "FAILED"
        ),

    "ready_for_phase13_6":
        overall_passed,

    "checks":
        audit,
}


CLOSURE_PATH = (
    VALIDATION
    / "phase13_5_6_closure_audit.json"
)

with open(
    CLOSURE_PATH,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        closure,
        f,
        indent=2,
        sort_keys=True,
    )

print(
    "Saved:",
    CLOSURE_PATH,
)


# =============================================================================
# FINAL
# =============================================================================

banner(
    "PHASE 13.5 COMPLETE — "
    "END-TO-END INTEGRATED SYSTEM VALIDATION"
)

print("\nSYSTEM")
print(" CareCompute")

print("\nFINAL SYSTEM")
print(" System D — Learned Router")

print("\nPOPULATION")
print(" 1178")

print("\nVALIDATION CHAIN")
print(" 13.5.1 End-to-End Execution: PASSED")
print(" 13.5.2 Cross-Component Contracts: PASSED")
print(" 13.5.3 Safety + HITL: PASSED")
print(" 13.5.4 Determinism + Replay: PASSED")
print(" 13.5.5 Failure + Edge Cases: PASSED")

print("\nEVIDENCE")
print(" Contract mismatches: 0")
print(" Safety/HITL violations: 0")
print(" Deterministic replay: 9/9 exact")
print(" Failure/edge tests: 28/28")

print("\nFROZEN PARAMETERS")
print(" Primary threshold: 0.115")
print(" Review budget: 0.15")

print("\nSAFETY")
print(" Human review required: YES")
print(" Autonomous clinical action: NO")
print(" Ground truth exposed: NO")
print(" Patient identifier exposed: NO")

print("\nFAIRNESS")
print(" Monitor: READ ONLY")
print(" Individual decisions modified: NO")
print(" Demographics used for routing: NO")
print(" Demographics used for priority: NO")

print("\nPHASE 13.5 STATUS")

if overall_passed:

    print(" VALIDATED_AND_LOCKED")

else:

    print(" FAILED")

print("\nREADY FOR PHASE 13.6")

print(
    " YES"
    if overall_passed
    else " NO"
)

print(
    "\nValidation lock:",
    LOCK_PATH,
)

print(
    "Lock SHA-256:",
    lock_hash,
)

print(
    "Closure audit:",
    CLOSURE_PATH,
)


if not overall_passed:

    raise SystemExit(
        "Phase 13.5 final validation lock failed."
    )


banner(
    "NEXT: PHASE 13.6 — "
    "FINAL CARECOMPUTE SYSTEM FREEZE"
)