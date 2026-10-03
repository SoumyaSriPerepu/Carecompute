import json
from pathlib import Path


# ============================================================
# PHASE 10.4.1 — EXPLANATION AGENT OUTPUT CONTRACT
# ============================================================

print("=" * 80)
print("PHASE 10.4.1 — EXPLANATION AGENT OUTPUT CONTRACT")
print("=" * 80)


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

AGENT_DIR = Path("results/eligible/agents")
AGENT_DIR.mkdir(parents=True, exist_ok=True)

RULE_FILE = AGENT_DIR / "rescue_review_agent_frozen_rules.json"

OUTPUT_CONTRACT_FILE = (
    AGENT_DIR / "explanation_agent_output_contract.json"
)

POLICY_FILE = (
    AGENT_DIR / "explanation_agent_policy.json"
)

SAMPLE_FILE = (
    AGENT_DIR / "sample_explanation_agent_output.json"
)


# ------------------------------------------------------------
# A — LOAD FROZEN RULE PACKAGE
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("A — LOAD FROZEN RESCUE REVIEW RULES")
print("=" * 80)

assert RULE_FILE.exists(), (
    f"Missing frozen rule package: {RULE_FILE}"
)

with open(RULE_FILE, "r") as f:
    frozen_rules = json.load(f)

print("Rule version:")
print(frozen_rules["rule_version"])

assert frozen_rules["status"] == "FROZEN"

print("Frozen Rescue Review rules available: PASSED")


# ------------------------------------------------------------
# B — VERIFY SAFETY CONTRACT
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("B — VERIFY FROZEN SAFETY CONTRACT")
print("=" * 80)

constraints = frozen_rules["constraints"]

assert constraints["ground_truth_used_for_calibration"] is False
assert constraints["may_change_primary_prediction"] is False
assert constraints["may_change_primary_probability"] is False
assert constraints["may_change_router_probability"] is False
assert constraints["may_change_router_selection"] is False
assert constraints["may_change_model_threshold"] is False
assert constraints["may_change_review_budget"] is False
assert constraints["may_diagnose"] is False
assert constraints["may_recommend_treatment"] is False
assert constraints["may_recommend_medication"] is False
assert constraints["human_review_required"] is True

print("Ground truth remains prohibited: PASSED")
print("Primary model remains frozen: PASSED")
print("Rescue Router remains frozen: PASSED")
print("Diagnosis remains prohibited: PASSED")
print("Treatment recommendation remains prohibited: PASSED")
print("Medication recommendation remains prohibited: PASSED")
print("Human review remains mandatory: PASSED")


# ------------------------------------------------------------
# C — APPROVED REASON CODES
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("C — APPROVED EXPLANATION SIGNALS")
print("=" * 80)

approved_reason_codes = list(
    frozen_rules["signal_rules"].keys()
)

# These two codes existed in the earlier output contract and may
# be used as summary-level explanation labels.
summary_reason_codes = [
    "MULTIPLE_RISK_SIGNALS",
    "LIMITED_RISK_SIGNALS",
]

approved_explanation_codes = (
    approved_reason_codes + summary_reason_codes
)

for code in approved_explanation_codes:
    print("-", code)

print(
    "\nExplanation Agent may explain only approved "
    "review signals: PASSED"
)


# ------------------------------------------------------------
# D — DEFINE EXPLANATION OUTPUT CONTRACT
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("D — DEFINE EXPLANATION OUTPUT CONTRACT")
print("=" * 80)

