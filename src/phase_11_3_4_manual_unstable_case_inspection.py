from pathlib import Path
import json
import hashlib
import pandas as pd
import numpy as np


# =============================================================================
# PATHS
# =============================================================================

ROBUSTNESS_DIR = Path(
    "results/eligible/robustness"
)

CANDIDATES = (
    ROBUSTNESS_DIR /
    "phase11_3_3_manual_inspection_candidates.csv"
)

CASE_INSTABILITY = (
    ROBUSTNESS_DIR /
    "phase11_3_3_case_instability.csv"
)

AUDIT_1133 = (
    ROBUSTNESS_DIR /
    "phase11_3_3_routing_instability_audit.json"
)

SCENARIOS = (
    ROBUSTNESS_DIR /
    "phase11_3_2_perturbed_router_scenarios.csv"
)

CASE_OUTPUT = (
    ROBUSTNESS_DIR /
    "phase11_3_4_manual_case_inspection.csv"
)

FLIP_OUTPUT = (
    ROBUSTNESS_DIR /
    "phase11_3_4_manual_flip_scenarios.csv"
)

PATTERN_OUTPUT = (
    ROBUSTNESS_DIR /
    "phase11_3_4_manual_failure_patterns.csv"
)

AUDIT_OUTPUT = (
    ROBUSTNESS_DIR /
    "phase11_3_4_manual_inspection_audit.json"
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
    "PHASE 11.3.4 — MANUAL INSPECTION OF UNSTABLE CASES"
)


# =============================================================================
# A — VERIFY INPUTS
# =============================================================================

section("A — VERIFY REQUIRED INPUTS")

required = [
    CANDIDATES,
    CASE_INSTABILITY,
    AUDIT_1133,
    SCENARIOS,
]

for path in required:

    if not path.exists():
        raise FileNotFoundError(path)

    print("FOUND:", path)


with AUDIT_1133.open() as f:
    audit_1133 = json.load(f)


if (
    audit_1133["status"]
    != "ROUTING_INSTABILITY_ANALYSIS_COMPLETE"
):
    raise RuntimeError(
        "Phase 11.3.3 is not complete."
    )


expected_rule = (
    "100_UNSTABLE_CASES_CLOSEST_TO_ROUTING_BOUNDARY"
)

actual_rule = (
    audit_1133[
        "manual_inspection"
    ][
        "selection_rule"
    ]
)


if actual_rule != expected_rule:
    raise RuntimeError(
        "Manual inspection rule differs from frozen rule."
    )


print("11.3.3 status: PASSED")
print("Frozen manual-inspection rule: PASSED")


# =============================================================================
# B — LOAD INSPECTION POPULATION
# =============================================================================

section("B — LOAD FROZEN MANUAL INSPECTION POPULATION")

candidate_rows = pd.read_csv(
    CANDIDATES
)

case_table = pd.read_csv(
    CASE_INSTABILITY
)

all_scenarios = pd.read_csv(
    SCENARIOS
)


case_ids = sorted(
    candidate_rows[
        "encounter_id"
    ].unique()
)


print(
    "Candidate scenario rows:",
    len(candidate_rows)
)

print(
    "Unique candidate cases:",
    len(case_ids)
)


if len(case_ids) != 100:
    raise RuntimeError(
        "Expected exactly 100 frozen manual-inspection cases."
    )


selected_cases = case_table[
    case_table[
        "encounter_id"
    ].isin(case_ids)
].copy()


if len(selected_cases) != 100:
    raise RuntimeError(
        "Case-level inspection population mismatch."
    )


if not (
    selected_cases[
        "any_route_flip"
    ] == 1
).all():
    raise RuntimeError(
        "Manual inspection set contains a stable case."
    )


print("All selected cases unstable: PASSED")


# =============================================================================
# C — VERIFY THEY ARE THE CLOSEST 100 UNSTABLE CASES
# =============================================================================

