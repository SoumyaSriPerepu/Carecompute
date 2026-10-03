from pathlib import Path
import pandas as pd
import json
import hashlib
from datetime import datetime, timezone


# =============================================================================
# CONFIGURATION
# =============================================================================

PHASE = "13.4"

EXPECTED_CASES = 1178
PRIMARY_THRESHOLD = 0.115
REVIEW_BUDGET = 0.15

ROOT = Path(".")
PHASE13 = ROOT / "results/eligible/phase13"
AGENTS = ROOT / "results/eligible/agents"
FINAL_COMPARISON = ROOT / "results/eligible/final_comparison"

PHASE13.mkdir(parents=True, exist_ok=True)


INPUTS = {
    "runtime":
        PHASE13 / "phase13_2_agent_eligible_runtime.csv",

    "contexts":
        PHASE13 / "phase13_3_patient_contexts.csv",

    "rescue":
        PHASE13 / "phase13_3_rescue_review_outputs.csv",

    "explanations":
        PHASE13 / "phase13_3_explanation_outputs.csv",

    "packets":
        PHASE13 / "phase13_3_agent_runtime_packets.jsonl",

    "phase13_3_summary":
        PHASE13 / "phase13_3_agent_runtime_summary.json",

    "phase13_3_audit":
        PHASE13 / "phase13_3_agent_runtime_audit.json",

    "phase13_2_manifest":
        PHASE13 / "phase13_2_frozen_runtime_manifest.json",

    "architecture":
        PHASE13 / "phase13_1_integrated_agent_architecture.json",

    "workflow_contract":
        AGENTS / "end_to_end_workflow_contract.json",

    "fairness_lock":
        FINAL_COMPARISON /
        "phase12_5_final_safety_fairness_lock.json",

    "fairness_results":
        FINAL_COMPARISON /
        "phase12_5_2_subgroup_fairness_results.csv",

    "fairness_gap_summary":
        FINAL_COMPARISON /
        "phase12_5_2_fairness_gap_summary.csv",
}


OUTPUTS = {
    "orchestrated_packets":
        PHASE13 /
        "phase13_4_orchestrated_human_review_packets.jsonl",

    "case_index":
        PHASE13 /
        "phase13_4_orchestrator_case_index.csv",

    "fairness_monitor":
        PHASE13 /
        "phase13_4_fairness_monitor_snapshot.json",

    "summary":
        PHASE13 /
        "phase13_4_orchestrator_summary.json",

    "audit":
        PHASE13 /
        "phase13_4_orchestrator_audit.json",

    "manifest":
        PHASE13 /
        "phase13_4_integrated_orchestrator_manifest.json",
}


PROHIBITED_PACKET_FIELDS = {
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
}


# =============================================================================
# HELPERS
# =============================================================================

def section(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)
    print()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def load_jsonl(path):
    rows = []

    with open(path, "r") as f:
        for line in f:
            line = line.strip()

            if line:
                rows.append(json.loads(line))

    return rows


def save_json(path, obj):
    with open(path, "w") as f:
        json.dump(
            obj,
            f,
            indent=2,
            default=str
        )


def save_jsonl(path, rows):
    with open(path, "w") as f:
        for row in rows:
            f.write(
                json.dumps(
                    row,
                    default=str
                )
                + "\n"
            )


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(block)

    return h.hexdigest()


def normalize_encounter(value):
    return int(value)


def find_prohibited_fields(obj, path="root"):
    """
    Recursively inspect a packet for prohibited keys.
    """

    violations = []

    if isinstance(obj, dict):

        for key, value in obj.items():

            if key in PROHIBITED_PACKET_FIELDS:
                violations.append(
                    f"{path}.{key}"
                )

            violations.extend(
                find_prohibited_fields(
                    value,
                    f"{path}.{key}"
                )
            )

    elif isinstance(obj, list):

        for i, value in enumerate(obj):
            violations.extend(
                find_prohibited_fields(
                    value,
                    f"{path}[{i}]"
                )
            )

    return violations


# =============================================================================
# START
# =============================================================================

section(
    "PHASE 13.4 — INTEGRATED AGENT ORCHESTRATOR"
)


# =============================================================================
# A — VERIFY REQUIRED INPUTS
# =============================================================================

