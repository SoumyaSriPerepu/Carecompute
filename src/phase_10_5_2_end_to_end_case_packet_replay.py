"""
Phase 10.5.2 — End-to-End Case Packet Assembly & Replay

CareCompute

Assembles final human-review packets from already-frozen upstream artifacts.

No model inference, router inference, thresholding, priority generation,
or explanation generation occurs in this phase.
"""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


# =============================================================================
# PATHS
# =============================================================================

BASE = Path("results/eligible/agents")

CONTEXT_PATH = BASE / "patient_agent_contexts.jsonl"
EXPLANATION_PATH = BASE / "explanation_agent_outputs.jsonl"
EXPLANATION_FREEZE_PATH = BASE / "explanation_agent_freeze_manifest.json"
WORKFLOW_CONTRACT_PATH = BASE / "end_to_end_workflow_contract.json"

OUTPUT_JSONL_PATH = BASE / "end_to_end_case_packets.jsonl"
OUTPUT_CSV_PATH = BASE / "end_to_end_case_packets.csv"
SUMMARY_PATH = BASE / "end_to_end_replay_summary.json"


# =============================================================================
# EXPECTATIONS
# =============================================================================

EXPECTED_POPULATION = 1178
EXPECTED_CONTEXT_SCHEMA = "10.2"
EXPECTED_EXPLANATION_SCHEMA = "10.4.2"
EXPECTED_WORKFLOW_CONTRACT = "10.5.1"

PACKET_SCHEMA_VERSION = "10.5.2"

EXPECTED_THRESHOLD = 0.115
EXPECTED_BUDGET = 0.15

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


def recursive_keys(obj):
    """
    Return all dictionary keys occurring anywhere in an object.
    """

    keys = set()

    if isinstance(obj, dict):

        for key, value in obj.items():

            keys.add(key)
            keys.update(recursive_keys(value))

    elif isinstance(obj, list):

        for value in obj:
            keys.update(recursive_keys(value))

    return keys


# =============================================================================
# PACKET ASSEMBLY
# =============================================================================

def build_packet(context, explanation):

    encounter_id = int(
        context["encounter"]["encounter_id"]
    )

    if encounter_id != int(explanation["encounter_id"]):
        raise ValueError(
            f"Encounter mismatch: {encounter_id}"
        )

    packet = {
        "schema_version":
            PACKET_SCHEMA_VERSION,

        "encounter_id":
            encounter_id,

        "primary_model": {
            "predicted_30d":
                int(
                    context["primary_model"]
                    ["predicted_30d"]
                ),

            "calibrated_probability":
                float(
                    context["primary_model"]
                    ["calibrated_probability"]
                ),

            "decision_threshold":
                float(
                    context["primary_model"]
                    ["decision_threshold"]
                ),
        },

        "rescue_router": {
            "fn_router_probability":
                float(
                    context["router_context"]
                    ["fn_router_probability"]
                ),

            "selected_for_review":
                int(
                    context["router_context"]
                    ["selected_for_review"]
                ),

            "review_budget":
                float(
                    context["router_context"]
                    ["review_budget"]
                ),
        },

        "rescue_review": {
            "review_priority":
                explanation["review_priority"]
        },

        "explanation": {
            "explanation":
                explanation["explanation"],

            "signal_explanations":
                explanation["signal_explanations"],

            "uncertainty_statement":
                explanation["uncertainty_statement"],

            "human_review_statement":
                explanation["human_review_statement"],
        },

        "workflow_disposition":
            "HUMAN_REVIEW_REQUIRED",

        "autonomous_clinical_action":
            False,

        "safety_flag":
            bool(explanation["safety_flag"]),
    }

    return packet


# =============================================================================
# PACKET VALIDATION
# =============================================================================

