"""
Phase 10.6.1 — Phase 10 Artifact Inventory
CareCompute

Creates a read-only inventory of Phase 10 source files and generated
artifacts. No frozen artifact is modified.
"""

import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone


SRC = Path("src")
RESULTS = Path("results/eligible")
AGENTS = RESULTS / "agents"

OUTPUT = AGENTS / "phase10_artifact_inventory.json"


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def describe_file(path):

    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def main():

    print("=" * 80)
    print("PHASE 10.6.1 — PHASE 10 ARTIFACT INVENTORY")
    print("=" * 80)

    # =========================================================================
    # A — FIND PHASE 10 SOURCE FILES
    # =========================================================================

    print("\n" + "=" * 80)
    print("A — DISCOVER PHASE 10 SOURCE FILES")
    print("=" * 80)

    source_files = sorted(
        SRC.glob("phase_10_*.py")
    )

    if not source_files:
        raise RuntimeError(
            "No Phase 10 source files found."
        )

    for path in source_files:
        print(path)

    print("\nPhase 10 source files:", len(source_files))

    # =========================================================================
    # B — VERIFY CRITICAL ARTIFACTS
    # =========================================================================

    print("\n" + "=" * 80)
    print("B — VERIFY CRITICAL PHASE 10 ARTIFACTS")
    print("=" * 80)

    critical = [
        AGENTS / "patient_agent_contexts.jsonl",

        AGENTS / "rescue_review_agent_frozen_rules.json",

        AGENTS / "explanation_agent_output_contract.json",

        AGENTS / "explanation_agent_outputs.jsonl",

        AGENTS / "explanation_fidelity_safety_audit.json",

        AGENTS / "explanation_agent_freeze_manifest.json",

        AGENTS / "end_to_end_workflow_contract.json",

        AGENTS / "end_to_end_case_packets.jsonl",

        AGENTS / "end_to_end_replay_summary.json",

        AGENTS / "end_to_end_system_audit.json",

        AGENTS / "carecompute_final_system_freeze_manifest.json",
    ]

    missing = []

    for path in critical:

        if path.exists():
            print("FOUND:", path)

        else:
            print("MISSING:", path)
            missing.append(str(path))

    if missing:
        raise RuntimeError(
            f"Missing critical Phase 10 artifacts: {missing}"
        )

    print("Critical artifact presence: PASSED")

    # =========================================================================
    # C — DISCOVER AGENT ARTIFACTS
    # =========================================================================

    print("\n" + "=" * 80)
    print("C — INVENTORY AGENT ARTIFACTS")
    print("=" * 80)

    artifact_extensions = {
        ".json",
        ".jsonl",
        ".csv",
    }

    agent_files = sorted(
        path
        for path in AGENTS.rglob("*")
        if (
            path.is_file()
            and path.suffix.lower()
            in artifact_extensions
            and path != OUTPUT
        )
    )

    print("Agent artifacts:", len(agent_files))

    for path in agent_files:
        print(path)

    # =========================================================================
    # D — VERIFY FINAL FREEZE
    # =========================================================================

    print("\n" + "=" * 80)
    print("D — VERIFY FINAL SYSTEM FREEZE")
    print("=" * 80)

    freeze_path = (
        AGENTS
        / "carecompute_final_system_freeze_manifest.json"
    )

    with freeze_path.open(
        "r",
        encoding="utf-8"
    ) as f:
        freeze = json.load(f)

    assert freeze["phase"] == "10.5.4"
    assert freeze["status"] == "FROZEN"

    assert (
        freeze["immutable_system"]["population"]
        == 1178
    )

    assert (
        freeze["immutable_system"]
        ["human_review_required"]
        is True
    )

    assert (
        freeze["immutable_system"]
        ["autonomous_clinical_action"]
        is False
    )

    print("Final freeze phase: 10.5.4")
    print("Final system status: FROZEN")
    print("Population: 1178")
    print("Human review required: TRUE")
    print("Autonomous clinical action: FALSE")
    print("Final freeze verification: PASSED")

    # =========================================================================
    # E — VERIFY FROZEN HASHES
    # =========================================================================

    print("\n" + "=" * 80)
    print("E — VERIFY FINAL FREEZE HASHES")
    print("=" * 80)

    hash_errors = []

    for filename, expected_hash in (
        freeze["artifact_sha256"].items()
    ):

        path = AGENTS / filename

        if not path.exists():

            hash_errors.append({
                "file": filename,
                "reason": "missing",
            })

            print("MISSING:", filename)
            continue

        current_hash = sha256_file(path)

        status = (
            "PASSED"
            if current_hash == expected_hash
            else "FAILED"
        )

        print(f"{filename}: {status}")

        if current_hash != expected_hash:

            hash_errors.append({
                "file": filename,
                "reason": "hash_mismatch",
                "expected": expected_hash,
                "current": current_hash,
            })

    if hash_errors:
        raise RuntimeError(
            f"Frozen artifact integrity failed: "
            f"{hash_errors}"
        )

    print("Final frozen artifact integrity: PASSED")

    # =========================================================================
    # F — BUILD INVENTORY
    # =========================================================================

    print("\n" + "=" * 80)
    print("F — BUILD PHASE 10 INVENTORY")
    print("=" * 80)

    inventory = {
        "phase": "10.6.1",

        "name":
            "Phase 10 Artifact Inventory",

        "status":
            "PASSED",

        "generated_utc":
            datetime.now(timezone.utc).isoformat(),

        "phase10_source_files": [
            describe_file(path)
            for path in source_files
        ],

        "critical_artifacts": [
            describe_file(path)
            for path in critical
        ],

        "agent_artifacts": [
            describe_file(path)
            for path in agent_files
        ],

        "counts": {
            "phase10_source_files":
                len(source_files),

            "critical_artifacts":
                len(critical),

            "agent_artifacts":
                len(agent_files),
        },

        "final_system": {
            "freeze_phase":
                freeze["phase"],

            "status":
                freeze["status"],

            "population":
                freeze["immutable_system"]
                ["population"],

            "primary_model_threshold":
                freeze["immutable_system"]
                ["primary_model_threshold"],

            "rescue_review_budget":
                freeze["immutable_system"]
                ["rescue_review_budget"],

            "human_review_required":
                freeze["immutable_system"]
                ["human_review_required"],

            "autonomous_clinical_action":
                freeze["immutable_system"]
                ["autonomous_clinical_action"],
        },

        "frozen_hash_verification":
            "PASSED",

        "modifies_frozen_artifacts":
            False,
    }

    with OUTPUT.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            inventory,
            f,
            indent=2,
            sort_keys=True
        )

    print("Inventory:", OUTPUT)

    # =========================================================================
    # G — VERIFY INVENTORY
    # =========================================================================

    print("\n" + "=" * 80)
    print("G — VERIFY INVENTORY")
    print("=" * 80)

    with OUTPUT.open(
        "r",
        encoding="utf-8"
    ) as f:
        written = json.load(f)

    assert written["phase"] == "10.6.1"
    assert written["status"] == "PASSED"

    assert (
        written["final_system"]["status"]
        == "FROZEN"
    )

    assert (
        written["frozen_hash_verification"]
        == "PASSED"
    )

    assert (
        written["modifies_frozen_artifacts"]
        is False
    )

    print("Inventory structure: PASSED")
    print("Final freeze reference: PASSED")
    print("Read-only requirement: PASSED")

    # =========================================================================
    # FINAL
    # =========================================================================

    print("\n" + "=" * 80)
    print(
        "PHASE 10.6.1 COMPLETE — "
        "ARTIFACT INVENTORY PASSED"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
