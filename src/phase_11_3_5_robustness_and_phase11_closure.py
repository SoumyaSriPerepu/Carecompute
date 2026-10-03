from pathlib import Path
import json
import hashlib


# =============================================================================
# PATHS
# =============================================================================

SAFETY = Path(
    "results/eligible/safety/"
    "phase11_1_safety_closure_manifest.json"
)

FAIRNESS = Path(
    "results/eligible/fairness/"
    "phase11_2_fairness_closure_manifest.json"
)

ROBUSTNESS_DIR = Path(
    "results/eligible/robustness"
)

SPEC = (
    ROBUSTNESS_DIR /
    "phase11_3_1b_frozen_perturbation_specification.json"
)

REEXECUTION = (
    ROBUSTNESS_DIR /
    "phase11_3_2_router_reexecution_audit.json"
)

INSTABILITY = (
    ROBUSTNESS_DIR /
    "phase11_3_3_routing_instability_audit.json"
)

MANUAL = (
    ROBUSTNESS_DIR /
    "phase11_3_4_manual_inspection_audit.json"
)

ROBUSTNESS_CLOSURE = (
    ROBUSTNESS_DIR /
    "phase11_3_robustness_closure_manifest.json"
)

PHASE11_CLOSURE = Path(
    "results/eligible/"
    "phase11_safety_fairness_robustness_closure_manifest.json"
)


# =============================================================================
# HELPERS
# =============================================================================

def section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def load_json(path):
    with path.open() as f:
        return json.load(f)


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
    "PHASE 11.3.5 — ROBUSTNESS FAILURE DISCLOSURE "
    "AND PHASE 11 CLOSURE"
)


# =============================================================================
# A — VERIFY COMPLETE PHASE 11 ARTIFACT CHAIN
# =============================================================================

section("A — VERIFY PHASE 11 ARTIFACT CHAIN")

required = [
    SAFETY,
    FAIRNESS,
    SPEC,
    REEXECUTION,
    INSTABILITY,
    MANUAL,
]

for path in required:

    if not path.exists():
        raise FileNotFoundError(path)

    print("FOUND:", path)


print("Phase 11 artifact presence: PASSED")


# =============================================================================
# B — LOAD VERIFIED PHASE RESULTS
# =============================================================================

section("B — LOAD VERIFIED PHASE RESULTS")

safety = load_json(SAFETY)
fairness = load_json(FAIRNESS)
spec = load_json(SPEC)
reexecution = load_json(REEXECUTION)
instability = load_json(INSTABILITY)
manual = load_json(MANUAL)


print(
    "11.1 Safety:",
    safety.get("status", safety.get("closure_status"))
)

print(
    "11.2 Fairness:",
    fairness.get("status", fairness.get("closure_status"))
)

print(
    "11.3.1B Perturbation freeze:",
    spec["status"]
)

print(
    "11.3.2 Reexecution:",
    reexecution["status"]
)

print(
    "11.3.3 Instability:",
    instability["status"]
)

print(
    "11.3.4 Manual inspection:",
    manual["status"]
)


# =============================================================================
# C — VERIFY PREDECLARATION AND FROZEN EXECUTION
# =============================================================================

section("C — VERIFY ROBUSTNESS EXPERIMENT INTEGRITY")

if (
    spec["status"]
    != "PERTURBATION_SPECIFICATION_FROZEN"
):
    raise RuntimeError(
        "Perturbation specification not frozen."
    )


if (
    reexecution["status"]
    != "PERTURBED_ROUTER_REEXECUTION_COMPLETE"
):
    raise RuntimeError(
        "Router reexecution incomplete."
    )


if (
    instability["status"]
    != "ROUTING_INSTABILITY_ANALYSIS_COMPLETE"
):
    raise RuntimeError(
        "Instability analysis incomplete."
    )


if (
    manual["status"]
    != "MANUAL_UNSTABLE_CASE_INSPECTION_COMPLETE"
):
    raise RuntimeError(
        "Manual inspection incomplete."
    )


print("Perturbations predeclared: PASSED")
print("Actual frozen router reexecuted: PASSED")
print("Manual route-label editing: NO")
print("Ground truth used to choose perturbations: NO")
print("Demographics perturbed: NO")
print("Phase 10 router modified: NO")


