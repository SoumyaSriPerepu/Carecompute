"""
Phase 10.4.3 — Independent Explanation Fidelity & Safety Audit

Independently audits Phase 10.4.2 outputs against:
- Phase 10.2 frozen patient contexts
- Phase 10.3.4 frozen Rescue Review rules
- Phase 10.4.1 Explanation Agent contract

This script does NOT regenerate explanations or modify upstream artifacts.
"""

import json
import hashlib
from collections import Counter
from pathlib import Path


# =============================================================================
# PATHS
# =============================================================================

BASE = Path("results/eligible/agents")

CONTEXT_PATH = BASE / "patient_agent_contexts.jsonl"
RULES_PATH = BASE / "rescue_review_agent_frozen_rules.json"
CONTRACT_PATH = BASE / "explanation_agent_output_contract.json"
OUTPUT_PATH = BASE / "explanation_agent_outputs.jsonl"

AUDIT_PATH = BASE / "explanation_fidelity_safety_audit.json"


# =============================================================================
# EXPECTATIONS
# =============================================================================

EXPECTED_POPULATION = 1178
EXPECTED_OUTPUT_SCHEMA = "10.4.2"
EXPECTED_THRESHOLD = 0.115
EXPECTED_BUDGET = 0.15
MAX_SIGNALS = 5


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
        ("utilization_context", "time_in_hospital"),
}


# These are fields explicitly prohibited by the 10.4.1 contract.
PROHIBITED_FIELDS = {
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
}


# Demographics are allowed in the input context, but must not be used as
# causal reasons in the explanation output.
DEMOGRAPHIC_TERMS = {
    "female",
    "male",
    "gender",
    "race",
    "caucasian",
    "africanamerican",
    "asian",
    "hispanic",
    "age_group",
}


# =============================================================================
# LOADERS
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
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


# =============================================================================
# INDEPENDENT RULE RECOMPUTATION
# =============================================================================

def get_value(context, field):
    section, key = FIELD_PATHS[field]
    return context[section][key]


def triggered(value, operator, threshold):
    if operator == "<=":
        return value <= threshold

    if operator == ">=":
        return value >= threshold

    raise ValueError(f"Unsupported operator: {operator}")


def independently_recompute(context, rules):
    triggered_codes = []
    score = 0

    for code, rule in rules["signal_rules"].items():

        value = get_value(
            context,
            rule["field"]
        )

        if triggered(
            value,
            rule["operator"],
            rule["threshold"]
        ):
            triggered_codes.append(code)
            score += rules["signal_weights"][code]

    if score >= 6:
        priority = "HIGH"

    elif score >= 3:
        priority = "MODERATE"

    else:
        priority = "LOW"

    return triggered_codes, score, priority


# =============================================================================
# TEXT / SAFETY HELPERS
# =============================================================================

def collect_output_text(output):
    pieces = [
        output.get("explanation", ""),
        output.get("uncertainty_statement", ""),
        output.get("human_review_statement", ""),
    ]

    for signal in output.get("signal_explanations", []):
        pieces.append(signal.get("description", ""))

    return " ".join(pieces).lower()


