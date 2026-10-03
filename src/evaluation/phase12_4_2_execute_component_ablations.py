from pathlib import Path
import json
import hashlib
import joblib
import numpy as np
import pandas as pd


print("=" * 80)
print("PHASE 12.4.2 — EXECUTE FROZEN COMPONENT ABLATIONS")
print("=" * 80)


# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------

ROUTER_PATH = Path(
    "src/models/saved/eligible/router/fn_rescue_router.joblib"
)

PREDICTIONS_PATH = Path(
    "results/eligible/final_test_router_predictions.csv"
)

PROTOCOL_PATH = Path(
    "results/eligible/final_comparison/"
    "phase12_4_1_ablation_protocol.json"
)

OUT_DIR = Path("results/eligible/final_comparison")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ASSIGNMENTS_PATH = (
    OUT_DIR / "phase12_4_2_ablation_assignments.csv"
)

RESULTS_PATH = (
    OUT_DIR / "phase12_4_2_ablation_results.csv"
)

AUDIT_PATH = (
    OUT_DIR / "phase12_4_2_ablation_execution_audit.json"
)


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


def select_top_budget(df, score_column, budget):
    """
    Deterministic ranking:
      1. Higher score first
      2. Lower encounter_id first for exact score ties
    """

    ranked = df[
        ["encounter_id", score_column]
    ].copy()

    ranked = ranked.sort_values(
        by=[score_column, "encounter_id"],
        ascending=[False, True],
        kind="mergesort",
    )

    selected_ids = set(
        ranked.head(budget)["encounter_id"].tolist()
    )

    return df["encounter_id"].isin(selected_ids).astype(int)


# ---------------------------------------------------------------------
# A — LOAD FROZEN PROTOCOL
# ---------------------------------------------------------------------

section("A — LOAD FROZEN ABLATION PROTOCOL")

if not PROTOCOL_PATH.exists():
    raise FileNotFoundError(PROTOCOL_PATH)

with open(PROTOCOL_PATH) as f:
    protocol = json.load(f)

if protocol.get("status") != "ABLATION_PROTOCOL_FROZEN":
    raise RuntimeError(
        "Phase 12.4.1 protocol is not frozen."
    )

features = protocol["router_features"]
ablations = protocol["ablations"]

budget = int(
    protocol["evaluation_rules"]["review_budget_cases"]
)

print("Protocol status:", protocol["status"])
print("Features:", features)
print("Review budget:", budget)
print("Variants:", list(ablations.keys()))

print("Frozen protocol load: PASSED")


# ---------------------------------------------------------------------
# B — VERIFY SOURCE INTEGRITY
# ---------------------------------------------------------------------

section("B — VERIFY FROZEN SOURCE INTEGRITY")

current_router_hash = sha256(ROUTER_PATH)
current_prediction_hash = sha256(PREDICTIONS_PATH)

expected_router_hash = protocol["source_hashes"][
    str(ROUTER_PATH)
]

expected_prediction_hash = protocol["source_hashes"][
    str(PREDICTIONS_PATH)
]

print("Router hash match:",
      current_router_hash == expected_router_hash)

print("Prediction hash match:",
      current_prediction_hash == expected_prediction_hash)

if current_router_hash != expected_router_hash:
    raise RuntimeError(
        "Frozen router changed after Phase 12.4.1."
    )

if current_prediction_hash != expected_prediction_hash:
    raise RuntimeError(
        "Frozen prediction file changed after Phase 12.4.1."
    )

print("Source integrity: PASSED")


# ---------------------------------------------------------------------
# C — LOAD DATA AND ROUTER
# ---------------------------------------------------------------------

section("C — LOAD ROUTING POPULATION AND MODEL")

df = pd.read_csv(PREDICTIONS_PATH)
router = joblib.load(ROUTER_PATH)

if len(df) != 7858:
    raise RuntimeError(
        f"Expected 7,858 cases, found {len(df)}"
    )