def validate_packet(
    packet,
    context,
    explanation,
    workflow_contract
):

    required_fields = set(
        workflow_contract[
            "final_packet_contract"
        ]["required_fields"].keys()
    )

    if set(packet.keys()) != required_fields:
        raise ValueError(
            f"Top-level packet contract mismatch for "
            f"encounter {packet['encounter_id']}"
        )

    if packet["schema_version"] != PACKET_SCHEMA_VERSION:
        raise ValueError("Incorrect packet schema.")

    if packet["encounter_id"] != int(
        context["encounter"]["encounter_id"]
    ):
        raise ValueError("Encounter ID changed.")

    # -------------------------------------------------------------------------
    # Primary model preservation
    # -------------------------------------------------------------------------

    if (
        packet["primary_model"]["predicted_30d"]
        != context["primary_model"]["predicted_30d"]
    ):
        raise ValueError("Primary prediction changed.")

    if (
        packet["primary_model"]["calibrated_probability"]
        != context["primary_model"]["calibrated_probability"]
    ):
        raise ValueError("Primary probability changed.")

    if (
        packet["primary_model"]["decision_threshold"]
        != EXPECTED_THRESHOLD
    ):
        raise ValueError("Primary threshold changed.")

    # -------------------------------------------------------------------------
    # Router preservation
    # -------------------------------------------------------------------------

    if (
        packet["rescue_router"]["fn_router_probability"]
        != context["router_context"]["fn_router_probability"]
    ):
        raise ValueError("Router probability changed.")

    if (
        packet["rescue_router"]["selected_for_review"]
        != 1
    ):
        raise ValueError(
            "Packet contains non-selected case."
        )

    if (
        packet["rescue_router"]["review_budget"]
        != EXPECTED_BUDGET
    ):
        raise ValueError("Review budget changed.")

    # -------------------------------------------------------------------------
    # Review priority preservation
    # -------------------------------------------------------------------------

    if (
        packet["rescue_review"]["review_priority"]
        != explanation["review_priority"]
    ):
        raise ValueError("Review priority changed.")

    # -------------------------------------------------------------------------
    # Explanation preservation
    # -------------------------------------------------------------------------

    if (
        packet["explanation"]["explanation"]
        != explanation["explanation"]
    ):
        raise ValueError("Explanation changed.")

    if (
        packet["explanation"]["signal_explanations"]
        != explanation["signal_explanations"]
    ):
        raise ValueError(
            "Signal explanations changed."
        )

    if (
        packet["explanation"]["uncertainty_statement"]
        != explanation["uncertainty_statement"]
    ):
        raise ValueError(
            "Uncertainty statement changed."
        )

    if (
        packet["explanation"]["human_review_statement"]
        != explanation["human_review_statement"]
    ):
        raise ValueError(
            "Human-review statement changed."
        )

    # -------------------------------------------------------------------------
    # Safety
    # -------------------------------------------------------------------------

    if (
        packet["workflow_disposition"]
        != "HUMAN_REVIEW_REQUIRED"
    ):
        raise ValueError(
            "Human-review disposition missing."
        )

    if packet["autonomous_clinical_action"] is not False:
        raise ValueError(
            "Autonomous clinical action must be False."
        )

    if packet["safety_flag"] is not False:
        raise ValueError(
            "Unexpected safety flag."
        )

    prohibited = set(
        workflow_contract[
            "prohibited_final_packet_fields"
        ]
    )

    found_prohibited = (
        recursive_keys(packet) & prohibited
    )

    if found_prohibited:
        raise ValueError(
            f"Prohibited fields found: "
            f"{sorted(found_prohibited)}"
        )


# =============================================================================
# SAVE
# =============================================================================

def save_jsonl(packets):

    with OUTPUT_JSONL_PATH.open(
        "w",
        encoding="utf-8"
    ) as f:

        for packet in packets:

            f.write(
                json.dumps(
                    packet,
                    ensure_ascii=False,
                    sort_keys=True
                )
                + "\n"
            )


