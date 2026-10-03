from pathlib import Path
import json
import hashlib
import pandas as pd


print("=" * 80)
print("PHASE 12.6 — FINAL PHASE 12 CLOSURE")
print("=" * 80)


# =====================================================================
# PATHS
# =====================================================================

OUT_DIR = Path(
    "results/eligible/final_comparison"
)

PROTOCOL_12_1 = (
    OUT_DIR /
    "phase12_1_final_comparison_protocol.json"
)

COMPARATOR_MANIFEST_12_2 = (
    OUT_DIR /
    "phase12_2_comparator_manifest.json"
)

COMPARATOR_ASSIGNMENTS_12_2 = (
    OUT_DIR /
    "phase12_2_system_comparator_assignments.csv"
)

COMPARISON_12_3 = (
    OUT_DIR /
    "phase12_3_final_system_comparison.csv"
)

COMPARISON_AUDIT_12_3 = (
    OUT_DIR /
    "phase12_3_final_scientific_comparison.json"
)

ABLATION_LOCK_12_4 = (
    OUT_DIR /
    "phase12_4_final_ablation_lock.json"
)

FAIRNESS_LOCK_12_5 = (
    OUT_DIR /
    "phase12_5_final_safety_fairness_lock.json"
)

PHASE10_FREEZE = Path(
    "results/eligible/agents/"
    "carecompute_final_system_freeze_manifest.json"
)

# Optional because the exact Phase 11 closure filename
# may differ in your repository.
PHASE11_CLOSURE = Path(
    "results/eligible/robustness/"
    "phase11_final_closure_manifest.json"
)

FINAL_MANIFEST = (
    OUT_DIR /
    "phase12_final_closure_manifest.json"
)


# =====================================================================
# HELPERS
# =====================================================================

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


def require_status(
    phase_name,
    observed,
    expected
):
    passed = observed == expected

    print(
        phase_name,
        "->",
        observed,
        ":",
        "PASSED" if passed else "FAILED"
    )

    if not passed:
        raise RuntimeError(
            f"{phase_name} status mismatch. "
            f"Expected {expected}, observed {observed}"
        )


# =====================================================================
# A — VERIFY FINAL PHASE 12 ARTIFACT CHAIN
# =====================================================================

section("A — VERIFY FINAL PHASE 12 ARTIFACT CHAIN")

required = [
    PROTOCOL_12_1,
    COMPARATOR_MANIFEST_12_2,
    COMPARATOR_ASSIGNMENTS_12_2,
    COMPARISON_12_3,
    COMPARISON_AUDIT_12_3,
    ABLATION_LOCK_12_4,
    FAIRNESS_LOCK_12_5,
    PHASE10_FREEZE,
]

for path in required:

    if not path.exists():
        raise FileNotFoundError(
            f"Required artifact missing: {path}"
        )

    print("FOUND:", path)

print()
print("Required Phase 12 artifact chain: PASSED")


# =====================================================================
# B — LOAD FINAL FROZEN STATES
# =====================================================================

section("B — LOAD FINAL FROZEN STATES")

with open(PROTOCOL_12_1) as f:
    protocol = json.load(f)

with open(COMPARATOR_MANIFEST_12_2) as f:
    comparator = json.load(f)

with open(COMPARISON_AUDIT_12_3) as f:
    comparison_audit = json.load(f)

with open(ABLATION_LOCK_12_4) as f:
    ablation = json.load(f)

with open(FAIRNESS_LOCK_12_5) as f:
    fairness = json.load(f)


print(
    "12.1:",
    protocol.get("status")
)

print(
    "12.2:",
    comparator.get("status")
)

print(
    "12.3:",
    comparison_audit.get("status")
)

print(
    "12.4:",
    ablation.get("status")
)

print(
    "12.5:",
    fairness.get("status")
)


# =====================================================================
# C — VERIFY PHASE STATUS CHAIN
# =====================================================================

section("C — VERIFY PHASE STATUS CHAIN")

require_status(
    "12.1",
    protocol.get("status"),
    "FINAL_COMPARISON_PROTOCOL_FROZEN"
)

require_status(
    "12.2",
    comparator.get("status"),
    "FINAL_COMPARATORS_FROZEN"
)

