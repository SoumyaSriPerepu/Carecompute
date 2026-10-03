from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
from statsmodels.stats.proportion import proportion_confint


# =============================================================================
# PATHS
# =============================================================================

DATA_PATH = Path(
    "results/eligible/final_test_end_to_end_patient_predictions.csv"
)

ELIGIBILITY_PATH = Path(
    "results/eligible/fairness/"
    "phase11_2_1_fairness_eligibility_manifest.json"
)

GROUP_PATH = Path(
    "results/eligible/fairness/"
    "phase11_2_1_group_eligibility.csv"
)

LOCAL_AGENT_PATH = Path(
    "results/eligible/agents/local_agent_outputs.csv"
)

EXPLANATION_AGENT_PATH = Path(
    "results/eligible/agents/explanation_agent_outputs.csv"
)

CASE_PACKET_PATH = Path(
    "results/eligible/agents/end_to_end_case_packets.csv"
)

OUTPUT_DIR = Path("results/eligible/fairness")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GROUP_OUTPUT = (
    OUTPUT_DIR /
    "phase11_2_3_compute_allocation_by_group.csv"
)

CASE_OUTPUT = (
    OUTPUT_DIR /
    "phase11_2_3_case_compute_allocation.csv"
)

AUDIT_OUTPUT = (
    OUTPUT_DIR /
    "phase11_2_3_compute_allocation_audit.json"
)


# =============================================================================
# SETTINGS
# =============================================================================

CI_LEVEL = 0.95
ALPHA = 1.0 - CI_LEVEL


# =============================================================================
# HELPERS
# =============================================================================

def section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def wilson_interval(successes, total):

    if total == 0:
        return np.nan, np.nan

    low, high = proportion_confint(
        successes,
        total,
        alpha=ALPHA,
        method="wilson",
    )

    return float(low), float(high)


# =============================================================================
# HEADER
# =============================================================================

section(
    "PHASE 11.2.3 — COMPUTE ALLOCATION FAIRNESS AUDIT"
)


# =============================================================================
# A — VERIFY INPUTS
# =============================================================================

section("A — VERIFY REQUIRED INPUTS")

required_paths = [
    DATA_PATH,
    ELIGIBILITY_PATH,
    GROUP_PATH,
    LOCAL_AGENT_PATH,
    EXPLANATION_AGENT_PATH,
    CASE_PACKET_PATH,
]

for p in required_paths:

    if not p.exists():
        raise FileNotFoundError(p)

    print("FOUND:", p)

print("Required input presence: PASSED")


# =============================================================================
# B — VERIFY FROZEN FAIRNESS ELIGIBILITY
# =============================================================================

section("B — VERIFY FAIRNESS ELIGIBILITY LOCK")

with ELIGIBILITY_PATH.open() as f:
    eligibility = json.load(f)

if (
    eligibility["status"]
    != "FAIRNESS_ELIGIBILITY_FROZEN"
):
    raise RuntimeError(
        "Phase 11.2.1 eligibility is not frozen."
    )

inventory = pd.read_csv(GROUP_PATH)

eligible_inventory = inventory[
    inventory["adequate_sample"] == True
].copy()

print(
    "Eligible groups:",
    len(eligible_inventory)
)

print(
    "Underpowered groups:",
    int(
        (
            inventory["adequate_sample"]
            == False
        ).sum()
    )
)

print("Eligibility lock: PASSED")


# =============================================================================
# C — LOAD FULL TEST POPULATION
# =============================================================================

section("C — LOAD FULL TEST POPULATION")

df = pd.read_csv(DATA_PATH)

required_columns = {
    "encounter_id",
    "actual_30d",
    "predicted_30d",
    "calibrated_probability",
    "uncertainty",
    "selected_for_review",
    "race",
    "gender",
    "age",
}

missing = required_columns - set(df.columns)

if missing:
    raise RuntimeError(
        f"Missing required columns: {sorted(missing)}"
    )

if len(df) != 15042:
    raise RuntimeError(
        "Expected frozen test population of 15042."
    )

if not df["encounter_id"].is_unique:
    raise RuntimeError(
        "Encounter IDs are not unique."
    )

selected = int(
    df["selected_for_review"].sum()
)

not_selected = int(
    (df["selected_for_review"] == 0).sum()
)

print("Test encounters:", len(df))
print("Selected for Rescue Review:", selected)
print("Not selected:", not_selected)

if selected != 1178:
    raise RuntimeError(
        "Frozen review-population lock failed."
    )

print("Population and routing lock: PASSED")


# =============================================================================
# D — VERIFY ACTUAL AGENT EXECUTION ARTIFACTS
# =============================================================================

section("D — VERIFY AGENT WORKFLOW EXECUTION")

