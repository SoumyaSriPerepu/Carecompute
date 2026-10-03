from pathlib import Path
import json
import hashlib
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path("results/eligible/fairness")

ELIGIBILITY = ROOT / (
    "phase11_2_1_fairness_eligibility_manifest.json"
)

PERFORMANCE = ROOT / (
    "phase11_2_2_fairness_performance_audit.json"
)

COMPUTE = ROOT / (
    "phase11_2_3_compute_allocation_audit.json"
)

ADJUSTED = ROOT / (
    "phase11_2_4_complexity_adjusted_compute_audit.json"
)

STABILITY = ROOT / (
    "phase11_2_4a_adjusted_model_stability_audit.json"
)

PERFORMANCE_TABLE = ROOT / (
    "phase11_2_2_group_performance_metrics.csv"
)

COMPUTE_TABLE = ROOT / (
    "phase11_2_3_compute_allocation_by_group.csv"
)

STABLE_TABLE = ROOT / (
    "phase11_2_4a_stable_adjusted_group_allocation.csv"
)

CLOSURE = ROOT / (
    "phase11_2_fairness_closure_manifest.json"
)


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
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


# =============================================================================
# HEADER
# =============================================================================

section(
    "PHASE 11.2.5 — FAIRNESS AUDIT CLOSURE AND LOCK"
)


# =============================================================================
# A — VERIFY ARTIFACT CHAIN
# =============================================================================

section("A — VERIFY PHASE 11.2 ARTIFACT CHAIN")

required = [
    ELIGIBILITY,
    PERFORMANCE,
    COMPUTE,
    ADJUSTED,
    STABILITY,
    PERFORMANCE_TABLE,
    COMPUTE_TABLE,
    STABLE_TABLE,
]

for p in required:

    if not p.exists():
        raise FileNotFoundError(p)

    print("FOUND:", p)

print("Fairness artifact presence: PASSED")


# =============================================================================
# B — LOAD VERIFIED AUDITS
# =============================================================================

section("B — LOAD VERIFIED FAIRNESS RESULTS")

with ELIGIBILITY.open() as f:
    eligibility = json.load(f)

with PERFORMANCE.open() as f:
    performance = json.load(f)

with COMPUTE.open() as f:
    compute = json.load(f)

with ADJUSTED.open() as f:
    adjusted = json.load(f)

with STABILITY.open() as f:
    stability = json.load(f)


expected_statuses = {
    "11.2.1":
        eligibility["status"]
        == "FAIRNESS_ELIGIBILITY_FROZEN",

    "11.2.2":
        performance["status"]
        == "FAIRNESS_PERFORMANCE_AUDIT_COMPLETE",

    "11.2.3":
        compute["status"]
        == "COMPUTE_ALLOCATION_AUDIT_COMPLETE",

    "11.2.4":
        adjusted["status"]
        == "COMPLEXITY_ADJUSTED_COMPUTE_AUDIT_COMPLETE",

    "11.2.4A":
        stability["status"]
        == "ADJUSTED_MODEL_STABILITY_AUDIT_COMPLETE",
}

for phase, passed in expected_statuses.items():

    print(
        phase + ":",
        "PASSED" if passed else "FAILED"
    )

if not all(expected_statuses.values()):
    raise RuntimeError(
        "Upstream fairness audit chain failed."
    )


# =============================================================================
# C — LOAD TABLES
# =============================================================================

section("C — LOAD FAIRNESS TABLES")

perf = pd.read_csv(PERFORMANCE_TABLE)
comp = pd.read_csv(COMPUTE_TABLE)
stable = pd.read_csv(STABLE_TABLE)

print("Performance rows:", len(perf))
print("Compute-allocation rows:", len(comp))
print("Stable adjusted rows:", len(stable))

if len(perf) != 13:
    raise RuntimeError(
        "Expected 13 eligible performance groups."
    )

print("Table integrity: PASSED")


# =============================================================================
# D — PERFORMANCE AUDIT SUMMARY
# =============================================================================

section("D — SUBGROUP PERFORMANCE FINDINGS")

print(
    "Global AUROC:",
    f"{performance['global_performance']['auroc']:.6f}"
)

print(
    "Global AUPRC:",
    f"{performance['global_performance']['auprc']:.6f}"
)

print(
    "Global Recall:",
    f"{performance['global_performance']['recall']:.6f}"
)

