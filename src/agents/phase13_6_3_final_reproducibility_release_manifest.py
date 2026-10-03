"""
CareCompute
Phase 13.6.3 — Final Reproducibility and Release Manifest

Creates the final release manifest from the already-frozen scientific,
runtime, validation, inventory, and provenance evidence.

This phase does NOT rerun or modify the CareCompute scientific system.
"""

from pathlib import Path
import hashlib
import json
import platform
import sys


ROOT = Path.cwd().resolve()

FINAL_FREEZE = ROOT / "results/eligible/final_freeze"
VALIDATION = ROOT / "results/eligible/runtime_validation"
PHASE13 = ROOT / "results/eligible/phase13"

FINAL_FREEZE.mkdir(parents=True, exist_ok=True)


# =============================================================================
# AUTHORITATIVE INPUTS
# =============================================================================

INVENTORY = (
    FINAL_FREEZE
    / "phase13_6_1_final_artifact_inventory.json"
)

INVENTORY_AUDIT = (
    FINAL_FREEZE
    / "phase13_6_1_final_artifact_inventory_audit.json"
)

PROVENANCE = (
    FINAL_FREEZE
    / "phase13_6_2_cross_phase_provenance_verification.json"
)

PROVENANCE_AUDIT = (
    FINAL_FREEZE
    / "phase13_6_2_cross_phase_provenance_audit.json"
)

VALIDATION_LOCK = (
    VALIDATION
    / "phase13_5_6_final_end_to_end_validation_lock.json"
)

ORCHESTRATOR_MANIFEST = (
    PHASE13
    / "phase13_4_integrated_orchestrator_manifest.json"
)


EXPECTED_ARTIFACT_COUNT = 104
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


def rel(path):
    return str(path.relative_to(ROOT))


def check(condition, name, audit):
    status = "PASSED" if bool(condition) else "FAILED"
    audit[name] = status

    print(f"{name}: {status}")

    if not condition:
        raise AssertionError(
            f"{name} FAILED"
        )


# =============================================================================
# START
# =============================================================================

banner(
    "PHASE 13.6.3 — "
    "FINAL REPRODUCIBILITY AND RELEASE MANIFEST"
)

audit = {}


# =============================================================================
# A — VERIFY AUTHORITATIVE INPUTS
# =============================================================================

banner("A — VERIFY AUTHORITATIVE INPUTS")

required = {
    "inventory": INVENTORY,
    "inventory_audit": INVENTORY_AUDIT,
    "provenance": PROVENANCE,
    "provenance_audit": PROVENANCE_AUDIT,
    "validation_lock": VALIDATION_LOCK,
    "orchestrator_manifest": ORCHESTRATOR_MANIFEST,
}

for name, path in required.items():
    print(
        f"{name}: "
        f"{'FOUND' if path.exists() else 'MISSING'}"
    )

check(
    all(path.exists() for path in required.values()),
    "release_inputs_present",
    audit,
)


# =============================================================================
# B — LOAD RELEASE STATE
# =============================================================================

banner("B — LOAD RELEASE STATE")

inventory = load_json(INVENTORY)
inventory_audit = load_json(INVENTORY_AUDIT)
provenance = load_json(PROVENANCE)
provenance_audit = load_json(PROVENANCE_AUDIT)
validation_lock = load_json(VALIDATION_LOCK)
orchestrator = load_json(ORCHESTRATOR_MANIFEST)

print("Release state loaded: PASSED")


# =============================================================================
# C — VERIFY INVENTORY LOCK
# =============================================================================

banner("C — VERIFY INVENTORY LOCK")

check(
    inventory.get("status") == "PASSED",
    "inventory_status_passed",
    audit,
)

check(
    inventory.get("total_artifact_count")
    == EXPECTED_ARTIFACT_COUNT,
    "inventory_count_104",
    audit,
)

inventory_records = inventory.get(
    "artifacts",
    []
)

check(
    len(inventory_records)
    == EXPECTED_ARTIFACT_COUNT,
    "inventory_records_104",
    audit,
)


# =============================================================================
# D — VERIFY ALL 104 INVENTORY HASHES AGAIN
# =============================================================================