def find_prohibited_fields_recursive(obj, path=""):
    findings = []

    if isinstance(obj, dict):

        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key

            if key in PROHIBITED_FIELDS:
                findings.append(current_path)

            findings.extend(
                find_prohibited_fields_recursive(
                    value,
                    current_path
                )
            )

    elif isinstance(obj, list):

        for index, value in enumerate(obj):
            findings.extend(
                find_prohibited_fields_recursive(
                    value,
                    f"{path}[{index}]"
                )
            )

    return findings


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 80)
    print("PHASE 10.4.3 — EXPLANATION FIDELITY & SAFETY AUDIT")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # A — LOAD ARTIFACTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("A — LOAD FROZEN ARTIFACTS")
    print("=" * 80)

    contexts = load_jsonl(CONTEXT_PATH)
    rules = load_json(RULES_PATH)
    contract = load_json(CONTRACT_PATH)
    outputs = load_jsonl(OUTPUT_PATH)

    print("Patient contexts:", len(contexts))
    print("Explanation outputs:", len(outputs))
    print("Rule version:", rules["rule_version"])
    print("Contract version:", contract["contract_version"])

    assert len(contexts) == EXPECTED_POPULATION
    assert len(outputs) == EXPECTED_POPULATION

    assert (
        rules["frozen_primary_model_threshold"]
        == EXPECTED_THRESHOLD
    )

    assert (
        rules["frozen_router_review_budget"]
        == EXPECTED_BUDGET
    )

    print("Artifact loading: PASSED")

    # -------------------------------------------------------------------------
    # B — BUILD ENCOUNTER MAPS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("B — ENCOUNTER ALIGNMENT")
    print("=" * 80)

    context_map = {
        int(x["encounter"]["encounter_id"]): x
        for x in contexts
    }

    output_map = {
        int(x["encounter_id"]): x
        for x in outputs
    }

    assert len(context_map) == EXPECTED_POPULATION
    assert len(output_map) == EXPECTED_POPULATION
    assert set(context_map) == set(output_map)

    print("Unique contexts:", len(context_map))
    print("Unique outputs:", len(output_map))
    print("Encounter sets identical: PASSED")

    # -------------------------------------------------------------------------
    # C — INDEPENDENT PRIORITY FIDELITY
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("C — INDEPENDENT PRIORITY FIDELITY")
    print("=" * 80)

    priority_mismatches = []
    recomputed_priorities = Counter()
    zero_signal_cases = []

    recomputed = {}

    for encounter_id, context in context_map.items():

        codes, score, priority = independently_recompute(
            context,
            rules
        )

        recomputed[encounter_id] = {
            "codes": codes,
            "score": score,
            "priority": priority,
        }

        recomputed_priorities[priority] += 1

        if not codes:
            zero_signal_cases.append(encounter_id)

        observed = output_map[encounter_id]["review_priority"]

        if observed != priority:
            priority_mismatches.append({
                "encounter_id": encounter_id,
                "expected": priority,
                "observed": observed,
                "score": score,
            })

    print(
        "Recomputed priority distribution:",
        dict(recomputed_priorities)
    )

    print(
        "Priority mismatches:",
        len(priority_mismatches)
    )

    assert len(priority_mismatches) == 0

    print("Independent priority fidelity: PASSED")

    # -------------------------------------------------------------------------
    # D — SIGNAL FIDELITY
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("D — SIGNAL FIDELITY")
    print("=" * 80)

    approved_base_codes = set(
        rules["signal_rules"].keys()
    )

    approved_contract_codes = set(
        contract[
            "signal_explanation_schema"
        ]["reason_code"]
    )

    signal_mismatches = []
    untriggered_signal_claims = []
    invalid_reason_codes = []
    excessive_signal_outputs = []

    for encounter_id, output in output_map.items():

        expected_codes = set(
            recomputed[encounter_id]["codes"]
        )

        explanations = output["signal_explanations"]

        if len(explanations) > MAX_SIGNALS:
            excessive_signal_outputs.append(encounter_id)

        for signal in explanations:

            code = signal["reason_code"]

            if code not in approved_contract_codes:
                invalid_reason_codes.append({
                    "encounter_id": encounter_id,
                    "reason_code": code,
                })

            # Summary codes are allowed and are not direct frozen rules.
            if code in approved_base_codes:

                if code not in expected_codes:
                    untriggered_signal_claims.append({
                        "encounter_id": encounter_id,
                        "reason_code": code,
                    })

        observed_base_codes = {
            x["reason_code"]
            for x in explanations
            if x["reason_code"] in approved_base_codes
        }

        # Generator can show at most 4 detailed base signals because
        # one slot is reserved for the summary signal.
        expected_order = sorted(
            recomputed[encounter_id]["codes"],
            key=lambda code: (
                -rules["signal_weights"][code],
                list(rules["signal_rules"]).index(code)
            )
        )

        expected_displayed = set(expected_order[:4])

        if observed_base_codes != expected_displayed:
            signal_mismatches.append({
                "encounter_id": encounter_id,
                "expected_displayed":
                    sorted(expected_displayed),
                "observed_displayed":
                    sorted(observed_base_codes),
            })

    print(
        "Untriggered signal claims:",
        len(untriggered_signal_claims)
    )

    print(
        "Displayed-signal mismatches:",
        len(signal_mismatches)
    )

    print(
        "Invalid reason codes:",
        len(invalid_reason_codes)
    )

    print(
        "Outputs exceeding signal limit:",
        len(excessive_signal_outputs)
    )

    assert not untriggered_signal_claims
    assert not signal_mismatches
    assert not invalid_reason_codes
    assert not excessive_signal_outputs

    print("Signal fidelity: PASSED")

    # -------------------------------------------------------------------------
    # E — SUMMARY REASON-CODE LOGIC
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("E — SUMMARY REASON-CODE LOGIC")
    print("=" * 80)

    summary_mismatches = []

    for encounter_id, output in output_map.items():

        n_signals = len(
            recomputed[encounter_id]["codes"]
        )

        reason_codes = {
            x["reason_code"]
            for x in output["signal_explanations"]
        }

        if n_signals >= 2:
            expected_summary = "MULTIPLE_RISK_SIGNALS"
        else:
            expected_summary = "LIMITED_RISK_SIGNALS"

        if expected_summary not in reason_codes:
            summary_mismatches.append({
                "encounter_id": encounter_id,
                "signal_count": n_signals,
                "expected_summary": expected_summary,
            })

    print(
        "Summary-code mismatches:",
        len(summary_mismatches)
    )

    assert not summary_mismatches

    print("Summary-code logic: PASSED")

    # -------------------------------------------------------------------------
    # F — ZERO-SIGNAL CASE AUDIT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("F — ZERO-SIGNAL CASE AUDIT")
    print("=" * 80)

    zero_signal_errors = []

    for encounter_id in zero_signal_cases:

        output = output_map[encounter_id]

        base_codes = [
            x["reason_code"]
            for x in output["signal_explanations"]
            if x["reason_code"] in approved_base_codes
        ]

        if base_codes:
            zero_signal_errors.append({
                "encounter_id": encounter_id,
                "base_codes": base_codes,
            })

        if (
            "LIMITED_RISK_SIGNALS"
            not in {
                x["reason_code"]
                for x in output["signal_explanations"]
            }
        ):
            zero_signal_errors.append({
                "encounter_id": encounter_id,
                "error":
                    "Missing LIMITED_RISK_SIGNALS"
            })

    print(
        "Zero-signal cases:",
        len(zero_signal_cases)
    )

    print(
        "Zero-signal errors:",
        len(zero_signal_errors)
    )

    assert not zero_signal_errors

    print("Zero-signal handling: PASSED")

    # -------------------------------------------------------------------------
    # G — CONTRACT / STRUCTURAL SAFETY
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("G — CONTRACT & STRUCTURAL SAFETY")
    print("=" * 80)

    required_fields = set(
        contract["required_fields"].keys()
    )

    field_errors = []
    prohibited_field_findings = []
    safety_flag_errors = []
    length_errors = []

    for encounter_id, output in output_map.items():

        if set(output.keys()) != required_fields:
            field_errors.append(encounter_id)

        findings = find_prohibited_fields_recursive(
            output
        )

        if findings:
            prohibited_field_findings.append({
                "encounter_id": encounter_id,
                "fields": findings,
            })

        if output["safety_flag"] is not False:
            safety_flag_errors.append(encounter_id)

        if len(output["explanation"]) > 800:
            length_errors.append({
                "encounter_id": encounter_id,
                "field": "explanation",
            })

        if len(output["uncertainty_statement"]) > 300:
            length_errors.append({
                "encounter_id": encounter_id,
                "field": "uncertainty_statement",
            })

        if len(output["human_review_statement"]) > 300:
            length_errors.append({
                "encounter_id": encounter_id,
                "field": "human_review_statement",
            })

        for signal in output["signal_explanations"]:

            if len(signal["description"]) > 250:
                length_errors.append({
                    "encounter_id": encounter_id,
                    "field": "signal_description",
                })

    print("Required-field errors:", len(field_errors))
    print(
        "Prohibited output-field findings:",
        len(prohibited_field_findings)
    )
    print(
        "Unexpected safety flags:",
        len(safety_flag_errors)
    )
    print("Length violations:", len(length_errors))

    assert not field_errors
    assert not prohibited_field_findings
    assert not safety_flag_errors
    assert not length_errors

    print("Structural contract safety: PASSED")

    # -------------------------------------------------------------------------
    # H — DEMOGRAPHIC CAUSAL-LANGUAGE AUDIT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("H — DEMOGRAPHIC CAUSAL-LANGUAGE AUDIT")
    print("=" * 80)

    demographic_findings = []

    for encounter_id, output in output_map.items():

        text = collect_output_text(output)

        found = sorted(
            term
            for term in DEMOGRAPHIC_TERMS
            if term in text
        )

        if found:
            demographic_findings.append({
                "encounter_id": encounter_id,
                "terms": found,
            })

    print(
        "Demographic terms in explanations:",
        len(demographic_findings)
    )

    assert not demographic_findings

    print(
        "Demographic causal-language exclusion: PASSED"
    )

    # -------------------------------------------------------------------------
    # I — HUMAN REVIEW / UNCERTAINTY SAFETY
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("I — HUMAN REVIEW & UNCERTAINTY SAFETY")
    print("=" * 80)

    missing_human_review = []
    missing_uncertainty_guardrail = []

    for encounter_id, output in output_map.items():

        human_text = (
            output["human_review_statement"].lower()
        )

        uncertainty_text = (
            output["uncertainty_statement"].lower()
        )

        if "human review" not in human_text:
            missing_human_review.append(encounter_id)

        if (
            "true outcome"
            not in uncertainty_text
        ):
            missing_uncertainty_guardrail.append(
                encounter_id
            )

    print(
        "Missing human-review statements:",
        len(missing_human_review)
    )

    print(
        "Missing uncertainty guardrails:",
        len(missing_uncertainty_guardrail)
    )

    assert not missing_human_review
    assert not missing_uncertainty_guardrail

    print("Human-review safety: PASSED")
    print("Uncertainty guardrail: PASSED")

    # -------------------------------------------------------------------------
    # J — HIGH-PRIORITY AUDIT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("J — HIGH-PRIORITY CASE AUDIT")
    print("=" * 80)

    high_cases = [
        encounter_id
        for encounter_id, values in recomputed.items()
        if values["priority"] == "HIGH"
    ]

    high_errors = []

    for encounter_id in high_cases:

        values = recomputed[encounter_id]

        if values["score"] < 6:
            high_errors.append(encounter_id)

        if (
            output_map[encounter_id]["review_priority"]
            != "HIGH"
        ):
            high_errors.append(encounter_id)

    print("HIGH-priority cases:", len(high_cases))
    print("HIGH-priority errors:", len(high_errors))

    assert not high_errors

    print("HIGH-priority audit: PASSED")

    # -------------------------------------------------------------------------
    # K — ARTIFACT HASHES
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("K — ARTIFACT HASHES")
    print("=" * 80)

    hashes = {
        "patient_agent_contexts.jsonl":
            sha256_file(CONTEXT_PATH),

        "rescue_review_agent_frozen_rules.json":
            sha256_file(RULES_PATH),

        "explanation_agent_output_contract.json":
            sha256_file(CONTRACT_PATH),

        "explanation_agent_outputs.jsonl":
            sha256_file(OUTPUT_PATH),
    }

    for name, digest in hashes.items():
        print(f"{name}: {digest}")

    # -------------------------------------------------------------------------
    # L — SAVE AUDIT
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("L — SAVE INDEPENDENT AUDIT")
    print("=" * 80)

    audit = {
        "phase": "10.4.3",
        "audit_name":
            "Explanation Fidelity & Safety Audit",
        "status": "PASSED",
        "population": EXPECTED_POPULATION,

        "priority_distribution":
            dict(recomputed_priorities),

        "zero_signal_cases":
            len(zero_signal_cases),

        "high_priority_cases":
            len(high_cases),

        "checks": {
            "encounter_alignment": True,
            "independent_priority_fidelity": True,
            "signal_fidelity": True,
            "summary_reason_code_logic": True,
            "zero_signal_handling": True,
            "structural_contract_safety": True,
            "prohibited_output_fields_absent": True,
            "demographic_causal_language_absent": True,
            "human_review_language_present": True,
            "uncertainty_guardrail_present": True,
            "high_priority_audit": True,
        },

        "violations": {
            "priority_mismatches":
                len(priority_mismatches),

            "signal_mismatches":
                len(signal_mismatches),

            "untriggered_signal_claims":
                len(untriggered_signal_claims),

            "invalid_reason_codes":
                len(invalid_reason_codes),

            "summary_mismatches":
                len(summary_mismatches),

            "zero_signal_errors":
                len(zero_signal_errors),

            "prohibited_field_findings":
                len(prohibited_field_findings),

            "demographic_findings":
                len(demographic_findings),

            "missing_human_review":
                len(missing_human_review),

            "missing_uncertainty_guardrail":
                len(missing_uncertainty_guardrail),

            "high_priority_errors":
                len(high_errors),
        },

        "artifact_sha256": hashes,

        "ground_truth_used": False,
        "model_modified": False,
        "router_modified": False,
        "threshold_modified": False,
        "review_budget_modified": False,
        "human_review_required": True,
    }

    with AUDIT_PATH.open(
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            audit,
            f,
            indent=2,
            sort_keys=True
        )

    print("Audit artifact:", AUDIT_PATH)

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("PHASE 10.4.3 COMPLETE — ALL AUDITS PASSED")
    print("=" * 80)

    print(
        "\nThe Phase 10.4.2 explanations independently match "
        "the frozen contexts, rules, and Explanation Agent contract."
    )


if __name__ == "__main__":
    main()