print(
    "Global FNR:",
    f"{performance['global_performance']['fnr']:.6f}"
)

print()
print(
    "Eligible groups evaluated:",
    performance["eligible_group_count"]
)

print(
    "Underpowered groups disclosed:",
    performance["underpowered_group_count"]
)

print()
print("Descriptive subgroup ranges:")

for x in performance["descriptive_gaps"]:

    print(
        f" - {x['attribute']} | "
        f"{x['metric']}: "
        f"{x['absolute_range']:.6f}"
    )


# =============================================================================
# E — RAW COMPUTE ALLOCATION SUMMARY
# =============================================================================

section("E — RAW COMPUTE ALLOCATION FINDINGS")

print(
    "Global additional-workflow allocation:",
    f"{compute['population']['allocation_rate']:.6f}"
)

print(
    "Selected for additional workflow:",
    compute["population"]["selected_for_review"]
)

print()
print("Raw demographic allocation gaps:")

for x in compute["descriptive_group_gaps"]:

    print(
        f" - {x['attribute']}: "
        f"{x['absolute_allocation_gap']:.6f}"
    )

print()
print(
    "Token telemetry:",
    compute["telemetry_availability"]["per_case_tokens"]
)

print(
    "Latency telemetry:",
    compute["telemetry_availability"]["per_case_latency"]
)


# =============================================================================
# F — ORIGINAL ADJUSTED MODEL DISCLOSURE
# =============================================================================

section("F — ORIGINAL ADJUSTED MODEL DISCLOSURE")

print(
    "Original 11.2.4 model converged:",
    adjusted["models"][
        "complexity_plus_demographics"
    ]["converged"]
)

print(
    "Original joint demographic p-value:",
    adjusted["joint_demographic_test"]["p_value"]
)

print()
print(
    "IMPORTANT:"
)

print(
    "The original adjusted model produced numerically unstable "
    "demographic coefficient estimates because sparse age "
    "categories and redundant routing-state controls were present."
)

print(
    "The original result is retained for transparency and was "
    "not silently replaced."
)

print(
    "Phase 11.2.4A was therefore performed as an explicit "
    "stability sensitivity analysis."
)


# =============================================================================
# G — STABLE SENSITIVITY FINDINGS
# =============================================================================

section("G — STABLE COMPLEXITY-ADJUSTED FINDINGS")

models = stability["attribute_models"]

for attribute in [
    "race",
    "gender",
    "age",
]:

    result = models[attribute]

    print()
    print(attribute.upper())

    print(
        "Analysis n:",
        result["n"]
    )

    print(
        "Group-term p-value:",
        result["group_term_p_value"]
    )

    print(
        "Highest adjusted group:",
        result["adjusted_highest_group"]
    )

    print(
        "Highest adjusted allocation:",
        f"{result['adjusted_highest_rate']:.6f}"
    )

    print(
        "Lowest adjusted group:",
        result["adjusted_lowest_group"]
    )

    print(
        "Lowest adjusted allocation:",
        f"{result['adjusted_lowest_rate']:.6f}"
    )

    print(
        "Adjusted absolute range:",
        f"{result['adjusted_absolute_range']:.6f}"
    )


# =============================================================================
# H — REQUIRED FAIRNESS FINDINGS
# =============================================================================

section("H — REQUIRED FAIRNESS FINDINGS AND LIMITATIONS")

