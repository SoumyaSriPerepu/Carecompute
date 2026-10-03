"""
Phase 10.4.4 — Explanation Agent Freeze

Freezes the validated CareCompute Explanation Agent subsystem after
successful completion of the independent Phase 10.4.3 fidelity and
safety audit.

No model, router, threshold, review-budget, rule, priority, or
explanation output is modified in this phase.
"""

import hashlib
import json
from datetime import datetime, timezone
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

FREEZE_PATH = BASE / "explanation_agent_freeze_manifest.json"


# =============================================================================
# EXPECTED FROZEN VALUES
# =============================================================================

EXPECTED_POPULATION = 1178

EXPECTED_CONTEXT_SCHEMA = "10.2"
EXPECTED_RULE_VERSION = "10.3.4"
EXPECTED_CONTRACT_VERSION = "10.4.1"
EXPECTED_OUTPUT_SCHEMA = "10.4.2"

EXPECTED_THRESHOLD = 0.115
EXPECTED_REVIEW_BUDGET = 0.15

EXPECTED_PRIORITY_DISTRIBUTION = {
    "LOW": 777,
    "MODERATE": 302,
    "HIGH": 99
}

EXPECTED_ZERO_SIGNAL_CASES = 25


# =============================================================================
# HELPERS
# =============================================================================