banner("D — VERIFY RELEASE ARTIFACT HASHES")

hash_mismatches = []

for record in inventory_records:

    path = ROOT / record["path"]

    if not path.exists():
        hash_mismatches.append({
            "path": record["path"],
            "reason": "MISSING",
        })
        continue

    observed = sha256(path)
    expected = record["sha256"]

    if observed != expected:
        hash_mismatches.append({
            "path": record["path"],
            "reason": "HASH_MISMATCH",
            "expected": expected,
            "observed": observed,
        })


print(
    "Artifacts verified:",
    len(inventory_records),
)

print(
    "Hash mismatches:",
    len(hash_mismatches),
)

check(
    len(hash_mismatches) == 0,
    "release_artifact_hashes_preserved",
    audit,
)


# =============================================================================
# E — VERIFY PROVENANCE LOCK
# =============================================================================

banner("E — VERIFY CROSS-PHASE PROVENANCE")

check(
    provenance.get("status") == "PASSED",
    "cross_phase_provenance_passed",
    audit,
)

check(
    provenance.get(
        "inventory_baseline",
        {},
    ).get(
        "hash_mismatches_after"
    ) == 0,
    "provenance_hash_mismatches_zero",
    audit,
)

check(
    len(
        provenance.get(
            "provenance_chain",
            [],
        )
    ) == 7,
    "seven_stage_provenance_chain",
    audit,
)


# =============================================================================
# F — VERIFY FINAL VALIDATION LOCK
# =============================================================================

banner("F — VERIFY PHASE 13.5 VALIDATION LOCK")

check(
    validation_lock.get(
        "phase13_5_status"
    ) == "VALIDATED_AND_LOCKED",
    "phase13_5_validated_and_locked",
    audit,
)

check(
    validation_lock.get(
        "ready_for_phase13_6"
    ) is True,
    "phase13_5_release_ready",
    audit,
)

check(
    validation_lock.get(
        "population"
    ) == EXPECTED_POPULATION,
    "population_1178",
    audit,
)

parameters = validation_lock.get(
    "frozen_parameters",
    {},
)

check(
    parameters.get(
        "primary_threshold"
    ) == EXPECTED_THRESHOLD,
    "primary_threshold_0_115",
    audit,
)

check(
    parameters.get(
        "review_budget"
    ) == EXPECTED_REVIEW_BUDGET,
    "review_budget_0_15",
    audit,
)


# =============================================================================
# G — VERIFY VALIDATION EVIDENCE
# =============================================================================

banner("G — VERIFY FINAL VALIDATION EVIDENCE")

evidence = validation_lock.get(
    "validation_evidence",
    {},
)

check(
    evidence.get(
        "contract_mismatches"
    ) == 0,
    "contract_mismatches_zero",
    audit,
)

check(
    evidence.get(
        "safety_hitl_violations"
    ) == 0,
    "safety_hitl_violations_zero",
    audit,
)

check(
    evidence.get(
        "deterministic_exact_matches"
    ) == "9/9",
    "deterministic_replay_9_of_9",
    audit,
)

check(
    evidence.get(
        "failure_edge_tests"
    ) == "28/28",
    "failure_edge_tests_28_of_28",
    audit,
)

check(
    evidence.get(
        "canonical_artifact_modification"
    ) is False,
    "canonical_artifacts_unmodified",
    audit,
)


# =============================================================================
# H — VERIFY FINAL SAFETY STATE
# =============================================================================

banner("H — VERIFY FINAL SAFETY STATE")

safety = validation_lock.get(
    "safety_state",
    {},
)

required_false = [
    "autonomous_clinical_action",
    "ground_truth_exposed",
    "patient_identifier_exposed",
    "diagnosis_allowed",
    "treatment_recommendation_allowed",
    "medication_recommendation_allowed",
    "prediction_modification_allowed",
    "router_modification_allowed",
    "priority_modification_allowed",
    "threshold_modification_allowed",
    "review_budget_modification_allowed",
]

check(
    safety.get(
        "human_review_required"
    ) is True,
    "human_review_required",
    audit,
)

for field in required_false:

    check(
        safety.get(field) is False,
        f"safety_{field}_false",
        audit,
    )


