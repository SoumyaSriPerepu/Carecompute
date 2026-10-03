"""
CareCompute
Phase 13.5.2 — Cross-Component Contract Validation

Purpose
-------
Validate field-level and semantic consistency across the frozen
CareCompute Phase 13 execution chain:

Phase 13.2 runtime
    -> Phase 13.3 patient contexts
    -> Rescue Review Agent
    -> Explanation Agent
    -> Phase 13.3 runtime packet
    -> Phase 13.4 orchestrated human-review packet
    -> Phase 13.4 case index

Validation only. No frozen artifacts are modified.
"""

from pathlib import Path
import ast
import hashlib
import json

import numpy as np
import pandas as pd


# =============================================================================
# CONFIGURATION
# =============================================================================

PHASE13 = Path("results/eligible/phase13")
VALIDATION = Path("results/eligible/runtime_validation")

VALIDATION.mkdir(parents=True, exist_ok=True)

EXPECTED_POPULATION = 1178
EXPECTED_THRESHOLD = 0.115
EXPECTED_REVIEW_BUDGET = 0.15

FILES = {
    "runtime":
        PHASE13 / "phase13_2_agent_eligible_runtime.csv",

    "contexts":
        PHASE13 / "phase13_3_patient_contexts.csv",

    "rescue":
        PHASE13 / "phase13_3_rescue_review_outputs.csv",

    "explanations":
        PHASE13 / "phase13_3_explanation_outputs.csv",

    "agent_packets":
        PHASE13 / "phase13_3_agent_runtime_packets.jsonl",

    "orchestrated_packets":
        PHASE13 / "phase13_4_orchestrated_human_review_packets.jsonl",

    "case_index":
        PHASE13 / "phase13_4_orchestrator_case_index.csv",
}


# =============================================================================
# HELPERS
# =============================================================================

def banner(text):
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


def sha256_file(path):

    h = hashlib.sha256()

    with open(path, "rb") as f:

        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def load_jsonl(path):

    records = []

    with open(path, "r", encoding="utf-8") as f:

        for line_number, line in enumerate(
            f,
            start=1,
        ):

            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))

            except json.JSONDecodeError as exc:

                raise RuntimeError(
                    f"Invalid JSONL: {path}, "
                    f"line {line_number}: {exc}"
                )

    return records


def check(condition, name, audit):

    result = bool(condition)

    audit[name] = (
        "PASSED"
        if result
        else "FAILED"
    )

    print(
        f"{name}: "
        f"{audit[name]}"
    )

    if not result:
        raise AssertionError(
            f"{name} FAILED"
        )


def normalize_id(value):

    return str(int(value))


def same_float(a, b, atol=1e-12):

    if pd.isna(a) and pd.isna(b):
        return True

    try:
        return bool(
            np.isclose(
                float(a),
                float(b),
                atol=atol,
                rtol=0.0,
            )
        )

    except Exception:
        return False


def same_scalar(a, b):

    if pd.isna(a) and pd.isna(b):
        return True

    if isinstance(a, (float, np.floating)) or \
       isinstance(b, (float, np.floating)):

        return same_float(a, b)

    return str(a) == str(b)


def normalize_sequence(value):
    """
    Convert list-like serialized values into a comparable list.

    Handles:
    - Python list
    - JSON list string
    - Python literal list string
    - delimiter-separated fallback string
    - empty/NaN
    """

    if value is None:
        return []

    if isinstance(value, list):
        return [str(x).strip() for x in value]

    try:
        if pd.isna(value):
            return []
    except Exception:
        pass

    text = str(value).strip()

    if text == "":
        return []

    # JSON
    try:

        parsed = json.loads(text)

        if isinstance(parsed, list):
            return [
                str(x).strip()
                for x in parsed
            ]

    except Exception:
        pass

    # Python literal representation
    try:

        parsed = ast.literal_eval(text)

        if isinstance(parsed, list):
            return [
                str(x).strip()
                for x in parsed
            ]

    except Exception:
        pass

    # Common delimiter fallback
    for delimiter in ["|", ";"]:

        if delimiter in text:

            return [
                x.strip()
                for x in text.split(delimiter)
                if x.strip()
            ]

    # Single semantic item
    return [text]