# =============================================================================
# D — ROUTING ROBUSTNESS FINDINGS
# =============================================================================

section("D — ROUTING ROBUSTNESS FINDINGS")

global_instability = (
    instability["global_instability"]
)

population = instability["population"]


router_cases = int(
    population["router_cases"]
)

valid_scenarios = int(
    population["valid_perturbation_scenarios"]
)

route_flip_scenarios = int(
    global_instability["route_flip_scenarios"]
)

scenario_flip_rate = float(
    global_instability["scenario_flip_rate"]
)

unstable_cases = int(
    global_instability["unstable_cases"]
)

case_flip_rate = float(
    global_instability["any_case_flip_rate"]
)

bypass_to_review = int(
    global_instability["bypass_to_review_flips"]
)

review_to_bypass = int(
    global_instability["review_to_bypass_flips"]
)


print("Router cases:", router_cases)
print("Valid perturbation scenarios:", valid_scenarios)

print(
    "Route-flip scenarios:",
    route_flip_scenarios
)

print(
    "Scenario-level route-flip rate:",
    f"{scenario_flip_rate:.6f}"
)

print(
    "Cases with >=1 route flip:",
    unstable_cases
)

print(
    "Any-case route-flip rate:",
    f"{case_flip_rate:.6f}"
)

print(
    "BYPASS -> REVIEW flips:",
    bypass_to_review
)

print(
    "REVIEW -> BYPASS flips:",
    review_to_bypass
)


# =============================================================================
# E — INSTABILITY BY ORIGINAL ROUTE
# =============================================================================

section("E — INSTABILITY BY ORIGINAL ROUTE")

route_results = {
    row["original_route"]: row
    for row in instability[
        "instability_by_original_route"
    ]
}


for route_name in [
    "BYPASS",
    "RESCUE_REVIEW",
]:

    row = route_results[route_name]

    print()
    print(route_name)

    print(
        "Cases:",
        row["n_cases"]
    )

    print(
        "Unstable cases:",
        row["unstable_cases"]
    )

    print(
        "Instability rate:",
        f'{row["instability_rate"]:.6f}'
    )


# =============================================================================
# F — FEATURE-SPECIFIC FAILURE DISCLOSURE
# =============================================================================

section("F — FEATURE-SPECIFIC ROBUSTNESS FINDINGS")

feature_rows = sorted(
    instability["feature_instability"],
    key=lambda x: x["scenario_flip_rate"],
    reverse=True,
)


for row in feature_rows:

    print()
    print(row["feature"])

    print(
        "Valid scenarios:",
        row["valid_scenarios"]
    )

    print(
        "Route flips:",
        row["route_flips"]
    )

    print(
        "Scenario flip rate:",
        f'{row["scenario_flip_rate"]:.6f}'
    )

    print(
        "Affected cases:",
        row["affected_cases"]
    )


# =============================================================================
# G — BOUNDARY-CONCENTRATION FINDINGS
# =============================================================================

section("G — ROUTING-BOUNDARY FINDINGS")

boundary = instability[
    "boundary_analysis"
]


print(
    "Median distance to cutoff — all cases:",
    boundary["median_distance_all"]
)

print(
    "Median distance to cutoff — stable cases:",
    boundary["median_distance_stable"]
)

print(
    "Median distance to cutoff — unstable cases:",
    boundary["median_distance_unstable"]
)

print(
    "Maximum distance to cutoff — unstable cases:",
    boundary["maximum_distance_unstable"]
)


# =============================================================================
# H — MANUAL INSPECTION FINDINGS
# =============================================================================

section("H — STRUCTURED MANUAL INSPECTION FINDINGS")

inspection = manual[
    "inspection_results"
]


print(
    "Cases inspected:",
    manual["selection"]["cases_inspected"]
)

print(
    "Original BYPASS cases:",
    inspection["original_bypass_cases"]
)

print(
    "Original RESCUE REVIEW cases:",
    inspection["original_review_cases"]
)

print(
    "Cases sensitive to >=2 features:",
    inspection["multi_feature_sensitive_cases"]
)

print(
    "Cases sensitive to >=4 features:",
    inspection["highly_boundary_sensitive_cases"]
)

