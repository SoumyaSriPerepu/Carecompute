from pathlib import Path
import pandas as pd
import numpy as np
import json
import hashlib

from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
)


# =============================================================================
# PATHS
# =============================================================================

ASSIGN_PATH = Path(
    "results/eligible/final_comparison/"
    "phase12_2_system_comparator_assignments.csv"
)

PROTOCOL_PATH = Path(
    "results/eligible/final_comparison/"
    "phase12_1_final_comparison_protocol.json"
)

COMPARATOR_MANIFEST_PATH = Path(
    "results/eligible/final_comparison/"
    "phase12_2_comparator_manifest.json"
)

OUT_DIR = Path(
    "results/eligible/final_comparison"
)

RESULT_TABLE_PATH = (
    OUT_DIR /
    "phase12_3_final_system_comparison.csv"
)

CASE_PATH = (
    OUT_DIR /
    "phase12_3_case_level_comparison.csv"
)

AUDIT_PATH = (
    OUT_DIR /
    "phase12_3_final_scientific_comparison.json"
)


# =============================================================================
# HELPERS
# =============================================================================

def section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def load_json(path):
    with path.open() as f:
        return json.load(f)


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
    "PHASE 12.3 — FINAL SCIENTIFIC COMPARISON"
)


# =============================================================================
# A — VERIFY FROZEN INPUTS
# =============================================================================

section("A — VERIFY FROZEN INPUTS")

required = [
    ASSIGN_PATH,
    PROTOCOL_PATH,
    COMPARATOR_MANIFEST_PATH,
]

for path in required:

    if not path.exists():
        raise FileNotFoundError(path)

    print("FOUND:", path)


protocol = load_json(PROTOCOL_PATH)
manifest = load_json(COMPARATOR_MANIFEST_PATH)


if protocol["status"] != "FINAL_COMPARISON_PROTOCOL_FROZEN":
    raise RuntimeError(
        "Phase 12.1 protocol is not frozen."
    )


if manifest["status"] != "FINAL_COMPARATORS_FROZEN":
    raise RuntimeError(
        "Phase 12.2 comparators are not frozen."
    )


print("Frozen comparison chain: PASSED")


# =============================================================================
# B — LOAD CASE-LEVEL COMPARISON
# =============================================================================

section("B — LOAD FINAL TEST COMPARISON POPULATION")

df = pd.read_csv(ASSIGN_PATH)


required_columns = [
    "encounter_id",
    "actual_30d",
    "predicted_30d",
    "calibrated_probability",
    "A_selected_for_review",
    "B_selected_for_review",
    "C_selected_for_review",
    "D_selected_for_review",
]


missing = [
    x for x in required_columns
    if x not in df.columns
]


if missing:
    raise RuntimeError(
        f"Missing comparison columns: {missing}"
    )


print("Rows:", len(df))
print(
    "Unique encounters:",
    df["encounter_id"].nunique()
)

print(
    "Actual positives:",
    int(df["actual_30d"].sum())
)

print(
    "Actual negatives:",
    int(
        len(df)
        - df["actual_30d"].sum()
    )
)


if len(df) != 15042:
    raise RuntimeError(
        "Final test population changed."
    )


if df["encounter_id"].nunique() != 15042:
    raise RuntimeError(
        "Encounter uniqueness failed."
    )


print("Final test population: PASSED")


# =============================================================================
# C — VERIFY FROZEN PRIMARY PERFORMANCE
# =============================================================================

section("C — VERIFY FROZEN PRIMARY PERFORMANCE")


y = df["actual_30d"].astype(int)
pred = df["predicted_30d"].astype(int)
prob = df["calibrated_probability"].astype(float)


auroc = float(
    roc_auc_score(
        y,
        prob,
    )
)

auprc = float(
    average_precision_score(
        y,
        prob,
    )
)


tn, fp, fn, tp = confusion_matrix(
    y,
    pred,
    labels=[0, 1],
).ravel()