def packet_map(records):

    result = {}

    for packet in records:

        encounter_id = normalize_id(
            packet["encounter_id"]
        )

        if encounter_id in result:
            raise AssertionError(
                "Duplicate encounter_id in JSONL: "
                f"{encounter_id}"
            )

        result[encounter_id] = packet

    return result


def df_map(df):

    result = {}

    for _, row in df.iterrows():

        encounter_id = normalize_id(
            row["encounter_id"]
        )

        if encounter_id in result:
            raise AssertionError(
                "Duplicate encounter_id in CSV: "
                f"{encounter_id}"
            )

        result[encounter_id] = row

    return result


def record_mismatch(
    mismatches,
    encounter_id,
    field,
    source,
    destination,
):

    mismatches.append({
        "encounter_id": encounter_id,
        "field": field,
        "source_value": str(source),
        "destination_value": str(destination),
    })


# =============================================================================
# START
# =============================================================================

banner(
    "PHASE 13.5.2 — "
    "CROSS-COMPONENT CONTRACT VALIDATION"
)

audit = {}
mismatches = []


# =============================================================================
# A — VERIFY INPUT ARTIFACTS
# =============================================================================

banner("A — VERIFY INPUT ARTIFACTS")

for name, path in FILES.items():

    print(
        f"{name}: "
        f"{'FOUND' if path.exists() else 'MISSING'}"
    )

    if not path.exists():
        raise FileNotFoundError(path)


check(
    all(path.exists() for path in FILES.values()),
    "required_contract_artifacts_present",
    audit,
)


# =============================================================================
# B — CAPTURE FROZEN HASHES
# =============================================================================

banner("B — CAPTURE FROZEN HASHES")

pre_hashes = {}

for name, path in FILES.items():

    digest = sha256_file(path)

    pre_hashes[name] = digest

    print(
        f"{path} -> {digest}"
    )


# =============================================================================
# C — LOAD COMPONENT OUTPUTS
# =============================================================================

banner("C — LOAD COMPONENT OUTPUTS")

runtime = pd.read_csv(FILES["runtime"])
contexts = pd.read_csv(FILES["contexts"])
rescue = pd.read_csv(FILES["rescue"])
explanations = pd.read_csv(FILES["explanations"])
case_index = pd.read_csv(FILES["case_index"])

agent_packets = load_jsonl(
    FILES["agent_packets"]
)

orchestrated_packets = load_jsonl(
    FILES["orchestrated_packets"]
)

datasets = {
    "runtime": runtime,
    "contexts": contexts,
    "rescue": rescue,
    "explanations": explanations,
    "case_index": case_index,
}

for name, df in datasets.items():
    print(f"{name}: {len(df)}")

print(
    "agent_packets:",
    len(agent_packets),
)

print(
    "orchestrated_packets:",
    len(orchestrated_packets),
)


# =============================================================================
# D — VERIFY GLOBAL CONTRACT POPULATION
# =============================================================================

banner("D — VERIFY GLOBAL CONTRACT POPULATION")

for name, df in datasets.items():

    check(
        len(df) == EXPECTED_POPULATION,
        f"{name}_population",
        audit,
    )

check(
    len(agent_packets) == EXPECTED_POPULATION,
    "agent_packet_population",
    audit,
)

check(
    len(orchestrated_packets)
    == EXPECTED_POPULATION,
    "orchestrated_packet_population",
    audit,
)


# =============================================================================
# E — BUILD ENCOUNTER MAPS
# =============================================================================

banner("E — BUILD ENCOUNTER MAPS")

runtime_map = df_map(runtime)
context_map = df_map(contexts)
rescue_map = df_map(rescue)
explanation_map = df_map(explanations)
case_index_map = df_map(case_index)

agent_map = packet_map(agent_packets)
orchestrated_map = packet_map(
    orchestrated_packets
)

