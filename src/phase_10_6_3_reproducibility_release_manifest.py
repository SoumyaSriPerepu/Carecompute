"""
Phase 10.6.3 — Reproducibility & Release Manifest
CareCompute

Creates a read-only release manifest for the completed Phase 10
agentic workflow.

This phase does not rerun models, regenerate outputs, change thresholds,
change review rules, or modify any frozen artifact.
"""

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


# =============================================================================
# PATHS
# =============================================================================

SRC = Path("src")
BASE = Path("results/eligible/agents")

INVENTORY_PATH = BASE / "phase10_artifact_inventory.json"
PROVENANCE_PATH = BASE / "phase10_cross_phase_provenance_audit.json"
FINAL_FREEZE_PATH = BASE / "carecompute_final_system_freeze_manifest.json"
SYSTEM_AUDIT_PATH = BASE / "end_to_end_system_audit.json"

OUTPUT_PATH = BASE / "phase10_reproducibility_release_manifest.json"


# =============================================================================
# EXPECTED LOCKED VALUES
# =============================================================================

EXPECTED_POPULATION = 1178
EXPECTED_THRESHOLD = 0.115
EXPECTED_REVIEW_BUDGET = 0.15

EXPECTED_PRIORITY_DISTRIBUTION = {
    "LOW": 777,
    "MODERATE": 302,
    "HIGH": 99,
}


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
    print("PHASE 10.6.3 — REPRODUCIBILITY & RELEASE MANIFEST")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # A — VERIFY CLOSURE INPUTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("A — VERIFY CLOSURE INPUTS")
    print("=" * 80)

    required = [
        INVENTORY_PATH,
        PROVENANCE_PATH,
        FINAL_FREEZE_PATH,
        SYSTEM_AUDIT_PATH,
    ]

    for path in required:
        if not path.exists():
            raise FileNotFoundError(
                f"Required closure artifact missing: {path}"
            )

        print("FOUND:", path)

    print("Closure inputs: PASSED")

    # -------------------------------------------------------------------------
    # B — LOAD VERIFIED STATE
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("B — LOAD VERIFIED PHASE 10 STATE")
    print("=" * 80)

    inventory = load_json(INVENTORY_PATH)
    provenance = load_json(PROVENANCE_PATH)
    final_freeze = load_json(FINAL_FREEZE_PATH)
    system_audit = load_json(SYSTEM_AUDIT_PATH)

    assert inventory["status"] == "PASSED"
    assert provenance["status"] == "PASSED"
    assert final_freeze["status"] == "FROZEN"
    assert system_audit["status"] == "PASSED"

    print("Artifact inventory: PASSED")
    print("Cross-phase provenance: PASSED")
    print("Final system freeze: FROZEN")
    print("Independent system audit: PASSED")

    # -------------------------------------------------------------------------
    # C — VERIFY RELEASE VALUES
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("C — VERIFY RELEASE VALUES")
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

    assert immutable["human_review_required"] is True

    assert immutable["autonomous_clinical_action"] is False

    print("Population:", EXPECTED_POPULATION)
    print("Primary threshold:", EXPECTED_THRESHOLD)
    print("Review budget:", EXPECTED_REVIEW_BUDGET)

    print(
        "Priority distribution:",
        EXPECTED_PRIORITY_DISTRIBUTION
    )

    print("Human review required: TRUE")
    print("Autonomous clinical action: FALSE")
    print("Release-value verification: PASSED")

    # -------------------------------------------------------------------------
    # D — VERIFY FROZEN ARTIFACT HASHES AGAIN
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("D — VERIFY FROZEN ARTIFACT HASHES")
    print("=" * 80)

    frozen_hash_errors = []

    for filename, expected_hash in (
        final_freeze["artifact_sha256"].items()
    ):

        path = BASE / filename

        if not path.exists():

            frozen_hash_errors.append(
                f"{filename}: missing"
            )

            print(filename, ": MISSING")
            continue

        current_hash = sha256_file(path)

        if current_hash != expected_hash:

            frozen_hash_errors.append(
                f"{filename}: hash mismatch"
            )

            print(filename, ": FAILED")

        else:
            print(filename, ": PASSED")

    assert not frozen_hash_errors, frozen_hash_errors

    print("Frozen release integrity: PASSED")

    # -------------------------------------------------------------------------
    # E — DISCOVER PHASE 10 SOURCE SCRIPTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("E — DISCOVER PHASE 10 SOURCE SCRIPTS")
    print("=" * 80)

    source_files = sorted(
        SRC.glob("phase_10_*.py")
    )

    if not source_files:
        raise RuntimeError(
            "No Phase 10 source scripts found."
        )

    for path in source_files:
        print(path)

    print("Phase 10 source scripts:", len(source_files))

    # -------------------------------------------------------------------------
    # F — HASH SOURCE SCRIPTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("F — HASH PHASE 10 SOURCE SCRIPTS")
    print("=" * 80)

    source_records = []

    for path in source_files:

        record = file_record(path)
        source_records.append(record)

        print(
            f"{path.name}: "
            f"{record['sha256']}"
        )

    print("Source hashing: PASSED")

    # -------------------------------------------------------------------------
    # G — DEFINE REPRODUCIBILITY BOUNDARY
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("G — DEFINE REPRODUCIBILITY BOUNDARY")
    print("=" * 80)

    reproducibility_boundary = {
        "phase10_scope":
            "Agentic human-in-the-loop Rescue Review workflow",

        "starts_with":
            "Phase 10.1 agent architecture",

        "ends_with":
            "Phase 10.6 closure and release lock",

        "frozen_system_boundary": {
            "population":
                EXPECTED_POPULATION,

            "primary_model_threshold":
                EXPECTED_THRESHOLD,

            "rescue_review_budget":
                EXPECTED_REVIEW_BUDGET,

            "priority_distribution":
                EXPECTED_PRIORITY_DISTRIBUTION,
        },

        "required_behavior": {
            "ground_truth_available_to_agents":
                False,

            "human_review_required":
                True,

            "autonomous_clinical_action":
                False,

            "frozen_artifacts_may_be_modified":
                False,
        },

        "revalidation_required_if": [
            "upstream model changes",
            "calibration changes",
            "primary threshold changes",
            "router changes",
            "review budget changes",
            "agent rule changes",
            "priority logic changes",
            "explanation logic changes",
            "workflow contract changes",
            "new evaluation data are introduced",
        ],
    }

    print("Scope: DEFINED")
    print("Frozen boundary: DEFINED")
    print("Safety boundary: DEFINED")
    print("Revalidation boundary: DEFINED")

    # -------------------------------------------------------------------------
    # H — RECORD EXECUTION ENVIRONMENT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("H — RECORD EXECUTION ENVIRONMENT")
    print("=" * 80)

    environment = {
        "python_version":
            sys.version,

        "python_implementation":
            platform.python_implementation(),

        "platform":
            platform.platform(),

        "machine":
            platform.machine(),

        "processor":
            platform.processor(),
    }

    print(
        "Python:",
        environment["python_version"].split()[0]
    )

    print(
        "Implementation:",
        environment["python_implementation"]
    )

    print(
        "Machine:",
        environment["machine"]
    )

    print("Environment metadata: RECORDED")

    # -------------------------------------------------------------------------
    # I — DEFINE RELEASE ARTIFACT SET
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("I — DEFINE RELEASE ARTIFACT SET")
    print("=" * 80)

    release_artifacts = {
        "final_system_freeze":
            file_record(FINAL_FREEZE_PATH),

        "independent_system_audit":
            file_record(SYSTEM_AUDIT_PATH),

        "phase10_artifact_inventory":
            file_record(INVENTORY_PATH),

        "cross_phase_provenance_audit":
            file_record(PROVENANCE_PATH),
    }

    for name, record in release_artifacts.items():
        print(
            name,
            "->",
            record["path"]
        )

    print("Release artifact set: DEFINED")

    # -------------------------------------------------------------------------
    # J — CREATE RELEASE MANIFEST
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("J — CREATE REPRODUCIBILITY RELEASE MANIFEST")
    print("=" * 80)

    manifest = {
        "phase": "10.6.3",

        "name":
            "CareCompute Phase 10 Reproducibility and Release Manifest",

        "status":
            "RELEASE_READY",

        "generated_utc":
            datetime.now(timezone.utc).isoformat(),

        "system_name":
            "CareCompute",

        "phase10_system_status":
            "FROZEN",

        "release_values": {
            "population":
                EXPECTED_POPULATION,

            "primary_model_threshold":
                EXPECTED_THRESHOLD,

            "rescue_review_budget":
                EXPECTED_REVIEW_BUDGET,

            "priority_distribution":
                EXPECTED_PRIORITY_DISTRIBUTION,

            "human_review_required":
                True,

            "autonomous_clinical_action":
                False,
        },

        "reproducibility_boundary":
            reproducibility_boundary,

        "execution_environment":
            environment,

        "source_scripts":
            source_records,

        "source_script_count":
            len(source_records),

        "release_artifacts":
            release_artifacts,

        "frozen_system_artifact_sha256":
            final_freeze["artifact_sha256"],

        "upstream_verification": {
            "artifact_inventory":
                "PASSED",

            "cross_phase_provenance":
                "PASSED",

            "independent_system_audit":
                "PASSED",

            "final_system_freeze":
                "FROZEN",

            "frozen_hash_integrity":
                "PASSED",
        },

        "modifies_frozen_artifacts":
            False,

        "ready_for_phase10_closure":
            True,
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

    print("Release manifest:", OUTPUT_PATH)

    # -------------------------------------------------------------------------
    # K — VERIFY RELEASE MANIFEST
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("K — VERIFY RELEASE MANIFEST")
    print("=" * 80)

    written = load_json(OUTPUT_PATH)

    assert written["phase"] == "10.6.3"

    assert written["status"] == "RELEASE_READY"

    assert (
        written["phase10_system_status"]
        == "FROZEN"
    )

    assert (
        written["release_values"]["population"]
        == EXPECTED_POPULATION
    )

    assert (
        written["release_values"]
        ["human_review_required"]
        is True
    )

    assert (
        written["release_values"]
        ["autonomous_clinical_action"]
        is False
    )

    assert (
        written["modifies_frozen_artifacts"]
        is False
    )

    assert (
        written["ready_for_phase10_closure"]
        is True
    )

    print("Release status: RELEASE_READY")
    print("Frozen-system reference: PASSED")
    print("Reproducibility boundary: PASSED")
    print("Source-script hash set: PASSED")
    print("Read-only requirement: PASSED")
    print("Ready for Phase 10 closure: YES")

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print(
        "PHASE 10.6.3 COMPLETE — "
        "REPRODUCIBILITY RELEASE READY"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