output_contract = {
    "contract_version": "10.4.1",
    "agent_name": "CareCompute Explanation Agent",
    "purpose": (
        "Generate a concise, non-diagnostic explanation of why an "
        "already-selected case received its Rescue Review priority."
    ),

    "required_fields": {
        "schema_version": "string",
        "encounter_id": "integer",

        "review_priority": [
            "LOW",
            "MODERATE",
            "HIGH",
        ],

        "explanation": "string <= 800 characters",

        "signal_explanations": (
            "list of structured explanations for approved reason codes"
        ),

        "uncertainty_statement": "string <= 300 characters",

        "human_review_statement": "string <= 300 characters",

        "safety_flag": "boolean",
    },

    "signal_explanation_schema": {
        "reason_code": approved_explanation_codes,
        "description": "string <= 250 characters",
    },

    "constraints": {
        "ground_truth_allowed": False,

        "diagnosis_allowed": False,
        "treatment_recommendation_allowed": False,
        "medication_recommendation_allowed": False,

        "prediction_modification_allowed": False,
        "probability_modification_allowed": False,
        "router_modification_allowed": False,
        "threshold_modification_allowed": False,
        "review_budget_modification_allowed": False,

        "new_clinical_fact_generation_allowed": False,

        "demographic_causal_explanation_allowed": False,

        "autonomous_clinical_action_allowed": False,

        "human_review_required": True,

        "maximum_signal_explanations": 5,
    },

    "prohibited_output_fields": [
        "diagnosis",
        "treatment",
        "medication",
        "prescription",

        "new_prediction",
        "predicted_outcome",
        "new_probability",

        "new_router_probability",
        "new_threshold",
        "new_router_selection",
        "new_review_budget",

        "actual_30d",
        "case_type",
        "router_target",
        "patient_nbr",
    ],
}

print(json.dumps(output_contract, indent=2))


# ------------------------------------------------------------
# E — SAVE OUTPUT CONTRACT
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("E — SAVE EXPLANATION OUTPUT CONTRACT")
print("=" * 80)

with open(OUTPUT_CONTRACT_FILE, "w") as f:
    json.dump(output_contract, f, indent=2)

print("Saved:")
print(OUTPUT_CONTRACT_FILE)


# ------------------------------------------------------------
# F — DEFINE SAFE SIGNAL DESCRIPTIONS
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("F — DEFINE SAFE SIGNAL DESCRIPTIONS")
print("=" * 80)

safe_signal_descriptions = {

    "NEAR_DECISION_THRESHOLD": (
        "The primary-model probability is relatively close to the "
        "frozen decision threshold."
    ),

    "HIGH_MODEL_DISAGREEMENT": (
        "The component model outputs show relatively elevated "
        "disagreement for this case."
    ),

    "HIGH_ROUTER_SCORE": (
        "The frozen Rescue Router assigned this case a relatively "
        "high review-prioritization score."
    ),

    "HIGH_DIAGNOSIS_BURDEN": (
        "The structured encounter record contains a relatively high "
        "number of recorded diagnoses."
    ),

    "HIGH_OUTPATIENT_UTILIZATION": (
        "The structured record indicates elevated recent outpatient "
        "utilization."
    ),

    "EMERGENCY_UTILIZATION": (
        "The structured record includes recent emergency utilization."
    ),

    "INPATIENT_UTILIZATION": (
        "The structured record includes recent inpatient utilization."
    ),

    "LONGER_HOSPITAL_STAY": (
        "The encounter has a relatively longer recorded hospital stay."
    ),

    "MULTIPLE_RISK_SIGNALS": (
        "Multiple approved review signals are present in the "
        "structured case context."
    ),

    "LIMITED_RISK_SIGNALS": (
        "Relatively few additional review signals are present within "
        "the approved explanation framework."
    ),
}

assert set(safe_signal_descriptions.keys()) == set(
    approved_explanation_codes
)

print("Safe description exists for every approved code: PASSED")


# ------------------------------------------------------------
# G — BUILD SAMPLE EXPLANATION
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("G — BUILD SAFE SAMPLE EXPLANATION")
print("=" * 80)