if df["encounter_id"].nunique() != len(df):
    raise RuntimeError(
        "Encounter IDs are not unique."
    )

X = df[features].copy()

print("Cases:", len(df))
print("Primary false negatives:",
      int(df["actual_30d"].sum()))

print("Original selected:",
      int(df["selected_for_review"].sum()))

print("Population load: PASSED")


# ---------------------------------------------------------------------
# D — VERIFY FULL ROUTER REPLAY AND SELECTION
# ---------------------------------------------------------------------

section("D — VERIFY FULL ROUTER REPLAY")

full_probability = router.predict_proba(X)[:, 1]

probability_difference = float(
    np.max(
        np.abs(
            full_probability -
            df["fn_router_probability"].to_numpy()
        )
    )
)

print(
    "Maximum replay probability difference:",
    probability_difference
)

if probability_difference > 1e-10:
    raise RuntimeError(
        "Full router probability replay failed."
    )

work = pd.DataFrame({
    "encounter_id": df["encounter_id"],
    "actual_30d": df["actual_30d"],
    "FULL_score": full_probability,
})

work["FULL_selected"] = select_top_budget(
    work,
    "FULL_score",
    budget,
)

stored_selected = (
    df["selected_for_review"]
    .astype(int)
    .to_numpy()
)

replayed_selected = (
    work["FULL_selected"]
    .astype(int)
    .to_numpy()
)

selection_mismatch = int(
    np.sum(
        stored_selected != replayed_selected
    )
)

print("Selection mismatches:", selection_mismatch)

if selection_mismatch != 0:
    raise RuntimeError(
        "Full-router top-budget replay does not reproduce "
        "stored routing assignments."
    )

print("Full router replay and ranking: PASSED")


# ---------------------------------------------------------------------
# E — DEFINE FROZEN NEUTRALIZATION VALUES
# ---------------------------------------------------------------------

section("E — DEFINE FEATURE NEUTRALIZATION VALUES")

neutral_values = {}

for feature in features:
    value = float(X[feature].mean())
    neutral_values[feature] = value

    print(
        f"{feature}: mean = {value:.12f}"
    )

print()
print(
    "Neutralization rule: replace the ablated feature "
    "with its frozen routing-population mean."
)

print("Neutralization values: FROZEN FOR THIS EXECUTION")


# ---------------------------------------------------------------------
# F — EXECUTE LEAVE-ONE-FEATURE-OUT ABLATIONS
# ---------------------------------------------------------------------

section("F — EXECUTE FROZEN COMPONENT ABLATIONS")

for variant, specification in ablations.items():

    removed_feature = specification["removed_feature"]

    if variant == "FULL":
        print("FULL: using frozen original router.")
        continue

    if removed_feature not in features:
        raise RuntimeError(
            f"Unknown ablation feature: {removed_feature}"
        )

    X_ablation = X.copy()

    X_ablation[removed_feature] = (
        neutral_values[removed_feature]
    )

    scores = router.predict_proba(
        X_ablation
    )[:, 1]

    score_column = f"{variant}_score"
    selected_column = f"{variant}_selected"

    work[score_column] = scores

    work[selected_column] = select_top_budget(
        work,
        score_column,
        budget,
    )

    selected_n = int(
        work[selected_column].sum()
    )

    print()
    print(variant)
    print(" Removed:", removed_feature)
    print(
        " Neutral value:",
        neutral_values[removed_feature]
    )
    print(" Selected:", selected_n)

    if selected_n != budget:
        raise RuntimeError(
            f"{variant} violates frozen review budget."
        )

print()
print("All ablations executed: PASSED")


# ---------------------------------------------------------------------
# G — CALCULATE ABLATION PERFORMANCE
# ---------------------------------------------------------------------

section("G — CALCULATE ABLATION PERFORMANCE")

total_fn = int(work["actual_30d"].sum())

full_selected_mask = (
    work["FULL_selected"] == 1
)