section("C — VERIFY PREDECLARED SELECTION RULE")

all_unstable = (
    case_table[
        case_table[
            "any_route_flip"
        ] == 1
    ]
    .sort_values(
        [
            "original_distance_to_cutoff",
            "encounter_id",
        ]
    )
)


expected_ids = set(
    all_unstable
    .head(100)[
        "encounter_id"
    ]
    .tolist()
)

observed_ids = set(
    case_ids
)


selection_match = (
    expected_ids
    == observed_ids
)


print(
    "Total unstable cases:",
    len(all_unstable)
)

print(
    "Expected manual cases:",
    100
)

print(
    "Frozen selection exactly reproduced:",
    selection_match
)


if not selection_match:
    raise RuntimeError(
        "Manual inspection population does not match "
        "the predeclared rule."
    )


# =============================================================================
# D — EXTRACT FLIPPING SCENARIOS
# =============================================================================

section("D — EXTRACT ROUTE-FLIPPING SCENARIOS")

manual_scenarios = all_scenarios[
    all_scenarios[
        "encounter_id"
    ].isin(case_ids)
].copy()


flips = manual_scenarios[
    (
        manual_scenarios[
            "valid_perturbation"
        ] == 1
    )
    &
    (
        manual_scenarios[
            "route_flip"
        ] == 1
    )
].copy()


print(
    "All retained scenario rows:",
    len(manual_scenarios)
)

print(
    "Valid route-flipping scenarios:",
    len(flips)
)

print(
    "Cases represented among flips:",
    flips[
        "encounter_id"
    ].nunique()
)


if (
    flips[
        "encounter_id"
    ].nunique()
    != 100
):
    raise RuntimeError(
        "Every manually inspected case should "
        "have at least one route flip."
    )


# =============================================================================
# E — BUILD CASE-BY-CASE INSPECTION
# =============================================================================

section("E — CASE-BY-CASE STRUCTURED INSPECTION")

inspection_rows = []


for encounter_id in case_ids:

    case_scenarios = manual_scenarios[
        manual_scenarios[
            "encounter_id"
        ] == encounter_id
    ]

    case_flips = case_scenarios[
        (
            case_scenarios[
                "valid_perturbation"
            ] == 1
        )
        &
        (
            case_scenarios[
                "route_flip"
            ] == 1
        )
    ]


    original_route = int(
        case_scenarios[
            "original_selected_for_review"
        ].iloc[0]
    )

    original_probability = float(
        case_scenarios[
            "original_router_probability"
        ].iloc[0]
    )

    cutoff = float(
        case_scenarios[
            "operational_cutoff"
        ].iloc[0]
    )

    distance = float(
        case_scenarios[
            "original_distance_to_cutoff"
        ].iloc[0]
    )


    features = sorted(
        case_flips[
            "feature"
        ].unique().tolist()
    )

    feature_directions = sorted(
        (
            case_flips["feature"]
            + ":"
            + case_flips["direction"]
        ).unique().tolist()
    )


    b2r = int(
        (
            (
                case_flips[
                    "original_selected_for_review"
                ] == 0
            )
            &
            (
                case_flips[
                    "perturbed_selected_for_review"
                ] == 1
            )
        ).sum()
    )

    r2b = int(
        (
            (
                case_flips[
                    "original_selected_for_review"
                ] == 1
            )
            &
            (
                case_flips[
                    "perturbed_selected_for_review"
                ] == 0
            )
        ).sum()
    )


    if original_route == 0:
        route_label = "BYPASS"
        flip_type = "BYPASS_TO_REVIEW"
    else:
        route_label = "RESCUE_REVIEW"
        flip_type = "REVIEW_TO_BYPASS"


    if len(features) >= 4:
        pattern = "HIGHLY_BOUNDARY_SENSITIVE"

    elif len(features) >= 2:
        pattern = "MULTI_FEATURE_SENSITIVE"

    else:
        pattern = "SINGLE_FEATURE_SENSITIVE"


    inspection_rows.append(
        {
            "encounter_id":
                encounter_id,

            "patient_nbr":
                case_scenarios[
                    "patient_nbr"
                ].iloc[0],

            "original_route":
                route_label,

            "original_router_probability":
                original_probability,

            "operational_cutoff":
                cutoff,

            "distance_to_cutoff":
                distance,

            "flip_type":
                flip_type,

            "n_valid_scenarios":
                int(
                    (
                        case_scenarios[
                            "valid_perturbation"
                        ] == 1
                    ).sum()
                ),

            "n_flip_scenarios":
                int(
                    len(case_flips)
                ),

            "n_flipping_features":
                int(
                    len(features)
                ),

            "flipping_features":
                "|".join(features),

            "flipping_feature_directions":
                "|".join(
                    feature_directions
                ),

            "maximum_flip_probability_change":
                float(
                    case_flips[
                        "absolute_probability_change"
                    ].max()
                ),

            "minimum_flip_probability_change":
                float(
                    case_flips[
                        "absolute_probability_change"
                    ].min()
                ),

            "bypass_to_review_flip_scenarios":
                b2r,

            "review_to_bypass_flip_scenarios":
                r2b,

            "inspection_pattern":
                pattern,

            "inspection_finding":
                (
                    "Small predeclared perturbation can "
                    "change the frozen compute route."
                ),
        }
    )


