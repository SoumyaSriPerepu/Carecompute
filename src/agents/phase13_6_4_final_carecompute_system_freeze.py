"""
CareCompute
Phase 13.6.4 — Final CareCompute System Freeze

Final immutable release lock for the integrated CareCompute system.

This phase:
- does NOT retrain models
- does NOT recalibrate probabilities
- does NOT change thresholds
- does NOT change review budget
- does NOT rerun routing decisions
- does NOT change agent outputs
- does NOT change priorities
- does NOT modify clinical decisions

It verifies the frozen release evidence and creates the final
CareCompute system freeze manifest.
"""

from pathlib import Path
import hashlib
import json


ROOT = Path.cwd().resolve()

FINAL_FREEZE = (
    ROOT
    / "results/eligible/final_freeze"
)

RUNTIME_VALIDATION = (
    ROOT
    / "results/eligible/runtime_validation"
)


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

RELEASE_MANIFEST = (
    FINAL_FREEZE
    / "phase13_6_3_final_reproducibility_release_manifest.json"
)

RELEASE_AUDIT = (
    FINAL_FREEZE
    / "phase13_6_3_reproducibility_release_audit.json"
)

VALIDATION_LOCK = (
    RUNTIME_VALIDATION
    / "phase13_5_6_final_end_to_end_validation_lock.json"
)


EXPECTED_ARTIFACT_COUNT = 104
EXPECTED_POPULATION = 1178
EXPECTED_THRESHOLD = 0.115
EXPECTED_REVIEW_BUDGET = 0.15

EXPECTED_PRIORITY_DISTRIBUTION = {
    "LOW": 504,
    "MODERATE": 666,
    "HIGH": 8,
}


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

    return str(
        path.relative_to(ROOT)
    )


def check(condition, name, audit):

    status = (
        "PASSED"
        if bool(condition)
        else "FAILED"
    )

    audit[name] = status

    print(
        f"{name}: {status}"
    )

    if not condition:

        raise AssertionError(
            f"{name} FAILED"
        )


# =============================================================================
# START
# =============================================================================

banner(
    "PHASE 13.6.4 — "
    "FINAL CARECOMPUTE SYSTEM FREEZE"
)

audit = {}


# =============================================================================
# A — VERIFY FINAL FREEZE INPUTS
# =============================================================================

banner(
    "A — VERIFY FINAL FREEZE INPUTS"
)

required = {
    "inventory":
        INVENTORY,

    "inventory_audit":
        INVENTORY_AUDIT,

    "provenance":
        PROVENANCE,

    "provenance_audit":
        PROVENANCE_AUDIT,

    "release_manifest":
        RELEASE_MANIFEST,

    "release_audit":
        RELEASE_AUDIT,

    "validation_lock":
        VALIDATION_LOCK,
}


for name, path in required.items():

    print(
        f"{name}: "
        f"{'FOUND' if path.exists() else 'MISSING'}"
    )


check(
    all(
        path.exists()
        for path in required.values()
    ),
    "final_freeze_inputs_present",
    audit,
)


# =============================================================================
# B — CAPTURE PRE-FREEZE EVIDENCE HASHES
# =============================================================================

banner(
    "B — CAPTURE PRE-FREEZE EVIDENCE HASHES"
)

pre_freeze_hashes = {}

for name, path in required.items():

    digest = sha256(
        path
    )

    pre_freeze_hashes[name] = {
        "path":
            rel(path),

        "sha256":
            digest,
    }

    print(
        rel(path),
        "->",
        digest,
    )


# =============================================================================
# C — LOAD FINAL RELEASE STATE
# =============================================================================

banner(
    "C — LOAD FINAL RELEASE STATE"
)

inventory = load_json(
    INVENTORY
)

inventory_audit = load_json(
    INVENTORY_AUDIT
)

provenance = load_json(
    PROVENANCE
)

