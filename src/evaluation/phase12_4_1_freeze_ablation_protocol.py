from pathlib import Path
import json
import hashlib
import joblib
import pandas as pd


print("=" * 80)
print("PHASE 12.4.1 — FREEZE ABLATION STUDY PROTOCOL")
print("=" * 80)


# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------

ROOT = Path(".")

OUT_DIR = Path("results/eligible/final_comparison")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ROUTER_PATH = Path(
    "src/models/saved/eligible/router/fn_rescue_router.joblib"
)

PREDICTIONS_PATH = Path(
    "results/eligible/final_test_router_predictions.csv"
)

COMPARATOR_PATH = Path(
    "results/eligible/final_comparison/"
    "phase12_2_system_comparator_assignments.csv"
)

PHASE12_3_PATH = Path(
    "results/eligible/final_comparison/"
    "phase12_3_final_system_comparison.csv"
)

PHASE11_INPUT_PATH = Path(
    "results/eligible/robustness/"
    "phase11_3_1_router_input_inspection.json"
)

COEFFICIENT_PATH = Path(
    "results/eligible/fn_rescue_router_coefficients.csv"
)

OUTPUT_PATH = OUT_DIR / "phase12_4_1_ablation_protocol.json"


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------

def section(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)

    return h.hexdigest()


# ---------------------------------------------------------------------
# A — VERIFY REQUIRED INPUTS
# ---------------------------------------------------------------------

section("A — VERIFY REQUIRED FROZEN INPUTS")

required = [
    ROUTER_PATH,
    PREDICTIONS_PATH,
    COMPARATOR_PATH,
    PHASE12_3_PATH,
    PHASE11_INPUT_PATH,
    COEFFICIENT_PATH,
]

for path in required:
    if not path.exists():
        raise FileNotFoundError(path)

    print("FOUND:", path)

print("Required input presence: PASSED")


# ---------------------------------------------------------------------
# B — LOAD FROZEN ROUTER
# ---------------------------------------------------------------------

section("B — LOAD FROZEN LEARNED ROUTER")

router = joblib.load(ROUTER_PATH)

print("Router class:", router.__class__.__name__)

if not hasattr(router, "feature_names_in_"):
    raise RuntimeError(
        "Frozen router does not expose feature_names_in_."
    )

features = list(router.feature_names_in_)

expected_features = [
    "calibrated_probability",
    "model_disagreement_std",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
]

print("Router features:")

for feature in features:
    print(" -", feature)

if features != expected_features:
    raise RuntimeError(
        f"Unexpected router feature order: {features}"
    )

print("Frozen router feature contract: PASSED")


# ---------------------------------------------------------------------
# C — VERIFY FINAL TEST ROUTING POPULATION
# ---------------------------------------------------------------------

section("C — VERIFY FINAL TEST ROUTING POPULATION")

df = pd.read_csv(PREDICTIONS_PATH)

required_columns = [
    "encounter_id",
    "actual_30d",
    "predicted_30d",
    "fn_router_probability",
    "selected_for_review",
] + expected_features

missing = [c for c in required_columns if c not in df.columns]

if missing:
    raise RuntimeError(
        f"Missing required columns: {missing}"
    )

print("Rows:", len(df))
print("Unique encounters:", df["encounter_id"].nunique())
print(
    "Selected for review:",
    int(df["selected_for_review"].sum())
)

if len(df) != 7858:
    raise RuntimeError(
        f"Expected 7,858 router cases, found {len(df)}"
    )

if df["encounter_id"].nunique() != 7858:
    raise RuntimeError(
        "Encounter IDs are not unique."
    )

if int(df["selected_for_review"].sum()) != 1178:
    raise RuntimeError(
        "Frozen review budget is not 1,178."
    )

if not (df["predicted_30d"] == 0).all():
    raise RuntimeError(
        "Router population contains primary-positive cases."
    )

print("Routing population lock: PASSED")


# ---------------------------------------------------------------------
# D — VERIFY ROUTER REPLAY
# ---------------------------------------------------------------------

section("D — VERIFY FROZEN ROUTER REPLAY")

X = df[expected_features].copy()

replayed_probability = router.predict_proba(X)[:, 1]

max_difference = float(
    abs(
        replayed_probability -
        df["fn_router_probability"].to_numpy()
    ).max()
)

print(
    "Maximum probability replay difference:",
    max_difference
)

if max_difference > 1e-10:
    raise RuntimeError(
        "Frozen router replay does not match stored probabilities."
    )

print("Frozen router replay: PASSED")


# ---------------------------------------------------------------------
# E — DEFINE ABLATION VARIANTS
# ---------------------------------------------------------------------

section("E — DEFINE PREDECLARED ABLATION VARIANTS")

ablations = {
    "FULL": {
        "removed_feature": None,
        "description":
            "Frozen learned router using all five features."
    },

    "DROP_CALIBRATED_PROBABILITY": {
        "removed_feature":
            "calibrated_probability",
        "description":
            "Remove calibrated primary-model risk signal."
    },

    "DROP_MODEL_DISAGREEMENT": {
        "removed_feature":
            "model_disagreement_std",
        "description":
            "Remove model-disagreement signal."
    },

    "DROP_NUMBER_DIAGNOSES": {
        "removed_feature":
            "number_diagnoses",
        "description":
            "Remove diagnosis-burden signal."
    },

    "DROP_NUMBER_OUTPATIENT": {
        "removed_feature":
            "number_outpatient",
        "description":
            "Remove outpatient-utilization signal."
    },

    "DROP_NUMBER_EMERGENCY": {
        "removed_feature":
            "number_emergency",
        "description":
            "Remove emergency-utilization signal."
    },
}

for name, spec in ablations.items():
    print(
        name,
        "->",
        spec["removed_feature"]
    )

