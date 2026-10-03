"""
Phase 10.5.3 — Independent End-to-End System Audit

CareCompute

Independently validates final Phase 10.5.2 human-review packets against
the frozen source artifacts and Phase 10.5.1 workflow contract.

This audit does NOT regenerate packets or modify any frozen artifact.
"""

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
PACKET_PATH = BASE / "end_to_end_case_packets.jsonl"
REPLAY_SUMMARY_PATH = BASE / "end_to_end_replay_summary.json"

AUDIT_PATH = BASE / "end_to_end_system_audit.json"


# =============================================================================
# EXPECTATIONS
# =============================================================================

EXPECTED_POPULATION = 1178

EXPECTED_THRESHOLD = 0.115
EXPECTED_BUDGET = 0.15

EXPECTED_PACKET_SCHEMA = "10.5.2"
EXPECTED_CONTRACT_VERSION = "10.5.1"

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
    keys = set()

    if isinstance(obj, dict):

        for key, value in obj.items():

            keys.add(key)
            keys.update(recursive_keys(value))

    elif isinstance(obj, list):

        for value in obj:
            keys.update(recursive_keys(value))

    return keys


def collect_text(obj):
    pieces = []

    if isinstance(obj, dict):

        for value in obj.values():
            pieces.append(collect_text(value))

    elif isinstance(obj, list):

        for value in obj:
            pieces.append(collect_text(value))

    elif isinstance(obj, str):
        pieces.append(obj)

    return " ".join(
        piece for piece in pieces if piece
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 80)
    print("PHASE 10.5.3 — INDEPENDENT END-TO-END SYSTEM AUDIT")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # A — LOAD ARTIFACTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("A — LOAD END-TO-END ARTIFACTS")
    print("=" * 80)

    contexts = load_jsonl(CONTEXT_PATH)
    explanations = load_jsonl(EXPLANATION_PATH)
    packets = load_jsonl(PACKET_PATH)

    contract = load_json(WORKFLOW_CONTRACT_PATH)
    replay_summary = load_json(REPLAY_SUMMARY_PATH)
    explanation_freeze = load_json(
        EXPLANATION_FREEZE_PATH
    )

    print("Contexts:", len(contexts))
    print("Explanations:", len(explanations))
    print("Final packets:", len(packets))
    print(
        "Workflow contract:",
        contract["contract_version"]
    )
    print(
        "Explanation subsystem:",
        explanation_freeze["status"]
    )

    assert len(contexts) == EXPECTED_POPULATION
    assert len(explanations) == EXPECTED_POPULATION
    assert len(packets) == EXPECTED_POPULATION

    assert (
        contract["contract_version"]
        == EXPECTED_CONTRACT_VERSION
    )

    assert explanation_freeze["status"] == "FROZEN"

    print("Artifact loading: PASSED")

    # -------------------------------------------------------------------------
    # B — ENCOUNTER ALIGNMENT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("B — ENCOUNTER ALIGNMENT")
    print("=" * 80)

    context_map = {
        int(x["encounter"]["encounter_id"]): x
        for x in contexts
    }

    explanation_map = {
        int(x["encounter_id"]): x
        for x in explanations
    }

    packet_map = {
        int(x["encounter_id"]): x
        for x in packets
    }

    assert len(context_map) == EXPECTED_POPULATION
    assert len(explanation_map) == EXPECTED_POPULATION
    assert len(packet_map) == EXPECTED_POPULATION

    assert (
        set(context_map)
        == set(explanation_map)
        == set(packet_map)
    )

    print("Unique contexts:", len(context_map))
    print("Unique explanations:", len(explanation_map))
    print("Unique packets:", len(packet_map))
    print("Encounter sets identical: PASSED")

    # -------------------------------------------------------------------------
    # C — PRIMARY MODEL PRESERVATION
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("C — PRIMARY MODEL PRESERVATION")
    print("=" * 80)

    prediction_mismatches = []
    probability_mismatches = []
    threshold_mismatches = []

    for encounter_id, packet in packet_map.items():

        context = context_map[encounter_id]

        if (
            packet["primary_model"]["predicted_30d"]
            != context["primary_model"]["predicted_30d"]
        ):
            prediction_mismatches.append(encounter_id)

        if (
            packet["primary_model"]["calibrated_probability"]
            != context["primary_model"]["calibrated_probability"]
        ):
            probability_mismatches.append(encounter_id)

        if (
            packet["primary_model"]["decision_threshold"]
            != EXPECTED_THRESHOLD
        ):
            threshold_mismatches.append(encounter_id)

    print(
        "Prediction mismatches:",
        len(prediction_mismatches)
    )

    print(
        "Probability mismatches:",
        len(probability_mismatches)
    )

    print(
        "Threshold mismatches:",
        len(threshold_mismatches)
    )

    assert not prediction_mismatches
    assert not probability_mismatches
    assert not threshold_mismatches

    print("Primary model preservation: PASSED")

    # -------------------------------------------------------------------------
    # D — ROUTER PRESERVATION
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("D — RESCUE ROUTER PRESERVATION")
    print("=" * 80)

    router_probability_mismatches = []
    router_selection_mismatches = []
    budget_mismatches = []

    for encounter_id, packet in packet_map.items():

        context = context_map[encounter_id]

        if (
            packet["rescue_router"]["fn_router_probability"]
            != context["router_context"]["fn_router_probability"]
        ):
            router_probability_mismatches.append(
                encounter_id
            )

        if (
            packet["rescue_router"]["selected_for_review"]
            != context["router_context"]["selected_for_review"]
        ):
            router_selection_mismatches.append(
                encounter_id
            )

        if (
            packet["rescue_router"]["review_budget"]
            != EXPECTED_BUDGET
        ):
            budget_mismatches.append(encounter_id)

    print(
        "Router probability mismatches:",
        len(router_probability_mismatches)
    )

    print(
        "Router selection mismatches:",
        len(router_selection_mismatches)
    )

    print(
        "Review-budget mismatches:",
        len(budget_mismatches)
    )

    assert not router_probability_mismatches
    assert not router_selection_mismatches
    assert not budget_mismatches

    print("Rescue Router preservation: PASSED")

    # -------------------------------------------------------------------------
    # E — REVIEW PRIORITY PRESERVATION
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("E — REVIEW PRIORITY PRESERVATION")
    print("=" * 80)

    priority_mismatches = []

    for encounter_id, packet in packet_map.items():

        explanation = explanation_map[encounter_id]

        if (
            packet["rescue_review"]["review_priority"]
            != explanation["review_priority"]
        ):
            priority_mismatches.append(encounter_id)

    distribution_counter = Counter(
        packet["rescue_review"]["review_priority"]
        for packet in packets
    )

    distribution = {
        "LOW": distribution_counter["LOW"],
        "MODERATE": distribution_counter["MODERATE"],
        "HIGH": distribution_counter["HIGH"],
    }

    print("Priority mismatches:", len(priority_mismatches))
    print("Priority distribution:", distribution)

    assert not priority_mismatches
    assert distribution == EXPECTED_PRIORITY_DISTRIBUTION

    print("Review priority preservation: PASSED")

    # -------------------------------------------------------------------------
    # F — EXPLANATION PRESERVATION
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("F — EXPLANATION PRESERVATION")
    print("=" * 80)

    explanation_mismatches = []
    signal_mismatches = []
    uncertainty_mismatches = []
    human_review_text_mismatches = []

    for encounter_id, packet in packet_map.items():

        source = explanation_map[encounter_id]
        final = packet["explanation"]

        if (
            final["explanation"]
            != source["explanation"]
        ):
            explanation_mismatches.append(encounter_id)

        if (
            final["signal_explanations"]
            != source["signal_explanations"]
        ):
            signal_mismatches.append(encounter_id)

        if (
            final["uncertainty_statement"]
            != source["uncertainty_statement"]
        ):
            uncertainty_mismatches.append(encounter_id)

        if (
            final["human_review_statement"]
            != source["human_review_statement"]
        ):
            human_review_text_mismatches.append(
                encounter_id
            )

    print(
        "Explanation mismatches:",
        len(explanation_mismatches)
    )

    print(
        "Signal-explanation mismatches:",
        len(signal_mismatches)
    )

    print(
        "Uncertainty mismatches:",
        len(uncertainty_mismatches)
    )

    print(
        "Human-review text mismatches:",
        len(human_review_text_mismatches)
    )

    assert not explanation_mismatches
    assert not signal_mismatches
    assert not uncertainty_mismatches
    assert not human_review_text_mismatches

    print("Explanation preservation: PASSED")

    # -------------------------------------------------------------------------
    # G — FINAL CONTRACT STRUCTURE
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("G — FINAL PACKET CONTRACT AUDIT")
    print("=" * 80)

    required_fields = set(
        contract[
            "final_packet_contract"
        ]["required_fields"].keys()
    )

    field_errors = []
    schema_errors = []

    for encounter_id, packet in packet_map.items():

        if set(packet.keys()) != required_fields:
            field_errors.append(encounter_id)

        if (
            packet["schema_version"]
            != EXPECTED_PACKET_SCHEMA
        ):
            schema_errors.append(encounter_id)

    print(
        "Top-level field errors:",
        len(field_errors)
    )

    print(
        "Packet schema errors:",
        len(schema_errors)
    )

    assert not field_errors
    assert not schema_errors

    print("Final packet contract: PASSED")

    # -------------------------------------------------------------------------
    # H — PROHIBITED FIELD AUDIT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("H — PROHIBITED FIELD AUDIT")
    print("=" * 80)

    prohibited = set(
        contract["prohibited_final_packet_fields"]
    )

    prohibited_findings = []

    for encounter_id, packet in packet_map.items():

        found = recursive_keys(packet) & prohibited

        if found:
            prohibited_findings.append({
                "encounter_id": encounter_id,
                "fields": sorted(found),
            })

    print(
        "Packets containing prohibited fields:",
        len(prohibited_findings)
    )

    assert not prohibited_findings

    print("Prohibited-field exclusion: PASSED")

    # -------------------------------------------------------------------------
    # I — HUMAN-IN-THE-LOOP SAFETY
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("I — HUMAN-IN-THE-LOOP SAFETY")
    print("=" * 80)

    disposition_errors = []
    autonomous_action_errors = []
    safety_flag_errors = []
    human_language_errors = []

    for encounter_id, packet in packet_map.items():

        if (
            packet["workflow_disposition"]
            != "HUMAN_REVIEW_REQUIRED"
        ):
            disposition_errors.append(encounter_id)

        if (
            packet["autonomous_clinical_action"]
            is not False
        ):
            autonomous_action_errors.append(
                encounter_id
            )

        if packet["safety_flag"] is not False:
            safety_flag_errors.append(encounter_id)

        human_text = (
            packet["explanation"]
            ["human_review_statement"]
            .lower()
        )

        if "human review" not in human_text:
            human_language_errors.append(
                encounter_id
            )

    print(
        "Disposition errors:",
        len(disposition_errors)
    )

    print(
        "Autonomous-action errors:",
        len(autonomous_action_errors)
    )

    print(
        "Safety-flag errors:",
        len(safety_flag_errors)
    )

    print(
        "Missing human-review language:",
        len(human_language_errors)
    )

    assert not disposition_errors
    assert not autonomous_action_errors
    assert not safety_flag_errors
    assert not human_language_errors

    print("Human-in-the-loop safety: PASSED")

    # -------------------------------------------------------------------------
    # J — DEMOGRAPHIC / GROUND-TRUTH LEAKAGE AUDIT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("J — LEAKAGE AUDIT")
    print("=" * 80)

    leakage_terms = [
        "actual_30d",
        "router_target",
        "case_type",
        "patient_nbr",
    ]

    demographic_terms = [
        "female",
        "male",
        "gender",
        "race",
        "caucasian",
        "africanamerican",
        "asian",
        "hispanic",
        "age_group",
    ]

    leakage_findings = []
    demographic_findings = []

    for encounter_id, packet in packet_map.items():

        text = collect_text(packet).lower()

        found_leakage = [
            term
            for term in leakage_terms
            if term in text
        ]

        found_demographic = [
            term
            for term in demographic_terms
            if term in text
        ]

        if found_leakage:
            leakage_findings.append({
                "encounter_id": encounter_id,
                "terms": found_leakage,
            })

        if found_demographic:
            demographic_findings.append({
                "encounter_id": encounter_id,
                "terms": found_demographic,
            })

    print(
        "Ground-truth/target leakage findings:",
        len(leakage_findings)
    )

    print(
        "Demographic explanation findings:",
        len(demographic_findings)
    )

    assert not leakage_findings
    assert not demographic_findings

    print("Leakage exclusion: PASSED")
    print("Demographic causal-language exclusion: PASSED")

    # -------------------------------------------------------------------------
    # K — REPLAY SUMMARY CONSISTENCY
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("K — REPLAY SUMMARY CONSISTENCY")
    print("=" * 80)

    assert replay_summary["population"] == EXPECTED_POPULATION

    assert (
        replay_summary["priority_distribution"]
        == EXPECTED_PRIORITY_DISTRIBUTION
    )

    assert (
        replay_summary["human_review_required_count"]
        == EXPECTED_POPULATION
    )

    assert (
        replay_summary["autonomous_clinical_action_count"]
        == 0
    )

    assert replay_summary["safety_flag_count"] == 0

    assert (
        replay_summary["deterministic_replay_passed"]
        is True
    )

    print("Replay population: PASSED")
    print("Replay priority distribution: PASSED")
    print("Human-review count: PASSED")
    print("Autonomous-action count: PASSED")
    print("Safety-flag count: PASSED")
    print("Determinism status: PASSED")

    # -------------------------------------------------------------------------
    # L — ARTIFACT HASHES
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("L — END-TO-END ARTIFACT HASHES")
    print("=" * 80)

    hashes = {
        "patient_agent_contexts.jsonl":
            sha256_file(CONTEXT_PATH),

        "explanation_agent_outputs.jsonl":
            sha256_file(EXPLANATION_PATH),

        "end_to_end_workflow_contract.json":
            sha256_file(WORKFLOW_CONTRACT_PATH),

        "end_to_end_case_packets.jsonl":
            sha256_file(PACKET_PATH),

        "end_to_end_replay_summary.json":
            sha256_file(REPLAY_SUMMARY_PATH),
    }

    for name, digest in hashes.items():
        print(f"{name}: {digest}")

    # -------------------------------------------------------------------------
    # M — SAVE INDEPENDENT AUDIT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("M — SAVE INDEPENDENT SYSTEM AUDIT")
    print("=" * 80)

    audit = {
        "phase": "10.5.3",

        "audit_name":
            "Independent End-to-End System Audit",

        "status": "PASSED",

        "population":
            EXPECTED_POPULATION,

        "packet_schema":
            EXPECTED_PACKET_SCHEMA,

        "priority_distribution":
            distribution,

        "checks": {
            "encounter_alignment": True,
            "primary_model_preservation": True,
            "router_preservation": True,
            "priority_preservation": True,
            "explanation_preservation": True,
            "final_packet_contract": True,
            "prohibited_fields_absent": True,
            "human_in_the_loop_safety": True,
            "ground_truth_leakage_absent": True,
            "demographic_causal_language_absent": True,
            "replay_summary_consistent": True,
        },

        "violations": {
            "prediction_mismatches":
                len(prediction_mismatches),

            "probability_mismatches":
                len(probability_mismatches),

            "threshold_mismatches":
                len(threshold_mismatches),

            "router_probability_mismatches":
                len(router_probability_mismatches),

            "router_selection_mismatches":
                len(router_selection_mismatches),

            "budget_mismatches":
                len(budget_mismatches),

            "priority_mismatches":
                len(priority_mismatches),

            "explanation_mismatches":
                len(explanation_mismatches),

            "signal_mismatches":
                len(signal_mismatches),

            "uncertainty_mismatches":
                len(uncertainty_mismatches),

            "human_review_text_mismatches":
                len(human_review_text_mismatches),

            "prohibited_field_findings":
                len(prohibited_findings),

            "disposition_errors":
                len(disposition_errors),

            "autonomous_action_errors":
                len(autonomous_action_errors),

            "safety_flag_errors":
                len(safety_flag_errors),

            "ground_truth_leakage_findings":
                len(leakage_findings),

            "demographic_findings":
                len(demographic_findings),
        },

        "artifact_sha256":
            hashes,

        "ground_truth_used_by_workflow":
            False,

        "autonomous_clinical_action":
            False,

        "human_review_required":
            True,
    }

    with AUDIT_PATH.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            audit,
            f,
            indent=2,
            sort_keys=True
        )

    print("Audit artifact:", AUDIT_PATH)

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print(
        "PHASE 10.5.3 COMPLETE — "
        "ALL END-TO-END AUDITS PASSED"
    )
    print("=" * 80)

    print(
        "\nThe final CareCompute human-review packets independently "
        "preserve the frozen upstream workflow and satisfy the "
        "Phase 10.5.1 safety contract."
    )


if __name__ == "__main__":
    main()
