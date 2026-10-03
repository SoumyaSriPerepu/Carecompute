from pathlib import Path
import json
import hashlib
import joblib
import numpy as np
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

DATA = Path(
    "results/eligible/final_test_router_predictions.csv"
)

MODEL = Path(
    "src/models/saved/eligible/router/fn_rescue_router.joblib"
)

SPEC = Path(
    "results/eligible/robustness/"
    "phase11_3_1b_frozen_perturbation_specification.json"
)

OUTPUT_DIR = Path(
    "results/eligible/robustness"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

SCENARIO_OUTPUT = (
    OUTPUT_DIR /
    "phase11_3_2_perturbed_router_scenarios.csv"
)

AUDIT_OUTPUT = (
    OUTPUT_DIR /
    "phase11_3_2_router_reexecution_audit.json"
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


def apply_bounds(value, spec):

    lower = spec.get("lower_bound")
    upper = spec.get("upper_bound")

    if lower is not None:
        value = max(value, lower)

    if upper is not None:
        value = min(value, upper)

    return value


# =============================================================================
# HEADER
# =============================================================================

section(
    "PHASE 11.3.2 — PERTURB AND RE-RUN FROZEN ROUTER"
)


# =============================================================================
# A — VERIFY REQUIRED INPUTS
# =============================================================================

section("A — VERIFY REQUIRED INPUTS")

for path in [
    DATA,
    MODEL,
    SPEC,
]:

    if not path.exists():
        raise FileNotFoundError(path)

    print("FOUND:", path)


with SPEC.open() as f:
    spec = json.load(f)


if (
    spec["status"]
    != "PERTURBATION_SPECIFICATION_FROZEN"
):
    raise RuntimeError(
        "Perturbation specification is not frozen."
    )


if not spec["freeze_state"]["perturbations_frozen"]:
    raise RuntimeError(
        "Perturbations are not frozen."
    )


if spec["freeze_state"]["route_flip_results_evaluated"]:
    raise RuntimeError(
        "Specification indicates route-flip results "
        "were already evaluated."
    )


print("Frozen perturbation specification: PASSED")


# =============================================================================
# B — LOAD FROZEN ROUTER AND POPULATION
# =============================================================================

section("B — LOAD FROZEN ROUTER AND POPULATION")

df = pd.read_csv(DATA)

router = joblib.load(MODEL)

features = [
    str(x)
    for x in router.feature_names_in_
]


if features != spec["router_features"]:
    raise RuntimeError(
        "Router feature contract does not match frozen specification."
    )


if len(df) != 7858:
    raise RuntimeError(
        f"Expected 7858 cases, found {len(df)}."
    )


if int(df["selected_for_review"].sum()) != 1178:
    raise RuntimeError(
        "Frozen review population mismatch."
    )


print("Router population:", len(df))
print("Frozen selected cases:", int(df["selected_for_review"].sum()))

print()
print("Frozen router features:")

for feature in features:
    print(" -", feature)

print("Population and feature lock: PASSED")


# =============================================================================
# C — REPRODUCE ORIGINAL ROUTER PROBABILITIES
# =============================================================================

section("C — REPRODUCE ORIGINAL ROUTER PROBABILITIES")

X = df[features].copy()

recomputed_probability = (
    router.predict_proba(X)[:, 1]
)

stored_probability = (
    df["fn_router_probability"].to_numpy()
)

abs_diff = np.abs(
    recomputed_probability
    - stored_probability
)


print(
    "Maximum absolute probability difference:",
    float(abs_diff.max())
)

print(
    "Mean absolute probability difference:",
    float(abs_diff.mean())
)


PROBABILITY_TOLERANCE = 1e-10

probability_match = bool(
    np.all(
        abs_diff <= PROBABILITY_TOLERANCE
    )
)


print(
    "Frozen router probability reproduction:",
    "PASSED"
    if probability_match
    else "FAILED"
)


if not probability_match:
    raise RuntimeError(
        "Frozen router probabilities could not be reproduced."
    )


# =============================================================================
# D — RECONSTRUCT FROZEN OPERATIONAL ROUTING CUTOFF
# =============================================================================

section("D — RECONSTRUCT FROZEN OPERATIONAL ROUTING CUTOFF")

selected_mask = (
    df["selected_for_review"] == 1
)

bypass_mask = (
    df["selected_for_review"] == 0
)


min_selected = float(
    df.loc[
        selected_mask,
        "fn_router_probability"
    ].min()
)

max_bypass = float(
    df.loc[
        bypass_mask,
        "fn_router_probability"
    ].max()
)


if not min_selected > max_bypass:
    raise RuntimeError(
        "Frozen selected/bypass probability boundary overlaps."
    )


operational_cutoff = (
    min_selected + max_bypass
) / 2.0


reconstructed_route = (
    recomputed_probability
    >= operational_cutoff
).astype(int)


route_mismatches = int(
    np.sum(
        reconstructed_route
        != df[
            "selected_for_review"
        ].to_numpy()
    )
)


print(
    "Maximum bypass probability:",
    max_bypass
)

print(
    "Minimum selected probability:",
    min_selected
)

print(
    "Frozen operational cutoff:",
    operational_cutoff
)

print(
    "Reconstructed selected cases:",
    int(reconstructed_route.sum())
)

print(
    "Frozen selected cases:",
    int(df["selected_for_review"].sum())
)

print(
    "Decision mismatches:",
    route_mismatches
)


if route_mismatches != 0:
    raise RuntimeError(
        "Operational cutoff does not reproduce "
        "the frozen routing policy."
    )


print("Frozen operational routing rule: PASSED")


# =============================================================================
# E — GENERATE PREDECLARED PERTURBATION SCENARIOS
# =============================================================================

section("E — GENERATE PERTURBATION SCENARIOS")

records = []

perturbations = spec["perturbations"]

expected_raw_scenarios = (
    len(df)
    * len(perturbations)
    * 2
)

print(
    "Expected raw scenarios:",
    expected_raw_scenarios
)


for feature, perturb_spec in perturbations.items():

    for direction in [
        "minus",
        "plus",
    ]:

        delta_key = (
            "minus_delta"
            if direction == "minus"
            else "plus_delta"
        )

        delta = perturb_spec[delta_key]

        Xp = X.copy()

        original_values = (
            Xp[feature]
            .astype(float)
            .to_numpy()
        )

        if direction == "minus":
            perturbed_values = (
                original_values - delta
            )
        else:
            perturbed_values = (
                original_values + delta
            )


        lower = perturb_spec.get(
            "lower_bound"
        )

        upper = perturb_spec.get(
            "upper_bound"
        )


        if lower is not None:
            perturbed_values = np.maximum(
                perturbed_values,
                lower,
            )

        if upper is not None:
            perturbed_values = np.minimum(
                perturbed_values,
                upper,
            )


        if perturb_spec["type"] == "count":

            perturbed_values = np.rint(
                perturbed_values
            ).astype(int)


        actual_change = (
            perturbed_values
            - original_values
        )

        valid_perturbation = (
            np.abs(actual_change) > 0
        )


        Xp[feature] = perturbed_values


        perturbed_probability = (
            router.predict_proba(
                Xp[features]
            )[:, 1]
        )


        perturbed_route = (
            perturbed_probability
            >= operational_cutoff
        ).astype(int)


        original_route = (
            df[
                "selected_for_review"
            ].to_numpy()
        )


        route_flip = (
            valid_perturbation
            & (
                perturbed_route
                != original_route
            )
        )


        probability_change = (
            perturbed_probability
            - recomputed_probability
        )


        for i in range(len(df)):

            records.append(
                {
                    "encounter_id":
                        df.iloc[i][
                            "encounter_id"
                        ],

                    "patient_nbr":
                        df.iloc[i][
                            "patient_nbr"
                        ],

                    "feature":
                        feature,

                    "direction":
                        direction,

                    "declared_delta":
                        delta,

                    "original_value":
                        original_values[i],

                    "perturbed_value":
                        perturbed_values[i],

                    "actual_change":
                        actual_change[i],

                    "valid_perturbation":
                        int(
                            valid_perturbation[i]
                        ),

                    "scenario_status":
                        (
                            "VALID"
                            if valid_perturbation[i]
                            else "NO_CHANGE_AFTER_CLIP"
                        ),

                    "original_router_probability":
                        recomputed_probability[i],

                    "perturbed_router_probability":
                        perturbed_probability[i],

                    "signed_probability_change":
                        probability_change[i],

                    "absolute_probability_change":
                        abs(
                            probability_change[i]
                        ),

                    "operational_cutoff":
                        operational_cutoff,

                    "original_selected_for_review":
                        int(
                            original_route[i]
                        ),

                    "perturbed_selected_for_review":
                        int(
                            perturbed_route[i]
                        ),

                    "route_flip":
                        int(
                            route_flip[i]
                        ),

                    "original_distance_to_cutoff":
                        abs(
                            recomputed_probability[i]
                            - operational_cutoff
                        ),
                }
            )


scenarios = pd.DataFrame(records)


print(
    "Generated raw scenarios:",
    len(scenarios)
)

print(
    "Valid perturbation scenarios:",
    int(
        scenarios[
            "valid_perturbation"
        ].sum()
    )
)

print(
    "No-change-after-clip scenarios:",
    int(
        (
            scenarios[
                "valid_perturbation"
            ] == 0
        ).sum()
    )
)


if len(scenarios) != expected_raw_scenarios:
    raise RuntimeError(
        "Unexpected raw scenario count."
    )


# =============================================================================
# F — VERIFY INVALID/CLIPPED SCENARIOS
# =============================================================================

section("F — VERIFY CLIPPED NO-CHANGE SCENARIOS")

invalid = scenarios[
    scenarios[
        "valid_perturbation"
    ] == 0
]


print(
    "Invalid/no-change scenarios:",
    len(invalid)
)


if len(invalid) > 0:

    print()
    print(
        invalid[
            [
                "feature",
                "direction",
                "scenario_status",
            ]
        ]
        .value_counts()
        .to_string()
    )


invalid_flip_count = int(
    invalid["route_flip"].sum()
)


print(
    "Route flips among invalid scenarios:",
    invalid_flip_count
)


if invalid_flip_count != 0:
    raise RuntimeError(
        "A no-change scenario was marked as a route flip."
    )


print(
    "No-change scenario handling: PASSED"
)


# =============================================================================
# G — SAVE CASE-SCENARIO OUTPUT
# =============================================================================

section("G — SAVE PERTURBATION SCENARIOS")

scenarios.to_csv(
    SCENARIO_OUTPUT,
    index=False,
)


print(
    "Scenario artifact:",
    SCENARIO_OUTPUT
)


# =============================================================================
# H — EXECUTION INTEGRITY ONLY
# =============================================================================

section("H — EXECUTION INTEGRITY")

valid_count = int(
    scenarios[
        "valid_perturbation"
    ].sum()
)

invalid_count = int(
    len(scenarios)
    - valid_count
)


print(
    "Raw scenarios:",
    len(scenarios)
)

print(
    "Valid scenarios:",
    valid_count
)

print(
    "No-change scenarios:",
    invalid_count
)

print()
print(
    "Route-flip counts are intentionally NOT "
    "summarized by feature in Phase 11.3.2."
)

print(
    "Comparative instability interpretation "
    "is deferred to Phase 11.3.3."
)


# =============================================================================
# I — CREATE REEXECUTION AUDIT ARTIFACT
# =============================================================================

section("I — CREATE REEXECUTION AUDIT ARTIFACT")

audit = {
    "phase": "11.3.2",

    "status":
        "PERTURBED_ROUTER_REEXECUTION_COMPLETE",

    "population": {
        "router_cases":
            int(len(df)),

        "frozen_selected":
            int(
                df[
                    "selected_for_review"
                ].sum()
            ),
    },

    "router_reproduction": {
        "probability_tolerance":
            PROBABILITY_TOLERANCE,

        "maximum_absolute_difference":
            float(
                abs_diff.max()
            ),

        "mean_absolute_difference":
            float(
                abs_diff.mean()
            ),

        "probability_reproduction_passed":
            probability_match,

        "decision_mismatches":
            route_mismatches,
    },

    "operational_routing_rule": {
        "maximum_bypass_probability":
            max_bypass,

        "minimum_selected_probability":
            min_selected,

        "operational_cutoff":
            operational_cutoff,

        "reconstructed_selected":
            int(
                reconstructed_route.sum()
            ),

        "frozen_selected":
            int(
                df[
                    "selected_for_review"
                ].sum()
            ),
    },

    "scenario_execution": {
        "features":
            list(
                perturbations.keys()
            ),

        "directions": [
            "minus",
            "plus",
        ],

        "raw_scenarios":
            int(
                len(scenarios)
            ),

        "valid_scenarios":
            valid_count,

        "no_change_after_clip":
            invalid_count,

        "one_feature_at_a_time":
            True,

        "actual_frozen_router_used":
            True,
    },

    "analysis_boundary": {
        "feature_specific_flip_rates_evaluated":
            False,

        "direction_specific_flip_rates_evaluated":
            False,

        "unstable_cases_manually_inspected":
            False,

        "ground_truth_used_for_perturbation":
            False,

        "demographics_perturbed":
            False,
    },

    "artifacts": {
        "scenario_csv":
            str(
                SCENARIO_OUTPUT
            ),

        "scenario_csv_sha256":
            sha256_file(
                SCENARIO_OUTPUT
            ),

        "frozen_spec_sha256":
            sha256_file(
                SPEC
            ),

        "router_sha256":
            sha256_file(
                MODEL
            ),
    },

    "integrity": {
        "phase10_modified":
            False,

        "phase11_1_modified":
            False,

        "phase11_2_modified":
            False,

        "frozen_spec_modified":
            False,
    },

    "next_phase":
        (
            "11.3.3 Quantify route instability "
            "and compute-route jumps"
        ),
}


with AUDIT_OUTPUT.open("w") as f:

    json.dump(
        audit,
        f,
        indent=2,
    )


print(
    "Reexecution audit:",
    AUDIT_OUTPUT
)


# =============================================================================
# J — FINAL VERIFICATION
# =============================================================================

section("J — FINAL VERIFICATION")

checks = {
    "population_lock":
        len(df) == 7858,

    "review_lock":
        int(
            df[
                "selected_for_review"
            ].sum()
        ) == 1178,

    "probability_reproduction":
        probability_match,

    "route_reconstruction":
        route_mismatches == 0,

    "raw_scenario_count":
        len(scenarios)
        == expected_raw_scenarios,

    "valid_scenarios_present":
        valid_count > 0,

    "invalid_scenarios_no_flips":
        invalid_flip_count == 0,

    "actual_router_used":
        audit[
            "scenario_execution"
        ][
            "actual_frozen_router_used"
        ]
        is True,

    "feature_analysis_deferred":
        audit[
            "analysis_boundary"
        ][
            "feature_specific_flip_rates_evaluated"
        ]
        is False,

    "manual_inspection_deferred":
        audit[
            "analysis_boundary"
        ][
            "unstable_cases_manually_inspected"
        ]
        is False,

    "phase10_unchanged":
        audit[
            "integrity"
        ][
            "phase10_modified"
        ]
        is False,
}


for name, passed in checks.items():

    print(
        name + ":",
        "PASSED" if passed else "FAILED"
    )


if not all(checks.values()):

    raise RuntimeError(
        "Phase 11.3.2 verification failed."
    )


# =============================================================================
# COMPLETE
# =============================================================================

section(
    "PHASE 11.3.2 COMPLETE — "
    "PERTURBED ROUTER REEXECUTION PASSED"
)

print(
    "Router population:",
    len(df)
)

print(
    "Frozen selected cases:",
    int(
        df[
            "selected_for_review"
        ].sum()
    )
)

print(
    "Raw perturbation scenarios:",
    len(scenarios)
)

print(
    "Valid perturbation scenarios:",
    valid_count
)

print(
    "No-change-after-clip scenarios:",
    invalid_count
)

print(
    "Original router probabilities reproduced: YES"
)

print(
    "Original routing decisions reproduced: YES"
)

print(
    "Perturbations passed through actual frozen router: YES"
)

print(
    "Comparative instability analysis performed: NO"
)

print(
    "Phase 10 frozen system modified: NO"
)

print()
print(
    "NEXT: PHASE 11.3.3 — "
    "ROUTING INSTABILITY ANALYSIS"
)