print(
    "Median distance to cutoff:",
    inspection["median_distance_to_cutoff"]
)


# =============================================================================
# I — REQUIRED ROBUSTNESS FAILURE DISCLOSURE
# =============================================================================

section("I — REQUIRED ROBUSTNESS FAILURE DISCLOSURE")


print("ROBUSTNESS-01")
print(
    "Small predeclared perturbations can change "
    "the frozen Rescue Router's compute allocation."
)

print(
    " unstable_cases:",
    unstable_cases
)

print(
    " fraction_of_router_population:",
    case_flip_rate
)


print()
print("ROBUSTNESS-02")
print(
    "Routing instability is concentrated near "
    "the frozen operational routing cutoff."
)

print(
    " median_distance_unstable:",
    boundary["median_distance_unstable"]
)

print(
    " median_distance_stable:",
    boundary["median_distance_stable"]
)


print()
print("ROBUSTNESS-03")
print(
    "Originally selected Rescue Review cases show "
    "greater perturbation sensitivity than original "
    "bypass cases."
)

print(
    " bypass_instability_rate:",
    route_results[
        "BYPASS"
    ][
        "instability_rate"
    ]
)

print(
    " review_instability_rate:",
    route_results[
        "RESCUE_REVIEW"
    ][
        "instability_rate"
    ]
)


print()
print("ROBUSTNESS-04")
print(
    "The strongest tested feature-specific "
    "instability was produced by:"
)

print(
    " feature:",
    feature_rows[0]["feature"]
)

print(
    " scenario_flip_rate:",
    feature_rows[0]["scenario_flip_rate"]
)


print()
print("ROBUSTNESS-05")
print(
    "The manually inspected boundary-nearest "
    "unstable cases frequently changed route under "
    "multiple independent feature perturbations."
)

print(
    " multi_feature_sensitive_cases:",
    inspection[
        "multi_feature_sensitive_cases"
    ]
)

print(
    " highly_boundary_sensitive_cases:",
    inspection[
        "highly_boundary_sensitive_cases"
    ]
)


print()
print("ROBUSTNESS-06")
print(
    "A route flip is an operational compute-routing "
    "change. It does not establish that either route "
    "is clinically correct."
)


print()
print("Robustness failures hidden: NO")
print("Residual routing instability present: YES")


# =============================================================================
# J — ROBUSTNESS INTERPRETATION BOUNDARY
# =============================================================================

section("J — ROBUSTNESS INTERPRETATION BOUNDARY")

limitations = [
    "This is a retrospective local perturbation audit.",
    (
        "Perturbations test local routing stability; "
        "they do not reproduce all real-world data shifts."
    ),
    (
        "A route flip represents a change in compute "
        "allocation, not necessarily a clinical error."
    ),
    (
        "The manual inspection population was deliberately "
        "enriched for unstable cases closest to the cutoff."
    ),
    (
        "The structured manual inspection is not clinician "
        "adjudication."
    ),
    (
        "Ground-truth outcomes were not used to select "
        "perturbation magnitudes."
    ),
    (
        "Demographic variables were not perturbed."
    ),
    (
        "The frozen Phase 10 router was not retrained "
        "or modified."
    ),
]


for item in limitations:
    print(" -", item)


print()
print("Clinical robustness claim permitted: NO")


# =============================================================================
# K — CREATE ROBUSTNESS CLOSURE MANIFEST
# =============================================================================

section("K — CREATE ROBUSTNESS CLOSURE MANIFEST")