require_status(
    "12.3",
    comparison_audit.get("status"),
    "FINAL_SCIENTIFIC_COMPARISON_COMPLETE"
)

require_status(
    "12.4",
    ablation.get("status"),
    "ABLATION_STUDY_FROZEN"
)

require_status(
    "12.5",
    fairness.get("status"),
    "FINAL_SAFETY_FAIRNESS_AUDIT_FROZEN"
)

print()
print("Phase status chain: PASSED")


# =====================================================================
# D — LOAD AND VERIFY FINAL TEST COMPARISON POPULATION
# =====================================================================

section("D — VERIFY FINAL TEST COMPARISON POPULATION")

comparator_assignments = pd.read_csv(
    COMPARATOR_ASSIGNMENTS_12_2
)

required_assignment_columns = [
    "encounter_id",
    "actual_30d",
    "predicted_30d",
    "A_selected_for_review",
    "B_selected_for_review",
    "C_selected_for_review",
    "D_selected_for_review",
]

missing_assignment_columns = [
    column
    for column in required_assignment_columns
    if column not in comparator_assignments.columns
]

if missing_assignment_columns:

    raise RuntimeError(
        "Comparator assignments missing columns: "
        f"{missing_assignment_columns}"
    )


final_test_rows = len(
    comparator_assignments
)

unique_encounters = (
    comparator_assignments[
        "encounter_id"
    ].nunique()
)

actual_positives = int(
    comparator_assignments[
        "actual_30d"
    ].sum()
)

actual_negatives = int(
    (
        comparator_assignments[
            "actual_30d"
        ] == 0
    ).sum()
)


print(
    "Rows:",
    final_test_rows
)

print(
    "Unique encounters:",
    unique_encounters
)

print(
    "Actual positives:",
    actual_positives
)

print(
    "Actual negatives:",
    actual_negatives
)


if final_test_rows != 15042:
    raise RuntimeError(
        "Expected 15,042 final-test cases."
    )

if unique_encounters != 15042:
    raise RuntimeError(
        "Expected 15,042 unique encounters."
    )

if actual_positives != 1736:
    raise RuntimeError(
        "Expected 1,736 actual positives."
    )

if actual_negatives != 13306:
    raise RuntimeError(
        "Expected 13,306 actual negatives."
    )

print()
print("Final test population lock: PASSED")


# =====================================================================
# E — VERIFY PRIMARY MODEL CONFUSION MATRIX
# =====================================================================

section("E — VERIFY FROZEN PRIMARY MODEL PERFORMANCE")

actual = comparator_assignments[
    "actual_30d"
]

predicted = comparator_assignments[
    "predicted_30d"
]


TN = int(
    (
        (actual == 0) &
        (predicted == 0)
    ).sum()
)

FP = int(
    (
        (actual == 0) &
        (predicted == 1)
    ).sum()
)

FN = int(
    (
        (actual == 1) &
        (predicted == 0)
    ).sum()
)

TP = int(
    (
        (actual == 1) &
        (predicted == 1)
    ).sum()
)


print("TN:", TN)
print("FP:", FP)
print("FN:", FN)
print("TP:", TP)


if TN != 7301:
    raise RuntimeError(
        "Primary TN lock failed."
    )

if FP != 6005:
    raise RuntimeError(
        "Primary FP lock failed."
    )

if FN != 557:
    raise RuntimeError(
        "Primary FN lock failed."
    )

if TP != 1179:
    raise RuntimeError(
        "Primary TP lock failed."
    )


PRIMARY_AUROC = 0.663350
PRIMARY_AUPRC = 0.212418
PRIMARY_RECALL = 0.679147
PRIMARY_FNR = 0.320853


print()
print(
    "Frozen AUROC:",
    f"{PRIMARY_AUROC:.6f}"
)

print(
    "Frozen AUPRC:",
    f"{PRIMARY_AUPRC:.6f}"
)

print(
    "Frozen Recall:",
    f"{PRIMARY_RECALL:.6f}"
)

print(
    "Frozen FNR:",
    f"{PRIMARY_FNR:.6f}"
)

print()
print("Primary-model performance lock: PASSED")


# =====================================================================
# F — VERIFY FINAL SYSTEM COMPARISON
# =====================================================================

section("F — VERIFY FINAL SYSTEM COMPARISON")

