"""
CARECOMPUTE
PHASE 10.3.1 — RESCUE REVIEW AGENT OUTPUT CONTRACT

Purpose
-------
Define and validate the structured output contract for the
CareCompute Rescue Review Agent.

IMPORTANT:
This phase does NOT call an LLM.

The agent:
- supports human review
- cannot diagnose
- cannot prescribe treatment
- cannot modify the frozen ML prediction
- cannot modify the Rescue Router selection
- cannot see retrospective ground truth
"""

from pathlib import Path
import json
import pandas as pd


# =============================================================================
# CONFIGURATION
# =============================================================================

INPUT_FILE = Path(
    "results/eligible/agents/patient_agent_contexts.jsonl"
)

INPUT_CONTRACT_FILE = Path(
    "results/eligible/agents/agent_input_contract.json"
)

OUTPUT_DIR = Path(
    "results/eligible/agents"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_CONTRACT_FILE = (
    OUTPUT_DIR / "rescue_review_agent_output_contract.json"
)

SAMPLE_OUTPUT_FILE = (
    OUTPUT_DIR / "sample_rescue_review_agent_output.json"
)

POLICY_FILE = (
    OUTPUT_DIR / "rescue_review_agent_policy.json"
)


EXPECTED_CASES = 1178


# =============================================================================
# ALLOWED ENUMS
# =============================================================================

REVIEW_PRIORITIES = [
    "LOW",
    "MODERATE",
    "HIGH",
]

HUMAN_REVIEW_ACTIONS = [
    "ROUTINE_REVIEW",
    "PRIORITY_REVIEW",
]

CONFIDENCE_LEVELS = [
    "LOW",
    "MEDIUM",
    "HIGH",
]


# =============================================================================
# ALLOWED REASON CODES
# =============================================================================

REASON_CODES = [

    "NEAR_DECISION_THRESHOLD",

    "HIGH_MODEL_DISAGREEMENT",

    "HIGH_ROUTER_SCORE",

    "HIGH_DIAGNOSIS_BURDEN",

    "HIGH_OUTPATIENT_UTILIZATION",

    "EMERGENCY_UTILIZATION",

    "INPATIENT_UTILIZATION",

    "LONGER_HOSPITAL_STAY",

    "MULTIPLE_RISK_SIGNALS",

    "LIMITED_RISK_SIGNALS",
]


# =============================================================================
# PROHIBITED OUTPUT CONCEPTS
# =============================================================================

PROHIBITED_OUTPUT_FIELDS = [

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

    "actual_30d",

    "case_type",

    "router_target",

    "patient_nbr",
]


# =============================================================================
# HELPERS
# =============================================================================

def section(title):

    print("\n" + "=" * 80)

    print(title)

    print("=" * 80)


def passed(message):

    print(f"{message}: PASSED")


def load_jsonl(path):

    records = []

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            line = line.strip()

            if line:

                records.append(
                    json.loads(line)
                )

    return records


# =============================================================================
# OUTPUT VALIDATOR
# =============================================================================

def validate_agent_output(output):

    """
    Validate one Rescue Review Agent response.

    Returns:
        list of validation errors
    """

    errors = []

    # -------------------------------------------------------------------------
    # Required top-level fields
    # -------------------------------------------------------------------------

    required_fields = [

        "schema_version",

        "encounter_id",

        "review_priority",

        "risk_signal_summary",

        "reason_codes",

        "uncertainty_flag",

        "human_review_action",

        "confidence",

        "safety_flag",
    ]

    for field in required_fields:

        if field not in output:

            errors.append(
                f"Missing required field: {field}"
            )

    if errors:

        return errors

    # -------------------------------------------------------------------------
    # Schema version
    # -------------------------------------------------------------------------

    if output["schema_version"] != "10.3.1":

        errors.append(
            "Invalid schema_version."
        )

    # -------------------------------------------------------------------------
    # Encounter ID
    # -------------------------------------------------------------------------

    if not isinstance(
        output["encounter_id"],
        int
    ):

        errors.append(
            "encounter_id must be an integer."
        )

    # -------------------------------------------------------------------------
    # Review priority
    # -------------------------------------------------------------------------

    if (
        output["review_priority"]
        not in REVIEW_PRIORITIES
    ):

        errors.append(
            "Invalid review_priority."
        )

    # -------------------------------------------------------------------------
    # Risk summary
    # -------------------------------------------------------------------------

    summary = output[
        "risk_signal_summary"
    ]

    if not isinstance(
        summary,
        str
    ):

        errors.append(
            "risk_signal_summary must be a string."
        )

    elif len(summary.strip()) == 0:

        errors.append(
            "risk_signal_summary cannot be empty."
        )

    elif len(summary) > 600:

        errors.append(
            "risk_signal_summary exceeds 600 characters."
        )

    # -------------------------------------------------------------------------
    # Reason codes
    # -------------------------------------------------------------------------

    reason_codes = output[
        "reason_codes"
    ]

    if not isinstance(
        reason_codes,
        list
    ):

        errors.append(
            "reason_codes must be a list."
        )

    else:

        if len(reason_codes) == 0:

            errors.append(
                "At least one reason code is required."
            )

        if len(reason_codes) > 5:

            errors.append(
                "Maximum five reason codes allowed."
            )

        for code in reason_codes:

            if code not in REASON_CODES:

                errors.append(
                    f"Invalid reason code: {code}"
                )

        if len(reason_codes) != len(set(reason_codes)):

            errors.append(
                "Duplicate reason codes detected."
            )

    # -------------------------------------------------------------------------
    # Boolean fields
    # -------------------------------------------------------------------------

    if not isinstance(
        output["uncertainty_flag"],
        bool
    ):

        errors.append(
            "uncertainty_flag must be boolean."
        )

    if not isinstance(
        output["safety_flag"],
        bool
    ):

        errors.append(
            "safety_flag must be boolean."
        )

    # -------------------------------------------------------------------------
    # Human review action
    # -------------------------------------------------------------------------

    if (
        output["human_review_action"]
        not in HUMAN_REVIEW_ACTIONS
    ):

        errors.append(
            "Invalid human_review_action."
        )

    # -------------------------------------------------------------------------
    # Confidence
    # -------------------------------------------------------------------------

    if (
        output["confidence"]
        not in CONFIDENCE_LEVELS
    ):

        errors.append(
            "Invalid confidence level."
        )

    # -------------------------------------------------------------------------
    # Prohibited fields
    # -------------------------------------------------------------------------

    for prohibited in PROHIBITED_OUTPUT_FIELDS:

        if prohibited in output:

            errors.append(
                f"Prohibited output field detected: {prohibited}"
            )

    return errors


# =============================================================================
# START
# =============================================================================

section(
    "PHASE 10.3.1 — RESCUE REVIEW AGENT OUTPUT CONTRACT"
)


# =============================================================================
# A — LOAD PHASE 10.2 CONTEXTS
# =============================================================================

section("A — LOAD PHASE 10.2 CONTEXTS")

if not INPUT_FILE.exists():

    raise FileNotFoundError(
        f"Missing context file: {INPUT_FILE}"
    )

contexts = load_jsonl(
    INPUT_FILE
)

print(
    "Patient contexts:",
    len(contexts)
)

if len(contexts) != EXPECTED_CASES:

    raise AssertionError(
        f"Expected {EXPECTED_CASES} contexts, "
        f"found {len(contexts)}."
    )

passed(
    "1,178 Phase 10.2 contexts available"
)


# =============================================================================
# B — VERIFY INPUT CONTRACT
# =============================================================================

section("B — VERIFY INPUT CONTRACT")

if not INPUT_CONTRACT_FILE.exists():

    raise FileNotFoundError(
        f"Missing input contract: {INPUT_CONTRACT_FILE}"
    )

with open(
    INPUT_CONTRACT_FILE,
    "r",
    encoding="utf-8"
) as f:

    input_contract = json.load(f)

print(
    "Input contract version:",
    input_contract["contract_version"]
)

if (
    input_contract[
        "ground_truth_available_to_agent"
    ]
    is not False
):

    raise AssertionError(
        "Ground truth unexpectedly available."
    )

passed(
    "Ground truth remains unavailable to agent"
)

if (
    input_contract[
        "human_review_required"
    ]
    is not True
):

    raise AssertionError(
        "Human-review requirement missing."
    )

passed(
    "Human review remains mandatory"
)


# =============================================================================
# C — DEFINE OUTPUT SCHEMA
# =============================================================================

section("C — DEFINE OUTPUT SCHEMA")

output_contract = {

    "contract_version":
        "10.3.1",

    "agent_name":
        "CareCompute Rescue Review Agent",

    "purpose":
        (
            "Summarize structured risk signals "
            "for cases already selected by the "
            "frozen Rescue Router and prioritize "
            "human review."
        ),

    "required_fields": {

        "schema_version":
            "string",

        "encounter_id":
            "integer",

        "review_priority":
            REVIEW_PRIORITIES,

        "risk_signal_summary":
            "string <= 600 characters",

        "reason_codes":
            REASON_CODES,

        "uncertainty_flag":
            "boolean",

        "human_review_action":
            HUMAN_REVIEW_ACTIONS,

        "confidence":
            CONFIDENCE_LEVELS,

        "safety_flag":
            "boolean",
    },

    "constraints": {

        "maximum_reason_codes":
            5,

        "ground_truth_allowed":
            False,

        "diagnosis_allowed":
            False,

        "treatment_recommendation_allowed":
            False,

        "medication_recommendation_allowed":
            False,

        "prediction_modification_allowed":
            False,

        "probability_modification_allowed":
            False,

        "router_modification_allowed":
            False,

        "threshold_modification_allowed":
            False,

        "autonomous_clinical_action_allowed":
            False,

        "human_review_required":
            True,
    },

    "prohibited_output_fields":
        PROHIBITED_OUTPUT_FIELDS,
}

print(
    json.dumps(
        output_contract,
        indent=2
    )
)


# =============================================================================
# D — SAVE OUTPUT CONTRACT
# =============================================================================

section("D — SAVE OUTPUT CONTRACT")

with open(
    OUTPUT_CONTRACT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output_contract,
        f,
        indent=2
    )

print("Saved:")

print(
    OUTPUT_CONTRACT_FILE
)


# =============================================================================
# E — BUILD SAFE SAMPLE OUTPUT
# =============================================================================

section("E — BUILD SAFE SAMPLE OUTPUT")

sample_context = contexts[0]

encounter_id = (
    sample_context[
        "encounter"
    ][
        "encounter_id"
    ]
)

sample_output = {

    "schema_version":
        "10.3.1",

    "encounter_id":
        encounter_id,

    "review_priority":
        "HIGH",

    "risk_signal_summary":
        (
            "This case was selected for human review "
            "because multiple model and utilization "
            "signals warrant additional attention. "
            "The summary supports review only and "
            "does not provide a diagnosis."
        ),

    "reason_codes": [

        "HIGH_ROUTER_SCORE",

        "HIGH_MODEL_DISAGREEMENT",

        "HIGH_OUTPATIENT_UTILIZATION",

        "MULTIPLE_RISK_SIGNALS",
    ],

    "uncertainty_flag":
        True,

    "human_review_action":
        "PRIORITY_REVIEW",

    "confidence":
        "MEDIUM",

    "safety_flag":
        False,
}

print(
    json.dumps(
        sample_output,
        indent=2
    )
)


# =============================================================================
# F — VALIDATE SAFE SAMPLE
# =============================================================================

section("F — VALIDATE SAFE SAMPLE")

sample_errors = validate_agent_output(
    sample_output
)

if sample_errors:

    print(
        "Validation errors:"
    )

    for error in sample_errors:

        print(
            "-",
            error
        )

    raise AssertionError(
        "Safe sample output failed validation."
    )

passed(
    "Safe sample satisfies output contract"
)


# =============================================================================
# G — SAVE SAFE SAMPLE
# =============================================================================

section("G — SAVE SAFE SAMPLE")

with open(
    SAMPLE_OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        sample_output,
        f,
        indent=2
    )

print("Saved:")

print(
    SAMPLE_OUTPUT_FILE
)


# =============================================================================
# H — NEGATIVE TEST: DIAGNOSIS FIELD
# =============================================================================

section(
    "H — NEGATIVE TEST: PROHIBITED DIAGNOSIS FIELD"
)

bad_diagnosis = (
    sample_output.copy()
)

bad_diagnosis[
    "diagnosis"
] = "Example prohibited diagnosis"

errors = validate_agent_output(
    bad_diagnosis
)

print(
    "Errors detected:"
)

for error in errors:

    print(
        "-",
        error
    )

if not any(
    "diagnosis" in error
    for error in errors
):

    raise AssertionError(
        "Validator failed to block diagnosis."
    )

passed(
    "Diagnosis field blocked"
)


# =============================================================================
# I — NEGATIVE TEST: NEW PREDICTION
# =============================================================================

section(
    "I — NEGATIVE TEST: MODEL OVERRIDE"
)

bad_prediction = (
    sample_output.copy()
)

bad_prediction[
    "new_prediction"
] = 1

errors = validate_agent_output(
    bad_prediction
)

for error in errors:

    print(
        "-",
        error
    )

if not any(
    "new_prediction" in error
    for error in errors
):

    raise AssertionError(
        "Validator failed to block prediction override."
    )

passed(
    "Prediction override blocked"
)


# =============================================================================
# J — NEGATIVE TEST: INVALID PRIORITY
# =============================================================================

section(
    "J — NEGATIVE TEST: INVALID PRIORITY"
)

bad_priority = (
    sample_output.copy()
)

bad_priority[
    "review_priority"
] = "CRITICAL"

errors = validate_agent_output(
    bad_priority
)

for error in errors:

    print(
        "-",
        error
    )

if not any(
    "review_priority" in error
    for error in errors
):

    raise AssertionError(
        "Invalid priority was not blocked."
    )

passed(
    "Unapproved priority blocked"
)


# =============================================================================
# K — NEGATIVE TEST: TOO MANY REASON CODES
# =============================================================================

section(
    "K — NEGATIVE TEST: TOO MANY REASON CODES"
)

bad_reasons = (
    sample_output.copy()
)

bad_reasons[
    "reason_codes"
] = REASON_CODES[:6]

errors = validate_agent_output(
    bad_reasons
)

for error in errors:

    print(
        "-",
        error
    )

if not any(
    "Maximum five" in error
    for error in errors
):

    raise AssertionError(
        "Reason-code limit was not enforced."
    )

passed(
    "Reason-code limit enforced"
)


# =============================================================================
# L — NEGATIVE TEST: GROUND TRUTH
# =============================================================================

section(
    "L — NEGATIVE TEST: GROUND-TRUTH OUTPUT"
)

bad_ground_truth = (
    sample_output.copy()
)

bad_ground_truth[
    "actual_30d"
] = 1

errors = validate_agent_output(
    bad_ground_truth
)

for error in errors:

    print(
        "-",
        error
    )

if not any(
    "actual_30d" in error
    for error in errors
):

    raise AssertionError(
        "Ground-truth output was not blocked."
    )

passed(
    "Ground-truth field blocked"
)


# =============================================================================
# M — DEFINE AGENT POLICY
# =============================================================================

section("M — DEFINE RESCUE REVIEW AGENT POLICY")

agent_policy = {

    "policy_version":
        "10.3.1",

    "agent_name":
        "CareCompute Rescue Review Agent",

    "role":
        (
            "Decision-support agent for human review "
            "of cases already selected by the frozen "
            "Rescue Router."
        ),

    "agent_must": [

        "Use only fields supplied in the approved patient context.",

        "Summarize observable model and utilization signals.",

        "Return output conforming to the structured output contract.",

        "Keep the original encounter_id unchanged.",

        "Treat every case as requiring human review.",

        "Express uncertainty when evidence is limited or mixed.",

        "Use neutral non-diagnostic language.",
    ],

    "agent_must_not": [

        "Infer or reveal retrospective ground truth.",

        "Diagnose a disease or condition.",

        "Recommend medication.",

        "Recommend treatment.",

        "Override the frozen primary model.",

        "Generate a replacement model probability.",

        "Change the Rescue Router score.",

        "Change router selection.",

        "Change the decision threshold.",

        "Change the review budget.",

        "Make an autonomous clinical decision.",
    ],

    "priority_meaning": {

        "LOW":
            (
                "Selected case has relatively limited "
                "additional review signals."
            ),

        "MODERATE":
            (
                "Selected case contains multiple or "
                "meaningful signals that warrant review."
            ),

        "HIGH":
            (
                "Selected case contains strong or "
                "multiple review signals and should be "
                "prioritized within the human review queue."
            ),
    },

    "human_review_actions": {

        "ROUTINE_REVIEW":
            (
                "Keep the case in the normal human "
                "review workflow."
            ),

        "PRIORITY_REVIEW":
            (
                "Move the already-selected case earlier "
                "within the human review workflow."
            ),
    },

    "important_interpretation":
        (
            "Review priority is not a diagnosis, "
            "predicted clinical outcome, or treatment "
            "recommendation."
        ),
}

print(
    json.dumps(
        agent_policy,
        indent=2
    )
)

with open(
    POLICY_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        agent_policy,
        f,
        indent=2
    )

print("\nSaved:")

print(
    POLICY_FILE
)


# =============================================================================
# N — CONTRACT RELOAD TEST
# =============================================================================

section("N — CONTRACT RELOAD TEST")

with open(
    OUTPUT_CONTRACT_FILE,
    "r",
    encoding="utf-8"
) as f:

    reloaded_contract = json.load(f)

if (
    reloaded_contract[
        "contract_version"
    ]
    != "10.3.1"
):

    raise AssertionError(
        "Output contract version changed."
    )

passed(
    "Output contract reload"
)

with open(
    POLICY_FILE,
    "r",
    encoding="utf-8"
) as f:

    reloaded_policy = json.load(f)

if (
    reloaded_policy[
        "policy_version"
    ]
    != "10.3.1"
):

    raise AssertionError(
        "Agent policy version changed."
    )

passed(
    "Agent policy reload"
)


# =============================================================================
# O — FINAL PERMISSION AUDIT
# =============================================================================

section("O — FINAL AGENT PERMISSION AUDIT")

constraints = output_contract[
    "constraints"
]

checks = {

    "Ground truth prohibited":
        constraints["ground_truth_allowed"] is False,

    "Diagnosis prohibited":
        constraints["diagnosis_allowed"] is False,

    "Treatment recommendation prohibited":
        constraints[
            "treatment_recommendation_allowed"
        ] is False,

    "Medication recommendation prohibited":
        constraints[
            "medication_recommendation_allowed"
        ] is False,

    "Prediction modification prohibited":
        constraints[
            "prediction_modification_allowed"
        ] is False,

    "Probability modification prohibited":
        constraints[
            "probability_modification_allowed"
        ] is False,

    "Router modification prohibited":
        constraints[
            "router_modification_allowed"
        ] is False,

    "Threshold modification prohibited":
        constraints[
            "threshold_modification_allowed"
        ] is False,

    "Autonomous clinical action prohibited":
        constraints[
            "autonomous_clinical_action_allowed"
        ] is False,

    "Human review mandatory":
        constraints[
            "human_review_required"
        ] is True,
}

for name, result in checks.items():

    if not result:

        raise AssertionError(
            f"Permission audit failed: {name}"
        )

    passed(name)


# =============================================================================
# P — FINAL STATUS
# =============================================================================

section("P — FINAL STATUS")

expected_outputs = [

    OUTPUT_CONTRACT_FILE,

    SAMPLE_OUTPUT_FILE,

    POLICY_FILE,
]

for output in expected_outputs:

    if not output.exists():

        raise AssertionError(
            f"Missing output: {output}"
        )

    print(
        f"{output}: CREATED"
    )


print("\n" + "=" * 80)

print(
    "PHASE 10.3.1 COMPLETE — PASSED"
)

print("=" * 80)

print(
    "\nRescue Review Agent output contract frozen."
)

print(
    "Agent may prioritize and summarize review signals."
)

print(
    "Agent may NOT diagnose, prescribe, "
    "change predictions, or modify the frozen router."
)

print(
    "Human review remains mandatory."
)

print(
    "\nNEXT PHASE:"
)

print(
    "PHASE 10.3.2 — DETERMINISTIC LOCAL AGENT SIMULATION"
)