from pathlib import Path
import json
import hashlib
import joblib


# =============================================================================
# PATHS
# =============================================================================

INSPECTION = Path(
    "results/eligible/robustness/"
    "phase11_3_1_router_input_inspection.json"
)

ROUTER_MODEL = Path(
    "src/models/saved/eligible/router/"
    "fn_rescue_router.joblib"
)

OUTPUT_DIR = Path(
    "results/eligible/robustness"
)

OUTPUT = (
    OUTPUT_DIR /
    "phase11_3_1b_frozen_perturbation_specification.json"
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
    "PHASE 11.3.1B — FREEZE ROUTING ROBUSTNESS PERTURBATIONS"
)


# =============================================================================
# A — VERIFY INPUT INSPECTION
# =============================================================================

section("A — VERIFY 11.3.1 INPUT INSPECTION")

for path in [
    INSPECTION,
    ROUTER_MODEL,
]:
    if not path.exists():
        raise FileNotFoundError(path)

    print("FOUND:", path)


with INSPECTION.open() as f:
    inspection = json.load(f)


if (
    inspection["status"]
    != "ROUTER_INPUT_INSPECTION_COMPLETE"
):
    raise RuntimeError(
        "11.3.1 input inspection not complete."
    )


if inspection["route_flip_results_evaluated"]:
    raise RuntimeError(
        "Route-flip outcomes were already evaluated "
        "before perturbation freeze."
    )


if inspection["perturbations_frozen"]:
    raise RuntimeError(
        "11.3.1 inspection unexpectedly says "
        "perturbations were already frozen."
    )


print("11.3.1 inspection status: PASSED")
print("Route-flip outcomes previously evaluated: NO")


# =============================================================================
# B — VERIFY ACTUAL FROZEN ROUTER INPUTS
# =============================================================================

section("B — VERIFY FROZEN ROUTER INPUT CONTRACT")

router = joblib.load(
    ROUTER_MODEL
)

if not hasattr(
    router,
    "feature_names_in_",
):
    raise RuntimeError(
        "Frozen router does not expose feature_names_in_."
    )


router_features = [
    str(x)
    for x in router.feature_names_in_
]


expected_features = [
    "calibrated_probability",
    "model_disagreement_std",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
]


print("Frozen router features:")

for feature in router_features:
    print(" -", feature)


if router_features != expected_features:
    raise RuntimeError(
        "Frozen router feature contract differs "
        "from expected inspected contract."
    )


print("Frozen router input contract: PASSED")


# =============================================================================
# C — PREDECLARE PERTURBATIONS
# =============================================================================

section("C — PREDECLARE PERTURBATION MAGNITUDES")

perturbations = {
    "calibrated_probability": {
        "type": "continuous",
        "minus_delta": 0.005,
        "plus_delta": 0.005,
        "lower_bound": 0.0,
        "upper_bound": 1.0,
        "rationale":
            (
                "Small absolute probability perturbation "
                "of 0.5 percentage points."
            ),
    },

    "model_disagreement_std": {
        "type": "continuous",
        "minus_delta": 0.01,
        "plus_delta": 0.01,
        "lower_bound": 0.0,
        "upper_bound": None,
        "rationale":
            (
                "Small local perturbation relative to the "
                "observed disagreement distribution."
            ),
    },

    "number_diagnoses": {
        "type": "count",
        "minus_delta": 1,
        "plus_delta": 1,
        "lower_bound": 0,
        "upper_bound": None,
        "rationale":
            (
                "One diagnosis-count difference represents "
                "a small plausible coding/count perturbation."
            ),
    },

    "number_outpatient": {
        "type": "count",
        "minus_delta": 1,
        "plus_delta": 1,
        "lower_bound": 0,
        "upper_bound": None,
        "rationale":
            (
                "One outpatient encounter difference."
            ),
    },

    "number_emergency": {
        "type": "count",
        "minus_delta": 1,
        "plus_delta": 1,
        "lower_bound": 0,
        "upper_bound": None,
        "rationale":
            (
                "One emergency encounter difference."
            ),
    },
}


for feature, spec in perturbations.items():

    print()
    print(feature)

    print(
        " type:",
        spec["type"]
    )

    print(
        " minus:",
        spec["minus_delta"]
    )

    print(
        " plus:",
        spec["plus_delta"]
    )

    print(
        " lower bound:",
        spec["lower_bound"]
    )

    print(
        " upper bound:",
        spec["upper_bound"]
    )

    print(
        " rationale:",
        spec["rationale"]
    )


# =============================================================================
# D — DEFINE EXPERIMENTAL RULES
# =============================================================================

section("D — FREEZE EXPERIMENTAL RULES")

rules = {
    "perturbation_mode":
        "one_feature_at_a_time",

    "directions": [
        "minus",
        "plus",
    ],

    "expected_scenarios_per_case":
        10,

    "count_rounding":
        "integer_preserving",

    "lower_bound_handling":
        "clip",

    "upper_bound_handling":
        "clip_when_declared",

    "router_reexecution":
        "actual_frozen_router_pipeline",

    "manual_probability_editing":
        False,

    "manual_route_label_editing":
        False,

    "ground_truth_used_to_choose_perturbations":
        False,

    "route_flip_results_used_to_choose_perturbations":
        False,

    "demographics_perturbed":
        False,

    "simultaneous_multifeature_perturbation":
        False,
}


