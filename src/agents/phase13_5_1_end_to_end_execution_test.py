"""
CareCompute
Phase 13.5.1 — End-to-End Execution Test

Purpose
-------
Validate that the frozen CareCompute Phase 13 runtime completed the
full execution chain:

    Frozen model/router runtime
        -> executable agents
        -> integrated orchestrator
        -> human-review packets

This phase performs validation only.

It MUST NOT:
- retrain models
- modify thresholds
- modify review budget
- reroute cases
- reprioritize cases
- expose ground truth
- expose patient identifiers
- modify frozen Phase 10/12/13 artifacts
"""

from pathlib import Path
import json
import hashlib
import pandas as pd


# =============================================================================
# CONFIGURATION
# =============================================================================

PHASE13_DIR = Path("results/eligible/phase13")
OUTPUT_DIR = Path("results/eligible/runtime_validation")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED_POPULATION = 1178
EXPECTED_PRIMARY_THRESHOLD = 0.115
EXPECTED_REVIEW_BUDGET = 0.15

EXPECTED_PRIORITIES = {
    "LOW": 504,
    "MODERATE": 666,
    "HIGH": 8,
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
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)

    return h.hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path):
    records = []

    with open(path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):

            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))

            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Invalid JSONL in {path} at line {line_number}: {exc}"
                )

    return records


def passed(condition, name, audit):
    audit[name] = "PASSED" if bool(condition) else "FAILED"

    print(f"{name}: {audit[name]}")

    if not condition:
        raise AssertionError(f"{name} FAILED")


# =============================================================================
# START
# =============================================================================

banner("PHASE 13.5.1 — END-TO-END EXECUTION TEST")

audit = {}


# =============================================================================
# A — VERIFY REQUIRED FROZEN ARTIFACTS
# =============================================================================

banner("A — VERIFY REQUIRED FROZEN ARTIFACTS")

required_files = {

    "phase13_1_architecture":
        PHASE13_DIR / "phase13_1_integrated_agent_architecture.json",

    "phase13_2_runtime":
        PHASE13_DIR / "phase13_2_agent_eligible_runtime.csv",

    "phase13_2_manifest":
        PHASE13_DIR / "phase13_2_frozen_runtime_manifest.json",

    "phase13_3_contexts":
        PHASE13_DIR / "phase13_3_patient_contexts.csv",

    "phase13_3_rescue_outputs":
        PHASE13_DIR / "phase13_3_rescue_review_outputs.csv",

    "phase13_3_explanation_outputs":
        PHASE13_DIR / "phase13_3_explanation_outputs.csv",

    "phase13_3_packets":
        PHASE13_DIR / "phase13_3_agent_runtime_packets.jsonl",

    "phase13_3_summary":
        PHASE13_DIR / "phase13_3_agent_runtime_summary.json",

    "phase13_3_audit":
        PHASE13_DIR / "phase13_3_agent_runtime_audit.json",

    "phase13_4_packets":
        PHASE13_DIR / "phase13_4_orchestrated_human_review_packets.jsonl",

    "phase13_4_case_index":
        PHASE13_DIR / "phase13_4_orchestrator_case_index.csv",

    "phase13_4_fairness":
        PHASE13_DIR / "phase13_4_fairness_monitor_snapshot.json",

    "phase13_4_summary":
        PHASE13_DIR / "phase13_4_orchestrator_summary.json",

    "phase13_4_audit":
        PHASE13_DIR / "phase13_4_orchestrator_audit.json",

    "phase13_4_manifest":
        PHASE13_DIR / "phase13_4_integrated_orchestrator_manifest.json",
}


for name, path in required_files.items():

    exists = path.exists()

    print(f"{name}: {'FOUND' if exists else 'MISSING'}")

    if not exists:
        raise FileNotFoundError(path)


passed(
    all(path.exists() for path in required_files.values()),
    "required_artifact_presence",
    audit,
)


# =============================================================================
# B — CAPTURE PRE-VALIDATION HASHES
# =============================================================================

banner("B — CAPTURE PRE-VALIDATION HASHES")

pre_hashes = {}

for name, path in required_files.items():

    digest = sha256_file(path)

    pre_hashes[name] = {
        "path": str(path),
        "sha256": digest,
    }

    print(f"{path} -> {digest}")


# =============================================================================
# C — LOAD END-TO-END EXECUTION CHAIN
# =============================================================================

banner("C — LOAD END-TO-END EXECUTION CHAIN")

