"""
Phase 10.6.2 — Cross-Phase Consistency & Provenance Audit
CareCompute

Performs a read-only audit across Phase 10 artifacts to verify that
the final frozen system is traceable to its upstream contracts,
contexts, rules, explanations, packets, audits, and freeze manifests.

No frozen artifact is modified.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone


# =============================================================================
# PATHS
# =============================================================================

BASE = Path("results/eligible/agents")

ARCHITECTURE_PATH = BASE / "agent_architecture.json"
INPUT_CONTRACT_PATH = BASE / "agent_input_contract.json"

CONTEXT_PATH = BASE / "patient_agent_contexts.jsonl"
CONTEXT_SUMMARY_PATH = BASE / "patient_context_builder_summary.json"

RESCUE_CONTRACT_PATH = BASE / "rescue_review_agent_output_contract.json"
RESCUE_RULES_PATH = BASE / "rescue_review_agent_frozen_rules.json"
RULE_FREEZE_AUDIT_PATH = BASE / "agent_rule_freeze_audit.json"

EXPLANATION_CONTRACT_PATH = BASE / "explanation_agent_output_contract.json"
EXPLANATION_OUTPUT_PATH = BASE / "explanation_agent_outputs.jsonl"
EXPLANATION_SUMMARY_PATH = BASE / "explanation_generator_summary.json"
EXPLANATION_AUDIT_PATH = BASE / "explanation_fidelity_safety_audit.json"
EXPLANATION_FREEZE_PATH = BASE / "explanation_agent_freeze_manifest.json"

WORKFLOW_CONTRACT_PATH = BASE / "end_to_end_workflow_contract.json"
PACKET_PATH = BASE / "end_to_end_case_packets.jsonl"
REPLAY_SUMMARY_PATH = BASE / "end_to_end_replay_summary.json"
SYSTEM_AUDIT_PATH = BASE / "end_to_end_system_audit.json"
FINAL_FREEZE_PATH = BASE / "carecompute_final_system_freeze_manifest.json"

INVENTORY_PATH = BASE / "phase10_artifact_inventory.json"

OUTPUT_PATH = BASE / "phase10_cross_phase_provenance_audit.json"


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

EXPECTED_CONTEXT_SCHEMA = "10.2"
EXPECTED_RULE_VERSION = "10.3.4"
EXPECTED_EXPLANATION_CONTRACT = "10.4.1"
EXPECTED_EXPLANATION_SCHEMA = "10.4.2"
EXPECTED_WORKFLOW_CONTRACT = "10.5.1"
EXPECTED_PACKET_SCHEMA = "10.5.2"


# =============================================================================
# HELPERS
# =============================================================================

def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path):
    records = []

    with path.open("r", encoding="utf-8") as f:

        for line_number, line in enumerate(f, start=1):

            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))

            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at {path}:{line_number}"
                ) from exc

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
    print("PHASE 10.6.2 — CROSS-PHASE CONSISTENCY & PROVENANCE AUDIT")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # A — VERIFY REQUIRED PROVENANCE ARTIFACTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("A — VERIFY PROVENANCE ARTIFACTS")
    print("=" * 80)

    required = [
        ARCHITECTURE_PATH,
        INPUT_CONTRACT_PATH,
        CONTEXT_PATH,
        CONTEXT_SUMMARY_PATH,
        RESCUE_CONTRACT_PATH,
        RESCUE_RULES_PATH,
        RULE_FREEZE_AUDIT_PATH,
        EXPLANATION_CONTRACT_PATH,
        EXPLANATION_OUTPUT_PATH,
        EXPLANATION_SUMMARY_PATH,
        EXPLANATION_AUDIT_PATH,
        EXPLANATION_FREEZE_PATH,
        WORKFLOW_CONTRACT_PATH,
        PACKET_PATH,
        REPLAY_SUMMARY_PATH,
        SYSTEM_AUDIT_PATH,
        FINAL_FREEZE_PATH,
        INVENTORY_PATH,
    ]

    missing = []

    for path in required:

        if path.exists():
            print("FOUND:", path)

        else:
            print("MISSING:", path)
            missing.append(str(path))

    if missing:
        raise RuntimeError(
            f"Missing provenance artifacts: {missing}"
        )

    print("Provenance artifact presence: PASSED")

    # -------------------------------------------------------------------------
    # B — LOAD CROSS-PHASE ARTIFACTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("B — LOAD CROSS-PHASE ARTIFACTS")
    print("=" * 80)

    architecture = load_json(ARCHITECTURE_PATH)
    input_contract = load_json(INPUT_CONTRACT_PATH)

    contexts = load_jsonl(CONTEXT_PATH)
    context_summary = load_json(CONTEXT_SUMMARY_PATH)

    rescue_contract = load_json(RESCUE_CONTRACT_PATH)
    rescue_rules = load_json(RESCUE_RULES_PATH)
    rule_freeze_audit = load_json(RULE_FREEZE_AUDIT_PATH)

    explanation_contract = load_json(EXPLANATION_CONTRACT_PATH)
    explanations = load_jsonl(EXPLANATION_OUTPUT_PATH)
    explanation_summary = load_json(EXPLANATION_SUMMARY_PATH)
    explanation_audit = load_json(EXPLANATION_AUDIT_PATH)
    explanation_freeze = load_json(EXPLANATION_FREEZE_PATH)

    workflow_contract = load_json(WORKFLOW_CONTRACT_PATH)
    packets = load_jsonl(PACKET_PATH)
    replay_summary = load_json(REPLAY_SUMMARY_PATH)
    system_audit = load_json(SYSTEM_AUDIT_PATH)
    final_freeze = load_json(FINAL_FREEZE_PATH)

    inventory = load_json(INVENTORY_PATH)

    print("Contexts:", len(contexts))
    print("Explanations:", len(explanations))
    print("Final packets:", len(packets))
    print("Inventory status:", inventory["status"])
    print("Final system:", final_freeze["status"])

    # -------------------------------------------------------------------------
    # C — VERSION PROVENANCE
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("C — VERSION PROVENANCE")
    print("=" * 80)

    assert all(
        x["schema_version"] == EXPECTED_CONTEXT_SCHEMA
        for x in contexts
    )

    assert rescue_rules["rule_version"] == EXPECTED_RULE_VERSION

    assert (
        explanation_contract["contract_version"]
        == EXPECTED_EXPLANATION_CONTRACT
    )

    assert all(
        x["schema_version"] == EXPECTED_EXPLANATION_SCHEMA
        for x in explanations
    )

    assert (
        workflow_contract["contract_version"]
        == EXPECTED_WORKFLOW_CONTRACT
    )

    assert all(
        x["schema_version"] == EXPECTED_PACKET_SCHEMA
        for x in packets
    )

    assert final_freeze["phase"] == "10.5.4"

    print("Context schema 10.2: PASSED")
    print("Rule version 10.3.4: PASSED")
    print("Explanation contract 10.4.1: PASSED")
    print("Explanation schema 10.4.2: PASSED")
    print("Workflow contract 10.5.1: PASSED")
    print("Packet schema 10.5.2: PASSED")
    print("Final freeze phase 10.5.4: PASSED")

    # -------------------------------------------------------------------------
    # D — POPULATION CONSISTENCY
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("D — POPULATION CONSISTENCY")
    print("=" * 80)

    population_values = {
        "contexts":
            len(contexts),

        "explanations":
            len(explanations),

        "packets":
            len(packets),

        "frozen_rules":
            rescue_rules["expected_population"],

        "workflow_contract":
            workflow_contract[
                "input_contract"
            ]["expected_population"],

        "replay_summary":
            replay_summary["population"],

        "system_audit":
            system_audit["population"],

        "final_freeze":
            final_freeze[
                "immutable_system"
            ]["population"],
    }

    for name, value in population_values.items():
        print(f"{name}: {value}")
        assert value == EXPECTED_POPULATION

    print("Cross-phase population consistency: PASSED")

    # -------------------------------------------------------------------------
    # E — THRESHOLD & BUDGET CONSISTENCY
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("E — THRESHOLD & REVIEW-BUDGET CONSISTENCY")
    print("=" * 80)

    threshold_values = [
        rescue_rules["frozen_primary_model_threshold"],

        workflow_contract[
            "frozen_dependencies"
        ]["primary_model_threshold"],

        replay_summary["primary_threshold"],

        final_freeze[
            "immutable_system"
        ]["primary_model_threshold"],
    ]

    budget_values = [
        rescue_rules["frozen_router_review_budget"],

        workflow_contract[
            "frozen_dependencies"
        ]["rescue_review_budget"],

        replay_summary["review_budget"],

        final_freeze[
            "immutable_system"
        ]["rescue_review_budget"],
    ]

    assert all(
        value == EXPECTED_THRESHOLD
        for value in threshold_values
    )

    assert all(
        value == EXPECTED_REVIEW_BUDGET
        for value in budget_values
    )

    assert all(
        context["primary_model"]["decision_threshold"]
        == EXPECTED_THRESHOLD
        for context in contexts
    )

    assert all(
        context["router_context"]["review_budget"]
        == EXPECTED_REVIEW_BUDGET
        for context in contexts
    )

    assert all(
        packet["primary_model"]["decision_threshold"]
        == EXPECTED_THRESHOLD
        for packet in packets
    )

    assert all(
        packet["rescue_router"]["review_budget"]
        == EXPECTED_REVIEW_BUDGET
        for packet in packets
    )

    print("Primary threshold 0.115: PASSED")
    print("Review budget 0.15: PASSED")
    print("Context-level locks: PASSED")
    print("Packet-level locks: PASSED")

    # -------------------------------------------------------------------------
    # F — ENCOUNTER PROVENANCE
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("F — ENCOUNTER PROVENANCE")
    print("=" * 80)

    context_ids = {
        int(x["encounter"]["encounter_id"])
        for x in contexts
    }

    explanation_ids = {
        int(x["encounter_id"])
        for x in explanations
    }

    packet_ids = {
        int(x["encounter_id"])
        for x in packets
    }

    assert len(context_ids) == EXPECTED_POPULATION
    assert context_ids == explanation_ids == packet_ids

    print("Unique encounters:", len(context_ids))
    print("Context → explanation alignment: PASSED")
    print("Explanation → final packet alignment: PASSED")
    print("Encounter provenance: PASSED")

    # -------------------------------------------------------------------------
    # G — PRIORITY CONSISTENCY
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("G — PRIORITY CONSISTENCY")
    print("=" * 80)

    explanation_distribution = Counter(
        x["review_priority"]
        for x in explanations
    )

    packet_distribution = Counter(
        x["rescue_review"]["review_priority"]
        for x in packets
    )

    explanation_distribution = {
        "LOW": explanation_distribution["LOW"],
        "MODERATE": explanation_distribution["MODERATE"],
        "HIGH": explanation_distribution["HIGH"],
    }

    packet_distribution = {
        "LOW": packet_distribution["LOW"],
        "MODERATE": packet_distribution["MODERATE"],
        "HIGH": packet_distribution["HIGH"],
    }

    assert (
        explanation_distribution
        == EXPECTED_PRIORITY_DISTRIBUTION
    )

    assert (
        packet_distribution
        == EXPECTED_PRIORITY_DISTRIBUTION
    )

    assert (
        replay_summary["priority_distribution"]
        == EXPECTED_PRIORITY_DISTRIBUTION
    )

    assert (
        system_audit["priority_distribution"]
        == EXPECTED_PRIORITY_DISTRIBUTION
    )

    assert (
        final_freeze[
            "immutable_system"
        ]["priority_distribution"]
        == EXPECTED_PRIORITY_DISTRIBUTION
    )

    print(
        "Priority distribution:",
        EXPECTED_PRIORITY_DISTRIBUTION
    )

    print("Explanation priorities: PASSED")
    print("Packet priorities: PASSED")
    print("Replay summary priorities: PASSED")
    print("Audit priorities: PASSED")
    print("Freeze priorities: PASSED")

    # -------------------------------------------------------------------------
    # H — SAFETY PROVENANCE
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("H — SAFETY PROVENANCE")
    print("=" * 80)

    assert (
        workflow_contract[
            "safety_constraints"
        ]["ground_truth_available_to_agents"]
        is False
    )

    assert (
        workflow_contract[
            "safety_constraints"
        ]["may_take_autonomous_clinical_action"]
        is False
    )

    assert (
        workflow_contract[
            "safety_constraints"
        ]["human_review_required"]
        is True
    )

    assert system_audit["ground_truth_used_by_workflow"] is False

    assert system_audit["autonomous_clinical_action"] is False

    assert system_audit["human_review_required"] is True

    assert (
        final_freeze[
            "immutable_system"
        ]["ground_truth_available_to_agents"]
        is False
    )

    assert (
        final_freeze[
            "immutable_system"
        ]["autonomous_clinical_action"]
        is False
    )

    assert (
        final_freeze[
            "immutable_system"
        ]["human_review_required"]
        is True
    )

    assert all(
        packet["workflow_disposition"]
        == "HUMAN_REVIEW_REQUIRED"
        for packet in packets
    )

    assert all(
        packet["autonomous_clinical_action"]
        is False
        for packet in packets
    )

    print("Ground-truth exclusion: PASSED")
    print("No autonomous clinical action: PASSED")
    print("Mandatory human review: PASSED")
    print("Packet-level safety propagation: PASSED")

    # -------------------------------------------------------------------------
    # I — AUDIT CHAIN
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("I — AUDIT CHAIN")
    print("=" * 80)

    assert explanation_audit["status"] == "PASSED"
    assert explanation_freeze["status"] == "FROZEN"

    assert system_audit["status"] == "PASSED"
    assert final_freeze["status"] == "FROZEN"

    assert (
        inventory["frozen_hash_verification"]
        == "PASSED"
    )

    nonzero_system_violations = {
        key: value
        for key, value in system_audit[
            "violations"
        ].items()
        if value != 0
    }

    assert not nonzero_system_violations

    print("Explanation independent audit: PASSED")
    print("Explanation freeze: FROZEN")
    print("End-to-end independent audit: PASSED")
    print("Final system freeze: FROZEN")
    print("Artifact inventory integrity: PASSED")
    print("Zero end-to-end violations: PASSED")

    # -------------------------------------------------------------------------
    # J — FINAL FREEZE HASH INTEGRITY
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("J — FINAL FREEZE HASH INTEGRITY")
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

            continue

        current_hash = sha256_file(path)

        if current_hash != expected_hash:

            hash_errors.append(
                f"{filename}: hash mismatch"
            )

        else:
            print(filename, ": PASSED")

    assert not hash_errors, hash_errors

    print("Final frozen hash chain: PASSED")

    # -------------------------------------------------------------------------
    # K — PROVENANCE CHAIN
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("K — DEFINE PROVENANCE CHAIN")
    print("=" * 80)

    provenance_chain = [
        {
            "phase": "10.1",
            "artifact": str(ARCHITECTURE_PATH),
            "role": "Agent architecture",
        },
        {
            "phase": "10.2",
            "artifact": str(CONTEXT_PATH),
            "role": "Frozen patient contexts",
        },
        {
            "phase": "10.3.1",
            "artifact": str(RESCUE_CONTRACT_PATH),
            "role": "Rescue Review output contract",
        },
        {
            "phase": "10.3.4",
            "artifact": str(RESCUE_RULES_PATH),
            "role": "Frozen deterministic review rules",
        },
        {
            "phase": "10.4.1",
            "artifact": str(EXPLANATION_CONTRACT_PATH),
            "role": "Explanation output contract",
        },
        {
            "phase": "10.4.2",
            "artifact": str(EXPLANATION_OUTPUT_PATH),
            "role": "Deterministic explanations",
        },
        {
            "phase": "10.4.3",
            "artifact": str(EXPLANATION_AUDIT_PATH),
            "role": "Independent explanation audit",
        },
        {
            "phase": "10.4.4",
            "artifact": str(EXPLANATION_FREEZE_PATH),
            "role": "Explanation subsystem freeze",
        },
        {
            "phase": "10.5.1",
            "artifact": str(WORKFLOW_CONTRACT_PATH),
            "role": "End-to-end workflow contract",
        },
        {
            "phase": "10.5.2",
            "artifact": str(PACKET_PATH),
            "role": "Final human-review packets",
        },
        {
            "phase": "10.5.3",
            "artifact": str(SYSTEM_AUDIT_PATH),
            "role": "Independent end-to-end audit",
        },
        {
            "phase": "10.5.4",
            "artifact": str(FINAL_FREEZE_PATH),
            "role": "Final system freeze",
        },
        {
            "phase": "10.6.1",
            "artifact": str(INVENTORY_PATH),
            "role": "Phase 10 artifact inventory",
        },
    ]

    for step in provenance_chain:
        print(
            f"{step['phase']} -> "
            f"{step['role']}"
        )

    print("Provenance chain: DEFINED")

    # -------------------------------------------------------------------------
    # L — SAVE AUDIT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("L — SAVE CROSS-PHASE AUDIT")
    print("=" * 80)

    audit = {
        "phase": "10.6.2",

        "name":
            "Cross-Phase Consistency and Provenance Audit",

        "status":
            "PASSED",

        "generated_utc":
            datetime.now(timezone.utc).isoformat(),

        "population":
            EXPECTED_POPULATION,

        "primary_model_threshold":
            EXPECTED_THRESHOLD,

        "rescue_review_budget":
            EXPECTED_REVIEW_BUDGET,

        "priority_distribution":
            EXPECTED_PRIORITY_DISTRIBUTION,

        "versions": {
            "context_schema":
                EXPECTED_CONTEXT_SCHEMA,

            "rescue_rule_version":
                EXPECTED_RULE_VERSION,

            "explanation_contract":
                EXPECTED_EXPLANATION_CONTRACT,

            "explanation_schema":
                EXPECTED_EXPLANATION_SCHEMA,

            "workflow_contract":
                EXPECTED_WORKFLOW_CONTRACT,

            "packet_schema":
                EXPECTED_PACKET_SCHEMA,
        },

        "checks": {
            "artifact_presence":
                True,

            "version_consistency":
                True,

            "population_consistency":
                True,

            "threshold_consistency":
                True,

            "review_budget_consistency":
                True,

            "encounter_provenance":
                True,

            "priority_consistency":
                True,

            "safety_provenance":
                True,

            "audit_chain":
                True,

            "final_freeze_hash_integrity":
                True,
        },

        "provenance_chain":
            provenance_chain,

        "final_system_status":
            "FROZEN",

        "modifies_frozen_artifacts":
            False,
    }

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            audit,
            f,
            indent=2,
            sort_keys=True
        )

    print("Audit:", OUTPUT_PATH)

    # -------------------------------------------------------------------------
    # M — VERIFY SAVED AUDIT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("M — VERIFY SAVED AUDIT")
    print("=" * 80)

    written = load_json(OUTPUT_PATH)

    assert written["phase"] == "10.6.2"
    assert written["status"] == "PASSED"

    assert all(
        written["checks"].values()
    )

    assert (
        written["final_system_status"]
        == "FROZEN"
    )

    assert (
        written["modifies_frozen_artifacts"]
        is False
    )

    print("Cross-phase checks: PASSED")
    print("Provenance chain: PASSED")
    print("Final system remains FROZEN: PASSED")
    print("Read-only requirement: PASSED")

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print(
        "PHASE 10.6.2 COMPLETE — "
        "CROSS-PHASE PROVENANCE PASSED"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