full_fn_escalated = int(
    (
        full_selected_mask &
        (work["actual_30d"] == 1)
    ).sum()
)

full_coverage = (
    full_fn_escalated / total_fn
)

print("Total primary-model FNs:", total_fn)
print("Full-router FNs escalated:", full_fn_escalated)
print("Full-router FN coverage:", f"{full_coverage:.6f}")

if total_fn != 557:
    raise RuntimeError(
        f"Expected 557 primary false negatives, found {total_fn}."
    )

if full_fn_escalated != 110:
    raise RuntimeError(
        "Expected frozen full router to escalate 110 FNs."
    )


results = []

for variant, specification in ablations.items():

    selected_column = f"{variant}_selected"

    selected_mask = (
        work[selected_column] == 1
    )

    selected_n = int(
        selected_mask.sum()
    )

    fn_escalated = int(
        (
            selected_mask &
            (work["actual_30d"] == 1)
        ).sum()
    )

    coverage = (
        fn_escalated / total_fn
    )

    precision = (
        fn_escalated / selected_n
        if selected_n > 0
        else np.nan
    )

    overlap = int(
        (
            selected_mask &
            full_selected_mask
        ).sum()
    )

    union = int(
        (
            selected_mask |
            full_selected_mask
        ).sum()
    )

    jaccard = (
        overlap / union
        if union > 0
        else np.nan
    )

    fn_loss = (
        full_fn_escalated -
        fn_escalated
    )

    coverage_loss = (
        full_coverage -
        coverage
    )

    results.append({
        "variant": variant,
        "removed_feature":
            specification["removed_feature"],

        "review_population":
            selected_n,

        "false_negatives_escalated":
            fn_escalated,

        "false_negative_review_coverage":
            coverage,

        "review_precision_for_false_negative":
            precision,

        "overlap_with_full_router":
            overlap,

        "jaccard_with_full_router":
            jaccard,

        "false_negative_loss_vs_full":
            fn_loss,

        "coverage_loss_vs_full":
            coverage_loss,
    })


results_df = pd.DataFrame(results)

print()
print(results_df.to_string(index=False))


# ---------------------------------------------------------------------
# H — VERIFY MATCHED BUDGET
# ---------------------------------------------------------------------

section("H — VERIFY MATCHED REVIEW BUDGET")

for _, row in results_df.iterrows():

    variant = row["variant"]
    n = int(row["review_population"])

    print(
        variant,
        "->",
        n
    )

    if n != budget:
        raise RuntimeError(
            f"{variant} review budget mismatch."
        )

print("Matched-budget verification: PASSED")


# ---------------------------------------------------------------------
# I — SCIENTIFIC BOUNDARY
# ---------------------------------------------------------------------

section("I — SCIENTIFIC INTERPRETATION BOUNDARY")

boundaries = [
    (
        "No ablated router was fitted or tuned using "
        "final-test outcomes."
    ),
    (
        "Feature masking uses a predeclared neutralization "
        "operation on the frozen fitted pipeline."
    ),
    (
        "All variants receive exactly the same 1,178-case "
        "review budget."
    ),
    (
        "actual_30d is used only after routing assignments "
        "are frozen for evaluation."
    ),
    (
        "A reduction in FN escalation after masking a feature "
        "supports routing contribution under this frozen-model "
        "ablation; it does not establish causal clinical effect."
    ),
    (
        "If masking improves FN escalation, the result is "
        "reported rather than used to retune the router."
    ),
    (
        "Phase 11 perturbation robustness results remain "
        "scientifically distinct from this component ablation."
    ),
]

for boundary in boundaries:
    print(" -", boundary)


# ---------------------------------------------------------------------
# J — SAVE CASE-LEVEL ASSIGNMENTS
# ---------------------------------------------------------------------

section("J — SAVE CASE-LEVEL ABLATION ASSIGNMENTS")

work.to_csv(
    ASSIGNMENTS_PATH,
    index=False
)

