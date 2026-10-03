"""
CARECOMPUTE
PHASE 10.3.2 — DETERMINISTIC LOCAL AGENT SIMULATION

Purpose
-------
Run all frozen Rescue Router-selected cases through a deterministic,
rule-based simulation of the Rescue Review Agent.

This phase:
- uses only approved Phase 10.2 context
- does NOT use an LLM
- does NOT use ground truth
- does NOT modify predictions or router selection
- produces outputs conforming to the Phase 10.3.1 contract
"""

from pathlib import Path
import json
from collections import Counter

import pandas as pd


# =============================================================================
# CONFIGURATION
# =============================================================================

INPUT_FILE = Path(
    "results/eligible/agents/patient_agent_contexts.jsonl"
)

OUTPUT_CONTRACT_FILE = Path(
    "results/eligible/agents/rescue_review_agent_output_contract.json"
)

OUTPUT_DIR = Path(
    "results/eligible/agents"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_JSONL = (
    OUTPUT_DIR / "local_agent_outputs.jsonl"
)

OUTPUT_CSV = (
    OUTPUT_DIR / "local_agent_outputs.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR / "local_agent_simulation_summary.json"
)

EXPECTED_CASES = 1178


# =============================================================================
# FIXED LOCAL-AGENT RULES
# =============================================================================

NEAR_THRESHOLD_DISTANCE = 0.015

HIGH_DISAGREEMENT = 0.12

HIGH_ROUTER_SCORE = 0.75

HIGH_DIAGNOSIS_BURDEN = 8

HIGH_OUTPATIENT_UTILIZATION = 5

LONG_HOSPITAL_STAY = 5


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

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                records.append(json.loads(line))

    return records


# =============================================================================
# LOCAL AGENT
# =============================================================================

def run_local_agent(context):
    """
    Deterministic Rescue Review Agent.

    IMPORTANT:
    Uses only approved fields from the Phase 10.2 packet.
    """

    encounter_id = int(
        context["encounter"]["encounter_id"]
    )

    primary = context["primary_model"]
    uncertainty = context["uncertainty"]
    utilization = context["utilization_context"]
    router = context["router_context"]

    distance = float(
        primary["distance_below_threshold"]
    )

    disagreement = float(
        uncertainty["model_disagreement_std"]
    )

    router_probability = float(
        router["fn_router_probability"]
    )

    diagnoses = int(
        utilization["number_diagnoses"]
    )

    outpatient = int(
        utilization["number_outpatient"]
    )

    emergency = int(
        utilization["number_emergency"]
    )

    inpatient = int(
        utilization["number_inpatient"]
    )

    hospital_days = int(
        utilization["time_in_hospital"]
    )

    reason_codes = []

    # -------------------------------------------------------------------------
    # Risk signal detection
    # -------------------------------------------------------------------------

    if distance <= NEAR_THRESHOLD_DISTANCE:
        reason_codes.append(
            "NEAR_DECISION_THRESHOLD"
        )

    if disagreement >= HIGH_DISAGREEMENT:
        reason_codes.append(
            "HIGH_MODEL_DISAGREEMENT"
        )

    if router_probability >= HIGH_ROUTER_SCORE:
        reason_codes.append(
            "HIGH_ROUTER_SCORE"
        )

    if diagnoses >= HIGH_DIAGNOSIS_BURDEN:
        reason_codes.append(
            "HIGH_DIAGNOSIS_BURDEN"
        )

    if outpatient >= HIGH_OUTPATIENT_UTILIZATION:
        reason_codes.append(
            "HIGH_OUTPATIENT_UTILIZATION"
        )

    if emergency > 0:
        reason_codes.append(
            "EMERGENCY_UTILIZATION"
        )

    if inpatient > 0:
        reason_codes.append(
            "INPATIENT_UTILIZATION"
        )

    if hospital_days >= LONG_HOSPITAL_STAY:
        reason_codes.append(
            "LONGER_HOSPITAL_STAY"
        )

    # -------------------------------------------------------------------------
    # Count independent signals before adding summary codes
    # -------------------------------------------------------------------------

    signal_count = len(reason_codes)

    if signal_count >= 3:
        reason_codes.append(
            "MULTIPLE_RISK_SIGNALS"
        )

    elif signal_count <= 1:
        reason_codes.append(
            "LIMITED_RISK_SIGNALS"
        )

    # Contract permits maximum 5 codes.
    reason_codes = reason_codes[:5]

    # -------------------------------------------------------------------------
    # Priority
    # -------------------------------------------------------------------------

    strong_signal_count = sum([
        distance <= NEAR_THRESHOLD_DISTANCE,
        disagreement >= HIGH_DISAGREEMENT,
        router_probability >= HIGH_ROUTER_SCORE,
        emergency > 0,
        inpatient > 0,
    ])

    if (
        router_probability >= HIGH_ROUTER_SCORE
        and strong_signal_count >= 3
    ):
        review_priority = "HIGH"

    elif signal_count >= 3:
        review_priority = "MODERATE"

    else:
        review_priority = "LOW"

    # -------------------------------------------------------------------------
    # Human-review action
    # -------------------------------------------------------------------------

    if review_priority == "HIGH":
        human_review_action = (
            "PRIORITY_REVIEW"
        )
    else:
        human_review_action = (
            "ROUTINE_REVIEW"
        )

    # -------------------------------------------------------------------------
    # Uncertainty
    # -------------------------------------------------------------------------

    uncertainty_flag = bool(
        disagreement >= HIGH_DISAGREEMENT
    )

    # -------------------------------------------------------------------------
    # Confidence in the AGENT SUMMARY
    #
    # This is NOT clinical confidence.
    # -------------------------------------------------------------------------

    if signal_count >= 4:
        confidence = "HIGH"

    elif signal_count >= 2:
        confidence = "MEDIUM"

    else:
        confidence = "LOW"

    # -------------------------------------------------------------------------
    # Human-readable summary
    # -------------------------------------------------------------------------

    signal_phrases = []

    if "NEAR_DECISION_THRESHOLD" in reason_codes:
        signal_phrases.append(
            "the primary-model probability is close to the frozen decision threshold"
        )

    if "HIGH_MODEL_DISAGREEMENT" in reason_codes:
        signal_phrases.append(
            "model disagreement is elevated"
        )

    if "HIGH_ROUTER_SCORE" in reason_codes:
        signal_phrases.append(
            "the frozen Rescue Router score is elevated"
        )

    if "HIGH_DIAGNOSIS_BURDEN" in reason_codes:
        signal_phrases.append(
            "the recorded diagnosis count is elevated"
        )

    if "HIGH_OUTPATIENT_UTILIZATION" in reason_codes:
        signal_phrases.append(
            "outpatient utilization is elevated"
        )

    if "EMERGENCY_UTILIZATION" in reason_codes:
        signal_phrases.append(
            "prior emergency utilization is present"
        )

    if "INPATIENT_UTILIZATION" in reason_codes:
        signal_phrases.append(
            "prior inpatient utilization is present"
        )

    if "LONGER_HOSPITAL_STAY" in reason_codes:
        signal_phrases.append(
            "the hospital stay is relatively long"
        )

    if len(signal_phrases) == 0:
        summary = (
            "The frozen Rescue Router selected this case for human review. "
            "The available structured signals are limited, so routine human "
            "review remains appropriate."
        )

    else:
        summary = (
            "The frozen Rescue Router selected this case for human review because "
            + "; ".join(signal_phrases)
            + ". This summary identifies review signals only and does not provide "
              "a diagnosis or treatment recommendation."
        )

    # Keep safely below contract maximum.
    summary = summary[:600]

    # -------------------------------------------------------------------------
    # Final output
    # -------------------------------------------------------------------------

    output = {
        "schema_version": "10.3.1",
        "encounter_id": encounter_id,
        "review_priority": review_priority,
        "risk_signal_summary": summary,
        "reason_codes": reason_codes,
        "uncertainty_flag": uncertainty_flag,
        "human_review_action": human_review_action,
        "confidence": confidence,
        "safety_flag": False,
    }

    return output


# =============================================================================
# OUTPUT VALIDATOR
# =============================================================================

def validate_output(output, contract):
    errors = []

    required = [
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

    for field in required:
        if field not in output:
            errors.append(
                f"Missing field: {field}"
            )

    if errors:
        return errors

    if output["schema_version"] != "10.3.1":
        errors.append(
            "Invalid schema version"
        )

    if output["review_priority"] not in [
        "LOW",
        "MODERATE",
        "HIGH",
    ]:
        errors.append(
            "Invalid review priority"
        )

    if output["human_review_action"] not in [
        "ROUTINE_REVIEW",
        "PRIORITY_REVIEW",
    ]:
        errors.append(
            "Invalid human review action"
        )

    if output["confidence"] not in [
        "LOW",
        "MEDIUM",
        "HIGH",
    ]:
        errors.append(
            "Invalid confidence"
        )

    if not isinstance(
        output["uncertainty_flag"],
        bool
    ):
        errors.append(
            "uncertainty_flag not boolean"
        )

    if not isinstance(
        output["safety_flag"],
        bool
    ):
        errors.append(
            "safety_flag not boolean"
        )

    if len(output["reason_codes"]) > 5:
        errors.append(
            "Too many reason codes"
        )

    if len(output["reason_codes"]) == 0:
        errors.append(
            "No reason codes"
        )

    if len(output["risk_signal_summary"]) > 600:
        errors.append(
            "Summary too long"
        )

    prohibited = contract[
        "prohibited_output_fields"
    ]

    for field in prohibited:
        if field in output:
            errors.append(
                f"Prohibited field: {field}"
            )

    return errors


# =============================================================================
# START
# =============================================================================

section(
    "PHASE 10.3.2 — DETERMINISTIC LOCAL AGENT SIMULATION"
)


# =============================================================================
# A — LOAD INPUTS
# =============================================================================

section("A — LOAD INPUTS")

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        INPUT_FILE
    )

if not OUTPUT_CONTRACT_FILE.exists():
    raise FileNotFoundError(
        OUTPUT_CONTRACT_FILE
    )

contexts = load_jsonl(
    INPUT_FILE
)

with open(
    OUTPUT_CONTRACT_FILE,
    "r",
    encoding="utf-8"
) as f:
    contract = json.load(f)

print(
    "Patient contexts:",
    len(contexts)
)

print(
    "Output contract version:",
    contract["contract_version"]
)

if len(contexts) != EXPECTED_CASES:
    raise AssertionError(
        f"Expected {EXPECTED_CASES} contexts."
    )

passed(
    "Expected frozen agent population"
)


# =============================================================================
# B — INPUT SAFETY AUDIT
# =============================================================================

section("B — INPUT SAFETY AUDIT")

prohibited_input_fields = [
    "actual_30d",
    "case_type",
    "router_target",
    "patient_nbr",
]

raw_text = json.dumps(
    contexts
)

for field in prohibited_input_fields:

    if f'"{field}"' in raw_text:
        raise AssertionError(
            f"Prohibited input detected: {field}"
        )

    passed(
        f"{field} absent"
    )


# =============================================================================
# C — RUN LOCAL AGENT
# =============================================================================

section("C — RUN LOCAL AGENT")

outputs = []

validation_failures = []

for index, context in enumerate(
    contexts,
    start=1
):

    output = run_local_agent(
        context
    )

    errors = validate_output(
        output,
        contract
    )

    if errors:
        validation_failures.append({
            "encounter_id":
                output.get(
                    "encounter_id"
                ),
            "errors":
                errors,
        })

    outputs.append(
        output
    )

    if index % 100 == 0:
        print(
            f"Processed {index}/{EXPECTED_CASES}"
        )

print(
    f"Processed {len(outputs)}/{EXPECTED_CASES}"
)

if validation_failures:
    print(
        json.dumps(
            validation_failures[:10],
            indent=2
        )
    )

    raise AssertionError(
        f"{len(validation_failures)} outputs "
        "failed contract validation."
    )

passed(
    "All outputs satisfy Phase 10.3.1 contract"
)


# =============================================================================
# D — OUTPUT COUNT
# =============================================================================

section("D — OUTPUT COUNT")

print(
    "Agent outputs:",
    len(outputs)
)

if len(outputs) != EXPECTED_CASES:
    raise AssertionError(
        "Output count mismatch."
    )

passed(
    "Exactly 1,178 agent outputs generated"
)


# =============================================================================
# E — ENCOUNTER INTEGRITY
# =============================================================================

section("E — ENCOUNTER INTEGRITY")

input_ids = [
    int(
        x["encounter"]["encounter_id"]
    )
    for x in contexts
]

output_ids = [
    int(
        x["encounter_id"]
    )
    for x in outputs
]

if input_ids != output_ids:
    raise AssertionError(
        "Encounter ordering or IDs changed."
    )

passed(
    "Encounter IDs preserved"
)

if len(set(output_ids)) != EXPECTED_CASES:
    raise AssertionError(
        "Duplicate encounter IDs detected."
    )

passed(
    "Encounter IDs unique"
)


# =============================================================================
# F — PRIORITY DISTRIBUTION
# =============================================================================

section("F — PRIORITY DISTRIBUTION")

priority_counts = Counter(
    x["review_priority"]
    for x in outputs
)

for key in [
    "HIGH",
    "MODERATE",
    "LOW",
]:
    print(
        f"{key}:",
        priority_counts.get(
            key,
            0
        )
    )

if sum(priority_counts.values()) != EXPECTED_CASES:
    raise AssertionError(
        "Priority distribution mismatch."
    )

passed(
    "Priority distribution complete"
)


# =============================================================================
# G — HUMAN REVIEW ACTION DISTRIBUTION
# =============================================================================

section(
    "G — HUMAN REVIEW ACTION DISTRIBUTION"
)

action_counts = Counter(
    x["human_review_action"]
    for x in outputs
)

for action, count in action_counts.items():
    print(
        f"{action}: {count}"
    )

if sum(action_counts.values()) != EXPECTED_CASES:
    raise AssertionError(
        "Action distribution mismatch."
    )

passed(
    "Every case remains assigned to human review"
)


# =============================================================================
# H — UNCERTAINTY DISTRIBUTION
# =============================================================================

section("H — UNCERTAINTY DISTRIBUTION")

uncertainty_counts = Counter(
    x["uncertainty_flag"]
    for x in outputs
)

print(
    "Uncertainty flag TRUE:",
    uncertainty_counts.get(
        True,
        0
    )
)

print(
    "Uncertainty flag FALSE:",
    uncertainty_counts.get(
        False,
        0
    )
)

passed(
    "Uncertainty flags generated"
)


# =============================================================================
# I — CONFIDENCE DISTRIBUTION
# =============================================================================

section("I — CONFIDENCE DISTRIBUTION")

confidence_counts = Counter(
    x["confidence"]
    for x in outputs
)

for confidence, count in confidence_counts.items():
    print(
        f"{confidence}: {count}"
    )

passed(
    "Agent-summary confidence generated"
)


# =============================================================================
# J — REASON CODE FREQUENCIES
# =============================================================================

section("J — REASON CODE FREQUENCIES")

reason_counter = Counter()

for output in outputs:
    for code in output["reason_codes"]:
        reason_counter[code] += 1

for code, count in reason_counter.most_common():
    print(
        f"{code}: {count}"
    )


# =============================================================================
# K — SAFETY FLAGS
# =============================================================================

section("K — SAFETY FLAGS")

safety_counts = Counter(
    x["safety_flag"]
    for x in outputs
)

print(
    "Safety flag FALSE:",
    safety_counts.get(
        False,
        0
    )
)

print(
    "Safety flag TRUE:",
    safety_counts.get(
        True,
        0
    )
)

if safety_counts.get(
    True,
    0
) != 0:
    raise AssertionError(
        "Unexpected safety flags in deterministic simulation."
    )

passed(
    "No local-agent safety violations"
)


# =============================================================================
# L — SAVE JSONL
# =============================================================================

section("L — SAVE JSONL")

with open(
    OUTPUT_JSONL,
    "w",
    encoding="utf-8"
) as f:

    for output in outputs:
        f.write(
            json.dumps(
                output
            )
            + "\n"
        )

print(
    "Saved:"
)

print(
    OUTPUT_JSONL
)


# =============================================================================
# M — SAVE FLAT CSV
# =============================================================================

section("M — SAVE FLAT CSV")

flat_rows = []

for output in outputs:

    flat_rows.append({
        "schema_version":
            output["schema_version"],

        "encounter_id":
            output["encounter_id"],

        "review_priority":
            output["review_priority"],

        "risk_signal_summary":
            output["risk_signal_summary"],

        "reason_codes":
            "|".join(
                output["reason_codes"]
            ),

        "uncertainty_flag":
            output["uncertainty_flag"],

        "human_review_action":
            output["human_review_action"],

        "confidence":
            output["confidence"],

        "safety_flag":
            output["safety_flag"],
    })

output_df = pd.DataFrame(
    flat_rows
)

output_df.to_csv(
    OUTPUT_CSV,
    index=False
)

print(
    "CSV shape:",
    output_df.shape
)

print(
    "Saved:"
)

print(
    OUTPUT_CSV
)


# =============================================================================
# N — SAMPLE OUTPUTS
# =============================================================================

section("N — SAMPLE OUTPUTS")

sample_indices = [
    0,
    len(outputs) // 2,
    len(outputs) - 1,
]

for idx in sample_indices:

    print(
        "\nSample:"
    )

    print(
        json.dumps(
            outputs[idx],
            indent=2
        )
    )


# =============================================================================
# O — DETERMINISM TEST
# =============================================================================

section("O — DETERMINISM TEST")

second_pass = [
    run_local_agent(context)
    for context in contexts
]

if outputs != second_pass:
    raise AssertionError(
        "Local agent is not deterministic."
    )

passed(
    "Repeated run produces identical outputs"
)


# =============================================================================
# P — GROUND-TRUTH LEAKAGE AUDIT
# =============================================================================

section(
    "P — GROUND-TRUTH LEAKAGE AUDIT"
)

serialized_outputs = json.dumps(
    outputs
)

for field in [
    "actual_30d",
    "case_type",
    "router_target",
    "patient_nbr",
]:

    if f'"{field}"' in serialized_outputs:
        raise AssertionError(
            f"Leakage detected: {field}"
        )

    passed(
        f"{field} absent from outputs"
    )


# =============================================================================
# Q — MODEL / ROUTER OVERRIDE AUDIT
# =============================================================================

section(
    "Q — MODEL / ROUTER OVERRIDE AUDIT"
)

for field in [
    "new_prediction",
    "predicted_outcome",
    "new_probability",
    "new_router_probability",
    "new_threshold",
    "new_router_selection",
]:

    if f'"{field}"' in serialized_outputs:
        raise AssertionError(
            f"Override field detected: {field}"
        )

    passed(
        f"{field} absent"
    )


# =============================================================================
# R — SAVE SUMMARY
# =============================================================================

section("R — SAVE SUMMARY")

summary = {
    "phase":
        "10.3.2",

    "agent_type":
        "deterministic_local_simulation",

    "cases_processed":
        len(outputs),

    "priority_distribution":
        dict(priority_counts),

    "human_review_action_distribution":
        dict(action_counts),

    "uncertainty_distribution": {
        str(k): v
        for k, v
        in uncertainty_counts.items()
    },

    "confidence_distribution":
        dict(confidence_counts),

    "reason_code_frequency":
        dict(reason_counter),

    "safety_flag_true":
        safety_counts.get(
            True,
            0
        ),

    "ground_truth_used":
        False,

    "llm_used":
        False,

    "model_prediction_modified":
        False,

    "router_selection_modified":
        False,

    "human_review_required":
        True,

    "rules": {
        "near_threshold_distance":
            NEAR_THRESHOLD_DISTANCE,

        "high_disagreement":
            HIGH_DISAGREEMENT,

        "high_router_score":
            HIGH_ROUTER_SCORE,

        "high_diagnosis_burden":
            HIGH_DIAGNOSIS_BURDEN,

        "high_outpatient_utilization":
            HIGH_OUTPATIENT_UTILIZATION,

        "long_hospital_stay":
            LONG_HOSPITAL_STAY,
    },

    "output_files": [
        str(OUTPUT_JSONL),
        str(OUTPUT_CSV),
    ],
}

with open(
    SUMMARY_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        summary,
        f,
        indent=2
    )

print(
    json.dumps(
        summary,
        indent=2
    )
)

print(
    "\nSaved:"
)

print(
    SUMMARY_FILE
)


# =============================================================================
# S — OUTPUT REPRODUCTION
# =============================================================================

section("S — OUTPUT REPRODUCTION")

reloaded_df = pd.read_csv(
    OUTPUT_CSV
)

reloaded_jsonl = load_jsonl(
    OUTPUT_JSONL
)

print(
    "Reloaded CSV shape:",
    reloaded_df.shape
)

print(
    "Reloaded JSONL:",
    len(reloaded_jsonl)
)

if len(reloaded_df) != EXPECTED_CASES:
    raise AssertionError(
        "CSV reproduction failed."
    )

if len(reloaded_jsonl) != EXPECTED_CASES:
    raise AssertionError(
        "JSONL reproduction failed."
    )

passed(
    "CSV reproduction"
)

passed(
    "JSONL reproduction"
)


# =============================================================================
# T — FINAL STATUS
# =============================================================================

section("T — FINAL STATUS")

for path in [
    OUTPUT_JSONL,
    OUTPUT_CSV,
    SUMMARY_FILE,
]:

    if not path.exists():
        raise AssertionError(
            f"Missing output: {path}"
        )

    print(
        f"{path}: CREATED"
    )

print("\n" + "=" * 80)

print(
    "PHASE 10.3.2 COMPLETE — PASSED"
)

print("=" * 80)

print(
    "\nAll 1,178 frozen Rescue Router cases "
    "processed by deterministic local agent."
)

print(
    "All outputs conform to the Phase 10.3.1 contract."
)

print(
    "No ground truth was used."
)

print(
    "No frozen ML prediction or router selection was changed."
)

print(
    "No external LLM/API was used."
)

print(
    "\nNEXT PHASE:"
)

print(
    "PHASE 10.3.3 — LOCAL AGENT QUALITY / SAFETY AUDIT"
)