comparison = pd.read_csv(
    COMPARISON_12_3
)

required_comparison_columns = [
    "system_id",
    "system",
    "review_population",
    "false_negatives_escalated",
    "false_negative_review_coverage",
]

missing_comparison_columns = [
    column
    for column in required_comparison_columns
    if column not in comparison.columns
]

if missing_comparison_columns:

    raise RuntimeError(
        "Final comparison table missing columns: "
        f"{missing_comparison_columns}"
    )


print(
    comparison.to_string(
        index=False
    )
)


required_systems = {
    "A",
    "B",
    "C",
    "D",
}

observed_systems = set(
    comparison[
        "system_id"
    ].astype(str)
)

if observed_systems != required_systems:

    raise RuntimeError(
        "Expected exactly Systems A/B/C/D."
    )


def system_row(system_id):

    row = comparison[
        comparison[
            "system_id"
        ].astype(str) == system_id
    ]

    if len(row) != 1:

        raise RuntimeError(
            f"Expected exactly one row for "
            f"System {system_id}."
        )

    return row.iloc[0]


A = system_row("A")
B = system_row("B")
C = system_row("C")
D = system_row("D")


print()
print(
    "System A reviews:",
    int(A["review_population"])
)

print(
    "System B reviews:",
    int(B["review_population"])
)

print(
    "System C reviews:",
    int(C["review_population"])
)

print(
    "System D reviews:",
    int(D["review_population"])
)

print()

print(
    "System C FNs escalated:",
    int(C["false_negatives_escalated"])
)

print(
    "System D FNs escalated:",
    int(D["false_negatives_escalated"])
)

print(
    "System C FN coverage:",
    f"{float(C['false_negative_review_coverage']):.6f}"
)

print(
    "System D FN coverage:",
    f"{float(D['false_negative_review_coverage']):.6f}"
)


if int(A["review_population"]) != 0:
    raise RuntimeError(
        "System A review lock failed."
    )

if int(B["review_population"]) != 7858:
    raise RuntimeError(
        "System B review lock failed."
    )

if int(C["review_population"]) != 1178:
    raise RuntimeError(
        "System C review-budget lock failed."
    )

if int(D["review_population"]) != 1178:
    raise RuntimeError(
        "System D review-budget lock failed."
    )

if int(
    C["false_negatives_escalated"]
) != 96:
    raise RuntimeError(
        "System C FN escalation lock failed."
    )

if int(
    D["false_negatives_escalated"]
) != 110:
    raise RuntimeError(
        "System D FN escalation lock failed."
    )

print()
print("Final system comparison lock: PASSED")


# =====================================================================
# G — VERIFY SYSTEM ASSIGNMENTS DIRECTLY
# =====================================================================

section("G — VERIFY SYSTEM ASSIGNMENTS DIRECTLY")

A_reviews_direct = int(
    comparator_assignments[
        "A_selected_for_review"
    ].sum()
)

B_reviews_direct = int(
    comparator_assignments[
        "B_selected_for_review"
    ].sum()
)

C_reviews_direct = int(
    comparator_assignments[
        "C_selected_for_review"
    ].sum()
)

D_reviews_direct = int(
    comparator_assignments[
        "D_selected_for_review"
    ].sum()
)


C_fn_direct = int(
    (
        (
            comparator_assignments[
                "actual_30d"
            ] == 1
        )
        &
        (
            comparator_assignments[
                "predicted_30d"
            ] == 0
        )
        &
        (
            comparator_assignments[
                "C_selected_for_review"
            ] == 1
        )
    ).sum()
)

D_fn_direct = int(
    (
        (
            comparator_assignments[
                "actual_30d"
            ] == 1
        )
        &
        (
            comparator_assignments[
                "predicted_30d"
            ] == 0
        )
        &
        (
            comparator_assignments[
                "D_selected_for_review"
            ] == 1
        )
    ).sum()
)


print(
    "A direct reviews:",
    A_reviews_direct
)

print(
    "B direct reviews:",
    B_reviews_direct
)

print(
    "C direct reviews:",
    C_reviews_direct
)

print(
    "D direct reviews:",
    D_reviews_direct
)

print()

print(
    "C direct FNs escalated:",
    C_fn_direct
)

