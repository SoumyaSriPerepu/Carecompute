"""
Phase 10.4.2 — Deterministic Explanation Generator

CareCompute

Purpose
-------
Generate deterministic, non-diagnostic explanations for cases already
selected by the frozen Rescue Router.

This phase:
- does NOT use ground truth,
- does NOT retrain any model,
- does NOT modify model probabilities,
- does NOT modify router probabilities,
- does NOT change the primary decision threshold,
- does NOT change the Rescue Review budget,
- does NOT diagnose,
- does NOT recommend treatment or medication.

Inputs
------
results/eligible/agents/patient_agent_contexts.jsonl
results/eligible/agents/rescue_review_agent_frozen_rules.json
results/eligible/agents/explanation_agent_output_contract.json

Outputs
-------
results/eligible/agents/explanation_agent_outputs.jsonl
results/eligible/agents/explanation_agent_outputs.csv
results/eligible/agents/explanation_generator_summary.json
"""

import csv
import json
from pathlib import Path


# =============================================================================
# PATHS
# =============================================================================

BASE_DIR = Path("results/eligible/agents")

CONTEXT_PATH = BASE_DIR / "patient_agent_contexts.jsonl"
RULES_PATH = BASE_DIR / "rescue_review_agent_frozen_rules.json"
CONTRACT_PATH = BASE_DIR / "explanation_agent_output_contract.json"

OUTPUT_JSONL_PATH = BASE_DIR / "explanation_agent_outputs.jsonl"
OUTPUT_CSV_PATH = BASE_DIR / "explanation_agent_outputs.csv"
SUMMARY_PATH = BASE_DIR / "explanation_generator_summary.json"


# =============================================================================
# FROZEN EXPECTATIONS
# =============================================================================

EXPECTED_POPULATION = 1178
EXPECTED_CONTEXT_SCHEMA = "10.2"
EXPECTED_RULE_VERSION = "10.3.4"
EXPECTED_CONTRACT_VERSION = "10.4.1"

EXPECTED_PRIMARY_THRESHOLD = 0.115
EXPECTED_REVIEW_BUDGET = 0.15

OUTPUT_SCHEMA_VERSION = "10.4.2"

MAX_SIGNAL_EXPLANATIONS = 5


# =============================================================================
# APPROVED SIGNAL DESCRIPTIONS
# =============================================================================

SIGNAL_DESCRIPTIONS = {
    "NEAR_DECISION_THRESHOLD":
        "The primary-model probability was close to the frozen decision threshold.",

    "HIGH_MODEL_DISAGREEMENT":
        "Model disagreement was elevated relative to the frozen Rescue Review queue.",

    "HIGH_ROUTER_SCORE":
        "The frozen Rescue Router assigned a comparatively high review score to this case.",

    "HIGH_DIAGNOSIS_BURDEN":
        "The encounter contained a high number of recorded diagnosis codes.",

    "HIGH_OUTPATIENT_UTILIZATION":
        "The available utilization context showed elevated prior outpatient use.",

    "EMERGENCY_UTILIZATION":
        "The available utilization context included prior emergency utilization.",

    "INPATIENT_UTILIZATION":
        "The available utilization context included prior inpatient utilization.",

    "LONGER_HOSPITAL_STAY":
        "The encounter had a longer hospital stay under the frozen review rule."
}


# =============================================================================
# FIELD LOCATIONS
# =============================================================================

FIELD_PATHS = {
    "distance_below_threshold":
        ("primary_model", "distance_below_threshold"),

    "model_disagreement_std":
        ("uncertainty", "model_disagreement_std"),

    "fn_router_probability":
        ("router_context", "fn_router_probability"),

    "number_diagnoses":
        ("utilization_context", "number_diagnoses"),

    "number_outpatient":
        ("utilization_context", "number_outpatient"),

    "number_emergency":
        ("utilization_context", "number_emergency"),

    "number_inpatient":
        ("utilization_context", "number_inpatient"),

    "time_in_hospital":
        ("utilization_context", "time_in_hospital")
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
                    f"Invalid JSON on line {line_number} of {path}"
                ) from exc

    return records