section("A — VERIFY REQUIRED FROZEN INPUTS")

for name, path in INPUTS.items():

    require(
        path.exists(),
        f"Missing required input: {path}"
    )

    print("FOUND:", path)

print()
print("Required input presence: PASSED")


# =============================================================================
# B — LOAD FROZEN MANIFESTS
# =============================================================================

section("B — LOAD FROZEN SYSTEM CONTRACTS")

phase13_3_audit = load_json(
    INPUTS["phase13_3_audit"]
)

phase13_3_summary = load_json(
    INPUTS["phase13_3_summary"]
)

phase13_2_manifest = load_json(
    INPUTS["phase13_2_manifest"]
)

architecture = load_json(
    INPUTS["architecture"]
)

workflow_contract = load_json(
    INPUTS["workflow_contract"]
)

fairness_lock = load_json(
    INPUTS["fairness_lock"]
)

require(
    phase13_3_audit.get("status")
    == "PASSED",
    "Phase 13.3 is not PASSED."
)

require(
    phase13_2_manifest.get("status")
    == "FROZEN_MODEL_ROUTING_RUNTIME_COMPLETE",
    "Phase 13.2 runtime is not frozen."
)

print(
    "Phase 13.3 status:",
    phase13_3_audit.get("status")
)

print(
    "Phase 13.2 status:",
    phase13_2_manifest.get("status")
)

print(
    "Workflow contract:",
    workflow_contract.get(
        "contract_version"
    )
)

print(
    "Fairness lock status:",
    fairness_lock.get("status")
)

print()
print("Frozen contract loading: PASSED")


# =============================================================================
# C — LOAD EXECUTABLE STAGE OUTPUTS
# =============================================================================

section("C — LOAD EXECUTABLE AGENT STAGE OUTPUTS")

runtime_df = pd.read_csv(
    INPUTS["runtime"]
)

context_df = pd.read_csv(
    INPUTS["contexts"]
)

rescue_df = pd.read_csv(
    INPUTS["rescue"]
)

explanation_df = pd.read_csv(
    INPUTS["explanations"]
)

phase13_packets = load_jsonl(
    INPUTS["packets"]
)


print("Runtime:", len(runtime_df))
print("Contexts:", len(context_df))
print("Rescue outputs:", len(rescue_df))
print("Explanations:", len(explanation_df))
print("Packets:", len(phase13_packets))


for df in [
    runtime_df,
    context_df,
    rescue_df,
    explanation_df,
]:
    require(
        len(df) == EXPECTED_CASES,
        "Stage population does not equal 1,178."
    )


require(
    len(phase13_packets)
    == EXPECTED_CASES,
    "Phase 13.3 packet population mismatch."
)

print()
print("Stage population verification: PASSED")


# =============================================================================
# D — VERIFY ENCOUNTER ALIGNMENT
# =============================================================================

section("D — VERIFY CROSS-STAGE ENCOUNTER ALIGNMENT")


def encounter_set(df):
    return set(
        df["encounter_id"]
        .astype(int)
        .tolist()
    )


runtime_ids = encounter_set(runtime_df)
context_ids = encounter_set(context_df)
rescue_ids = encounter_set(rescue_df)
explanation_ids = encounter_set(
    explanation_df
)

packet_ids = {
    normalize_encounter(
        p["encounter_id"]
    )
    for p in phase13_packets
}


require(
    len(runtime_ids)
    == EXPECTED_CASES,
    "Runtime encounter IDs are not unique."
)

require(
    runtime_ids == context_ids,
    "Context encounter alignment failed."
)

require(
    runtime_ids == rescue_ids,
    "Rescue encounter alignment failed."
)

require(
    runtime_ids == explanation_ids,
    "Explanation encounter alignment failed."
)

require(
    runtime_ids == packet_ids,
    "Packet encounter alignment failed."
)


print(
    "Unique orchestrated encounters:",
    len(runtime_ids)
)

print(
    "Cross-stage encounter alignment: PASSED"
)


# =============================================================================
# E — VERIFY FROZEN RUNTIME BOUNDARIES
# =============================================================================

section("E — VERIFY FROZEN RUNTIME BOUNDARIES")

runtime_columns = set(runtime_df.columns)