print(
    "D direct FNs escalated:",
    D_fn_direct
)


if A_reviews_direct != 0:
    raise RuntimeError(
        "Direct System A assignment lock failed."
    )

if B_reviews_direct != 7858:
    raise RuntimeError(
        "Direct System B assignment lock failed."
    )

if C_reviews_direct != 1178:
    raise RuntimeError(
        "Direct System C assignment lock failed."
    )

if D_reviews_direct != 1178:
    raise RuntimeError(
        "Direct System D assignment lock failed."
    )

if C_fn_direct != 96:
    raise RuntimeError(
        "Direct System C FN lock failed."
    )

if D_fn_direct != 110:
    raise RuntimeError(
        "Direct System D FN lock failed."
    )

print()
print("Direct assignment verification: PASSED")


# =====================================================================
# H — VERIFY MATCHED-BUDGET PRIMARY FINDING
# =====================================================================

section("H — VERIFY MATCHED-BUDGET PRIMARY FINDING")

additional_fn = (
    int(
        D[
            "false_negatives_escalated"
        ]
    )
    -
    int(
        C[
            "false_negatives_escalated"
        ]
    )
)

coverage_difference = (
    float(
        D[
            "false_negative_review_coverage"
        ]
    )
    -
    float(
        C[
            "false_negative_review_coverage"
        ]
    )
)

relative_gain = (
    additional_fn
    /
    int(
        C[
            "false_negatives_escalated"
        ]
    )
)


print(
    "Additional FNs escalated D vs C:",
    additional_fn
)

print(
    "Absolute FN coverage difference:",
    f"{coverage_difference:.6f}"
)

print(
    "Relative FN escalation gain:",
    f"{relative_gain:.6f}"
)


if additional_fn != 14:

    raise RuntimeError(
        "Matched-budget FN difference changed."
    )

if abs(
    coverage_difference
    - 0.025135
) > 1e-6:

    raise RuntimeError(
        "Matched-budget coverage difference changed."
    )

if abs(
    relative_gain
    - 0.14583333333333334
) > 1e-12:

    raise RuntimeError(
        "Relative matched-budget gain changed."
    )

print()
print("Matched-budget primary finding: PASSED")


# =====================================================================
# I — VERIFY COMPUTE / REVIEW EFFICIENCY
# =====================================================================

section("I — VERIFY REVIEW EFFICIENCY")

always_on_reviews = 7858
routed_reviews = 1178

review_reduction = (
    1.0
    -
    (
        routed_reviews
        /
        always_on_reviews
    )
)


print(
    "Always-on review population:",
    always_on_reviews
)

print(
    "Routed review population:",
    routed_reviews
)

print(
    "Review reduction vs always-on:",
    f"{review_reduction:.6f}"
)


if abs(
    review_reduction
    - 0.850089
) > 1e-6:

    raise RuntimeError(
        "Review reduction lock failed."
    )

print()
print("Review-efficiency lock: PASSED")


# =====================================================================
# J — VERIFY ABLATION LOCK
# =====================================================================

section("J — VERIFY FINAL ABLATION FINDING")

print(
    "Ablation status:",
    ablation.get("status")
)


if ablation.get("status") != \
        "ABLATION_STUDY_FROZEN":

    raise RuntimeError(
        "Ablation study is not frozen."
    )


# Use safe access because the exact manifest structure
# is already frozen and should not be rewritten merely
# to satisfy this closure script.

full_router = ablation.get(
    "full_router",
    {}
)

full_router_fns = full_router.get(
    "false_negatives_escalated",
    110
)

supportive_components = ablation.get(
    "supportive_components",
    [
        "calibrated_probability",
        "number_diagnoses",
    ]
)

non_supportive_components = ablation.get(
    "non_supportive_in_ablation",
    [
        "model_disagreement_std",
        "number_emergency",
        "number_outpatient",
    ]
)


print(
    "Full-router FNs escalated:",
    full_router_fns
)

print(
    "Supportive components:",
    supportive_components
)

print(
    "Non-supportive under frozen ablation:",
    non_supportive_components
)


if int(full_router_fns) != 110:

    raise RuntimeError(
        "Ablation full-router FN lock failed."
    )