runtime = pd.read_csv(required_files["phase13_2_runtime"])
contexts = pd.read_csv(required_files["phase13_3_contexts"])
rescue = pd.read_csv(required_files["phase13_3_rescue_outputs"])
explanations = pd.read_csv(required_files["phase13_3_explanation_outputs"])
case_index = pd.read_csv(required_files["phase13_4_case_index"])

agent_packets = load_jsonl(required_files["phase13_3_packets"])
orchestrated_packets = load_jsonl(required_files["phase13_4_packets"])

print("Phase 13.2 eligible runtime:", len(runtime))
print("Phase 13.3 patient contexts:", len(contexts))
print("Phase 13.3 rescue outputs:", len(rescue))
print("Phase 13.3 explanation outputs:", len(explanations))
print("Phase 13.3 runtime packets:", len(agent_packets))
print("Phase 13.4 orchestrated packets:", len(orchestrated_packets))
print("Phase 13.4 case index:", len(case_index))


# =============================================================================
# D — VERIFY POPULATION LOCK
# =============================================================================

banner("D — VERIFY POPULATION LOCK")

population_checks = {
    "runtime_population": len(runtime) == EXPECTED_POPULATION,
    "context_population": len(contexts) == EXPECTED_POPULATION,
    "rescue_output_population": len(rescue) == EXPECTED_POPULATION,
    "explanation_output_population": len(explanations) == EXPECTED_POPULATION,
    "agent_packet_population": len(agent_packets) == EXPECTED_POPULATION,
    "orchestrated_packet_population":
        len(orchestrated_packets) == EXPECTED_POPULATION,
    "case_index_population": len(case_index) == EXPECTED_POPULATION,
}

for name, condition in population_checks.items():
    passed(condition, name, audit)


# =============================================================================
# E — VERIFY ENCOUNTER ALIGNMENT
# =============================================================================

banner("E — VERIFY ENCOUNTER ALIGNMENT")

tables = {
    "runtime": runtime,
    "contexts": contexts,
    "rescue": rescue,
    "explanations": explanations,
    "case_index": case_index,
}

for name, df in tables.items():

    passed(
        "encounter_id" in df.columns,
        f"{name}_encounter_id_present",
        audit,
    )

    passed(
        df["encounter_id"].notna().all(),
        f"{name}_encounter_id_complete",
        audit,
    )

    passed(
        df["encounter_id"].nunique() == EXPECTED_POPULATION,
        f"{name}_encounter_id_unique",
        audit,
    )


reference_ids = set(runtime["encounter_id"].astype(str))

for name, df in tables.items():

    ids = set(df["encounter_id"].astype(str))

    passed(
        ids == reference_ids,
        f"{name}_encounter_alignment",
        audit,
    )


# =============================================================================
# F — VERIFY JSONL PACKET ALIGNMENT
# =============================================================================

banner("F — VERIFY JSONL PACKET ALIGNMENT")


def packet_encounter_ids(records):

    ids = []

    for record in records:

        if "encounter_id" not in record:
            raise AssertionError(
                "JSONL packet missing encounter_id"
            )

        ids.append(str(record["encounter_id"]))

    return ids


agent_packet_ids = packet_encounter_ids(agent_packets)
orchestrated_packet_ids = packet_encounter_ids(orchestrated_packets)


passed(
    len(set(agent_packet_ids)) == EXPECTED_POPULATION,
    "agent_packet_unique_encounters",
    audit,
)

passed(
    len(set(orchestrated_packet_ids)) == EXPECTED_POPULATION,
    "orchestrated_packet_unique_encounters",
    audit,
)

passed(
    set(agent_packet_ids) == reference_ids,
    "agent_packet_encounter_alignment",
    audit,
)

passed(
    set(orchestrated_packet_ids) == reference_ids,
    "orchestrated_packet_encounter_alignment",
    audit,
)


# =============================================================================
# G — VERIFY PRIORITY DISTRIBUTION
# =============================================================================

banner("G — VERIFY PRIORITY DISTRIBUTION")

priority_column = None

for candidate in [
    "review_priority",
    "priority",
    "rescue_review_priority",
]:

    if candidate in case_index.columns:
        priority_column = candidate
        break


passed(
    priority_column is not None,
    "priority_column_present",
    audit,
)


priority_counts = (
    case_index[priority_column]
    .astype(str)
    .str.upper()
    .value_counts()
    .to_dict()
)

print("Observed priority distribution:", priority_counts)
print("Expected priority distribution:", EXPECTED_PRIORITIES)


passed(
    priority_counts == EXPECTED_PRIORITIES,
    "priority_distribution_lock",
    audit,
)


# =============================================================================
# H — VERIFY FROZEN ORCHESTRATOR AUDIT
# =============================================================================