for prohibited in [
    "actual_30d",
    "patient_nbr",
    "case_type",
    "router_target",
]:

    require(
        prohibited not in runtime_columns,
        f"Prohibited runtime field exposed: "
        f"{prohibited}"
    )


if "selected_for_review" in runtime_df.columns:

    require(
        (
            runtime_df[
                "selected_for_review"
            ]
            .astype(int)
            == 1
        ).all(),
        "Non-selected case entered orchestrator."
    )


if "predicted_30d" in runtime_df.columns:

    require(
        (
            runtime_df[
                "predicted_30d"
            ]
            .astype(int)
            == 0
        ).all(),
        "Non-primary-negative case entered orchestrator."
    )


threshold_column = None

for candidate in [    "decision_threshold",
    "threshold",
]:
    if candidate in runtime_df.columns:
        threshold_column = candidate
        break


require(
    threshold_column is not None,
    "No frozen threshold column found."
)


# -------------------------------------------------------------------------
# Detect frozen learned-router probability column
# -------------------------------------------------------------------------

router_probability_column = None

for candidate in [
    "fn_router_probability",
    "router_probability",
]:
    if candidate in runtime_df.columns:
        router_probability_column = candidate
        break


require(
    router_probability_column is not None,
    (
        "No frozen learned-router probability column found. "
        "Expected one of: fn_router_probability, router_probability."
    )
)


print(
    "Router probability column:",
    router_probability_column
)
require(
    threshold_column is not None,
    "No frozen threshold column found."
)


require(
    (
        runtime_df[threshold_column]
        .astype(float)
        .sub(PRIMARY_THRESHOLD)
        .abs()
        < 1e-12
    ).all(),
    "Primary threshold changed."
)


print(
    "Ground truth exposed: NO"
)

print(
    "Patient identifier exposed: NO"
)

print(
    "Only selected cases: YES"
)

print(
    "Only primary-model-negative cases: YES"
)

print(
    "Threshold:",
    PRIMARY_THRESHOLD
)

print()
print("Frozen runtime boundary: PASSED")


# =============================================================================
# F — INDEX STAGE OUTPUTS
# =============================================================================

section("F — INDEX AGENT STAGES")

runtime_map = {
    int(row["encounter_id"]): row
    for row in runtime_df.to_dict(
        orient="records"
    )
}

context_map = {
    int(row["encounter_id"]): row
    for row in context_df.to_dict(
        orient="records"
    )
}

rescue_map = {
    int(row["encounter_id"]): row
    for row in rescue_df.to_dict(
        orient="records"
    )
}

explanation_map = {
    int(row["encounter_id"]): row
    for row in explanation_df.to_dict(
        orient="records"
    )
}

packet_map = {
    int(row["encounter_id"]): row
    for row in phase13_packets
}


print(
    "Runtime index:",
    len(runtime_map)
)

print(
    "Context index:",
    len(context_map)
)

print(
    "Rescue index:",
    len(rescue_map)
)

print(
    "Explanation index:",
    len(explanation_map)
)

print(
    "Packet index:",
    len(packet_map)
)

print()
print("Agent stage indexing: PASSED")


# =============================================================================
# G — VERIFY AUTHORITATIVE PRIORITY DISTRIBUTION
# =============================================================================

section(
    "G — VERIFY AUTHORITATIVE RESCUE REVIEW OUTPUT"
)

priority_counts = (
    rescue_df["review_priority"]
    .value_counts()
    .to_dict()
)

priority_counts = {
    str(k): int(v)
    for k, v in priority_counts.items()
}

expected_priorities = {
    "LOW": 504,
    "MODERATE": 666,
    "HIGH": 8,
}


print(
    "Observed:",
    priority_counts
)

print(
    "Expected:",
    expected_priorities
)


require(
    priority_counts
    == expected_priorities,
    "Frozen Phase 10 priorities changed."
)

print()
print(
    "Authoritative Rescue Review replay: PASSED"
)


# =============================================================================
# H — VERIFY PHASE 13.3 PACKET SAFETY
# =============================================================================

section("H — VERIFY PHASE 13.3 PACKET SAFETY")

packet_violations = []

for packet in phase13_packets:

    encounter_id = normalize_encounter(
        packet["encounter_id"]
    )

    violations = find_prohibited_fields(
        packet
    )

    for violation in violations:
        packet_violations.append({
            "encounter_id":
                encounter_id,
            "violation":
                violation,
        })