def get_nested_value(context, field):
    if field not in FIELD_PATHS:
        raise KeyError(f"Unsupported frozen-rule field: {field}")

    section, key = FIELD_PATHS[field]

    if section not in context:
        raise KeyError(f"Missing context section: {section}")

    if key not in context[section]:
        raise KeyError(f"Missing context field: {section}.{key}")

    return context[section][key]


def rule_triggered(value, operator, threshold):
    if operator == "<=":
        return value <= threshold

    if operator == ">=":
        return value >= threshold

    raise ValueError(f"Unsupported operator: {operator}")


def determine_priority(score):
    if score >= 6:
        return "HIGH"

    if score >= 3:
        return "MODERATE"

    return "LOW"


def evaluate_signals(context, rules):
    triggered = []

    signal_rules = rules["signal_rules"]
    signal_weights = rules["signal_weights"]

    # Dictionary order is frozen in the rule artifact and is intentionally
    # preserved here for deterministic tie-breaking.
    for reason_code, rule in signal_rules.items():

        field = rule["field"]
        operator = rule["operator"]
        threshold = rule["threshold"]

        value = get_nested_value(context, field)

        if rule_triggered(value, operator, threshold):
            triggered.append({
                "reason_code": reason_code,
                "weight": signal_weights[reason_code]
            })

    return triggered


def order_signals(triggered_signals, rules):
    """
    Deterministic ordering:
    1. Higher frozen signal weight first.
    2. Frozen signal-rule order breaks ties.
    """

    frozen_order = {
        reason_code: index
        for index, reason_code in enumerate(rules["signal_rules"].keys())
    }

    return sorted(
        triggered_signals,
        key=lambda x: (
            -x["weight"],
            frozen_order[x["reason_code"]]
        )
    )


def build_signal_explanations(triggered_signals, rules):
    ordered = order_signals(triggered_signals, rules)

    signal_explanations = []

    # Reserve one slot for the summary reason code.
    detailed_limit = MAX_SIGNAL_EXPLANATIONS - 1

    for signal in ordered[:detailed_limit]:
        reason_code = signal["reason_code"]

        signal_explanations.append({
            "reason_code": reason_code,
            "description": SIGNAL_DESCRIPTIONS[reason_code]
        })

    # Contract-approved summary reason code.
    if len(triggered_signals) >= 2:
        signal_explanations.append({
            "reason_code": "MULTIPLE_RISK_SIGNALS",
            "description":
                "Multiple frozen review signals contributed to this case's review priority."
        })

    else:
        signal_explanations.append({
            "reason_code": "LIMITED_RISK_SIGNALS",
            "description":
                "Only a limited number of frozen review signals contributed to this case's review priority."
        })

    return signal_explanations[:MAX_SIGNAL_EXPLANATIONS]


def build_explanation(priority, triggered_signals):
    count = len(triggered_signals)

    if count == 0:
        return (
            f"This already-selected Rescue Review case received {priority} priority "
            "under the frozen deterministic review rules. No individual frozen "
            "signal rule was triggered strongly enough to add a specific signal explanation. "
            "This output summarizes review priority only and does not change the "
            "primary-model prediction or router selection."
        )

    if count == 1:
        return (
            f"This already-selected Rescue Review case received {priority} priority "
            "under the frozen deterministic review rules. One approved review signal "
            "contributed to the priority score. This explanation is descriptive only "
            "and does not change the primary-model prediction or router selection."
        )

    return (
        f"This already-selected Rescue Review case received {priority} priority "
        f"under the frozen deterministic review rules. {count} approved review signals "
        "contributed to the priority score. The explanation summarizes the strongest "
        "frozen signals and does not change the primary-model prediction or router selection."
    )


def build_uncertainty_statement(context):
    disagreement = context["uncertainty"]["model_disagreement_std"]

    return (
        f"Model disagreement is reported descriptively from the frozen context "
        f"(standard deviation {disagreement:.4f}); it does not establish the "
        "patient's true outcome."
    )


