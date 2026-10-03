from pathlib import Path
import json
import hashlib
import pandas as pd


print("=" * 80)
print("PHASE 12.5.1 — FREEZE FINAL SAFETY AND FAIRNESS PROTOCOL")
print("=" * 80)


# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------

ROOT = Path(".")

PREDICTIONS_PATH = Path(
    "results/eligible/final_test_router_predictions.csv"
)

PHASE12_4_LOCK = Path(
    "results/eligible/final_comparison/"
    "phase12_4_final_ablation_lock.json"
)

PHASE12_3_COMPARISON = Path(
    "results/eligible/final_comparison/"
    "phase12_3_final_system_comparison.csv"
)

OUT_DIR = Path(
    "results/eligible/final_comparison"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_PATH = (
    OUT_DIR /
    "phase12_5_1_fairness_protocol.json"
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

        for block in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(block)

    return h.hexdigest()


# ---------------------------------------------------------------------
# A — VERIFY FROZEN INPUTS
# ---------------------------------------------------------------------

section("A — VERIFY FROZEN INPUTS")

required = [
    PREDICTIONS_PATH,
    PHASE12_4_LOCK,
    PHASE12_3_COMPARISON,
]

for path in required:

    if not path.exists():
        raise FileNotFoundError(path)

    print("FOUND:", path)

print("Frozen input presence: PASSED")


# ---------------------------------------------------------------------
# B — VERIFY PHASE 12.4 LOCK
# ---------------------------------------------------------------------

section("B — VERIFY PREVIOUS PHASE LOCK")

with open(PHASE12_4_LOCK) as f:
    phase12_4 = json.load(f)

print(
    "Phase 12.4 status:",
    phase12_4["status"]
)

if phase12_4["status"] != \
        "ABLATION_STUDY_FROZEN":

    raise RuntimeError(
        "Phase 12.4 is not frozen."
    )

print("Phase 12.4 lock: PASSED")


# ---------------------------------------------------------------------
# C — LOAD FINAL ROUTER POPULATION
# ---------------------------------------------------------------------

section("C — LOAD FINAL ROUTER POPULATION")

df = pd.read_csv(
    PREDICTIONS_PATH
)

required_columns = [
    "encounter_id",
    "actual_30d",
    "predicted_30d",
    "selected_for_review",
    "age",
    "gender",
    "race",
]

missing = [
    c for c in required_columns
    if c not in df.columns
]

if missing:

    raise RuntimeError(
        f"Missing columns: {missing}"
    )

print("Rows:", len(df))

print(
    "Unique encounters:",
    df["encounter_id"].nunique()
)

print(
    "Primary false negatives:",
    int(df["actual_30d"].sum())
)

print(
    "Selected for review:",
    int(df["selected_for_review"].sum())
)

if len(df) != 7858:
    raise RuntimeError(
        "Expected 7,858 router-eligible cases."
    )

if df["encounter_id"].nunique() != 7858:
    raise RuntimeError(
        "Encounter IDs are not unique."
    )

if int(df["actual_30d"].sum()) != 557:
    raise RuntimeError(
        "Primary FN lock failed."
    )

if int(df["selected_for_review"].sum()) != 1178:
    raise RuntimeError(
        "Review-budget lock failed."
    )

if not (df["predicted_30d"] == 0).all():
    raise RuntimeError(
        "Population contains primary-positive cases."
    )

print("Final routing population: PASSED")


# ---------------------------------------------------------------------
# D — VERIFY FINAL ROUTER FN CAPTURE
# ---------------------------------------------------------------------

section("D — VERIFY FINAL ROUTER FN CAPTURE")

selected_fn = int(
    (
        (df["actual_30d"] == 1) &
        (df["selected_for_review"] == 1)
    ).sum()
)

fn_coverage = (
    selected_fn / 557
)

print(
    "False negatives escalated:",
    selected_fn
)

print(
    "FN coverage:",
    f"{fn_coverage:.6f}"
)

if selected_fn != 110:
    raise RuntimeError(
        "Expected 110 escalated false negatives."
    )

print("System D FN lock: PASSED")


# ---------------------------------------------------------------------
# E — FREEZE PROTECTED GROUPS
# ---------------------------------------------------------------------

section("E — FREEZE FAIRNESS GROUPS")

protected_attributes = {
    "gender": {
        "column": "gender",
        "grouping": "observed categories",
    },

    "race": {
        "column": "race",
        "grouping": "observed categories",
    },

    "age": {
        "column": "age",
        "grouping": "observed dataset age bands",
    },
}

for name, spec in protected_attributes.items():

    print()
    print(name.upper())

    print(
        df[spec["column"]]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

print()
print("Protected-group definitions: FROZEN")


# ---------------------------------------------------------------------
# F — FREEZE FAIRNESS METRICS
# ---------------------------------------------------------------------

section("F — FREEZE FAIRNESS METRICS")

metrics = {
    "group_population":
        (
            "Number of primary-model-negative cases "
            "in the subgroup."
        ),

    "group_review_rate":
        (
            "Fraction of subgroup cases selected "
            "for additional review."
        ),

    "group_false_negatives":
        (
            "Number of actual false negatives "
            "within the subgroup."
        ),

    "group_false_negatives_escalated":
        (
            "Number of subgroup false negatives "
            "selected for additional review."
        ),

    "group_fn_capture_rate":
        (
            "Fraction of subgroup false negatives "
            "selected for review."
        ),

    "group_review_precision_for_fn":
        (
            "Fraction of reviewed subgroup cases "
            "that are actual primary-model "
            "false negatives."
        ),

    "review_rate_gap":
        (
            "Maximum subgroup review rate minus "
            "minimum subgroup review rate among "
            "adequately supported groups."
        ),

    "fn_capture_gap":
        (
            "Maximum subgroup FN capture rate minus "
            "minimum subgroup FN capture rate among "
            "adequately supported groups."
        ),
}

for name, definition in metrics.items():

    print(name)
    print(" ", definition)

print()
print("Fairness metrics: FROZEN")


# ---------------------------------------------------------------------
# G — FREEZE SUPPORT RULES
# ---------------------------------------------------------------------

section("G — FREEZE SUBGROUP SUPPORT RULES")

support_rules = {
    "minimum_group_population": 50,

    "minimum_group_false_negatives": 10,

    "adequate_for_review_rate_comparison":
        (
            "group_population >= 50"
        ),

    "adequate_for_fn_capture_comparison":
        (
            "group_false_negatives >= 10"
        ),

    "small_group_policy":
        (
            "Report observed counts and rates but "
            "flag as LOW_SUPPORT and exclude from "
            "max-min disparity claims."
        ),
}

for key, value in support_rules.items():

    print(f"{key}: {value}")

print("Support rules: FROZEN")


# ---------------------------------------------------------------------
# H — FREEZE SAFETY INTERPRETATION
# ---------------------------------------------------------------------

section("H — FREEZE SAFETY INTERPRETATION BOUNDARY")

boundaries = [
    (
        "Demographic attributes are used only for "
        "post-routing audit and are not router inputs."
    ),

    (
        "Observed subgroup differences are descriptive "
        "and do not by themselves establish unlawful, "
        "causal, or clinically harmful discrimination."
    ),

    (
        "Small subgroups are reported with explicit "
        "support warnings rather than suppressed."
    ),

    (
        "No subgroup-specific threshold or routing rule "
        "may be created after viewing final-test results."
    ),

    (
        "No fairness result may be used to retune the "
        "frozen System D on the final test set."
    ),

    (
        "FN capture evaluates allocation of additional "
        "review, not guaranteed correction of the "
        "underlying false-negative prediction."
    ),

    (
        "The audit does not claim demographic parity, "
        "equalized odds, or clinical fairness certification."
    ),
]

for boundary in boundaries:
    print(" -", boundary)

print()
print("Safety interpretation boundary: FROZEN")


# ---------------------------------------------------------------------
# I — FREEZE COMPARISON QUESTIONS
# ---------------------------------------------------------------------

section("I — FREEZE PRIMARY FAIRNESS QUESTIONS")

questions = [
    (
        "Does System D allocate additional review at "
        "materially different rates across demographic "
        "subgroups?"
    ),

    (
        "Does System D capture primary-model false "
        "negatives at materially different rates across "
        "demographic subgroups?"
    ),

    (
        "Are apparent disparities driven by very small "
        "subgroup support?"
    ),

    (
        "Do the final results reveal safety signals that "
        "must be disclosed without post-hoc modification "
        "of the frozen router?"
    ),
]

for i, question in enumerate(
    questions,
    start=1
):
    print(f"{i}. {question}")

print()
print("Fairness questions: FROZEN")


# ---------------------------------------------------------------------
# J — PROHIBITED ACTIONS
# ---------------------------------------------------------------------

section("J — FREEZE PROHIBITED ACTIONS")

prohibited = [
    "Using gender as a router input",
    "Using race as a router input",
    "Using age as a router input",
    "Changing subgroup thresholds",
    "Changing the 1,178-case review budget",
    "Retraining the router",
    "Retuning the router",
    "Changing the primary classifier",
    "Changing the primary threshold",
    "Selecting a preferred system based on subgroup test results",
    "Suppressing unfavorable subgroup results",
]

for item in prohibited:
    print("PROHIBITED:", item)

print()
print("Prohibited actions: FROZEN")


# ---------------------------------------------------------------------
# K — CAPTURE SOURCE HASHES
# ---------------------------------------------------------------------

section("K — CAPTURE SOURCE HASHES")

source_hashes = {}

for path in required:

    digest = sha256(path)

    source_hashes[
        str(path)
    ] = digest

    print(
        path.name,
        "->",
        digest
    )

print("Source hashes captured: PASSED")


# ---------------------------------------------------------------------
# L — CREATE FINAL FAIRNESS PROTOCOL
# ---------------------------------------------------------------------

section("L — CREATE FINAL FAIRNESS PROTOCOL")

protocol = {
    "phase": "12.5.1",

    "status":
        "FINAL_FAIRNESS_PROTOCOL_FROZEN",

    "population": {
        "primary_model_negative_cases": 7858,
        "primary_model_false_negatives": 557,
        "system_D_reviews": 1178,
        "system_D_false_negatives_escalated": 110,
    },

    "protected_attributes":
        protected_attributes,

    "metrics":
        metrics,

    "support_rules":
        support_rules,

    "primary_questions":
        questions,

    "interpretation_boundaries":
        boundaries,

    "prohibited_actions":
        prohibited,

    "source_hashes":
        source_hashes,

    "integrity": {
        "demographics_used_for_routing":
            False,

        "subgroup_thresholds_allowed":
            False,

        "test_retuning_allowed":
            False,

        "router_retraining_allowed":
            False,

        "primary_model_change_allowed":
            False,

        "phase10_change_allowed":
            False,

        "phase11_change_allowed":
            False,

        "phase12_1_to_12_4_change_allowed":
            False,
    },

    "next_phase":
        (
            "12.5.2 — Execute final subgroup "
            "safety/fairness audit"
        ),
}

with open(
    OUTPUT_PATH,
    "w"
) as f:

    json.dump(
        protocol,
        f,
        indent=2
    )

print(
    "Protocol saved:",
    OUTPUT_PATH
)


# ---------------------------------------------------------------------
# M — FINAL VERIFICATION
# ---------------------------------------------------------------------

section("M — FINAL VERIFICATION")

checks = {
    "phase12_4_frozen":
        phase12_4["status"]
        == "ABLATION_STUDY_FROZEN",

    "population_lock":
        len(df) == 7858,

    "primary_fn_lock":
        int(df["actual_30d"].sum())
        == 557,

    "review_budget_lock":
        int(
            df["selected_for_review"].sum()
        ) == 1178,

    "system_D_fn_lock":
        selected_fn == 110,

    "three_attributes_frozen":
        len(protected_attributes) == 3,

    "minimum_population_rule_frozen":
        support_rules[
            "minimum_group_population"
        ] == 50,

    "minimum_fn_rule_frozen":
        support_rules[
            "minimum_group_false_negatives"
        ] == 10,

    "demographics_not_router_inputs":
        protocol["integrity"][
            "demographics_used_for_routing"
        ] is False,

    "test_retuning_prohibited":
        protocol["integrity"][
            "test_retuning_allowed"
        ] is False,

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
        "Phase 12.5.1 verification failed."
    )


print()
print("=" * 80)

print(
    "PHASE 12.5.1 COMPLETE — "
    "FINAL SAFETY/FAIRNESS PROTOCOL FROZEN"
)

print("=" * 80)

print()
print("Audit population: 7,858")
print("Primary false negatives: 557")
print("System D reviews: 1,178")
print("System D FNs escalated: 110")

print()
print(
    "Protected attributes: "
    "gender, race, age"
)

print(
    "Demographics used for routing: NO"
)

print(
    "Subgroup-specific retuning allowed: NO"
)

print()
print(
    "NEXT: PHASE 12.5.2 — "
    "EXECUTE FINAL SUBGROUP SAFETY/FAIRNESS AUDIT"
)