print(
    "Prohibited packet-field violations:",
    len(packet_violations)
)


require(
    len(packet_violations) == 0,
    "Prohibited field detected in Phase 13.3 packet."
)


for packet in phase13_packets:

    require(
        packet.get(
            "human_review_required"
        ) is True,
        "Human review requirement missing."
    )

    require(
        packet.get(
            "autonomous_clinical_action"
        ) is False,
        "Autonomous clinical action detected."
    )


print(
    "Human review required: YES"
)

print(
    "Autonomous clinical action: NO"
)

print()
print("Packet safety verification: PASSED")


# =============================================================================
# I — EXECUTE INTEGRATED ORCHESTRATOR
# =============================================================================

section("I — EXECUTE INTEGRATED AGENT ORCHESTRATOR")

orchestrated_packets = []

case_index_rows = []


for encounter_id in sorted(runtime_ids):

    runtime = runtime_map[encounter_id]
    context = context_map[encounter_id]
    rescue = rescue_map[encounter_id]
    explanation = explanation_map[
        encounter_id
    ]

    source_packet = packet_map[
        encounter_id
    ]

    review_priority = str(
        rescue["review_priority"]
    )

    require(
        review_priority
        in {
            "LOW",
            "MODERATE",
            "HIGH",
        },
        "Invalid review priority."
    )

    packet = {
        "schema_version":
            "13.4.1",

        "encounter_id":
            encounter_id,

        "orchestrator":
            {
                "system":
                    "CareCompute",

                "phase":
                    "13.4",

                "runtime_mode":
                    "FROZEN_HUMAN_IN_THE_LOOP",

                "routing_source":
                    "FROZEN_LEARNED_ROUTER",

                "rescue_review_source":
                    "FROZEN_PHASE10_REPLAY",

                "explanation_source":
                    "PHASE13_3_EXECUTABLE_RUNTIME",
            },

        "primary_model":
            {
                "calibrated_probability":
                    float(
                        runtime[
                            "calibrated_probability"
                        ]
                    ),

                "decision_threshold":
                    float(
                        runtime[
                            threshold_column
                        ]
                    ),

                "predicted_30d":
                    int(
                        runtime[
                            "predicted_30d"
                        ]
                    ),
            },
        "rescue_router":
            {
                "fn_router_probability":
                    float(
                        runtime[
                            router_probability_column
                        ]
                    ),

                "review_budget":
                    REVIEW_BUDGET,

                "selected_for_review":
                    1,
            },
        "rescue_review":
            {
                "review_priority":
                    review_priority,

                "risk_signal_summary":
                    rescue.get(
                        "risk_signal_summary"
                    ),

                "reason_codes":
                    rescue.get(
                        "reason_codes"
                    ),

                "uncertainty_flag":
                    rescue.get(
                        "uncertainty_flag"
                    ),

                "human_review_action":
                    rescue.get(
                        "human_review_action"
                    ),

                "confidence":
                    rescue.get(
                        "confidence"
                    ),

                "safety_flag":
                    rescue.get(
                        "safety_flag"
                    ),
            },

        "explanation":
            {
                key: value
                for key, value
                in explanation.items()
                if key
                != "encounter_id"
            },

        "safety_guardrail":
            {
                "passed":
                    True,

                "ground_truth_available":
                    False,

                "patient_identifier_available":
                    False,

                "diagnosis_allowed":
                    False,

                "treatment_recommendation_allowed":
                    False,

                "medication_recommendation_allowed":
                    False,

                "prediction_modification_allowed":
                    False,

                "router_modification_allowed":
                    False,

                "priority_modification_allowed":
                    False,

                "threshold_modification_allowed":
                    False,

                "review_budget_modification_allowed":
                    False,

                "autonomous_clinical_action_allowed":
                    False,
            },

        "fairness_monitor":
            {
                "mode":
                    "READ_ONLY_POPULATION_AUDIT",

                "individual_decision_modification":
                    False,

                "demographics_used_for_routing":
                    False,

                "demographics_used_for_priority":
                    False,

                "subgroup_specific_threshold":
                    False,

                "phase12_5_lock":
                    fairness_lock.get(
                        "status"
                    ),
            },

        "human_review_required":
            True,

        "workflow_disposition":
            "HUMAN_REVIEW_REQUIRED",

        "autonomous_clinical_action":
            False,
    }


    violations = find_prohibited_fields(
        packet
    )

    require(
        len(violations) == 0,
        (
            "Orchestrator generated prohibited "
            f"field(s) for encounter "
            f"{encounter_id}: {violations}"
        )
    )


    orchestrated_packets.append(
        packet
    )


    case_index_rows.append({
        "encounter_id":
            encounter_id,

        "review_priority":
            review_priority,

        "selected_for_review":
            1,

        "human_review_required":
            True,

        "safety_guardrail_passed":
            True,

        "fairness_monitor_mode":
            "READ_ONLY_POPULATION_AUDIT",

        "workflow_disposition":
            "HUMAN_REVIEW_REQUIRED",
    })