sample_output = {
    "schema_version": "10.4.1",
    "encounter_id": 192838872,

    "review_priority": "HIGH",

    "explanation": (
        "This case was prioritized within the existing human-review "
        "queue because multiple approved model and utilization signals "
        "were present. These signals support additional review but do "
        "not establish a diagnosis or clinical outcome."
    ),

    "signal_explanations": [
        {
            "reason_code": "HIGH_ROUTER_SCORE",
            "description": safe_signal_descriptions[
                "HIGH_ROUTER_SCORE"
            ],
        },
        {
            "reason_code": "HIGH_MODEL_DISAGREEMENT",
            "description": safe_signal_descriptions[
                "HIGH_MODEL_DISAGREEMENT"
            ],
        },
        {
            "reason_code": "HIGH_OUTPATIENT_UTILIZATION",
            "description": safe_signal_descriptions[
                "HIGH_OUTPATIENT_UTILIZATION"
            ],
        },
        {
            "reason_code": "MULTIPLE_RISK_SIGNALS",
            "description": safe_signal_descriptions[
                "MULTIPLE_RISK_SIGNALS"
            ],
        },
    ],

    "uncertainty_statement": (
        "These signals describe model behavior and structured "
        "utilization patterns; they do not determine the patient's "
        "true clinical outcome."
    ),

    "human_review_statement": (
        "A human reviewer should interpret these signals together "
        "with the appropriate clinical context."
    ),

    "safety_flag": False,
}

print(json.dumps(sample_output, indent=2))


# ------------------------------------------------------------
# H — VALIDATOR
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("H — DEFINE EXPLANATION VALIDATOR")
print("=" * 80)


def validate_explanation_output(output):

    errors = []

    required = [
        "schema_version",
        "encounter_id",
        "review_priority",
        "explanation",
        "signal_explanations",
        "uncertainty_statement",
        "human_review_statement",
        "safety_flag",
    ]

    for field in required:
        if field not in output:
            errors.append(
                f"Missing required field: {field}"
            )

    prohibited_fields = output_contract[
        "prohibited_output_fields"
    ]

    for field in prohibited_fields:
        if field in output:
            errors.append(
                f"Prohibited output field detected: {field}"
            )

    if output.get("review_priority") not in [
        "LOW",
        "MODERATE",
        "HIGH",
    ]:
        errors.append("Invalid review_priority.")

    explanation = output.get("explanation", "")

    if not isinstance(explanation, str):
        errors.append("Explanation must be a string.")
    elif len(explanation) > 800:
        errors.append(
            "Explanation exceeds 800 characters."
        )

    uncertainty = output.get(
        "uncertainty_statement",
        "",
    )

    if not isinstance(uncertainty, str):
        errors.append(
            "uncertainty_statement must be a string."
        )
    elif len(uncertainty) > 300:
        errors.append(
            "uncertainty_statement exceeds 300 characters."
        )

    human_statement = output.get(
        "human_review_statement",
        "",
    )

    if not isinstance(human_statement, str):
        errors.append(
            "human_review_statement must be a string."
        )
    elif len(human_statement) > 300:
        errors.append(
            "human_review_statement exceeds 300 characters."
        )

    signal_explanations = output.get(
        "signal_explanations",
        [],
    )

    if not isinstance(signal_explanations, list):
        errors.append(
            "signal_explanations must be a list."
        )

    else:

        if len(signal_explanations) > 5:
            errors.append(
                "Maximum five signal explanations allowed."
            )

        for item in signal_explanations:

            if not isinstance(item, dict):
                errors.append(
                    "Each signal explanation must be an object."
                )
                continue

            reason_code = item.get("reason_code")

            if reason_code not in approved_explanation_codes:
                errors.append(
                    f"Unapproved reason code: {reason_code}"
                )

            description = item.get(
                "description",
                "",
            )

            if not isinstance(description, str):
                errors.append(
                    "Signal description must be a string."
                )

            elif len(description) > 250:
                errors.append(
                    "Signal description exceeds 250 characters."
                )

    if not isinstance(
        output.get("safety_flag"),
        bool,
    ):
        errors.append(
            "safety_flag must be boolean."
        )

    return errors