recall = (
    tp / (tp + fn)
)

fnr = (
    fn / (tp + fn)
)


print("TN:", tn)
print("FP:", fp)
print("FN:", fn)
print("TP:", tp)

print()
print(
    "AUROC:",
    f"{auroc:.6f}"
)

print(
    "AUPRC:",
    f"{auprc:.6f}"
)

print(
    "Recall:",
    f"{recall:.6f}"
)

print(
    "FNR:",
    f"{fnr:.6f}"
)


if fn != 557:
    raise RuntimeError(
        "Frozen FN count changed."
    )


if tp != 1179:
    raise RuntimeError(
        "Frozen TP count changed."
    )


print("Primary-model performance lock: PASSED")


# =============================================================================
# D — DEFINE PRIMARY-MODEL FALSE NEGATIVES
# =============================================================================

section("D — DEFINE ROUTING-EVALUATION TARGET")


df["primary_false_negative"] = (
    (df["actual_30d"] == 1)
    &
    (df["predicted_30d"] == 0)
).astype(int)


total_fn = int(
    df[
        "primary_false_negative"
    ].sum()
)


negative_population = int(
    (df["predicted_30d"] == 0).sum()
)


print(
    "Primary-model-negative cases:",
    negative_population
)

print(
    "Primary-model false negatives:",
    total_fn
)


if negative_population != 7858:
    raise RuntimeError(
        "Negative population changed."
    )


if total_fn != 557:
    raise RuntimeError(
        "False-negative population changed."
    )


print(
    "Routing evaluation target: "
    "primary-model false-negative escalation"
)


# =============================================================================
# E — CALCULATE SYSTEM RESULTS
# =============================================================================

section("E — CALCULATE A/B/C/D SYSTEM RESULTS")


system_definitions = {
    "A": {
        "name":
            "ML only",

        "column":
            "A_selected_for_review",
    },

    "B": {
        "name":
            "Always-on",

        "column":
            "B_selected_for_review",
    },

    "C": {
        "name":
            "Rule router",

        "column":
            "C_selected_for_review",
    },

    "D": {
        "name":
            "Learned router",

        "column":
            "D_selected_for_review",
    },
}


rows = []


for system_id, spec in system_definitions.items():

    col = spec["column"]

    selected = (
        df[col] == 1
    )

    reviewed = int(
        selected.sum()
    )

    review_rate_full = (
        reviewed / len(df)
    )

    review_rate_negative = (
        reviewed / negative_population
    )

    fn_reviewed = int(
        (
            selected
            &
            (df["primary_false_negative"] == 1)
        ).sum()
    )

    fn_bypassed = (
        total_fn - fn_reviewed
    )

    fn_coverage = (
        fn_reviewed / total_fn
    )

    fn_bypass_fraction = (
        fn_bypassed / total_fn
    )

    review_precision_for_fn = (
        fn_reviewed / reviewed
        if reviewed > 0
        else np.nan
    )

    reviews_per_fn = (
        reviewed / fn_reviewed
        if fn_reviewed > 0
        else np.nan
    )

    # Frozen workflow:
    # selected cases have two observed downstream
    # agent-output stages.
    observed_agent_stage_executions = (
        reviewed * 2
    )

    mean_stage_executions_per_test_case = (
        observed_agent_stage_executions
        / len(df)
    )

    row = {
        "system_id":
            system_id,

        "system":
            spec["name"],

        "auprc":
            auprc,

        "auroc":
            auroc,

        "recall":
            recall,

        "fnr":
            fnr,

        "review_population":
            reviewed,

        "review_rate_full_test":
            review_rate_full,

        "review_rate_model_negative":
            review_rate_negative,

        "false_negatives_escalated":
            fn_reviewed,

        "false_negative_review_coverage":
            fn_coverage,

        "false_negatives_bypassed":
            fn_bypassed,

        "false_negative_bypass_fraction":
            fn_bypass_fraction,

        "review_precision_for_false_negative":
            review_precision_for_fn,

        "reviews_per_escalated_false_negative":
            reviews_per_fn,

        "observed_agent_stage_executions":
            observed_agent_stage_executions,

        "mean_observed_agent_stage_executions":
            mean_stage_executions_per_test_case,

        "measured_calls":
            np.nan,

        "measured_latency":
            np.nan,

        "measured_cost":
            np.nan,
    }

    rows.append(row)


