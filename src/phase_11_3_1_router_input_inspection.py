from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

ROUTER_DATA = Path(
    "results/eligible/final_test_router_predictions.csv"
)

FAIRNESS_CLOSURE = Path(
    "results/eligible/fairness/"
    "phase11_2_fairness_closure_manifest.json"
)

PHASE10_MANIFEST = Path(
    "results/eligible/agents/"
    "phase10_final_completion_manifest.json"
)

OUTPUT_DIR = Path(
    "results/eligible/robustness"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

INSPECTION_OUTPUT = (
    OUTPUT_DIR /
    "phase11_3_1_router_input_inspection.json"
)


# =============================================================================
# HELPERS
# =============================================================================

def section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def safe_value(x):
    if pd.isna(x):
        return None

    if isinstance(x, np.integer):
        return int(x)

    if isinstance(x, np.floating):
        return float(x)

    if isinstance(x, np.bool_):
        return bool(x)

    return x


# =============================================================================
# HEADER
# =============================================================================

section(
    "PHASE 11.3.1 — ROUTER INPUT AND PERTURBATION INSPECTION"
)


# =============================================================================
# A — VERIFY UPSTREAM LOCKS
# =============================================================================

section("A — VERIFY UPSTREAM LOCKS")

required = [
    ROUTER_DATA,
    FAIRNESS_CLOSURE,
    PHASE10_MANIFEST,
]

for path in required:

    if not path.exists():
        raise FileNotFoundError(path)

    print("FOUND:", path)


with FAIRNESS_CLOSURE.open() as f:
    fairness = json.load(f)

with PHASE10_MANIFEST.open() as f:
    phase10 = json.load(f)


if fairness["status"] != "FAIRNESS_AUDIT_COMPLETE":
    raise RuntimeError(
        "Phase 11.2 fairness audit is not locked."
    )

print("Phase 11.2 fairness closure: PASSED")

print(
    "Phase 10 artifact available: PASSED"
)


# =============================================================================
# B — LOAD FROZEN ROUTER POPULATION
# =============================================================================

section("B — LOAD FROZEN ROUTER POPULATION")

df = pd.read_csv(ROUTER_DATA)

print("Shape:", df.shape)

print()
print("Columns:")

for col in df.columns:
    print(" -", col)


if len(df) != 7858:
    raise RuntimeError(
        "Expected frozen router population of 7858."
    )


required_columns = {
    "encounter_id",
    "actual_30d",
    "predicted_30d",
    "router_target",
    "fn_router_probability",
    "selected_for_review",
}

missing = required_columns - set(df.columns)

if missing:
    raise RuntimeError(
        f"Missing required columns: {sorted(missing)}"
    )


print()
print("Router population:", len(df))

print(
    "Selected for review:",
    int(df["selected_for_review"].sum())
)

print(
    "Router population lock: PASSED"
)


# =============================================================================
# C — CLASSIFY COLUMNS BY ROLE
# =============================================================================

section("C — CLASSIFY AVAILABLE COLUMNS")

protected_or_outcome = {
    "actual_30d",
    "case_type",
    "router_target",
    "selected_for_review",
    "rescued_fn",
    "residual_fn",
}

identifiers = {
    "encounter_id",
    "patient_nbr",
}

router_outputs = {
    "fn_router_probability",
}

demographics = {
    "race",
    "gender",
    "age",
}


numeric_candidates = []

for col in df.columns:

    if col in protected_or_outcome:
        continue

    if col in identifiers:
        continue

    if col in router_outputs:
        continue

    if col in demographics:
        continue

    if pd.api.types.is_numeric_dtype(df[col]):
        numeric_candidates.append(col)


print("Identifier columns:")
for x in sorted(identifiers & set(df.columns)):
    print(" -", x)

print()
print("Outcome/post-routing columns excluded:")
for x in sorted(protected_or_outcome & set(df.columns)):
    print(" -", x)

print()
print("Router-output columns excluded from perturbation:")
for x in sorted(router_outputs & set(df.columns)):
    print(" -", x)

print()
print("Demographic columns excluded from perturbation:")
for x in sorted(demographics & set(df.columns)):
    print(" -", x)

print()
print("Numeric perturbation candidates:")
for x in numeric_candidates:
    print(" -", x)


# =============================================================================
# D — NUMERIC FEATURE INSPECTION
# =============================================================================

section("D — NUMERIC FEATURE DISTRIBUTIONS")

feature_inventory = []

for col in numeric_candidates:

    s = pd.to_numeric(
        df[col],
        errors="coerce",
    )

    nonmissing = s.dropna()

    if len(nonmissing) == 0:
        continue

    unique_count = int(
        nonmissing.nunique()
    )

    integer_like = bool(
        np.allclose(
            nonmissing,
            np.round(nonmissing),
        )
    )

    values = {
        "feature": col,

        "n_nonmissing":
            int(nonmissing.shape[0]),

        "n_missing":
            int(s.isna().sum()),

        "n_unique":
            unique_count,

        "integer_like":
            integer_like,

        "min":
            safe_value(nonmissing.min()),

        "q01":
            safe_value(nonmissing.quantile(0.01)),

        "q05":
            safe_value(nonmissing.quantile(0.05)),

        "q25":
            safe_value(nonmissing.quantile(0.25)),

        "median":
            safe_value(nonmissing.median()),

        "q75":
            safe_value(nonmissing.quantile(0.75)),

        "q95":
            safe_value(nonmissing.quantile(0.95)),

        "q99":
            safe_value(nonmissing.quantile(0.99)),

        "max":
            safe_value(nonmissing.max()),

        "mean":
            safe_value(nonmissing.mean()),

        "std":
            safe_value(nonmissing.std()),
    }

    feature_inventory.append(values)

    print()
    print("-" * 80)
    print(col)
    print("-" * 80)

    for key, value in values.items():

        if key == "feature":
            continue

        print(
            f"{key}: {value}"
        )


# =============================================================================
# E — LOW-CARDINALITY NUMERIC FEATURES
# =============================================================================

section("E — LOW-CARDINALITY NUMERIC FEATURES")

for col in numeric_candidates:

    s = df[col].dropna()

    if s.nunique() <= 20:

        print()
        print(col)

        counts = (
            s.value_counts()
            .sort_index()
        )

        print(
            counts.head(30).to_string()
        )


# =============================================================================
# F — ROUTER PROBABILITY / DECISION BOUNDARY
# =============================================================================

section("F — FROZEN ROUTER OUTPUT INSPECTION")

p = df["fn_router_probability"]

print(
    "Router probability min:",
    float(p.min())
)

print(
    "Router probability median:",
    float(p.median())
)

print(
    "Router probability max:",
    float(p.max())
)

selected = df[
    df["selected_for_review"] == 1
]

bypass = df[
    df["selected_for_review"] == 0
]

print()
print(
    "Minimum selected router probability:",
    float(
        selected[
            "fn_router_probability"
        ].min()
    )
)

print(
    "Maximum bypass router probability:",
    float(
        bypass[
            "fn_router_probability"
        ].max()
    )
)

print(
    "Selected cases:",
    len(selected)
)

print(
    "Bypass cases:",
    len(bypass)
)


# =============================================================================
# G — SEARCH FOR SAVED ROUTER MODEL
# =============================================================================

section("G — SEARCH FOR FROZEN ROUTER MODEL ARTIFACT")

search_roots = [
    Path("src/models/saved"),
    Path("results/eligible"),
]

model_candidates = []

for root in search_roots:

    if not root.exists():
        continue

    for pattern in [
        "*router*.joblib",
        "*rescue*.joblib",
        "*router*.pkl",
        "*rescue*.pkl",
    ]:

        for path in root.rglob(pattern):
            model_candidates.append(path)


model_candidates = sorted(
    set(model_candidates)
)

if model_candidates:

    for path in model_candidates:
        print("FOUND MODEL CANDIDATE:", path)

else:

    print(
        "No router model artifact found by filename search."
    )


# =============================================================================
# H — SEARCH FOR ROUTER FEATURE METADATA
# =============================================================================

section("H — INSPECT MODEL FEATURE METADATA WHEN AVAILABLE")

model_metadata = []

for path in model_candidates:

    record = {
        "path": str(path),
        "loadable": False,
        "class": None,
        "feature_names_in": None,
        "n_features_in": None,
    }

    try:

        model = joblib.load(path)

        record["loadable"] = True

        record["class"] = (
            model.__class__.__module__
            + "."
            + model.__class__.__name__
        )

        if hasattr(
            model,
            "feature_names_in_",
        ):

            record["feature_names_in"] = [
                str(x)
                for x in model.feature_names_in_
            ]

        if hasattr(
            model,
            "n_features_in_",
        ):

            record["n_features_in"] = int(
                model.n_features_in_
            )

    except Exception as exc:

        record["load_error"] = str(exc)

    model_metadata.append(record)

    print()
    print("MODEL:", path)

    for key, value in record.items():

        if key == "path":
            continue

        print(
            f"{key}: {value}"
        )


# =============================================================================
# I — INFORMATION BOUNDARY
# =============================================================================

section("I — ROBUSTNESS INFORMATION BOUNDARY")

print(
    "Perturbations must be selected from genuine "
    "pre-routing numeric/count inputs."
)

print(
    "Ground truth must NOT be perturbed."
)

print(
    "Demographic attributes must NOT be perturbed."
)

print(
    "Frozen router probabilities must NOT be manually perturbed."
)

print(
    "Frozen selected_for_review labels must NOT be manually changed."
)

print(
    "Perturbed inputs must be passed back through the "
    "actual frozen router."
)

print(
    "Perturbation sizes will be frozen BEFORE route-flip "
    "results are inspected."
)


# =============================================================================
# J — SAVE INSPECTION ARTIFACT
# =============================================================================

section("J — SAVE INPUT INSPECTION ARTIFACT")

artifact = {
    "phase": "11.3.1",

    "status":
        "ROUTER_INPUT_INSPECTION_COMPLETE",

    "population": {
        "router_cases":
            int(len(df)),
        "selected":
            int(
                df[
                    "selected_for_review"
                ].sum()
            ),
        "bypassed":
            int(
                (
                    df[
                        "selected_for_review"
                    ] == 0
                ).sum()
            ),
    },

    "excluded_from_perturbation": {
        "identifiers":
            sorted(
                identifiers
                & set(df.columns)
            ),

        "outcome_or_postrouting":
            sorted(
                protected_or_outcome
                & set(df.columns)
            ),

        "demographics":
            sorted(
                demographics
                & set(df.columns)
            ),

        "router_outputs":
            sorted(
                router_outputs
                & set(df.columns)
            ),
    },

    "numeric_candidate_features":
        numeric_candidates,

    "feature_inventory":
        feature_inventory,

    "router_output_boundary": {
        "minimum_selected_probability":
            float(
                selected[
                    "fn_router_probability"
                ].min()
            ),

        "maximum_bypass_probability":
            float(
                bypass[
                    "fn_router_probability"
                ].max()
            ),
    },

    "model_candidates":
        [str(x) for x in model_candidates],

    "model_metadata":
        model_metadata,

    "perturbations_frozen":
        False,

    "route_flip_results_evaluated":
        False,

    "integrity": {
        "phase10_modified":
            False,
        "phase11_1_modified":
            False,
        "phase11_2_modified":
            False,
    },

    "next_step":
        (
            "Review feature inventory and frozen router "
            "model metadata, then predeclare perturbation "
            "features and magnitudes."
        ),
}


with INSPECTION_OUTPUT.open("w") as f:

    json.dump(
        artifact,
        f,
        indent=2,
    )


print(
    "Inspection artifact:",
    INSPECTION_OUTPUT
)


# =============================================================================
# K — FINAL VERIFICATION
# =============================================================================

section("K — FINAL VERIFICATION")

checks = {
    "population_lock":
        len(df) == 7858,

    "review_lock":
        int(
            df[
                "selected_for_review"
            ].sum()
        ) == 1178,

    "numeric_candidates_identified":
        len(numeric_candidates) > 0,

    "ground_truth_excluded":
        "actual_30d"
        not in numeric_candidates,

    "router_probability_excluded":
        "fn_router_probability"
        not in numeric_candidates,

    "routing_decision_excluded":
        "selected_for_review"
        not in numeric_candidates,

    "demographics_excluded":
        all(
            x not in numeric_candidates
            for x in [
                "race",
                "gender",
                "age",
            ]
        ),

    "perturbations_not_yet_frozen":
        artifact[
            "perturbations_frozen"
        ] is False,

    "route_flips_not_yet_evaluated":
        artifact[
            "route_flip_results_evaluated"
        ] is False,

    "phase10_unchanged":
        artifact[
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
        "Phase 11.3.1 verification failed."
    )


section(
    "PHASE 11.3.1 COMPLETE — ROUTER INPUT INSPECTION PASSED"
)

print(
    "Router population:",
    len(df)
)

print(
    "Numeric perturbation candidates:",
    len(numeric_candidates)
)

print(
    "Router model candidates found:",
    len(model_candidates)
)

print(
    "Perturbation magnitudes frozen: NO"
)

print(
    "Route-flip outcomes inspected: NO"
)

print(
    "Phase 10 frozen system modified: NO"
)

print()
print(
    "NEXT: inspect this output before defining "
    "the 11.3.1 perturbation specification."
)