provenance_audit = load_json(
    PROVENANCE_AUDIT
)

release_manifest = load_json(
    RELEASE_MANIFEST
)

release_audit = load_json(
    RELEASE_AUDIT
)

validation_lock = load_json(
    VALIDATION_LOCK
)


print(
    "Final release state loaded: PASSED"
)


# =============================================================================
# D — VERIFY PHASE 13.6.1
# =============================================================================

banner(
    "D — VERIFY PHASE 13.6.1 ARTIFACT INVENTORY"
)

check(
    inventory.get(
        "status"
    ) == "PASSED",
    "phase13_6_1_inventory_passed",
    audit,
)

check(
    inventory.get(
        "total_artifact_count"
    ) == EXPECTED_ARTIFACT_COUNT,
    "phase13_6_1_artifact_count_104",
    audit,
)

check(
    len(
        inventory.get(
            "artifacts",
            [],
        )
    ) == EXPECTED_ARTIFACT_COUNT,
    "phase13_6_1_inventory_records_104",
    audit,
)


# =============================================================================
# E — VERIFY ALL 104 BASELINE ARTIFACT HASHES
# =============================================================================

banner(
    "E — VERIFY 104-ARTIFACT BASELINE"
)

inventory_records = inventory.get(
    "artifacts",
    [],
)

baseline_mismatches = []

for record in inventory_records:

    path = (
        ROOT
        / record["path"]
    )

    if not path.exists():

        baseline_mismatches.append({
            "path":
                record["path"],

            "reason":
                "MISSING",
        })

        continue

    observed = sha256(
        path
    )

    expected = record[
        "sha256"
    ]

    if observed != expected:

        baseline_mismatches.append({
            "path":
                record["path"],

            "reason":
                "HASH_MISMATCH",

            "expected":
                expected,

            "observed":
                observed,
        })


print(
    "Baseline artifacts:",
    len(inventory_records),
)

print(
    "Hash mismatches:",
    len(baseline_mismatches),
)


check(
    len(baseline_mismatches) == 0,
    "baseline_artifact_integrity",
    audit,
)


# =============================================================================
# F — VERIFY PHASE 13.6.2
# =============================================================================

banner(
    "F — VERIFY PHASE 13.6.2 PROVENANCE"
)

check(
    provenance.get(
        "status"
    ) == "PASSED",
    "phase13_6_2_provenance_passed",
    audit,
)

check(
    len(
        provenance.get(
            "provenance_chain",
            [],
        )
    ) == 7,
    "phase13_6_2_seven_stage_chain",
    audit,
)

check(
    provenance.get(
        "inventory_baseline",
        {},
    ).get(
        "hash_mismatches_after"
    ) == 0,
    "phase13_6_2_hash_mismatches_zero",
    audit,
)


# =============================================================================
# G — VERIFY PHASE 13.6.3
# =============================================================================

banner(
    "G — VERIFY PHASE 13.6.3 RELEASE MANIFEST"
)

check(
    release_manifest.get(
        "release_status"
    ) == "RELEASE_READY",
    "phase13_6_3_release_ready",
    audit,
)

check(
    release_manifest.get(
        "ready_for_final_system_freeze"
    ) is True,
    "phase13_6_3_ready_for_final_freeze",
    audit,
)

check(
    release_manifest.get(
        "artifact_integrity",
        {},
    ).get(
        "sha256_mismatches"
    ) == 0,
    "phase13_6_3_artifact_integrity",
    audit,
)


# =============================================================================
# H — VERIFY FINAL VALIDATION LOCK
# =============================================================================

banner(
    "H — VERIFY END-TO-END VALIDATION LOCK"
)

check(
    validation_lock.get(
        "phase13_5_status"
    ) == "VALIDATED_AND_LOCKED",
    "phase13_5_validation_locked",
    audit,
)

check(
    validation_lock.get(
        "population"
    ) == EXPECTED_POPULATION,
    "final_population_1178",
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
    "final_primary_threshold_0_115",
    audit,
)