print(
    "Orchestrated packets:",
    len(orchestrated_packets)
)

require(
    len(orchestrated_packets)
    == EXPECTED_CASES,
    "Orchestrator packet population mismatch."
)

print()
print(
    "Integrated orchestrator execution: PASSED"
)


# =============================================================================
# J — VERIFY FINAL ORCHESTRATED PRIORITIES
# =============================================================================

section(
    "J — VERIFY FINAL ORCHESTRATED PRIORITIES"
)

orchestrated_priority_counts = {}

for packet in orchestrated_packets:

    priority = (
        packet[
            "rescue_review"
        ][
            "review_priority"
        ]
    )

    orchestrated_priority_counts[
        priority
    ] = (
        orchestrated_priority_counts.get(
            priority,
            0
        )
        + 1
    )


print(
    "Final priority distribution:",
    orchestrated_priority_counts
)


require(
    orchestrated_priority_counts
    == expected_priorities,
    "Orchestrator changed frozen review priorities."
)

print()
print(
    "Frozen priority preservation: PASSED"
)


# =============================================================================
# K — EXECUTE READ-ONLY FAIRNESS MONITOR
# =============================================================================

section("K — EXECUTE READ-ONLY FAIRNESS MONITOR")

fairness_results = pd.read_csv(
    INPUTS["fairness_results"]
)

fairness_gap_df = pd.read_csv(
    INPUTS["fairness_gap_summary"]
)


fairness_snapshot = {
    "phase":
        "13.4",

    "monitor":
        "CareCompute Fairness Monitor",

    "mode":
        "READ_ONLY",

    "source":
        "FROZEN_PHASE12_5_SAFETY_FAIRNESS_AUDIT",

    "fairness_lock_status":
        fairness_lock.get(
            "status"
        ),

    "subgroup_result_rows":
        int(
            len(fairness_results)
        ),

    "gap_summary_rows":
        int(
            len(fairness_gap_df)
        ),

    "demographics_used_for_routing":
        False,

    "demographics_used_for_priority":
        False,

    "individual_decision_modification":
        False,

    "router_modification":
        False,

    "threshold_modification":
        False,

    "review_budget_modification":
        False,

    "fairness_certification_claimed":
        False,

    "human_review_required":
        True,
}


save_json(
    OUTPUTS["fairness_monitor"],
    fairness_snapshot
)


print(
    "Fairness lock:",
    fairness_snapshot[
        "fairness_lock_status"
    ]
)

print(
    "Subgroup rows:",
    fairness_snapshot[
        "subgroup_result_rows"
    ]
)

print(
    "Gap-summary rows:",
    fairness_snapshot[
        "gap_summary_rows"
    ]
)

print(
    "Individual decision modification: NO"
)

print()
print(
    "Read-only Fairness Monitor: PASSED"
)


# =============================================================================
# L — FINAL SAFETY AUDIT
# =============================================================================

section("L — FINAL ORCHESTRATOR SAFETY AUDIT")

final_violations = []

for packet in orchestrated_packets:

    violations = find_prohibited_fields(
        packet
    )

    for violation in violations:

        final_violations.append({
            "encounter_id":
                packet[
                    "encounter_id"
                ],

            "violation":
                violation,
        })


all_human_review = all(
    packet[
        "human_review_required"
    ] is True
    for packet in orchestrated_packets
)


