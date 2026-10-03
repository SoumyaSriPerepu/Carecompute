from pathlib import Path
import json
import hashlib
import pandas as pd
import numpy as np


print("=" * 80)
print("PHASE 12.5.3 — FINAL SAFETY/FAIRNESS INTERPRETATION AND LOCK")
print("=" * 80)


# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------

OUT_DIR = Path("results/eligible/final_comparison")

PROTOCOL_PATH = (
    OUT_DIR / "phase12_5_1_fairness_protocol.json"
)

SUBGROUP_PATH = (
    OUT_DIR / "phase12_5_2_subgroup_fairness_results.csv"
)

GAP_PATH = (
    OUT_DIR / "phase12_5_2_fairness_gap_summary.csv"
)

EXECUTION_AUDIT_PATH = (
    OUT_DIR / "phase12_5_2_fairness_execution_audit.json"
)

PHASE12_4_LOCK = (
    OUT_DIR / "phase12_4_final_ablation_lock.json"
)

FINAL_LOCK_PATH = (
    OUT_DIR / "phase12_5_final_safety_fairness_lock.json"
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


def get_group(df, attribute, group):
    row = df[
        (df["attribute"] == attribute) &
        (df["group"] == group)
    ]

    if len(row) != 1:
        raise RuntimeError(
            f"Expected one row for {attribute}/{group}"
        )

    return row.iloc[0]


# ---------------------------------------------------------------------
# A — VERIFY COMPLETE FAIRNESS CHAIN
# ---------------------------------------------------------------------

section("A — VERIFY COMPLETE PHASE 12.5 ARTIFACT CHAIN")

required = [
    PROTOCOL_PATH,
    SUBGROUP_PATH,
    GAP_PATH,
    EXECUTION_AUDIT_PATH,
    PHASE12_4_LOCK,
]

for path in required:

    if not path.exists():
        raise FileNotFoundError(path)

    print("FOUND:", path)

print("Phase 12.5 artifact chain: PASSED")


# ---------------------------------------------------------------------
# B — VERIFY FROZEN PHASE STATES
# ---------------------------------------------------------------------

section("B — VERIFY FROZEN PHASE STATES")

with open(PROTOCOL_PATH) as f:
    protocol = json.load(f)

with open(EXECUTION_AUDIT_PATH) as f:
    execution = json.load(f)

with open(PHASE12_4_LOCK) as f:
    phase12_4 = json.load(f)

print("12.4:", phase12_4["status"])
print("12.5.1:", protocol["status"])
print("12.5.2:", execution["status"])

if phase12_4["status"] != "ABLATION_STUDY_FROZEN":
    raise RuntimeError("Phase 12.4 lock invalid.")

if protocol["status"] != "FINAL_FAIRNESS_PROTOCOL_FROZEN":
    raise RuntimeError("Phase 12.5.1 lock invalid.")

if execution["status"] != \
        "FINAL_SUBGROUP_FAIRNESS_AUDIT_EXECUTED":
    raise RuntimeError("Phase 12.5.2 status invalid.")

print("Phase-state verification: PASSED")


# ---------------------------------------------------------------------
# C — LOAD FINAL RESULTS
# ---------------------------------------------------------------------

section("C — LOAD FINAL FAIRNESS RESULTS")

subgroups = pd.read_csv(
    SUBGROUP_PATH,
    keep_default_na=False
)

gaps = pd.read_csv(
    GAP_PATH
)

print("Subgroup rows:", len(subgroups))
print("Gap rows:", len(gaps))

print()
print(
    gaps[
        [
            "attribute",
            "review_rate_gap",
            "fn_capture_gap",
        ]
    ].to_string(index=False)
)

if set(gaps["attribute"]) != {
    "gender",
    "race",
    "age"
}:
    raise RuntimeError(
        "Expected gender, race, and age gap rows."
    )

print("Final fairness results loaded: PASSED")


# ---------------------------------------------------------------------
# D — VERIFY GLOBAL SYSTEM LOCK
# ---------------------------------------------------------------------

section("D — VERIFY GLOBAL SYSTEM LOCK")

population = execution["population"]

print("Cases:", population["cases"])
print(
    "Primary false negatives:",
    population["primary_false_negatives"]
)
print("Reviews:", population["reviews"])
print(
    "FNs escalated:",
    population["false_negatives_escalated"]
)

if population["cases"] != 7858:
    raise RuntimeError("Population lock failed.")

if population["primary_false_negatives"] != 557:
    raise RuntimeError("FN lock failed.")

if population["reviews"] != 1178:
    raise RuntimeError("Review budget lock failed.")

if population["false_negatives_escalated"] != 110:
    raise RuntimeError("Escalated-FN lock failed.")

print("Global system lock: PASSED")


# ---------------------------------------------------------------------
# E — LOCK GENDER FINDINGS
# ---------------------------------------------------------------------

section("E — LOCK GENDER FINDINGS")

female = get_group(
    subgroups,
    "gender",
    "Female"
)

male = get_group(
    subgroups,
    "gender",
    "Male"
)

gender_gap = gaps[
    gaps["attribute"] == "gender"
].iloc[0]

print(
    "Female review rate:",
    f"{float(female['group_review_rate']):.2%}"
)

print(
    "Male review rate:",
    f"{float(male['group_review_rate']):.2%}"
)

print(
    "Review-rate gap:",
    f"{float(gender_gap['review_rate_gap']):.2%}"
)

print()

print(
    "Female FN capture:",
    f"{float(female['group_fn_capture_rate']):.2%}"
)

print(
    "Male FN capture:",
    f"{float(male['group_fn_capture_rate']):.2%}"
)

print(
    "FN-capture gap:",
    f"{float(gender_gap['fn_capture_gap']):.2%}"
)

print()
print(
    "Interpretation: observed gender differences were "
    "small in this frozen audit."
)


# ---------------------------------------------------------------------
# F — LOCK RACE FINDINGS
# ---------------------------------------------------------------------

section("F — LOCK RACE FINDINGS")

race_gap = gaps[
    gaps["attribute"] == "race"
].iloc[0]

print(
    "Supported review-rate gap:",
    f"{float(race_gap['review_rate_gap']):.2%}"
)

print(
    "Supported FN-capture gap:",
    f"{float(race_gap['fn_capture_gap']):.2%}"
)

print()

race_rows = subgroups[
    subgroups["attribute"] == "race"
].copy()

print(
    race_rows[
        [
            "group",
            "group_population",
            "group_review_rate",
            "group_false_negatives",
            "group_false_negatives_escalated",
            "group_fn_capture_rate",
            "support_status",
        ]
    ].to_string(index=False)
)

missing_race = get_group(
    subgroups,
    "race",
    "MISSING"
)

caucasian = get_group(
    subgroups,
    "race",
    "Caucasian"
)

african_american = get_group(
    subgroups,
    "race",
    "AfricanAmerican"
)

print()
print(
    "IMPORTANT: the predeclared maximum FN-capture "
    "gap includes the MISSING-race audit group."
)

print(
    "MISSING race FNs:",
    int(missing_race["group_false_negatives"])
)

print(
    "MISSING race FNs escalated:",
    int(
        missing_race[
            "group_false_negatives_escalated"
        ]
    )
)

print(
    "MISSING race FN capture:",
    f"{float(missing_race['group_fn_capture_rate']):.2%}"
)

print()
print(
    "Caucasian FN capture:",
    f"{float(caucasian['group_fn_capture_rate']):.2%}"
)

print(
    "AfricanAmerican FN capture:",
    f"{float(african_american['group_fn_capture_rate']):.2%}"
)

print()
print(
    "Interpretation: race-associated routing differences "
    "require disclosure. The largest predeclared FN-capture "
    "gap is specifically a missingness-associated comparison "
    "because MISSING is not a demographic race category."
)


# ---------------------------------------------------------------------
# G — LOCK AGE FINDINGS
# ---------------------------------------------------------------------

section("G — LOCK AGE FINDINGS")

age_gap = gaps[
    gaps["attribute"] == "age"
].iloc[0]

print(
    "Supported review-rate gap:",
    f"{float(age_gap['review_rate_gap']):.2%}"
)

print(
    "Supported FN-capture gap:",
    f"{float(age_gap['fn_capture_gap']):.2%}"
)

age_rows = subgroups[
    subgroups["attribute"] == "age"
].copy()

print()
print(
    age_rows[
        [
            "group",
            "group_population",
            "group_review_rate",
            "group_false_negatives",
            "group_false_negatives_escalated",
            "group_fn_capture_rate",
            "support_status",
        ]
    ].to_string(index=False)
)

age_70_80 = get_group(
    subgroups,
    "age",
    "[70-80)"
)

age_90_100 = get_group(
    subgroups,
    "age",
    "[90-100)"
)

print()
print(
    "[70-80) FN capture:",
    f"{float(age_70_80['group_fn_capture_rate']):.2%}",
    "| FNs:",
    int(age_70_80["group_false_negatives"])
)

print(
    "[90-100) FN capture:",
    f"{float(age_90_100['group_fn_capture_rate']):.2%}",
    "| FNs:",
    int(age_90_100["group_false_negatives"])
)

print()
print(
    "Interpretation: age-associated allocation and FN-capture "
    "differences are present. The [90-100) FN denominator is "
    "11, which passes the frozen minimum but remains limited."
)


# ---------------------------------------------------------------------
# H — LOCK LOW-SUPPORT LIMITATIONS
# ---------------------------------------------------------------------

section("H — LOCK LOW-SUPPORT LIMITATIONS")

low_support = subgroups[
    subgroups["support_status"] == "LOW_SUPPORT"
].copy()

print(
    low_support[
        [
            "attribute",
            "group",
            "group_population",
            "group_false_negatives",
        ]
    ].to_string(index=False)
)

low_support_groups = [
    {
        "attribute": row["attribute"],
        "group": row["group"],
        "population": int(row["group_population"]),
        "false_negatives":
            int(row["group_false_negatives"]),
    }
    for _, row in low_support.iterrows()
]

print()
print(
    "Low-support subgroup estimates are disclosed but "
    "are not treated as supported FN-capture disparity estimates."
)


# ---------------------------------------------------------------------
# I — FINAL SAFETY CLASSIFICATION
# ---------------------------------------------------------------------

section("I — FINAL SAFETY CLASSIFICATION")

classification = (
    "SAFETY_FAIRNESS_SIGNALS_PRESENT"
)

print("Classification:", classification)

print()
print(
    "Reason 1: gender differences are small."
)

print(
    "Reason 2: race-associated review allocation and "
    "FN-capture differences are present."
)

print(
    "Reason 3: the largest race FN-capture gap is driven "
    "by the MISSING-race audit group and must be identified "
    "as a missingness-associated signal."
)

print(
    "Reason 4: age-associated review allocation and "
    "FN-capture differences are present."
)

print(
    "Reason 5: several subgroup estimates have limited "
    "support and require cautious interpretation."
)

print()
print(
    "This classification is a disclosure status, "
    "NOT a clinical safety certification and NOT a "
    "finding of unlawful discrimination."
)


# ---------------------------------------------------------------------
# J — FREEZE PUBLICATION-SAFE CONCLUSION
# ---------------------------------------------------------------------

section("J — FREEZE PUBLICATION-SAFE CONCLUSION")

conclusion = {
    "gender":
        (
            "Gender-stratified routing behavior was similar "
            "in the frozen final-test audit, with a 1.07 "
            "percentage-point review-rate gap and a 1.53 "
            "percentage-point false-negative capture gap."
        ),

    "race":
        (
            "Race-stratified auditing revealed differences in "
            "review allocation and false-negative capture. The "
            "predeclared supported maximum FN-capture gap was "
            "22.25 percentage points; however, its minimum was "
            "the MISSING-race group, so this maximum specifically "
            "reflects a missingness-associated comparison rather "
            "than a direct comparison between two observed race "
            "categories."
        ),

    "age":
        (
            "Age-stratified auditing revealed larger variation "
            "in review allocation and false-negative capture, "
            "with supported max-min gaps of 23.28 and 20.84 "
            "percentage points, respectively. Some age strata "
            "had limited false-negative counts, including 11 "
            "false negatives in the [90-100) group."
        ),

    "system_boundary":
        (
            "Demographic attributes were not router inputs, and "
            "no subgroup-specific thresholds, retraining, or "
            "post-hoc routing modifications were performed after "
            "observing these results."
        ),

    "safety_boundary":
        (
            "These subgroup differences are reported as "
            "descriptive safety/fairness signals and do not "
            "constitute causal discrimination findings, "
            "demographic-parity certification, equalized-odds "
            "certification, or clinical safety certification."
        ),
}

for key, text in conclusion.items():
    print()
    print(key + ":")
    print(text)


# ---------------------------------------------------------------------
# K — CAPTURE ARTIFACT HASHES
# ---------------------------------------------------------------------

section("K — CAPTURE FINAL FAIRNESS ARTIFACT HASHES")

artifact_hashes = {}

for path in required:

    digest = sha256(path)

    artifact_hashes[str(path)] = digest

    print(
        path.name,
        "->",
        digest
    )

print("Artifact hashes captured: PASSED")


# ---------------------------------------------------------------------
# L — CREATE FINAL FAIRNESS LOCK
# ---------------------------------------------------------------------

section("L — CREATE FINAL SAFETY/FAIRNESS LOCK")

manifest = {
    "phase": "12.5",

    "status":
        "FINAL_SAFETY_FAIRNESS_AUDIT_FROZEN",

    "classification":
        classification,

    "population": {
        "primary_model_negative_cases": 7858,
        "primary_model_false_negatives": 557,
        "reviews": 1178,
        "false_negatives_escalated": 110,
    },

    "observed_gaps": {
        "gender": {
            "review_rate_gap":
                float(
                    gender_gap[
                        "review_rate_gap"
                    ]
                ),

            "fn_capture_gap":
                float(
                    gender_gap[
                        "fn_capture_gap"
                    ]
                ),
        },

        "race": {
            "review_rate_gap":
                float(
                    race_gap[
                        "review_rate_gap"
                    ]
                ),

            "fn_capture_gap":
                float(
                    race_gap[
                        "fn_capture_gap"
                    ]
                ),

            "fn_gap_minimum_group":
                str(
                    race_gap[
                        "fn_capture_min_group"
                    ]
                ),

            "missingness_driven_max_gap":
                True,
        },

        "age": {
            "review_rate_gap":
                float(
                    age_gap[
                        "review_rate_gap"
                    ]
                ),

            "fn_capture_gap":
                float(
                    age_gap[
                        "fn_capture_gap"
                    ]
                ),

            "fn_gap_maximum_group":
                str(
                    age_gap[
                        "fn_capture_max_group"
                    ]
                ),

            "fn_gap_minimum_group":
                str(
                    age_gap[
                        "fn_capture_min_group"
                    ]
                ),
        },
    },

    "low_support_groups":
        low_support_groups,

    "publication_safe_conclusion":
        conclusion,

    "artifact_hashes":
        artifact_hashes,

    "integrity": {
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

        "fairness_result_used_for_model_selection":
            False,

        "unfavorable_results_suppressed":
            False,

        "phase10_modified":
            False,

        "phase11_modified":
            False,

        "phase12_1_to_12_4_modified":
            False,
    },

    "next_phase":
        "12.6 — Final Phase 12 closure",
}

with open(
    FINAL_LOCK_PATH,
    "w"
) as f:

    json.dump(
        manifest,
        f,
        indent=2
    )

print(
    "Saved:",
    FINAL_LOCK_PATH
)


# ---------------------------------------------------------------------
# M — FINAL VERIFICATION
# ---------------------------------------------------------------------

section("M — FINAL VERIFICATION")

checks = {
    "protocol_frozen":
        protocol["status"]
        == "FINAL_FAIRNESS_PROTOCOL_FROZEN",

    "execution_complete":
        execution["status"]
        == "FINAL_SUBGROUP_FAIRNESS_AUDIT_EXECUTED",

    "population_lock":
        population["cases"] == 7858,

    "primary_fn_lock":
        population[
            "primary_false_negatives"
        ] == 557,

    "review_budget_lock":
        population["reviews"] == 1178,

    "system_D_fn_lock":
        population[
            "false_negatives_escalated"
        ] == 110,

    "gender_gap_lock":
        np.isclose(
            float(
                gender_gap[
                    "fn_capture_gap"
                ]
            ),
            0.015270,
            atol=1e-6
        ),

    "race_gap_lock":
        np.isclose(
            float(
                race_gap[
                    "fn_capture_gap"
                ]
            ),
            0.222488,
            atol=1e-6
        ),

    "age_gap_lock":
        np.isclose(
            float(
                age_gap[
                    "fn_capture_gap"
                ]
            ),
            0.208361,
            atol=1e-6
        ),

    "missing_race_preserved":
        int(
            missing_race[
                "group_false_negatives"
            ]
        ) == 14,

    "missing_race_zero_capture_preserved":
        int(
            missing_race[
                "group_false_negatives_escalated"
            ]
        ) == 0,

    "demographics_not_used_for_routing":
        execution["integrity"][
            "demographics_used_for_routing"
        ] is False,

    "router_not_retuned":
        execution["integrity"][
            "router_retuned"
        ] is False,

    "final_lock_exists":
        FINAL_LOCK_PATH.exists(),
}

for name, passed in checks.items():

    print(
        f"{name}:",
        "PASSED" if passed else "FAILED"
    )

if not all(checks.values()):

    raise RuntimeError(
        "Phase 12.5 final lock verification failed."
    )


print()
print("=" * 80)

print(
    "PHASE 12.5 COMPLETE — "
    "FINAL SAFETY/FAIRNESS AUDIT FROZEN"
)

print("=" * 80)

print()
print(
    "Safety/fairness classification:",
    classification
)

print()

print("GENDER")
print(
    " Review-rate gap:",
    f"{float(gender_gap['review_rate_gap']):.2%}"
)
print(
    " FN-capture gap:",
    f"{float(gender_gap['fn_capture_gap']):.2%}"
)

print()

print("RACE")
print(
    " Review-rate gap:",
    f"{float(race_gap['review_rate_gap']):.2%}"
)
print(
    " FN-capture gap:",
    f"{float(race_gap['fn_capture_gap']):.2%}"
)
print(
    " FN-capture minimum group:",
    race_gap["fn_capture_min_group"]
)
print(
    " Missingness-associated maximum gap: YES"
)

print()

print("AGE")
print(
    " Review-rate gap:",
    f"{float(age_gap['review_rate_gap']):.2%}"
)
print(
    " FN-capture gap:",
    f"{float(age_gap['fn_capture_gap']):.2%}"
)

print()
print("Demographics used for routing: NO")
print("Router modified after audit: NO")
print("Subgroup thresholds created: NO")
print("Unfavorable findings suppressed: NO")

print()
print(
    "NEXT: PHASE 12.6 — "
    "FINAL PHASE 12 CLOSURE"
)