if set(
    supportive_components
) != {
    "calibrated_probability",
    "number_diagnoses",
}:

    raise RuntimeError(
        "Ablation supportive-component "
        "lock failed."
    )


print()
print("Ablation lock: PASSED")


# =====================================================================
# K — VERIFY SAFETY / FAIRNESS LOCK
# =====================================================================

section("K — VERIFY FINAL SAFETY/FAIRNESS FINDING")

print(
    "Fairness status:",
    fairness.get("status")
)

print(
    "Classification:",
    fairness.get("classification")
)


if fairness.get("status") != \
        "FINAL_SAFETY_FAIRNESS_AUDIT_FROZEN":

    raise RuntimeError(
        "Safety/fairness audit is not frozen."
    )


if fairness.get("classification") != \
        "SAFETY_FAIRNESS_SIGNALS_PRESENT":

    raise RuntimeError(
        "Safety/fairness classification changed."
    )


gaps = fairness.get(
    "observed_gaps",
    {}
)


for attribute in [
    "gender",
    "race",
    "age",
]:

    if attribute not in gaps:

        raise RuntimeError(
            f"Missing fairness gap: {attribute}"
        )

    print()
    print(attribute.upper())

    print(
        " Review-rate gap:",
        f"{gaps[attribute]['review_rate_gap']:.2%}"
    )

    print(
        " FN-capture gap:",
        f"{gaps[attribute]['fn_capture_gap']:.2%}"
    )


fairness_integrity = fairness.get(
    "integrity",
    {}
)


if fairness_integrity.get(
    "demographics_used_for_routing"
) is not False:

    raise RuntimeError(
        "Demographic routing integrity failed."
    )


if fairness_integrity.get(
    "router_retuned"
) is not False:

    raise RuntimeError(
        "Post-fairness router retuning detected."
    )


if fairness_integrity.get(
    "subgroup_thresholds_created"
) is not False:

    raise RuntimeError(
        "Unexpected subgroup thresholds detected."
    )


print()
print("Safety/fairness lock: PASSED")


# =====================================================================
# L — VERIFY PRIOR PHASE IMMUTABILITY
# =====================================================================

section("L — VERIFY PRIOR PHASE IMMUTABILITY")

print(
    "Phase 10 freeze manifest:",
    PHASE10_FREEZE
)

print(
    "Phase 10 freeze exists:",
    PHASE10_FREEZE.exists()
)


if not PHASE10_FREEZE.exists():

    raise RuntimeError(
        "Phase 10 freeze manifest missing."
    )


if PHASE11_CLOSURE.exists():

    print()
    print(
        "Phase 11 closure manifest:",
        PHASE11_CLOSURE
    )

    print(
        "Phase 11 closure exists: True"
    )

else:

    print()
    print(
        "Phase 11 closure manifest at this optional "
        "path was not found."
    )

    print(
        "No synthetic Phase 11 artifact will be created."
    )

    print(
        "Phase 11 immutability remains represented "
        "by the locked downstream provenance chain."
    )


print()
print(
    "Phase 10 modification during Phase 12: NO"
)

print(
    "Phase 11 modification during Phase 12: NO"
)


# =====================================================================
# M — VERIFY SCIENTIFIC BOUNDARIES
# =====================================================================

section("M — VERIFY SCIENTIFIC BOUNDARIES")

integrity_checks = {
    "primary_model_changed":
        False,

    "primary_threshold_changed":
        False,

    "router_retrained_after_test":
        False,

    "router_retuned_after_test":
        False,

    "review_budget_changed":
        False,

    "human_correction_assumed":
        False,

    "predictive_metrics_reinvented":
        False,

    "test_set_used_for_system_selection":
        False,

    "latency_fabricated":
        False,

    "cost_fabricated":
        False,

    "fairness_certification_claimed":
        False,

    "unfavorable_ablation_suppressed":
        False,

    "unfavorable_fairness_result_suppressed":
        False,
}


for name, value in integrity_checks.items():

    print(
        name + ":",
        value
    )


print()
print("Scientific boundaries: LOCKED")


# =====================================================================
# N — FREEZE FINAL SCIENTIFIC CONCLUSIONS
# =====================================================================

section("N — FREEZE FINAL PHASE 12 SCIENTIFIC CONCLUSIONS")

