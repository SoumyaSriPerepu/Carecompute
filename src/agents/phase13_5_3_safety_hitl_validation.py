"""
CareCompute
Phase 13.5.3 — Safety and Human-in-the-Loop Validation

Validates the frozen Phase 13.4 human-review packets.

This script is read-only with respect to all frozen Phase 13 artifacts.
"""

from pathlib import Path
import hashlib
import json
import pandas as pd


# =============================================================================
# CONFIGURATION
# =============================================================================

PHASE13 = Path("results/eligible/phase13")
VALIDATION = Path("results/eligible/runtime_validation")

VALIDATION.mkdir(parents=True, exist_ok=True)

PACKET_PATH = (
    PHASE13
    / "phase13_4_orchestrated_human_review_packets.jsonl"
)

CASE_INDEX_PATH = (
    PHASE13
    / "phase13_4_orchestrator_case_index.csv"
)

EXPECTED_POPULATION = 1178


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
                    f"Invalid JSONL line "
                    f"{line_number}: {exc}"
                )

    return records


def check(condition, name, audit):

    result = bool(condition)

    audit[name] = (
        "PASSED"
        if result
        else "FAILED"
    )

    print(f"{name}: {audit[name]}")

    if not result:
        raise AssertionError(
            f"{name} FAILED"
        )


def recursive_keys(obj):

    keys = set()

    if isinstance(obj, dict):

        for key, value in obj.items():

            keys.add(str(key).lower())

            keys.update(
                recursive_keys(value)
            )

    elif isinstance(obj, list):

        for value in obj:
            keys.update(
                recursive_keys(value)
            )

    return keys


# =============================================================================
# START
# =============================================================================

banner(
    "PHASE 13.5.3 — "
    "SAFETY AND HUMAN-IN-THE-LOOP VALIDATION"
)

audit = {}
violations = []


# =============================================================================
# A — VERIFY INPUTS
# =============================================================================

banner("A — VERIFY FROZEN INPUTS")

print(
    "Packets:",
    "FOUND"
    if PACKET_PATH.exists()
    else "MISSING",
)

print(
    "Case index:",
    "FOUND"
    if CASE_INDEX_PATH.exists()
    else "MISSING",
)

check(
    PACKET_PATH.exists()
    and CASE_INDEX_PATH.exists(),
    "required_inputs_present",
    audit,
)


# =============================================================================
# B — CAPTURE PRE-VALIDATION HASHES
# =============================================================================

banner("B — CAPTURE PRE-VALIDATION HASHES")

packet_hash_before = sha256_file(
    PACKET_PATH
)

index_hash_before = sha256_file(
    CASE_INDEX_PATH
)

print(
    PACKET_PATH,
    "->",
    packet_hash_before,
)

print(
    CASE_INDEX_PATH,
    "->",
    index_hash_before,
)


# =============================================================================
# C — LOAD POPULATION
# =============================================================================

banner("C — LOAD VALIDATION POPULATION")

packets = load_jsonl(
    PACKET_PATH
)

case_index = pd.read_csv(
    CASE_INDEX_PATH
)

print(
    "Human-review packets:",
    len(packets),
)

print(
    "Case-index rows:",
    len(case_index),
)

check(
    len(packets) == EXPECTED_POPULATION,
    "packet_population_lock",
    audit,
)

check(
    len(case_index) == EXPECTED_POPULATION,
    "case_index_population_lock",
    audit,
)


# =============================================================================
# D — VALIDATE SAFETY GUARDRAIL FOR EVERY CASE
# =============================================================================

banner(
    "D — VALIDATE SAFETY GUARDRAIL "
    "FOR EVERY CASE"
)

for packet in packets:

    eid = packet["encounter_id"]

    guard = packet[
        "safety_guardrail"
    ]

    expected = {
        "passed": True,

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
    }

    for field, expected_value in expected.items():

        observed = guard.get(field)

        if observed is not expected_value:

            violations.append({
                "encounter_id": eid,
                "category":
                    "SAFETY_GUARDRAIL",
                "field": field,
                "expected":
                    expected_value,
                "observed":
                    observed,
            })


guardrail_violations = [
    v for v in violations
    if v["category"]
    == "SAFETY_GUARDRAIL"
]

print(
    "Guardrail violations:",
    len(guardrail_violations),
)

check(
    len(guardrail_violations) == 0,
    "safety_guardrail_contract",
    audit,
)


# =============================================================================
# E — VALIDATE HUMAN REVIEW REQUIREMENT
# =============================================================================

banner(
    "E — VALIDATE HUMAN REVIEW REQUIREMENT"
)

hitl_violations = []