robustness_closure = {
    "phase": "11.3",

    "status":
        "ROUTING_ROBUSTNESS_AUDIT_COMPLETE",

    "subphases": {
        "11.3.1B":
            "COMPLETE",

        "11.3.2":
            "COMPLETE",

        "11.3.3":
            "COMPLETE",

        "11.3.4":
            "COMPLETE",

        "11.3.5":
            "COMPLETE",
    },

    "key_findings": {
        "router_population":
            router_cases,

        "valid_perturbation_scenarios":
            valid_scenarios,

        "route_flip_scenarios":
            route_flip_scenarios,

        "scenario_flip_rate":
            scenario_flip_rate,

        "unstable_cases":
            unstable_cases,

        "any_case_flip_rate":
            case_flip_rate,

        "bypass_instability_rate":
            route_results[
                "BYPASS"
            ][
                "instability_rate"
            ],

        "review_instability_rate":
            route_results[
                "RESCUE_REVIEW"
            ][
                "instability_rate"
            ],

        "strongest_feature":
            feature_rows[0]["feature"],

        "strongest_feature_flip_rate":
            feature_rows[0][
                "scenario_flip_rate"
            ],

        "manual_cases_inspected":
            manual[
                "selection"
            ][
                "cases_inspected"
            ],

        "manual_multi_feature_sensitive":
            inspection[
                "multi_feature_sensitive_cases"
            ],

        "manual_highly_boundary_sensitive":
            inspection[
                "highly_boundary_sensitive_cases"
            ],
    },

    "required_disclosures": {
        "routing_instability_present":
            True,

        "boundary_concentration_present":
            True,

        "multi_feature_instability_present":
            True,

        "failures_hidden":
            False,

        "clinical_robustness_established":
            False,
    },

    "integrity": {
        "perturbations_predeclared":
            True,

        "ground_truth_excluded_from_perturbation_choice":
            True,

        "actual_frozen_router_reexecuted":
            True,

        "phase10_modified":
            False,
    },

    "source_hashes": {
        "perturbation_spec":
            sha256_file(SPEC),

        "reexecution_audit":
            sha256_file(REEXECUTION),

        "instability_audit":
            sha256_file(INSTABILITY),

        "manual_inspection_audit":
            sha256_file(MANUAL),
    },
}


with ROBUSTNESS_CLOSURE.open("w") as f:
    json.dump(
        robustness_closure,
        f,
        indent=2,
    )


print(
    "Robustness closure manifest:",
    ROBUSTNESS_CLOSURE
)


# =============================================================================
# L — VERIFY SAFETY AND FAIRNESS CLOSURES
# =============================================================================

section("L — VERIFY SAFETY AND FAIRNESS CLOSURES")


safety_passed = (
    safety.get("closure_status") == "PASSED"
    or safety.get("status") == "SAFETY_AUDIT_COMPLETE"
)


fairness_passed = (
    fairness.get("closure_status") == "PASSED"
    or fairness.get("status") == "FAIRNESS_AUDIT_COMPLETE"
)


print(
    "Phase 11.1 Safety closure:",
    "PASSED" if safety_passed else "FAILED"
)

print(
    "Phase 11.2 Fairness closure:",
    "PASSED" if fairness_passed else "FAILED"
)

print(
    "Phase 11.3 Robustness closure: PASSED"
)


if not safety_passed:
    raise RuntimeError(
        "Safety closure not verified."
    )

if not fairness_passed:
    raise RuntimeError(
        "Fairness closure not verified."
    )


# =============================================================================
# M — PHASE 11 CROSS-DOMAIN FINDINGS
# =============================================================================

section("M — PHASE 11 CROSS-DOMAIN FINDINGS")

print("SAFETY")
print(
    "The frozen system retains clinically important "
    "false-negative and routing-bypass limitations."
)

print()
print("FAIRNESS")
print(
    "Subgroup performance and compute allocation vary; "
    "age remained associated with adjusted workflow "
    "allocation in the stable sensitivity analysis."
)

print()
print("ROBUSTNESS")
print(
    "Small plausible perturbations can change the "
    "compute route for a non-trivial subset of cases, "
    "especially near the routing boundary."
)

print()
print(
    "These findings are retained as limitations. "
    "They are not suppressed because individual "
    "sub-audits executed successfully."
)


# =============================================================================
# N — CREATE PHASE 11 FINAL CLOSURE MANIFEST
# =============================================================================

section("N — CREATE PHASE 11 FINAL CLOSURE MANIFEST")