check(
    parameters.get(
        "review_budget"
    ) == EXPECTED_REVIEW_BUDGET,
    "final_review_budget_0_15",
    audit,
)


# =============================================================================
# I — VERIFY FINAL VALIDATION EVIDENCE
# =============================================================================

banner(
    "I — VERIFY FINAL VALIDATION EVIDENCE"
)

validation_evidence = (
    validation_lock.get(
        "validation_evidence",
        {},
    )
)

check(
    validation_evidence.get(
        "contract_mismatches"
    ) == 0,
    "final_contract_mismatches_zero",
    audit,
)

check(
    validation_evidence.get(
        "safety_hitl_violations"
    ) == 0,
    "final_safety_hitl_violations_zero",
    audit,
)

check(
    validation_evidence.get(
        "deterministic_exact_matches"
    ) == "9/9",
    "final_deterministic_replay_9_of_9",
    audit,
)

check(
    validation_evidence.get(
        "failure_edge_tests"
    ) == "28/28",
    "final_failure_edge_tests_28_of_28",
    audit,
)

check(
    validation_evidence.get(
        "canonical_artifact_modification"
    ) is False,
    "final_canonical_artifacts_unmodified",
    audit,
)


# =============================================================================
# J — VERIFY FINAL SAFETY LOCK
# =============================================================================

banner(
    "J — VERIFY FINAL SAFETY LOCK"
)

safety = validation_lock.get(
    "safety_state",
    {},
)

check(
    safety.get(
        "human_review_required"
    ) is True,
    "final_human_review_required",
    audit,
)

