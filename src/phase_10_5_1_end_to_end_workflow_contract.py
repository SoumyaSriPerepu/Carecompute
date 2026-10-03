"""
Phase 10.5.1 — End-to-End Agentic Workflow Contract

CareCompute

Purpose
-------
Define the immutable input/output and safety contract for the complete
CareCompute human-in-the-loop Rescue Review workflow.

This phase does NOT:
- retrain a model,
- recalculate model probabilities,
- recalculate router probabilities,
- modify router selection,
- modify the primary threshold,
- modify the review budget,
- modify Rescue Review priority,
- modify explanations,
- use ground truth,
- make diagnoses,
- recommend treatments or medications.

The contract binds already-frozen upstream artifacts into a single
end-to-end workflow specification.
"""

import hashlib
import json
from pathlib import Path


# =============================================================================
# PATHS
# =============================================================================

BASE = Path("results/eligible/agents")

CONTEXT_PATH = BASE / "patient_agent_contexts.jsonl"
RULES_PATH = BASE / "rescue_review_agent_frozen_rules.json"
EXPLANATION_CONTRACT_PATH = BASE / "explanation_agent_output_contract.json"
EXPLANATION_OUTPUT_PATH = BASE / "explanation_agent_outputs.jsonl"
EXPLANATION_AUDIT_PATH = BASE / "explanation_fidelity_safety_audit.json"
EXPLANATION_FREEZE_PATH = BASE / "explanation_agent_freeze_manifest.json"

OUTPUT_PATH = BASE / "end_to_end_workflow_contract.json"


# =============================================================================
# FROZEN EXPECTATIONS
# =============================================================================

EXPECTED_POPULATION = 1178

EXPECTED_PRIMARY_THRESHOLD = 0.115
EXPECTED_REVIEW_BUDGET = 0.15

EXPECTED_CONTEXT_SCHEMA = "10.2"
EXPECTED_RULE_VERSION = "10.3.4"
EXPECTED_EXPLANATION_CONTRACT = "10.4.1"
EXPECTED_EXPLANATION_SCHEMA = "10.4.2"

