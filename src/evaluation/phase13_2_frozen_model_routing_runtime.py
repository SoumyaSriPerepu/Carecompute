from pathlib import Path
import json
import hashlib
import joblib
import numpy as np
import pandas as pd


print("=" * 80)
print("PHASE 13.2 — FROZEN MODEL AND ROUTING RUNTIME")
print("=" * 80)


# =============================================================================
# PATHS
# =============================================================================

ROUTER_MODEL = Path(
    "src/models/saved/eligible/router/fn_rescue_router.joblib"
)

ROUTER_PREDICTIONS = Path(
    "results/eligible/final_test_router_predictions.csv"
)

AGENT_INPUT_CONTRACT = Path(
    "results/eligible/agents/agent_input_contract.json"
)

PHASE13_ARCHITECTURE = Path(
    "results/eligible/phase13/"
    "phase13_1_integrated_agent_architecture.json"
)

PHASE12_FREEZE = Path(
    "results/eligible/final_comparison/"
    "phase12_final_closure_manifest.json"
)

OUT_DIR = Path(
    "results/eligible/phase13"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

RUNTIME_OUTPUT = (
    OUT_DIR /
    "phase13_2_frozen_routing_runtime.csv"
)

ELIGIBLE_OUTPUT = (
    OUT_DIR /
    "phase13_2_agent_eligible_runtime.csv"
)

RUNTIME_MANIFEST = (
    OUT_DIR /
    "phase13_2_frozen_runtime_manifest.json"
)

RUNTIME_AUDIT = (
    OUT_DIR /
    "phase13_2_runtime_replay_audit.json"
)


# =============================================================================
# CONSTANTS
# =============================================================================

PRIMARY_THRESHOLD = 0.115

REVIEW_BUDGET = 0.15

EXPECTED_ROUTING_POPULATION = 7858

EXPECTED_SELECTED_CASES = 1178

EXPECTED_PRIMARY_FALSE_NEGATIVES = 557

EXPECTED_ESCALATED_FALSE_NEGATIVES = 110


ROUTER_FEATURES = [
    "calibrated_probability",
    "model_disagreement_std",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
]


PROHIBITED_AGENT_FIELDS = [
    "actual_30d",
    "case_type",
    "router_target",
    "patient_nbr",
]


# =============================================================================
# HELPERS
# =============================================================================

def section(title):

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def require(condition, message):

    if not condition:
        raise RuntimeError(message)


def load_json(path):

    with open(path, "r") as f:
        return json.load(f)


def sha256(path):

    h = hashlib.sha256()

    with open(path, "rb") as f:

        for block in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(block)

    return h.hexdigest()


# =============================================================================
# A — VERIFY FROZEN DEPENDENCIES
# =============================================================================

section("A — VERIFY FROZEN DEPENDENCIES")


required_files = [
    ROUTER_MODEL,
    ROUTER_PREDICTIONS,
    AGENT_INPUT_CONTRACT,
    PHASE13_ARCHITECTURE,
    PHASE12_FREEZE,
]


for path in required_files:

    require(
        path.exists(),
        f"Missing required frozen dependency: {path}"
    )

    print(
        "FOUND:",
        path
    )


print()
print("Frozen dependency presence: PASSED")


# =============================================================================
# B — LOAD FROZEN CONTRACTS
# =============================================================================

section("B — LOAD FROZEN CONTRACTS")


contract = load_json(
    AGENT_INPUT_CONTRACT
)

architecture = load_json(
    PHASE13_ARCHITECTURE
)

phase12 = load_json(
    PHASE12_FREEZE
)


print(
    "Agent contract version:",
    contract.get(
        "contract_version"
    )
)

print(
    "Architecture status:",
    architecture.get(
        "status"
    )
)

print(
    "Phase 12 status:",
    phase12.get(
        "status"
    )
)


require(
    contract.get(
        "contract_version"
    ) == "10.1",
    "Unexpected agent input contract version."
)


require(
    architecture.get(
        "status"
    )
    ==
    "FINAL_INTEGRATED_AGENT_ARCHITECTURE_FROZEN",
    "Phase 13.1 architecture is not frozen."
)


require(
    phase12.get(
        "status"
    )
    ==
    "PHASE_12_FINAL_COMPARISON_FROZEN",
    "Phase 12 is not frozen."
)


print()
print("Frozen contract load: PASSED")


# =============================================================================
# C — VERIFY FROZEN PARAMETERS
# =============================================================================

section("C — VERIFY FROZEN PARAMETERS")


print(
    "Primary threshold:",
    contract[
        "frozen_threshold"
    ]
)

print(
    "Review budget:",
    contract[
        "frozen_review_budget"
    ]
)

print(
    "Expected agent cases:",
    contract[
        "expected_cases"
    ]
)


require(
    float(
        contract[
            "frozen_threshold"
        ]
    ) == PRIMARY_THRESHOLD,
    "Primary threshold changed."
)


require(
    float(
        contract[
            "frozen_review_budget"
        ]
    ) == REVIEW_BUDGET,
    "Review budget changed."
)


require(
    int(
        contract[
            "expected_cases"
        ]
    ) == EXPECTED_SELECTED_CASES,
    "Expected selected-case count changed."
)


require(
    contract[
        "ground_truth_available_to_agent"
    ] is False,
    "Ground truth unexpectedly available to agent."
)


require(
    contract[
        "human_review_required"
    ] is True,
    "Human review requirement changed."
)


print()
print("Frozen parameter lock: PASSED")


# =============================================================================
# D — LOAD FROZEN ROUTING POPULATION
# =============================================================================

section("D — LOAD FROZEN ROUTING POPULATION")


df = pd.read_csv(
    ROUTER_PREDICTIONS
)


print(
    "Rows:",
    len(df)
)

print(
    "Columns:",
    len(df.columns)
)

print(
    "Unique encounters:",
    df[
        "encounter_id"
    ].nunique()
)


require(
    len(df)
    == EXPECTED_ROUTING_POPULATION,
    "Routing population changed."
)


require(
    df[
        "encounter_id"
    ].nunique()
    == EXPECTED_ROUTING_POPULATION,
    "Duplicate encounter IDs detected."
)


print()
print("Routing population lock: PASSED")


# =============================================================================
# E — VERIFY REQUIRED RUNTIME COLUMNS
# =============================================================================

section("E — VERIFY REQUIRED RUNTIME COLUMNS")


required_runtime_columns = [
    "encounter_id",
    "calibrated_probability",
    "threshold",
    "predicted_30d",
    "model_disagreement_std",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
    "number_inpatient",
    "time_in_hospital",
    "age",
    "gender",
    "race",
    "fn_router_probability",
    "selected_for_review",
]


for column in required_runtime_columns:

    require(
        column in df.columns,
        f"Missing runtime column: {column}"
    )

    print(
        "FOUND:",
        column
    )


print()
print("Runtime column contract: PASSED")


# =============================================================================
# F — VERIFY THIS IS PRIMARY-MODEL-NEGATIVE POPULATION
# =============================================================================

section("F — VERIFY PRIMARY-MODEL-NEGATIVE ROUTING POPULATION")


predicted_values = sorted(
    df[
        "predicted_30d"
    ].dropna().unique().tolist()
)


print(
    "Observed predicted_30d values:",
    predicted_values
)


require(
    predicted_values == [0],
    "Router population contains non-negative primary predictions."
)


require(
    np.allclose(
        df[
            "threshold"
        ].astype(float),
        PRIMARY_THRESHOLD
    ),
    "Primary threshold column does not match frozen threshold."
)


require(
    (
        df[
            "calibrated_probability"
        ]
        <
        PRIMARY_THRESHOLD
    ).all(),
    "Found primary-negative case at or above frozen threshold."
)


print(
    "Primary-model-negative cases:",
    len(df)
)

print()
print("Primary negative population: PASSED")


# =============================================================================
# G — VERIFY FROZEN ROUTER FEATURE CONTRACT
# =============================================================================

section("G — VERIFY FROZEN ROUTER FEATURE CONTRACT")


contract_features = contract[
    "router_features"
]


print(
    "Contract router features:"
)


for feature in contract_features:

    print(
        " -",
        feature
    )


require(
    contract_features
    == ROUTER_FEATURES,
    "Router feature contract changed."
)


for feature in ROUTER_FEATURES:

    require(
        feature in df.columns,
        f"Missing router feature: {feature}"
    )


X_router = df[
    ROUTER_FEATURES
].copy()


missing_counts = (
    X_router
    .isna()
    .sum()
)


print()
print("Missing values:")


for feature in ROUTER_FEATURES:

    print(
        feature,
        "->",
        int(
            missing_counts[
                feature
            ]
        )
    )


require(
    int(
        missing_counts.sum()
    ) == 0,
    "Missing router feature values detected."
)


print()
print("Router feature contract: PASSED")


# =============================================================================
# H — LOAD FROZEN LEARNED ROUTER
# =============================================================================

section("H — LOAD FROZEN LEARNED ROUTER")


router = joblib.load(
    ROUTER_MODEL
)


print(
    "Router class:",
    type(router).__name__
)


require(
    hasattr(
        router,
        "predict_proba"
    ),
    "Frozen router does not support predict_proba."
)


if hasattr(
    router,
    "feature_names_in_"
):

    observed_model_features = list(
        router.feature_names_in_
    )

    print()
    print(
        "Router feature_names_in_:"
    )

    for feature in observed_model_features:

        print(
            " -",
            feature
        )

    require(
        observed_model_features
        == ROUTER_FEATURES,
        "Frozen router feature names changed."
    )


print()
print("Frozen learned router load: PASSED")


# =============================================================================
# I — REPLAY FROZEN ROUTER PROBABILITIES
# =============================================================================

section("I — REPLAY FROZEN ROUTER PROBABILITIES")


replayed_probability = (
    router.predict_proba(
        X_router
    )[:, 1]
)


stored_probability = (
    df[
        "fn_router_probability"
    ]
    .astype(float)
    .to_numpy()
)


probability_difference = np.abs(
    replayed_probability
    -
    stored_probability
)


max_probability_difference = float(
    probability_difference.max()
)


mean_probability_difference = float(
    probability_difference.mean()
)


print(
    "Maximum probability difference:",
    max_probability_difference
)

print(
    "Mean probability difference:",
    mean_probability_difference
)


require(
    max_probability_difference
    <= 1e-12,
    "Frozen router probability replay failed."
)


print()
print("Frozen router probability replay: PASSED")


# =============================================================================
# J — REPLAY FIXED-BUDGET ROUTING
# =============================================================================

section("J — REPLAY FIXED-BUDGET ROUTING")


runtime = df.copy()


runtime[
    "runtime_router_probability"
] = replayed_probability


runtime = runtime.sort_values(
    by=[
        "runtime_router_probability",
        "encounter_id",
    ],
    ascending=[
        False,
        True,
    ],
    kind="mergesort",
).copy()


runtime[
    "runtime_selected_for_review"
] = 0


runtime.iloc[
    :EXPECTED_SELECTED_CASES,
    runtime.columns.get_loc(
        "runtime_selected_for_review"
    )
] = 1


runtime = runtime.sort_values(
    "encounter_id"
).reset_index(
    drop=True
)


stored_sorted = (
    df.sort_values(
        "encounter_id"
    )
    .reset_index(
        drop=True
    )
)


require(
    np.array_equal(
        runtime[
            "encounter_id"
        ].to_numpy(),
        stored_sorted[
            "encounter_id"
        ].to_numpy()
    ),
    "Encounter alignment failed during replay."
)


stored_selection = (
    stored_sorted[
        "selected_for_review"
    ]
    .astype(int)
    .to_numpy()
)


runtime_selection = (
    runtime[
        "runtime_selected_for_review"
    ]
    .astype(int)
    .to_numpy()
)


selection_mismatches = int(
    (
        stored_selection
        !=
        runtime_selection
    ).sum()
)


runtime_selected_count = int(
    runtime_selection.sum()
)


print(
    "Runtime selected cases:",
    runtime_selected_count
)

print(
    "Stored selected cases:",
    int(
        stored_selection.sum()
    )
)

print(
    "Selection mismatches:",
    selection_mismatches
)


require(
    runtime_selected_count
    == EXPECTED_SELECTED_CASES,
    "Runtime review budget failed."
)


require(
    int(
        stored_selection.sum()
    )
    == EXPECTED_SELECTED_CASES,
    "Stored review count changed."
)


require(
    selection_mismatches == 0,
    "Runtime selection does not reproduce frozen System D."
)


print()
print("Frozen System D routing replay: PASSED")


# =============================================================================
# K — VERIFY RANKING BOUNDARY
# =============================================================================

section("K — VERIFY ROUTING RANKING BOUNDARY")


selected_runtime = runtime[
    runtime[
        "runtime_selected_for_review"
    ] == 1
]


bypassed_runtime = runtime[
    runtime[
        "runtime_selected_for_review"
    ] == 0
]


minimum_selected_probability = float(
    selected_runtime[
        "runtime_router_probability"
    ].min()
)


maximum_bypassed_probability = float(
    bypassed_runtime[
        "runtime_router_probability"
    ].max()
)


print(
    "Minimum selected router probability:",
    minimum_selected_probability
)

print(
    "Maximum bypassed router probability:",
    maximum_bypassed_probability
)


require(
    minimum_selected_probability
    >=
    maximum_bypassed_probability,
    "Routing ranking boundary invalid."
)


print()
print("Routing ranking boundary: PASSED")


# =============================================================================
# L — RETROSPECTIVE EVALUATION LOCK
# =============================================================================

section("L — RETROSPECTIVE EVALUATION LOCK")


# Ground truth is used HERE ONLY to verify that the runtime replay
# reproduces the already-frozen scientific result.
#
# It is never copied into agent runtime packets.


require(
    "actual_30d"
    in runtime.columns,
    "Ground truth unavailable for retrospective replay audit."
)


primary_false_negative_mask = (
    (
        runtime[
            "actual_30d"
        ] == 1
    )
    &
    (
        runtime[
            "predicted_30d"
        ] == 0
    )
)


primary_false_negatives = int(
    primary_false_negative_mask.sum()
)


escalated_false_negatives = int(
    (
        primary_false_negative_mask
        &
        (
            runtime[
                "runtime_selected_for_review"
            ] == 1
        )
    ).sum()
)


fn_coverage = (
    escalated_false_negatives
    /
    primary_false_negatives
)


print(
    "Primary false negatives:",
    primary_false_negatives
)

print(
    "Escalated false negatives:",
    escalated_false_negatives
)

print(
    "FN coverage:",
    f"{fn_coverage:.6f}"
)


require(
    primary_false_negatives
    == EXPECTED_PRIMARY_FALSE_NEGATIVES,
    "Primary FN lock failed."
)


require(
    escalated_false_negatives
    == EXPECTED_ESCALATED_FALSE_NEGATIVES,
    "System D FN escalation lock failed."
)


print()
print(
    "Ground truth used for routing: NO"
)

print(
    "Ground truth used for retrospective replay audit: YES"
)

print()
print("Frozen scientific-result replay: PASSED")


# =============================================================================
# M — BUILD AGENT-SAFE RUNTIME TABLE
# =============================================================================

section("M — BUILD AGENT-SAFE RUNTIME TABLE")


runtime[
    "decision_threshold"
] = PRIMARY_THRESHOLD


runtime[
    "router_probability"
] = runtime[
    "runtime_router_probability"
]


runtime[
    "selected_for_review_runtime"
] = runtime[
    "runtime_selected_for_review"
]


# Convert source age field to contract name.
runtime[
    "age_group"
] = runtime[
    "age"
]


agent_safe_columns = [
    "encounter_id",
    "calibrated_probability",
    "decision_threshold",
    "predicted_30d",
    "model_disagreement_std",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
    "number_inpatient",
    "time_in_hospital",
    "router_probability",
    "selected_for_review_runtime",
    "age_group",
    "gender",
    "race",
]


agent_runtime = runtime[
    agent_safe_columns
].copy()


agent_runtime = agent_runtime.rename(
    columns={
        "selected_for_review_runtime":
            "selected_for_review"
    }
)


print(
    "Agent-safe runtime rows:",
    len(agent_runtime)
)

print(
    "Agent-safe runtime columns:",
    len(agent_runtime.columns)
)


for prohibited in PROHIBITED_AGENT_FIELDS:

    require(
        prohibited
        not in agent_runtime.columns,
        f"Prohibited field exposed: {prohibited}"
    )


print()
print(
    "Ground truth exposed:",
    "actual_30d"
    in agent_runtime.columns
)

print(
    "Patient identifier exposed:",
    "patient_nbr"
    in agent_runtime.columns
)

print(
    "Case type exposed:",
    "case_type"
    in agent_runtime.columns
)

print(
    "Router target exposed:",
    "router_target"
    in agent_runtime.columns
)


print()
print("Agent-safe runtime table: PASSED")


# =============================================================================
# N — VERIFY AGENT CONTRACT ALLOWLIST
# =============================================================================

section("N — VERIFY AGENT CONTRACT ALLOWLIST")


allowed_fields = set(
    contract[
        "allowed_fields"
    ]
)


runtime_fields = set(
    agent_runtime.columns
)


unexpected_fields = (
    runtime_fields
    -
    allowed_fields
)


missing_core_fields = set(
    [
        "encounter_id",
        "calibrated_probability",
        "decision_threshold",
        "predicted_30d",
        "model_disagreement_std",
        "number_diagnoses",
        "number_outpatient",
        "number_emergency",
        "number_inpatient",
        "time_in_hospital",
        "router_probability",
        "selected_for_review",
        "age_group",
        "gender",
        "race",
    ]
) - runtime_fields


print(
    "Unexpected runtime fields:",
    sorted(
        unexpected_fields
    )
)

print(
    "Missing core fields:",
    sorted(
        missing_core_fields
    )
)


require(
    len(
        unexpected_fields
    ) == 0,
    "Runtime exposes fields outside agent allowlist."
)


require(
    len(
        missing_core_fields
    ) == 0,
    "Runtime missing required agent fields."
)


print()
print("Agent input allowlist verification: PASSED")


# =============================================================================
# O — BUILD AGENT-ELIGIBLE POPULATION
# =============================================================================

section("O — BUILD AGENT-ELIGIBLE POPULATION")


agent_eligible = agent_runtime[
    agent_runtime[
        "selected_for_review"
    ] == 1
].copy()


agent_eligible = agent_eligible.sort_values(
    "encounter_id"
).reset_index(
    drop=True
)


print(
    "Agent-eligible cases:",
    len(agent_eligible)
)


require(
    len(agent_eligible)
    == EXPECTED_SELECTED_CASES,
    "Agent-eligible population changed."
)


require(
    (
        agent_eligible[
            "predicted_30d"
        ] == 0
    ).all(),
    "Agent population contains primary-positive cases."
)


require(
    (
        agent_eligible[
            "selected_for_review"
        ] == 1
    ).all(),
    "Agent population contains bypassed cases."
)


print()
print("Agent eligibility gate: PASSED")


# =============================================================================
# P — SAVE RUNTIME OUTPUTS
# =============================================================================

section("P — SAVE RUNTIME OUTPUTS")


agent_runtime.to_csv(
    RUNTIME_OUTPUT,
    index=False
)


agent_eligible.to_csv(
    ELIGIBLE_OUTPUT,
    index=False
)


print(
    "Runtime table:",
    RUNTIME_OUTPUT
)

print(
    "Agent-eligible table:",
    ELIGIBLE_OUTPUT
)


require(
    RUNTIME_OUTPUT.exists(),
    "Runtime output not created."
)


require(
    ELIGIBLE_OUTPUT.exists(),
    "Eligible runtime output not created."
)


print()
print("Runtime outputs saved: PASSED")


# =============================================================================
# Q — CAPTURE SOURCE HASHES
# =============================================================================

section("Q — CAPTURE FROZEN SOURCE HASHES")


source_hashes = {}


for path in required_files:

    digest = sha256(
        path
    )

    source_hashes[
        str(path)
    ] = digest

    print(
        path.name,
        "->",
        digest
    )


print()
print("Source hashes captured: PASSED")


# =============================================================================
# R — CREATE FROZEN RUNTIME MANIFEST
# =============================================================================

section("R — CREATE FROZEN RUNTIME MANIFEST")


manifest = {

    "phase":
        "13.2",

    "status":
        "FROZEN_MODEL_ROUTING_RUNTIME_COMPLETE",

    "system":
        "CareCompute",

    "runtime_mode":
        "FROZEN_PRIMARY_OUTPUT_REPLAY_PLUS_FROZEN_ROUTER_INFERENCE",

    "important_boundary":
        (
            "Phase 13.2 consumes already-frozen primary-model "
            "outputs from final_test_router_predictions.csv and "
            "executes the frozen learned rescue router. It does "
            "not claim fresh raw-patient primary-model inference."
        ),

    "primary_model_runtime": {

        "mode":
            "FROZEN_OUTPUT_REPLAY",

        "decision_threshold":
            PRIMARY_THRESHOLD,

        "retrained":
            False,

        "retuned":
            False,

        "prediction_modified":
            False,
    },

    "router_runtime": {

        "model_path":
            str(
                ROUTER_MODEL
            ),

        "features":
            ROUTER_FEATURES,

        "population":
            EXPECTED_ROUTING_POPULATION,

        "review_budget":
            REVIEW_BUDGET,

        "selected_cases":
            EXPECTED_SELECTED_CASES,

        "probability_replay_max_difference":
            max_probability_difference,

        "selection_mismatches":
            selection_mismatches,

        "retrained":
            False,

        "retuned":
            False,
    },

    "scientific_replay": {

        "primary_false_negatives":
            primary_false_negatives,

        "false_negatives_escalated":
            escalated_false_negatives,

        "false_negative_review_coverage":
            fn_coverage,

        "ground_truth_used_for_routing":
            False,

        "ground_truth_used_for_retrospective_audit":
            True,
    },

    "agent_runtime_boundary": {

        "rows":
            len(
                agent_runtime
            ),

        "eligible_cases":
            len(
                agent_eligible
            ),

        "ground_truth_exposed":
            False,

        "patient_identifier_exposed":
            False,

        "case_type_exposed":
            False,

        "router_target_exposed":
            False,

        "human_review_required":
            True,
    },

    "ranking_boundary": {

        "minimum_selected_router_probability":
            minimum_selected_probability,

        "maximum_bypassed_router_probability":
            maximum_bypassed_probability,
    },

    "source_hashes":
        source_hashes,

    "output_hashes": {

        str(
            RUNTIME_OUTPUT
        ):
            sha256(
                RUNTIME_OUTPUT
            ),

        str(
            ELIGIBLE_OUTPUT
        ):
            sha256(
                ELIGIBLE_OUTPUT
            ),
    },

    "phase12_modified":
        False,

    "phase13_1_modified":
        False,

    "next_phase":
        "13.3 — Executable agent runtime"
}


with open(
    RUNTIME_MANIFEST,
    "w"
) as f:

    json.dump(
        manifest,
        f,
        indent=2
    )


print(
    "Saved:",
    RUNTIME_MANIFEST
)


# =============================================================================
# S — CREATE RUNTIME REPLAY AUDIT
# =============================================================================

section("S — CREATE RUNTIME REPLAY AUDIT")


checks = {

    "phase12_frozen":
        phase12.get(
            "status"
        )
        ==
        "PHASE_12_FINAL_COMPARISON_FROZEN",

    "phase13_1_frozen":
        architecture.get(
            "status"
        )
        ==
        "FINAL_INTEGRATED_AGENT_ARCHITECTURE_FROZEN",

    "routing_population_lock":
        len(df)
        ==
        EXPECTED_ROUTING_POPULATION,

    "unique_encounter_lock":
        df[
            "encounter_id"
        ].nunique()
        ==
        EXPECTED_ROUTING_POPULATION,

    "primary_negative_only":
        predicted_values
        ==
        [0],

    "primary_threshold_lock":
        np.allclose(
            df[
                "threshold"
            ].astype(float),
            PRIMARY_THRESHOLD
        ),

    "router_feature_contract":
        contract_features
        ==
        ROUTER_FEATURES,

    "router_probability_replay":
        max_probability_difference
        <=
        1e-12,

    "review_budget_lock":
        runtime_selected_count
        ==
        EXPECTED_SELECTED_CASES,

    "selection_replay":
        selection_mismatches
        ==
        0,

    "primary_fn_lock":
        primary_false_negatives
        ==
        EXPECTED_PRIMARY_FALSE_NEGATIVES,

    "system_D_fn_lock":
        escalated_false_negatives
        ==
        EXPECTED_ESCALATED_FALSE_NEGATIVES,

    "ground_truth_not_exposed":
        "actual_30d"
        not in agent_runtime.columns,

    "patient_identifier_not_exposed":
        "patient_nbr"
        not in agent_runtime.columns,

    "case_type_not_exposed":
        "case_type"
        not in agent_runtime.columns,

    "router_target_not_exposed":
        "router_target"
        not in agent_runtime.columns,

    "agent_eligible_population_lock":
        len(
            agent_eligible
        )
        ==
        EXPECTED_SELECTED_CASES,

    "router_not_retrained":
        True,

    "router_not_retuned":
        True,

    "primary_model_not_retrained":
        True,

    "primary_model_not_retuned":
        True,

    "phase12_unchanged":
        True,

    "phase13_1_unchanged":
        True,

    "runtime_output_exists":
        RUNTIME_OUTPUT.exists(),

    "eligible_output_exists":
        ELIGIBLE_OUTPUT.exists(),

    "manifest_exists":
        RUNTIME_MANIFEST.exists(),
}


for name, passed in checks.items():

    print(
        name + ":",
        "PASSED"
        if passed
        else "FAILED"
    )


failed = [
    name
    for name, passed
    in checks.items()
    if not passed
]


if failed:

    raise RuntimeError(
        "Phase 13.2 runtime verification failed: "
        f"{failed}"
    )


audit = {

    "phase":
        "13.2",

    "status":
        "PASSED",

    "checks":
        {
            key:
                bool(value)
            for key, value
            in checks.items()
        },

    "router_probability_replay": {

        "maximum_difference":
            max_probability_difference,

        "mean_difference":
            mean_probability_difference,
    },

    "selection_replay": {

        "expected_selected":
            EXPECTED_SELECTED_CASES,

        "runtime_selected":
            runtime_selected_count,

        "mismatches":
            selection_mismatches,
    },

    "scientific_replay": {

        "primary_false_negatives":
            primary_false_negatives,

        "escalated_false_negatives":
            escalated_false_negatives,

        "fn_coverage":
            fn_coverage,
    },

    "runtime_manifest_sha256":
        sha256(
            RUNTIME_MANIFEST
        ),
}


with open(
    RUNTIME_AUDIT,
    "w"
) as f:

    json.dump(
        audit,
        f,
        indent=2
    )


print()
print(
    "Saved:",
    RUNTIME_AUDIT
)


# =============================================================================
# FINAL
# =============================================================================

print()
print("=" * 80)

print(
    "PHASE 13.2 COMPLETE — "
    "FROZEN MODEL AND ROUTING RUNTIME VERIFIED"
)

print("=" * 80)


print()
print("RUNTIME MODE")
print(
    " Frozen primary-output replay "
    "+ frozen learned-router inference"
)


print()
print("PRIMARY MODEL")

print(
    " Threshold:",
    PRIMARY_THRESHOLD
)

print(
    " Fresh raw-patient inference claimed: NO"
)

print(
    " Retrained: NO"
)

print(
    " Retuned: NO"
)


print()
print("LEARNED ROUTER")

print(
    " Population:",
    EXPECTED_ROUTING_POPULATION
)

print(
    " Review budget:",
    f"{REVIEW_BUDGET:.0%}"
)

print(
    " Selected cases:",
    runtime_selected_count
)

print(
    " Probability replay max difference:",
    max_probability_difference
)

print(
    " Selection mismatches:",
    selection_mismatches
)


print()
print("FROZEN SCIENTIFIC REPLAY")

print(
    " Primary false negatives:",
    primary_false_negatives
)

print(
    " FNs escalated:",
    escalated_false_negatives
)

print(
    " FN coverage:",
    f"{fn_coverage:.2%}"
)


print()
print("AGENT RUNTIME")

print(
    " Safe runtime cases:",
    len(
        agent_runtime
    )
)

print(
    " Agent-eligible cases:",
    len(
        agent_eligible
    )
)

print(
    " Ground truth exposed: NO"
)

print(
    " Patient identifier exposed: NO"
)

print(
    " Retrospective case type exposed: NO"
)

print(
    " Router training target exposed: NO"
)


print()
print("SCIENTIFIC BOUNDARY")

print(
    " Ground truth used for routing: NO"
)

print(
    " Ground truth used only for replay verification: YES"
)

print(
    " Router retrained: NO"
)

print(
    " Router retuned: NO"
)

print(
    " Review budget changed: NO"
)


print()
print(
    "Runtime output:",
    RUNTIME_OUTPUT
)

print(
    "Agent-eligible output:",
    ELIGIBLE_OUTPUT
)

print(
    "Runtime manifest:",
    RUNTIME_MANIFEST
)

print(
    "Replay audit:",
    RUNTIME_AUDIT
)


print()
print("=" * 80)

print(
    "NEXT: PHASE 13.3 — "
    "EXECUTABLE AGENT RUNTIME"
)

print("=" * 80)