for packet in packets:

    eid = packet["encounter_id"]

    if packet.get(
        "human_review_required"
    ) is not True:

        hitl_violations.append({
            "encounter_id": eid,
            "category":
                "HUMAN_REVIEW",
            "field":
                "human_review_required",
            "expected": True,
            "observed":
                packet.get(
                    "human_review_required"
                ),
        })

    if packet.get(
        "autonomous_clinical_action"
    ) is not False:

        hitl_violations.append({
            "encounter_id": eid,
            "category":
                "AUTONOMOUS_ACTION",
            "field":
                "autonomous_clinical_action",
            "expected": False,
            "observed":
                packet.get(
                    "autonomous_clinical_action"
                ),
        })


violations.extend(
    hitl_violations
)

print(
    "HITL/autonomy violations:",
    len(hitl_violations),
)

check(
    len(hitl_violations) == 0,
    "mandatory_human_review_contract",
    audit,
)


# =============================================================================
# F — VALIDATE HUMAN REVIEW ACTION
# =============================================================================

banner(
    "F — VALIDATE RESCUE REVIEW "
    "HUMAN ACTION CONTRACT"
)

action_violations = []

for packet in packets:

    eid = packet["encounter_id"]

    action = (
        packet["rescue_review"]
        .get("human_review_action")
    )

    if not isinstance(action, str) \
       or not action.strip():

        action_violations.append({
            "encounter_id": eid,
            "category":
                "HUMAN_REVIEW_ACTION",
            "field":
                "human_review_action",
            "expected":
                "non-empty human-review action",
            "observed":
                action,
        })


violations.extend(
    action_violations
)

print(
    "Human-review action violations:",
    len(action_violations),
)

check(
    len(action_violations) == 0,
    "human_review_action_present",
    audit,
)


# =============================================================================
# G — VALIDATE EXPLANATION HUMAN-REVIEW STATEMENT
# =============================================================================

banner(
    "G — VALIDATE EXPLANATION "
    "HUMAN-REVIEW STATEMENT"
)

statement_violations = []

for packet in packets:

    eid = packet["encounter_id"]

    statement = (
        packet["explanation"]
        .get("human_review_statement")
    )

    if not isinstance(statement, str) \
       or not statement.strip():

        statement_violations.append({
            "encounter_id": eid,
            "category":
                "EXPLANATION_HITL",
            "field":
                "human_review_statement",
            "expected":
                "non-empty statement",
            "observed":
                statement,
        })


violations.extend(
    statement_violations
)

print(
    "Explanation HITL violations:",
    len(statement_violations),
)

check(
    len(statement_violations) == 0,
    "explanation_human_review_contract",
    audit,
)


# =============================================================================
# H — VALIDATE FAIRNESS MONITOR IS NON-INTERVENTIONAL
# =============================================================================

banner(
    "H — VALIDATE FAIRNESS MONITOR "
    "IS NON-INTERVENTIONAL"
)

fairness_violations = []

for packet in packets:

    eid = packet["encounter_id"]

    fairness = packet[
        "fairness_monitor"
    ]

    expected_false = [
        "individual_decision_modification",
        "demographics_used_for_routing",
        "demographics_used_for_priority",
        "subgroup_specific_threshold",
    ]

    for field in expected_false:

        observed = fairness.get(
            field
        )

        if observed is not False:

            fairness_violations.append({
                "encounter_id": eid,
                "category":
                    "FAIRNESS_MONITOR",
                "field": field,
                "expected": False,
                "observed": observed,
            })


violations.extend(
    fairness_violations
)

print(
    "Fairness intervention violations:",
    len(fairness_violations),
)

check(
    len(fairness_violations) == 0,
    "fairness_monitor_non_intervention",
    audit,
)


# =============================================================================
# I — VERIFY PROHIBITED DATA IS ABSENT
# =============================================================================

banner(
    "I — VERIFY PROHIBITED DATA "
    "IS ABSENT"
)

prohibited_fields = {
    "target_30d",
    "ground_truth",
    "actual_outcome",
    "true_label",
    "patient_nbr",
    "patient_id",
    "case_type",
    "router_target",
}

prohibited_violations = []

for packet in packets:

    keys = recursive_keys(
        packet
    )

    bad = (
        keys
        .intersection(
            prohibited_fields
        )
    )

    if bad:

        prohibited_violations.append({
            "encounter_id":
                packet["encounter_id"],
            "category":
                "PROHIBITED_DATA",
            "field":
                ",".join(
                    sorted(bad)
                ),
            "expected":
                "ABSENT",
            "observed":
                "PRESENT",
        })


violations.extend(
    prohibited_violations
)

print(
    "Prohibited-data violations:",
    len(prohibited_violations),
)

check(
    len(prohibited_violations) == 0,
    "prohibited_data_absent",
    audit,
)


# =============================================================================
# J — VALIDATE CASE INDEX HITL CONTRACT
# =============================================================================