safety_false_fields = [
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


for field in safety_false_fields:

    check(
        safety.get(field) is False,
        f"final_safety_{field}_false",
        audit,
    )


# =============================================================================
# K — VERIFY FINAL FAIRNESS LOCK
# =============================================================================

banner(
    "K — VERIFY FINAL FAIRNESS LOCK"
)

fairness = validation_lock.get(
    "fairness_state",
    {},
)

check(
    fairness.get(
        "monitor_mode"
    ) == "READ_ONLY",
    "final_fairness_monitor_read_only",
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
        f"final_fairness_{field}_false",
        audit,
    )


# =============================================================================
# L — VERIFY RELEASE MANIFEST LOCKED SYSTEM
# =============================================================================

banner(
    "L — VERIFY RELEASE MANIFEST SYSTEM STATE"
)

locked_state = (
    release_manifest.get(
        "locked_system_state",
        {},
    )
)

check(
    locked_state.get(
        "population"
    ) == EXPECTED_POPULATION,
    "release_population_lock",
    audit,
)

check(
    locked_state.get(
        "primary_threshold"
    ) == EXPECTED_THRESHOLD,
    "release_threshold_lock",
    audit,
)

check(
    locked_state.get(
        "review_budget"
    ) == EXPECTED_REVIEW_BUDGET,
    "release_review_budget_lock",
    audit,
)

check(
    locked_state.get(
        "human_review_required"
    ) is True,
    "release_hitl_lock",
    audit,
)

check(
    locked_state.get(
        "autonomous_clinical_action"
    ) is False,
    "release_no_autonomous_action",
    audit,
)


# =============================================================================
# M — VERIFY FREEZE EVIDENCE DID NOT CHANGE
# =============================================================================

banner(
    "M — VERIFY FREEZE EVIDENCE UNCHANGED"
)

freeze_evidence_mismatches = []

for name, record in pre_freeze_hashes.items():

    path = ROOT / record["path"]

    observed = sha256(
        path
    )

    if observed != record["sha256"]:

        freeze_evidence_mismatches.append(
            record["path"]
        )


print(
    "Freeze evidence mismatches:",
    len(freeze_evidence_mismatches),
)


check(
    len(freeze_evidence_mismatches) == 0,
    "freeze_evidence_unchanged",
    audit,
)


# =============================================================================
# N — CREATE FINAL SYSTEM FREEZE MANIFEST
# =============================================================================

banner(
    "N — CREATE FINAL CARECOMPUTE FREEZE MANIFEST"
)

overall_passed = all(
    value == "PASSED"
    for value in audit.values()
)

FINAL_MANIFEST = (
    FINAL_FREEZE
    / "phase13_6_4_final_carecompute_system_freeze_manifest.json"
)


final_manifest = {
    "system":
        "CareCompute",

    "phase":
        "13.6.4",

    "manifest":
        "FINAL_CARECOMPUTE_SYSTEM_FREEZE",

    "final_system":
        "System D — Learned Router",

    "system_state":
        "FROZEN",

    "runtime_mode":
        "FROZEN_HUMAN_IN_THE_LOOP",

    "scientific_state":
        "FROZEN",

    "evaluation_state":
        "FROZEN",

    "runtime_state":
        "FROZEN",

    "agent_state":
        "FROZEN",

    "orchestrator_state":
        "FROZEN",

    "validation_state":
        "VALIDATED_AND_LOCKED",

    "release_state":
        "RELEASE_READY",

    "locked_values": {
        "population":
            EXPECTED_POPULATION,

        "primary_threshold":
            EXPECTED_THRESHOLD,

        "review_budget":
            EXPECTED_REVIEW_BUDGET,

        "priority_distribution":
            EXPECTED_PRIORITY_DISTRIBUTION,
    },

    "safety_lock": {
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

    "fairness_lock": {
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

    "validation_lock": {
        "contract_mismatches":
            0,

        "safety_hitl_violations":
            0,

        "deterministic_replay":
            "9/9 exact",

        "failure_edge_case_tests":
            "28/28 passed",
    },

    "provenance_lock": {
        "verified_stages":
            7,

        "chain":
            [
                "Phase 10",
                "Phase 12",
                "Phase 13.1",
                "Phase 13.2",
                "Phase 13.3",
                "Phase 13.4",
                "Phase 13.5",
            ],
    },

    "artifact_lock": {
        "pre_phase13_6_artifacts":
            EXPECTED_ARTIFACT_COUNT,

        "sha256_mismatches":
            len(baseline_mismatches),

        "baseline_status":
            "LOCKED",
    },

    "freeze_evidence_hashes":
        pre_freeze_hashes,

    "checks":
        audit,

    "posthoc_retuning_allowed":
        False,

    "posthoc_threshold_change_allowed":
        False,

    "posthoc_review_budget_change_allowed":
        False,

    "posthoc_router_change_allowed":
        False,

    "posthoc_agent_change_allowed":
        False,

    "posthoc_priority_change_allowed":
        False,

    "final_status":
        (
            "FROZEN"
            if overall_passed
            else "FAILED"
        ),
}


with open(
    FINAL_MANIFEST,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        final_manifest,
        f,
        indent=2,
        sort_keys=True,
    )


print(
    "Saved:",
    rel(FINAL_MANIFEST),
)


# =============================================================================
# O — HASH FINAL SYSTEM FREEZE
# =============================================================================

banner(
    "O — HASH FINAL SYSTEM FREEZE"
)

final_manifest_hash = sha256(
    FINAL_MANIFEST
)

print(
    rel(FINAL_MANIFEST),
    "->",
    final_manifest_hash,
)


# =============================================================================
# P — CREATE FINAL FREEZE AUDIT
# =============================================================================

banner(
    "P — CREATE FINAL FREEZE AUDIT"
)

FINAL_AUDIT = (
    FINAL_FREEZE
    / "phase13_6_4_final_carecompute_system_freeze_audit.json"
)

final_audit = {
    "system":
        "CareCompute",

    "phase":
        "13.6.4",

    "checks":
        audit,

    "final_manifest":
        rel(FINAL_MANIFEST),

    "final_manifest_sha256":
        final_manifest_hash,

    "baseline_artifacts_verified":
        len(inventory_records),

    "baseline_hash_mismatches":
        len(baseline_mismatches),

    "freeze_evidence_mismatches":
        len(freeze_evidence_mismatches),

    "final_system":
        "System D — Learned Router",

    "final_status":
        (
            "FROZEN"
            if overall_passed
            else "FAILED"
        ),
}


with open(
    FINAL_AUDIT,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        final_audit,
        f,
        indent=2,
        sort_keys=True,
    )


print(
    "Saved:",
    rel(FINAL_AUDIT),
)


# =============================================================================
# Q — FINAL IMMUTABILITY CHECK
# =============================================================================

banner(
    "Q — FINAL IMMUTABILITY CHECK"
)

final_baseline_mismatches = []

for record in inventory_records:

    path = ROOT / record["path"]

    if sha256(path) != record["sha256"]:

        final_baseline_mismatches.append(
            record["path"]
        )


print(
    "Final baseline mismatches:",
    len(final_baseline_mismatches),
)


check(
    len(final_baseline_mismatches) == 0,
    "final_baseline_immutable",
    audit,
)


# =============================================================================
# FINAL
# =============================================================================

banner(
    "PHASE 13.6.4 COMPLETE — "
    "CARECOMPUTE FINAL SYSTEM FROZEN"
)

print("\nSYSTEM")
print(" CareCompute")

print("\nFINAL SYSTEM")
print(" System D — Learned Router")

print("\nSYSTEM STATE")
print(" FROZEN")

print("\nSCIENTIFIC STATE")
print(" FROZEN")

print("\nRUNTIME STATE")
print(" FROZEN")

print("\nVALIDATION STATE")
print(" VALIDATED_AND_LOCKED")

print("\nRELEASE STATE")
print(" RELEASE_READY")

print("\nLOCKED VALUES")
print(" Population: 1178")
print(" Primary threshold: 0.115")
print(" Review budget: 0.15")
print(
    " Priorities: "
    "LOW=504, MODERATE=666, HIGH=8"
)

print("\nVALIDATION EVIDENCE")
print(" Contract mismatches: 0")
print(" Safety/HITL violations: 0")
print(" Deterministic replay: 9/9 exact")
print(" Failure/edge tests: 28/28 passed")

print("\nSAFETY")
print(" Human review required: YES")
print(" Autonomous clinical action: NO")
print(" Ground truth exposed: NO")
print(" Patient identifier exposed: NO")

print("\nFAIRNESS")
print(" Monitor: READ ONLY")
print(" Demographics used for routing: NO")
print(" Demographics used for priority: NO")
print(" Subgroup-specific threshold: NO")

print("\nARTIFACT INTEGRITY")
print(" Baseline artifacts: 104")
print(" SHA-256 mismatches: 0")

print("\nPOST-FREEZE CHANGES")
print(" Retuning allowed: NO")
print(" Threshold changes allowed: NO")
print(" Review-budget changes allowed: NO")
print(" Router changes allowed: NO")
print(" Agent changes allowed: NO")
print(" Priority changes allowed: NO")

print("\nFINAL STATUS")

if overall_passed:
    print(" CARECOMPUTE_FINAL_SYSTEM_FROZEN")
else:
    print(" CARECOMPUTE_FINAL_SYSTEM_FREEZE_FAILED")

print(
    "\nFinal manifest:",
    rel(FINAL_MANIFEST),
)

print(
    "Final manifest SHA-256:",
    final_manifest_hash,
)

print(
    "Final audit:",
    rel(FINAL_AUDIT),
)


if not overall_passed:

    raise SystemExit(
        "Final CareCompute freeze failed."
    )


banner(
    "PHASE 13 COMPLETE — "
    "INTEGRATED CARECOMPUTE SYSTEM RELEASE LOCKED"
)