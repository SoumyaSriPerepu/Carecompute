"""
CARECOMPUTE
PHASE 10.2 — PATIENT CASE CONTEXT BUILDER

Purpose
-------
Transform the 1,178 cases selected by the frozen Rescue Router into
structured, privacy-conscious case packets for the future AI-agent layer.

This phase does NOT call an LLM.

It does NOT expose:
- actual_30d
- case_type
- router_target
- patient_nbr

It does NOT change:
- model predictions
- threshold
- router scores
- router selections
- review budget
"""

from pathlib import Path
import json
import math
import pandas as pd


# =============================================================================
# CONFIGURATION
# =============================================================================

INPUT_FILE = Path(
    "results/eligible/final_test_router_predictions.csv"
)

CONTRACT_FILE = Path(
    "results/eligible/agents/agent_input_contract.json"
)

OUTPUT_DIR = Path(
    "results/eligible/agents"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CONTEXT_CSV = OUTPUT_DIR / "patient_agent_contexts.csv"

CONTEXT_JSONL = OUTPUT_DIR / "patient_agent_contexts.jsonl"

SUMMARY_FILE = OUTPUT_DIR / "patient_context_builder_summary.json"

SAMPLE_FILE = OUTPUT_DIR / "sample_patient_context_packet.json"


EXPECTED_LOW_RISK_ROWS = 7858
EXPECTED_REVIEW_CASES = 1178
FROZEN_THRESHOLD = 0.115
FROZEN_REVIEW_BUDGET = 0.15


PROHIBITED_FIELDS = [
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


def safe_int(value):
    if pd.isna(value):
        return None
    return int(value)


def safe_float(value):
    if pd.isna(value):
        return None
    return float(value)


def safe_string(value):
    if pd.isna(value):
        return "Missing"
    return str(value)


def json_safe(value):
    """
    Convert pandas/numpy values into JSON-safe Python values.
    """

    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        return value.item()

    return value


# =============================================================================
# CONTEXT BUILDER
# =============================================================================

def build_patient_context(row):
    """
    Build the exact context packet that may later be passed
    to the generative review agent.

    Ground-truth labels are intentionally excluded.
    """

    probability = safe_float(
        row["calibrated_probability"]
    )

    disagreement = safe_float(
        row["model_disagreement_std"]
    )

    router_probability = safe_float(
        row["fn_router_probability"]
    )

    # -------------------------------------------------------------------------
    # Distance from frozen model threshold
    # -------------------------------------------------------------------------

    if probability is None:
        distance_to_threshold = None
    else:
        distance_to_threshold = (
            FROZEN_THRESHOLD - probability
        )

    # -------------------------------------------------------------------------
    # Structured context
    # -------------------------------------------------------------------------

    context = {

        "schema_version": "10.2",

        "encounter": {

            "encounter_id":
                safe_int(row["encounter_id"]),

        },

        "primary_model": {

            "predicted_30d":
                safe_int(row["predicted_30d"]),

            "calibrated_probability":
                probability,

            "decision_threshold":
                FROZEN_THRESHOLD,

            "distance_below_threshold":
                distance_to_threshold,

        },

        "uncertainty": {

            "model_disagreement_std":
                disagreement,

        },

        "utilization_context": {

            "number_diagnoses":
                safe_int(row["number_diagnoses"]),

            "number_outpatient":
                safe_int(row["number_outpatient"]),

            "number_emergency":
                safe_int(row["number_emergency"]),

            "number_inpatient":
                safe_int(row["number_inpatient"]),

            "time_in_hospital":
                safe_int(row["time_in_hospital"]),

        },

        "router_context": {

            "fn_router_probability":
                router_probability,

            "selected_for_review":
                safe_int(row["selected_for_review"]),

            "review_budget":
                FROZEN_REVIEW_BUDGET,

        },

        "demographic_context": {

            "age_group":
                safe_string(row["age"]),

            "gender":
                safe_string(row["gender"]),

            "race":
                safe_string(row["race"]),

        },

        "agent_constraints": {

            "ground_truth_available":
                False,

            "may_change_model_prediction":
                False,

            "may_change_router_selection":
                False,

            "may_make_diagnosis":
                False,

            "may_recommend_treatment":
                False,

            "human_review_required":
                True,

        },

    }

    return context


# =============================================================================
# FLATTEN CONTEXT FOR CSV
# =============================================================================

def flatten_context(context):

    return {

        "schema_version":
            context["schema_version"],

        "encounter_id":
            context["encounter"]["encounter_id"],

        "predicted_30d":
            context["primary_model"]["predicted_30d"],

        "calibrated_probability":
            context["primary_model"]["calibrated_probability"],

        "decision_threshold":
            context["primary_model"]["decision_threshold"],

        "distance_below_threshold":
            context["primary_model"]["distance_below_threshold"],

        "model_disagreement_std":
            context["uncertainty"]["model_disagreement_std"],

        "number_diagnoses":
            context["utilization_context"]["number_diagnoses"],

        "number_outpatient":
            context["utilization_context"]["number_outpatient"],

        "number_emergency":
            context["utilization_context"]["number_emergency"],

        "number_inpatient":
            context["utilization_context"]["number_inpatient"],

        "time_in_hospital":
            context["utilization_context"]["time_in_hospital"],

        "fn_router_probability":
            context["router_context"]["fn_router_probability"],

        "selected_for_review":
            context["router_context"]["selected_for_review"],

        "review_budget":
            context["router_context"]["review_budget"],

        "age_group":
            context["demographic_context"]["age_group"],

        "gender":
            context["demographic_context"]["gender"],

        "race":
            context["demographic_context"]["race"],

    }


# =============================================================================
# A — LOAD INPUTS
# =============================================================================

section(
    "PHASE 10.2 — PATIENT CASE CONTEXT BUILDER"
)

section("A — LOAD FROZEN INPUTS")

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Missing frozen router file: {INPUT_FILE}"
    )

if not CONTRACT_FILE.exists():
    raise FileNotFoundError(
        f"Missing Phase 10.1 contract: {CONTRACT_FILE}"
    )

df = pd.read_csv(INPUT_FILE)

with open(
    CONTRACT_FILE,
    "r",
    encoding="utf-8"
) as f:
    contract = json.load(f)

print("Router input shape:")
print(df.shape)

print("\nContract version:")
print(contract["contract_version"])


# =============================================================================
# B — INPUT INTEGRITY
# =============================================================================

section("B — INPUT INTEGRITY")

if len(df) != EXPECTED_LOW_RISK_ROWS:
    raise AssertionError(
        f"Expected {EXPECTED_LOW_RISK_ROWS} rows, "
        f"found {len(df)}."
    )

passed(
    f"Frozen low-risk population = {EXPECTED_LOW_RISK_ROWS}"
)

if contract["expected_cases"] != EXPECTED_REVIEW_CASES:
    raise AssertionError(
        "Phase 10.1 contract expected-case count changed."
    )

passed(
    "Phase 10.1 contract preserved"
)


# =============================================================================
# C — SELECT FROZEN ROUTER CASES
# =============================================================================

section("C — SELECT FROZEN ROUTER CASES")

review_df = df[
    df["selected_for_review"] == 1
].copy()

print("Selected cases:")
print(len(review_df))

if len(review_df) != EXPECTED_REVIEW_CASES:
    raise AssertionError(
        f"Expected {EXPECTED_REVIEW_CASES} review cases, "
        f"found {len(review_df)}."
    )

passed("Exactly 1,178 frozen review cases selected")

if not (
    review_df["predicted_30d"] == 0
).all():

    raise AssertionError(
        "Review population contains non-low-risk predictions."
    )

passed("All agent cases remain primary-model low risk")


# =============================================================================
# D — ENCOUNTER INTEGRITY
# =============================================================================

section("D — ENCOUNTER INTEGRITY")

missing_encounters = int(
    review_df["encounter_id"].isna().sum()
)

duplicate_encounters = int(
    review_df["encounter_id"].duplicated().sum()
)

print("Missing encounter IDs:")
print(missing_encounters)

print("Duplicate encounter IDs:")
print(duplicate_encounters)

if missing_encounters != 0:
    raise AssertionError(
        "Missing encounter IDs detected."
    )

if duplicate_encounters != 0:
    raise AssertionError(
        "Duplicate encounter IDs detected."
    )

passed("Encounter IDs complete and unique")


# =============================================================================
# E — BUILD ALL CONTEXT PACKETS
# =============================================================================

section("E — BUILD PATIENT CONTEXT PACKETS")

contexts = []

for _, row in review_df.iterrows():

    context = build_patient_context(row)

    contexts.append(context)

print("Contexts built:")
print(len(contexts))

if len(contexts) != EXPECTED_REVIEW_CASES:
    raise AssertionError(
        "Context count does not match review population."
    )

passed("1,178 patient contexts created")


# =============================================================================
# F — GROUND-TRUTH LEAKAGE AUDIT
# =============================================================================

section("F — GROUND-TRUTH LEAKAGE AUDIT")

serialized_contexts = json.dumps(
    contexts
)

for prohibited in PROHIBITED_FIELDS:

    if f'"{prohibited}"' in serialized_contexts:

        raise AssertionError(
            f"Prohibited field leaked into contexts: {prohibited}"
        )

    print(
        f"{prohibited}: NOT PRESENT"
    )

passed("No prohibited fields leaked into agent contexts")


# =============================================================================
# G — MODEL CONTRACT AUDIT
# =============================================================================

section("G — FROZEN MODEL CONTRACT AUDIT")

for context in contexts:

    if (
        context["primary_model"]["decision_threshold"]
        != FROZEN_THRESHOLD
    ):
        raise AssertionError(
            "Threshold mutation detected."
        )

    if (
        context["primary_model"]["predicted_30d"]
        != 0
    ):
        raise AssertionError(
            "Prediction mutation detected."
        )

    if (
        context["router_context"]["selected_for_review"]
        != 1
    ):
        raise AssertionError(
            "Router selection mutation detected."
        )

passed("Frozen threshold preserved")
passed("Frozen prediction preserved")
passed("Frozen router selection preserved")


# =============================================================================
# H — VALUE RANGE CHECKS
# =============================================================================

section("H — VALUE RANGE CHECKS")

probabilities = [
    c["primary_model"]["calibrated_probability"]
    for c in contexts
    if c["primary_model"]["calibrated_probability"]
    is not None
]

router_probabilities = [
    c["router_context"]["fn_router_probability"]
    for c in contexts
    if c["router_context"]["fn_router_probability"]
    is not None
]

if not all(
    0 <= value <= 1
    for value in probabilities
):
    raise AssertionError(
        "Invalid calibrated probability detected."
    )

if not all(
    0 <= value <= 1
    for value in router_probabilities
):
    raise AssertionError(
        "Invalid router probability detected."
    )

passed("Primary probabilities within [0, 1]")
passed("Router probabilities within [0, 1]")


# =============================================================================
# I — DISTANCE-TO-THRESHOLD CHECK
# =============================================================================

section("I — DISTANCE-TO-THRESHOLD CHECK")

distances = [
    c["primary_model"]["distance_below_threshold"]
    for c in contexts
    if c["primary_model"]["distance_below_threshold"]
    is not None
]

negative_distances = [
    value
    for value in distances
    if value < -1e-12
]

print(
    "Minimum distance below threshold:",
    min(distances)
)

print(
    "Maximum distance below threshold:",
    max(distances)
)

if negative_distances:

    raise AssertionError(
        "Low-risk case found above frozen threshold."
    )

passed(
    "All selected cases remain below/equal to frozen threshold"
)


# =============================================================================
# J — MISSING VALUE AUDIT
# =============================================================================

section("J — MISSING VALUE AUDIT")

flat_contexts = [
    flatten_context(context)
    for context in contexts
]

flat_df = pd.DataFrame(
    flat_contexts
)

missing_summary = (
    flat_df
    .isna()
    .sum()
    .sort_values(
        ascending=False
    )
)

print(
    missing_summary.to_string()
)

critical_fields = [
    "encounter_id",
    "calibrated_probability",
    "decision_threshold",
    "predicted_30d",
    "fn_router_probability",
    "selected_for_review",
]

for field in critical_fields:

    if flat_df[field].isna().any():

        raise AssertionError(
            f"Critical field contains missing values: {field}"
        )

passed("No missing values in critical agent fields")


# =============================================================================
# K — CONTEXT STATISTICS
# =============================================================================

section("K — CONTEXT STATISTICS")

print(
    "Primary probability range:"
)

print(
    f"{flat_df['calibrated_probability'].min():.6f}"
    f" to "
    f"{flat_df['calibrated_probability'].max():.6f}"
)

print(
    "\nRouter probability range:"
)

print(
    f"{flat_df['fn_router_probability'].min():.6f}"
    f" to "
    f"{flat_df['fn_router_probability'].max():.6f}"
)

print(
    "\nModel disagreement range:"
)

print(
    f"{flat_df['model_disagreement_std'].min():.6f}"
    f" to "
    f"{flat_df['model_disagreement_std'].max():.6f}"
)

print(
    "\nAge distribution:"
)

print(
    flat_df["age_group"]
    .value_counts(dropna=False)
    .sort_index()
)

print(
    "\nGender distribution:"
)

print(
    flat_df["gender"]
    .value_counts(dropna=False)
)

print(
    "\nRace distribution:"
)

print(
    flat_df["race"]
    .value_counts(dropna=False)
)


# =============================================================================
# L — SAVE CSV
# =============================================================================

section("L — SAVE FLAT CONTEXT CSV")

flat_df.to_csv(
    CONTEXT_CSV,
    index=False
)

print("Saved:")
print(CONTEXT_CSV)


# =============================================================================
# M — SAVE JSONL
# =============================================================================

section("M — SAVE STRUCTURED JSONL")

with open(
    CONTEXT_JSONL,
    "w",
    encoding="utf-8"
) as f:

    for context in contexts:

        f.write(
            json.dumps(
                context,
                ensure_ascii=False
            )
            + "\n"
        )

print("Saved:")
print(CONTEXT_JSONL)


# =============================================================================
# N — SAVE SAMPLE PACKET
# =============================================================================

section("N — SAMPLE AGENT PACKET")

sample_context = contexts[0]

print(
    json.dumps(
        sample_context,
        indent=2
    )
)

with open(
    SAMPLE_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        sample_context,
        f,
        indent=2
    )

print("\nSaved:")
print(SAMPLE_FILE)


# =============================================================================
# O — SAVE SUMMARY
# =============================================================================

section("O — SAVE CONTEXT BUILDER SUMMARY")

summary = {

    "phase": "10.2",

    "source_rows":
        int(len(df)),

    "agent_eligible_cases":
        int(len(contexts)),

    "frozen_threshold":
        FROZEN_THRESHOLD,

    "frozen_review_budget":
        FROZEN_REVIEW_BUDGET,

    "ground_truth_exposed":
        False,

    "patient_identifier_exposed":
        False,

    "prediction_modification_allowed":
        False,

    "router_modification_allowed":
        False,

    "human_review_required":
        True,

    "output_files": [
        str(CONTEXT_CSV),
        str(CONTEXT_JSONL),
        str(SAMPLE_FILE),
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

print("\nSaved:")
print(SUMMARY_FILE)


# =============================================================================
# P — OUTPUT REPRODUCTION CHECK
# =============================================================================

section("P — OUTPUT REPRODUCTION CHECK")

reloaded_csv = pd.read_csv(
    CONTEXT_CSV
)

print(
    "Reloaded CSV shape:",
    reloaded_csv.shape
)

if len(reloaded_csv) != EXPECTED_REVIEW_CASES:

    raise AssertionError(
        "Saved CSV does not contain 1,178 cases."
    )

with open(
    CONTEXT_JSONL,
    "r",
    encoding="utf-8"
) as f:

    jsonl_lines = [
        line
        for line in f
        if line.strip()
    ]

print(
    "JSONL records:",
    len(jsonl_lines)
)

if len(jsonl_lines) != EXPECTED_REVIEW_CASES:

    raise AssertionError(
        "Saved JSONL does not contain 1,178 cases."
    )

passed("CSV reproduction")
passed("JSONL reproduction")


# =============================================================================
# Q — FINAL SAFETY CHECK
# =============================================================================

section("Q — FINAL SAFETY CHECK")

for prohibited in PROHIBITED_FIELDS:

    if prohibited in flat_df.columns:

        raise AssertionError(
            f"Prohibited column found in CSV: {prohibited}"
        )

passed("actual_30d excluded")
passed("case_type excluded")
passed("router_target excluded")
passed("patient_nbr excluded")

print(
    "\nThe generated contexts contain model and utilization "
    "information only."
)

print(
    "They do not contain the retrospective outcome label."
)


# =============================================================================
# R — FINAL STATUS
# =============================================================================

section("R — FINAL STATUS")

expected_outputs = [
    CONTEXT_CSV,
    CONTEXT_JSONL,
    SAMPLE_FILE,
    SUMMARY_FILE,
]

for output in expected_outputs:

    if not output.exists():

        raise AssertionError(
            f"Output missing: {output}"
        )

    print(
        f"{output}: CREATED"
    )


print("\n" + "=" * 80)
print("PHASE 10.2 COMPLETE — PASSED")
print("=" * 80)

print(
    "\n1,178 frozen Rescue Router cases converted "
    "into agent-ready patient contexts."
)

print(
    "No retrospective outcome leakage detected."
)

print(
    "Frozen ML predictions and router selections preserved."
)

print(
    "\nNEXT PHASE:"
)

print(
    "PHASE 10.3 — RESCUE REVIEW AGENT"
)