def build_human_review_statement(priority):
    if priority == "HIGH":
        return (
            "Human review remains required. HIGH priority indicates review ordering "
            "under the frozen policy and is not an autonomous clinical decision."
        )

    return (
        "Human review remains required. This priority supports review ordering only "
        "and is not an autonomous clinical decision."
    )


# =============================================================================
# INPUT VALIDATION
# =============================================================================

def validate_frozen_inputs(contexts, rules, contract):

    assert len(contexts) == EXPECTED_POPULATION, (
        f"Expected {EXPECTED_POPULATION} contexts, found {len(contexts)}"
    )

    assert rules["rule_version"] == EXPECTED_RULE_VERSION
    assert rules["status"] == "FROZEN"
    assert rules["expected_population"] == EXPECTED_POPULATION

    assert (
        rules["frozen_primary_model_threshold"]
        == EXPECTED_PRIMARY_THRESHOLD
    )

    assert (
        rules["frozen_router_review_budget"]
        == EXPECTED_REVIEW_BUDGET
    )

    assert contract["contract_version"] == EXPECTED_CONTRACT_VERSION

    assert (
        contract["constraints"]["maximum_signal_explanations"]
        == MAX_SIGNAL_EXPLANATIONS
    )

    encounter_ids = set()

    for context in contexts:

        assert context["schema_version"] == EXPECTED_CONTEXT_SCHEMA

        encounter_id = context["encounter"]["encounter_id"]

        if encounter_id in encounter_ids:
            raise ValueError(
                f"Duplicate encounter_id detected: {encounter_id}"
            )

        encounter_ids.add(encounter_id)

        primary = context["primary_model"]
        router = context["router_context"]
        constraints = context["agent_constraints"]

        assert primary["decision_threshold"] == EXPECTED_PRIMARY_THRESHOLD
        assert router["review_budget"] == EXPECTED_REVIEW_BUDGET

        # 10.4.2 must only operate on the frozen Rescue Review queue.
        assert router["selected_for_review"] == 1

        assert constraints["ground_truth_available"] is False
        assert constraints["may_change_model_prediction"] is False
        assert constraints["may_change_router_selection"] is False
        assert constraints["may_make_diagnosis"] is False
        assert constraints["may_recommend_treatment"] is False
        assert constraints["human_review_required"] is True


# =============================================================================
# OUTPUT VALIDATION
# =============================================================================

def validate_output(output, contract):

    required_fields = set(contract["required_fields"].keys())

    if set(output.keys()) != required_fields:
        raise ValueError(
            "Output fields do not exactly match Phase 10.4.1 contract."
        )

    if output["schema_version"] != OUTPUT_SCHEMA_VERSION:
        raise ValueError("Incorrect output schema version.")

    if not isinstance(output["encounter_id"], int):
        raise ValueError("encounter_id must be an integer.")

    if output["review_priority"] not in {"LOW", "MODERATE", "HIGH"}:
        raise ValueError("Invalid review priority.")

    if len(output["explanation"]) > 800:
        raise ValueError("Explanation exceeds 800 characters.")

    if len(output["uncertainty_statement"]) > 300:
        raise ValueError("Uncertainty statement exceeds 300 characters.")

    if len(output["human_review_statement"]) > 300:
        raise ValueError("Human review statement exceeds 300 characters.")

    if len(output["signal_explanations"]) > MAX_SIGNAL_EXPLANATIONS:
        raise ValueError("Too many signal explanations.")

    approved_reason_codes = set(
        contract["signal_explanation_schema"]["reason_code"]
    )

    for signal in output["signal_explanations"]:

        if set(signal.keys()) != {"reason_code", "description"}:
            raise ValueError("Invalid signal explanation structure.")

        if signal["reason_code"] not in approved_reason_codes:
            raise ValueError(
                f"Unapproved reason code: {signal['reason_code']}"
            )

        if len(signal["description"]) > 250:
            raise ValueError(
                "Signal description exceeds 250 characters."
            )

    if not isinstance(output["safety_flag"], bool):
        raise ValueError("safety_flag must be boolean.")