local = pd.read_csv(LOCAL_AGENT_PATH)
explanation = pd.read_csv(EXPLANATION_AGENT_PATH)
packets = pd.read_csv(CASE_PACKET_PATH)

print("Local/Rescue Review outputs:", len(local))
print("Explanation Agent outputs:", len(explanation))
print("End-to-end case packets:", len(packets))

if len(local) != 1178:
    raise RuntimeError(
        "Expected 1178 local agent outputs."
    )

if len(explanation) != 1178:
    raise RuntimeError(
        "Expected 1178 explanation agent outputs."
    )

if len(packets) != 1178:
    raise RuntimeError(
        "Expected 1178 end-to-end packets."
    )

print("Agent workflow artifact counts: PASSED")


# =============================================================================
# E — DEFINE COMPUTE TELEMETRY BOUNDARY
# =============================================================================

section("E — COMPUTE TELEMETRY BOUNDARY")

print("Measured per-case routing allocation: AVAILABLE")
print("Observed agent-stage execution: AVAILABLE")
print("Measured per-case token counts: NOT CAPTURED")
print("Measured per-case latency: NOT CAPTURED")

print()
print(
    "No token counts or latency values will be "
    "estimated, imputed, or fabricated."
)

print()
print(
    "Primary compute-allocation measure:"
)

print(
    "  additional_workflow_allocated = selected_for_review"
)

print()
print(
    "Observed selected cases contain two downstream "
    "agent-output stages:"
)

print("  1. Rescue Review / local agent output")
print("  2. Explanation agent output")

print()
print(
    "Therefore agent_stage_executions is represented "
    "descriptively as 2 for selected cases and 0 for "
    "non-selected cases."
)

print(
    "This is a workflow-stage count, NOT an API-call, "
    "token, latency, FLOP, or cost measurement."
)


# =============================================================================
# F — BUILD CASE-LEVEL COMPUTE ALLOCATION TABLE
# =============================================================================

section("F — BUILD CASE-LEVEL COMPUTE ALLOCATION TABLE")

case_df = df[
    [
        "encounter_id",
        "actual_30d",
        "predicted_30d",
        "calibrated_probability",
        "uncertainty",
        "selected_for_review",
        "race",
        "gender",
        "age",
    ]
].copy()

case_df["additional_workflow_allocated"] = (
    case_df["selected_for_review"].astype(int)
)

case_df["observed_agent_stage_executions"] = (
    case_df["selected_for_review"].astype(int) * 2
)

case_df["token_telemetry_available"] = False
case_df["latency_telemetry_available"] = False

case_df.to_csv(
    CASE_OUTPUT,
    index=False
)

print("Rows:", len(case_df))

print(
    "Additional workflows allocated:",
    int(
        case_df[
            "additional_workflow_allocated"
        ].sum()
    )
)

print(
    "Observed downstream agent-stage executions:",
    int(
        case_df[
            "observed_agent_stage_executions"
        ].sum()
    )
)

print("Saved:", CASE_OUTPUT)


# =============================================================================
# G — COMPUTE GROUP ALLOCATION
# =============================================================================

section("G — COMPUTE ALLOCATION BY ELIGIBLE GROUP")

records = []

for attribute in ["race", "gender", "age"]:

    groups = eligible_inventory.loc[
        eligible_inventory["attribute"]
        == attribute,
        "group",
    ].tolist()

    for group in groups:

        if group == "MISSING":
            mask = df[attribute].isna()
        else:
            mask = (
                df[attribute].astype(str)
                == str(group)
            )

        g = case_df.loc[mask].copy()

        n = len(g)

        n_allocated = int(
            g[
                "additional_workflow_allocated"
            ].sum()
        )

        allocation_rate = (
            n_allocated / n
            if n
            else np.nan
        )

        ci_low, ci_high = wilson_interval(
            n_allocated,
            n,
        )

        mean_stage_executions = float(
            g[
                "observed_agent_stage_executions"
            ].mean()
        )

        records.append({
            "attribute": attribute,
            "group": group,
            "n_total": n,

            "additional_workflows_allocated":
                n_allocated,

            "allocation_rate":
                allocation_rate,

            "allocation_rate_ci_low":
                ci_low,

            "allocation_rate_ci_high":
                ci_high,

            "mean_observed_agent_stage_executions":
                mean_stage_executions,

            "mean_tokens":
                np.nan,

            "mean_latency":
                np.nan,

            "token_telemetry_status":
                "NOT_CAPTURED",

            "latency_telemetry_status":
                "NOT_CAPTURED",

            "interpret_as_demographic_group":
                not (
                    attribute == "race"
                    and group == "MISSING"
                ),
        })


group_results = pd.DataFrame(records)