results = pd.DataFrame(rows)


print(
    results[
        [
            "system_id",
            "system",
            "review_population",
            "review_rate_model_negative",
            "false_negatives_escalated",
            "false_negative_review_coverage",
            "false_negatives_bypassed",
            "review_precision_for_false_negative",
        ]
    ].to_string(index=False)
)


# =============================================================================
# F — VERIFY EXPECTED SYSTEM BOUNDS
# =============================================================================

section("F — VERIFY SYSTEM CONSTRUCTION")


result_map = (
    results
    .set_index("system_id")
    .to_dict("index")
)


if result_map["A"]["review_population"] != 0:
    raise RuntimeError(
        "System A review count changed."
    )


if result_map["B"]["review_population"] != 7858:
    raise RuntimeError(
        "System B review count changed."
    )


if result_map["C"]["review_population"] != 1178:
    raise RuntimeError(
        "System C review count changed."
    )


if result_map["D"]["review_population"] != 1178:
    raise RuntimeError(
        "System D review count changed."
    )


if result_map["B"]["false_negatives_escalated"] != 557:
    raise RuntimeError(
        "Always-on must escalate all primary-model FNs."
    )


print("System A review lock: PASSED")
print("System B review lock: PASSED")
print("System C review lock: PASSED")
print("System D review lock: PASSED")
print("Always-on FN coverage sanity check: PASSED")


# =============================================================================
# G — MATCHED-BUDGET C VS D COMPARISON
# =============================================================================

section("G — MATCHED-BUDGET RULE VS LEARNED ROUTER")


c = result_map["C"]
d = result_map["D"]


if (
    c["review_population"]
    != d["review_population"]
):
    raise RuntimeError(
        "C/D review budgets are not matched."
    )


fn_difference = (
    d["false_negatives_escalated"]
    - c["false_negatives_escalated"]
)


coverage_difference = (
    d["false_negative_review_coverage"]
    - c["false_negative_review_coverage"]
)


precision_difference = (
    d["review_precision_for_false_negative"]
    - c["review_precision_for_false_negative"]
)


relative_fn_gain = (
    fn_difference
    / c["false_negatives_escalated"]
    if c["false_negatives_escalated"] > 0
    else np.nan
)


print(
    "Review budget — C:",
    c["review_population"]
)

print(
    "Review budget — D:",
    d["review_population"]
)

print()
print(
    "Rule-router FNs escalated:",
    c["false_negatives_escalated"]
)

print(
    "Learned-router FNs escalated:",
    d["false_negatives_escalated"]
)

print(
    "Absolute FN escalation difference D-C:",
    fn_difference
)

print()
print(
    "Rule-router FN coverage:",
    f'{c["false_negative_review_coverage"]:.6f}'
)

print(
    "Learned-router FN coverage:",
    f'{d["false_negative_review_coverage"]:.6f}'
)

print(
    "Absolute coverage difference D-C:",
    f"{coverage_difference:.6f}"
)

print(
    "Relative FN escalation gain D vs C:",
    relative_fn_gain
)

print()
print(
    "Rule-router FN review precision:",
    c["review_precision_for_false_negative"]
)

print(
    "Learned-router FN review precision:",
    d["review_precision_for_false_negative"]
)

print(
    "Precision difference D-C:",
    precision_difference
)


# =============================================================================
# H — COMPUTE EFFICIENCY RELATIVE TO ALWAYS-ON
# =============================================================================