print("Ablation definitions: FROZEN")


# ---------------------------------------------------------------------
# F — FREEZE EVALUATION RULES
# ---------------------------------------------------------------------

section("F — FREEZE ABLATION EVALUATION RULES")

evaluation_rules = {
    "population":
        "7,858 frozen primary-model-negative final-test encounters",

    "review_budget_cases": 1178,

    "review_budget_rate":
        1178 / 7858,

    "ranking_rule":
        "Higher ablated routing score receives review.",

    "tie_break":
        "Ascending encounter_id.",

    "primary_metric":
        "false_negative_review_coverage",

    "secondary_metrics": [
        "false_negatives_escalated",
        "review_precision_for_false_negative",
        "overlap_with_full_router",
        "jaccard_with_full_router",
        "false_negative_loss_vs_full",
        "coverage_loss_vs_full",
    ],

    "ground_truth_for_ranking": False,

    "ground_truth_for_evaluation": True,

    "test_set_retraining": False,

    "test_set_retuning": False,

    "review_budget_changed": False,

    "primary_model_changed": False,

    "phase10_changed": False,

    "phase11_changed": False,
}

for key, value in evaluation_rules.items():
    print(f"{key}: {value}")

print("Evaluation rules: FROZEN")


# ---------------------------------------------------------------------
# G — DEFINE ABLATION METHOD BOUNDARY
# ---------------------------------------------------------------------

section("G — DEFINE ABLATION METHOD BOUNDARY")

method = {
    "type":
        "frozen-model component masking",

    "principle":
        (
            "The fitted router is not retrained on final-test outcomes. "
            "For each leave-one-feature-out analysis, the contribution "
            "of the predeclared feature is neutralized while all other "
            "frozen model parameters remain unchanged."
        ),

    "prohibited": [
        "Refitting router coefficients on final-test labels",
        "Choosing ablations based on final-test performance",
        "Changing the 1,178-case review budget",
        "Changing the primary classifier",
        "Changing the primary threshold",
        "Using actual_30d during routing",
        "Using case_type during routing",
        "Using router_target during routing",
        "Modifying Phase 10 artifacts",
        "Modifying Phase 11 artifacts",
    ],
}

print("Method:", method["type"])

for item in method["prohibited"]:
    print("PROHIBITED:", item)

print("Ablation methodological boundary: FROZEN")


# ---------------------------------------------------------------------
# H — CAPTURE SOURCE HASHES
# ---------------------------------------------------------------------

section("H — CAPTURE SOURCE HASHES")

source_hashes = {}

for path in required:
    digest = sha256(path)
    source_hashes[str(path)] = digest

    print(
        path.name,
        "->",
        digest
    )

print("Source hashes captured: PASSED")


# ---------------------------------------------------------------------
# I — CREATE PROTOCOL
# ---------------------------------------------------------------------

section("I — CREATE ABLATION PROTOCOL")

protocol = {
    "phase": "12.4.1",

    "status": "ABLATION_PROTOCOL_FROZEN",

    "purpose":
        (
            "Quantify the contribution of each frozen learned-router "
            "input signal to false-negative escalation under the same "
            "matched review budget."
        ),

    "router_features": expected_features,

    "ablations": ablations,

    "evaluation_rules": evaluation_rules,

    "method": method,

    "source_hashes": source_hashes,

    "scientific_boundary": [
        (
            "Ablation results describe routing allocation, "
            "not corrected clinical outcomes."
        ),
        (
            "Escalated false negatives remain false negatives "
            "in predictive-performance accounting."
        ),
        (
            "No final-test labels may be used to fit or tune "
            "an ablation."
        ),
        (
            "Phase 11 perturbation analysis remains distinct: "
            "Phase 11 measured sensitivity to input perturbations; "
            "Phase 12.4 measures contribution of frozen router "
            "components."
        ),
    ],

    "next_phase":
        "12.4.2 — Execute frozen component ablations",
}

with open(OUTPUT_PATH, "w") as f:
    json.dump(
        protocol,
        f,
        indent=2
    )

print("Protocol saved:", OUTPUT_PATH)


# ---------------------------------------------------------------------
# J — FINAL VERIFICATION
# ---------------------------------------------------------------------

section("J — FINAL VERIFICATION")

checks = {
    "router_replay_verified":
        max_difference <= 1e-10,

    "five_feature_contract":
        features == expected_features,

    "population_lock":
        len(df) == 7858,

    "review_budget_lock":
        int(df["selected_for_review"].sum()) == 1178,

    "leave_one_feature_out_predeclared":
        len(ablations) == 6,

    "test_retraining_prohibited":
        evaluation_rules["test_set_retraining"] is False,

    "test_retuning_prohibited":
        evaluation_rules["test_set_retuning"] is False,

    "ground_truth_routing_prohibited":
        evaluation_rules["ground_truth_for_ranking"] is False,

    "protocol_exists":
        OUTPUT_PATH.exists(),
}

for name, passed in checks.items():
    print(
        f"{name}:",
        "PASSED" if passed else "FAILED"
    )

if not all(checks.values()):
    raise RuntimeError(
        "Phase 12.4.1 verification failed."
    )


print()
print("=" * 80)
print(
    "PHASE 12.4.1 COMPLETE — "
    "ABLATION PROTOCOL FROZEN"
)
print("=" * 80)

print()
print("Frozen router features:", len(expected_features))
print("Frozen review budget: 1178 / 7858")
print("Ablation variants:", len(ablations))
print("Final-test retraining allowed: NO")
print("Final-test retuning allowed: NO")
print("Ground truth allowed for routing: NO")
print()
print(
    "NEXT: PHASE 12.4.2 — "
    "EXECUTE FROZEN COMPONENT ABLATIONS"
)
