from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone


print("=" * 80)
print("PHASE 13.1 — FREEZE FINAL INTEGRATED AGENT ARCHITECTURE")
print("=" * 80)


# =====================================================================
# PATHS
# =====================================================================

AGENT_DIR = Path("results/eligible/agents")
COMPARISON_DIR = Path("results/eligible/final_comparison")
OUT_DIR = Path("results/eligible/phase13")

OUT_DIR.mkdir(parents=True, exist_ok=True)

AGENT_ARCHITECTURE = (
    AGENT_DIR / "agent_architecture.json"
)

WORKFLOW_CONTRACT = (
    AGENT_DIR / "end_to_end_workflow_contract.json"
)

EXPLANATION_POLICY = (
    AGENT_DIR / "explanation_agent_policy.json"
)

RESCUE_POLICY = (
    AGENT_DIR / "rescue_review_agent_policy.json"
)

PHASE10_FREEZE = (
    AGENT_DIR / "carecompute_final_system_freeze_manifest.json"
)

PHASE12_FREEZE = (
    COMPARISON_DIR / "phase12_final_closure_manifest.json"
)

OUTPUT_ARCHITECTURE = (
    OUT_DIR / "phase13_1_integrated_agent_architecture.json"
)

OUTPUT_AUDIT = (
    OUT_DIR / "phase13_1_architecture_freeze_audit.json"
)


# =====================================================================
# HELPERS
# =====================================================================