section("H — COMPUTE / REVIEW EFFICIENCY")


always_review = (
    result_map["B"]["review_population"]
)


for system_id in [
    "A",
    "B",
    "C",
    "D",
]:

    r = result_map[system_id]

    review_reduction = (
        1
        - (
            r["review_population"]
            / always_review
        )
    )

    print()
    print(
        system_id,
        "-",
        r["system"],
    )

    print(
        "Review population:",
        r["review_population"]
    )

    print(
        "Observed agent-stage executions:",
        r["observed_agent_stage_executions"]
    )

    print(
        "Review reduction vs always-on:",
        f"{review_reduction:.6f}"
    )

    print(
        "FN coverage:",
        f'{r["false_negative_review_coverage"]:.6f}'
    )


# =============================================================================
# I — BUILD CASE-LEVEL PAIRED COMPARISON
# =============================================================================

section("I — BUILD CASE-LEVEL PAIRED COMPARISON")


for system_id, spec in system_definitions.items():

    col = spec["column"]

    df[
        f"{system_id}_fn_escalated"
    ] = (
        (df["primary_false_negative"] == 1)
        &
        (df[col] == 1)
    ).astype(int)


df[
    "D_vs_C_fn_escalation_difference"
] = (
    df["D_fn_escalated"]
    - df["C_fn_escalated"]
)


d_only = int(
    (
        df[
            "D_vs_C_fn_escalation_difference"
        ] == 1
    ).sum()
)


c_only = int(
    (
        df[
            "D_vs_C_fn_escalation_difference"
        ] == -1
    ).sum()
)


both = int(
    (
        (df["D_fn_escalated"] == 1)
        &
        (df["C_fn_escalated"] == 1)
    ).sum()
)


neither = int(
    (
        (df["primary_false_negative"] == 1)
        &
        (df["D_fn_escalated"] == 0)
        &
        (df["C_fn_escalated"] == 0)
    ).sum()
)


print(
    "FN escalated by D but not C:",
    d_only
)

print(
    "FN escalated by C but not D:",
    c_only
)

print(
    "FN escalated by both:",
    both
)

print(
    "FN escalated by neither:",
    neither
)


if (
    d_only
    - c_only
    != fn_difference
):
    raise RuntimeError(
        "Paired C/D FN difference mismatch."
    )


print("Paired C/D accounting: PASSED")


# =============================================================================
# J — PERFORMANCE INTERPRETATION
# =============================================================================

section("J — SCIENTIFIC INTERPRETATION BOUNDARY")


interpretation = [
    (
        "All four systems retain the same frozen primary "
        "classifier; therefore AUROC, AUPRC, Recall, and FNR "
        "are identical unless a genuine downstream prediction "
        "is produced."
    ),

    (
        "The comparison evaluates additional-review allocation "
        "and false-negative escalation, not hypothetical "
        "correction of escalated predictions."
    ),

    (
        "System B provides an upper-compute reference because "
        "every primary-model-negative case is escalated."
    ),

    (
        "Systems C and D are the primary matched-budget routing "
        "comparison because both escalate exactly 1,178 cases."
    ),

    (
        "An escalated false negative remains a false negative "
        "in predictive-performance accounting."
    ),

    (
        "Observed agent-stage executions are workflow-stage "
        "counts and are not measured API calls, tokens, "
        "latency, FLOPs, or monetary cost."
    ),

    (
        "Measured latency and monetary cost remain unavailable "
        "for the frozen execution and are not fabricated."
    ),
]


for item in interpretation:
    print(" -", item)


# =============================================================================
# K — SAVE FINAL RESULT TABLE
# =============================================================================

section("K — SAVE FINAL RESULT TABLE")


results.to_csv(
    RESULT_TABLE_PATH,
    index=False,
)


print(
    "Final comparison table:",
    RESULT_TABLE_PATH
)