reference_ids = set(runtime_map)

component_maps = {
    "contexts": context_map,
    "rescue": rescue_map,
    "explanations": explanation_map,
    "agent_packets": agent_map,
    "orchestrated_packets": orchestrated_map,
    "case_index": case_index_map,
}

for name, mapping in component_maps.items():

    check(
        set(mapping) == reference_ids,
        f"{name}_encounter_contract",
        audit,
    )


# =============================================================================
# F — VALIDATE 13.2 -> 13.3 PATIENT CONTEXT
# =============================================================================

banner(
    "F — VALIDATE 13.2 RUNTIME "
    "-> 13.3 PATIENT CONTEXT"
)

runtime_context_fields = [
    "calibrated_probability",
    "decision_threshold",
    "predicted_30d",
    "model_disagreement_std",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
    "number_inpatient",
    "time_in_hospital",
    "selected_for_review",
    "age_group",
    "gender",
    "race",
]

stage_mismatches = 0

for eid in reference_ids:

    r = runtime_map[eid]
    c = context_map[eid]

    for field in runtime_context_fields:

        if not same_scalar(
            r[field],
            c[field],
        ):

            stage_mismatches += 1

            record_mismatch(
                mismatches,
                eid,
                f"13.2->13.3_context.{field}",
                r[field],
                c[field],
            )

    if not same_float(
        r["router_probability"],
        c["fn_router_probability"],
    ):

        stage_mismatches += 1

        record_mismatch(
            mismatches,
            eid,
            "13.2.router_probability"
            "->13.3.fn_router_probability",
            r["router_probability"],
            c["fn_router_probability"],
        )


print(
    "Runtime -> context mismatches:",
    stage_mismatches,
)

check(
    stage_mismatches == 0,
    "runtime_to_context_contract",
    audit,
)


# =============================================================================
# G — VALIDATE 13.3 CSV OUTPUTS -> AGENT PACKETS
# =============================================================================

banner(
    "G — VALIDATE 13.3 OUTPUTS "
    "-> AGENT PACKETS"
)

stage_mismatches = 0

for eid in reference_ids:

    c = context_map[eid]
    r = rescue_map[eid]
    e = explanation_map[eid]
    p = agent_map[eid]

    # Primary model
    primary = p["primary_model"]

    comparisons = [
        (
            "calibrated_probability",
            c["calibrated_probability"],
            primary["calibrated_probability"],
        ),
        (
            "decision_threshold",
            c["decision_threshold"],
            primary["decision_threshold"],
        ),
        (
            "predicted_30d",
            c["predicted_30d"],
            primary["predicted_30d"],
        ),
    ]

    for field, source, destination in comparisons:

        if not same_scalar(
            source,
            destination,
        ):

            stage_mismatches += 1

            record_mismatch(
                mismatches,
                eid,
                f"context->agent_packet."
                f"primary_model.{field}",
                source,
                destination,
            )

    # Rescue router
    router = p["rescue_router"]

    if not same_float(
        c["fn_router_probability"],
        router["fn_router_probability"],
    ):

        stage_mismatches += 1

        record_mismatch(
            mismatches,
            eid,
            "context->agent_packet."
            "fn_router_probability",
            c["fn_router_probability"],
            router["fn_router_probability"],
        )

    if not same_scalar(
        c["selected_for_review"],
        router["selected_for_review"],
    ):

        stage_mismatches += 1

        record_mismatch(
            mismatches,
            eid,
            "context->agent_packet."
            "selected_for_review",
            c["selected_for_review"],
            router["selected_for_review"],
        )

    if not same_float(
        router["review_budget"],
        EXPECTED_REVIEW_BUDGET,
    ):

        stage_mismatches += 1

        record_mismatch(
            mismatches,
            eid,
            "agent_packet.review_budget",
            EXPECTED_REVIEW_BUDGET,
            router["review_budget"],
        )

    # Rescue Review Agent
    rescue_packet = p["rescue_review"]

    scalar_fields = [
        "source_execution",
        "review_priority",
        "agent_priority_score",
        "risk_signal_summary",
        "triggered_signal_count",
        "uncertainty_flag",
        "human_review_action",
        "confidence",
    ]

    for field in scalar_fields:

        if not same_scalar(
            r[field],
            rescue_packet[field],
        ):

            stage_mismatches += 1

            record_mismatch(
                mismatches,
                eid,
                f"rescue_csv->agent_packet.{field}",
                r[field],
                rescue_packet[field],
            )

    for field in [
        "reason_codes",
        "triggered_signals",
    ]:

        source = normalize_sequence(
            r[field]
        )

        destination = normalize_sequence(
            rescue_packet[field]
        )

        if source != destination:

            stage_mismatches += 1

            record_mismatch(
                mismatches,
                eid,
                f"rescue_csv->agent_packet.{field}",
                source,
                destination,
            )

    # Explanation Agent
    explanation_packet = p["explanation"]

    for field in [
        "explanation",
        "uncertainty_statement",
        "human_review_statement",
    ]:

        if not same_scalar(
            e[field],
            explanation_packet[field],
        ):

            stage_mismatches += 1

            record_mismatch(
                mismatches,
                eid,
                f"explanation_csv->agent_packet."
                f"{field}",
                e[field],
                explanation_packet[field],
            )

    source_signal_explanations = (
        normalize_sequence(
            e["signal_explanations"]
        )
    )

    destination_signal_explanations = (
        normalize_sequence(
            explanation_packet[
                "signal_explanations"
            ]
        )
    )

    if (
        source_signal_explanations
        != destination_signal_explanations
    ):

        stage_mismatches += 1

        record_mismatch(
            mismatches,
            eid,
            "explanation_csv->agent_packet."
            "signal_explanations",
            source_signal_explanations,
            destination_signal_explanations,
        )