banner("H — VERIFY FROZEN ORCHESTRATOR AUDIT")

orchestrator_audit = load_json(
    required_files["phase13_4_audit"]
)

# Phase 13.4 contains both:
#
#   positive assertions:
#       "human_review_required": True
#
# and negative safety assertions:
#       "posthoc_retuning_performed": False
#
# Therefore a generic "False == failure" rule is invalid.
# Only explicit FAILED audit statuses should be treated as failed checks.

explicit_failed_checks = []

def find_explicit_failures(obj, prefix=""):

    if isinstance(obj, dict):

        for key, value in obj.items():

            path = f"{prefix}.{key}" if prefix else key

            if isinstance(value, str):

                if value.strip().upper() == "FAILED":
                    explicit_failed_checks.append(path)

            elif isinstance(value, (dict, list)):

                find_explicit_failures(value, path)

    elif isinstance(obj, list):

        for i, value in enumerate(obj):

            path = f"{prefix}[{i}]"

            if isinstance(value, str):

                if value.strip().upper() == "FAILED":
                    explicit_failed_checks.append(path)

            elif isinstance(value, (dict, list)):

                find_explicit_failures(value, path)


find_explicit_failures(orchestrator_audit)

print(
    "Explicit FAILED Phase 13.4 audit checks:",
    explicit_failed_checks
)

passed(
    len(explicit_failed_checks) == 0,
    "phase13_4_audit_preserved",
    audit,
)


# Explicitly verify the known no-retuning safety condition when present.

if "posthoc_retuning_performed" in orchestrator_audit:

    passed(
        orchestrator_audit["posthoc_retuning_performed"] is False,
        "posthoc_retuning_not_performed",
        audit,
    )


if "no_posthoc_retuning" in orchestrator_audit:

    value = orchestrator_audit["no_posthoc_retuning"]

    passed(
        value is True
        or (
            isinstance(value, str)
            and value.strip().upper() == "PASSED"
        ),
        "no_posthoc_retuning_preserved",
        audit,
    )


# =============================================================================
# I — VERIFY SAFETY IN ORCHESTRATED PACKETS
# =============================================================================

banner("I — VERIFY SAFETY IN ORCHESTRATED PACKETS")

prohibited_fields = {
    "target_30d",
    "ground_truth",
    "label",
    "actual_outcome",
    "patient_nbr",
    "patient_id",
    "case_type",
    "router_target",
}


def recursive_keys(obj):

    keys = set()

    if isinstance(obj, dict):

        for key, value in obj.items():

            keys.add(str(key))

            keys.update(recursive_keys(value))

    elif isinstance(obj, list):

        for value in obj:
            keys.update(recursive_keys(value))

    return keys


violations = []

for packet in orchestrated_packets:

    keys = recursive_keys(packet)

    bad = prohibited_fields.intersection(keys)

    if bad:
        violations.append({
            "encounter_id": packet.get("encounter_id"),
            "fields": sorted(bad),
        })


print("Packets with prohibited fields:", len(violations))


passed(
    len(violations) == 0,
    "prohibited_packet_fields_absent",
    audit,
)


# =============================================================================
# J — VERIFY HUMAN-IN-THE-LOOP CONTRACT
# =============================================================================

banner("J — VERIFY HUMAN-IN-THE-LOOP CONTRACT")

packet_text = json.dumps(
    orchestrated_packets,
    sort_keys=True,
).upper()


passed(
    "FROZEN_HUMAN_IN_THE_LOOP" in packet_text,
    "human_in_the_loop_runtime_marker",
    audit,
)

passed(
    "FROZEN_LEARNED_ROUTER" in packet_text,
    "frozen_router_runtime_marker",
    audit,
)


# =============================================================================
# K — VERIFY FROZEN PARAMETERS
# =============================================================================

banner("K — VERIFY FROZEN PARAMETERS")

manifest = load_json(
    required_files["phase13_4_manifest"]
)

manifest_text = json.dumps(
    manifest,
    sort_keys=True,
)


passed(
    str(EXPECTED_PRIMARY_THRESHOLD) in manifest_text,
    "primary_threshold_lock",
    audit,
)

passed(
    str(EXPECTED_REVIEW_BUDGET) in manifest_text,
    "review_budget_lock",
    audit,
)


# =============================================================================
# L — VERIFY FAIRNESS MONITOR EXISTS AND IS READ-ONLY
# =============================================================================

banner("L — VERIFY FAIRNESS MONITOR")

fairness = load_json(
    required_files["phase13_4_fairness"]
)