inspection = pd.DataFrame(
    inspection_rows
)


print(
    inspection[
        [
            "encounter_id",
            "original_route",
            "distance_to_cutoff",
            "n_flip_scenarios",
            "n_flipping_features",
            "inspection_pattern",
        ]
    ]
    .head(20)
    .to_string(
        index=False
    )
)


# =============================================================================
# F — MANUAL INSPECTION SUMMARY
# =============================================================================

section("F — MANUAL INSPECTION SUMMARY")

print(
    "Cases inspected:",
    len(inspection)
)

print()
print("Original route:")

print(
    inspection[
        "original_route"
    ]
    .value_counts()
    .to_string()
)


print()
print("Inspection patterns:")

print(
    inspection[
        "inspection_pattern"
    ]
    .value_counts()
    .to_string()
)


print()
print("Number of flipping features:")

print(
    inspection[
        "n_flipping_features"
    ]
    .value_counts()
    .sort_index()
    .to_string()
)


# =============================================================================
# G — RECURRING DESTABILIZING FEATURES
# =============================================================================

section("G — RECURRING DESTABILIZING FEATURES")

feature_case_counts = (
    flips[
        [
            "feature",
            "encounter_id",
        ]
    ]
    .drop_duplicates()
    .groupby(
        "feature"
    )
    .size()
    .sort_values(
        ascending=False
    )
)


print(
    feature_case_counts.to_string()
)


print()
print("Feature × direction flip scenarios:")

feature_direction_counts = (
    flips
    .groupby(
        [
            "feature",
            "direction",
        ]
    )
    .size()
    .sort_values(
        ascending=False
    )
)


print(
    feature_direction_counts.to_string()
)


# =============================================================================
# H — FAILURE-PATTERN TABLE
# =============================================================================

section("H — BUILD FAILURE-PATTERN TABLE")

pattern_rows = []


for pattern, group in inspection.groupby(
    "inspection_pattern"
):

    pattern_rows.append(
        {
            "pattern":
                pattern,

            "cases":
                int(len(group)),

            "fraction_of_manual_cases":
                float(
                    len(group)
                    / len(inspection)
                ),

            "median_distance_to_cutoff":
                float(
                    group[
                        "distance_to_cutoff"
                    ].median()
                ),

            "median_flipping_features":
                float(
                    group[
                        "n_flipping_features"
                    ].median()
                ),

            "median_flip_scenarios":
                float(
                    group[
                        "n_flip_scenarios"
                    ].median()
                ),
        }
    )