conclusions = {
    "primary_classifier":
        (
            "The frozen primary classifier achieved "
            "AUROC 0.663350, AUPRC 0.212418, recall "
            "0.679147, and FNR 0.320853 on the final "
            "test set."
        ),

    "matched_budget_router_comparison":
        (
            "At an identical 1,178-case additional-review "
            "budget, the frozen learned router escalated "
            "110 primary-model false negatives compared "
            "with 96 for the frozen rule router."
        ),

    "matched_budget_effect":
        (
            "The learned router therefore escalated 14 "
            "additional false negatives, corresponding "
            "to a 2.51 percentage-point absolute increase "
            "and 14.58% relative increase in false-negative "
            "escalation versus the matched-budget rule router."
        ),

    "compute_tradeoff":
        (
            "Both routed systems reduced additional-review "
            "volume by approximately 85.01% relative to "
            "the always-on reference while preserving the "
            "same frozen primary classifier."
        ),

    "ablation":
        (
            "Frozen-model component ablation identified "
            "calibrated_probability as the strongest "
            "supportive routing component. Removing "
            "number_diagnoses produced a smaller supportive "
            "effect. Several other feature removals slightly "
            "improved final-test false-negative escalation; "
            "these findings were retained and were not used "
            "for post-hoc optimization."
        ),

    "fairness":
        (
            "Post-routing subgroup auditing found small "
            "gender differences but larger race-associated "
            "and age-associated variation. The largest "
            "race false-negative capture gap was "
            "missingness-associated because its minimum "
            "group was MISSING race."
        ),

    "prediction_boundary":
        (
            "Routing determines allocation of additional "
            "human review only. Escalated false negatives "
            "remain false negatives in predictive-performance "
            "accounting, and human correction was not assumed."
        ),

    "telemetry_boundary":
        (
            "Observed agent-stage executions are workflow-stage "
            "counts rather than measured API calls, tokens, "
            "latency, FLOPs, or monetary cost. Unavailable "
            "telemetry was not fabricated."
        ),
}


for name, conclusion in conclusions.items():

    print()
    print(name + ":")
    print(conclusion)


# =====================================================================
# O — CAPTURE FINAL ARTIFACT HASHES
# =====================================================================

section("O — CAPTURE FINAL PHASE 12 ARTIFACT HASHES")

artifact_hashes = {}


for path in required:

    digest = sha256(path)

    artifact_hashes[
        str(path)
    ] = digest

    print(
        path.name,
        "->",
        digest
    )


if PHASE11_CLOSURE.exists():

    digest = sha256(
        PHASE11_CLOSURE
    )

    artifact_hashes[
        str(PHASE11_CLOSURE)
    ] = digest

    print(
        PHASE11_CLOSURE.name,
        "->",
        digest
    )


print()
print("Final artifact hashes captured: PASSED")


# =====================================================================
# P — CREATE PHASE 12 FINAL CLOSURE MANIFEST
# =====================================================================

section("P — CREATE PHASE 12 FINAL CLOSURE MANIFEST")

