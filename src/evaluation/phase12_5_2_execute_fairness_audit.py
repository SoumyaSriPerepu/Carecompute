from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd


print("=" * 80)
print("PHASE 12.5.2 — EXECUTE FINAL SUBGROUP SAFETY/FAIRNESS AUDIT")
print("=" * 80)


# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------

PREDICTIONS_PATH = Path(
    "results/eligible/final_test_router_predictions.csv"
)

PROTOCOL_PATH = Path(
    "results/eligible/final_comparison/"
    "phase12_5_1_fairness_protocol.json"
)

OUT_DIR = Path(
    "results/eligible/final_comparison"
)

SUBGROUP_PATH = (
    OUT_DIR /
    "phase12_5_2_subgroup_fairness_results.csv"
)

GAP_PATH = (
    OUT_DIR /
    "phase12_5_2_fairness_gap_summary.csv"
)

AUDIT_PATH = (
    OUT_DIR /
    "phase12_5_2_fairness_execution_audit.json"
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
# A — LOAD FROZEN PROTOCOL
# ---------------------------------------------------------------------

section("A — LOAD FROZEN FAIRNESS PROTOCOL")

if not PROTOCOL_PATH.exists():
    raise FileNotFoundError(PROTOCOL_PATH)

with open(PROTOCOL_PATH) as f:
    protocol = json.load(f)

if protocol["status"] != \
        "FINAL_FAIRNESS_PROTOCOL_FROZEN":

    raise RuntimeError(
        "Phase 12.5.1 protocol is not frozen."
    )

min_population = int(
    protocol["support_rules"][
        "minimum_group_population"
    ]
)

min_fn = int(
    protocol["support_rules"][
        "minimum_group_false_negatives"
    ]
)

print("Protocol:", protocol["status"])
print("Minimum population:", min_population)
print("Minimum FNs:", min_fn)

print("Protocol load: PASSED")


# ---------------------------------------------------------------------
# B — VERIFY SOURCE INTEGRITY
# ---------------------------------------------------------------------

section("B — VERIFY FROZEN SOURCE INTEGRITY")

current_hash = sha256(
    PREDICTIONS_PATH
)

expected_hash = protocol[
    "source_hashes"
][str(PREDICTIONS_PATH)]

print(
    "Prediction hash match:",
    current_hash == expected_hash
)

if current_hash != expected_hash:
    raise RuntimeError(
        "Final router predictions changed "
        "after fairness protocol freeze."
    )

print("Source integrity: PASSED")


# ---------------------------------------------------------------------
# C — LOAD FINAL ROUTING POPULATION
# ---------------------------------------------------------------------

section("C — LOAD FINAL ROUTING POPULATION")

df = pd.read_csv(
    PREDICTIONS_PATH
)

if len(df) != 7858:
    raise RuntimeError(
        "Expected 7,858 cases."
    )

if int(df["actual_30d"].sum()) != 557:
    raise RuntimeError(
        "Expected 557 primary false negatives."
    )

if int(
    df["selected_for_review"].sum()
) != 1178:
    raise RuntimeError(
        "Expected 1,178 reviewed cases."
    )

selected_fn = int(
    (
        (df["actual_30d"] == 1) &
        (df["selected_for_review"] == 1)
    ).sum()
)

if selected_fn != 110:
    raise RuntimeError(
        "Expected 110 escalated false negatives."
    )

print("Cases:", len(df))
print("Primary FNs:", 557)
print("Reviews:", 1178)
print("FNs escalated:", selected_fn)

print("Population lock: PASSED")


# ---------------------------------------------------------------------
# D — NORMALIZE MISSING AUDIT LABELS
# ---------------------------------------------------------------------

section("D — NORMALIZE MISSING AUDIT LABELS")

audit_df = df.copy()

attributes = [
    "gender",
    "race",
    "age",
]

for attribute in attributes:

    audit_df[attribute] = (
        audit_df[attribute]
        .astype("object")
        .where(
            audit_df[attribute].notna(),
            "MISSING"
        )
        .astype(str)
    )

    print()
    print(attribute.upper())

    print(
        audit_df[attribute]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

print()
print(
    "Missing demographic values retained as "
    "explicit MISSING audit groups."
)


# ---------------------------------------------------------------------
# E — CALCULATE SUBGROUP METRICS
# ---------------------------------------------------------------------

section("E — CALCULATE SUBGROUP METRICS")

records = []

for attribute in attributes:

    groups = sorted(
        audit_df[attribute].unique()
    )

    for group in groups:

        g = audit_df[
            audit_df[attribute] == group
        ]

        population = len(g)

        reviews = int(
            g["selected_for_review"].sum()
        )

        review_rate = (
            reviews / population
            if population > 0
            else np.nan
        )

        false_negatives = int(
            g["actual_30d"].sum()
        )

        fn_escalated = int(
            (
                (g["actual_30d"] == 1) &
                (g["selected_for_review"] == 1)
            ).sum()
        )

        fn_capture_rate = (
            fn_escalated / false_negatives
            if false_negatives > 0
            else np.nan
        )

        review_precision = (
            fn_escalated / reviews
            if reviews > 0
            else np.nan
        )

        review_rate_support = (
            population >= min_population
        )

        fn_capture_support = (
            false_negatives >= min_fn
        )

        if (
            review_rate_support and
            fn_capture_support
        ):
            support_status = "ADEQUATE"

        else:
            support_status = "LOW_SUPPORT"

        records.append({
            "attribute":
                attribute,

            "group":
                group,

            "group_population":
                population,

            "reviews":
                reviews,

            "group_review_rate":
                review_rate,

            "group_false_negatives":
                false_negatives,

            "group_false_negatives_escalated":
                fn_escalated,

            "group_fn_capture_rate":
                fn_capture_rate,

            "group_review_precision_for_fn":
                review_precision,

            "adequate_for_review_rate_comparison":
                review_rate_support,

            "adequate_for_fn_capture_comparison":
                fn_capture_support,

            "support_status":
                support_status,
        })


subgroups = pd.DataFrame(records)

for attribute in attributes:

    print()
    print("-" * 80)
    print(attribute.upper())
    print("-" * 80)

    display = subgroups[
        subgroups["attribute"] == attribute
    ].copy()

    print(
        display[
            [
                "group",
                "group_population",
                "reviews",
                "group_review_rate",
                "group_false_negatives",
                "group_false_negatives_escalated",
                "group_fn_capture_rate",
                "group_review_precision_for_fn",
                "support_status",
            ]
        ].to_string(
            index=False
        )
    )


# ---------------------------------------------------------------------
# F — VERIFY SUBGROUP ACCOUNTING
# ---------------------------------------------------------------------

section("F — VERIFY SUBGROUP ACCOUNTING")

for attribute in attributes:

    part = subgroups[
        subgroups["attribute"] == attribute
    ]

    population_sum = int(
        part["group_population"].sum()
    )

    review_sum = int(
        part["reviews"].sum()
    )

    fn_sum = int(
        part["group_false_negatives"].sum()
    )

    fn_escalated_sum = int(
        part[
            "group_false_negatives_escalated"
        ].sum()
    )

    print()
    print(attribute.upper())

    print(" Population:", population_sum)
    print(" Reviews:", review_sum)
    print(" FNs:", fn_sum)
    print(" FNs escalated:", fn_escalated_sum)

    if population_sum != 7858:
        raise RuntimeError(
            f"{attribute}: population accounting failed."
        )

    if review_sum != 1178:
        raise RuntimeError(
            f"{attribute}: review accounting failed."
        )

    if fn_sum != 557:
        raise RuntimeError(
            f"{attribute}: FN accounting failed."
        )

    if fn_escalated_sum != 110:
        raise RuntimeError(
            f"{attribute}: escalated-FN accounting failed."
        )

print()
print("Subgroup accounting: PASSED")


# ---------------------------------------------------------------------
# G — COMPUTE SUPPORTED MAX-MIN GAPS
# ---------------------------------------------------------------------

section("G — COMPUTE SUPPORTED FAIRNESS GAPS")

gap_records = []

for attribute in attributes:

    part = subgroups[
        subgroups["attribute"] == attribute
    ].copy()

    review_supported = part[
        part[
            "adequate_for_review_rate_comparison"
        ]
    ].copy()

    fn_supported = part[
        part[
            "adequate_for_fn_capture_comparison"
        ]
    ].copy()

    if len(review_supported) >= 2:

        review_max_idx = (
            review_supported[
                "group_review_rate"
            ].idxmax()
        )

        review_min_idx = (
            review_supported[
                "group_review_rate"
            ].idxmin()
        )

        review_max_group = (
            review_supported.loc[
                review_max_idx,
                "group"
            ]
        )

        review_min_group = (
            review_supported.loc[
                review_min_idx,
                "group"
            ]
        )

        review_max = float(
            review_supported.loc[
                review_max_idx,
                "group_review_rate"
            ]
        )

        review_min = float(
            review_supported.loc[
                review_min_idx,
                "group_review_rate"
            ]
        )

        review_gap = (
            review_max - review_min
        )

    else:

        review_max_group = None
        review_min_group = None
        review_max = np.nan
        review_min = np.nan
        review_gap = np.nan

    if len(fn_supported) >= 2:

        fn_max_idx = (
            fn_supported[
                "group_fn_capture_rate"
            ].idxmax()
        )

        fn_min_idx = (
            fn_supported[
                "group_fn_capture_rate"
            ].idxmin()
        )

        fn_max_group = (
            fn_supported.loc[
                fn_max_idx,
                "group"
            ]
        )

        fn_min_group = (
            fn_supported.loc[
                fn_min_idx,
                "group"
            ]
        )

        fn_max = float(
            fn_supported.loc[
                fn_max_idx,
                "group_fn_capture_rate"
            ]
        )

        fn_min = float(
            fn_supported.loc[
                fn_min_idx,
                "group_fn_capture_rate"
            ]
        )

        fn_gap = (
            fn_max - fn_min
        )

    else:

        fn_max_group = None
        fn_min_group = None
        fn_max = np.nan
        fn_min = np.nan
        fn_gap = np.nan

    gap_records.append({
        "attribute":
            attribute,

        "review_supported_groups":
            len(review_supported),

        "review_rate_max_group":
            review_max_group,

        "review_rate_max":
            review_max,

        "review_rate_min_group":
            review_min_group,

        "review_rate_min":
            review_min,

        "review_rate_gap":
            review_gap,

        "fn_supported_groups":
            len(fn_supported),

        "fn_capture_max_group":
            fn_max_group,

        "fn_capture_max":
            fn_max,

        "fn_capture_min_group":
            fn_min_group,

        "fn_capture_min":
            fn_min,

        "fn_capture_gap":
            fn_gap,
    })


gaps = pd.DataFrame(
    gap_records
)

print(
    gaps.to_string(
        index=False
    )
)


# ---------------------------------------------------------------------
# H — LOW-SUPPORT DISCLOSURE
# ---------------------------------------------------------------------

section("H — LOW-SUPPORT DISCLOSURE")

for attribute in attributes:

    part = subgroups[
        subgroups["attribute"] == attribute
    ]

    low = part[
        part["support_status"]
        == "LOW_SUPPORT"
    ]

    print()
    print(attribute.upper())

    if len(low) == 0:

        print(
            " No LOW_SUPPORT groups."
        )

    else:

        print(
            low[
                [
                    "group",
                    "group_population",
                    "group_false_negatives",
                    "adequate_for_review_rate_comparison",
                    "adequate_for_fn_capture_comparison",
                ]
            ].to_string(
                index=False
            )
        )


# ---------------------------------------------------------------------
# I — SCIENTIFIC INTERPRETATION BOUNDARY
# ---------------------------------------------------------------------

section("I — SCIENTIFIC INTERPRETATION BOUNDARY")

boundaries = [
    (
        "Demographics were not used to generate "
        "routing assignments."
    ),

    (
        "All subgroup metrics are post-routing "
        "descriptive audits."
    ),

    (
        "Max-min gaps exclude groups that fail the "
        "predeclared support criterion for that metric."
    ),

    (
        "Observed differences are safety/fairness "
        "signals requiring disclosure, not proof of "
        "causal discrimination."
    ),

    (
        "No subgroup result is used to alter the "
        "frozen System D."
    ),

    (
        "Escalated false negatives remain false "
        "negatives in predictive-performance accounting."
    ),
]

for boundary in boundaries:
    print(" -", boundary)


# ---------------------------------------------------------------------
# J — SAVE SUBGROUP RESULTS
# ---------------------------------------------------------------------

section("J — SAVE SUBGROUP RESULTS")

subgroups.to_csv(
    SUBGROUP_PATH,
    index=False
)

print(
    "Saved:",
    SUBGROUP_PATH
)


# ---------------------------------------------------------------------
# K — SAVE GAP SUMMARY
# ---------------------------------------------------------------------

section("K — SAVE FAIRNESS GAP SUMMARY")

gaps.to_csv(
    GAP_PATH,
    index=False
)

print(
    "Saved:",
    GAP_PATH
)


# ---------------------------------------------------------------------
# L — CREATE EXECUTION AUDIT
# ---------------------------------------------------------------------

section("L — CREATE FAIRNESS EXECUTION AUDIT")

audit = {
    "phase": "12.5.2",

    "status":
        "FINAL_SUBGROUP_FAIRNESS_AUDIT_EXECUTED",

    "population": {
        "cases": 7858,
        "primary_false_negatives": 557,
        "reviews": 1178,
        "false_negatives_escalated": 110,
    },

    "attributes":
        attributes,

    "support_rules": {
        "minimum_group_population":
            min_population,

        "minimum_group_false_negatives":
            min_fn,
    },

    "gap_summary":
        gaps.to_dict(
            orient="records"
        ),

    "integrity": {
        "prediction_hash":
            current_hash,

        "demographics_used_for_routing":
            False,

        "subgroup_thresholds_created":
            False,

        "router_retrained":
            False,

        "router_retuned":
            False,

        "review_budget_changed":
            False,

        "primary_model_changed":
            False,

        "phase10_modified":
            False,

        "phase11_modified":
            False,

        "phase12_1_to_12_4_modified":
            False,
    },

    "next_phase":
        (
            "12.5.3 — Final safety/fairness "
            "interpretation and lock"
        ),
}

with open(
    AUDIT_PATH,
    "w"
) as f:

    json.dump(
        audit,
        f,
        indent=2
    )

print(
    "Saved:",
    AUDIT_PATH
)


# ---------------------------------------------------------------------
# M — FINAL VERIFICATION
# ---------------------------------------------------------------------

section("M — FINAL VERIFICATION")

checks = {
    "protocol_frozen":
        protocol["status"]
        == "FINAL_FAIRNESS_PROTOCOL_FROZEN",

    "prediction_hash_unchanged":
        current_hash == expected_hash,

    "population_lock":
        len(df) == 7858,

    "primary_fn_lock":
        int(
            df["actual_30d"].sum()
        ) == 557,

    "review_budget_lock":
        int(
            df["selected_for_review"].sum()
        ) == 1178,

    "system_D_fn_lock":
        selected_fn == 110,

    "three_attributes_audited":
        set(
            subgroups["attribute"].unique()
        ) == {
            "gender",
            "race",
            "age"
        },

    "subgroup_results_exist":
        SUBGROUP_PATH.exists(),

    "gap_summary_exists":
        GAP_PATH.exists(),

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
        "Phase 12.5.2 verification failed."
    )


print()
print("=" * 80)

print(
    "PHASE 12.5.2 COMPLETE — "
    "FINAL SUBGROUP SAFETY/FAIRNESS AUDIT EXECUTED"
)

print("=" * 80)

print()

for _, row in gaps.iterrows():

    print(
        row["attribute"].upper()
    )

    print(
        " Review-rate gap:",
        f"{row['review_rate_gap']:.2%}"
        if pd.notna(
            row["review_rate_gap"]
        )
        else "NA"
    )

    print(
        " FN-capture gap:",
        f"{row['fn_capture_gap']:.2%}"
        if pd.notna(
            row["fn_capture_gap"]
        )
        else "NA"
    )

    print()

print(
    "Demographics used for routing: NO"
)

print(
    "Subgroup retuning performed: NO"
)

print()
print(
    "NEXT: PHASE 12.5.3 — "
    "FINAL SAFETY/FAIRNESS INTERPRETATION AND LOCK"
)