# ------------------------------------------------------------
# I — VALIDATE SAFE SAMPLE
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("I — VALIDATE SAFE SAMPLE")
print("=" * 80)

sample_errors = validate_explanation_output(
    sample_output
)

if sample_errors:
    print("Errors:")
    for error in sample_errors:
        print("-", error)
    raise AssertionError(
        "Safe sample failed validation."
    )

print("Safe explanation satisfies contract: PASSED")


# ------------------------------------------------------------
# J — SAVE SAFE SAMPLE
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("J — SAVE SAFE SAMPLE")
print("=" * 80)

with open(SAMPLE_FILE, "w") as f:
    json.dump(sample_output, f, indent=2)

print("Saved:")
print(SAMPLE_FILE)


# ------------------------------------------------------------
# K — NEGATIVE TEST: DIAGNOSIS FIELD
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("K — NEGATIVE TEST: DIAGNOSIS FIELD")
print("=" * 80)

bad_output = sample_output.copy()
bad_output["diagnosis"] = "Example diagnosis"

errors = validate_explanation_output(
    bad_output
)

for error in errors:
    print("-", error)

assert any(
    "diagnosis" in error
    for error in errors
)

print("Diagnosis field blocked: PASSED")


# ------------------------------------------------------------
# L — NEGATIVE TEST: NEW PROBABILITY
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("L — NEGATIVE TEST: MODEL PROBABILITY OVERRIDE")
print("=" * 80)

bad_output = sample_output.copy()
bad_output["new_probability"] = 0.82

errors = validate_explanation_output(
    bad_output
)

for error in errors:
    print("-", error)

assert any(
    "new_probability" in error
    for error in errors
)

print("Probability override blocked: PASSED")


# ------------------------------------------------------------
# M — NEGATIVE TEST: GROUND TRUTH
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("M — NEGATIVE TEST: GROUND TRUTH")
print("=" * 80)

bad_output = sample_output.copy()
bad_output["actual_30d"] = 1

errors = validate_explanation_output(
    bad_output
)

for error in errors:
    print("-", error)

assert any(
    "actual_30d" in error
    for error in errors
)

print("Ground-truth output blocked: PASSED")


# ------------------------------------------------------------
# N — NEGATIVE TEST: UNAPPROVED REASON
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("N — NEGATIVE TEST: UNAPPROVED REASON CODE")
print("=" * 80)

bad_output = sample_output.copy()

bad_output["signal_explanations"] = [
    {
        "reason_code": "PATIENT_IS_SICK",
        "description": "Unsafe invented clinical interpretation.",
    }
]

errors = validate_explanation_output(
    bad_output
)

for error in errors:
    print("-", error)

assert any(
    "Unapproved reason code" in error
    for error in errors
)

print("Unapproved explanation signal blocked: PASSED")


# ------------------------------------------------------------
# O — DEFINE EXPLANATION POLICY
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("O — DEFINE EXPLANATION AGENT POLICY")
print("=" * 80)

policy = {
    "policy_version": "10.4.1",

    "agent_name": "CareCompute Explanation Agent",

    "role": (
        "Explain the approved signals underlying an already-assigned "
        "Rescue Review priority for human reviewers."
    ),

    "agent_must": [
        (
            "Use only approved signals produced by the frozen "
            "Rescue Review Agent rules."
        ),
        (
            "Describe signals using neutral and non-diagnostic "
            "language."
        ),
        (
            "Preserve the encounter identifier and assigned "
            "review priority."
        ),
        (
            "Clearly state that explanations support human review "
            "only."
        ),
        (
            "Communicate uncertainty and limitations."
        ),
        (
            "Use only information present in the approved "
            "structured context."
        ),
    ],

    "agent_must_not": [
        "Infer retrospective ground truth.",
        "Invent clinical facts.",
        "Diagnose a disease or condition.",
        "Recommend treatment.",
        "Recommend medication.",
        "Generate a new clinical risk probability.",
        "Override the frozen primary-model prediction.",
        "Change the Rescue Router score.",
        "Change router selection.",
        "Change the decision threshold.",
        "Change the review budget.",
        (
            "Claim that age, gender, or race caused the assigned "
            "priority."
        ),
        "Make an autonomous clinical decision.",
    ],

    "demographic_policy": {
        "demographics_may_be_displayed": True,
        "demographics_may_be_used_as_causal_explanation": False,
        "demographics_may_be_used_to_invent_risk": False,
    },

    "important_interpretation": (
        "An explanation describes why the deterministic review "
        "rules fired. It is not a diagnosis, prediction of the true "
        "outcome, or treatment recommendation."
    ),

    "human_review_required": True,
}