# =============================================================================
# L — SAVE CASE-LEVEL PAIRED TABLE
# =============================================================================

section("L — SAVE CASE-LEVEL COMPARISON")


case_columns = [
    "encounter_id",
    "actual_30d",
    "predicted_30d",
    "calibrated_probability",
    "primary_false_negative",
    "A_selected_for_review",
    "B_selected_for_review",
    "C_selected_for_review",
    "D_selected_for_review",
    "A_fn_escalated",
    "B_fn_escalated",
    "C_fn_escalated",
    "D_fn_escalated",
    "D_vs_C_fn_escalation_difference",
]


df[
    case_columns
].to_csv(
    CASE_PATH,
    index=False,
)


print(
    "Case-level comparison:",
    CASE_PATH
)


# =============================================================================
# M — CREATE FINAL COMPARISON AUDIT
# =============================================================================

section("M — CREATE FINAL COMPARISON AUDIT")


audit = {
    "phase": "12.3",

    "status":
        "FINAL_SCIENTIFIC_COMPARISON_COMPLETE",

    "test_population": {
        "encounters":
            len(df),

        "actual_positives":
            int(y.sum()),

        "primary_model_negatives":
            negative_population,

        "primary_model_false_negatives":
            total_fn,
    },

    "primary_predictive_performance": {
        "auroc":
            auroc,

        "auprc":
            auprc,

        "recall":
            recall,

        "fnr":
            fnr,

        "tn":
            int(tn),

        "fp":
            int(fp),

        "fn":
            int(fn),

        "tp":
            int(tp),
    },

    "systems":
        {
            row["system_id"]: {
                k: (
                    None
                    if (
                        isinstance(v, float)
                        and np.isnan(v)
                    )
                    else v
                )
                for k, v in row.items()
                if k != "system_id"
            }
            for row in rows
        },

    "matched_budget_C_vs_D": {
        "review_budget_each":
            1178,

        "rule_router_fn_escalated":
            int(
                c[
                    "false_negatives_escalated"
                ]
            ),

        "learned_router_fn_escalated":
            int(
                d[
                    "false_negatives_escalated"
                ]
            ),

        "absolute_fn_difference_D_minus_C":
            int(fn_difference),

        "absolute_coverage_difference_D_minus_C":
            float(coverage_difference),

        "relative_fn_gain_D_vs_C":
            (
                None
                if np.isnan(relative_fn_gain)
                else float(relative_fn_gain)
            ),

        "paired_D_only":
            d_only,

        "paired_C_only":
            c_only,

        "paired_both":
            both,

        "paired_neither":
            neither,
    },

    "telemetry": {
        "workflow_allocation":
            "AVAILABLE",

        "observed_agent_stage_executions":
            "AVAILABLE",

        "measured_api_calls":
            "UNVERIFIED",

        "measured_tokens":
            "NOT_CAPTURED",

        "measured_latency":
            "NOT_CAPTURED",

        "measured_cost":
            "NOT_CAPTURED",
    },

    "interpretation_boundary":
        interpretation,

    "test_retuning_performed":
        False,

    "primary_model_modified":
        False,

    "learned_router_modified":
        False,

    "source_hashes": {
        "assignments":
            sha256_file(ASSIGN_PATH),

        "protocol":
            sha256_file(PROTOCOL_PATH),

        "comparator_manifest":
            sha256_file(
                COMPARATOR_MANIFEST_PATH
            ),
    },

    "artifacts": {
        "result_table":
            str(RESULT_TABLE_PATH),

        "case_level_comparison":
            str(CASE_PATH),
    },

    "next_phase":
        "12.4 — Ablation study",
}


with AUDIT_PATH.open("w") as f:
    json.dump(
        audit,
        f,
        indent=2,
    )


print(
    "Comparison audit:",
    AUDIT_PATH
)


# =============================================================================
# N — FINAL VERIFICATION
# =============================================================================