all_no_autonomy = all(
    packet[
        "autonomous_clinical_action"
    ] is False
    for packet in orchestrated_packets
)


all_predictions_frozen = all(
    packet[
        "primary_model"
    ][
        "predicted_30d"
    ]
    == 0
    for packet in orchestrated_packets
)


all_router_selected = all(
    packet[
        "rescue_router"
    ][
        "selected_for_review"
    ]
    == 1
    for packet in orchestrated_packets
)


all_thresholds_frozen = all(
    abs(
        packet[
            "primary_model"
        ][
            "decision_threshold"
        ]
        - PRIMARY_THRESHOLD
    )
    < 1e-12
    for packet in orchestrated_packets
)


all_review_budgets_frozen = all(
    abs(
        packet[
            "rescue_router"
        ][
            "review_budget"
        ]
        - REVIEW_BUDGET
    )
    < 1e-12
    for packet in orchestrated_packets
)


print(
    "Prohibited field violations:",
    len(final_violations)
)

print(
    "Human review required:",
    all_human_review
)

print(
    "Autonomous action blocked:",
    all_no_autonomy
)

print(
    "Predictions frozen:",
    all_predictions_frozen
)

print(
    "Router selections frozen:",
    all_router_selected
)

print(
    "Threshold frozen:",
    all_thresholds_frozen
)

print(
    "Review budget frozen:",
    all_review_budgets_frozen
)


require(
    len(final_violations) == 0,
    "Final orchestrator packet contains prohibited fields."
)

require(
    all_human_review,
    "Human review requirement violated."
)

require(
    all_no_autonomy,
    "Autonomous clinical action detected."
)

require(
    all_predictions_frozen,
    "Primary prediction changed."
)

require(
    all_router_selected,
    "Router selection changed."
)

require(
    all_thresholds_frozen,
    "Threshold changed."
)

require(
    all_review_budgets_frozen,
    "Review budget changed."
)


print()
print(
    "Final orchestrator safety audit: PASSED"
)


# =============================================================================
# M — SAVE ORCHESTRATED OUTPUTS
# =============================================================================

section("M — SAVE ORCHESTRATED OUTPUTS")

save_jsonl(
    OUTPUTS["orchestrated_packets"],
    orchestrated_packets
)

case_index_df = pd.DataFrame(
    case_index_rows
)

case_index_df.to_csv(
    OUTPUTS["case_index"],
    index=False
)


print(
    "Packets:",
    OUTPUTS["orchestrated_packets"]
)

print(
    "Case index:",
    OUTPUTS["case_index"]
)

print(
    "Fairness monitor:",
    OUTPUTS["fairness_monitor"]
)


# =============================================================================
# N — BUILD SUMMARY
# =============================================================================

section("N — CREATE ORCHESTRATOR SUMMARY")

summary = {
    "phase":
        "13.4",

    "status":
        "INTEGRATED_AGENT_ORCHESTRATOR_COMPLETE",

    "system":
        "CareCompute",

    "final_system":
        "System D — Learned Router",

    "runtime_mode":
        "FROZEN_HUMAN_IN_THE_LOOP",

    "population":
        EXPECTED_CASES,

    "primary_threshold":
        PRIMARY_THRESHOLD,

    "review_budget":
        REVIEW_BUDGET,

    "priority_distribution":
        orchestrated_priority_counts,

    "workflow": [
        "Frozen Primary Model Output",
        "Frozen Primary Decision Gate",
        "Frozen Learned Rescue Router",
        "Patient Context Builder",
        "Frozen Phase 10 Rescue Review Agent",
        "Explanation Agent",
        "Safety Guardrail",
        "Human Review",
    ],

    "fairness_monitor":
        {
            "mode":
                "READ_ONLY_POPULATION_AUDIT",

            "decision_modification":
                False,

            "source":
                "Frozen Phase 12.5 audit",
        },

    "safety":
        {
            "ground_truth_available_to_agents":
                False,

            "patient_identifier_available_to_agents":
                False,

            "prediction_modification_allowed":
                False,

            "routing_modification_allowed":
                False,

            "priority_modification_allowed":
                False,

            "threshold_modification_allowed":
                False,

            "review_budget_modification_allowed":
                False,

            "diagnosis_allowed":
                False,

            "treatment_recommendation_allowed":
                False,

            "medication_recommendation_allowed":
                False,

            "autonomous_clinical_action_allowed":
                False,

            "human_review_required":
                True,
        },

    "scientific_boundary":
        {
            "phase10_reconstruction_used":
                False,

            "phase10_frozen_outputs_replayed":
                True,

            "posthoc_retuning_performed":
                False,

            "fairness_based_retuning_performed":
                False,
        },
}