print(json.dumps(policy, indent=2))


# ------------------------------------------------------------
# P — SAVE POLICY
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("P — SAVE EXPLANATION POLICY")
print("=" * 80)

with open(POLICY_FILE, "w") as f:
    json.dump(policy, f, indent=2)

print("Saved:")
print(POLICY_FILE)


# ------------------------------------------------------------
# Q — RELOAD TEST
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("Q — CONTRACT RELOAD TEST")
print("=" * 80)

with open(OUTPUT_CONTRACT_FILE, "r") as f:
    reloaded_contract = json.load(f)

with open(POLICY_FILE, "r") as f:
    reloaded_policy = json.load(f)

assert (
    reloaded_contract["contract_version"]
    == "10.4.1"
)

assert (
    reloaded_policy["policy_version"]
    == "10.4.1"
)

print("Explanation output contract reload: PASSED")
print("Explanation policy reload: PASSED")


# ------------------------------------------------------------
# R — FINAL PERMISSION AUDIT
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("R — FINAL EXPLANATION PERMISSION AUDIT")
print("=" * 80)

c = output_contract["constraints"]

assert c["ground_truth_allowed"] is False
print("Ground truth prohibited: PASSED")

assert c["diagnosis_allowed"] is False
print("Diagnosis prohibited: PASSED")

assert c["treatment_recommendation_allowed"] is False
print("Treatment recommendation prohibited: PASSED")

assert c["medication_recommendation_allowed"] is False
print("Medication recommendation prohibited: PASSED")

assert c["prediction_modification_allowed"] is False
print("Prediction modification prohibited: PASSED")

assert c["probability_modification_allowed"] is False
print("Probability modification prohibited: PASSED")

assert c["router_modification_allowed"] is False
print("Router modification prohibited: PASSED")

assert c["threshold_modification_allowed"] is False
print("Threshold modification prohibited: PASSED")

assert c["review_budget_modification_allowed"] is False
print("Review-budget modification prohibited: PASSED")

assert c["new_clinical_fact_generation_allowed"] is False
print("Clinical fact invention prohibited: PASSED")

assert c["demographic_causal_explanation_allowed"] is False
print("Demographic causal explanation prohibited: PASSED")

assert c["autonomous_clinical_action_allowed"] is False
print("Autonomous clinical action prohibited: PASSED")

assert c["human_review_required"] is True
print("Human review mandatory: PASSED")


# ------------------------------------------------------------
# S — FINAL STATUS
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("S — FINAL STATUS")
print("=" * 80)

for path in [
    OUTPUT_CONTRACT_FILE,
    POLICY_FILE,
    SAMPLE_FILE,
]:
    assert path.exists()
    print(f"{path}: CREATED")

print("\n" + "=" * 80)
print("PHASE 10.4.1 COMPLETE — PASSED")
print("=" * 80)

print(
    "\nExplanation Agent contract established."
)

print(
    "The agent may explain only frozen, approved review signals."
)

print(
    "It may not diagnose, prescribe, invent clinical facts, "
    "or modify the ML/router system."
)

print(
    "Human review remains mandatory."
)

print("\nNEXT PHASE:")
print(
    "PHASE 10.4.2 — DETERMINISTIC EXPLANATION GENERATOR"
)