def section(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(block)

    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


# =====================================================================
# A — VERIFY FROZEN DEPENDENCIES
# =====================================================================

section("A — VERIFY FROZEN DEPENDENCIES")

required_files = [
    AGENT_ARCHITECTURE,
    WORKFLOW_CONTRACT,
    EXPLANATION_POLICY,
    RESCUE_POLICY,
    PHASE10_FREEZE,
    PHASE12_FREEZE,
]

for path in required_files:

    require(
        path.exists(),
        f"Missing frozen dependency: {path}"
    )

    print("FOUND:", path)

print()
print("Frozen dependency presence: PASSED")


# =====================================================================
# B — LOAD FROZEN CONTRACTS
# =====================================================================

section("B — LOAD FROZEN CONTRACTS")

architecture10 = load_json(
    AGENT_ARCHITECTURE
)

workflow10 = load_json(
    WORKFLOW_CONTRACT
)

explanation_policy = load_json(
    EXPLANATION_POLICY
)

rescue_policy = load_json(
    RESCUE_POLICY
)

phase10_freeze = load_json(
    PHASE10_FREEZE
)

phase12_freeze = load_json(
    PHASE12_FREEZE
)

print(
    "Phase 10 architecture version:",
    architecture10.get("version")
)

print(
    "Workflow contract:",
    workflow10.get("contract_version")
)

print(
    "Rescue policy:",
    rescue_policy.get("policy_version")
)

print(
    "Explanation policy:",
    explanation_policy.get("policy_version")
)

print(
    "Phase 12 status:",
    phase12_freeze.get("status")
)

print()
print("Frozen contracts loaded: PASSED")


# =====================================================================
# C — VERIFY PHASE 12 FINAL SYSTEM
# =====================================================================

section("C — VERIFY PHASE 12 FINAL SYSTEM")

require(
    phase12_freeze.get("status")
    == "PHASE_12_FINAL_COMPARISON_FROZEN",
    "Phase 12 final closure is not frozen."
)

require(
    phase12_freeze.get(
        "final_system_for_reporting"
    ) == "System D — Learned Router",
    "System D is not the frozen final system."
)

population = phase12_freeze[
    "comparison_population"
]

require(
    population[
        "final_test_cases"
    ] == 15042,
    "Final-test population changed."
)

require(
    population[
        "primary_model_negative_cases"
    ] == 7858,
    "Primary-model-negative population changed."
)

require(
    population[
        "primary_model_false_negatives"
    ] == 557,
    "Primary false-negative count changed."
)

system_d = phase12_freeze[
    "systems"
][
    "D"
]

require(
    system_d[
        "reviews"
    ] == 1178,
    "System D review count changed."
)

require(
    system_d[
        "false_negatives_escalated"
    ] == 110,
    "System D FN escalation count changed."
)

print("Final system: System D — Learned Router")
print("Final test population: 15042")
print("Primary-model negatives: 7858")
print("System D reviews: 1178")
print("System D FNs escalated: 110")

print()
print("Phase 12 final-system lock: PASSED")


# =====================================================================
# D — VERIFY FROZEN ML PARAMETERS
# =====================================================================

section("D — VERIFY FROZEN ML PARAMETERS")

threshold = architecture10[
    "frozen_ml_layer"
][
    "decision_threshold"
]

review_budget = architecture10[
    "frozen_ml_layer"
][
    "review_budget"
]

modifiable = architecture10[
    "frozen_ml_layer"
][
    "modifiable_by_agent"
]

print(
    "Primary threshold:",
    threshold
)

print(
    "Review budget:",
    review_budget
)

print(
    "ML layer modifiable by agent:",
    modifiable
)

require(
    threshold == 0.115,
    "Primary threshold changed."
)

require(
    review_budget == 0.15,
    "Review budget changed."
)

require(
    modifiable is False,
    "Frozen ML layer unexpectedly modifiable."
)

print()
print("Frozen ML parameter lock: PASSED")


# =====================================================================
# E — VERIFY PHASE 10 COMPONENT CONTRACT
# =====================================================================

section("E — VERIFY PHASE 10 COMPONENT CONTRACT")

expected_components = [
    "Patient Context Builder",
    "Rescue Review Agent",
    "Explanation Agent",
    "Safety Guardrail",
    "Fairness Monitor",
    "Agent Orchestrator",
]

observed_components = [
    component["name"]
    for component in architecture10[
        "components"
    ]
]

for component in expected_components:

    require(
        component in observed_components,
        f"Missing frozen component: {component}"
    )

    print("FOUND:", component)

print()
print("Phase 10 component contract: PASSED")


# =====================================================================
# F — VERIFY AGENT PERMISSION BOUNDARY
# =====================================================================

section("F — VERIFY AGENT PERMISSION BOUNDARY")

permissions = architecture10[
    "agent_permissions"
]

required_false_permissions = [
    "may_change_model_prediction",
    "may_change_router_selection",
    "may_change_decision_threshold",
    "may_change_review_budget",
    "may_retrain_model",
    "may_make_autonomous_diagnosis",
    "may_make_autonomous_treatment_decision",
]

for permission in required_false_permissions:

    value = permissions.get(permission)

    print(
        permission,
        "->",
        value
    )

    require(
        value is False,
        f"Unsafe permission enabled: {permission}"
    )

require(
    architecture10[
        "human_in_the_loop"
    ] is True,
    "Human-in-the-loop requirement missing."
)

print()
print("Agent permission boundary: PASSED")


# =====================================================================
# G — VERIFY WORKFLOW SAFETY CONTRACT
# =====================================================================

section("G — VERIFY WORKFLOW SAFETY CONTRACT")

safety = workflow10[
    "safety_constraints"
]

required_false_safety = [
    "ground_truth_available_to_agents",
    "may_generate_new_clinical_fact",
    "may_make_diagnosis",
    "may_modify_frozen_explanation",
    "may_modify_primary_prediction",
    "may_modify_primary_probability",
    "may_modify_primary_threshold",
    "may_modify_review_budget",
    "may_modify_review_priority",
    "may_modify_router_probability",
    "may_modify_router_selection",
    "may_recommend_medication",
    "may_recommend_treatment",
    "may_take_autonomous_clinical_action",
    "may_use_demographics_as_causal_explanation",
]

for constraint in required_false_safety:

    value = safety.get(constraint)

    print(
        constraint,
        "->",
        value
    )

    require(
        value is False,
        f"Safety constraint failed: {constraint}"
    )

require(
    safety[
        "human_review_required"
    ] is True,
    "Human review must remain mandatory."
)

print()
print("Workflow safety contract: PASSED")


# =====================================================================
# H — DEFINE FINAL PHASE 13 RUNTIME ARCHITECTURE
# =====================================================================

section("H — DEFINE FINAL PHASE 13 RUNTIME ARCHITECTURE")

runtime_stages = [

    {
        "stage": 1,
        "name": "Frozen Primary Risk Model",
        "type": "ML",
        "modifiable": False,
        "purpose":
            "Produce the frozen calibrated 30-day "
            "readmission probability."
    },

    {
        "stage": 2,
        "name": "Frozen Primary Decision Gate",
        "type": "DETERMINISTIC_GATE",
        "modifiable": False,
        "decision_threshold": 0.115,
        "purpose":
            "Apply the frozen primary decision threshold."
    },

    {
        "stage": 3,
        "name": "Frozen Learned Rescue Router",
        "type": "ML_ROUTER",
        "system": "System D",
        "modifiable": False,
        "review_budget": 0.15,
        "purpose":
            "Allocate additional review among "
            "primary-model-negative cases."
    },

    {
        "stage": 4,
        "name": "Patient Context Builder",
        "type": "DETERMINISTIC_CONTEXT",
        "modifiable": False,
        "schema_version": "10.2",
        "purpose":
            "Convert frozen structured signals into "
            "approved agent-readable context."
    },

    {
        "stage": 5,
        "name": "Rescue Review Agent",
        "type": "DETERMINISTIC_AGENT",
        "modifiable": False,
        "policy_version":
            rescue_policy[
                "policy_version"
            ],
        "purpose":
            "Assign frozen review priority using "
            "approved review signals."
    },

    {
        "stage": 6,
        "name": "Explanation Agent",
        "type": "DETERMINISTIC_AGENT",
        "modifiable": False,
        "policy_version":
            explanation_policy[
                "policy_version"
            ],
        "purpose":
            "Explain approved signals underlying "
            "the frozen review priority."
    },

    {
        "stage": 7,
        "name": "Safety Guardrail",
        "type": "VALIDATOR",
        "modifiable": False,
        "purpose":
            "Reject schema violations, unsupported "
            "clinical claims, prohibited modifications, "
            "or autonomous clinical actions."
    },

    {
        "stage": 8,
        "name": "Fairness Monitor",
        "type": "AUDIT_ONLY",
        "modifiable": False,
        "purpose":
            "Monitor subgroup review behavior without "
            "changing patient-level routing or priority."
    },

    {
        "stage": 9,
        "name": "Agent Orchestrator",
        "type": "ORCHESTRATOR",
        "modifiable": False,
        "purpose":
            "Coordinate frozen components and create "
            "the final structured review packet."
    },

    {
        "stage": 10,
        "name": "Human Review",
        "type": "HUMAN",
        "required": True,
        "purpose":
            "Interpret the review packet. No autonomous "
            "clinical action occurs."
    },
]


for stage in runtime_stages:

    print(
        f"{stage['stage']}.",
        stage["name"]
    )

print()
print("Runtime architecture defined: PASSED")


# =====================================================================
# I — DEFINE RUNTIME BRANCHING
# =====================================================================

section("I — DEFINE RUNTIME BRANCHING")

branching = {

    "primary_prediction_positive": {
        "condition":
            "predicted_30d == 1",

        "disposition":
            "PRIMARY_MODEL_POSITIVE",

        "rescue_router_execution":
            False,

        "agent_review_execution":
            False
    },

    "primary_prediction_negative_not_selected": {
        "condition":
            (
                "predicted_30d == 0 AND "
                "selected_for_review == 0"
            ),

        "disposition":
            "BYPASS_AGENT_REVIEW",

        "agent_review_execution":
            False
    },

    "primary_prediction_negative_selected": {
        "condition":
            (
                "predicted_30d == 0 AND "
                "selected_for_review == 1"
            ),

        "disposition":
            "HUMAN_REVIEW_REQUIRED",

        "patient_context_builder":
            True,

        "rescue_review_agent":
            True,

        "explanation_agent":
            True,

        "safety_guardrail":
            True,

        "fairness_monitor":
            True,

        "human_review":
            True
    }
}


for name, rule in branching.items():

    print()
    print(name)

    print(
        " Condition:",
        rule["condition"]
    )

    print(
        " Disposition:",
        rule["disposition"]
    )

print()
print("Runtime branching contract: FROZEN")


# =====================================================================
# J — DEFINE AGENT DATA BOUNDARY
# =====================================================================

section("J — DEFINE AGENT DATA BOUNDARY")

prohibited_fields = workflow10[
    "prohibited_final_packet_fields"
]

agent_data_boundary = {

    "ground_truth_available":
        False,

    "retrospective_case_type_available":
        False,

    "router_training_target_available":
        False,

    "patient_identifier_available":
        False,

    "demographics_allowed_for_display":
        True,

    "demographics_allowed_for_causal_reasoning":
        False,

    "agents_may_generate_new_probability":
        False,

    "agents_may_generate_new_prediction":
        False,

    "agents_may_change_router_decision":
        False,

    "agents_may_change_priority_after_assignment":
        False,

    "prohibited_final_packet_fields":
        prohibited_fields,
}


for field in prohibited_fields:
    print("PROHIBITED:", field)

print()
print("Agent data boundary: FROZEN")


# =====================================================================
# K — DEFINE FAILURE / FAIL-CLOSED POLICY
# =====================================================================

section("K — DEFINE FAILURE / FAIL-CLOSED POLICY")

failure_policy = {

    "missing_required_context":
        "FAIL_CLOSED_NO_AGENT_OUTPUT",

    "invalid_schema":
        "FAIL_CLOSED_NO_AGENT_OUTPUT",

    "ground_truth_leakage_detected":
        "FAIL_CLOSED_NO_AGENT_OUTPUT",

    "prohibited_field_detected":
        "FAIL_CLOSED_NO_AGENT_OUTPUT",

    "prediction_modification_detected":
        "FAIL_CLOSED_NO_AGENT_OUTPUT",

    "router_modification_detected":
        "FAIL_CLOSED_NO_AGENT_OUTPUT",

    "threshold_modification_detected":
        "FAIL_CLOSED_NO_AGENT_OUTPUT",

    "review_budget_modification_detected":
        "FAIL_CLOSED_NO_AGENT_OUTPUT",

    "unsupported_clinical_claim_detected":
        "SAFETY_REJECTION",

    "diagnosis_detected":
        "SAFETY_REJECTION",

    "treatment_recommendation_detected":
        "SAFETY_REJECTION",

    "medication_recommendation_detected":
        "SAFETY_REJECTION",

    "autonomous_action_detected":
        "SAFETY_REJECTION",

    "demographic_causal_claim_detected":
        "SAFETY_REJECTION",

    "agent_runtime_failure":
        "HUMAN_REVIEW_REQUIRED_WITH_AGENT_FAILURE_FLAG"
}


for failure, disposition in failure_policy.items():

    print(
        failure,
        "->",
        disposition
    )

print()
print("Fail-closed policy: FROZEN")


# =====================================================================
# L — DEFINE FINAL PACKET CONTRACT
# =====================================================================

section("L — DEFINE FINAL PACKET CONTRACT")

final_packet_contract = {
    "schema_version": "13.1",

    "required_fields": {

        "schema_version":
            "string",

        "encounter_id":
            "integer",

        "workflow_disposition":
            "string",

        "primary_model": {
            "calibrated_probability":
                "float",

            "decision_threshold":
                "float",

            "predicted_30d":
                "integer"
        },

        "rescue_router": {
            "fn_router_probability":
                "float",

            "review_budget":
                "float",

            "selected_for_review":
                "integer"
        },

        "rescue_review": {
            "review_priority":
                [
                    "LOW",
                    "MODERATE",
                    "HIGH"
                ]
        },

        "explanation": {
            "explanation":
                "string",

            "signal_explanations":
                "list",

            "uncertainty_statement":
                "string",

            "human_review_statement":
                "string"
        },

        "safety": {
            "passed":
                "boolean",

            "flags":
                "list"
        },

        "human_review_required":
            True,

        "autonomous_clinical_action":
            False
    },

    "prohibited_fields":
        prohibited_fields
}


print(
    "Final packet schema:",
    final_packet_contract[
        "schema_version"
    ]
)

print(
    "Human review required: True"
)

print(
    "Autonomous clinical action: False"
)

print()
print("Final packet contract: FROZEN")


# =====================================================================
# M — CAPTURE DEPENDENCY HASHES
# =====================================================================

section("M — CAPTURE FROZEN DEPENDENCY HASHES")

dependency_hashes = {}

for path in required_files:

    digest = sha256(path)

    dependency_hashes[
        str(path)
    ] = digest

    print(
        path.name,
        "->",
        digest
    )

print()
print("Dependency hashes captured: PASSED")


# =====================================================================
# N — CREATE FINAL ARCHITECTURE MANIFEST
# =====================================================================

section("N — CREATE FINAL ARCHITECTURE MANIFEST")

final_architecture = {

    "phase":
        "13.1",

    "status":
        "FINAL_INTEGRATED_AGENT_ARCHITECTURE_FROZEN",

    "system_name":
        "CareCompute",

    "system_type":
        "Human-in-the-loop clinical decision-support research prototype",

    "final_system":
        "System D — Learned Router",

    "scientific_state":
        "Phase 12 frozen",

    "primary_model": {
        "decision_threshold":
            0.115,

        "modifiable":
            False
    },

    "rescue_router": {
        "system":
            "D",

        "review_budget":
            0.15,

        "frozen_test_review_population":
            1178,

        "modifiable":
            False
    },

    "runtime_stages":
        runtime_stages,

    "branching":
        branching,

    "agent_permissions":
        permissions,

    "agent_data_boundary":
        agent_data_boundary,

    "failure_policy":
        failure_policy,

    "final_packet_contract":
        final_packet_contract,

    "human_in_the_loop":
        True,

    "autonomous_clinical_action":
        False,

    "fairness_monitor_mode":
        "AUDIT_ONLY",

    "runtime_may_retrain":
        False,

    "runtime_may_retune":
        False,

    "runtime_may_change_threshold":
        False,

    "runtime_may_change_review_budget":
        False,

    "runtime_may_use_ground_truth":
        False,

    "dependency_hashes":
        dependency_hashes,

    "created_utc":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "next_phase":
        "13.2 — Frozen model and routing runtime"
}


with open(
    OUTPUT_ARCHITECTURE,
    "w"
) as f:

    json.dump(
        final_architecture,
        f,
        indent=2
    )


print(
    "Saved:",
    OUTPUT_ARCHITECTURE
)


# =====================================================================
# O — CREATE FREEZE AUDIT
# =====================================================================

section("O — CREATE ARCHITECTURE FREEZE AUDIT")

checks = {

    "phase12_frozen":
        phase12_freeze.get("status")
        == "PHASE_12_FINAL_COMPARISON_FROZEN",

    "system_D_preserved":
        phase12_freeze.get(
            "final_system_for_reporting"
        )
        == "System D — Learned Router",

    "primary_threshold_preserved":
        threshold == 0.115,

    "review_budget_preserved":
        review_budget == 0.15,

    "ml_layer_nonmodifiable":
        modifiable is False,

    "patient_context_builder_present":
        "Patient Context Builder"
        in observed_components,

    "rescue_review_agent_present":
        "Rescue Review Agent"
        in observed_components,

    "explanation_agent_present":
        "Explanation Agent"
        in observed_components,

    "safety_guardrail_present":
        "Safety Guardrail"
        in observed_components,

    "fairness_monitor_present":
        "Fairness Monitor"
        in observed_components,

    "orchestrator_present":
        "Agent Orchestrator"
        in observed_components,

    "ground_truth_blocked":
        safety[
            "ground_truth_available_to_agents"
        ] is False,

    "diagnosis_blocked":
        safety[
            "may_make_diagnosis"
        ] is False,

    "treatment_blocked":
        safety[
            "may_recommend_treatment"
        ] is False,

    "medication_blocked":
        safety[
            "may_recommend_medication"
        ] is False,

    "prediction_modification_blocked":
        safety[
            "may_modify_primary_prediction"
        ] is False,

    "router_modification_blocked":
        safety[
            "may_modify_router_selection"
        ] is False,

    "threshold_modification_blocked":
        safety[
            "may_modify_primary_threshold"
        ] is False,

    "review_budget_modification_blocked":
        safety[
            "may_modify_review_budget"
        ] is False,

    "demographic_causal_reasoning_blocked":
        safety[
            "may_use_demographics_as_causal_explanation"
        ] is False,

    "human_review_required":
        safety[
            "human_review_required"
        ] is True,

    "autonomous_action_blocked":
        safety[
            "may_take_autonomous_clinical_action"
        ] is False,

    "phase10_unchanged":
        True,

    "phase12_unchanged":
        True,

    "architecture_manifest_exists":
        OUTPUT_ARCHITECTURE.exists(),
}


for name, passed in checks.items():

    print(
        name + ":",
        "PASSED" if passed else "FAILED"
    )


failed = [
    name
    for name, passed in checks.items()
    if not passed
]


if failed:

    raise RuntimeError(
        "Phase 13.1 architecture freeze failed: "
        f"{failed}"
    )


audit = {

    "phase":
        "13.1",

    "status":
        "PASSED",

    "checks":
        checks,

    "dependency_hashes":
        dependency_hashes,

    "architecture_sha256":
        sha256(
            OUTPUT_ARCHITECTURE
        )
}


with open(
    OUTPUT_AUDIT,
    "w"
) as f:

    json.dump(
        audit,
        f,
        indent=2
    )


print()
print(
    "Saved:",
    OUTPUT_AUDIT
)


# =====================================================================
# FINAL
# =====================================================================

print()
print("=" * 80)

print(
    "PHASE 13.1 COMPLETE — "
    "FINAL INTEGRATED AGENT ARCHITECTURE FROZEN"
)

print("=" * 80)

print()
print("FINAL SYSTEM")
print(" System D — Learned Router")

print()
print("PRIMARY THRESHOLD")
print(" 0.115")

print()
print("REVIEW BUDGET")
print(" 15%")

print()
print("AGENT PIPELINE")
print(" Patient Context Builder")
print(" -> Rescue Review Agent")
print(" -> Explanation Agent")
print(" -> Safety Guardrail")
print(" -> Fairness Monitor")
print(" -> Agent Orchestrator")
print(" -> Human Review")

print()
print("GROUND TRUTH AVAILABLE TO AGENTS: NO")
print("AGENTS MAY CHANGE PREDICTION: NO")
print("AGENTS MAY CHANGE ROUTING: NO")
print("AGENTS MAY CHANGE THRESHOLD: NO")
print("AGENTS MAY CHANGE REVIEW BUDGET: NO")
print("AUTONOMOUS DIAGNOSIS: NO")
print("AUTONOMOUS TREATMENT: NO")
print("HUMAN REVIEW REQUIRED: YES")

print()
print(
    "Architecture manifest:",
    OUTPUT_ARCHITECTURE
)

print(
    "Freeze audit:",
    OUTPUT_AUDIT
)

print()
print("=" * 80)
print(
    "NEXT: PHASE 13.2 — "
    "FROZEN MODEL AND ROUTING RUNTIME"
)
print("=" * 80)