print(
    "13.3 CSV -> agent packet mismatches:",
    stage_mismatches,
)

check(
    stage_mismatches == 0,
    "phase13_3_output_to_packet_contract",
    audit,
)


# =============================================================================
# H — VALIDATE AGENT PACKETS -> 13.4 ORCHESTRATOR
# =============================================================================

banner(
    "H — VALIDATE AGENT PACKETS "
    "-> 13.4 ORCHESTRATOR"
)

stage_mismatches = 0

for eid in reference_ids:

    a = agent_map[eid]
    o = orchestrated_map[eid]

    # Primary model
    for field in [
        "calibrated_probability",
        "decision_threshold",
        "predicted_30d",
    ]:

        if not same_scalar(
            a["primary_model"][field],
            o["primary_model"][field],
        ):

            stage_mismatches += 1

            record_mismatch(
                mismatches,
                eid,
                f"agent->orchestrator."
                f"primary_model.{field}",
                a["primary_model"][field],
                o["primary_model"][field],
            )

    # Router
    for field in [
        "fn_router_probability",
        "review_budget",
        "selected_for_review",
    ]:

        if not same_scalar(
            a["rescue_router"][field],
            o["rescue_router"][field],
        ):

            stage_mismatches += 1

            record_mismatch(
                mismatches,
                eid,
                f"agent->orchestrator."
                f"rescue_router.{field}",
                a["rescue_router"][field],
                o["rescue_router"][field],
            )

    # Rescue review
    for field in [
        "review_priority",
        "risk_signal_summary",
        "uncertainty_flag",
        "human_review_action",
        "confidence",
    ]:

        if not same_scalar(
            a["rescue_review"][field],
            o["rescue_review"][field],
        ):

            stage_mismatches += 1

            record_mismatch(
                mismatches,
                eid,
                f"agent->orchestrator."
                f"rescue_review.{field}",
                a["rescue_review"][field],
                o["rescue_review"][field],
            )

    # reason_codes changed list -> serialized string.
    if normalize_sequence(
        a["rescue_review"]["reason_codes"]
    ) != normalize_sequence(
        o["rescue_review"]["reason_codes"]
    ):

        stage_mismatches += 1

        record_mismatch(
            mismatches,
            eid,
            "agent->orchestrator."
            "rescue_review.reason_codes",
            normalize_sequence(
                a["rescue_review"]["reason_codes"]
            ),
            normalize_sequence(
                o["rescue_review"]["reason_codes"]
            ),
        )

    # Explanation
    for field in [
        "explanation",
        "uncertainty_statement",
        "human_review_statement",
    ]:

        if not same_scalar(
            a["explanation"][field],
            o["explanation"][field],
        ):

            stage_mismatches += 1

            record_mismatch(
                mismatches,
                eid,
                f"agent->orchestrator."
                f"explanation.{field}",
                a["explanation"][field],
                o["explanation"][field],
            )

    # signal_explanations list -> serialized string.
    if normalize_sequence(
        a["explanation"]["signal_explanations"]
    ) != normalize_sequence(
        o["explanation"]["signal_explanations"]
    ):

        stage_mismatches += 1

        record_mismatch(
            mismatches,
            eid,
            "agent->orchestrator."
            "explanation.signal_explanations",
            normalize_sequence(
                a["explanation"][
                    "signal_explanations"
                ]
            ),
            normalize_sequence(
                o["explanation"][
                    "signal_explanations"
                ]
            ),
        )

    # Workflow state
    if not same_scalar(
        a["workflow_disposition"],
        o["workflow_disposition"],
    ):

        stage_mismatches += 1

        record_mismatch(
            mismatches,
            eid,
            "agent->orchestrator."
            "workflow_disposition",
            a["workflow_disposition"],
            o["workflow_disposition"],
        )

    if not same_scalar(
        a["human_review_required"],
        o["human_review_required"],
    ):

        stage_mismatches += 1

        record_mismatch(
            mismatches,
            eid,
            "agent->orchestrator."
            "human_review_required",
            a["human_review_required"],
            o["human_review_required"],
        )

    if not same_scalar(
        a["autonomous_clinical_action"],
        o["autonomous_clinical_action"],
    ):

        stage_mismatches += 1

        record_mismatch(
            mismatches,
            eid,
            "agent->orchestrator."
            "autonomous_clinical_action",
            a["autonomous_clinical_action"],
            o["autonomous_clinical_action"],
        )