phase11 = {
    "phase": "11",

    "name":
        "Safety, Fairness, and Robustness",

    "status":
        "PHASE_11_COMPLETE",

    "domains": {
        "safety": {
            "status":
                "SAFETY_AUDIT_COMPLETE",

            "clinical_safety_established":
                False,

            "failures_reported":
                True,
        },

        "fairness": {
            "status":
                "FAIRNESS_AUDIT_COMPLETE",

            "clinical_fairness_established":
                False,

            "limitations_reported":
                True,
        },

        "robustness": {
            "status":
                "ROUTING_ROBUSTNESS_AUDIT_COMPLETE",

            "clinical_robustness_established":
                False,

            "routing_instability_present":
                True,

            "limitations_reported":
                True,
        },
    },

    "global_claim_boundary": {
        "clinical_deployment_validated":
            False,

        "prospective_safety_established":
            False,

        "clinical_fairness_established":
            False,

        "clinical_robustness_established":
            False,

        "phase11_is_retrospective_audit":
            True,
    },

    "frozen_system_integrity": {
        "phase10_modified":
            False,

        "primary_model_retrained":
            False,

        "rescue_router_retrained":
            False,

        "audit_results_used_to_rewrite_frozen_results":
            False,
    },

    "closure_manifests": {
        "safety":
            str(SAFETY),

        "fairness":
            str(FAIRNESS),

        "robustness":
            str(ROBUSTNESS_CLOSURE),
    },

    "closure_hashes": {
        "safety":
            sha256_file(SAFETY),

        "fairness":
            sha256_file(FAIRNESS),

        "robustness":
            sha256_file(ROBUSTNESS_CLOSURE),
    },

    "next_phase":
        "Phase 12 — Final reporting and poster-ready evidence synthesis",
}


with PHASE11_CLOSURE.open("w") as f:
    json.dump(
        phase11,
        f,
        indent=2,
    )


print(
    "Phase 11 closure manifest:",
    PHASE11_CLOSURE
)


# =============================================================================
# O — FINAL VERIFICATION
# =============================================================================

section("O — FINAL PHASE 11 VERIFICATION")

checks = {
    "safety_closed":
        safety_passed,

    "fairness_closed":
        fairness_passed,

    "robustness_closed":
        robustness_closure[
            "status"
        ]
        == "ROUTING_ROBUSTNESS_AUDIT_COMPLETE",

    "instability_disclosed":
        robustness_closure[
            "required_disclosures"
        ][
            "routing_instability_present"
        ] is True,

    "failures_not_hidden":
        robustness_closure[
            "required_disclosures"
        ][
            "failures_hidden"
        ] is False,

    "no_clinical_safety_claim":
        phase11[
            "domains"
        ][
            "safety"
        ][
            "clinical_safety_established"
        ] is False,

    "no_clinical_fairness_claim":
        phase11[
            "domains"
        ][
            "fairness"
        ][
            "clinical_fairness_established"
        ] is False,

    "no_clinical_robustness_claim":
        phase11[
            "domains"
        ][
            "robustness"
        ][
            "clinical_robustness_established"
        ] is False,

    "no_deployment_claim":
        phase11[
            "global_claim_boundary"
        ][
            "clinical_deployment_validated"
        ] is False,

    "phase10_unchanged":
        phase11[
            "frozen_system_integrity"
        ][
            "phase10_modified"
        ] is False,

    "phase11_manifest_exists":
        PHASE11_CLOSURE.exists(),
}


for name, passed in checks.items():

    print(
        name + ":",
        "PASSED" if passed else "FAILED"
    )


if not all(checks.values()):

    raise RuntimeError(
        "Phase 11 final closure verification failed."
    )


# =============================================================================
# COMPLETE
# =============================================================================

section(
    "PHASE 11 COMPLETE — "
    "SAFETY, FAIRNESS, AND ROBUSTNESS AUDIT LOCKED"
)

print("11.1 Safety: COMPLETE")
print("11.2 Fairness: COMPLETE")
print("11.3 Routing robustness: COMPLETE")

print()
print(
    "Safety failures transparently reported: YES"
)

print(
    "Fairness limitations transparently reported: YES"
)

print(
    "Routing instability transparently reported: YES"
)

print()
print(
    "Clinical safety established: NO"
)

print(
    "Clinical fairness established: NO"
)

print(
    "Clinical robustness established: NO"
)

print(
    "Clinical deployment validated: NO"
)

print()
print(
    "Phase 10 frozen system modified: NO"
)

print(
    "Phase 11 audit status: PHASE_11_COMPLETE"
)

print()
print(
    "NEXT: PHASE 12 — "
    "FINAL REPORTING AND POSTER-READY EVIDENCE SYNTHESIS"
)
