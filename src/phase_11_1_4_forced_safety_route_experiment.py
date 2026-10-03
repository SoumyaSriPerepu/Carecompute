from pathlib import Path
import json
import hashlib
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

ROUTING_PATH = Path(
    "results/eligible/final_test_end_to_end_patient_predictions.csv"
)

TEST_PATH = Path(
    "results/eligible/test_predictions.csv"
)

RULE_PATH = Path(
    "results/eligible/safety/phase11_1_3_safety_override_rule.json"
)

PHASE11_1_2 = Path(
    "results/eligible/safety/"
    "phase11_1_2_routing_false_negative_safety_audit.json"
)

OUTPUT_DIR = Path("results/eligible/safety")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_PATH = (
    OUTPUT_DIR /
    "phase11_1_4_forced_safety_route_experiment.json"
)

CASE_PATH = (
    OUTPUT_DIR /
    "phase11_1_4_forced_safety_route_cases.csv"
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
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


# =============================================================================
# HEADER
# =============================================================================

section(
    "PHASE 11.1.4 — FORCED SAFETY-ROUTE EXPERIMENT"
)


# =============================================================================
# A — VERIFY INPUTS
# =============================================================================

section("A — VERIFY REQUIRED INPUTS")

for path in [
    ROUTING_PATH,
    TEST_PATH,
    RULE_PATH,
    PHASE11_1_2,
]:
    if not path.exists():
        raise FileNotFoundError(path)

    print("FOUND:", path)

print("Required input presence: PASSED")


# =============================================================================
# B — LOAD PRE-DECLARED FROZEN RULE
# =============================================================================

section("B — LOAD PRE-DECLARED SAFETY RULE")

with RULE_PATH.open() as f:
    rule = json.load(f)

if rule["status"] != "PREDECLARED_FROZEN":
    raise RuntimeError(
        "Safety rule is not PREDECLARED_FROZEN."
    )

if rule["evaluation_boundary"][
    "outcome_performance_evaluated_in_phase_11_1_3"
]:
    raise RuntimeError(
        "Rule was not outcome-blind during pre-declaration."
    )

uncertainty_threshold = float(
    rule["conditions"]["HIGH_UNCERTAINTY"]["threshold"]
)

distance_threshold = float(
    rule["conditions"]["NEAR_PRIMARY_THRESHOLD"]["threshold"]
)

print("Rule version:", rule["rule_version"])
print("Rule status:", rule["status"])

print(
    "High-uncertainty threshold:",
    uncertainty_threshold
)

print(
    "Near-threshold maximum distance:",
    distance_threshold
)

print("Outcome-blind pre-declaration: PASSED")


# =============================================================================
# C — LOAD AND ALIGN FINAL TEST DATA
# =============================================================================

# =============================================================================
# C — LOAD AND ALIGN FINAL TEST DATA
# =============================================================================

section("C — LOAD AND ALIGN FINAL TEST DATA")

routing = pd.read_csv(ROUTING_PATH)
test = pd.read_csv(TEST_PATH)

needed_routing = {
    "encounter_id",
    "actual_30d",
    "predicted_30d",
    "selected_for_review",
}

missing = needed_routing - set(routing.columns)

if missing:
    raise RuntimeError(
        f"Missing routing columns: {sorted(missing)}"
    )

needed_test = {
    "encounter_id",
    "calibrated_probability",
    "uncertainty",
    "threshold",
}

missing = needed_test - set(test.columns)

if missing:
    raise RuntimeError(
        f"Missing test columns: {sorted(missing)}"
    )

# -------------------------------------------------------------------------
# IMPORTANT:
# Keep only routing fields required for the experiment before merging.
# This prevents duplicate probability/threshold fields from being renamed
# to *_x and *_y by pandas.
# -------------------------------------------------------------------------

routing_core = routing[
    [
        "encounter_id",
        "actual_30d",
        "predicted_30d",
        "selected_for_review",
    ]
].copy()

test_core = test[
    [
        "encounter_id",
        "calibrated_probability",
        "uncertainty",
        "threshold",
    ]
].copy()

df = routing_core.merge(
    test_core,
    on="encounter_id",
    how="inner",
    validate="one_to_one",
)

print("Routing population:", len(routing))
print("Test population:", len(test))
print("Aligned population:", len(df))

if len(df) != 15042:
    raise RuntimeError(
        f"Expected 15042 aligned encounters; found {len(df)}"
    )

expected_columns = {
    "encounter_id",
    "actual_30d",
    "predicted_30d",
    "selected_for_review",
    "calibrated_probability",
    "uncertainty",
    "threshold",
}

missing_after_merge = expected_columns - set(df.columns)

if missing_after_merge:
    raise RuntimeError(
        "Required columns missing after merge: "
        f"{sorted(missing_after_merge)}"
    )

duplicate_suffix_columns = [
    c for c in df.columns
    if c.endswith("_x") or c.endswith("_y")
]

print(
    "Duplicate-suffix columns after merge:",
    duplicate_suffix_columns
)

if duplicate_suffix_columns:
    raise RuntimeError(
        "Unexpected duplicate merge columns detected."
    )

print("Final experiment columns:")
for c in df.columns:
    print(" -", c)

print("Population alignment: PASSED")
print("Merge-column integrity: PASSED")

# =============================================================================
# D — RECONSTRUCT PRE-DECLARED SAFETY CONDITION
# =============================================================================

section("D — RECONSTRUCT FROZEN SAFETY CONDITION")

df["distance_below_threshold"] = (
    df["threshold"] - df["calibrated_probability"]
)

eligible = df["predicted_30d"] == 0

high_uncertainty = (
    df["uncertainty"] >= uncertainty_threshold
)

near_threshold = (
    df["distance_below_threshold"] <= distance_threshold
)

df["safety_override"] = (
    eligible
    & (high_uncertainty | near_threshold)
).astype(int)

override_count = int(df["safety_override"].sum())

expected_override = int(
    rule["rule_prevalence"]["union_override_count"]
)

print("Reconstructed override cases:", override_count)
print("Pre-declared override cases:", expected_override)

if override_count != expected_override:
    raise RuntimeError(
        "Reconstructed safety override does not match "
        "the pre-declared rule prevalence."
    )

print("Frozen safety-rule reconstruction: PASSED")


# =============================================================================
# E — ORIGINAL FROZEN ROUTING
# =============================================================================

section("E — ORIGINAL FROZEN ROUTING")

original_selected = (
    df["selected_for_review"] == 1
)

original_count = int(original_selected.sum())

negative_count = int(eligible.sum())

print("Primary-model-negative cases:", negative_count)
print("Original Rescue Review cases:", original_count)

original_review_rate_negative = (
    original_count / negative_count
)

print(
    f"Original review rate among negatives: "
    f"{original_review_rate_negative:.6f}"
)


# =============================================================================
# F — APPLY FORCED SAFETY ROUTE
# =============================================================================

section("F — APPLY COUNTERFACTUAL SAFETY OVERRIDE")

override_selected = (
    df["safety_override"] == 1
)

combined_selected = (
    original_selected | override_selected
)

df["counterfactual_selected_for_review"] = (
    combined_selected.astype(int)
)

new_total_review = int(combined_selected.sum())

additional_review = int(
    (override_selected & ~original_selected).sum()
)

overlap = int(
    (override_selected & original_selected).sum()
)

new_review_rate_negative = (
    new_total_review / negative_count
)

additional_review_rate_negative = (
    additional_review / negative_count
)

print("Original Rescue Review cases:", original_count)
print("Safety-override cases:", override_count)
print("Original/override overlap:", overlap)
print("Additional cases forced to review:", additional_review)

print("Combined review population:", new_total_review)

print(
    f"New review rate among negatives: "
    f"{new_review_rate_negative:.6f}"
)

print(
    f"Additional review burden among negatives: "
    f"{additional_review_rate_negative:.6f}"
)


# =============================================================================
# G — FALSE-NEGATIVE RESCUE IMPACT
# =============================================================================

section("G — FALSE-NEGATIVE RESCUE IMPACT")

fn_mask = (
    (df["actual_30d"] == 1)
    & (df["predicted_30d"] == 0)
)

fn_total = int(fn_mask.sum())

original_fn_reviewed = int(
    (fn_mask & original_selected).sum()
)

original_fn_bypass = int(
    (fn_mask & ~original_selected).sum()
)

override_fn = int(
    (fn_mask & override_selected).sum()
)

additional_fn_rescued = int(
    (
        fn_mask
        & override_selected
        & ~original_selected
    ).sum()
)

combined_fn_reviewed = int(
    (fn_mask & combined_selected).sum()
)

remaining_fn_bypass = int(
    (fn_mask & ~combined_selected).sum()
)

original_fn_coverage = (
    original_fn_reviewed / fn_total
)

combined_fn_coverage = (
    combined_fn_reviewed / fn_total
)

remaining_fn_fraction = (
    remaining_fn_bypass / fn_total
)

print("Total primary-model false negatives:", fn_total)

print()
print("ORIGINAL POLICY")
print("FN reviewed:", original_fn_reviewed)
print("FN bypassed:", original_fn_bypass)
print(
    f"FN review coverage: {original_fn_coverage:.6f}"
)

print()
print("SAFETY OVERRIDE")
print("FNs meeting override:", override_fn)
print(
    "Previously bypassed FNs newly forced to review:",
    additional_fn_rescued
)

print()
print("COMBINED POLICY")
print("FN reviewed:", combined_fn_reviewed)
print("FN still bypassed:", remaining_fn_bypass)

print(
    f"FN review coverage: {combined_fn_coverage:.6f}"
)

print(
    f"Remaining FN bypass fraction: "
    f"{remaining_fn_fraction:.6f}"
)


# =============================================================================
# H — EFFECTIVE POST-REVIEW SAFETY
# =============================================================================

section("H — EFFECTIVE POST-REVIEW SAFETY")

# This does NOT assume review changes the model prediction.
#
# It measures unresolved primary-model false negatives that receive
# no additional review opportunity.

actual_positive_count = int(
    (df["actual_30d"] == 1).sum()
)

original_unreviewed_fn_rate = (
    original_fn_bypass / actual_positive_count
)

combined_unreviewed_fn_rate = (
    remaining_fn_bypass / actual_positive_count
)

absolute_reduction = (
    original_unreviewed_fn_rate
    - combined_unreviewed_fn_rate
)

relative_reduction = (
    absolute_reduction / original_unreviewed_fn_rate
    if original_unreviewed_fn_rate > 0
    else float("nan")
)

print("Actual positive cases:", actual_positive_count)

print(
    "Original unresolved-FN rate among actual positives:",
    round(original_unreviewed_fn_rate, 6)
)

print(
    "Combined unresolved-FN rate among actual positives:",
    round(combined_unreviewed_fn_rate, 6)
)

print(
    "Absolute reduction:",
    round(absolute_reduction, 6)
)

print(
    "Relative reduction:",
    round(relative_reduction, 6)
)

print()
print(
    "IMPORTANT: this is an escalation-coverage metric, "
    "not proof that human review would correct the prediction."
)


# =============================================================================
# I — MARGINAL SAFETY EFFICIENCY
# =============================================================================

section("I — MARGINAL SAFETY EFFICIENCY")

marginal_precision = (
    additional_fn_rescued / additional_review
    if additional_review
    else float("nan")
)

reviews_per_additional_fn = (
    additional_review / additional_fn_rescued
    if additional_fn_rescued
    else float("inf")
)

print("Additional reviews:", additional_review)
print("Additional false negatives escalated:", additional_fn_rescued)

print(
    "Marginal FN yield of additional review:",
    round(marginal_precision, 6)
)

print(
    "Additional reviews per newly escalated FN:",
    round(reviews_per_additional_fn, 6)
)


# =============================================================================
# J — ROUTING FAILURE REPORT
# =============================================================================

section("J — SAFETY FAILURE REPORT")

print(
    "Baseline primary-model false negatives:",
    fn_total
)

print(
    "Original routing failures "
    "(FN bypassed Rescue Review):",
    original_fn_bypass
)

print(
    "Routing failures addressed by override:",
    additional_fn_rescued
)

print(
    "Routing failures remaining after override:",
    remaining_fn_bypass
)

if remaining_fn_bypass > 0:
    print("Residual safety failure present: YES")
else:
    print("Residual safety failure present: NO")

print(
    "Failures are retained and reported; none are removed "
    "from the audit."
)


# =============================================================================
# K — SAVE CASE-LEVEL EXPERIMENT
# =============================================================================

section("K — SAVE CASE-LEVEL EXPERIMENT")

case_columns = [
    "encounter_id",
    "actual_30d",
    "predicted_30d",
    "calibrated_probability",
    "uncertainty",
    "threshold",
    "distance_below_threshold",
    "selected_for_review",
    "safety_override",
    "counterfactual_selected_for_review",
]

df[case_columns].to_csv(
    CASE_PATH,
    index=False
)

print("Case-level experiment:", CASE_PATH)


# =============================================================================
# L — SAVE EXPERIMENT ARTIFACT
# =============================================================================

section("L — SAVE EXPERIMENT ARTIFACT")

audit = {
    "phase": "11.1.4",
    "experiment":
        "Forced Safety-Route Counterfactual Experiment",

    "predeclared_rule": {
        "rule_path": str(RULE_PATH),
        "rule_sha256": sha256_file(RULE_PATH),
        "rule_version": rule["rule_version"],
        "rule_status": rule["status"],
        "rule_modified_after_outcome_evaluation": False,
    },

    "population": {
        "test_population": int(len(df)),
        "actual_positive_cases": actual_positive_count,
        "primary_model_negative_cases": negative_count,
        "primary_model_false_negatives": fn_total,
    },

    "original_policy": {
        "review_cases": original_count,
        "negative_review_rate": original_review_rate_negative,
        "false_negatives_reviewed": original_fn_reviewed,
        "false_negatives_bypassed": original_fn_bypass,
        "false_negative_review_coverage":
            original_fn_coverage,
    },

    "safety_override": {
        "override_cases": override_count,
        "overlap_with_original_review": overlap,
        "additional_review_cases": additional_review,
        "additional_review_rate":
            additional_review_rate_negative,
        "false_negatives_meeting_override": override_fn,
        "previously_bypassed_false_negatives_escalated":
            additional_fn_rescued,
    },

    "combined_policy": {
        "review_cases": new_total_review,
        "negative_review_rate": new_review_rate_negative,
        "false_negatives_reviewed": combined_fn_reviewed,
        "false_negatives_remaining_bypass":
            remaining_fn_bypass,
        "false_negative_review_coverage":
            combined_fn_coverage,
        "false_negative_remaining_bypass_fraction":
            remaining_fn_fraction,
    },

    "safety_impact": {
        "original_unreviewed_fn_rate_among_actual_positives":
            original_unreviewed_fn_rate,
        "combined_unreviewed_fn_rate_among_actual_positives":
            combined_unreviewed_fn_rate,
        "absolute_reduction":
            absolute_reduction,
        "relative_reduction":
            relative_reduction,
        "additional_reviews_per_newly_escalated_fn":
            reviews_per_additional_fn,
        "marginal_fn_yield":
            marginal_precision,
    },

    "failure_reporting": {
        "original_routing_failures":
            original_fn_bypass,
        "failures_addressed_by_override":
            additional_fn_rescued,
        "residual_routing_failures":
            remaining_fn_bypass,
        "residual_failure_present":
            bool(remaining_fn_bypass > 0),
    },

    "interpretation": {
        "counterfactual_only": True,
        "primary_model_modified": False,
        "phase10_router_modified": False,
        "human_review_assumed_to_correct_prediction": False,
        "clinical_safety_claim": False,
        "note":
            "The experiment measures additional opportunities for "
            "human review. It does not assume that review would "
            "necessarily correct a false-negative prediction."
    },

    "integrity": {
        "routing_sha256": sha256_file(ROUTING_PATH),
        "test_predictions_sha256": sha256_file(TEST_PATH),
        "phase11_1_2_sha256": sha256_file(PHASE11_1_2),
        "phase10_modified": False,
    },

    "status": "PASSED",
}

with AUDIT_PATH.open("w") as f:
    json.dump(audit, f, indent=2)

print("Experiment artifact:", AUDIT_PATH)


# =============================================================================
# M — FINAL VERIFICATION
# =============================================================================

section("M — FINAL VERIFICATION")

with AUDIT_PATH.open() as f:
    saved = json.load(f)

checks = {
    "status":
        saved["status"] == "PASSED",

    "baseline_fn_lock":
        saved["population"][
            "primary_model_false_negatives"
        ] == 557,

    "original_review_lock":
        saved["original_policy"]["review_cases"] == 1178,

    "original_fn_lock":
        saved["original_policy"][
            "false_negatives_reviewed"
        ] == 110,

    "original_bypass_lock":
        saved["original_policy"][
            "false_negatives_bypassed"
        ] == 447,

    "rule_remained_frozen":
        saved["predeclared_rule"][
            "rule_modified_after_outcome_evaluation"
        ] is False,

    "phase10_unchanged":
        saved["integrity"]["phase10_modified"] is False,

    "fn_accounting":
        (
            saved["combined_policy"][
                "false_negatives_reviewed"
            ]
            +
            saved["combined_policy"][
                "false_negatives_remaining_bypass"
            ]
        ) == 557,

    "case_artifact":
        CASE_PATH.exists(),
}

for name, passed in checks.items():
    print(
        name + ":",
        "PASSED" if passed else "FAILED"
    )

if not all(checks.values()):
    raise RuntimeError(
        "Phase 11.1.4 final verification failed."
    )


# =============================================================================
# COMPLETE
# =============================================================================

section(
    "PHASE 11.1.4 COMPLETE — FORCED SAFETY-ROUTE EXPERIMENT PASSED"
)

print(
    "PASSED means the pre-declared experiment executed correctly."
)

print(
    "It does NOT establish clinical safety."
)

print()
print("Original FN reviewed:", original_fn_reviewed)
print("Original FN bypassed:", original_fn_bypass)

print(
    "Additional bypassed FNs escalated:",
    additional_fn_rescued
)

print(
    "Combined FN review coverage:",
    f"{combined_fn_coverage:.2%}"
)

print(
    "Residual FN bypass:",
    remaining_fn_bypass
)

print(
    "Combined review population:",
    new_total_review
)

print("Phase 10 frozen system modified: NO")