patterns = pd.DataFrame(
    pattern_rows
).sort_values(
    "cases",
    ascending=False,
)


print(
    patterns.to_string(
        index=False
    )
)


# =============================================================================
# I — REQUIRED MANUAL FINDINGS
# =============================================================================

section("I — REQUIRED MANUAL INSPECTION FINDINGS")

multi_feature = int(
    (
        inspection[
            "n_flipping_features"
        ] >= 2
    ).sum()
)

highly_sensitive = int(
    (
        inspection[
            "n_flipping_features"
        ] >= 4
    ).sum()
)

bypass_cases = int(
    (
        inspection[
            "original_route"
        ] == "BYPASS"
    ).sum()
)

review_cases = int(
    (
        inspection[
            "original_route"
        ] == "RESCUE_REVIEW"
    ).sum()
)


print(
    "ROBUSTNESS-01"
)

print(
    "The 100 predeclared closest-to-boundary "
    "unstable cases were manually/structurally inspected."
)


print()
print(
    "ROBUSTNESS-02"
)

print(
    "Cases sensitive to >=2 independent features:",
    multi_feature
)


print()
print(
    "ROBUSTNESS-03"
)

print(
    "Cases sensitive to >=4 independent features:",
    highly_sensitive
)


print()
print(
    "ROBUSTNESS-04"
)

print(
    "Originally BYPASS cases in manual set:",
    bypass_cases
)

print(
    "Originally RESCUE REVIEW cases in manual set:",
    review_cases
)


print()
print(
    "ROBUSTNESS-05"
)

print(
    "Instability in this inspection set is expected "
    "to be boundary-concentrated because the selection "
    "rule intentionally chose unstable cases closest "
    "to the frozen routing cutoff."
)


print()
print(
    "ROBUSTNESS-06"
)

print(
    "Manual inspection does not establish that the "
    "perturbed value is clinically correct or that "
    "the original route is clinically incorrect."
)


# =============================================================================
# J — SAVE ARTIFACTS
# =============================================================================

section("J — SAVE MANUAL INSPECTION ARTIFACTS")

inspection.to_csv(
    CASE_OUTPUT,
    index=False,
)

flips.to_csv(
    FLIP_OUTPUT,
    index=False,
)

patterns.to_csv(
    PATTERN_OUTPUT,
    index=False,
)


print(
    "Case inspection:",
    CASE_OUTPUT
)

print(
    "Flip scenarios:",
    FLIP_OUTPUT
)

print(
    "Failure patterns:",
    PATTERN_OUTPUT
)


# =============================================================================
# K — CREATE MANUAL INSPECTION AUDIT
# =============================================================================

section("K — CREATE MANUAL INSPECTION AUDIT")