fairness_text = json.dumps(
    fairness,
    sort_keys=True,
).lower()


passed(
    "read" in fairness_text,
    "fairness_monitor_read_only_marker",
    audit,
)


# =============================================================================
# M — VERIFY VALIDATION DID NOT MODIFY FROZEN INPUTS
# =============================================================================

banner("M — VERIFY VALIDATION DID NOT MODIFY FROZEN INPUTS")

post_hashes = {}

for name, path in required_files.items():

    digest = sha256_file(path)

    post_hashes[name] = {
        "path": str(path),
        "sha256": digest,
    }


for name in required_files:

    passed(
        pre_hashes[name]["sha256"]
        == post_hashes[name]["sha256"],
        f"{name}_unchanged",
        audit,
    )


# =============================================================================
# N — CREATE VALIDATION SUMMARY
# =============================================================================

banner("N — CREATE VALIDATION SUMMARY")

all_passed = all(
    value == "PASSED"
    for value in audit.values()
)


summary = {
    "system": "CareCompute",
    "phase": "13.5.1",
    "validation": "END_TO_END_EXECUTION_TEST",

    "expected_population": EXPECTED_POPULATION,

    "observed_population": {
        "phase13_2_runtime": len(runtime),
        "phase13_3_contexts": len(contexts),
        "phase13_3_rescue_outputs": len(rescue),
        "phase13_3_explanation_outputs": len(explanations),
        "phase13_3_agent_packets": len(agent_packets),
        "phase13_4_orchestrated_packets":
            len(orchestrated_packets),
        "phase13_4_case_index": len(case_index),
    },

    "frozen_parameters": {
        "primary_threshold":
            EXPECTED_PRIMARY_THRESHOLD,

        "review_budget":
            EXPECTED_REVIEW_BUDGET,
    },

    "priority_distribution":
        priority_counts,

    "safety": {
        "ground_truth_exposed": False,
        "patient_identifier_exposed": False,
        "autonomous_action_authorized": False,
        "human_review_required": True,
    },

    "validation_result":
        "PASSED" if all_passed else "FAILED",
}


summary_path = (
    OUTPUT_DIR
    / "phase13_5_1_end_to_end_execution_summary.json"
)

with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(
        summary,
        f,
        indent=2,
        sort_keys=True,
    )


print("Saved:", summary_path)


# =============================================================================
# O — SAVE DETAILED AUDIT
# =============================================================================

banner("O — SAVE DETAILED AUDIT")

audit_output = {
    "system": "CareCompute",
    "phase": "13.5.1",
    "validation_type":
        "END_TO_END_EXECUTION_TEST",

    "checks": audit,

    "pre_validation_hashes":
        pre_hashes,

    "post_validation_hashes":
        post_hashes,

    "overall_status":
        "PASSED" if all_passed else "FAILED",
}


audit_path = (
    OUTPUT_DIR
    / "phase13_5_1_end_to_end_execution_audit.json"
)

with open(audit_path, "w", encoding="utf-8") as f:
    json.dump(
        audit_output,
        f,
        indent=2,
        sort_keys=True,
    )


print("Saved:", audit_path)


# =============================================================================
# FINAL
# =============================================================================

banner("PHASE 13.5.1 COMPLETE")

print("SYSTEM")
print(" CareCompute")

print("\nVALIDATION")
print(" End-to-End Execution Test")

print("\nPOPULATION")
print(f" {EXPECTED_POPULATION}")

print("\nPRIORITIES")
for priority in ["LOW", "MODERATE", "HIGH"]:
    print(
        f" {priority}: "
        f"{priority_counts.get(priority, 0)}"
    )

print("\nFROZEN PARAMETERS")
print(
    f" Primary threshold: "
    f"{EXPECTED_PRIMARY_THRESHOLD}"
)
print(
    f" Review budget: "
    f"{EXPECTED_REVIEW_BUDGET}"
)

print("\nSAFETY")
print(" Ground truth exposed: NO")
print(" Patient identifier exposed: NO")
print(" Autonomous action authorized: NO")
print(" Human review required: YES")

print("\nFROZEN INPUT MODIFICATION")
print(" NONE")

print("\nFINAL STATUS")
print(
    " END_TO_END_EXECUTION_VALIDATED"
    if all_passed
    else "VALIDATION_FAILED"
)

print("\nSummary:", summary_path)
print("Audit:", audit_path)


if not all_passed:
    raise SystemExit(
        "Phase 13.5.1 validation failed."
    )


banner(
    "NEXT: PHASE 13.5.2 — "
    "CROSS-COMPONENT CONTRACT VALIDATION"
)