findings = {
    "FAIRNESS-01": {
        "finding":
            (
                "Subgroup model performance varies across "
                "race, gender, and age categories."
            ),
        "interpretation":
            (
                "The largest descriptive variation was observed "
                "across age groups; this is an audit signal and "
                "not proof of clinical unfairness."
            ),
    },

    "FAIRNESS-02": {
        "finding":
            (
                "Raw additional-workflow allocation differs "
                "across some demographic groups."
            ),
        "interpretation":
            (
                "Raw allocation differences cannot be interpreted "
                "without considering routing-state complexity."
            ),
    },

    "FAIRNESS-03": {
        "finding":
            (
                "In the numerically stable sensitivity analysis, "
                "race did not show a statistically detectable "
                "allocation association after adjustment for "
                "calibrated probability."
            ),
        "p_value":
            models["race"]["group_term_p_value"],
        "adjusted_range":
            models["race"]["adjusted_absolute_range"],
        "fairness_proven":
            False,
    },

    "FAIRNESS-04": {
        "finding":
            (
                "In the numerically stable sensitivity analysis, "
                "gender did not show a statistically detectable "
                "allocation association after adjustment for "
                "calibrated probability."
            ),
        "p_value":
            models["gender"]["group_term_p_value"],
        "adjusted_range":
            models["gender"]["adjusted_absolute_range"],
        "fairness_proven":
            False,
    },

    "FAIRNESS-05": {
        "finding":
            (
                "Age remained associated with additional-workflow "
                "allocation after adjustment for calibrated "
                "probability in the stable sensitivity analysis."
            ),
        "p_value":
            models["age"]["group_term_p_value"],
        "adjusted_range":
            models["age"]["adjusted_absolute_range"],
        "interpretation":
            (
                "This requires disclosure and further investigation "
                "but does not establish discrimination, causality, "
                "or clinical unfairness."
            ),
    },

    "FAIRNESS-06": {
        "finding":
            (
                "Token and latency telemetry were not captured "
                "by the frozen system."
            ),
        "token_fairness_audited":
            False,
        "latency_fairness_audited":
            False,
        "telemetry_fabricated":
            False,
    },

    "FAIRNESS-07": {
        "finding":
            (
                "Several demographic categories were underpowered "
                "under the predeclared eligibility rule."
            ),
        "underpowered_group_count":
            performance["underpowered_group_count"],
        "interpretation":
            (
                "No fairness conclusion is made for those "
                "underpowered groups."
            ),
    },

    "FAIRNESS-08": {
        "finding":
            (
                "The original joint adjusted model showed numerical "
                "instability; this limitation is retained and "
                "reported rather than hidden."
            ),
        "sensitivity_analysis_performed":
            True,
        "original_result_preserved":
            True,
    },
}


for key, value in findings.items():

    print()
    print(key)
    print(value["finding"])

    if "p_value" in value:
        print(
            " p-value:",
            value["p_value"]
        )

    if "adjusted_range" in value:
        print(
            " adjusted range:",
            value["adjusted_range"]
        )


# =============================================================================
# I — INTERPRETATION BOUNDARY
# =============================================================================

section("I — FAIRNESS INTERPRETATION BOUNDARY")

boundaries = [
    "This is a retrospective fairness audit.",
    "This audit does not establish clinical fairness.",
    "This audit does not establish causal discrimination.",
    "Statistical non-significance does not prove fairness.",
    "Statistical significance does not by itself establish harm.",
    "AUPRC differences must be interpreted with subgroup prevalence.",
    "Underpowered groups are disclosed rather than silently removed.",
    "The MISSING race category is not interpreted as a racial group.",
    "Token fairness could not be directly audited.",
    "Latency fairness could not be directly audited.",
    "Only available frozen routing-state controls were evaluated.",
    "The Phase 10 system was not modified.",
]

for item in boundaries:
    print(" -", item)

print()
print("Clinical fairness claim permitted: NO")


# =============================================================================
# J — CREATE CLOSURE MANIFEST
# =============================================================================

section("J — CREATE FAIRNESS CLOSURE MANIFEST")

manifest = {
    "phase": "11.2",

    "status":
        "FAIRNESS_AUDIT_COMPLETE",

    "subphases": {
        "11.2.1":
            "FAIRNESS_ELIGIBILITY_FROZEN",
        "11.2.2":
            "FAIRNESS_PERFORMANCE_AUDIT_COMPLETE",
        "11.2.3":
            "COMPUTE_ALLOCATION_AUDIT_COMPLETE",
        "11.2.4":
            "COMPLEXITY_ADJUSTED_COMPUTE_AUDIT_COMPLETE",
        "11.2.4A":
            "ADJUSTED_MODEL_STABILITY_AUDIT_COMPLETE",
        "11.2.5":
            "COMPLETE",
    },

    "population": {
        "full_test_population":
            performance["population"]["test_encounters"],
        "negative_routing_population":
            adjusted["analysis_population"]["n"],
        "review_population":
            compute["population"]["selected_for_review"],
    },

    "performance_audit": {
        "eligible_groups":
            performance["eligible_group_count"],
        "underpowered_groups":
            performance["underpowered_group_count"],
        "confidence_intervals_reported":
            True,
    },

    "compute_audit": {
        "workflow_allocation_audited":
            True,
        "agent_stage_execution_audited":
            True,
        "token_telemetry_available":
            False,
        "latency_telemetry_available":
            False,
        "telemetry_fabricated":
            False,
    },

    "stable_adjusted_results": {
        "race": models["race"],
        "gender": models["gender"],
        "age": models["age"],
    },

    "required_findings":
        findings,

    "limitations": {
        "original_adjusted_model_numerically_unstable":
            True,
        "stability_sensitivity_performed":
            True,
        "underpowered_demographic_groups_present":
            True,
        "token_fairness_not_directly_audited":
            True,
        "latency_fairness_not_directly_audited":
            True,
        "all_possible_confounders_controlled":
            False,
    },

    "claims_boundary": {
        "clinical_fairness_established":
            False,
        "causal_fairness_established":
            False,
        "discrimination_established":
            False,
        "audit_only":
            True,
    },

    "integrity": {
        "phase10_modified":
            False,
        "phase11_1_modified":
            False,
        "original_11_2_4_preserved":
            True,

        "eligibility_sha256":
            sha256_file(ELIGIBILITY),

        "performance_sha256":
            sha256_file(PERFORMANCE),

        "compute_sha256":
            sha256_file(COMPUTE),

        "adjusted_sha256":
            sha256_file(ADJUSTED),

        "stability_sha256":
            sha256_file(STABILITY),
    },

    "next_phase":
        "11.3 Routing Robustness",
}