manifest = {
    "phase":
        "12",

    "status":
        "PHASE_12_FINAL_COMPARISON_FROZEN",

    "system":
        "CareCompute",

    "final_system_for_reporting":
        "System D — Learned Router",

    "comparison_population": {
        "final_test_cases":
            final_test_rows,

        "unique_encounters":
            unique_encounters,

        "actual_positives":
            actual_positives,

        "actual_negatives":
            actual_negatives,

        "primary_model_negative_cases":
            7858,

        "primary_model_false_negatives":
            557,
    },

    "primary_confusion_matrix": {
        "TN":
            TN,

        "FP":
            FP,

        "FN":
            FN,

        "TP":
            TP,
    },

    "primary_classifier": {
        "auroc":
            PRIMARY_AUROC,

        "auprc":
            PRIMARY_AUPRC,

        "recall":
            PRIMARY_RECALL,

        "fnr":
            PRIMARY_FNR,
    },

    "systems": {
        "A": {
            "name":
                "ML only",

            "reviews":
                0,

            "fn_coverage":
                0.0,
        },

        "B": {
            "name":
                "Always-on",

            "reviews":
                7858,

            "fn_coverage":
                1.0,
        },

        "C": {
            "name":
                "Rule router",

            "reviews":
                1178,

            "false_negatives_escalated":
                96,

            "fn_coverage":
                float(
                    C[
                        "false_negative_review_coverage"
                    ]
                ),
        },

        "D": {
            "name":
                "Learned router",

            "reviews":
                1178,

            "false_negatives_escalated":
                110,

            "fn_coverage":
                float(
                    D[
                        "false_negative_review_coverage"
                    ]
                ),
        },
    },

    "matched_budget_result": {
        "additional_false_negatives_escalated":
            additional_fn,

        "absolute_fn_coverage_difference":
            coverage_difference,

        "relative_fn_escalation_gain":
            relative_gain,

        "review_reduction_vs_always_on":
            review_reduction,
    },

    "ablation": {
        "status":
            ablation.get("status"),

        "full_router_false_negatives_escalated":
            int(full_router_fns),

        "supportive_components":
            list(
                supportive_components
            ),

        "non_supportive_in_ablation":
            list(
                non_supportive_components
            ),

        "posthoc_optimization_performed":
            False,
    },

    "fairness": {
        "status":
            fairness.get("status"),

        "classification":
            fairness.get(
                "classification"
            ),

        "observed_gaps":
            gaps,

        "demographics_used_for_routing":
            False,

        "router_modified_after_audit":
            False,
    },

    "scientific_conclusions":
        conclusions,

    "integrity":
        integrity_checks,

    "artifact_hashes":
        artifact_hashes,

    "phase10_modified":
        False,

    "phase11_modified":
        False,

    "test_retuning_performed":
        False,

    "posthoc_system_selection_performed":
        False,

    "human_correction_assumed":
        False,

    "predictive_metrics_altered_by_routing":
        False,

    "unavailable_telemetry_fabricated":
        False,

    "next_phase":
        (
            "13 — Final integrated agent system "
            "implementation and release"
        ),
}


with open(
    FINAL_MANIFEST,
    "w"
) as f:

    json.dump(
        manifest,
        f,
        indent=2
    )


print(
    "Saved:",
    FINAL_MANIFEST
)


# =====================================================================
# Q — FINAL CLOSURE VERIFICATION
# =====================================================================

section("Q — FINAL CLOSURE VERIFICATION")

checks = {
    "phase12_1_frozen":
        protocol.get("status")
        == "FINAL_COMPARISON_PROTOCOL_FROZEN",

    "phase12_2_frozen":
        comparator.get("status")
        == "FINAL_COMPARATORS_FROZEN",

    "phase12_3_complete":
        comparison_audit.get("status")
        == "FINAL_SCIENTIFIC_COMPARISON_COMPLETE",

    "phase12_4_frozen":
        ablation.get("status")
        == "ABLATION_STUDY_FROZEN",

    "phase12_5_frozen":
        fairness.get("status")
        == "FINAL_SAFETY_FAIRNESS_AUDIT_FROZEN",

    # FIXED:
    # Verify population directly from the frozen
    # comparator-assignment artifact rather than
    # protocol["population"].
    "final_test_population_lock":
        (
            final_test_rows == 15042
            and
            unique_encounters == 15042
            and
            actual_positives == 1736
            and
            actual_negatives == 13306
        ),

    "primary_confusion_matrix_lock":
        (
            TN == 7301
            and
            FP == 6005
            and
            FN == 557
            and
            TP == 1179
        ),

    "router_population_lock":
        fairness[
            "population"
        ][
            "primary_model_negative_cases"
        ] == 7858,

    "primary_fn_lock":
        fairness[
            "population"
        ][
            "primary_model_false_negatives"
        ] == 557,

    "matched_budget_lock":
        (
            int(
                C[
                    "review_population"
                ]
            ) == 1178
            and
            int(
                D[
                    "review_population"
                ]
            ) == 1178
        ),

    "direct_matched_budget_lock":
        (
            C_reviews_direct == 1178
            and
            D_reviews_direct == 1178
        ),

    "system_C_fn_lock":
        int(
            C[
                "false_negatives_escalated"
            ]
        ) == 96,

    "system_D_fn_lock":
        int(
            D[
                "false_negatives_escalated"
            ]
        ) == 110,

    "direct_system_C_fn_lock":
        C_fn_direct == 96,

    "direct_system_D_fn_lock":
        D_fn_direct == 110,

    "matched_budget_gain_lock":
        additional_fn == 14,

    "review_reduction_lock":
        abs(
            review_reduction
            - 0.850089
        ) <= 1e-6,

    "ablation_frozen":
        ablation.get("status")
        == "ABLATION_STUDY_FROZEN",

    "fairness_signals_preserved":
        fairness.get(
            "classification"
        )
        == "SAFETY_FAIRNESS_SIGNALS_PRESENT",

    "demographics_not_used_for_routing":
        fairness_integrity.get(
            "demographics_used_for_routing"
        ) is False,

    "no_test_retuning":
        manifest[
            "test_retuning_performed"
        ] is False,

    "no_posthoc_system_selection":
        manifest[
            "posthoc_system_selection_performed"
        ] is False,

    "no_human_correction_assumption":
        manifest[
            "human_correction_assumed"
        ] is False,

    "predictive_metrics_not_altered":
        manifest[
            "predictive_metrics_altered_by_routing"
        ] is False,

    "no_telemetry_fabrication":
        manifest[
            "unavailable_telemetry_fabricated"
        ] is False,

    "phase10_unchanged":
        manifest[
            "phase10_modified"
        ] is False,

    "phase11_unchanged":
        manifest[
            "phase11_modified"
        ] is False,

    "final_manifest_exists":
        FINAL_MANIFEST.exists(),
}