print(
    "Agent -> orchestrator mismatches:",
    stage_mismatches,
)

check(
    stage_mismatches == 0,
    "agent_to_orchestrator_contract",
    audit,
)


# =============================================================================
# I — VALIDATE ORCHESTRATOR -> CASE INDEX
# =============================================================================

banner(
    "I — VALIDATE ORCHESTRATOR "
    "-> CASE INDEX"
)

stage_mismatches = 0

for eid in reference_ids:

    o = orchestrated_map[eid]
    idx = case_index_map[eid]

    comparisons = {
        "review_priority":
            o["rescue_review"][
                "review_priority"
            ],

        "selected_for_review":
            o["rescue_router"][
                "selected_for_review"
            ],

        "human_review_required":
            o["human_review_required"],

        "safety_guardrail_passed":
            o["safety_guardrail"][
                "passed"
            ],

        "fairness_monitor_mode":
            o["fairness_monitor"][
                "mode"
            ],

        "workflow_disposition":
            o["workflow_disposition"],
    }

    for field, packet_value in comparisons.items():

        index_value = idx[field]

        # Normalize booleans loaded by pandas.
        if isinstance(
            packet_value,
            (bool, np.bool_),
        ):

            if isinstance(index_value, str):

                index_normalized = (
                    index_value.strip().lower()
                    == "true"
                )

            else:
                index_normalized = bool(
                    index_value
                )

            equivalent = (
                bool(packet_value)
                == index_normalized
            )

        else:

            equivalent = same_scalar(
                packet_value,
                index_value,
            )

        if not equivalent:

            stage_mismatches += 1

            record_mismatch(
                mismatches,
                eid,
                f"orchestrator->case_index."
                f"{field}",
                packet_value,
                index_value,
            )


