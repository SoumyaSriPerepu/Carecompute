"""
Phase 10.5.4 — Final CareCompute System Freeze

Freezes the independently validated end-to-end CareCompute
human-in-the-loop Rescue Review workflow.

No model, router, priority, explanation, packet, threshold,
or review-budget artifact is modified.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


# =============================================================================
# PATHS
# =============================================================================

BASE = Path("results/eligible/agents")

CONTEXT_PATH = BASE / "patient_agent_contexts.jsonl"
RULES_PATH = BASE / "rescue_review_agent_frozen_rules.json"

EXPLANATION_OUTPUT_PATH = BASE / "explanation_agent_outputs.jsonl"
EXPLANATION_FREEZE_PATH = BASE / "explanation_agent_freeze_manifest.json"

WORKFLOW_CONTRACT_PATH = BASE / "end_to_end_workflow_contract.json"
PACKET_PATH = BASE / "end_to_end_case_packets.jsonl"
REPLAY_SUMMARY_PATH = BASE / "end_to_end_replay_summary.json"
SYSTEM_AUDIT_PATH = BASE / "end_to_end_system_audit.json"

FINAL_FREEZE_PATH = BASE / "carecompute_final_system_freeze_manifest.json"


# =============================================================================
# FROZEN EXPECTATIONS
# =============================================================================

EXPECTED_POPULATION = 1178

EXPECTED_THRESHOLD = 0.115
EXPECTED_REVIEW_BUDGET = 0.15

EXPECTED_RULE_VERSION = "10.3.4"
EXPECTED_EXPLANATION_SCHEMA = "10.4.2"
EXPECTED_WORKFLOW_CONTRACT = "10.5.1"
EXPECTED_PACKET_SCHEMA = "10.5.2"
EXPECTED_AUDIT_PHASE = "10.5.3"

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


def load_jsonl(path):
    records = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                records.append(json.loads(line))

    return records


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 80)
    print("PHASE 10.5.4 — FINAL CARECOMPUTE SYSTEM FREEZE")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # A — VERIFY REQUIRED ARTIFACTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("A — VERIFY FINAL SYSTEM ARTIFACTS")
    print("=" * 80)

    required_paths = [
        CONTEXT_PATH,
        RULES_PATH,
        EXPLANATION_OUTPUT_PATH,
        EXPLANATION_FREEZE_PATH,
        WORKFLOW_CONTRACT_PATH,
        PACKET_PATH,
        REPLAY_SUMMARY_PATH,
        SYSTEM_AUDIT_PATH,
    ]

    for path in required_paths:

        if not path.exists():
            raise FileNotFoundError(
                f"Required final artifact missing: {path}"
            )

        print(f"FOUND: {path}")

    print("Required final artifacts: PASSED")

    # -------------------------------------------------------------------------
    # B — LOAD FINAL SYSTEM
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("B — LOAD VALIDATED END-TO-END SYSTEM")
    print("=" * 80)

    contexts = load_jsonl(CONTEXT_PATH)
    rules = load_json(RULES_PATH)
    explanations = load_jsonl(EXPLANATION_OUTPUT_PATH)
    explanation_freeze = load_json(EXPLANATION_FREEZE_PATH)

    workflow_contract = load_json(WORKFLOW_CONTRACT_PATH)
    packets = load_jsonl(PACKET_PATH)
    replay_summary = load_json(REPLAY_SUMMARY_PATH)
    system_audit = load_json(SYSTEM_AUDIT_PATH)

    print("Contexts:", len(contexts))
    print("Explanations:", len(explanations))
    print("Final packets:", len(packets))
    print("Rescue rules:", rules["status"])
    print("Explanation subsystem:", explanation_freeze["status"])
    print("System audit:", system_audit["status"])

    # -------------------------------------------------------------------------
    # C — VERIFY FINAL FREEZE PRECONDITIONS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("C — VERIFY FINAL FREEZE PRECONDITIONS")
    print("=" * 80)

    assert len(contexts) == EXPECTED_POPULATION
    assert len(explanations) == EXPECTED_POPULATION
    assert len(packets) == EXPECTED_POPULATION

    assert rules["rule_version"] == EXPECTED_RULE_VERSION
    assert rules["status"] == "FROZEN"

    assert explanation_freeze["status"] == "FROZEN"

    assert (
        workflow_contract["contract_version"]
        == EXPECTED_WORKFLOW_CONTRACT
    )

    assert (
        system_audit["phase"]
        == EXPECTED_AUDIT_PHASE
    )

    assert system_audit["status"] == "PASSED"

    assert all(
        x["schema_version"] == EXPECTED_EXPLANATION_SCHEMA
        for x in explanations
    )

    assert all(
        x["schema_version"] == EXPECTED_PACKET_SCHEMA
        for x in packets
    )

    assert (
        rules["frozen_primary_model_threshold"]
        == EXPECTED_THRESHOLD
    )

    assert (
        rules["frozen_router_review_budget"]
        == EXPECTED_REVIEW_BUDGET
    )

    assert (
        system_audit["priority_distribution"]
        == EXPECTED_PRIORITY_DISTRIBUTION
    )

    print("Population lock: PASSED")
    print("Rescue Review rules lock: PASSED")
    print("Explanation Agent freeze: PASSED")
    print("Workflow contract lock: PASSED")
    print("Packet-schema lock: PASSED")
    print("Independent system audit: PASSED")
    print("Primary threshold lock: PASSED")
    print("Review-budget lock: PASSED")
    print("Priority-distribution lock: PASSED")

    # -------------------------------------------------------------------------
    # D — VERIFY ZERO AUDIT VIOLATIONS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("D — VERIFY ZERO END-TO-END VIOLATIONS")
    print("=" * 80)

    violations = system_audit["violations"]

    nonzero_violations = {
        name: count
        for name, count in violations.items()
        if count != 0
    }

    print(
        "Audit violation categories:",
        len(violations)
    )

    print(
        "Non-zero violation categories:",
        len(nonzero_violations)
    )

    if nonzero_violations:
        print(nonzero_violations)

    assert not nonzero_violations

    print("Zero-violation requirement: PASSED")

    # -------------------------------------------------------------------------
    # E — VERIFY AUDITED ARTIFACT HASHES
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("E — VERIFY SYSTEM AUDIT HASHES")
    print("=" * 80)

    audited_hashes = system_audit["artifact_sha256"]

    audited_paths = {
        "patient_agent_contexts.jsonl":
            CONTEXT_PATH,

        "explanation_agent_outputs.jsonl":
            EXPLANATION_OUTPUT_PATH,

        "end_to_end_workflow_contract.json":
            WORKFLOW_CONTRACT_PATH,

        "end_to_end_case_packets.jsonl":
            PACKET_PATH,

        "end_to_end_replay_summary.json":
            REPLAY_SUMMARY_PATH,
    }

    for name, path in audited_paths.items():

        current = sha256_file(path)
        audited = audited_hashes[name]

        print(name)
        print("  audited:", audited)
        print("  current:", current)

        assert current == audited

    print(
        "Artifact integrity since independent system audit: PASSED"
    )

    # -------------------------------------------------------------------------
    # F — VERIFY HUMAN-IN-THE-LOOP LOCK
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("F — VERIFY HUMAN-IN-THE-LOOP LOCK")
    print("=" * 80)

    human_review_count = sum(
        packet["workflow_disposition"]
        == "HUMAN_REVIEW_REQUIRED"
        for packet in packets
    )

    autonomous_action_count = sum(
        packet["autonomous_clinical_action"]
        is True
        for packet in packets
    )

    safety_flag_count = sum(
        packet["safety_flag"] is True
        for packet in packets
    )

    assert human_review_count == EXPECTED_POPULATION
    assert autonomous_action_count == 0
    assert safety_flag_count == 0

    print(
        "Human-review-required packets:",
        human_review_count
    )

    print(
        "Autonomous clinical actions:",
        autonomous_action_count
    )

    print(
        "Safety flags:",
        safety_flag_count
    )

    print("Human-in-the-loop lock: PASSED")

    # -------------------------------------------------------------------------
    # G — DEFINE FINAL IMMUTABLE SYSTEM
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("G — DEFINE FINAL IMMUTABLE SYSTEM")
    print("=" * 80)

    immutable_system = {
        "population":
            EXPECTED_POPULATION,

        "primary_model_threshold":
            EXPECTED_THRESHOLD,

        "rescue_review_budget":
            EXPECTED_REVIEW_BUDGET,

        "rescue_review_rule_version":
            EXPECTED_RULE_VERSION,

        "explanation_output_schema":
            EXPECTED_EXPLANATION_SCHEMA,

        "workflow_contract_version":
            EXPECTED_WORKFLOW_CONTRACT,

        "final_packet_schema":
            EXPECTED_PACKET_SCHEMA,

        "priority_distribution":
            EXPECTED_PRIORITY_DISTRIBUTION,

        "workflow_disposition":
            "HUMAN_REVIEW_REQUIRED",

        "autonomous_clinical_action":
            False,

        "ground_truth_available_to_agents":
            False,

        "human_review_required":
            True,
    }

    for key, value in immutable_system.items():
        print(f"{key}: {value}")

    # -------------------------------------------------------------------------
    # H — CREATE COMPLETE ARTIFACT HASH SET
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("H — HASH FINAL SYSTEM ARTIFACTS")
    print("=" * 80)

    final_hashes = {
        "patient_agent_contexts.jsonl":
            sha256_file(CONTEXT_PATH),

        "rescue_review_agent_frozen_rules.json":
            sha256_file(RULES_PATH),

        "explanation_agent_outputs.jsonl":
            sha256_file(EXPLANATION_OUTPUT_PATH),

        "explanation_agent_freeze_manifest.json":
            sha256_file(EXPLANATION_FREEZE_PATH),

        "end_to_end_workflow_contract.json":
            sha256_file(WORKFLOW_CONTRACT_PATH),

        "end_to_end_case_packets.jsonl":
            sha256_file(PACKET_PATH),

        "end_to_end_replay_summary.json":
            sha256_file(REPLAY_SUMMARY_PATH),

        "end_to_end_system_audit.json":
            sha256_file(SYSTEM_AUDIT_PATH),
    }

    for name, digest in final_hashes.items():
        print(f"{name}: {digest}")

    # -------------------------------------------------------------------------
    # I — CREATE FINAL FREEZE MANIFEST
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("I — CREATE FINAL SYSTEM FREEZE MANIFEST")
    print("=" * 80)

    manifest = {
        "phase": "10.5.4",

        "system_name":
            "CareCompute",

        "workflow_name":
            "Human-in-the-Loop Rescue Review Workflow",

        "status":
            "FROZEN",

        "freeze_timestamp_utc":
            datetime.now(timezone.utc).isoformat(),

        "purpose":
            "Freeze the independently validated end-to-end "
            "CareCompute Rescue Review workflow.",

        "immutable_system":
            immutable_system,

        "artifact_sha256":
            final_hashes,

        "independent_system_audit": {
            "phase":
                system_audit["phase"],

            "status":
                system_audit["status"],

            "artifact":
                str(SYSTEM_AUDIT_PATH),

            "sha256":
                sha256_file(SYSTEM_AUDIT_PATH),
        },

        "safety_constraints": {
            "ground_truth_allowed":
                False,

            "prediction_modification_allowed":
                False,

            "probability_modification_allowed":
                False,

            "router_modification_allowed":
                False,

            "threshold_modification_allowed":
                False,

            "review_budget_modification_allowed":
                False,

            "review_priority_modification_allowed":
                False,

            "explanation_modification_allowed":
                False,

            "diagnosis_allowed":
                False,

            "treatment_recommendation_allowed":
                False,

            "medication_recommendation_allowed":
                False,

            "demographic_causal_explanation_allowed":
                False,

            "autonomous_clinical_action_allowed":
                False,

            "human_review_required":
                True,
        },

        "change_control": {
            "system_frozen":
                True,

            "model_change_requires_new_version":
                True,

            "calibration_change_requires_new_version":
                True,

            "threshold_change_requires_new_version":
                True,

            "router_change_requires_new_version":
                True,

            "review_budget_change_requires_new_version":
                True,

            "agent_rule_change_requires_new_version":
                True,

            "priority_logic_change_requires_new_version":
                True,

            "explanation_change_requires_new_version":
                True,

            "workflow_contract_change_requires_new_version":
                True,

            "new_data_requires_revalidation":
                True,

            "any_upstream_change_requires_end_to_end_revalidation":
                True,
        },

        "validation_summary": {
            "population_complete":
                True,

            "primary_model_preserved":
                True,

            "router_preserved":
                True,

            "review_priority_preserved":
                True,

            "explanations_preserved":
                True,

            "prohibited_fields_absent":
                True,

            "ground_truth_leakage_absent":
                True,

            "demographic_causal_language_absent":
                True,

            "human_in_the_loop_safety_passed":
                True,

            "deterministic_replay_passed":
                True,

            "independent_system_audit_passed":
                True,

            "artifact_integrity_passed":
                True,
        },
    }

    with FINAL_FREEZE_PATH.open(
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
        "Final freeze manifest:",
        FINAL_FREEZE_PATH
    )

    # -------------------------------------------------------------------------
    # J — VERIFY FINAL FREEZE
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("J — VERIFY FINAL SYSTEM FREEZE")
    print("=" * 80)

    written = load_json(FINAL_FREEZE_PATH)

    assert written["status"] == "FROZEN"

    assert (
        written["immutable_system"]["population"]
        == EXPECTED_POPULATION
    )

    assert (
        written["immutable_system"]
        ["human_review_required"]
        is True
    )

    assert (
        written["immutable_system"]
        ["autonomous_clinical_action"]
        is False
    )

    assert (
        written["change_control"]
        ["system_frozen"]
        is True
    )

    print("Final system status: FROZEN")
    print("Population lock: PASSED")
    print("Human-review lock: PASSED")
    print("No-autonomous-action lock: PASSED")
    print("Change-control lock: PASSED")
    print("Final manifest verification: PASSED")

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print(
        "PHASE 10.5.4 COMPLETE — "
        "CARECOMPUTE SYSTEM FROZEN"
    )
    print("=" * 80)

    print(
        "\nThe independently validated CareCompute "
        "human-in-the-loop Rescue Review workflow is now frozen."
    )

    print(
        "Any future upstream or workflow modification requires "
        "versioning and end-to-end revalidation."
    )


if __name__ == "__main__":
    main()