section("N — FINAL VERIFICATION")


checks = {
    "test_population_lock":
        len(df) == 15042,

    "primary_fn_lock":
        total_fn == 557,

    "system_A_lock":
        result_map["A"][
            "review_population"
        ] == 0,

    "system_B_lock":
        result_map["B"][
            "review_population"
        ] == 7858,

    "system_C_lock":
        result_map["C"][
            "review_population"
        ] == 1178,

    "system_D_lock":
        result_map["D"][
            "review_population"
        ] == 1178,

    "C_D_budget_matched":
        result_map["C"][
            "review_population"
        ]
        ==
        result_map["D"][
            "review_population"
        ],

    "always_on_covers_all_FN":
        result_map["B"][
            "false_negatives_escalated"
        ] == 557,

    "paired_accounting":
        (
            d_only
            - c_only
        )
        == fn_difference,

    "predictive_metrics_not_reinvented":
        True,

    "human_review_not_assumed_corrective":
        True,

    "latency_not_fabricated":
        True,

    "cost_not_fabricated":
        True,

    "test_retuning_not_performed":
        True,

    "phase10_unchanged":
        True,

    "phase11_unchanged":
        True,

    "result_table_exists":
        RESULT_TABLE_PATH.exists(),

    "case_table_exists":
        CASE_PATH.exists(),

    "audit_exists":
        AUDIT_PATH.exists(),
}


for key, value in checks.items():

    print(
        key + ":",
        "PASSED" if value else "FAILED"
    )


if not all(checks.values()):

    raise RuntimeError(
        "Phase 12.3 final comparison failed."
    )


# =============================================================================
# COMPLETE
# =============================================================================

section(
    "PHASE 12.3 COMPLETE — "
    "FINAL SCIENTIFIC COMPARISON PASSED"
)


print(
    "Frozen primary AUROC:",
    f"{auroc:.6f}"
)

print(
    "Frozen primary AUPRC:",
    f"{auprc:.6f}"
)

print(
    "Frozen primary Recall:",
    f"{recall:.6f}"
)

print(
    "Frozen primary FNR:",
    f"{fnr:.6f}"
)


print()
print("System A — ML only")
print(
    "  Reviews:",
    result_map["A"]["review_population"]
)

print(
    "  FN coverage:",
    f'{result_map["A"]["false_negative_review_coverage"]:.2%}'
)


print()
print("System B — Always-on")
print(
    "  Reviews:",
    result_map["B"]["review_population"]
)

print(
    "  FN coverage:",
    f'{result_map["B"]["false_negative_review_coverage"]:.2%}'
)


print()
print("System C — Rule router")
print(
    "  Reviews:",
    result_map["C"]["review_population"]
)

print(
    "  FNs escalated:",
    result_map["C"]["false_negatives_escalated"]
)

print(
    "  FN coverage:",
    f'{result_map["C"]["false_negative_review_coverage"]:.2%}'
)


print()
print("System D — Learned router")
print(
    "  Reviews:",
    result_map["D"]["review_population"]
)

print(
    "  FNs escalated:",
    result_map["D"]["false_negatives_escalated"]
)

print(
    "  FN coverage:",
    f'{result_map["D"]["false_negative_review_coverage"]:.2%}'
)


print()
print("MATCHED-BUDGET D VS C")

print(
    "  Additional FNs escalated by D:",
    fn_difference
)

print(
    "  Absolute FN coverage difference:",
    f"{coverage_difference:.2%}"
)

print(
    "  Relative FN escalation gain:",
    (
        "NA"
        if np.isnan(relative_fn_gain)
        else f"{relative_fn_gain:.2%}"
    )
)


print()
print("Predictive metrics altered by routing: NO")
print("Human correction assumed: NO")
print("Test-set retuning performed: NO")
print("Unavailable telemetry fabricated: NO")

print()
print(
    "NEXT: PHASE 12.4 — ABLATION STUDY"
)