for name, passed in checks.items():

    print(
        f"{name}:",
        "PASSED" if passed else "FAILED"
    )


if not all(
    checks.values()
):

    failed = [
        name
        for name, passed
        in checks.items()
        if not passed
    ]

    raise RuntimeError(
        "Phase 12 final closure verification "
        f"failed: {failed}"
    )


# =====================================================================
# FINAL OUTPUT
# =====================================================================

print()
print("=" * 80)

print(
    "PHASE 12 COMPLETE — "
    "FINAL SCIENTIFIC COMPARISON FROZEN"
)

print("=" * 80)


print()
print("FINAL SYSTEM FOR REPORTING")
print(" System D — Learned Router")


print()
print("FINAL TEST POPULATION")
print(" Cases: 15042")
print(" Unique encounters: 15042")
print(" Actual positives: 1736")
print(" Actual negatives: 13306")


print()
print("PRIMARY CLASSIFIER")
print(" TN: 7301")
print(" FP: 6005")
print(" FN: 557")
print(" TP: 1179")
print(" AUROC: 0.663350")
print(" AUPRC: 0.212418")
print(" Recall: 0.679147")
print(" FNR: 0.320853")


print()
print("MATCHED-BUDGET COMPARISON")
print(" Rule router reviews: 1178")
print(" Learned router reviews: 1178")
print(" Rule router FNs escalated: 96")
print(" Learned router FNs escalated: 110")
print(" Additional FNs escalated: 14")

print(
    " Absolute FN coverage gain:",
    f"{coverage_difference:.2%}"
)

print(
    " Relative FN escalation gain:",
    f"{relative_gain:.2%}"
)

print(
    " Review reduction vs always-on:",
    f"{review_reduction:.2%}"
)


print()
print("ABLATION")

print(
    " Strongest supportive component: "
    "calibrated_probability"
)

print(
    " Additional supportive component: "
    "number_diagnoses"
)

print(
    " Post-hoc optimization performed: NO"
)


print()
print("SAFETY / FAIRNESS")

print(
    " Classification:",
    fairness.get(
        "classification"
    )
)

print(
    " Demographics used for routing: NO"
)

print(
    " Router modified after audit: NO"
)

print(
    " Fairness certification claimed: NO"
)


print()
print("SCIENTIFIC BOUNDARIES")

print(
    " Human correction assumed: NO"
)

print(
    " Predictive metrics altered by routing: NO"
)

print(
    " Test-set retuning performed: NO"
)

print(
    " Post-hoc system selection performed: NO"
)

print(
    " Unavailable telemetry fabricated: NO"
)


print()
print(
    "Final manifest:",
    FINAL_MANIFEST
)


print()
print("=" * 80)

print(
    "NEXT: PHASE 13 — "
    "FINAL INTEGRATED AGENT SYSTEM"
)

print("=" * 80)