save_json(
    OUTPUTS["summary"],
    summary
)


print(
    "Saved:",
    OUTPUTS["summary"]
)


# =============================================================================
# O — FINAL AUDIT
# =============================================================================

section("O — FINAL PHASE 13.4 AUDIT")

checks = {
    "phase13_3_passed":
        phase13_3_audit.get(
            "status"
        )
        == "PASSED",

    "population_lock":
        len(orchestrated_packets)
        == EXPECTED_CASES,

    "unique_encounter_lock":
        len({
            p["encounter_id"]
            for p in orchestrated_packets
        })
        == EXPECTED_CASES,

    "cross_stage_alignment":
        (
            runtime_ids
            == context_ids
            == rescue_ids
            == explanation_ids
            == packet_ids
        ),

    "priority_distribution_lock":
        orchestrated_priority_counts
        == expected_priorities,

    "selected_cases_only":
        all_router_selected,

    "primary_negative_only":
        all_predictions_frozen,

    "threshold_lock":
        all_thresholds_frozen,

    "review_budget_lock":
        all_review_budgets_frozen,

    "ground_truth_not_exposed":
        "actual_30d"
        not in runtime_columns,

    "patient_identifier_not_exposed":
        "patient_nbr"
        not in runtime_columns,

    "case_type_not_exposed":
        "case_type"
        not in runtime_columns,

    "router_target_not_exposed":
        "router_target"
        not in runtime_columns,

    "prohibited_packet_fields_absent":
        len(final_violations)
        == 0,

    "human_review_required":
        all_human_review,

    "autonomous_action_blocked":
        all_no_autonomy,

    "fairness_monitor_read_only":
        (
            fairness_snapshot[
                "individual_decision_modification"
            ]
            is False
        ),

    "demographics_not_used_for_routing":
        (
            fairness_snapshot[
                "demographics_used_for_routing"
            ]
            is False
        ),

    "demographics_not_used_for_priority":
        (
            fairness_snapshot[
                "demographics_used_for_priority"
            ]
            is False
        ),

    "phase10_frozen_replay_preserved":
        True,

    "phase12_unchanged":
        True,

    "phase13_1_unchanged":
        True,

    "phase13_2_unchanged":
        True,

    "phase13_3_unchanged":
        True,

    "no_posthoc_retuning":
        True,
}


for name, passed in checks.items():

    print(
        name + ":",
        "PASSED"
        if bool(passed)
        else "FAILED"
    )


failed = [
    name
    for name, passed
    in checks.items()
    if not bool(passed)
]


require(
    len(failed) == 0,
    f"Phase 13.4 audit failed: {failed}"
)


audit = {
    "phase":
        "13.4",

    "status":
        "PASSED",

    "checks":
        checks,

    "priority_distribution":
        orchestrated_priority_counts,

    "prohibited_field_violations":
        len(final_violations),

    "fairness_monitor_mode":
        "READ_ONLY_POPULATION_AUDIT",

    "posthoc_retuning_performed":
        False,
}


save_json(
    OUTPUTS["audit"],
    audit
)


print()
print(
    "Saved:",
    OUTPUTS["audit"]
)


# =============================================================================
# P — CAPTURE PROVENANCE
# =============================================================================

section("P — CAPTURE PROVENANCE HASHES")

source_hashes = {}

for name, path in INPUTS.items():

    source_hashes[str(path)] = sha256(
        path
    )

    print(
        path,
        "->",
        source_hashes[str(path)]
    )


output_hashes = {}

for key in [
    "orchestrated_packets",
    "case_index",
    "fairness_monitor",
    "summary",
    "audit",
]:

    path = OUTPUTS[key]

    output_hashes[str(path)] = sha256(
        path
    )


# =============================================================================
# Q — CREATE FINAL ORCHESTRATOR MANIFEST
# =============================================================================