banner(
    "J — VALIDATE CASE INDEX "
    "HITL CONTRACT"
)

index_violations = []

for _, row in case_index.iterrows():

    value = row[
        "human_review_required"
    ]

    if isinstance(value, str):

        is_true = (
            value.strip().lower()
            == "true"
        )

    else:

        is_true = bool(value)

    if not is_true:

        index_violations.append({
            "encounter_id":
                row["encounter_id"],
            "category":
                "CASE_INDEX_HITL",
            "field":
                "human_review_required",
            "expected": True,
            "observed": value,
        })


violations.extend(
    index_violations
)

print(
    "Case-index HITL violations:",
    len(index_violations),
)

check(
    len(index_violations) == 0,
    "case_index_human_review_contract",
    audit,
)


# =============================================================================
# K — VERIFY FROZEN FILES UNCHANGED
# =============================================================================

banner(
    "K — VERIFY FROZEN FILES UNCHANGED"
)

packet_hash_after = sha256_file(
    PACKET_PATH
)

index_hash_after = sha256_file(
    CASE_INDEX_PATH
)

check(
    packet_hash_before
    == packet_hash_after,
    "orchestrated_packets_unchanged",
    audit,
)

check(
    index_hash_before
    == index_hash_after,
    "case_index_unchanged",
    audit,
)


# =============================================================================
# L — SAVE VIOLATION REPORT
# =============================================================================

banner("L — SAVE VIOLATION REPORT")

violation_path = (
    VALIDATION
    / "phase13_5_3_safety_hitl_violations.csv"
)

columns = [
    "encounter_id",
    "category",
    "field",
    "expected",
    "observed",
]

pd.DataFrame(
    violations,
    columns=columns,
).to_csv(
    violation_path,
    index=False,
)

print(
    "Total violations:",
    len(violations),
)

print(
    "Saved:",
    violation_path,
)


# =============================================================================
# M — SAVE AUDIT
# =============================================================================

banner("M — SAVE VALIDATION AUDIT")

overall_passed = (
    len(violations) == 0
    and all(
        result == "PASSED"
        for result in audit.values()
    )
)

audit_output = {
    "system":
        "CareCompute",

    "phase":
        "13.5.3",

    "validation":
        "SAFETY_AND_HUMAN_IN_THE_LOOP",

    "population":
        EXPECTED_POPULATION,

    "safety_properties": {
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

        "human_review_required":
            True,
    },

    "total_violations":
        len(violations),

    "checks":
        audit,

    "frozen_hashes": {
        "packet_before":
            packet_hash_before,

        "packet_after":
            packet_hash_after,

        "case_index_before":
            index_hash_before,

        "case_index_after":
            index_hash_after,
    },

    "overall_status":
        "PASSED"
        if overall_passed
        else "FAILED",
}


audit_path = (
    VALIDATION
    / "phase13_5_3_safety_hitl_audit.json"
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
    "PHASE 13.5.3 COMPLETE — "
    "SAFETY + HUMAN-IN-THE-LOOP VALIDATION"
)

print("\nSYSTEM")
print(" CareCompute")

print("\nPOPULATION")
print(f" {EXPECTED_POPULATION}")

print("\nCLINICAL SAFETY")
print(" Ground truth available: NO")
print(" Patient identifier available: NO")
print(" Diagnosis allowed: NO")
print(" Treatment recommendation allowed: NO")
print(" Medication recommendation allowed: NO")

print("\nSYSTEM MODIFICATION")
print(" Prediction modification allowed: NO")
print(" Router modification allowed: NO")
print(" Priority modification allowed: NO")
print(" Threshold modification allowed: NO")
print(" Review-budget modification allowed: NO")

print("\nAUTONOMY")
print(" Autonomous clinical action allowed: NO")
print(" Autonomous clinical action performed: NO")
print(" Human review required: YES")

print("\nFAIRNESS MONITOR")
print(" Individual decision modification: NO")
print(" Demographics used for routing: NO")
print(" Demographics used for priority: NO")
print(" Subgroup-specific threshold: NO")

print("\nVIOLATIONS")
print(f" {len(violations)}")

print("\nFROZEN INPUT MODIFICATION")
print(" NONE")

print("\nFINAL STATUS")

if overall_passed:

    print(
        " SAFETY_AND_HITL_VALIDATED"
    )

else:

    print(
        " SAFETY_AND_HITL_VALIDATION_FAILED"
    )


print(
    "\nAudit:",
    audit_path,
)

print(
    "Violation report:",
    violation_path,
)


if not overall_passed:

    raise SystemExit(
        "Phase 13.5.3 validation failed."
    )


banner(
    "NEXT: PHASE 13.5.4 — "
    "DETERMINISM AND REPLAY VALIDATION"
)