audit = {
    "phase": "11.3.4",

    "status":
        "MANUAL_UNSTABLE_CASE_INSPECTION_COMPLETE",

    "selection": {
        "rule":
            expected_rule,

        "available_unstable_cases":
            int(
                audit_1133[
                    "manual_inspection"
                ][
                    "unstable_cases_available"
                ]
            ),

        "cases_inspected":
            int(
                len(inspection)
            ),

        "selection_reproduced":
            selection_match,
    },

    "inspection_results": {
        "original_bypass_cases":
            bypass_cases,

        "original_review_cases":
            review_cases,

        "multi_feature_sensitive_cases":
            multi_feature,

        "highly_boundary_sensitive_cases":
            highly_sensitive,

        "median_distance_to_cutoff":
            float(
                inspection[
                    "distance_to_cutoff"
                ].median()
            ),

        "minimum_distance_to_cutoff":
            float(
                inspection[
                    "distance_to_cutoff"
                ].min()
            ),

        "maximum_distance_to_cutoff":
            float(
                inspection[
                    "distance_to_cutoff"
                ].max()
            ),
    },

    "feature_case_counts": {
        str(k): int(v)
        for k, v in
        feature_case_counts.items()
    },

    "interpretation_boundary": {
        "inspection_is_structured_manual_review":
            True,

        "selection_is_boundary_enriched":
            True,

        "ground_truth_used_for_selection":
            False,

        "demographics_used_for_selection":
            False,

        "clinical_correctness_of_original_route_established":
            False,

        "clinical_correctness_of_perturbed_route_established":
            False,

        "clinical_robustness_established":
            False,
    },

    "artifacts": {
        "case_inspection_csv":
            str(CASE_OUTPUT),

        "flip_scenarios_csv":
            str(FLIP_OUTPUT),

        "failure_patterns_csv":
            str(PATTERN_OUTPUT),

        "candidate_source_sha256":
            sha256_file(
                CANDIDATES
            ),

        "case_instability_source_sha256":
            sha256_file(
                CASE_INSTABILITY
            ),
    },

    "integrity": {
        "phase10_modified":
            False,

        "phase11_1_modified":
            False,

        "phase11_2_modified":
            False,

        "phase11_3_3_modified":
            False,
    },

    "next_phase":
        (
            "11.3.5 Robustness failure disclosure "
            "and Phase 11 closure"
        ),
}


with AUDIT_OUTPUT.open("w") as f:

    json.dump(
        audit,
        f,
        indent=2,
    )


print(
    "Audit artifact:",
    AUDIT_OUTPUT
)


# =============================================================================
# L — FINAL VERIFICATION
# =============================================================================

section("L — FINAL VERIFICATION")

checks = {
    "selection_rule":
        selection_match,

    "exactly_100_cases":
        len(inspection) == 100,

    "all_cases_unstable":
        (
            inspection[
                "n_flip_scenarios"
            ] > 0
        ).all(),

    "all_cases_have_flipping_feature":
        (
            inspection[
                "n_flipping_features"
            ] >= 1
        ).all(),

    "all_flip_rows_valid":
        (
            flips[
                "valid_perturbation"
            ] == 1
        ).all(),

    "all_flip_rows_are_flips":
        (
            flips[
                "route_flip"
            ] == 1
        ).all(),

    "no_ground_truth_selection":
        audit[
            "interpretation_boundary"
        ][
            "ground_truth_used_for_selection"
        ] is False,

    "no_demographic_selection":
        audit[
            "interpretation_boundary"
        ][
            "demographics_used_for_selection"
        ] is False,

    "no_clinical_robustness_claim":
        audit[
            "interpretation_boundary"
        ][
            "clinical_robustness_established"
        ] is False,

    "phase10_unchanged":
        audit[
            "integrity"
        ][
            "phase10_modified"
        ] is False,
}


for name, passed in checks.items():

    print(
        name + ":",
        "PASSED" if passed else "FAILED"
    )


if not all(checks.values()):

    raise RuntimeError(
        "Phase 11.3.4 verification failed."
    )


# =============================================================================
# COMPLETE
# =============================================================================

section(
    "PHASE 11.3.4 COMPLETE — "
    "MANUAL UNSTABLE-CASE INSPECTION PASSED"
)

print(
    "Cases inspected:",
    len(inspection)
)

print(
    "Cases sensitive to >=2 features:",
    multi_feature
)

print(
    "Cases sensitive to >=4 features:",
    highly_sensitive
)

print(
    "Originally BYPASS:",
    bypass_cases
)

print(
    "Originally RESCUE REVIEW:",
    review_cases
)

print(
    "Manual inspection completed: YES"
)

print(
    "Clinical robustness established: NO"
)

print(
    "Phase 10 frozen system modified: NO"
)

print()
print(
    "NEXT: PHASE 11.3.5 — "
    "ROBUSTNESS FAILURE DISCLOSURE AND PHASE 11 CLOSURE"
)