for key, value in rules.items():
    print(
        key + ":",
        value
    )


# =============================================================================
# E — DEFINE ROBUSTNESS OUTCOMES BEFORE EXECUTION
# =============================================================================

section("E — PREDECLARE ROBUSTNESS OUTCOMES")

outcomes = {
    "primary": {
        "any_route_flip_rate":
            (
                "Fraction of cases for which at least one "
                "predeclared single-feature perturbation "
                "changes selected_for_review."
            ),

        "scenario_flip_rate":
            (
                "Fraction of valid perturbation scenarios "
                "that change selected_for_review."
            ),
    },

    "secondary": {
        "flip_rate_by_feature":
            (
                "Route-flip rate separately for each "
                "perturbed router feature."
            ),

        "flip_rate_by_direction":
            (
                "Route-flip rate separately for plus/minus "
                "perturbations."
            ),

        "router_probability_change":
            (
                "Absolute and signed change in frozen "
                "router probability."
            ),

        "large_route_jump":
            (
                "Binary compute-route transition between "
                "bypass and Rescue Review."
            ),

        "distance_to_original_boundary":
            (
                "Original router probability distance from "
                "the frozen review cutoff."
            ),
    },

    "manual_inspection": {
        "required":
            True,

        "selection_rule":
            (
                "All route-flip cases if <=100; otherwise "
                "the 100 cases with the smallest original "
                "distance to the frozen routing boundary, "
                "with all perturbation scenarios retained "
                "for those cases."
            ),
    },
}


print(
    "Primary outcome 1: any-case route-flip rate"
)

print(
    "Primary outcome 2: scenario-level route-flip rate"
)

print(
    "Secondary: feature-specific instability"
)

print(
    "Secondary: direction-specific instability"
)

print(
    "Secondary: router-probability change"
)

print(
    "Manual unstable-case inspection: REQUIRED"
)


# =============================================================================
# F — SAVE FROZEN SPECIFICATION
# =============================================================================

section("F — SAVE FROZEN PERTURBATION SPECIFICATION")

artifact = {
    "phase": "11.3.1B",

    "status":
        "PERTURBATION_SPECIFICATION_FROZEN",

    "router_model":
        str(ROUTER_MODEL),

    "router_sha256":
        sha256_file(ROUTER_MODEL),

    "router_features":
        router_features,

    "perturbations":
        perturbations,

    "experimental_rules":
        rules,

    "predeclared_outcomes":
        outcomes,

    "information_boundary": {
        "actual_30d_used":
            False,

        "case_type_used":
            False,

        "router_target_used":
            False,

        "demographics_used":
            False,

        "existing_fn_router_probability_modified":
            False,

        "existing_selected_for_review_modified":
            False,
    },

    "freeze_state": {
        "perturbations_frozen":
            True,

        "route_flip_results_evaluated":
            False,

        "unstable_cases_inspected":
            False,
    },

    "integrity": {
        "phase10_modified":
            False,

        "phase11_1_modified":
            False,

        "phase11_2_modified":
            False,

        "phase11_3_1_modified":
            False,
    },

    "next_phase":
        "11.3.2 Perturb and re-run frozen router",
}


with OUTPUT.open("w") as f:
    json.dump(
        artifact,
        f,
        indent=2,
    )


print(
    "Frozen specification:",
    OUTPUT
)


# =============================================================================
# G — FINAL VERIFICATION
# =============================================================================

section("G — FINAL VERIFICATION")

with OUTPUT.open() as f:
    saved = json.load(f)


checks = {
    "status":
        saved["status"]
        == "PERTURBATION_SPECIFICATION_FROZEN",

    "five_router_features":
        len(
            saved["router_features"]
        ) == 5,

    "five_perturbation_features":
        len(
            saved["perturbations"]
        ) == 5,

    "feature_contract_match":
        saved["router_features"]
        == expected_features,

    "one_at_a_time":
        saved[
            "experimental_rules"
        ][
            "perturbation_mode"
        ]
        == "one_feature_at_a_time",

    "ground_truth_excluded":
        saved[
            "information_boundary"
        ][
            "actual_30d_used"
        ]
        is False,

    "demographics_excluded":
        saved[
            "information_boundary"
        ][
            "demographics_used"
        ]
        is False,

    "route_results_not_seen":
        saved[
            "freeze_state"
        ][
            "route_flip_results_evaluated"
        ]
        is False,

    "perturbations_frozen":
        saved[
            "freeze_state"
        ][
            "perturbations_frozen"
        ]
        is True,

    "phase10_unchanged":
        saved[
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
        "11.3.1B perturbation freeze failed."
    )


# =============================================================================
# COMPLETE
# =============================================================================

section(
    "PHASE 11.3.1B COMPLETE — PERTURBATION SPECIFICATION FROZEN"
)

print(
    "Router features:",
    len(router_features)
)

print(
    "Perturbation features:",
    len(perturbations)
)

print(
    "Scenarios per case:",
    rules[
        "expected_scenarios_per_case"
    ]
)

print(
    "Ground truth used to choose perturbations: NO"
)

print(
    "Route-flip outcomes inspected before freeze: NO"
)

print(
    "Perturbation specification frozen: YES"
)

print(
    "Phase 10 frozen system modified: NO"
)

print()
print(
    "NEXT: PHASE 11.3.2 — "
    "PERTURB AND RE-RUN FROZEN ROUTER"
)

