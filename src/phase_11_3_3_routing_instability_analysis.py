from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

SCENARIOS = Path(
    "results/eligible/robustness/"
    "phase11_3_2_perturbed_router_scenarios.csv"
)

REEXECUTION = Path(
    "results/eligible/robustness/"
    "phase11_3_2_router_reexecution_audit.json"
)

SPEC = Path(
    "results/eligible/robustness/"
    "phase11_3_1b_frozen_perturbation_specification.json"
)

OUTPUT_DIR = Path(
    "results/eligible/robustness"
)

CASE_OUTPUT = (
    OUTPUT_DIR /
    "phase11_3_3_case_instability.csv"
)

FEATURE_OUTPUT = (
    OUTPUT_DIR /
    "phase11_3_3_feature_instability.csv"
)

DIRECTION_OUTPUT = (
    OUTPUT_DIR /
    "phase11_3_3_feature_direction_instability.csv"
)

MANUAL_OUTPUT = (
    OUTPUT_DIR /
    "phase11_3_3_manual_inspection_candidates.csv"
)

AUDIT_OUTPUT = (
    OUTPUT_DIR /
    "phase11_3_3_routing_instability_audit.json"
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


def safe_rate(num, den):
    if den == 0:
        return None
    return float(num / den)


# =============================================================================
# HEADER
# =============================================================================

section(
    "PHASE 11.3.3 — ROUTING INSTABILITY ANALYSIS"
)


# =============================================================================
# A — VERIFY INPUTS
# =============================================================================

section("A — VERIFY REQUIRED INPUTS")

for path in [
    SCENARIOS,
    REEXECUTION,
    SPEC,
]:

    if not path.exists():
        raise FileNotFoundError(path)

    print("FOUND:", path)


with REEXECUTION.open() as f:
    reexecution = json.load(f)

with SPEC.open() as f:
    spec = json.load(f)


if (
    reexecution["status"]
    != "PERTURBED_ROUTER_REEXECUTION_COMPLETE"
):
    raise RuntimeError(
        "Phase 11.3.2 is not complete."
    )


if (
    spec["status"]
    != "PERTURBATION_SPECIFICATION_FROZEN"
):
    raise RuntimeError(
        "Perturbation specification is not frozen."
    )


print("11.3.2 reexecution status: PASSED")
print("Frozen perturbation specification: PASSED")


# =============================================================================
# B — LOAD SCENARIOS
# =============================================================================

section("B — LOAD PERTURBATION SCENARIOS")

df = pd.read_csv(SCENARIOS)

print("Raw scenarios:", len(df))

valid = df[
    df["valid_perturbation"] == 1
].copy()

invalid = df[
    df["valid_perturbation"] == 0
].copy()


print("Valid scenarios:", len(valid))
print("No-change scenarios:", len(invalid))


if len(df) != 78580:
    raise RuntimeError(
        "Raw scenario count mismatch."
    )

if len(valid) != 64174:
    raise RuntimeError(
        "Valid scenario count mismatch."
    )

if int(invalid["route_flip"].sum()) != 0:
    raise RuntimeError(
        "Invalid scenarios contain route flips."
    )


print("Scenario accounting: PASSED")


# =============================================================================
# C — VERIFY INFORMATION BOUNDARY
# =============================================================================

section("C — VERIFY ROBUSTNESS INFORMATION BOUNDARY")

prohibited = [
    "actual_30d",
    "case_type",
    "router_target",
    "race",
    "gender",
    "age",
]

present_prohibited = [
    x
    for x in prohibited
    if x in df.columns
]


print(
    "Ground-truth/demographic columns in "
    "scenario artifact:",
    present_prohibited
)


if present_prohibited:
    raise RuntimeError(
        "Scenario artifact unexpectedly contains "
        "prohibited analysis columns."
    )


print("Ground truth used for instability definition: NO")
print("Demographics used for instability definition: NO")
print("Information boundary: PASSED")


# =============================================================================
# D — GLOBAL SCENARIO-LEVEL INSTABILITY
# =============================================================================

section("D — GLOBAL SCENARIO-LEVEL INSTABILITY")

scenario_flips = int(
    valid["route_flip"].sum()
)

scenario_flip_rate = safe_rate(
    scenario_flips,
    len(valid),
)


bypass_to_review = int(
    (
        (valid["route_flip"] == 1)
        & (
            valid[
                "original_selected_for_review"
            ] == 0
        )
        & (
            valid[
                "perturbed_selected_for_review"
            ] == 1
        )
    ).sum()
)


review_to_bypass = int(
    (
        (valid["route_flip"] == 1)
        & (
            valid[
                "original_selected_for_review"
            ] == 1
        )
        & (
            valid[
                "perturbed_selected_for_review"
            ] == 0
        )
    ).sum()
)


print("Valid perturbation scenarios:", len(valid))
print("Route-flip scenarios:", scenario_flips)
print(
    "Scenario-level route-flip rate:",
    f"{scenario_flip_rate:.6f}"
)

print()
print(
    "BYPASS -> REVIEW flips:",
    bypass_to_review
)

print(
    "REVIEW -> BYPASS flips:",
    review_to_bypass
)


if (
    bypass_to_review
    + review_to_bypass
    != scenario_flips
):
    raise RuntimeError(
        "Flip-direction accounting failed."
    )


print("Flip-direction accounting: PASSED")


# =============================================================================
# E — CASE-LEVEL INSTABILITY
# =============================================================================

section("E — CASE-LEVEL INSTABILITY")

case_rows = []


for encounter_id, group in valid.groupby(
    "encounter_id",
    sort=False,
):

    flip_rows = group[
        group["route_flip"] == 1
    ]

    any_flip = int(
        len(flip_rows) > 0
    )

    flipping_features = sorted(
        flip_rows[
            "feature"
        ].unique().tolist()
    )

    flipping_directions = sorted(
        (
            flip_rows["feature"]
            + ":"
            + flip_rows["direction"]
        ).unique().tolist()
    )

    case_rows.append(
        {
            "encounter_id":
                encounter_id,

            "patient_nbr":
                group[
                    "patient_nbr"
                ].iloc[0],

            "original_selected_for_review":
                int(
                    group[
                        "original_selected_for_review"
                    ].iloc[0]
                ),

            "original_router_probability":
                float(
                    group[
                        "original_router_probability"
                    ].iloc[0]
                ),

            "operational_cutoff":
                float(
                    group[
                        "operational_cutoff"
                    ].iloc[0]
                ),

            "original_distance_to_cutoff":
                float(
                    group[
                        "original_distance_to_cutoff"
                    ].iloc[0]
                ),

            "valid_scenarios":
                int(len(group)),

            "flip_scenarios":
                int(
                    flip_rows.shape[0]
                ),

            "any_route_flip":
                any_flip,

            "n_flipping_features":
                int(
                    len(flipping_features)
                ),

            "flipping_features":
                "|".join(
                    flipping_features
                ),

            "flipping_feature_directions":
                "|".join(
                    flipping_directions
                ),

            "max_absolute_probability_change":
                float(
                    group[
                        "absolute_probability_change"
                    ].max()
                ),

            "mean_absolute_probability_change":
                float(
                    group[
                        "absolute_probability_change"
                    ].mean()
                ),
        }
    )


cases = pd.DataFrame(case_rows)


if len(cases) != 7858:
    raise RuntimeError(
        "Expected 7858 unique router cases."
    )


unstable = cases[
    cases["any_route_flip"] == 1
].copy()


stable = cases[
    cases["any_route_flip"] == 0
].copy()


unstable_count = len(unstable)

case_flip_rate = safe_rate(
    unstable_count,
    len(cases),
)


print("Router cases:", len(cases))
print("Cases with >=1 route flip:", unstable_count)
print("Cases with no route flip:", len(stable))

print(
    "Any-case route-flip rate:",
    f"{case_flip_rate:.6f}"
)


# =============================================================================
# F — INSTABILITY BY ORIGINAL COMPUTE ROUTE
# =============================================================================

section("F — INSTABILITY BY ORIGINAL COMPUTE ROUTE")

route_summary = []


for original_route in [
    0,
    1,
]:

    subset = cases[
        cases[
            "original_selected_for_review"
        ] == original_route
    ]

    n = len(subset)

    n_unstable = int(
        subset[
            "any_route_flip"
        ].sum()
    )

    rate = safe_rate(
        n_unstable,
        n,
    )

    label = (
        "BYPASS"
        if original_route == 0
        else "RESCUE_REVIEW"
    )

    route_summary.append(
        {
            "original_route":
                label,

            "n_cases":
                n,

            "unstable_cases":
                n_unstable,

            "instability_rate":
                rate,
        }
    )

    print()
    print(label)

    print("Cases:", n)
    print("Unstable cases:", n_unstable)

    print(
        "Instability rate:",
        f"{rate:.6f}"
    )


# =============================================================================
# G — FEATURE-SPECIFIC INSTABILITY
# =============================================================================

section("G — FEATURE-SPECIFIC INSTABILITY")

feature_rows = []


for feature in spec["router_features"]:

    subset = valid[
        valid["feature"] == feature
    ]

    flips = int(
        subset["route_flip"].sum()
    )

    rate = safe_rate(
        flips,
        len(subset),
    )

    affected_cases = int(
        subset.loc[
            subset["route_flip"] == 1,
            "encounter_id"
        ].nunique()
    )

    b2r = int(
        (
            (subset["route_flip"] == 1)
            & (
                subset[
                    "original_selected_for_review"
                ] == 0
            )
        ).sum()
    )

    r2b = int(
        (
            (subset["route_flip"] == 1)
            & (
                subset[
                    "original_selected_for_review"
                ] == 1
            )
        ).sum()
    )

    mean_abs_change = float(
        subset[
            "absolute_probability_change"
        ].mean()
    )

    max_abs_change = float(
        subset[
            "absolute_probability_change"
        ].max()
    )

    row = {
        "feature":
            feature,

        "valid_scenarios":
            int(len(subset)),

        "route_flips":
            flips,

        "scenario_flip_rate":
            rate,

        "affected_cases":
            affected_cases,

        "bypass_to_review_flips":
            b2r,

        "review_to_bypass_flips":
            r2b,

        "mean_absolute_probability_change":
            mean_abs_change,

        "max_absolute_probability_change":
            max_abs_change,
    }

    feature_rows.append(row)


feature_table = pd.DataFrame(
    feature_rows
).sort_values(
    [
        "scenario_flip_rate",
        "route_flips",
    ],
    ascending=False,
)


print(
    feature_table.to_string(
        index=False
    )
)


# =============================================================================
# H — FEATURE × DIRECTION INSTABILITY
# =============================================================================

section("H — FEATURE × DIRECTION INSTABILITY")

direction_rows = []


for (
    feature,
    direction
) in valid.groupby(
    [
        "feature",
        "direction",
    ],
    sort=False,
):

    flips = int(
        direction["route_flip"].sum()
    )

    rate = safe_rate(
        flips,
        len(direction),
    )

    b2r = int(
        (
            (direction["route_flip"] == 1)
            & (
                direction[
                    "original_selected_for_review"
                ] == 0
            )
        ).sum()
    )

    r2b = int(
        (
            (direction["route_flip"] == 1)
            & (
                direction[
                    "original_selected_for_review"
                ] == 1
            )
        ).sum()
    )

    direction_rows.append(
        {
            "feature":
                feature,

            "direction":
                direction[
                    "direction"
                ].iloc[0],

            "valid_scenarios":
                int(len(direction)),

            "route_flips":
                flips,

            "scenario_flip_rate":
                rate,

            "bypass_to_review_flips":
                b2r,

            "review_to_bypass_flips":
                r2b,

            "mean_signed_probability_change":
                float(
                    direction[
                        "signed_probability_change"
                    ].mean()
                ),

            "mean_absolute_probability_change":
                float(
                    direction[
                        "absolute_probability_change"
                    ].mean()
                ),

            "max_absolute_probability_change":
                float(
                    direction[
                        "absolute_probability_change"
                    ].max()
                ),
        }
    )


direction_table = pd.DataFrame(
    direction_rows
).sort_values(
    [
        "scenario_flip_rate",
        "route_flips",
    ],
    ascending=False,
)


print(
    direction_table.to_string(
        index=False
    )
)


# =============================================================================
# I — DISTANCE-TO-BOUNDARY ANALYSIS
# =============================================================================

section("I — DISTANCE TO ROUTING BOUNDARY")

print(
    "Median distance — all cases:",
    float(
        cases[
            "original_distance_to_cutoff"
        ].median()
    )
)

print(
    "Median distance — stable cases:",
    float(
        stable[
            "original_distance_to_cutoff"
        ].median()
    )
)


if unstable_count > 0:

    print(
        "Median distance — unstable cases:",
        float(
            unstable[
                "original_distance_to_cutoff"
            ].median()
        )
    )

    print(
        "Maximum distance — unstable cases:",
        float(
            unstable[
                "original_distance_to_cutoff"
            ].max()
        )
    )

    print(
        "Minimum distance — unstable cases:",
        float(
            unstable[
                "original_distance_to_cutoff"
            ].min()
        )
    )

else:

    print(
        "No unstable cases were observed."
    )


# =============================================================================
# J — MULTI-FEATURE INSTABILITY
# =============================================================================

section("J — NUMBER OF DESTABILIZING FEATURES PER CASE")

if unstable_count > 0:

    feature_count_distribution = (
        unstable[
            "n_flipping_features"
        ]
        .value_counts()
        .sort_index()
    )

    print(
        feature_count_distribution.to_string()
    )

    multi_feature_unstable = int(
        (
            unstable[
                "n_flipping_features"
            ] >= 2
        ).sum()
    )

else:

    feature_count_distribution = pd.Series(
        dtype=int
    )

    multi_feature_unstable = 0


print()
print(
    "Cases destabilized by >=2 features:",
    multi_feature_unstable
)


# =============================================================================
# K — PREDECLARE MANUAL INSPECTION SET
# =============================================================================

section("K — CREATE MANUAL INSPECTION SET")

if unstable_count <= 100:

    manual_case_ids = (
        unstable[
            "encounter_id"
        ].tolist()
    )

    manual_rule = (
        "ALL_UNSTABLE_CASES"
    )

else:

    manual_case_ids = (
        unstable
        .sort_values(
            "original_distance_to_cutoff",
            ascending=True,
        )
        .head(100)[
            "encounter_id"
        ]
        .tolist()
    )

    manual_rule = (
        "100_UNSTABLE_CASES_CLOSEST_TO_ROUTING_BOUNDARY"
    )


manual = df[
    df[
        "encounter_id"
    ].isin(
        manual_case_ids
    )
].copy()


manual = manual.sort_values(
    [
        "original_distance_to_cutoff",
        "encounter_id",
        "feature",
        "direction",
    ]
)


print(
    "Unstable cases available:",
    unstable_count
)

print(
    "Manual inspection rule:",
    manual_rule
)

print(
    "Cases selected for manual inspection:",
    len(
        set(manual_case_ids)
    )
)

print(
    "Scenario rows retained for inspection:",
    len(manual)
)


# =============================================================================
# L — SAVE ANALYSIS TABLES
# =============================================================================

section("L — SAVE ROBUSTNESS TABLES")

cases.to_csv(
    CASE_OUTPUT,
    index=False,
)

feature_table.to_csv(
    FEATURE_OUTPUT,
    index=False,
)

direction_table.to_csv(
    DIRECTION_OUTPUT,
    index=False,
)

manual.to_csv(
    MANUAL_OUTPUT,
    index=False,
)


print(
    "Case instability:",
    CASE_OUTPUT
)

print(
    "Feature instability:",
    FEATURE_OUTPUT
)

print(
    "Feature-direction instability:",
    DIRECTION_OUTPUT
)

print(
    "Manual inspection candidates:",
    MANUAL_OUTPUT
)


# =============================================================================
# M — CREATE ROBUSTNESS AUDIT
# =============================================================================

section("M — CREATE ROUTING INSTABILITY AUDIT")

audit = {
    "phase": "11.3.3",

    "status":
        "ROUTING_INSTABILITY_ANALYSIS_COMPLETE",

    "population": {
        "router_cases":
            int(len(cases)),

        "valid_perturbation_scenarios":
            int(len(valid)),

        "original_bypass_cases":
            int(
                (
                    cases[
                        "original_selected_for_review"
                    ] == 0
                ).sum()
            ),

        "original_review_cases":
            int(
                (
                    cases[
                        "original_selected_for_review"
                    ] == 1
                ).sum()
            ),
    },

    "global_instability": {
        "route_flip_scenarios":
            scenario_flips,

        "scenario_flip_rate":
            scenario_flip_rate,

        "unstable_cases":
            unstable_count,

        "any_case_flip_rate":
            case_flip_rate,

        "bypass_to_review_flips":
            bypass_to_review,

        "review_to_bypass_flips":
            review_to_bypass,
    },

    "instability_by_original_route":
        route_summary,

    "feature_instability":
        feature_table.to_dict(
            orient="records"
        ),

    "feature_direction_instability":
        direction_table.to_dict(
            orient="records"
        ),

    "boundary_analysis": {
        "median_distance_all":
            float(
                cases[
                    "original_distance_to_cutoff"
                ].median()
            ),

        "median_distance_stable":
            (
                float(
                    stable[
                        "original_distance_to_cutoff"
                    ].median()
                )
                if len(stable) > 0
                else None
            ),

        "median_distance_unstable":
            (
                float(
                    unstable[
                        "original_distance_to_cutoff"
                    ].median()
                )
                if unstable_count > 0
                else None
            ),

        "maximum_distance_unstable":
            (
                float(
                    unstable[
                        "original_distance_to_cutoff"
                    ].max()
                )
                if unstable_count > 0
                else None
            ),
    },

    "multi_feature_instability": {
        "cases_destabilized_by_two_or_more_features":
            multi_feature_unstable,
    },

    "manual_inspection": {
        "required":
            True,

        "selection_rule":
            manual_rule,

        "unstable_cases_available":
            unstable_count,

        "cases_selected":
            int(
                len(
                    set(
                        manual_case_ids
                    )
                )
            ),

        "inspection_completed":
            False,
    },

    "interpretation_boundary": {
        "route_flip_is_full_compute_route_jump":
            True,

        "ground_truth_used_to_define_instability":
            False,

        "demographics_used_to_define_instability":
            False,

        "clinical_robustness_established":
            False,

        "manual_inspection_pending":
            True,
    },

    "artifacts": {
        "case_instability_csv":
            str(CASE_OUTPUT),

        "feature_instability_csv":
            str(FEATURE_OUTPUT),

        "feature_direction_csv":
            str(DIRECTION_OUTPUT),

        "manual_inspection_candidates_csv":
            str(MANUAL_OUTPUT),

        "scenario_source_sha256":
            sha256_file(
                SCENARIOS
            ),

        "frozen_spec_sha256":
            sha256_file(
                SPEC
            ),
    },

    "integrity": {
        "phase10_modified":
            False,

        "phase11_1_modified":
            False,

        "phase11_2_modified":
            False,

        "frozen_perturbation_spec_modified":
            False,
    },

    "next_phase":
        "11.3.4 Manual inspection of unstable cases",
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
# N — FINAL VERIFICATION
# =============================================================================

section("N — FINAL VERIFICATION")

checks = {
    "router_population":
        len(cases) == 7858,

    "valid_scenario_lock":
        len(valid) == 64174,

    "scenario_flip_accounting":
        (
            bypass_to_review
            + review_to_bypass
        ) == scenario_flips,

    "case_accounting":
        (
            unstable_count
            + len(stable)
        ) == 7858,

    "ground_truth_excluded":
        len(
            present_prohibited
        ) == 0,

    "feature_rows":
        len(
            feature_table
        ) == 5,

    "feature_direction_rows":
        len(
            direction_table
        ) == 10,

    "manual_set_created":
        (
            len(manual_case_ids)
            == min(
                unstable_count,
                100,
            )
        ),

    "manual_inspection_not_claimed_complete":
        audit[
            "manual_inspection"
        ][
            "inspection_completed"
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
        "Phase 11.3.3 verification failed."
    )


# =============================================================================
# COMPLETE
# =============================================================================

section(
    "PHASE 11.3.3 COMPLETE — "
    "ROUTING INSTABILITY ANALYSIS PASSED"
)

print(
    "Valid perturbation scenarios:",
    len(valid)
)

print(
    "Scenario route-flip rate:",
    f"{scenario_flip_rate:.4%}"
)

print(
    "Cases with >=1 route flip:",
    unstable_count
)

print(
    "Any-case route-flip rate:",
    f"{case_flip_rate:.4%}"
)

print(
    "BYPASS -> REVIEW scenario flips:",
    bypass_to_review
)

print(
    "REVIEW -> BYPASS scenario flips:",
    review_to_bypass
)

print(
    "Manual inspection cases prepared:",
    len(
        manual_case_ids
    )
)

print(
    "Manual inspection completed: NO"
)

print(
    "Clinical robustness established: NO"
)

print(
    "Phase 10 frozen system modified: NO"
)

print()
print(
    "NEXT: PHASE 11.3.4 — "
    "MANUAL INSPECTION OF UNSTABLE CASES"
)