# =============================================================================
# I — VERIFY FAIRNESS STATE
# =============================================================================

banner("I — VERIFY FINAL FAIRNESS STATE")

fairness = validation_lock.get(
    "fairness_state",
    {},
)

check(
    fairness.get(
        "monitor_mode"
    ) == "READ_ONLY",
    "fairness_monitor_read_only",
    audit,
)

for field in [
    "individual_decision_modification",
    "demographics_used_for_routing",
    "demographics_used_for_priority",
    "subgroup_specific_threshold",
]:

    check(
        fairness.get(field) is False,
        f"fairness_{field}_false",
        audit,
    )


# =============================================================================
# J — CAPTURE RELEASE EVIDENCE HASHES
# =============================================================================

banner("J — CAPTURE RELEASE EVIDENCE HASHES")

release_evidence_hashes = {}

for name, path in required.items():

    digest = sha256(path)

    release_evidence_hashes[name] = {
        "path": rel(path),
        "sha256": digest,
    }

    print(
        rel(path),
        "->",
        digest,
    )


# =============================================================================
# K — CAPTURE REPRODUCIBILITY ENVIRONMENT
# =============================================================================

banner("K — CAPTURE REPRODUCIBILITY ENVIRONMENT")

environment = {
    "python_version":
        sys.version.split()[0],

    "python_implementation":
        platform.python_implementation(),

    "platform_system":
        platform.system(),

    "platform_release":
        platform.release(),

    "machine":
        platform.machine(),
}

for key, value in environment.items():
    print(
        f"{key}: {value}"
    )


# =============================================================================
# L — DEFINE REPRODUCIBILITY PROCEDURE
# =============================================================================

banner("L — DEFINE REPRODUCIBILITY PROCEDURE")

reproduction_sequence = [
    "python src/evaluation/"
    "phase13_1_freeze_integrated_agent_architecture.py",

    "python src/evaluation/"
    "phase13_2_frozen_model_routing_runtime.py",

    "python src/evaluation/"
    "phase13_3_executable_agent_runtime.py",

    "python src/evaluation/"
    "phase13_4_integrated_agent_orchestrator.py",

    "python src/agents/"
    "phase13_5_1_end_to_end_execution_test.py",

    "python src/agents/"
    "phase13_5_2_cross_component_contract_validation.py",

    "python src/agents/"
    "phase13_5_3_safety_hitl_validation.py",

    "python src/agents/"
    "phase13_5_4_determinism_replay_validation.py",

    "python src/agents/"
    "phase13_5_5_failure_edge_case_validation.py",

    "python src/agents/"
    "phase13_5_6_final_end_to_end_validation_lock.py",
]

for index, command in enumerate(
    reproduction_sequence,
    start=1,
):
    print(
        f"{index}. {command}"
    )


# =============================================================================
# M — CREATE FINAL RELEASE MANIFEST
# =============================================================================

banner("M — CREATE FINAL RELEASE MANIFEST")

overall_passed = all(
    value == "PASSED"
    for value in audit.values()
)

MANIFEST_PATH = (
    FINAL_FREEZE
    / "phase13_6_3_final_reproducibility_release_manifest.json"
)