print(
    "Orchestrator -> case index mismatches:",
    stage_mismatches,
)

check(
    stage_mismatches == 0,
    "orchestrator_to_case_index_contract",
    audit,
)


# =============================================================================
# J — VALIDATE GLOBAL FROZEN PARAMETERS
# =============================================================================

banner("J — VALIDATE GLOBAL FROZEN PARAMETERS")

threshold_values = set(
    runtime["decision_threshold"]
    .astype(float)
    .round(12)
)

print(
    "Observed thresholds:",
    threshold_values,
)

check(
    threshold_values
    == {round(EXPECTED_THRESHOLD, 12)},
    "global_primary_threshold_contract",
    audit,
)


review_budgets = {
    round(
        float(
            p["rescue_router"][
                "review_budget"
            ]
        ),
        12,
    )
    for p in orchestrated_packets
}

print(
    "Observed review budgets:",
    review_budgets,
)

check(
    review_budgets
    == {round(EXPECTED_REVIEW_BUDGET, 12)},
    "global_review_budget_contract",
    audit,
)


# =============================================================================
# K — VALIDATE ORCHESTRATOR SAFETY CONTRACT
# =============================================================================

banner("K — VALIDATE ORCHESTRATOR SAFETY CONTRACT")

safety_violations = []

for eid in reference_ids:

    o = orchestrated_map[eid]

    guard = o["safety_guardrail"]
    fairness = o["fairness_monitor"]

    conditions = {
        "safety_guardrail.passed":
            guard["passed"] is True,

        "ground_truth_available":
            guard["ground_truth_available"]
            is False,

        "patient_identifier_available":
            guard[
                "patient_identifier_available"
            ] is False,

        "diagnosis_allowed":
            guard["diagnosis_allowed"]
            is False,

        "treatment_recommendation_allowed":
            guard[
                "treatment_recommendation_allowed"
            ] is False,

        "medication_recommendation_allowed":
            guard[
                "medication_recommendation_allowed"
            ] is False,

        "prediction_modification_allowed":
            guard[
                "prediction_modification_allowed"
            ] is False,

        "router_modification_allowed":
            guard[
                "router_modification_allowed"
            ] is False,

        "priority_modification_allowed":
            guard[
                "priority_modification_allowed"
            ] is False,

        "threshold_modification_allowed":
            guard[
                "threshold_modification_allowed"
            ] is False,

        "review_budget_modification_allowed":
            guard[
                "review_budget_modification_allowed"
            ] is False,

        "autonomous_clinical_action_allowed":
            guard[
                "autonomous_clinical_action_allowed"
            ] is False,

        "human_review_required":
            o["human_review_required"]
            is True,

        "autonomous_clinical_action":
            o["autonomous_clinical_action"]
            is False,

        "fairness_individual_decision_modification":
            fairness[
                "individual_decision_modification"
            ] is False,

        "demographics_used_for_routing":
            fairness[
                "demographics_used_for_routing"
            ] is False,

        "demographics_used_for_priority":
            fairness[
                "demographics_used_for_priority"
            ] is False,

        "subgroup_specific_threshold":
            fairness[
                "subgroup_specific_threshold"
            ] is False,
    }

    for field, condition in conditions.items():

        if not condition:

            safety_violations.append({
                "encounter_id": eid,
                "field": field,
            })


print(
    "Safety contract violations:",
    len(safety_violations),
)

check(
    len(safety_violations) == 0,
    "orchestrator_safety_contract",
    audit,
)


# =============================================================================
# L — VERIFY NO FROZEN ARTIFACT MODIFICATION
# =============================================================================

banner(
    "L — VERIFY NO FROZEN ARTIFACT MODIFICATION"
)

post_hashes = {}

for name, path in FILES.items():

    digest = sha256_file(path)

    post_hashes[name] = digest

    check(
        digest == pre_hashes[name],
        f"{name}_unchanged",
        audit,
    )


# =============================================================================
# M — SAVE MISMATCH REPORT
# =============================================================================