group_results.to_csv(
    GROUP_OUTPUT,
    index=False
)

print(
    group_results[
        [
            "attribute",
            "group",
            "n_total",
            "additional_workflows_allocated",
            "allocation_rate",
            "allocation_rate_ci_low",
            "allocation_rate_ci_high",
            "mean_observed_agent_stage_executions",
            "token_telemetry_status",
            "latency_telemetry_status",
        ]
    ].to_string(index=False)
)

print()
print("Saved:", GROUP_OUTPUT)


# =============================================================================
# H — DESCRIPTIVE ALLOCATION GAPS
# =============================================================================

section("H — DESCRIPTIVE COMPUTE-ALLOCATION GAPS")

gap_records = []

for attribute in ["race", "gender", "age"]:

    attr = group_results[
        (
            group_results["attribute"]
            == attribute
        )
        &
        (
            group_results[
                "interpret_as_demographic_group"
            ]
            == True
        )
    ].copy()

    if len(attr) < 2:
        continue

    max_idx = attr["allocation_rate"].idxmax()
    min_idx = attr["allocation_rate"].idxmin()

    maximum = float(
        attr.loc[
            max_idx,
            "allocation_rate"
        ]
    )

    minimum = float(
        attr.loc[
            min_idx,
            "allocation_rate"
        ]
    )

    max_group = str(
        attr.loc[max_idx, "group"]
    )

    min_group = str(
        attr.loc[min_idx, "group"]
    )

    gap = maximum - minimum

    ratio = (
        maximum / minimum
        if minimum > 0
        else np.nan
    )

    gap_records.append({
        "attribute": attribute,
        "highest_allocation_group":
            max_group,
        "highest_allocation_rate":
            maximum,
        "lowest_allocation_group":
            min_group,
        "lowest_allocation_rate":
            minimum,
        "absolute_allocation_gap":
            gap,
        "max_to_min_ratio":
            ratio,
    })

    print()
    print(attribute.upper())

    print(
        "Highest allocation:",
        max_group,
        f"{maximum:.6f}",
    )

    print(
        "Lowest allocation:",
        min_group,
        f"{minimum:.6f}",
    )

    print(
        "Absolute gap:",
        f"{gap:.6f}",
    )

    print(
        "Max/min ratio:",
        f"{ratio:.6f}"
        if not np.isnan(ratio)
        else "NA",
    )


# =============================================================================
# I — GLOBAL COMPUTE ALLOCATION
# =============================================================================

section("I — GLOBAL COMPUTE ALLOCATION")

global_rate = selected / len(df)

global_stage_mean = float(
    case_df[
        "observed_agent_stage_executions"
    ].mean()
)

print(
    "Additional workflow allocation rate:",
    f"{global_rate:.6f}",
)

print(
    "Mean observed agent-stage executions per test case:",
    f"{global_stage_mean:.6f}",
)

print(
    "Measured mean tokens:",
    "UNAVAILABLE",
)

print(
    "Measured mean latency:",
    "UNAVAILABLE",
)


# =============================================================================
# J — INTERPRETATION BOUNDARY
# =============================================================================

section("J — INTERPRETATION BOUNDARY")

print(
    "Differences in workflow-allocation rates are "
    "descriptive and are not yet adjusted for case complexity."
)

print(
    "A demographic group receiving more additional workflow "
    "does not by itself establish preferential treatment, "
    "discrimination, benefit, or harm."
)

print(
    "Token and latency fairness cannot be directly evaluated "
    "because those telemetry fields were not captured by the "
    "frozen CareCompute execution."
)

print(
    "Observed agent-stage executions represent frozen workflow "
    "stages, not measured API calls or computational cost."
)

print(
    "The MISSING race category remains a missingness audit "
    "category and is not interpreted as a racial population."
)

print(
    "Phase 11.2.4 will test allocation after accounting "
    "for case complexity."
)

print(
    "This remains a retrospective fairness audit, "
    "not proof of clinical fairness."
)


# =============================================================================
# K — CREATE AUDIT ARTIFACT
# =============================================================================

section("K — CREATE COMPUTE ALLOCATION AUDIT ARTIFACT")

