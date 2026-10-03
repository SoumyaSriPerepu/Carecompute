"""
CARECOMPUTE
PHASE 10.1 — AI AGENT ARCHITECTURE & CONTRACTS

Purpose
-------
Define the interface between the frozen CareCompute ML pipeline
and the future AI-agent layer.

IMPORTANT:
This phase does NOT modify:
- the primary model
- threshold
- Rescue Router
- review budget
- test predictions
- publication results
"""

from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
import json
import pandas as pd


# =============================================================================
# CONFIGURATION
# =============================================================================

INPUT_FILE = Path(
    "results/eligible/final_test_router_predictions.csv"
)

OUTPUT_DIR = Path(
    "results/eligible/agents"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

ARCHITECTURE_FILE = OUTPUT_DIR / "agent_architecture.json"
CONTRACT_FILE = OUTPUT_DIR / "agent_input_contract.json"
SAMPLE_CONTEXT_FILE = OUTPUT_DIR / "sample_agent_context.json"


# =============================================================================
# FROZEN SYSTEM CONSTANTS
# =============================================================================

FROZEN_MODEL_THRESHOLD = 0.115
FROZEN_REVIEW_BUDGET = 0.15

EXPECTED_LOW_RISK_ROWS = 7858

EXPECTED_ROUTER_FEATURES = [
    "calibrated_probability",
    "model_disagreement_std",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
]


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def section(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def passed(message: str):
    print(f"{message}: PASSED")


# =============================================================================
# DATA CONTRACT
# =============================================================================

@dataclass
class PatientAgentContext:

    # -------------------------------------------------------------------------
    # IDENTIFIERS
    # -------------------------------------------------------------------------

    encounter_id: int

    # -------------------------------------------------------------------------
    # PRIMARY MODEL
    # -------------------------------------------------------------------------

    calibrated_probability: float
    decision_threshold: float
    predicted_30d: int

    # -------------------------------------------------------------------------
    # MODEL UNCERTAINTY
    # -------------------------------------------------------------------------

    model_disagreement_std: float

    # -------------------------------------------------------------------------
    # UTILIZATION / CLINICAL CONTEXT
    # -------------------------------------------------------------------------

    number_diagnoses: int
    number_outpatient: int
    number_emergency: int
    number_inpatient: int
    time_in_hospital: int

    # -------------------------------------------------------------------------
    # ROUTER
    # -------------------------------------------------------------------------

    router_probability: float
    selected_for_review: int

    # -------------------------------------------------------------------------
    # DEMOGRAPHIC CONTEXT
    #
    # These fields may be useful for auditing/context but should NOT be used
    # by the LLM to independently infer clinical risk.
    # -------------------------------------------------------------------------

    age_group: str
    gender: str
    race: str


# =============================================================================
# AGENT OUTPUT CONTRACT
# =============================================================================

@dataclass
class AgentReviewOutput:

    encounter_id: int

    review_status: str

    case_summary: str

    routing_explanation: str

    uncertainty_summary: str

    important_signals: List[str]

    reviewer_attention_points: List[str]

    safety_flags: List[str]

    fairness_note: Optional[str]

    human_review_required: bool

    agent_version: str


# =============================================================================
# ARCHITECTURE DEFINITION
# =============================================================================

AGENT_ARCHITECTURE = {

    "system_name": "CareCompute",

    "version": "10.1",

    "pipeline_status": "Frozen ML + experimental agent layer",

    "frozen_ml_layer": {

        "decision_threshold": FROZEN_MODEL_THRESHOLD,

        "review_budget": FROZEN_REVIEW_BUDGET,

        "modifiable_by_agent": False,
    },

    "components": [

        {
            "name": "Patient Context Builder",
            "phase": "10.2",
            "responsibility":
                "Convert frozen structured model output into a safe "
                "agent-readable patient context.",
        },

        {
            "name": "Rescue Review Agent",
            "phase": "10.3",
            "responsibility":
                "Review cases selected by the frozen Rescue Router and "
                "produce structured human-review support.",
        },

        {
            "name": "Explanation Agent",
            "phase": "10.4",
            "responsibility":
                "Explain model/router signals without claiming causality "
                "or making autonomous clinical diagnoses.",
        },

        {
            "name": "Safety Guardrail",
            "phase": "10.5",
            "responsibility":
                "Validate agent outputs for unsupported clinical claims, "
                "unsafe recommendations, missing uncertainty language, "
                "and schema violations.",
        },

        {
            "name": "Fairness Monitor",
            "phase": "10.6",
            "responsibility":
                "Monitor review behavior and subgroup performance without "
                "allowing demographic attributes to become unsupported "
                "clinical risk explanations.",
        },

        {
            "name": "Agent Orchestrator",
            "phase": "10.7",
            "responsibility":
                "Coordinate context building, review, explanation, safety "
                "validation, and fairness monitoring.",
        },
    ],

    "agent_permissions": {

        "may_summarize_case": True,

        "may_explain_existing_model_signals": True,

        "may_flag_case_for_human_attention": True,

        "may_report_uncertainty": True,

        "may_generate_structured_review_notes": True,

        "may_change_model_prediction": False,

        "may_change_router_selection": False,

        "may_change_decision_threshold": False,

        "may_change_review_budget": False,

        "may_retrain_model": False,

        "may_make_autonomous_diagnosis": False,

        "may_make_autonomous_treatment_decision": False,
    },

    "human_in_the_loop": True,
}


# =============================================================================
# A — LOAD FROZEN ROUTER OUTPUT
# =============================================================================

section("PHASE 10.1 — CARECOMPUTE AI AGENT ARCHITECTURE")

section("A — LOAD FROZEN ROUTER OUTPUT")

if not INPUT_FILE.exists():

    raise FileNotFoundError(
        f"Frozen router file not found: {INPUT_FILE}"
    )

df = pd.read_csv(INPUT_FILE)

print("Input file:")
print(INPUT_FILE)

print("\nShape:")
print(df.shape)

print("\nColumns:")

for column in df.columns:
    print(" -", column)


# =============================================================================
# B — FROZEN POPULATION INTEGRITY
# =============================================================================

section("B — FROZEN POPULATION INTEGRITY")

if len(df) != EXPECTED_LOW_RISK_ROWS:

    raise AssertionError(
        f"Expected {EXPECTED_LOW_RISK_ROWS} low-risk rows, "
        f"found {len(df)}."
    )

passed(
    f"Low-risk population = {EXPECTED_LOW_RISK_ROWS}"
)


# =============================================================================
# C — REQUIRED COLUMN CHECK
# =============================================================================

section("C — AGENT INPUT COLUMN CHECK")

required_columns = [

    "encounter_id",

    "calibrated_probability",

    "predicted_30d",

    "model_disagreement_std",

    "number_diagnoses",

    "number_outpatient",

    "number_emergency",

    "number_inpatient",

    "time_in_hospital",

    "fn_router_probability",

    "selected_for_review",

    "age",

    "gender",

    "race",
]

missing_columns = [

    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:

    raise AssertionError(
        f"Missing required columns: {missing_columns}"
    )

passed("All required agent input columns present")


# =============================================================================
# D — FROZEN THRESHOLD CHECK
# =============================================================================

section("D — FROZEN MODEL CONTRACT")

if "threshold" not in df.columns:

    raise AssertionError(
        "Frozen threshold column missing."
    )

threshold_values = sorted(
    df["threshold"].dropna().unique().tolist()
)

print("Observed thresholds:")
print(threshold_values)

if len(threshold_values) != 1:

    raise AssertionError(
        "Multiple thresholds detected in frozen output."
    )

if abs(
    float(threshold_values[0])
    - FROZEN_MODEL_THRESHOLD
) > 1e-12:

    raise AssertionError(
        "Frozen threshold does not equal 0.115."
    )

passed("Frozen threshold = 0.115")


# =============================================================================
# E — LOW-RISK CONTRACT CHECK
# =============================================================================

section("E — LOW-RISK CONTRACT")

prediction_values = sorted(
    df["predicted_30d"].dropna().unique().tolist()
)

print("predicted_30d values:")
print(prediction_values)

if prediction_values != [0]:

    raise AssertionError(
        "Agent router dataset contains patients outside "
        "the frozen low-risk population."
    )

passed("All router cases are primary-model low-risk predictions")


# =============================================================================
# F — ROUTER SELECTION CHECK
# =============================================================================

section("F — FROZEN ROUTER SELECTION")

selected = int(
    df["selected_for_review"].sum()
)

print("Selected for review:")
print(selected)

expected_selected = 1178

if selected != expected_selected:

    raise AssertionError(
        f"Expected {expected_selected} selected cases, "
        f"found {selected}."
    )

passed("Frozen Rescue Router selected 1,178 patients")


# =============================================================================
# G — AGENT ELIGIBILITY
# =============================================================================

section("G — AGENT ELIGIBILITY")

agent_cases = df[
    df["selected_for_review"] == 1
].copy()

print("Cases eligible for Rescue Review Agent:")
print(len(agent_cases))

if len(agent_cases) != 1178:

    raise AssertionError(
        "Agent eligibility population does not match "
        "the frozen review population."
    )

passed("Agent eligibility matches frozen review population")


# =============================================================================
# H — ROUTER FEATURE CHECK
# =============================================================================

section("H — ROUTER FEATURE CONTRACT")

for feature in EXPECTED_ROUTER_FEATURES:

    if feature not in df.columns:

        raise AssertionError(
            f"Frozen router feature missing: {feature}"
        )

    print(feature, "FOUND")

passed("Frozen router features preserved")


# =============================================================================
# I — BUILD SAMPLE AGENT CONTEXT
# =============================================================================

section("I — BUILD SAMPLE AGENT CONTEXT")

sample = agent_cases.iloc[0]

sample_context = PatientAgentContext(

    encounter_id=int(
        sample["encounter_id"]
    ),

    calibrated_probability=float(
        sample["calibrated_probability"]
    ),

    decision_threshold=FROZEN_MODEL_THRESHOLD,

    predicted_30d=int(
        sample["predicted_30d"]
    ),

    model_disagreement_std=float(
        sample["model_disagreement_std"]
    ),

    number_diagnoses=int(
        sample["number_diagnoses"]
    ),

    number_outpatient=int(
        sample["number_outpatient"]
    ),

    number_emergency=int(
        sample["number_emergency"]
    ),

    number_inpatient=int(
        sample["number_inpatient"]
    ),

    time_in_hospital=int(
        sample["time_in_hospital"]
    ),

    router_probability=float(
        sample["fn_router_probability"]
    ),

    selected_for_review=int(
        sample["selected_for_review"]
    ),

    age_group=str(
        sample["age"]
    ),

    gender=str(
        sample["gender"]
    ),

    race=str(
        sample["race"]
    ),
)

sample_context_dict = asdict(
    sample_context
)

print(
    json.dumps(
        sample_context_dict,
        indent=2
    )
)


# =============================================================================
# J — PRIVACY / LABEL LEAKAGE CONTRACT
# =============================================================================

section("J — PRIVACY AND LABEL-LEAKAGE CONTRACT")

# These columns exist for retrospective evaluation,
# but should NOT be passed into the generative review agent.

PROHIBITED_AGENT_FIELDS = [

    "actual_30d",

    "case_type",

    "router_target",

    "patient_nbr",
]

print("Fields prohibited from generative agent context:")

for field in PROHIBITED_AGENT_FIELDS:
    print(" -", field)

sample_fields = set(
    sample_context_dict.keys()
)

leaked_fields = [

    field
    for field in PROHIBITED_AGENT_FIELDS
    if field in sample_fields
]

if leaked_fields:

    raise AssertionError(
        f"Outcome/privacy leakage detected: {leaked_fields}"
    )

passed("No ground-truth outcome leakage in agent context")
passed("patient_nbr excluded from agent context")


# =============================================================================
# K — SAVE AGENT ARCHITECTURE
# =============================================================================

section("K — SAVE AGENT ARCHITECTURE")

with open(
    ARCHITECTURE_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        AGENT_ARCHITECTURE,
        f,
        indent=2
    )

print("Saved:")
print(ARCHITECTURE_FILE)


# =============================================================================
# L — SAVE INPUT CONTRACT
# =============================================================================

section("L — SAVE AGENT INPUT CONTRACT")

input_contract = {

    "contract_version": "10.1",

    "source_file":
        str(INPUT_FILE),

    "eligible_population":
        "Frozen Rescue Router selected cases",

    "expected_cases":
        1178,

    "frozen_threshold":
        FROZEN_MODEL_THRESHOLD,

    "frozen_review_budget":
        FROZEN_REVIEW_BUDGET,

    "allowed_fields":
        list(
            PatientAgentContext.__dataclass_fields__.keys()
        ),

    "prohibited_fields":
        PROHIBITED_AGENT_FIELDS,

    "router_features":
        EXPECTED_ROUTER_FEATURES,

    "ground_truth_available_to_agent":
        False,

    "human_review_required":
        True,
}

with open(
    CONTRACT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        input_contract,
        f,
        indent=2
    )

print(
    json.dumps(
        input_contract,
        indent=2
    )
)

print("\nSaved:")
print(CONTRACT_FILE)


# =============================================================================
# M — SAVE SAMPLE CONTEXT
# =============================================================================

section("M — SAVE SAMPLE AGENT CONTEXT")

with open(
    SAMPLE_CONTEXT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        sample_context_dict,
        f,
        indent=2
    )

print("Saved:")
print(SAMPLE_CONTEXT_FILE)


# =============================================================================
# N — AGENT PERMISSION AUDIT
# =============================================================================

section("N — AGENT PERMISSION AUDIT")

permissions = AGENT_ARCHITECTURE[
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

    value = permissions[permission]

    print(
        f"{permission}: {value}"
    )

    if value is not False:

        raise AssertionError(
            f"Unsafe permission enabled: {permission}"
        )

passed("Agent cannot modify frozen ML system")
passed("Agent cannot autonomously diagnose")
passed("Agent cannot autonomously select treatment")


# =============================================================================
# O — FINAL ARCHITECTURE SUMMARY
# =============================================================================

section("O — CARECOMPUTE AGENT ARCHITECTURE")

print(
    """
PATIENT ENCOUNTER
       |
       v
+-------------------------+
| FROZEN PRIMARY MODEL    |
| threshold = 0.115       |
+------------+------------+
             |
             | predicted low risk
             v
+-------------------------+
| FROZEN RESCUE ROUTER    |
| review budget = 15%     |
+------------+------------+
             |
             | selected_for_review = 1
             v
+-------------------------+
| PATIENT CONTEXT BUILDER |
| Phase 10.2              |
+------------+------------+
             |
             v
+-------------------------+
| RESCUE REVIEW AGENT     |
| Phase 10.3              |
+------------+------------+
             |
             v
+-------------------------+
| EXPLANATION AGENT       |
| Phase 10.4              |
+------------+------------+
             |
             v
+-------------------------+
| SAFETY GUARDRAIL        |
| Phase 10.5              |
+------------+------------+
             |
             v
+-------------------------+
| FAIRNESS MONITOR        |
| Phase 10.6              |
+------------+------------+
             |
             v
+-------------------------+
| HUMAN REVIEWER          |
+-------------------------+

IMPORTANT:

The AI-agent layer supports review.

It does NOT replace the frozen model.

It does NOT change the frozen router.

It does NOT see the retrospective ground-truth outcome.

It does NOT autonomously diagnose or prescribe treatment.
"""
)


# =============================================================================
# P — FINAL STATUS
# =============================================================================

section("P — FINAL STATUS")

generated_files = [

    ARCHITECTURE_FILE,

    CONTRACT_FILE,

    SAMPLE_CONTEXT_FILE,
]

for file in generated_files:

    if not file.exists():

        raise AssertionError(
            f"Expected output was not created: {file}"
        )

    print(
        f"{file}: CREATED"
    )


print("\n" + "=" * 80)
print("PHASE 10.1 COMPLETE — PASSED")
print("=" * 80)

print(
    "\nFrozen ML → Agent boundary successfully established."
)

print(
    "Ground-truth outcome leakage prevented."
)

print(
    "Human-in-the-loop requirement established."
)

print(
    "\nNEXT PHASE:"
)

print(
    "PHASE 10.2 — PATIENT CASE CONTEXT BUILDER"
)