banner("M — SAVE MISMATCH REPORT")

mismatch_path = (
    VALIDATION
    / "phase13_5_2_contract_mismatches.csv"
)

mismatch_columns = [
    "encounter_id",
    "field",
    "source_value",
    "destination_value",
]

pd.DataFrame(
    mismatches,
    columns=mismatch_columns,
).to_csv(
    mismatch_path,
    index=False,
)

print(
    "Total mismatches:",
    len(mismatches),
)

print(
    "Saved:",
    mismatch_path,
)


# =============================================================================
# N — SAVE VALIDATION AUDIT
# =============================================================================

banner("N — SAVE VALIDATION AUDIT")

overall_passed = (
    all(
        value == "PASSED"
        for value in audit.values()
    )
    and len(mismatches) == 0
    and len(safety_violations) == 0
)


audit_output = {
    "system": "CareCompute",

    "phase": "13.5.2",

    "validation":
        "CROSS_COMPONENT_CONTRACT_VALIDATION",

    "population":
        EXPECTED_POPULATION,

    "contracts_validated": [
        "13.2_runtime_to_13.3_patient_context",
        "13.3_csv_outputs_to_agent_packet",
        "13.3_agent_packet_to_13.4_orchestrator",
        "13.4_orchestrator_to_case_index",
        "global_frozen_parameter_contract",
        "orchestrator_safety_contract",
    ],

    "total_mismatches":
        len(mismatches),

    "safety_violations":
        len(safety_violations),

    "checks":
        audit,

    "pre_validation_hashes":
        pre_hashes,

    "post_validation_hashes":
        post_hashes,

    "overall_status":
        "PASSED"
        if overall_passed
        else "FAILED",
}


audit_path = (
    VALIDATION
    / "phase13_5_2_cross_component_contract_audit.json"
)

with open(
    audit_path,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        audit_output,
        f,
        indent=2,
        sort_keys=True,
    )


print(
    "Saved:",
    audit_path,
)


# =============================================================================
# FINAL
# =============================================================================

banner(
    "PHASE 13.5.2 COMPLETE — "
    "CROSS-COMPONENT CONTRACT VALIDATION"
)

print("\nSYSTEM")
print(" CareCompute")

print("\nPOPULATION")
print(f" {EXPECTED_POPULATION}")

print("\nCONTRACTS")

print(
    " 13.2 Runtime -> "
    "13.3 Patient Context: "
    f"{audit.get('runtime_to_context_contract')}"
)

print(
    " 13.3 Outputs -> "
    "Agent Packet: "
    f"{audit.get('phase13_3_output_to_packet_contract')}"
)

print(
    " Agent Packet -> "
    "13.4 Orchestrator: "
    f"{audit.get('agent_to_orchestrator_contract')}"
)

print(
    " 13.4 Orchestrator -> "
    "Case Index: "
    f"{audit.get('orchestrator_to_case_index_contract')}"
)

print("\nFROZEN PARAMETERS")
print(
    f" Primary threshold: "
    f"{EXPECTED_THRESHOLD}"
)
print(
    f" Review budget: "
    f"{EXPECTED_REVIEW_BUDGET}"
)

print("\nMISMATCHES")
print(f" {len(mismatches)}")

print("\nSAFETY VIOLATIONS")
print(f" {len(safety_violations)}")

print("\nFROZEN INPUT MODIFICATION")
print(" NONE")

print("\nFINAL STATUS")

if overall_passed:

    print(
        " CROSS_COMPONENT_CONTRACTS_VALIDATED"
    )

else:

    print(
        " CONTRACT_VALIDATION_FAILED"
    )


print(
    "\nAudit:",
    audit_path,
)

print(
    "Mismatch report:",
    mismatch_path,
)


if not overall_passed:

    raise SystemExit(
        "Phase 13.5.2 validation failed."
    )


banner(
    "NEXT: PHASE 13.5.3 — "
    "SAFETY AND HUMAN-IN-THE-LOOP VALIDATION"
)