manifest = {
    "system":
        "CareCompute",

    "phase":
        "13.6.3",

    "manifest":
        "FINAL_REPRODUCIBILITY_RELEASE_MANIFEST",

    "system_variant":
        "System D — Learned Router",

    "runtime_mode":
        "FROZEN_HUMAN_IN_THE_LOOP",

    "release_scope": {
        "pre_phase13_6_artifact_count":
            EXPECTED_ARTIFACT_COUNT,

        "inventory_scope":
            "104 artifacts frozen by Phase 13.6.1",

        "phase13_6_outputs":
            "Release/freeze evidence layered on top "
            "of the 104-artifact baseline",
    },

    "locked_system_state": {
        "population":
            EXPECTED_POPULATION,

        "primary_threshold":
            EXPECTED_THRESHOLD,

        "review_budget":
            EXPECTED_REVIEW_BUDGET,

        "human_review_required":
            True,

        "autonomous_clinical_action":
            False,
    },

    "validation_evidence": {
        "contract_mismatches":
            0,

        "safety_hitl_violations":
            0,

        "deterministic_replay":
            "9/9 exact",

        "failure_edge_case_tests":
            "28/28 passed",
    },

    "provenance": {
        "stages_verified":
            7,

        "chain":
            [
                node.get("stage")
                for node in provenance.get(
                    "provenance_chain",
                    []
                )
            ],

        "status":
            "VERIFIED",
    },

    "artifact_integrity": {
        "artifacts_verified":
            len(inventory_records),

        "sha256_mismatches":
            len(hash_mismatches),

        "status":
            "VERIFIED",
    },

    "reproducibility_environment":
        environment,

    "reproduction_sequence":
        reproduction_sequence,

    "release_evidence_hashes":
        release_evidence_hashes,

    "checks":
        audit,

    "release_status":
        (
            "RELEASE_READY"
            if overall_passed
            else "FAILED"
        ),

    "ready_for_final_system_freeze":
        overall_passed,
}


with open(
    MANIFEST_PATH,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        manifest,
        f,
        indent=2,
        sort_keys=True,
    )


print(
    "Saved:",
    rel(MANIFEST_PATH),
)


# =============================================================================
# N — HASH RELEASE MANIFEST
# =============================================================================

banner("N — HASH RELEASE MANIFEST")

manifest_hash = sha256(
    MANIFEST_PATH
)

print(
    rel(MANIFEST_PATH),
    "->",
    manifest_hash,
)


# =============================================================================
# O — SAVE RELEASE AUDIT
# =============================================================================

banner("O — SAVE RELEASE AUDIT")

AUDIT_PATH = (
    FINAL_FREEZE
    / "phase13_6_3_reproducibility_release_audit.json"
)

release_audit = {
    "system":
        "CareCompute",

    "phase":
        "13.6.3",

    "checks":
        audit,

    "release_manifest":
        rel(MANIFEST_PATH),

    "release_manifest_sha256":
        manifest_hash,

    "release_status":
        (
            "RELEASE_READY"
            if overall_passed
            else "FAILED"
        ),

    "ready_for_phase13_6_4":
        overall_passed,
}


with open(
    AUDIT_PATH,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        release_audit,
        f,
        indent=2,
        sort_keys=True,
    )


print(
    "Saved:",
    rel(AUDIT_PATH),
)


# =============================================================================
# FINAL
# =============================================================================

banner(
    "PHASE 13.6.3 COMPLETE — "
    "FINAL REPRODUCIBILITY RELEASE VERIFIED"
)

print("\nSYSTEM")
print(" CareCompute")

print("\nFINAL SYSTEM")
print(" System D — Learned Router")

print("\nRELEASE BASELINE")
print(" Pre-13.6 artifacts: 104")
print(" SHA-256 mismatches: 0")

print("\nPROVENANCE")
print(" Verified stages: 7")
print(" Phase 10 -> Phase 12 -> Phase 13 -> Phase 13.5")

print("\nVALIDATION")
print(" Contract mismatches: 0")
print(" Safety/HITL violations: 0")
print(" Deterministic replay: 9/9 exact")
print(" Failure/edge tests: 28/28 passed")

print("\nLOCKED SYSTEM")
print(" Population: 1178")
print(" Primary threshold: 0.115")
print(" Review budget: 0.15")
print(" Human review required: YES")
print(" Autonomous clinical action: NO")

print("\nRELEASE STATUS")

if overall_passed:
    print(" RELEASE_READY")
else:
    print(" FAILED")

print("\nREADY FOR FINAL SYSTEM FREEZE")

print(
    " YES"
    if overall_passed
    else " NO"
)

print(
    "\nManifest:",
    rel(MANIFEST_PATH),
)

print(
    "Manifest SHA-256:",
    manifest_hash,
)

print(
    "Audit:",
    rel(AUDIT_PATH),
)


if not overall_passed:
    raise SystemExit(
        "Phase 13.6.3 release verification failed."
    )


banner(
    "NEXT: PHASE 13.6.4 — "
    "FINAL CARECOMPUTE SYSTEM FREEZE"
)