WORKFLOW_CONTRACT_VERSION = "10.5.1"


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
    print("PHASE 10.5.1 — END-TO-END AGENTIC WORKFLOW CONTRACT")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # A — VERIFY FROZEN UPSTREAM ARTIFACTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("A — VERIFY FROZEN UPSTREAM ARTIFACTS")
    print("=" * 80)

    required_paths = [
        CONTEXT_PATH,
        RULES_PATH,
        EXPLANATION_CONTRACT_PATH,
        EXPLANATION_OUTPUT_PATH,
        EXPLANATION_AUDIT_PATH,
        EXPLANATION_FREEZE_PATH,
    ]

    for path in required_paths:

        if not path.exists():
            raise FileNotFoundError(
                f"Missing required artifact: {path}"
            )

        print(f"FOUND: {path}")

    print("Required upstream artifacts: PASSED")

    # -------------------------------------------------------------------------
    # B — LOAD FROZEN SUBSYSTEM
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("B — LOAD FROZEN SUBSYSTEM")
    print("=" * 80)

    contexts = load_jsonl(CONTEXT_PATH)
    rules = load_json(RULES_PATH)
    explanation_contract = load_json(
        EXPLANATION_CONTRACT_PATH
    )
    explanation_outputs = load_jsonl(
        EXPLANATION_OUTPUT_PATH
    )
    explanation_audit = load_json(
        EXPLANATION_AUDIT_PATH
    )
    explanation_freeze = load_json(
        EXPLANATION_FREEZE_PATH
    )

    print("Contexts:", len(contexts))
    print("Explanation outputs:", len(explanation_outputs))
    print("Rule version:", rules["rule_version"])
    print(
        "Explanation contract:",
        explanation_contract["contract_version"]
    )
    print(
        "Explanation freeze:",
        explanation_freeze["status"]
    )

    # -------------------------------------------------------------------------
    # C — VERIFY UPSTREAM LOCKS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("C — VERIFY UPSTREAM LOCKS")
    print("=" * 80)

    assert len(contexts) == EXPECTED_POPULATION
    assert len(explanation_outputs) == EXPECTED_POPULATION

    assert all(
        context["schema_version"] == EXPECTED_CONTEXT_SCHEMA
        for context in contexts
    )

    assert all(
        output["schema_version"] == EXPECTED_EXPLANATION_SCHEMA
        for output in explanation_outputs
    )

    assert rules["rule_version"] == EXPECTED_RULE_VERSION
    assert rules["status"] == "FROZEN"

    assert (
        explanation_contract["contract_version"]
        == EXPECTED_EXPLANATION_CONTRACT
    )

    assert explanation_audit["status"] == "PASSED"
    assert explanation_freeze["status"] == "FROZEN"

    assert (
        rules["frozen_primary_model_threshold"]
        == EXPECTED_PRIMARY_THRESHOLD
    )

    assert (
        rules["frozen_router_review_budget"]
        == EXPECTED_REVIEW_BUDGET
    )

    assert (
        explanation_freeze["immutable_components"]
        ["primary_model_threshold"]
        == EXPECTED_PRIMARY_THRESHOLD
    )

    assert (
        explanation_freeze["immutable_components"]
        ["rescue_review_budget"]
        == EXPECTED_REVIEW_BUDGET
    )

    print("Population lock: PASSED")
    print("Context-schema lock: PASSED")
    print("Rescue Review rules frozen: PASSED")
    print("Explanation audit passed: PASSED")
    print("Explanation Agent frozen: PASSED")
    print("Primary threshold lock: PASSED")
    print("Review-budget lock: PASSED")

    # -------------------------------------------------------------------------
    # D — VERIFY EXPLANATION FREEZE HASHES
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("D — VERIFY FROZEN ARTIFACT INTEGRITY")
    print("=" * 80)

    frozen_hashes = explanation_freeze["artifact_sha256"]

    current_hashes = {
        "patient_agent_contexts.jsonl":
            sha256_file(CONTEXT_PATH),

        "rescue_review_agent_frozen_rules.json":
            sha256_file(RULES_PATH),

        "explanation_agent_output_contract.json":
            sha256_file(EXPLANATION_CONTRACT_PATH),

        "explanation_agent_outputs.jsonl":
            sha256_file(EXPLANATION_OUTPUT_PATH),
    }

    for name, current_hash in current_hashes.items():

        frozen_hash = frozen_hashes[name]

        print(name)
        print("  frozen :", frozen_hash)
        print("  current:", current_hash)

        assert current_hash == frozen_hash

    print("Frozen artifact integrity: PASSED")

    # -------------------------------------------------------------------------
    # E — DEFINE WORKFLOW STAGES
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("E — DEFINE END-TO-END WORKFLOW")
    print("=" * 80)

    workflow_stages = [
        {
            "stage": 1,
            "name": "Primary Risk Model",
            "role":
                "Provide the frozen calibrated 30-day readmission "
                "probability and frozen binary prediction.",
            "modifiable": False,
        },
        {
            "stage": 2,
            "name": "Primary Decision Gate",
            "role":
                "Apply the already-frozen primary decision threshold.",
            "threshold": EXPECTED_PRIMARY_THRESHOLD,
            "modifiable": False,
        },
        {
            "stage": 3,
            "name": "Rescue Router",
            "role":
                "Identify already-selected low-risk cases for "
                "additional human review.",
            "review_budget": EXPECTED_REVIEW_BUDGET,
            "modifiable": False,
        },
        {
            "stage": 4,
            "name": "Rescue Review Agent",
            "role":
                "Assign deterministic review priority from approved "
                "frozen review signals.",
            "modifiable": False,
        },
        {
            "stage": 5,
            "name": "Explanation Agent",
            "role":
                "Provide deterministic non-diagnostic explanations "
                "for the frozen review priority.",
            "modifiable": False,
        },
        {
            "stage": 6,
            "name": "Human Review",
            "role":
                "Require a human reviewer to interpret the structured "
                "review packet. No autonomous clinical action occurs.",
            "required": True,
        },
    ]

    for stage in workflow_stages:
        print(
            f"{stage['stage']}. {stage['name']}"
        )

    print("Workflow-stage definition: PASSED")

    # -------------------------------------------------------------------------
    # F — DEFINE INPUT CONTRACT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("F — DEFINE WORKFLOW INPUT CONTRACT")
    print("=" * 80)

    input_contract = {
        "schema_version":
            EXPECTED_CONTEXT_SCHEMA,

        "population":
            "Frozen Rescue Router selected cases only",

        "expected_population":
            EXPECTED_POPULATION,

        "required_sections": [
            "encounter",
            "primary_model",
            "uncertainty",
            "utilization_context",
            "router_context",
            "demographic_context",
            "agent_constraints",
        ],

        "ground_truth_allowed":
            False,

        "requires_router_selection":
            True,

        "required_router_selection_value":
            1,

        "primary_threshold":
            EXPECTED_PRIMARY_THRESHOLD,

        "review_budget":
            EXPECTED_REVIEW_BUDGET,
    }

    print("Input population:", EXPECTED_POPULATION)
    print("Ground truth allowed: NO")
    print("Router-selected cases only: YES")
    print("Input contract: DEFINED")

    # -------------------------------------------------------------------------
    # G — DEFINE FINAL CASE-PACKET CONTRACT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("G — DEFINE FINAL CASE-PACKET CONTRACT")
    print("=" * 80)

    final_packet_contract = {
        "schema_version": "10.5.2",

        "required_fields": {
            "schema_version": "string",
            "encounter_id": "integer",

            "primary_model": {
                "predicted_30d": "integer",
                "calibrated_probability": "float",
                "decision_threshold": "float",
            },

            "rescue_router": {
                "fn_router_probability": "float",
                "selected_for_review": "integer",
                "review_budget": "float",
            },

            "rescue_review": {
                "review_priority": [
                    "LOW",
                    "MODERATE",
                    "HIGH",
                ]
            },

            "explanation": {
                "explanation": "string",
                "signal_explanations": "list",
                "uncertainty_statement": "string",
                "human_review_statement": "string",
            },

            "workflow_disposition":
                "HUMAN_REVIEW_REQUIRED",

            "autonomous_clinical_action":
                False,

            "safety_flag":
                "boolean",
        },
    }

    print("Final packet schema: 10.5.2")
    print(
        "Workflow disposition: HUMAN_REVIEW_REQUIRED"
    )
    print("Autonomous clinical action: FALSE")
    print("Final packet contract: DEFINED")

    # -------------------------------------------------------------------------
    # H — DEFINE GLOBAL SAFETY CONSTRAINTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("H — DEFINE GLOBAL SAFETY CONSTRAINTS")
    print("=" * 80)

    safety_constraints = {
        "ground_truth_available_to_agents": False,

        "may_modify_primary_prediction": False,
        "may_modify_primary_probability": False,
        "may_modify_primary_threshold": False,

        "may_modify_router_probability": False,
        "may_modify_router_selection": False,
        "may_modify_review_budget": False,

        "may_modify_review_priority": False,
        "may_modify_frozen_explanation": False,

        "may_make_diagnosis": False,
        "may_recommend_treatment": False,
        "may_recommend_medication": False,

        "may_generate_new_clinical_fact": False,

        "may_use_demographics_as_causal_explanation": False,

        "may_take_autonomous_clinical_action": False,

        "human_review_required": True,
    }

    for key, value in safety_constraints.items():
        print(f"{key}: {value}")

    # -------------------------------------------------------------------------
    # I — DEFINE PROHIBITED FINAL FIELDS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("I — DEFINE PROHIBITED FINAL-PACKET FIELDS")
    print("=" * 80)

    prohibited_fields = [
        "actual_30d",
        "case_type",
        "router_target",
        "patient_nbr",

        "diagnosis",
        "treatment",
        "medication",
        "prescription",

        "new_prediction",
        "new_probability",
        "new_router_probability",
        "new_router_selection",
        "new_threshold",
        "new_review_budget",
    ]

    for field in prohibited_fields:
        print("-", field)

    print("Prohibited-field policy: DEFINED")

    # -------------------------------------------------------------------------
    # J — CREATE CONTRACT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("J — CREATE END-TO-END CONTRACT")
    print("=" * 80)

    contract = {
        "contract_version":
            WORKFLOW_CONTRACT_VERSION,

        "system_name":
            "CareCompute",

        "workflow_name":
            "Human-in-the-Loop Rescue Review Workflow",

        "status":
            "DEFINED",

        "purpose":
            "Bind frozen model, routing, review-priority, explanation, "
            "and human-review stages into a reproducible end-to-end "
            "workflow without autonomous clinical action.",

        "workflow_stages":
            workflow_stages,

        "input_contract":
            input_contract,

        "final_packet_contract":
            final_packet_contract,

        "safety_constraints":
            safety_constraints,

        "prohibited_final_packet_fields":
            prohibited_fields,

        "frozen_dependencies": {
            "context_schema":
                EXPECTED_CONTEXT_SCHEMA,

            "rescue_review_rule_version":
                EXPECTED_RULE_VERSION,

            "explanation_contract_version":
                EXPECTED_EXPLANATION_CONTRACT,

            "explanation_output_schema":
                EXPECTED_EXPLANATION_SCHEMA,

            "primary_model_threshold":
                EXPECTED_PRIMARY_THRESHOLD,

            "rescue_review_budget":
                EXPECTED_REVIEW_BUDGET,

            "expected_population":
                EXPECTED_POPULATION,
        },

        "dependency_sha256": {
            **current_hashes,

            "explanation_fidelity_safety_audit.json":
                sha256_file(EXPLANATION_AUDIT_PATH),

            "explanation_agent_freeze_manifest.json":
                sha256_file(EXPLANATION_FREEZE_PATH),
        },
    }

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            contract,
            f,
            indent=2,
            sort_keys=True
        )

    print("Contract written:", OUTPUT_PATH)

    # -------------------------------------------------------------------------
    # K — VERIFY WRITTEN CONTRACT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("K — VERIFY WRITTEN CONTRACT")
    print("=" * 80)

    written = load_json(OUTPUT_PATH)

    assert (
        written["contract_version"]
        == WORKFLOW_CONTRACT_VERSION
    )

    assert (
        written["input_contract"]
        ["expected_population"]
        == EXPECTED_POPULATION
    )

    assert (
        written["safety_constraints"]
        ["ground_truth_available_to_agents"]
        is False
    )

    assert (
        written["safety_constraints"]
        ["may_take_autonomous_clinical_action"]
        is False
    )

    assert (
        written["safety_constraints"]
        ["human_review_required"]
        is True
    )

    assert (
        written["final_packet_contract"]
        ["required_fields"]
        ["workflow_disposition"]
        == "HUMAN_REVIEW_REQUIRED"
    )

    print("Contract version: PASSED")
    print("Population requirement: PASSED")
    print("Ground-truth exclusion: PASSED")
    print("No autonomous clinical action: PASSED")
    print("Human-review requirement: PASSED")
    print("Final disposition requirement: PASSED")

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("PHASE 10.5.1 COMPLETE — WORKFLOW CONTRACT DEFINED")
    print("=" * 80)

    print(
        "\nNo frozen upstream prediction, probability, routing decision, "
        "review priority, explanation, threshold, or review budget "
        "was modified."
    )


if __name__ == "__main__":
    main()