# =============================================================================
# GENERATOR
# =============================================================================

def generate_output(context, rules, contract):

    triggered_signals = evaluate_signals(context, rules)

    priority_score = sum(
        signal["weight"]
        for signal in triggered_signals
    )

    priority = determine_priority(priority_score)

    signal_explanations = build_signal_explanations(
        triggered_signals,
        rules
    )

    output = {
        "schema_version": OUTPUT_SCHEMA_VERSION,

        "encounter_id":
            int(context["encounter"]["encounter_id"]),

        "review_priority":
            priority,

        "explanation":
            build_explanation(priority, triggered_signals),

        "signal_explanations":
            signal_explanations,

        "uncertainty_statement":
            build_uncertainty_statement(context),

        "human_review_statement":
            build_human_review_statement(priority),

        "safety_flag":
            False
    }

    validate_output(output, contract)

    return output, priority_score, triggered_signals


# =============================================================================
# SAVE OUTPUTS
# =============================================================================

def save_jsonl(outputs):

    with OUTPUT_JSONL_PATH.open(
        "w",
        encoding="utf-8"
    ) as f:

        for output in outputs:
            f.write(
                json.dumps(
                    output,
                    ensure_ascii=False,
                    sort_keys=True
                )
                + "\n"
            )


def save_csv(outputs):

    fieldnames = [
        "schema_version",
        "encounter_id",
        "review_priority",
        "explanation",
        "signal_explanations",
        "uncertainty_statement",
        "human_review_statement",
        "safety_flag"
    ]

    with OUTPUT_CSV_PATH.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for output in outputs:

            row = dict(output)

            row["signal_explanations"] = json.dumps(
                output["signal_explanations"],
                ensure_ascii=False,
                sort_keys=True
            )

            writer.writerow(row)


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 80)
    print("PHASE 10.4.2 — DETERMINISTIC EXPLANATION GENERATOR")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # A — LOAD FROZEN INPUTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("A — LOAD FROZEN INPUTS")
    print("=" * 80)

    contexts = load_jsonl(CONTEXT_PATH)
    rules = load_json(RULES_PATH)
    contract = load_json(CONTRACT_PATH)

    print(f"Phase 10.2 contexts: {len(contexts)}")
    print(
        f"Phase 10.3.4 frozen rules: "
        f"{rules['status']}"
    )
    print(
        f"Phase 10.4.1 output contract: "
        f"{contract['contract_version']}"
    )

    # -------------------------------------------------------------------------
    # B — VERIFY FROZEN INPUT CONTRACT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("B — VERIFY FROZEN INPUT CONTRACT")
    print("=" * 80)

    validate_frozen_inputs(
        contexts,
        rules,
        contract
    )

    print(
        "Frozen primary threshold:",
        rules["frozen_primary_model_threshold"]
    )

    print(
        "Frozen Rescue Review budget:",
        rules["frozen_router_review_budget"]
    )

    print("Ground truth available to generator: NO")
    print("Frozen-input verification: PASSED")

    # -------------------------------------------------------------------------
    # C — GENERATE EXPLANATIONS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("C — GENERATE DETERMINISTIC EXPLANATIONS")
    print("=" * 80)

    outputs = []

    priority_counts = {
        "LOW": 0,
        "MODERATE": 0,
        "HIGH": 0
    }

    signal_counts = {
        code: 0
        for code in rules["signal_rules"].keys()
    }

    score_counts = {}

    zero_signal_cases = 0

    for context in contexts:

        output, priority_score, triggered_signals = generate_output(
            context,
            rules,
            contract
        )

        outputs.append(output)

        priority_counts[
            output["review_priority"]
        ] += 1

        score_counts[priority_score] = (
            score_counts.get(priority_score, 0) + 1
        )

        if len(triggered_signals) == 0:
            zero_signal_cases += 1

        for signal in triggered_signals:
            signal_counts[
                signal["reason_code"]
            ] += 1

    print(f"Generated explanations: {len(outputs)}")
    print(f"LOW priority: {priority_counts['LOW']}")
    print(f"MODERATE priority: {priority_counts['MODERATE']}")
    print(f"HIGH priority: {priority_counts['HIGH']}")
    print(f"Zero-signal cases: {zero_signal_cases}")

    # -------------------------------------------------------------------------
    # D — CONTRACT AND SAFETY AUDIT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("D — CONTRACT AND SAFETY AUDIT")
    print("=" * 80)

    for output in outputs:
        validate_output(output, contract)

    output_ids = [
        output["encounter_id"]
        for output in outputs
    ]

    input_ids = [
        int(context["encounter"]["encounter_id"])
        for context in contexts
    ]

    assert len(outputs) == EXPECTED_POPULATION
    assert len(set(output_ids)) == EXPECTED_POPULATION
    assert set(output_ids) == set(input_ids)

    print("Required fields: PASSED")
    print("Approved reason codes only: PASSED")
    print("Character limits: PASSED")
    print("Maximum 5 signal explanations: PASSED")
    print("Encounter coverage: PASSED")
    print("Ground-truth exclusion: PASSED")
    print("Prediction modification: NONE")
    print("Router modification: NONE")
    print("Threshold modification: NONE")
    print("Review-budget modification: NONE")
    print("Human review preserved: PASSED")

    # -------------------------------------------------------------------------
    # E — DETERMINISM TEST
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("E — DETERMINISM TEST")
    print("=" * 80)

    second_pass = []

    for context in contexts:

        output, _, _ = generate_output(
            context,
            rules,
            contract
        )

        second_pass.append(output)

    first_serialized = json.dumps(
        outputs,
        sort_keys=True,
        ensure_ascii=False
    )

    second_serialized = json.dumps(
        second_pass,
        sort_keys=True,
        ensure_ascii=False
    )

    assert first_serialized == second_serialized

    print("Repeated generation identical: PASSED")

    # -------------------------------------------------------------------------
    # F — SAVE OUTPUTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("F — SAVE OUTPUTS")
    print("=" * 80)

    save_jsonl(outputs)
    save_csv(outputs)

    summary = {
        "phase": OUTPUT_SCHEMA_VERSION,
        "status": "COMPLETED",
        "generator_type": "deterministic_rule_based",
        "input_population": len(contexts),
        "output_population": len(outputs),
        "primary_model_threshold": EXPECTED_PRIMARY_THRESHOLD,
        "rescue_review_budget": EXPECTED_REVIEW_BUDGET,
        "priority_distribution": priority_counts,
        "priority_score_distribution": {
            str(k): v
            for k, v in sorted(score_counts.items())
        },
        "signal_trigger_counts": signal_counts,
        "zero_signal_cases": zero_signal_cases,
        "ground_truth_used": False,
        "prediction_modified": False,
        "router_modified": False,
        "threshold_modified": False,
        "review_budget_modified": False,
        "human_review_required": True,
        "determinism_check_passed": True,
        "contract_validation_passed": True
    }

    with SUMMARY_PATH.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            summary,
            f,
            indent=2,
            sort_keys=True
        )

    print(f"JSONL: {OUTPUT_JSONL_PATH}")
    print(f"CSV:   {OUTPUT_CSV_PATH}")
    print(f"Summary: {SUMMARY_PATH}")

    # -------------------------------------------------------------------------
    # G — SAMPLE OUTPUT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("G — SAMPLE EXPLANATION")
    print("=" * 80)

    print(
        json.dumps(
            outputs[0],
            indent=2,
            ensure_ascii=False
        )
    )

    print("\n" + "=" * 80)
    print("PHASE 10.4.2 COMPLETE")
    print("=" * 80)

    print(
        "\nDeterministic explanations generated without "
        "ground truth or modification of frozen model/router decisions."
    )


if __name__ == "__main__":
    main()