def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path):
    records = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                records.append(json.loads(line))

    return records


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 80)
    print("PHASE 10.4.4 — EXPLANATION AGENT FREEZE")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # A — VERIFY REQUIRED ARTIFACTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("A — VERIFY REQUIRED ARTIFACTS")
    print("=" * 80)

    required_paths = [
        CONTEXT_PATH,
        RULES_PATH,
        CONTRACT_PATH,
        OUTPUT_PATH,
        AUDIT_PATH,
    ]

    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(
                f"Required artifact missing: {path}"
            )

        print(f"FOUND: {path}")

    print("Required artifacts: PASSED")

    # -------------------------------------------------------------------------
    # B — LOAD ARTIFACTS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("B — LOAD VALIDATED SUBSYSTEM")
    print("=" * 80)

    contexts = load_jsonl(CONTEXT_PATH)
    rules = load_json(RULES_PATH)
    contract = load_json(CONTRACT_PATH)
    outputs = load_jsonl(OUTPUT_PATH)
    audit = load_json(AUDIT_PATH)

    print("Contexts:", len(contexts))
    print("Outputs:", len(outputs))
    print("Rule version:", rules["rule_version"])
    print("Contract version:", contract["contract_version"])
    print("Audit status:", audit["status"])

    # -------------------------------------------------------------------------
    # C — VERIFY FREEZE PRECONDITIONS
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("C — VERIFY FREEZE PRECONDITIONS")
    print("=" * 80)

    assert len(contexts) == EXPECTED_POPULATION
    assert len(outputs) == EXPECTED_POPULATION

    assert all(
        x["schema_version"] == EXPECTED_CONTEXT_SCHEMA
        for x in contexts
    )

    assert all(
        x["schema_version"] == EXPECTED_OUTPUT_SCHEMA
        for x in outputs
    )

    assert rules["rule_version"] == EXPECTED_RULE_VERSION
    assert rules["status"] == "FROZEN"

    assert (
        contract["contract_version"]
        == EXPECTED_CONTRACT_VERSION
    )

    assert audit["phase"] == "10.4.3"
    assert audit["status"] == "PASSED"

    assert (
        rules["frozen_primary_model_threshold"]
        == EXPECTED_THRESHOLD
    )

    assert (
        rules["frozen_router_review_budget"]
        == EXPECTED_REVIEW_BUDGET
    )

    observed_priorities = {
        "LOW": 0,
        "MODERATE": 0,
        "HIGH": 0,
    }

    for output in outputs:
        observed_priorities[
            output["review_priority"]
        ] += 1

    assert (
        observed_priorities
        == EXPECTED_PRIORITY_DISTRIBUTION
    )

    assert (
        audit["zero_signal_cases"]
        == EXPECTED_ZERO_SIGNAL_CASES
    )

    assert audit["violations"]["priority_mismatches"] == 0
    assert audit["violations"]["signal_mismatches"] == 0
    assert audit["violations"]["untriggered_signal_claims"] == 0
    assert audit["violations"]["invalid_reason_codes"] == 0
    assert audit["violations"]["summary_mismatches"] == 0
    assert audit["violations"]["zero_signal_errors"] == 0
    assert audit["violations"]["prohibited_field_findings"] == 0
    assert audit["violations"]["demographic_findings"] == 0
    assert audit["violations"]["missing_human_review"] == 0
    assert audit["violations"]["missing_uncertainty_guardrail"] == 0
    assert audit["violations"]["high_priority_errors"] == 0

    print("Population lock: PASSED")
    print("Schema lock: PASSED")
    print("Rule-version lock: PASSED")
    print("Contract-version lock: PASSED")
    print("Independent audit requirement: PASSED")
    print("Primary threshold lock: PASSED")
    print("Review-budget lock: PASSED")
    print("Priority distribution lock: PASSED")
    print("Safety-violation requirement: PASSED")

    # -------------------------------------------------------------------------
    # D — VERIFY AUDIT HASHES
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("D — VERIFY PHASE 10.4.3 ARTIFACT HASHES")
    print("=" * 80)

    current_hashes = {
        "patient_agent_contexts.jsonl":
            sha256_file(CONTEXT_PATH),

        "rescue_review_agent_frozen_rules.json":
            sha256_file(RULES_PATH),

        "explanation_agent_output_contract.json":
            sha256_file(CONTRACT_PATH),

        "explanation_agent_outputs.jsonl":
            sha256_file(OUTPUT_PATH),
    }

    audited_hashes = audit["artifact_sha256"]

    for name, current_hash in current_hashes.items():

        audited_hash = audited_hashes[name]

        print(f"{name}")
        print(f"  audited: {audited_hash}")
        print(f"  current: {current_hash}")

        assert current_hash == audited_hash

    print("Artifact integrity since independent audit: PASSED")

    # -------------------------------------------------------------------------
    # E — DEFINE IMMUTABLE SUBSYSTEM
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("E — DEFINE IMMUTABLE EXPLANATION SUBSYSTEM")
    print("=" * 80)

    immutable_components = {
        "population": EXPECTED_POPULATION,

        "context_schema":
            EXPECTED_CONTEXT_SCHEMA,

        "rule_version":
            EXPECTED_RULE_VERSION,

        "contract_version":
            EXPECTED_CONTRACT_VERSION,

        "output_schema":
            EXPECTED_OUTPUT_SCHEMA,

        "primary_model_threshold":
            EXPECTED_THRESHOLD,

        "rescue_review_budget":
            EXPECTED_REVIEW_BUDGET,

        "priority_distribution":
            EXPECTED_PRIORITY_DISTRIBUTION,

        "zero_signal_cases":
            EXPECTED_ZERO_SIGNAL_CASES,

        "signal_rules":
            rules["signal_rules"],

        "signal_weights":
            rules["signal_weights"],

        "priority_rules":
            rules["priority_rules"],

        "maximum_signal_explanations":
            contract["constraints"][
                "maximum_signal_explanations"
            ],
    }

    print("Population:", EXPECTED_POPULATION)
    print(
        "Primary threshold:",
        EXPECTED_THRESHOLD
    )
    print(
        "Review budget:",
        EXPECTED_REVIEW_BUDGET
    )
    print(
        "Priority distribution:",
        EXPECTED_PRIORITY_DISTRIBUTION
    )
    print(
        "Zero-signal cases:",
        EXPECTED_ZERO_SIGNAL_CASES
    )

    # -------------------------------------------------------------------------
    # F — CREATE FREEZE MANIFEST
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("F — CREATE FREEZE MANIFEST")
    print("=" * 80)

    freeze_manifest = {
        "phase": "10.4.4",

        "agent_name":
            "CareCompute Explanation Agent",

        "status": "FROZEN",

        "freeze_timestamp_utc":
            datetime.now(timezone.utc).isoformat(),

        "purpose":
            "Freeze the independently validated deterministic "
            "Explanation Agent subsystem.",

        "immutable_components":
            immutable_components,

        "artifact_sha256":
            current_hashes,

        "independent_audit": {
            "phase": audit["phase"],
            "status": audit["status"],
            "audit_artifact":
                str(AUDIT_PATH),
            "audit_sha256":
                sha256_file(AUDIT_PATH),
        },

        "constraints": {
            "ground_truth_allowed": False,
            "diagnosis_allowed": False,
            "treatment_recommendation_allowed": False,
            "medication_recommendation_allowed": False,
            "prediction_modification_allowed": False,
            "probability_modification_allowed": False,
            "router_modification_allowed": False,
            "threshold_modification_allowed": False,
            "review_budget_modification_allowed": False,
            "demographic_causal_explanation_allowed": False,
            "autonomous_clinical_action_allowed": False,
            "human_review_required": True,
        },

        "change_control": {
            "frozen": True,

            "rule_changes_require_new_version": True,

            "signal_weight_changes_require_new_version": True,

            "priority_rule_changes_require_new_version": True,

            "template_changes_require_new_version": True,

            "contract_changes_require_new_version": True,

            "upstream_model_changes_require_revalidation": True,

            "router_changes_require_revalidation": True,

            "threshold_changes_require_revalidation": True,

            "review_budget_changes_require_revalidation": True,
        },

        "validation_summary": {
            "population_complete": True,
            "encounter_alignment_passed": True,
            "priority_fidelity_passed": True,
            "signal_fidelity_passed": True,
            "contract_safety_passed": True,
            "demographic_causal_language_excluded": True,
            "human_review_guardrail_passed": True,
            "uncertainty_guardrail_passed": True,
            "artifact_integrity_passed": True,
        },
    }

    with FREEZE_PATH.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            freeze_manifest,
            f,
            indent=2,
            sort_keys=True
        )

    print("Freeze manifest:", FREEZE_PATH)

    # -------------------------------------------------------------------------
    # G — VERIFY WRITTEN MANIFEST
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("G — VERIFY FREEZE MANIFEST")
    print("=" * 80)

    written_manifest = load_json(FREEZE_PATH)

    assert written_manifest["status"] == "FROZEN"

    assert (
        written_manifest["immutable_components"]
        ["population"]
        == EXPECTED_POPULATION
    )

    assert (
        written_manifest["constraints"]
        ["human_review_required"]
        is True
    )

    assert (
        written_manifest["change_control"]
        ["frozen"]
        is True
    )

    print("Manifest status: FROZEN")
    print("Manifest verification: PASSED")

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("PHASE 10.4.4 COMPLETE — EXPLANATION AGENT FROZEN")
    print("=" * 80)

    print(
        "\nThe validated Explanation Agent subsystem is now frozen."
    )

    print(
        "Any future change to its rules, weights, priority logic, "
        "templates, contract, or upstream frozen decisions requires "
        "versioning and revalidation."
    )


if __name__ == "__main__":
    main()