audit = {
    "phase": "11.2.3",

    "audit_name":
        "Compute Allocation Fairness Audit",

    "status":
        "COMPUTE_ALLOCATION_AUDIT_COMPLETE",

    "population": {
        "test_encounters":
            int(len(df)),
        "selected_for_review":
            selected,
        "not_selected":
            not_selected,
        "allocation_rate":
            float(global_rate),
    },

    "telemetry_availability": {
        "routing_allocation":
            "AVAILABLE",
        "observed_agent_stage_execution":
            "AVAILABLE",
        "per_case_tokens":
            "NOT_CAPTURED",
        "per_case_latency":
            "NOT_CAPTURED",
    },

    "compute_measure_definition": {
        "primary_measure":
            "selected_for_review",
        "primary_measure_interpretation":
            "allocation of additional frozen agent workflow",
        "observed_agent_stage_count":
            {
                "selected_case": 2,
                "non_selected_case": 0,
            },
        "agent_stage_count_is_api_call_count":
            False,
        "agent_stage_count_is_token_measure":
            False,
        "agent_stage_count_is_latency_measure":
            False,
    },

    "global_compute": {
        "mean_additional_workflow_allocation":
            float(global_rate),
        "mean_observed_agent_stage_executions":
            global_stage_mean,
        "mean_tokens":
            None,
        "mean_latency":
            None,
    },

    "descriptive_group_gaps":
        gap_records,

    "limitations": {
        "token_fairness_directly_auditable":
            False,
        "latency_fairness_directly_auditable":
            False,
        "token_values_estimated":
            False,
        "latency_values_estimated":
            False,
        "allocation_adjusted_for_case_complexity":
            False,
    },

    "claims_boundary": {
        "compute_allocation_equality_established":
            False,
        "clinical_fairness_established":
            False,
        "audit_only":
            True,
    },

    "integrity": {
        "phase10_modified":
            False,
        "phase11_2_1_modified":
            False,
        "phase11_2_2_modified":
            False,
        "input_sha256":
            sha256_file(DATA_PATH),
        "eligibility_sha256":
            sha256_file(ELIGIBILITY_PATH),
        "group_output_sha256":
            sha256_file(GROUP_OUTPUT),
        "case_output_sha256":
            sha256_file(CASE_OUTPUT),
    },

    "next_phase":
        "11.2.4 Complexity-Adjusted Compute Allocation Audit",
}


with AUDIT_OUTPUT.open("w") as f:
    json.dump(
        audit,
        f,
        indent=2,
    )

print("Audit artifact:", AUDIT_OUTPUT)


# =============================================================================
# L — FINAL VERIFICATION
# =============================================================================

section("L — FINAL VERIFICATION")

with AUDIT_OUTPUT.open() as f:
    saved = json.load(f)


checks = {
    "status":
        saved["status"]
        == "COMPUTE_ALLOCATION_AUDIT_COMPLETE",

    "population":
        saved["population"][
            "test_encounters"
        ]
        == 15042,

    "review_lock":
        saved["population"][
            "selected_for_review"
        ]
        == 1178,

    "tokens_not_fabricated":
        (
            saved["telemetry_availability"][
                "per_case_tokens"
            ]
            == "NOT_CAPTURED"
            and
            saved["limitations"][
                "token_values_estimated"
            ]
            is False
        ),

    "latency_not_fabricated":
        (
            saved["telemetry_availability"][
                "per_case_latency"
            ]
            == "NOT_CAPTURED"
            and
            saved["limitations"][
                "latency_values_estimated"
            ]
            is False
        ),

    "agent_stage_not_mislabeled":
        (
            saved[
                "compute_measure_definition"
            ][
                "agent_stage_count_is_api_call_count"
            ]
            is False
        ),

    "complexity_not_yet_adjusted":
        saved["limitations"][
            "allocation_adjusted_for_case_complexity"
        ]
        is False,

    "no_fairness_claim":
        saved["claims_boundary"][
            "clinical_fairness_established"
        ]
        is False,

    "phase10_unchanged":
        saved["integrity"][
            "phase10_modified"
        ]
        is False,

    "group_artifact":
        GROUP_OUTPUT.exists(),

    "case_artifact":
        CASE_OUTPUT.exists(),
}


for name, passed in checks.items():

    print(
        name + ":",
        "PASSED" if passed else "FAILED"
    )


if not all(checks.values()):

    raise RuntimeError(
        "Phase 11.2.3 final verification failed."
    )


# =============================================================================
# COMPLETE
# =============================================================================

section(
    "PHASE 11.2.3 COMPLETE — COMPUTE ALLOCATION AUDIT PASSED"
)

print(
    "Full test population:",
    len(df)
)

print(
    "Additional workflow allocated:",
    selected
)

print(
    "Additional workflow allocation rate:",
    f"{global_rate:.2%}"
)

print(
    "Token telemetry captured: NO"
)

print(
    "Latency telemetry captured: NO"
)

print(
    "Fabricated telemetry introduced: NO"
)

print(
    "Case-complexity adjustment performed: NO"
)

print(
    "Clinical fairness established: NO"
)

print(
    "Phase 10 frozen system modified: NO"
)

print()
print(
    "NEXT: 11.2.4 — COMPLEXITY-ADJUSTED "
    "COMPUTE ALLOCATION AUDIT"
)