print(
    "Assignments saved:",
    ASSIGNMENTS_PATH
)


# ---------------------------------------------------------------------
# K — SAVE SUMMARY RESULTS
# ---------------------------------------------------------------------

section("K — SAVE ABLATION RESULT TABLE")

results_df.to_csv(
    RESULTS_PATH,
    index=False
)

print(
    "Results saved:",
    RESULTS_PATH
)


# ---------------------------------------------------------------------
# L — CREATE EXECUTION AUDIT
# ---------------------------------------------------------------------

section("L — CREATE EXECUTION AUDIT")

audit = {
    "phase": "12.4.2",

    "status":
        "FROZEN_COMPONENT_ABLATIONS_EXECUTED",

    "population": {
        "cases": int(len(work)),
        "primary_false_negatives": total_fn,
    },

    "review_budget": {
        "cases": budget,
        "rate": budget / len(work),
    },

    "neutralization_method":
        "replace removed feature with frozen "
        "routing-population mean",

    "neutral_values":
        neutral_values,

    "full_router": {
        "false_negatives_escalated":
            full_fn_escalated,

        "false_negative_review_coverage":
            full_coverage,
    },

    "variants":
        results_df.to_dict(
            orient="records"
        ),

    "integrity": {
        "router_hash":
            current_router_hash,

        "prediction_hash":
            current_prediction_hash,

        "router_retrained":
            False,

        "router_retuned":
            False,

        "primary_model_modified":
            False,

        "phase10_modified":
            False,

        "phase11_modified":
            False,

        "ground_truth_used_for_routing":
            False,

        "ground_truth_used_for_evaluation":
            True,
    },

    "next_phase":
        "12.4.3 — Ablation contribution analysis",
}

with open(AUDIT_PATH, "w") as f:
    json.dump(
        audit,
        f,
        indent=2
    )

print(
    "Audit saved:",
    AUDIT_PATH
)


# ---------------------------------------------------------------------
# M — FINAL VERIFICATION
# ---------------------------------------------------------------------

section("M — FINAL VERIFICATION")

checks = {
    "protocol_frozen":
        protocol["status"] ==
        "ABLATION_PROTOCOL_FROZEN",

    "router_hash_unchanged":
        current_router_hash ==
        expected_router_hash,

    "prediction_hash_unchanged":
        current_prediction_hash ==
        expected_prediction_hash,

    "router_replay":
        probability_difference <= 1e-10,

    "full_selection_replay":
        selection_mismatch == 0,

    "population_lock":
        len(work) == 7858,

    "primary_fn_lock":
        total_fn == 557,

    "full_router_fn_lock":
        full_fn_escalated == 110,

    "all_budgets_matched":
        bool(
            (
                results_df["review_population"]
                == budget
            ).all()
        ),

    "assignments_exist":
        ASSIGNMENTS_PATH.exists(),

    "results_exist":
        RESULTS_PATH.exists(),

    "audit_exists":
        AUDIT_PATH.exists(),
}

for name, passed in checks.items():

    print(
        f"{name}:",
        "PASSED" if passed else "FAILED"
    )

if not all(checks.values()):
    raise RuntimeError(
        "Phase 12.4.2 verification failed."
    )


print()
print("=" * 80)
print(
    "PHASE 12.4.2 COMPLETE — "
    "FROZEN COMPONENT ABLATIONS EXECUTED"
)
print("=" * 80)

print()
print(
    results_df[
        [
            "variant",
            "false_negatives_escalated",
            "false_negative_review_coverage",
            "false_negative_loss_vs_full",
            "coverage_loss_vs_full",
        ]
    ].to_string(index=False)
)

print()
print("Router retrained: NO")
print("Router retuned: NO")
print("Review budget changed: NO")
print("Ground truth used for routing: NO")
print()
print(
    "NEXT: PHASE 12.4.3 — "
    "ABLATION CONTRIBUTION ANALYSIS"
)