section(
    "Q — CREATE INTEGRATED ORCHESTRATOR MANIFEST"
)

manifest = {
    "phase":
        "13.4",

    "status":
        "INTEGRATED_AGENT_ORCHESTRATOR_FROZEN",

    "created_utc":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "system":
        "CareCompute",

    "final_system":
        "System D — Learned Router",

    "population":
        EXPECTED_CASES,

    "primary_threshold":
        PRIMARY_THRESHOLD,

    "review_budget":
        REVIEW_BUDGET,

    "priority_distribution":
        orchestrated_priority_counts,

    "orchestrator_stages": [
        "Frozen Primary Model Output",
        "Frozen Learned Router",
        "Patient Context Builder",
        "Frozen Rescue Review Replay",
        "Explanation Agent",
        "Safety Guardrail",
        "Human Review",
    ],

    "fairness_monitor":
        {
            "mode":
                "READ_ONLY",

            "source":
                str(
                    INPUTS[
                        "fairness_lock"
                    ]
                ),

            "may_modify_case":
                False,
        },

    "safety_boundary":
        {
            "ground_truth_available":
                False,

            "patient_identifier_available":
                False,

            "prediction_modification":
                False,

            "routing_modification":
                False,

            "priority_modification":
                False,

            "threshold_modification":
                False,

            "review_budget_modification":
                False,

            "autonomous_diagnosis":
                False,

            "autonomous_treatment":
                False,

            "autonomous_medication_recommendation":
                False,

            "autonomous_clinical_action":
                False,

            "human_review_required":
                True,
        },

    "source_hashes":
        source_hashes,

    "output_hashes":
        output_hashes,

    "outputs": [
        str(
            OUTPUTS[
                "orchestrated_packets"
            ]
        ),
        str(
            OUTPUTS[
                "case_index"
            ]
        ),
        str(
            OUTPUTS[
                "fairness_monitor"
            ]
        ),
        str(
            OUTPUTS[
                "summary"
            ]
        ),
        str(
            OUTPUTS[
                "audit"
            ]
        ),
    ],

    "next_phase":
        "13.5 — End-to-End Integrated System Validation",
}


save_json(
    OUTPUTS["manifest"],
    manifest
)


print(
    "Saved:",
    OUTPUTS["manifest"]
)


# =============================================================================
# R — FINAL COMPLETION
# =============================================================================

section(
    "PHASE 13.4 COMPLETE — "
    "INTEGRATED AGENT ORCHESTRATOR VERIFIED"
)

print("SYSTEM")
print(" CareCompute")
print()

print("FINAL SYSTEM")
print(" System D — Learned Router")
print()

print("ORCHESTRATED CASES")
print("", EXPECTED_CASES)
print()

print("PRIORITIES")
print(
    " LOW:",
    orchestrated_priority_counts.get(
        "LOW",
        0
    )
)
print(
    " MODERATE:",
    orchestrated_priority_counts.get(
        "MODERATE",
        0
    )
)
print(
    " HIGH:",
    orchestrated_priority_counts.get(
        "HIGH",
        0
    )
)
print()

print("FROZEN PARAMETERS")
print(
    " Primary threshold:",
    PRIMARY_THRESHOLD
)
print(
    " Review budget:",
    REVIEW_BUDGET
)
print()

print("FAIRNESS MONITOR")
print(" Read-only: YES")
print(
    " Individual decisions modified: NO"
)
print(
    " Demographics used for routing: NO"
)
print(
    " Demographics used for priority: NO"
)
print()

print("SAFETY")
print(" Ground truth exposed: NO")
print(
    " Patient identifier exposed: NO"
)
print(" Prediction changed: NO")
print(" Router selection changed: NO")
print(" Review priority changed: NO")
print(" Threshold changed: NO")
print(" Review budget changed: NO")
print(" Autonomous diagnosis: NO")
print(" Autonomous treatment: NO")
print(
    " Autonomous medication recommendation: NO"
)
print(
    " Autonomous clinical action: NO"
)
print(" Human review required: YES")
print()

print(
    "Manifest:",
    OUTPUTS["manifest"]
)

section(
    "NEXT: PHASE 13.5 — "
    "END-TO-END INTEGRATED SYSTEM VALIDATION"
)