def save_csv(packets):

    fieldnames = [
        "schema_version",
        "encounter_id",
        "predicted_30d",
        "calibrated_probability",
        "decision_threshold",
        "fn_router_probability",
        "selected_for_review",
        "review_budget",
        "review_priority",
        "explanation",
        "signal_explanations",
        "uncertainty_statement",
        "human_review_statement",
        "workflow_disposition",
        "autonomous_clinical_action",
        "safety_flag",
    ]

    with OUTPUT_CSV_PATH.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for packet in packets:

            row = {
                "schema_version":
                    packet["schema_version"],

                "encounter_id":
                    packet["encounter_id"],

                "predicted_30d":
                    packet["primary_model"]
                    ["predicted_30d"],

                "calibrated_probability":
                    packet["primary_model"]
                    ["calibrated_probability"],

                "decision_threshold":
                    packet["primary_model"]
                    ["decision_threshold"],

                "fn_router_probability":
                    packet["rescue_router"]
                    ["fn_router_probability"],

                "selected_for_review":
                    packet["rescue_router"]
                    ["selected_for_review"],

                "review_budget":
                    packet["rescue_router"]
                    ["review_budget"],

                "review_priority":
                    packet["rescue_review"]
                    ["review_priority"],

                "explanation":
                    packet["explanation"]
                    ["explanation"],

                "signal_explanations":
                    json.dumps(
                        packet["explanation"]
                        ["signal_explanations"],
                        ensure_ascii=False,
                        sort_keys=True
                    ),

                "uncertainty_statement":
                    packet["explanation"]
                    ["uncertainty_statement"],

                "human_review_statement":
                    packet["explanation"]
                    ["human_review_statement"],

                "workflow_disposition":
                    packet["workflow_disposition"],

                "autonomous_clinical_action":
                    packet["autonomous_clinical_action"],

                "safety_flag":
                    packet["safety_flag"],
            }

            writer.writerow(row)


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 80)
    print(
        "PHASE 10.5.2 — END-TO-END CASE PACKET "
        "ASSEMBLY & REPLAY"
    )
    print("=" * 80)

    # -------------------------------------------------------------------------
    # A — LOAD FROZEN INPUTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("A — LOAD FROZEN WORKFLOW INPUTS")
    print("=" * 80)

    contexts = load_jsonl(CONTEXT_PATH)
    explanations = load_jsonl(EXPLANATION_PATH)
    explanation_freeze = load_json(
        EXPLANATION_FREEZE_PATH
    )
    workflow_contract = load_json(
        WORKFLOW_CONTRACT_PATH
    )

    print("Contexts:", len(contexts))
    print("Explanations:", len(explanations))
    print(
        "Explanation subsystem:",
        explanation_freeze["status"]
    )
    print(
        "Workflow contract:",
        workflow_contract["contract_version"]
    )

    assert len(contexts) == EXPECTED_POPULATION
    assert len(explanations) == EXPECTED_POPULATION

    assert (
        workflow_contract["contract_version"]
        == EXPECTED_WORKFLOW_CONTRACT
    )

    print("Input loading: PASSED")

    # -------------------------------------------------------------------------
    # B — VERIFY FROZEN INPUT INTEGRITY
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("B — VERIFY FROZEN INPUT INTEGRITY")
    print("=" * 80)

    frozen_hashes = explanation_freeze[
        "artifact_sha256"
    ]

    current_context_hash = sha256_file(
        CONTEXT_PATH
    )

    current_explanation_hash = sha256_file(
        EXPLANATION_PATH
    )

    assert (
        current_context_hash
        == frozen_hashes[
            "patient_agent_contexts.jsonl"
        ]
    )

    assert (
        current_explanation_hash
        == frozen_hashes[
            "explanation_agent_outputs.jsonl"
        ]
    )

    print("Context integrity: PASSED")
    print("Explanation integrity: PASSED")

    # -------------------------------------------------------------------------
    # C — ALIGN ENCOUNTERS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("C — ALIGN FROZEN ENCOUNTERS")
    print("=" * 80)

    context_map = {
        int(x["encounter"]["encounter_id"]): x
        for x in contexts
    }

    explanation_map = {
        int(x["encounter_id"]): x
        for x in explanations
    }

    assert len(context_map) == EXPECTED_POPULATION
    assert len(explanation_map) == EXPECTED_POPULATION
    assert set(context_map) == set(explanation_map)

    print("Unique contexts:", len(context_map))
    print("Unique explanations:", len(explanation_map))
    print("Encounter alignment: PASSED")

    # -------------------------------------------------------------------------
    # D — ASSEMBLE FINAL PACKETS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("D — ASSEMBLE FINAL HUMAN-REVIEW PACKETS")
    print("=" * 80)

    packets = []

    for context in contexts:

        encounter_id = int(
            context["encounter"]["encounter_id"]
        )

        explanation = explanation_map[
            encounter_id
        ]

        packet = build_packet(
            context,
            explanation
        )

        validate_packet(
            packet,
            context,
            explanation,
            workflow_contract
        )

        packets.append(packet)

    print("Packets assembled:", len(packets))
    print("Packet validation: PASSED")

    # -------------------------------------------------------------------------
    # E — VERIFY POPULATION-LEVEL RESULTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("E — VERIFY POPULATION-LEVEL REPLAY")
    print("=" * 80)

    priorities = Counter(
        packet["rescue_review"]["review_priority"]
        for packet in packets
    )

    priority_distribution = {
        "LOW": priorities["LOW"],
        "MODERATE": priorities["MODERATE"],
        "HIGH": priorities["HIGH"],
    }

    print(
        "Priority distribution:",
        priority_distribution
    )

    assert (
        priority_distribution
        == EXPECTED_PRIORITY_DISTRIBUTION
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

    assert all(
        packet["safety_flag"] is False
        for packet in packets
    )

    print("Priority preservation: PASSED")
    print("Human-review disposition: 1178 / 1178")
    print("Autonomous clinical actions: 0")
    print("Safety flags: 0")
    print("Population-level replay: PASSED")

    # -------------------------------------------------------------------------
    # F — DETERMINISTIC REPLAY TEST
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("F — DETERMINISTIC REPLAY TEST")
    print("=" * 80)

    second_pass = []

    for context in contexts:

        encounter_id = int(
            context["encounter"]["encounter_id"]
        )

        second_pass.append(
            build_packet(
                context,
                explanation_map[encounter_id]
            )
        )

    first_serialized = json.dumps(
        packets,
        ensure_ascii=False,
        sort_keys=True
    )

    second_serialized = json.dumps(
        second_pass,
        ensure_ascii=False,
        sort_keys=True
    )

    assert first_serialized == second_serialized

    print("Repeated packet assembly identical: PASSED")

    # -------------------------------------------------------------------------
    # G — SAVE PACKETS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("G — SAVE FINAL CASE PACKETS")
    print("=" * 80)

    save_jsonl(packets)
    save_csv(packets)

    print("JSONL:", OUTPUT_JSONL_PATH)
    print("CSV:  ", OUTPUT_CSV_PATH)

    # -------------------------------------------------------------------------
    # H — SAVE REPLAY SUMMARY
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("H — SAVE REPLAY SUMMARY")
    print("=" * 80)

    summary = {
        "phase": "10.5.2",
        "status": "COMPLETED",

        "packet_schema":
            PACKET_SCHEMA_VERSION,

        "population":
            len(packets),

        "assembly_type":
            "frozen_artifact_replay",

        "new_model_inference":
            False,

        "new_router_inference":
            False,

        "priority_recalculated":
            False,

        "explanation_regenerated":
            False,

        "primary_threshold":
            EXPECTED_THRESHOLD,

        "review_budget":
            EXPECTED_BUDGET,

        "priority_distribution":
            priority_distribution,

        "human_review_required_count":
            sum(
                packet["workflow_disposition"]
                == "HUMAN_REVIEW_REQUIRED"
                for packet in packets
            ),

        "autonomous_clinical_action_count":
            sum(
                packet["autonomous_clinical_action"]
                is True
                for packet in packets
            ),

        "safety_flag_count":
            sum(
                packet["safety_flag"] is True
                for packet in packets
            ),

        "deterministic_replay_passed":
            True,

        "source_sha256": {
            "patient_agent_contexts.jsonl":
                sha256_file(CONTEXT_PATH),

            "explanation_agent_outputs.jsonl":
                sha256_file(EXPLANATION_PATH),

            "end_to_end_workflow_contract.json":
                sha256_file(WORKFLOW_CONTRACT_PATH),
        },
    }

    with SUMMARY_PATH.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            summary,
            f,
            indent=2,
            sort_keys=True
        )

    print("Summary:", SUMMARY_PATH)

    # -------------------------------------------------------------------------
    # I — SAMPLE FINAL PACKET
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("I — SAMPLE FINAL HUMAN-REVIEW PACKET")
    print("=" * 80)

    print(
        json.dumps(
            packets[0],
            indent=2,
            ensure_ascii=False
        )
    )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print(
        "PHASE 10.5.2 COMPLETE — "
        "END-TO-END REPLAY PASSED"
    )
    print("=" * 80)

    print(
        "\nAll 1,178 frozen Rescue Review cases were assembled "
        "into final human-review packets without changing upstream "
        "predictions, probabilities, routing decisions, priorities, "
        "explanations, threshold, or review budget."
    )


if __name__ == "__main__":
    main()