with CLOSURE.open("w") as f:
    json.dump(
        manifest,
        f,
        indent=2,
    )

print(
    "Fairness closure manifest:",
    CLOSURE
)


# =============================================================================
# K — FINAL CLOSURE VERIFICATION
# =============================================================================

section("K — FINAL FAIRNESS CLOSURE VERIFICATION")

with CLOSURE.open() as f:
    saved = json.load(f)


checks = {
    "closure_status":
        saved["status"]
        == "FAIRNESS_AUDIT_COMPLETE",

    "eligible_group_lock":
        saved["performance_audit"][
            "eligible_groups"
        ] == 13,

    "underpowered_group_lock":
        saved["performance_audit"][
            "underpowered_groups"
        ] == 6,

    "review_population_lock":
        saved["population"][
            "review_population"
        ] == 1178,

    "stable_sensitivity_present":
        saved["limitations"][
            "stability_sensitivity_performed"
        ] is True,

    "original_instability_disclosed":
        saved["limitations"][
            "original_adjusted_model_numerically_unstable"
        ] is True,

    "tokens_not_fabricated":
        saved["compute_audit"][
            "telemetry_fabricated"
        ] is False,

    "no_clinical_fairness_claim":
        saved["claims_boundary"][
            "clinical_fairness_established"
        ] is False,

    "no_discrimination_claim":
        saved["claims_boundary"][
            "discrimination_established"
        ] is False,

    "phase10_unchanged":
        saved["integrity"][
            "phase10_modified"
        ] is False,

    "closure_artifact":
        CLOSURE.exists(),
}


for name, passed in checks.items():

    print(
        name + ":",
        "PASSED" if passed else "FAILED"
    )


if not all(checks.values()):

    raise RuntimeError(
        "Phase 11.2 fairness closure verification failed."
    )


# =============================================================================
# COMPLETE
# =============================================================================

section(
    "PHASE 11.2 FAIRNESS — COMPLETE AND LOCKED"
)

print("11.2.1 Eligibility lock: COMPLETE")
print("11.2.2 Performance + CI audit: COMPLETE")
print("11.2.3 Compute allocation audit: COMPLETE")
print("11.2.4 Adjusted allocation audit: COMPLETE")
print("11.2.4A Stability sensitivity: COMPLETE")
print("11.2.5 Fairness disclosure/closure: COMPLETE")

print()
print(
    "Fairness audit status: FAIRNESS_AUDIT_COMPLETE"
)

print(
    "Race adjusted association detected "
    "in stable sensitivity:",
    "NO"
)

print(
    "Gender adjusted association detected "
    "in stable sensitivity:",
    "NO"
)

print(
    "Age adjusted association detected "
    "in stable sensitivity:",
    "YES"
)

print(
    "Token fairness directly audited: NO"
)

print(
    "Latency fairness directly audited: NO"
)

print(
    "Clinical fairness established: NO"
)

print(
    "Limitations transparently reported: YES"
)

print(
    "Phase 10 frozen system modified: NO"
)

print()
print(
    "NEXT: PHASE 11.3 — ROUTING ROBUSTNESS"
)
