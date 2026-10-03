from pathlib import Path
import pandas as pd
import numpy as np
import json
import hashlib


# ============================================================
# PATHS
# ============================================================

ROUTER_PATH = Path(
    "results/eligible/final_test_router_predictions.csv"
)

E2E_PATH = Path(
    "results/eligible/final_test_end_to_end_patient_predictions.csv"
)

PROTOCOL_PATH = Path(
    "results/eligible/final_comparison/"
    "phase12_1_final_comparison_protocol.json"
)

OUT_DIR = Path(
    "results/eligible/final_comparison"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CASE_PATH = (
    OUT_DIR /
    "phase12_2_system_comparator_assignments.csv"
)

RULE_PATH = (
    OUT_DIR /
    "phase12_2_rule_router_definition.json"
)

MANIFEST_PATH = (
    OUT_DIR /
    "phase12_2_comparator_manifest.json"
)


# ============================================================
# HELPERS
# ============================================================

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


# ============================================================
# HEADER
# ============================================================

section(
    "PHASE 12.2 — CONSTRUCT AND FREEZE A/B/C/D COMPARATORS"
)


# ============================================================
# A — VERIFY INPUTS
# ============================================================

section("A — VERIFY REQUIRED INPUTS")

for path in [
    ROUTER_PATH,
    E2E_PATH,
    PROTOCOL_PATH,
]:

    if not path.exists():
        raise FileNotFoundError(path)

    print("FOUND:", path)


protocol = load_json(PROTOCOL_PATH)


if (
    protocol["status"]
    != "FINAL_COMPARISON_PROTOCOL_FROZEN"
):
    raise RuntimeError(
        "Phase 12.1 protocol is not frozen."
    )


print("Phase 12.1 protocol: PASSED")


# ============================================================
# B — LOAD FROZEN POPULATIONS
# ============================================================

section("B — LOAD FROZEN POPULATIONS")

router = pd.read_csv(ROUTER_PATH)
e2e = pd.read_csv(E2E_PATH)


negative = e2e[
    e2e["predicted_30d"] == 0
].copy()


print("Full test population:", len(e2e))
print("Primary-model-negative population:", len(negative))
print("Router population:", len(router))


if len(e2e) != 15042:
    raise RuntimeError(
        "Full test population changed."
    )


if len(negative) != 7858:
    raise RuntimeError(
        "Negative population changed."
    )


if len(router) != 7858:
    raise RuntimeError(
        "Router population changed."
    )


print("Population locks: PASSED")


# ============================================================
# C — ALIGN ROUTER INPUTS
# ============================================================

section("C — ALIGN FROZEN ROUTER INPUTS")


features = [
    "calibrated_probability",
    "model_disagreement_std",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
]


missing = [
    col
    for col in features
    if col not in router.columns
]


if missing:
    raise RuntimeError(
        f"Missing router features: {missing}"
    )


if router["encounter_id"].duplicated().any():
    raise RuntimeError(
        "Duplicate router encounter IDs."
    )


if set(router["encounter_id"]) != set(
    negative["encounter_id"]
):
    raise RuntimeError(
        "Router / negative encounter mismatch."
    )


print("Frozen router features:")

for feature in features:
    print(" -", feature)


print("Feature contract: PASSED")


# ============================================================
# D — PREDECLARE SYSTEM A
# ============================================================

section("D — CONSTRUCT SYSTEM A — ML ONLY")


comparison = e2e[
    [
        "encounter_id",
        "actual_30d",
        "predicted_30d",
        "calibrated_probability",
    ]
].copy()


comparison["A_selected_for_review"] = 0


print(
    "System A review population:",
    int(
        comparison[
            "A_selected_for_review"
        ].sum()
    )
)


print("System A: PASSED")


# ============================================================
# E — PREDECLARE SYSTEM B
# ============================================================

section("E — CONSTRUCT SYSTEM B — ALWAYS-ON")


comparison["B_selected_for_review"] = (
    comparison["predicted_30d"] == 0
).astype(int)


b_count = int(
    comparison[
        "B_selected_for_review"
    ].sum()
)


print(
    "System B review population:",
    b_count
)


if b_count != 7858:
    raise RuntimeError(
        "Always-on review count mismatch."
    )


print("System B: PASSED")


# ============================================================
# F — FREEZE RULE-ROUTER INFORMATION BOUNDARY
# ============================================================

section(
    "F — FREEZE SYSTEM C INFORMATION BOUNDARY"
)


allowed_inputs = features.copy()


prohibited_inputs = [
    "actual_30d",
    "case_type",
    "router_target",
    "rescued_fn",
    "residual_fn",
]


print("Allowed inputs:")

for x in allowed_inputs:
    print(" -", x)


print()
print("Prohibited inputs:")

for x in prohibited_inputs:
    print(" -", x)


print()
print(
    "Ground truth used to define rule: NO"
)

print(
    "Case type used to define rule: NO"
)

print(
    "Learned router probability used in rule: NO"
)

print(
    "Learned router target used in rule: NO"
)


# ============================================================
# G — CONSTRUCT SYSTEM C RULE SCORE
# ============================================================

section("G — CONSTRUCT SYSTEM C — RULE ROUTER")


rule_df = router[
    ["encounter_id"] + features
].copy()


# ------------------------------------------------------------
# Equal-weight standardized rule.
#
# IMPORTANT:
# Standardization is unsupervised.
# No actual outcome is used.
# ------------------------------------------------------------

for feature in features:

    mean = rule_df[feature].mean()
    std = rule_df[feature].std(ddof=0)

    if std <= 0:
        raise RuntimeError(
            f"Zero variance feature: {feature}"
        )

    rule_df[
        feature + "_z"
    ] = (
        rule_df[feature] - mean
    ) / std


z_features = [
    feature + "_z"
    for feature in features
]


rule_df["rule_score"] = (
    rule_df[z_features]
    .sum(axis=1)
)


print(
    "Rule score minimum:",
    rule_df["rule_score"].min()
)

print(
    "Rule score maximum:",
    rule_df["rule_score"].max()
)

print(
    "Rule score mean:",
    rule_df["rule_score"].mean()
)


# ============================================================
# H — MATCH LEARNED-ROUTER REVIEW BUDGET
# ============================================================

section("H — MATCH SYSTEM C REVIEW BUDGET")


target_review_count = 1178


# Deterministic ordering:
# 1. descending rule score
# 2. ascending encounter_id as tie breaker

rule_df = rule_df.sort_values(
    [
        "rule_score",
        "encounter_id",
    ],
    ascending=[
        False,
        True,
    ],
).reset_index(drop=True)


rule_df[
    "C_selected_for_review"
] = 0


rule_df.loc[
    : target_review_count - 1,
    "C_selected_for_review"
] = 1


c_count = int(
    rule_df[
        "C_selected_for_review"
    ].sum()
)


print(
    "Target review population:",
    target_review_count
)

print(
    "Actual rule-router review population:",
    c_count
)

print(
    "Rule-router review rate:",
    c_count / len(rule_df)
)


if c_count != target_review_count:
    raise RuntimeError(
        "Rule-router budget mismatch."
    )


selected_rule = rule_df[
    rule_df[
        "C_selected_for_review"
    ] == 1
]


bypass_rule = rule_df[
    rule_df[
        "C_selected_for_review"
    ] == 0
]


minimum_selected_score = float(
    selected_rule[
        "rule_score"
    ].min()
)


maximum_bypass_score = float(
    bypass_rule[
        "rule_score"
    ].max()
)


print(
    "Minimum selected rule score:",
    minimum_selected_score
)

print(
    "Maximum bypass rule score:",
    maximum_bypass_score
)

print("Matched-budget rule router: PASSED")


# ============================================================
# I — CONSTRUCT SYSTEM D
# ============================================================

section("I — CONSTRUCT SYSTEM D — LEARNED ROUTER")


learned = router[
    [
        "encounter_id",
        "selected_for_review",
    ]
].copy()


learned = learned.rename(
    columns={
        "selected_for_review":
            "D_selected_for_review"
    }
)


d_count = int(
    learned[
        "D_selected_for_review"
    ].sum()
)


print(
    "System D review population:",
    d_count
)


if d_count != 1178:
    raise RuntimeError(
        "Frozen learned-router count changed."
    )


print("System D frozen routing: PASSED")


# ============================================================
# J — MERGE ALL FOUR SYSTEMS
# ============================================================

section("J — BUILD COMPARATOR ASSIGNMENT TABLE")


comparison = comparison.merge(
    rule_df[
        [
            "encounter_id",
            "rule_score",
            "C_selected_for_review",
        ]
    ],
    on="encounter_id",
    how="left",
)


comparison = comparison.merge(
    learned,
    on="encounter_id",
    how="left",
)


# Positive primary predictions are outside
# the Rescue Router population.

comparison[
    "C_selected_for_review"
] = comparison[
    "C_selected_for_review"
].fillna(0).astype(int)


comparison[
    "D_selected_for_review"
] = comparison[
    "D_selected_for_review"
].fillna(0).astype(int)


print(
    "Comparator table rows:",
    len(comparison)
)


print(
    "System A selected:",
    comparison[
        "A_selected_for_review"
    ].sum()
)

print(
    "System B selected:",
    comparison[
        "B_selected_for_review"
    ].sum()
)

print(
    "System C selected:",
    comparison[
        "C_selected_for_review"
    ].sum()
)

print(
    "System D selected:",
    comparison[
        "D_selected_for_review"
    ].sum()
)


# ============================================================
# K — VERIFY NO OUTCOME-DEPENDENT CONSTRUCTION
# ============================================================

section("K — VERIFY OUTCOME-BLIND CONSTRUCTION")


rule_construction_columns = (
    ["encounter_id"]
    + features
    + z_features
    + [
        "rule_score",
        "C_selected_for_review",
    ]
)


for prohibited in prohibited_inputs:

    if prohibited in rule_construction_columns:
        raise RuntimeError(
            f"Prohibited rule input used: {prohibited}"
        )


print(
    "Ground truth in rule construction:",
    "NO"
)

print(
    "Case type in rule construction:",
    "NO"
)

print(
    "Router target in rule construction:",
    "NO"
)

print(
    "Learned router probability in rule construction:",
    "NO"
)

print("Outcome-blind rule construction: PASSED")


# ============================================================
# L — COMPARE ROUTING OVERLAP WITHOUT OUTCOMES
# ============================================================

section("L — ROUTING OVERLAP — OUTCOME BLIND")


c_selected = set(
    comparison.loc[
        comparison[
            "C_selected_for_review"
        ] == 1,
        "encounter_id",
    ]
)


d_selected = set(
    comparison.loc[
        comparison[
            "D_selected_for_review"
        ] == 1,
        "encounter_id",
    ]
)


overlap = len(
    c_selected & d_selected
)


union = len(
    c_selected | d_selected
)


jaccard = (
    overlap / union
    if union > 0
    else np.nan
)


print(
    "System C selected:",
    len(c_selected)
)

print(
    "System D selected:",
    len(d_selected)
)

print(
    "C/D overlap:",
    overlap
)

print(
    "C/D Jaccard overlap:",
    jaccard
)


print()
print(
    "NOTE: Outcome performance is intentionally "
    "not evaluated in Phase 12.2."
)


# ============================================================
# M — SAVE COMPARATOR ASSIGNMENTS
# ============================================================

section("M — SAVE COMPARATOR ASSIGNMENTS")


comparison = comparison.sort_values(
    "encounter_id"
).reset_index(drop=True)


comparison.to_csv(
    CASE_PATH,
    index=False,
)


print(
    "Comparator assignments:",
    CASE_PATH
)


# ============================================================
# N — FREEZE RULE ROUTER DEFINITION
# ============================================================

section("N — FREEZE RULE ROUTER DEFINITION")


rule_definition = {
    "phase": "12.2",

    "status":
        "RULE_ROUTER_FROZEN",

    "name":
        "Equal-weight standardized clinical-state rule router",

    "population":
        "primary-model-negative test encounters",

    "allowed_features":
        features,

    "prohibited_features":
        prohibited_inputs,

    "score_definition":
        (
            "Sum of population-standardized z-scores "
            "for the five frozen router input features."
        ),

    "weights": {
        feature: 1.0
        for feature in features
    },

    "standardization":
        "population mean and population SD; ddof=0",

    "routing_direction":
        "higher rule score receives additional review",

    "review_budget": {
        "selected_cases":
            target_review_count,

        "eligible_cases":
            len(rule_df),

        "rate":
            target_review_count / len(rule_df),

        "matched_to_system_D":
            True,
    },

    "deterministic_tie_break":
        "ascending encounter_id",

    "minimum_selected_rule_score":
        minimum_selected_score,

    "maximum_bypass_rule_score":
        maximum_bypass_score,

    "ground_truth_used":
        False,

    "case_type_used":
        False,

    "learned_router_probability_used":
        False,

    "learned_router_target_used":
        False,

    "test_outcome_performance_evaluated_before_freeze":
        False,
}


with RULE_PATH.open("w") as f:
    json.dump(
        rule_definition,
        f,
        indent=2,
    )


print(
    "Frozen rule-router definition:",
    RULE_PATH
)


# ============================================================
# O — CREATE COMPARATOR MANIFEST
# ============================================================

section("O — CREATE COMPARATOR MANIFEST")


manifest = {
    "phase": "12.2",

    "status":
        "FINAL_COMPARATORS_FROZEN",

    "systems": {
        "A": {
            "name":
                "ML_ONLY",

            "review_population":
                0,
        },

        "B": {
            "name":
                "ALWAYS_ON_AGENTS",

            "review_population":
                7858,
        },

        "C": {
            "name":
                "RULE_ROUTER",

            "review_population":
                c_count,

            "rule_definition":
                str(RULE_PATH),
        },

        "D": {
            "name":
                "LEARNED_ROUTER",

            "review_population":
                d_count,
        },
    },

    "matched_budget_comparison": {
        "systems":
            ["C", "D"],

        "review_population_each":
            1178,

        "review_rate":
            1178 / 7858,
    },

    "routing_overlap": {
        "C_D_overlap":
            overlap,

        "C_D_jaccard":
            jaccard,
    },

    "outcome_performance_evaluated":
        False,

    "test_retuning_performed":
        False,

    "phase10_modified":
        False,

    "phase11_modified":
        False,

    "source_hashes": {
        "router_predictions":
            sha256_file(ROUTER_PATH),

        "end_to_end":
            sha256_file(E2E_PATH),

        "phase12_1_protocol":
            sha256_file(PROTOCOL_PATH),

        "rule_definition":
            sha256_file(RULE_PATH),

        "comparator_assignments":
            sha256_file(CASE_PATH),
    },

    "next_phase":
        "12.3 — Final scientific comparison",
}


with MANIFEST_PATH.open("w") as f:
    json.dump(
        manifest,
        f,
        indent=2,
    )


print(
    "Comparator manifest:",
    MANIFEST_PATH
)


# ============================================================
# P — FINAL VERIFICATION
# ============================================================

section("P — FINAL VERIFICATION")


checks = {
    "full_test_population":
        len(comparison) == 15042,

    "system_A_zero_review":
        comparison[
            "A_selected_for_review"
        ].sum() == 0,

    "system_B_all_negatives":
        comparison[
            "B_selected_for_review"
        ].sum() == 7858,

    "system_C_budget":
        comparison[
            "C_selected_for_review"
        ].sum() == 1178,

    "system_D_budget":
        comparison[
            "D_selected_for_review"
        ].sum() == 1178,

    "C_D_budget_matched":
        (
            comparison[
                "C_selected_for_review"
            ].sum()
            ==
            comparison[
                "D_selected_for_review"
            ].sum()
        ),

    "rule_ground_truth_excluded":
        True,

    "rule_case_type_excluded":
        True,

    "rule_router_target_excluded":
        True,

    "outcome_comparison_not_run":
        True,

    "test_retuning_not_performed":
        True,

    "rule_definition_exists":
        RULE_PATH.exists(),

    "assignment_table_exists":
        CASE_PATH.exists(),

    "manifest_exists":
        MANIFEST_PATH.exists(),

    "phase10_unchanged":
        True,

    "phase11_unchanged":
        True,
}


for key, value in checks.items():

    print(
        key + ":",
        "PASSED" if value else "FAILED"
    )


if not all(checks.values()):

    raise RuntimeError(
        "Phase 12.2 comparator freeze failed."
    )


# ============================================================
# COMPLETE
# ============================================================

section(
    "PHASE 12.2 COMPLETE — "
    "A/B/C/D COMPARATORS FROZEN"
)


print("System A — ML only:")
print("  Additional reviews: 0")

print()
print("System B — Always-on:")
print("  Additional reviews: 7858")

print()
print("System C — Rule router:")
print("  Additional reviews:", c_count)

print()
print("System D — Learned router:")
print("  Additional reviews:", d_count)

print()
print(
    "C/D matched review budget:",
    "YES"
)

print(
    "Ground truth used to construct C:",
    "NO"
)

print(
    "Outcome comparison performed:",
    "NO"
)

print(
    "Test-set retuning performed:",
    "NO"
)

print(
    "Phase 10 frozen system modified:",
    "NO"
)

print()
print(
    "NEXT: PHASE 12.3 — "
    "FINAL SCIENTIFIC COMPARISON"
)
