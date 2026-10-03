from pathlib import Path
import json
import hashlib
import pandas as pd
import numpy as np


print("=" * 80)
print("PHASE 12.4.3 — ABLATION CONTRIBUTION ANALYSIS")
print("=" * 80)


# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------

OUT_DIR = Path("results/eligible/final_comparison")

PROTOCOL_PATH = (
    OUT_DIR / "phase12_4_1_ablation_protocol.json"
)

ASSIGNMENTS_PATH = (
    OUT_DIR / "phase12_4_2_ablation_assignments.csv"
)

RESULTS_PATH = (
    OUT_DIR / "phase12_4_2_ablation_results.csv"
)

EXECUTION_AUDIT_PATH = (
    OUT_DIR / "phase12_4_2_ablation_execution_audit.json"
)

OUTPUT_TABLE = (
    OUT_DIR / "phase12_4_3_component_contributions.csv"
)

OUTPUT_AUDIT = (
    OUT_DIR / "phase12_4_3_ablation_contribution_audit.json"
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


# ---------------------------------------------------------------------
# A — VERIFY REQUIRED INPUTS
# ---------------------------------------------------------------------

section("A — VERIFY FROZEN ABLATION INPUTS")

required = [
    PROTOCOL_PATH,
    ASSIGNMENTS_PATH,
    RESULTS_PATH,
    EXECUTION_AUDIT_PATH,
]

for path in required:

    if not path.exists():
        raise FileNotFoundError(path)

    print("FOUND:", path)

print("Ablation input presence: PASSED")


# ---------------------------------------------------------------------
# B — LOAD ABLATION RESULTS
# ---------------------------------------------------------------------

section("B — LOAD FROZEN ABLATION RESULTS")

results = pd.read_csv(RESULTS_PATH)

assignments = pd.read_csv(
    ASSIGNMENTS_PATH
)

with open(PROTOCOL_PATH) as f:
    protocol = json.load(f)

with open(EXECUTION_AUDIT_PATH) as f:
    execution_audit = json.load(f)

print("Result rows:", len(results))
print("Assignment rows:", len(assignments))

if len(results) != 6:
    raise RuntimeError(
        "Expected FULL + five ablations."
    )

if len(assignments) != 7858:
    raise RuntimeError(
        "Expected 7,858 case-level assignments."
    )

if protocol["status"] != "ABLATION_PROTOCOL_FROZEN":
    raise RuntimeError(
        "Ablation protocol is not frozen."
    )

if execution_audit["status"] != \
        "FROZEN_COMPONENT_ABLATIONS_EXECUTED":

    raise RuntimeError(
        "Phase 12.4.2 execution is not frozen."
    )

print("Frozen ablation load: PASSED")


# ---------------------------------------------------------------------
# C — VERIFY FULL ROUTER REFERENCE
# ---------------------------------------------------------------------

section("C — VERIFY FULL ROUTER REFERENCE")

full = results[
    results["variant"] == "FULL"
]

if len(full) != 1:
    raise RuntimeError(
        "Exactly one FULL row required."
    )

full = full.iloc[0]

full_reviews = int(
    full["review_population"]
)

full_fn = int(
    full["false_negatives_escalated"]
)

full_coverage = float(
    full["false_negative_review_coverage"]
)

full_precision = float(
    full["review_precision_for_false_negative"]
)

print("Reviews:", full_reviews)
print("FNs escalated:", full_fn)
print("FN coverage:", f"{full_coverage:.6f}")
print("FN review precision:", f"{full_precision:.6f}")

if full_reviews != 1178:
    raise RuntimeError(
        "Full-router review budget changed."
    )

if full_fn != 110:
    raise RuntimeError(
        "Full-router FN escalation changed."
    )

print("Full-router reference: PASSED")


# ---------------------------------------------------------------------
# D — DERIVE COMPONENT CONTRIBUTION
# ---------------------------------------------------------------------

section("D — DERIVE COMPONENT CONTRIBUTION")

ablated = results[
    results["variant"] != "FULL"
].copy()

ablated[
    "fn_difference_full_minus_ablation"
] = (
    full_fn -
    ablated["false_negatives_escalated"]
)

ablated[
    "coverage_difference_full_minus_ablation"
] = (
    full_coverage -
    ablated["false_negative_review_coverage"]
)

ablated[
    "precision_difference_full_minus_ablation"
] = (
    full_precision -
    ablated["review_precision_for_false_negative"]
)


def classify(row):

    difference = int(
        row["fn_difference_full_minus_ablation"]
    )

    if difference > 0:
        return "SUPPORTIVE"

    if difference == 0:
        return "NEUTRAL"

    return "NON_SUPPORTIVE_IN_ABLATION"


ablated["contribution_class"] = (
    ablated.apply(
        classify,
        axis=1
    )
)

ablated[
    "interpretation"
] = ablated.apply(
    lambda row:
        (
            "Removing this signal reduced false-negative "
            "escalation under the matched review budget."
            if row["contribution_class"] == "SUPPORTIVE"
            else
            (
                "Removing this signal produced no change in "
                "false-negative escalation under the matched "
                "review budget."
                if row["contribution_class"] == "NEUTRAL"
                else
                "Removing this signal increased false-negative "
                "escalation on the frozen final test set. This "
                "is reported descriptively and is not used for "
                "post-hoc router retuning."
            )
        ),
    axis=1
)

display_columns = [
    "variant",
    "removed_feature",
    "false_negatives_escalated",
    "false_negative_review_coverage",
    "review_precision_for_false_negative",
    "overlap_with_full_router",
    "jaccard_with_full_router",
    "fn_difference_full_minus_ablation",
    "coverage_difference_full_minus_ablation",
    "contribution_class",
]

print(
    ablated[
        display_columns
    ].to_string(index=False)
)


# ---------------------------------------------------------------------
# E — RANK SUPPORTIVE CONTRIBUTIONS
# ---------------------------------------------------------------------

section("E — RANK OBSERVED COMPONENT CONTRIBUTIONS")

ranking = ablated.sort_values(
    by=[
        "fn_difference_full_minus_ablation",
        "coverage_difference_full_minus_ablation",
    ],
    ascending=[False, False],
).copy()

ranking["contribution_rank"] = (
    np.arange(1, len(ranking) + 1)
)

for _, row in ranking.iterrows():

    print()
    print(
        f"Rank {int(row['contribution_rank'])}: "
        f"{row['removed_feature']}"
    )

    print(
        " FN difference full - ablation:",
        int(
            row[
                "fn_difference_full_minus_ablation"
            ]
        )
    )

    print(
        " Coverage difference:",
        f"{row['coverage_difference_full_minus_ablation']:.6f}"
    )

    print(
        " Classification:",
        row["contribution_class"]
    )


# ---------------------------------------------------------------------
# F — CASE-LEVEL ROUTING DISPLACEMENT
# ---------------------------------------------------------------------

section("F — CASE-LEVEL ROUTING DISPLACEMENT")

full_selected = (
    assignments["FULL_selected"] == 1
)

displacement_records = []

for _, row in ablated.iterrows():

    variant = row["variant"]

    selected_column = (
        f"{variant}_selected"
    )

    if selected_column not in assignments.columns:
        raise RuntimeError(
            f"Missing {selected_column}"
        )

    ablation_selected = (
        assignments[selected_column] == 1
    )

    full_only = int(
        (
            full_selected &
            ~ablation_selected
        ).sum()
    )

    ablation_only = int(
        (
            ~full_selected &
            ablation_selected
        ).sum()
    )

    both = int(
        (
            full_selected &
            ablation_selected
        ).sum()
    )

    neither = int(
        (
            ~full_selected &
            ~ablation_selected
        ).sum()
    )

    displaced = (
        full_only + ablation_only
    )

    if full_only != ablation_only:
        raise RuntimeError(
            f"{variant}: matched-budget displacement "
            "is asymmetric."
        )

    displacement_records.append({
        "variant": variant,
        "removed_feature":
            row["removed_feature"],

        "full_only_selected":
            full_only,

        "ablation_only_selected":
            ablation_only,

        "selected_by_both":
            both,

        "selected_by_neither":
            neither,

        "total_selection_status_changes":
            displaced,

        "replacement_pairs":
            full_only,
    })

    print()
    print(variant)
    print(" Full only:", full_only)
    print(" Ablation only:", ablation_only)
    print(" Both:", both)
    print(" Replacement pairs:", full_only)


displacement_df = pd.DataFrame(
    displacement_records
)


# ---------------------------------------------------------------------
# G — MERGE CONTRIBUTION AND DISPLACEMENT
# ---------------------------------------------------------------------

section("G — BUILD FINAL COMPONENT TABLE")

component_table = ranking.merge(
    displacement_df,
    on=[
        "variant",
        "removed_feature"
    ],
    how="left"
)

component_table = component_table[
    [
        "contribution_rank",
        "variant",
        "removed_feature",
        "review_population",
        "false_negatives_escalated",
        "false_negative_review_coverage",
        "review_precision_for_false_negative",
        "fn_difference_full_minus_ablation",
        "coverage_difference_full_minus_ablation",
        "precision_difference_full_minus_ablation",
        "overlap_with_full_router",
        "jaccard_with_full_router",
        "replacement_pairs",
        "total_selection_status_changes",
        "contribution_class",
        "interpretation",
    ]
]

print(
    component_table[
        [
            "contribution_rank",
            "removed_feature",
            "false_negatives_escalated",
            "fn_difference_full_minus_ablation",
            "replacement_pairs",
            "contribution_class",
        ]
    ].to_string(index=False)
)


# ---------------------------------------------------------------------
# H — PREDECLARE SCIENTIFIC INTERPRETATION
# ---------------------------------------------------------------------

section("H — SCIENTIFIC INTERPRETATION")

supportive = component_table[
    component_table["contribution_class"]
    == "SUPPORTIVE"
]

non_supportive = component_table[
    component_table["contribution_class"]
    == "NON_SUPPORTIVE_IN_ABLATION"
]

neutral = component_table[
    component_table["contribution_class"]
    == "NEUTRAL"
]

print(
    "Supportive components:",
    supportive["removed_feature"].tolist()
)

print(
    "Neutral components:",
    neutral["removed_feature"].tolist()
)

print(
    "Non-supportive under ablation:",
    non_supportive["removed_feature"].tolist()
)

print()
print(
    "IMPORTANT: These labels describe observed matched-budget "
    "routing behavior on the frozen final test set."
)

print(
    "They are not causal feature-importance claims and are not "
    "used to modify the frozen router."
)


# ---------------------------------------------------------------------
# I — SAVE COMPONENT TABLE
# ---------------------------------------------------------------------

section("I — SAVE COMPONENT CONTRIBUTION TABLE")

component_table.to_csv(
    OUTPUT_TABLE,
    index=False
)

print(
    "Saved:",
    OUTPUT_TABLE
)


# ---------------------------------------------------------------------
# J — CREATE CONTRIBUTION AUDIT
# ---------------------------------------------------------------------

section("J — CREATE CONTRIBUTION AUDIT")

audit = {
    "phase": "12.4.3",

    "status":
        "ABLATION_CONTRIBUTION_ANALYSIS_COMPLETE",

    "full_router_reference": {
        "reviews":
            full_reviews,

        "false_negatives_escalated":
            full_fn,

        "false_negative_review_coverage":
            full_coverage,

        "review_precision_for_false_negative":
            full_precision,
    },

    "classification_rule": {
        "SUPPORTIVE":
            (
                "Full router escalates more false negatives "
                "than the corresponding ablation."
            ),

        "NEUTRAL":
            (
                "Full router and ablation escalate the same "
                "number of false negatives."
            ),

        "NON_SUPPORTIVE_IN_ABLATION":
            (
                "Ablation escalates more false negatives than "
                "the full router on the frozen final test set."
            ),
    },

    "supportive_components":
        supportive["removed_feature"].tolist(),

    "neutral_components":
        neutral["removed_feature"].tolist(),

    "non_supportive_components":
        non_supportive["removed_feature"].tolist(),

    "scientific_boundary": [
        (
            "No ablation was fitted or tuned using "
            "final-test outcomes."
        ),
        (
            "Contribution classes are descriptive "
            "test-set ablation results."
        ),
        (
            "They do not establish causal clinical "
            "feature importance."
        ),
        (
            "Observed ablation improvements are not "
            "used to alter the frozen router."
        ),
        (
            "All comparisons retain the identical "
            "1,178-case review budget."
        ),
    ],

    "source_hashes": {
        str(PROTOCOL_PATH):
            sha256(PROTOCOL_PATH),

        str(ASSIGNMENTS_PATH):
            sha256(ASSIGNMENTS_PATH),

        str(RESULTS_PATH):
            sha256(RESULTS_PATH),

        str(EXECUTION_AUDIT_PATH):
            sha256(EXECUTION_AUDIT_PATH),
    },

    "integrity": {
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
    },

    "next_phase":
        "12.4.4 — Final ablation study lock",
}

with open(OUTPUT_AUDIT, "w") as f:
    json.dump(
        audit,
        f,
        indent=2
    )

print(
    "Saved:",
    OUTPUT_AUDIT
)


# ---------------------------------------------------------------------
# K — FINAL VERIFICATION
# ---------------------------------------------------------------------

section("K — FINAL VERIFICATION")

checks = {
    "six_variants_loaded":
        len(results) == 6,

    "five_ablations_analyzed":
        len(component_table) == 5,

    "full_review_budget_lock":
        full_reviews == 1178,

    "full_fn_lock":
        full_fn == 110,

    "all_review_budgets_matched":
        bool(
            (
                results["review_population"]
                == 1178
            ).all()
        ),

    "displacement_accounting":
        bool(
            (
                component_table[
                    "total_selection_status_changes"
                ]
                ==
                2 * component_table[
                    "replacement_pairs"
                ]
            ).all()
        ),

    "component_table_exists":
        OUTPUT_TABLE.exists(),

    "audit_exists":
        OUTPUT_AUDIT.exists(),
}

for name, passed in checks.items():

    print(
        f"{name}:",
        "PASSED" if passed else "FAILED"
    )

if not all(checks.values()):
    raise RuntimeError(
        "Phase 12.4.3 verification failed."
    )


print()
print("=" * 80)
print(
    "PHASE 12.4.3 COMPLETE — "
    "ABLATION CONTRIBUTION ANALYSIS PASSED"
)
print("=" * 80)

print()

print(
    component_table[
        [
            "removed_feature",
            "false_negatives_escalated",
            "false_negative_review_coverage",
            "fn_difference_full_minus_ablation",
            "contribution_class",
        ]
    ].to_string(index=False)
)

print()
print("Router modified: NO")
print("Post-hoc retuning performed: NO")
print("Review budget changed: NO")
print()

print(
    "NEXT: PHASE 12.4.4 — "
    "FINAL ABLATION STUDY LOCK"
)
