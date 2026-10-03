"""
Phase 10.6.4 — Final Phase 10 Closure Lock
CareCompute

Final read-only closure of the completed Phase 10 agentic workflow.

This script:
1. verifies all Phase 10 closure artifacts,
2. verifies the frozen CareCompute system,
3. verifies the reproducibility release manifest,
4. verifies frozen artifact hashes,
5. creates the definitive Phase 10 source-code hash snapshot,
6. creates the final Phase 10 completion manifest.

It does NOT modify any frozen model, router, rule, explanation,
case packet, threshold, review budget, or clinical workflow artifact.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


# =============================================================================
# PATHS
# =============================================================================

SRC = Path("src")
BASE = Path("results/eligible/agents")

INVENTORY_PATH = BASE / "phase10_artifact_inventory.json"
PROVENANCE_PATH = BASE / "phase10_cross_phase_provenance_audit.json"
RELEASE_PATH = BASE / "phase10_reproducibility_release_manifest.json"

FINAL_FREEZE_PATH = BASE / "carecompute_final_system_freeze_manifest.json"
SYSTEM_AUDIT_PATH = BASE / "end_to_end_system_audit.json"

OUTPUT_PATH = BASE / "phase10_final_completion_manifest.json"


# =============================================================================
# EXPECTED FINAL VALUES
# =============================================================================

EXPECTED_POPULATION = 1178
EXPECTED_THRESHOLD = 0.115
EXPECTED_REVIEW_BUDGET = 0.15

EXPECTED_PRIORITY_DISTRIBUTION = {
    "LOW": 777,
    "MODERATE": 302,
    "HIGH": 99,
}

EXPECTED_FINAL_FREEZE_PHASE = "10.5.4"
EXPECTED_INVENTORY_PHASE = "10.6.1"
EXPECTED_PROVENANCE_PHASE = "10.6.2"
EXPECTED_RELEASE_PHASE = "10.6.3"
EXPECTED_CLOSURE_PHASE = "10.6.4"


# =============================================================================
# HELPERS
# =============================================================================

def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


def file_record(path):
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 80)
    print("PHASE 10.6.4 — FINAL PHASE 10 CLOSURE LOCK")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # A — VERIFY FINAL CLOSURE ARTIFACTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("A — VERIFY FINAL CLOSURE ARTIFACTS")
    print("=" * 80)

    required = [
        INVENTORY_PATH,
        PROVENANCE_PATH,
        RELEASE_PATH,
        FINAL_FREEZE_PATH,
        SYSTEM_AUDIT_PATH,
    ]

    for path in required:

        if not path.exists():
            raise FileNotFoundError(
                f"Required Phase 10 closure artifact missing: {path}"
            )

        print("FOUND:", path)

    print("Final closure artifact presence: PASSED")

    # -------------------------------------------------------------------------
    # B — LOAD FINAL VERIFIED STATE
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("B — LOAD FINAL VERIFIED STATE")
    print("=" * 80)

    inventory = load_json(INVENTORY_PATH)
    provenance = load_json(PROVENANCE_PATH)
    release = load_json(RELEASE_PATH)
    final_freeze = load_json(FINAL_FREEZE_PATH)
    system_audit = load_json(SYSTEM_AUDIT_PATH)

    assert inventory["phase"] == EXPECTED_INVENTORY_PHASE
    assert inventory["status"] == "PASSED"

    assert provenance["phase"] == EXPECTED_PROVENANCE_PHASE
    assert provenance["status"] == "PASSED"

    assert release["phase"] == EXPECTED_RELEASE_PHASE
    assert release["status"] == "RELEASE_READY"

    assert final_freeze["phase"] == EXPECTED_FINAL_FREEZE_PHASE
    assert final_freeze["status"] == "FROZEN"

    assert system_audit["status"] == "PASSED"

    print("10.6.1 Artifact inventory: PASSED")
    print("10.6.2 Cross-phase provenance: PASSED")
    print("10.6.3 Reproducibility release: RELEASE_READY")
    print("10.5.4 Final system freeze: FROZEN")
    print("Independent system audit: PASSED")

    # -------------------------------------------------------------------------
    # C — VERIFY FINAL IMMUTABLE VALUES
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("C — VERIFY FINAL IMMUTABLE VALUES")
    print("=" * 80)

    immutable = final_freeze["immutable_system"]

    assert immutable["population"] == EXPECTED_POPULATION

    assert (
        immutable["primary_model_threshold"]
        == EXPECTED_THRESHOLD
    )

    assert (
        immutable["rescue_review_budget"]
        == EXPECTED_REVIEW_BUDGET
    )

    assert (
        immutable["priority_distribution"]
        == EXPECTED_PRIORITY_DISTRIBUTION
    )

    assert immutable["ground_truth_available_to_agents"] is False
    assert immutable["human_review_required"] is True
    assert immutable["autonomous_clinical_action"] is False

    print("Population:", EXPECTED_POPULATION)
    print("Primary threshold:", EXPECTED_THRESHOLD)
    print("Review budget:", EXPECTED_REVIEW_BUDGET)

    print(
        "Priority distribution:",
        EXPECTED_PRIORITY_DISTRIBUTION
    )

    print("Ground truth available to agents: FALSE")
    print("Human review required: TRUE")
    print("Autonomous clinical action: FALSE")

    print("Final immutable-value verification: PASSED")

    # -------------------------------------------------------------------------
    # D — VERIFY INDEPENDENT AUDIT REMAINS CLEAN
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("D — VERIFY INDEPENDENT SYSTEM AUDIT")
    print("=" * 80)

    assert system_audit["status"] == "PASSED"

    violations = system_audit["violations"]

    nonzero = {
        name: value
        for name, value in violations.items()
        if value != 0
    }

    print("Audit violation categories:", len(violations))
    print("Non-zero violation categories:", len(nonzero))

    assert not nonzero

    print("Independent system audit: PASSED")
    print("Zero-violation requirement: PASSED")

    # -------------------------------------------------------------------------
    # E — VERIFY FROZEN ARTIFACT HASH CHAIN
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("E — VERIFY FROZEN ARTIFACT HASH CHAIN")
    print("=" * 80)

    hash_errors = []

    for filename, expected_hash in (
        final_freeze["artifact_sha256"].items()
    ):

        path = BASE / filename

        if not path.exists():

            hash_errors.append(
                f"{filename}: missing"
            )

            print(filename, ": MISSING")
            continue

        current_hash = sha256_file(path)

        if current_hash != expected_hash:

            hash_errors.append(
                f"{filename}: hash mismatch"
            )

            print(filename, ": FAILED")

        else:
            print(filename, ": PASSED")

    assert not hash_errors, hash_errors

    print("Frozen artifact hash chain: PASSED")

    # -------------------------------------------------------------------------
    # F — VERIFY 10.6 RELEASE CHAIN
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("F — VERIFY PHASE 10.6 RELEASE CHAIN")
    print("=" * 80)

    assert (
        inventory["frozen_hash_verification"]
        == "PASSED"
    )

    assert all(
        provenance["checks"].values()
    )

    assert (
        provenance["final_system_status"]
        == "FROZEN"
    )

    assert (
        release["phase10_system_status"]
        == "FROZEN"
    )

    assert (
        release["ready_for_phase10_closure"]
        is True
    )

    assert (
        inventory["modifies_frozen_artifacts"]
        is False
    )

    assert (
        provenance["modifies_frozen_artifacts"]
        is False
    )

    assert (
        release["modifies_frozen_artifacts"]
        is False
    )

    print("10.6.1 integrity verification: PASSED")
    print("10.6.2 provenance verification: PASSED")
    print("10.6.3 release verification: PASSED")
    print("Frozen system preserved: PASSED")
    print("Read-only closure chain: PASSED")

    # -------------------------------------------------------------------------
    # G — VERIFY RELEASE VALUES MATCH FINAL FREEZE
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("G — VERIFY RELEASE/FREEZE CONSISTENCY")
    print("=" * 80)

    release_values = release["release_values"]

    assert (
        release_values["population"]
        == immutable["population"]
    )

    assert (
        release_values["primary_model_threshold"]
        == immutable["primary_model_threshold"]
    )

    assert (
        release_values["rescue_review_budget"]
        == immutable["rescue_review_budget"]
    )

    assert (
        release_values["priority_distribution"]
        == immutable["priority_distribution"]
    )

    assert (
        release_values["human_review_required"]
        == immutable["human_review_required"]
    )

    assert (
        release_values["autonomous_clinical_action"]
        == immutable["autonomous_clinical_action"]
    )

    print("Population consistency: PASSED")
    print("Threshold consistency: PASSED")
    print("Review-budget consistency: PASSED")
    print("Priority consistency: PASSED")
    print("Human-review consistency: PASSED")
    print("Autonomous-action consistency: PASSED")

    # -------------------------------------------------------------------------
    # H — CREATE DEFINITIVE PHASE 10 SOURCE SNAPSHOT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("H — CREATE DEFINITIVE PHASE 10 SOURCE SNAPSHOT")
    print("=" * 80)

    source_files = sorted(
        SRC.glob("phase_10_*.py")
    )

    if not source_files:
        raise RuntimeError(
            "No Phase 10 source scripts found."
        )

    source_records = []

    for path in source_files:

        record = file_record(path)
        source_records.append(record)

        print(
            f"{path.name}: "
            f"{record['sha256']}"
        )

    print("Final Phase 10 source scripts:", len(source_records))

    # -------------------------------------------------------------------------
    # I — HASH PHASE 10 CLOSURE ARTIFACTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("I — HASH PHASE 10 CLOSURE ARTIFACTS")
    print("=" * 80)

    closure_artifacts = {
        "phase10_artifact_inventory.json":
            file_record(INVENTORY_PATH),

        "phase10_cross_phase_provenance_audit.json":
            file_record(PROVENANCE_PATH),

        "phase10_reproducibility_release_manifest.json":
            file_record(RELEASE_PATH),

        "carecompute_final_system_freeze_manifest.json":
            file_record(FINAL_FREEZE_PATH),

        "end_to_end_system_audit.json":
            file_record(SYSTEM_AUDIT_PATH),
    }

    for name, record in closure_artifacts.items():
        print(
            f"{name}: {record['sha256']}"
        )

    print("Closure artifact hashing: PASSED")

    # -------------------------------------------------------------------------
    # J — DEFINE FINAL PHASE 10 STATUS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("J — DEFINE FINAL PHASE 10 STATUS")
    print("=" * 80)

    final_status = {
        "phase":
            "10",

        "engineering_status":
            "COMPLETE",

        "release_status":
            "LOCKED",

        "system_status":
            "FROZEN",

        "population":
            EXPECTED_POPULATION,

        "primary_model_threshold":
            EXPECTED_THRESHOLD,

        "rescue_review_budget":
            EXPECTED_REVIEW_BUDGET,

        "priority_distribution":
            EXPECTED_PRIORITY_DISTRIBUTION,

        "ground_truth_available_to_agents":
            False,

        "human_review_required":
            True,

        "autonomous_clinical_action":
            False,

        "independent_system_audit":
            "PASSED",

        "cross_phase_provenance":
            "PASSED",

        "reproducibility_release":
            "RELEASE_READY",

        "frozen_artifact_integrity":
            "PASSED",
    }

    for key, value in final_status.items():
        print(f"{key}: {value}")

    # -------------------------------------------------------------------------
    # K — CREATE FINAL PHASE 10 COMPLETION MANIFEST
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("K — CREATE FINAL PHASE 10 COMPLETION MANIFEST")
    print("=" * 80)

    manifest = {
        "phase": EXPECTED_CLOSURE_PHASE,

        "name":
            "CareCompute Phase 10 Final Completion Manifest",

        "status":
            "PHASE_10_COMPLETE",

        "release_status":
            "LOCKED",

        "generated_utc":
            datetime.now(timezone.utc).isoformat(),

        "system_name":
            "CareCompute",

        "final_phase10_status":
            final_status,

        "phase10_source_scripts":
            source_records,

        "phase10_source_script_count":
            len(source_records),

        "closure_artifacts":
            closure_artifacts,

        "frozen_system_artifact_sha256":
            final_freeze["artifact_sha256"],

        "closure_chain": [
            {
                "phase": "10.6.1",
                "status": "PASSED",
                "artifact": str(INVENTORY_PATH),
            },
            {
                "phase": "10.6.2",
                "status": "PASSED",
                "artifact": str(PROVENANCE_PATH),
            },
            {
                "phase": "10.6.3",
                "status": "RELEASE_READY",
                "artifact": str(RELEASE_PATH),
            },
            {
                "phase": "10.6.4",
                "status": "PHASE_10_COMPLETE",
                "artifact": str(OUTPUT_PATH),
            },
        ],

        "change_control": {
            "phase10_closed":
                True,

            "release_locked":
                True,

            "frozen_system_may_be_modified":
                False,

            "future_change_requires_new_version":
                True,

            "future_change_requires_revalidation":
                True,

            "future_change_requires_new_release_manifest":
                True,
        },

        "safety_closure": {
            "ground_truth_excluded_from_agents":
                True,

            "prediction_modification_prohibited":
                True,

            "router_modification_prohibited":
                True,

            "priority_modification_prohibited":
                True,

            "explanation_modification_prohibited":
                True,

            "diagnosis_prohibited":
                True,

            "treatment_recommendation_prohibited":
                True,

            "medication_recommendation_prohibited":
                True,

            "autonomous_clinical_action_prohibited":
                True,

            "human_review_required":
                True,
        },

        "modifies_frozen_artifacts":
            False,
    }

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            manifest,
            f,
            indent=2,
            sort_keys=True
        )

    print(
        "Final completion manifest:",
        OUTPUT_PATH
    )

    # -------------------------------------------------------------------------
    # L — VERIFY FINAL COMPLETION MANIFEST
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("L — VERIFY FINAL COMPLETION MANIFEST")
    print("=" * 80)

    written = load_json(OUTPUT_PATH)

    assert written["phase"] == EXPECTED_CLOSURE_PHASE
    assert written["status"] == "PHASE_10_COMPLETE"
    assert written["release_status"] == "LOCKED"

    assert (
        written["final_phase10_status"]
        ["engineering_status"]
        == "COMPLETE"
    )

    assert (
        written["final_phase10_status"]
        ["system_status"]
        == "FROZEN"
    )

    assert (
        written["change_control"]
        ["phase10_closed"]
        is True
    )

    assert (
        written["change_control"]
        ["release_locked"]
        is True
    )

    assert (
        written["change_control"]
        ["frozen_system_may_be_modified"]
        is False
    )

    assert (
        written["safety_closure"]
        ["human_review_required"]
        is True
    )

    assert (
        written["safety_closure"]
        ["autonomous_clinical_action_prohibited"]
        is True
    )

    assert written["modifies_frozen_artifacts"] is False

    print("Completion status: PHASE_10_COMPLETE")
    print("Release status: LOCKED")
    print("System status: FROZEN")
    print("Change control: LOCKED")
    print("Human-review requirement: PRESERVED")
    print("Read-only closure: PASSED")
    print("Final completion manifest: PASSED")

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("PHASE 10 COMPLETE — RELEASE LOCKED")
    print("=" * 80)

    print(
        "\nCareCompute Phase 10 is formally complete."
    )

    print(
        "The validated human-in-the-loop Rescue Review "
        "workflow remains frozen."
    )

    print(
        "Any future system change requires a new version, "
        "revalidation, and a new release manifest."
    )


if __name__ == "__main__":
    main()
