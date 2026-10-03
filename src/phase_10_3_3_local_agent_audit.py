"""
CARECOMPUTE
PHASE 10.3.3 — LOCAL AGENT QUALITY / SAFETY AUDIT

Audits the deterministic Rescue Review Agent from Phase 10.3.2.

IMPORTANT:
- No rules are changed.
- No ground truth is used.
- No model/router values are modified.
- This phase evaluates reproducibility, consistency, safety,
  signal prevalence, and demographic priority distribution.
"""

from pathlib import Path
import json
import re

import numpy as np
import pandas as pd


# =============================================================================
# CONFIGURATION
# =============================================================================

CONTEXT_FILE = Path(
    "results/eligible/agents/patient_agent_contexts.csv"
)

AGENT_OUTPUT_FILE = Path(
    "results/eligible/agents/local_agent_outputs.csv"
)

SUMMARY_FILE = Path(
    "results/eligible/agents/local_agent_simulation_summary.json"
)

OUTPUT_DIR = Path(
    "results/eligible/agents"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_SUMMARY_FILE = (
    OUTPUT_DIR / "local_agent_quality_safety_audit.json"
)

SIGNAL_AUDIT_FILE = (
    OUTPUT_DIR / "local_agent_signal_prevalence.csv"
)

PRIORITY_AUDIT_FILE = (
    OUTPUT_DIR / "local_agent_priority_audit.csv"
)

DEMOGRAPHIC_AUDIT_FILE = (
    OUTPUT_DIR / "local_agent_demographic_priority_audit.csv"
)

EXPECTED_CASES = 1178

# These are the frozen Phase 10.3.2 rules.
NEAR_THRESHOLD_DISTANCE = 0.015
HIGH_DISAGREEMENT = 0.12
HIGH_ROUTER_SCORE = 0.75
HIGH_DIAGNOSIS_BURDEN = 8
HIGH_OUTPATIENT_UTILIZATION = 5
LONG_HOSPITAL_STAY = 5

ALLOWED_PRIORITIES = {
    "LOW",
    "MODERATE",
    "HIGH",
}

ALLOWED_ACTIONS = {
    "ROUTINE_REVIEW",
    "PRIORITY_REVIEW",
}

ALLOWED_CONFIDENCE = {
    "LOW",
    "MEDIUM",
    "HIGH",
}

ALLOWED_REASON_CODES = {
    "NEAR_DECISION_THRESHOLD",
    "HIGH_MODEL_DISAGREEMENT",
    "HIGH_ROUTER_SCORE",
    "HIGH_DIAGNOSIS_BURDEN",
    "HIGH_OUTPATIENT_UTILIZATION",
    "EMERGENCY_UTILIZATION",
    "INPATIENT_UTILIZATION",
    "LONGER_HOSPITAL_STAY",
    "MULTIPLE_RISK_SIGNALS",
    "LIMITED_RISK_SIGNALS",
}

PROHIBITED_FIELDS = [
    "actual_30d",
    "case_type",
    "router_target",
    "patient_nbr",
    "diagnosis",
    "treatment",
    "medication",
    "prescription",
    "new_prediction",
    "predicted_outcome",
    "new_probability",
    "new_router_probability",
    "new_threshold",
    "new_router_selection",
]


# =============================================================================
# HELPERS
# =============================================================================

def section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def passed(message):
    print(f"{message}: PASSED")


def warning(message):
    print(f"{message}: WARNING")


def parse_bool(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, np.integer)):
        return bool(value)

    text = str(value).strip().lower()

    if text in {"true", "1", "yes"}:
        return True

    if text in {"false", "0", "no"}:
        return False

    raise ValueError(
        f"Cannot parse boolean value: {value}"
    )


def parse_reason_codes(value):
    if pd.isna(value):
        return []

    return [
        x.strip()
        for x in str(value).split("|")
        if x.strip()
    ]


# =============================================================================
# START
# =============================================================================

section(
    "PHASE 10.3.3 — LOCAL AGENT QUALITY / SAFETY AUDIT"
)


# =============================================================================
# A — LOAD INPUTS
# =============================================================================

section("A — LOAD INPUTS")

for path in [
    CONTEXT_FILE,
    AGENT_OUTPUT_FILE,
    SUMMARY_FILE,
]:
    if not path.exists():
        raise FileNotFoundError(path)

contexts = pd.read_csv(CONTEXT_FILE)

outputs = pd.read_csv(AGENT_OUTPUT_FILE)

with open(
    SUMMARY_FILE,
    "r",
    encoding="utf-8"
) as f:
    simulation_summary = json.load(f)

print("Contexts:", contexts.shape)
print("Agent outputs:", outputs.shape)

if len(contexts) != EXPECTED_CASES:
    raise AssertionError(
        f"Expected {EXPECTED_CASES} contexts."
    )

if len(outputs) != EXPECTED_CASES:
    raise AssertionError(
        f"Expected {EXPECTED_CASES} outputs."
    )

passed("Expected case counts")


# =============================================================================
# B — ENCOUNTER ALIGNMENT
# =============================================================================

section("B — ENCOUNTER ALIGNMENT")

if contexts["encounter_id"].duplicated().any():
    raise AssertionError(
        "Duplicate encounter IDs in contexts."
    )

if outputs["encounter_id"].duplicated().any():
    raise AssertionError(
        "Duplicate encounter IDs in outputs."
    )

passed("Context encounter IDs unique")
passed("Output encounter IDs unique")

context_ids = set(
    contexts["encounter_id"].astype(int)
)

output_ids = set(
    outputs["encounter_id"].astype(int)
)

if context_ids != output_ids:
    raise AssertionError(
        "Context/output encounter ID sets differ."
    )

passed("Context and output encounters match")

audit = contexts.merge(
    outputs,
    on="encounter_id",
    how="inner",
    validate="one_to_one",
)

print("Merged audit rows:", len(audit))

if len(audit) != EXPECTED_CASES:
    raise AssertionError(
        "Merged audit population mismatch."
    )

passed("One-to-one audit merge")


# =============================================================================
# C — OUTPUT SCHEMA AUDIT
# =============================================================================

section("C — OUTPUT SCHEMA AUDIT")

required_columns = [
    "schema_version",
    "encounter_id",
    "review_priority",
    "risk_signal_summary",
    "reason_codes",
    "uncertainty_flag",
    "human_review_action",
    "confidence",
    "safety_flag",
]

missing_columns = [
    col
    for col in required_columns
    if col not in outputs.columns
]

if missing_columns:
    raise AssertionError(
        f"Missing output columns: {missing_columns}"
    )

passed("Required output columns present")

if not set(
    outputs["review_priority"].dropna().unique()
).issubset(ALLOWED_PRIORITIES):
    raise AssertionError(
        "Invalid review priority detected."
    )

passed("Review priorities valid")

if not set(
    outputs["human_review_action"].dropna().unique()
).issubset(ALLOWED_ACTIONS):
    raise AssertionError(
        "Invalid human review action detected."
    )

passed("Human review actions valid")

if not set(
    outputs["confidence"].dropna().unique()
).issubset(ALLOWED_CONFIDENCE):
    raise AssertionError(
        "Invalid confidence detected."
    )

passed("Confidence values valid")


# =============================================================================
# D — REASON CODE SCHEMA AUDIT
# =============================================================================

section("D — REASON CODE SCHEMA AUDIT")

reason_lists = outputs[
    "reason_codes"
].apply(parse_reason_codes)

invalid_reason_codes = []

too_many_reason_codes = 0

empty_reason_codes = 0

for encounter_id, codes in zip(
    outputs["encounter_id"],
    reason_lists
):
    if len(codes) > 5:
        too_many_reason_codes += 1

    if len(codes) == 0:
        empty_reason_codes += 1

    for code in codes:
        if code not in ALLOWED_REASON_CODES:
            invalid_reason_codes.append(
                (encounter_id, code)
            )

print(
    "Outputs with >5 reason codes:",
    too_many_reason_codes
)

print(
    "Outputs with zero reason codes:",
    empty_reason_codes
)

print(
    "Invalid reason codes:",
    len(invalid_reason_codes)
)

if too_many_reason_codes:
    raise AssertionError(
        "Reason-code maximum violated."
    )

if empty_reason_codes:
    raise AssertionError(
        "Empty reason-code output detected."
    )

if invalid_reason_codes:
    raise AssertionError(
        f"Invalid reason codes: "
        f"{invalid_reason_codes[:10]}"
    )

passed("Reason-code schema valid")


# =============================================================================
# E — REPRODUCE RAW SIGNALS
# =============================================================================

section("E — REPRODUCE RAW SIGNALS")

audit["expected_near_threshold"] = (
    audit["distance_below_threshold"]
    <= NEAR_THRESHOLD_DISTANCE
)

audit["expected_high_disagreement"] = (
    audit["model_disagreement_std"]
    >= HIGH_DISAGREEMENT
)

audit["expected_high_router"] = (
    audit["fn_router_probability"]
    >= HIGH_ROUTER_SCORE
)

audit["expected_high_diagnosis"] = (
    audit["number_diagnoses"]
    >= HIGH_DIAGNOSIS_BURDEN
)

audit["expected_high_outpatient"] = (
    audit["number_outpatient"]
    >= HIGH_OUTPATIENT_UTILIZATION
)

audit["expected_emergency"] = (
    audit["number_emergency"] > 0
)

audit["expected_inpatient"] = (
    audit["number_inpatient"] > 0
)

audit["expected_long_stay"] = (
    audit["time_in_hospital"]
    >= LONG_HOSPITAL_STAY
)

signal_map = {
    "NEAR_DECISION_THRESHOLD":
        "expected_near_threshold",

    "HIGH_MODEL_DISAGREEMENT":
        "expected_high_disagreement",

    "HIGH_ROUTER_SCORE":
        "expected_high_router",

    "HIGH_DIAGNOSIS_BURDEN":
        "expected_high_diagnosis",

    "HIGH_OUTPATIENT_UTILIZATION":
        "expected_high_outpatient",

    "EMERGENCY_UTILIZATION":
        "expected_emergency",

    "INPATIENT_UTILIZATION":
        "expected_inpatient",

    "LONGER_HOSPITAL_STAY":
        "expected_long_stay",
}

reason_dict = {
    int(row.encounter_id):
        set(parse_reason_codes(row.reason_codes))
    for row in outputs.itertuples()
}


# =============================================================================
# F — SIGNAL / REASON-CODE CONSISTENCY
# =============================================================================

section(
    "F — SIGNAL / REASON-CODE CONSISTENCY"
)

signal_rows = []

total_false_positive_codes = 0
total_missing_codes = 0

for reason_code, expected_col in signal_map.items():

    expected = audit[
        expected_col
    ].astype(bool)

    observed = audit[
        "encounter_id"
    ].astype(int).apply(
        lambda encounter_id:
            reason_code
            in reason_dict[encounter_id]
    )

    expected_count = int(
        expected.sum()
    )

    observed_count = int(
        observed.sum()
    )

    false_positive_codes = int(
        ((~expected) & observed).sum()
    )

    # IMPORTANT:
    # Because Phase 10.3.2 truncates reason codes to max 5,
    # an expected signal may legitimately be absent from the
    # output reason-code list.
    missing_codes = int(
        (expected & (~observed)).sum()
    )

    total_false_positive_codes += (
        false_positive_codes
    )

    total_missing_codes += (
        missing_codes
    )

    prevalence = (
        100.0
        * expected_count
        / EXPECTED_CASES
    )

    print(
        f"{reason_code}: "
        f"expected={expected_count}, "
        f"observed={observed_count}, "
        f"false_positive_codes="
        f"{false_positive_codes}, "
        f"missing_due_to_output/truncation="
        f"{missing_codes}, "
        f"prevalence={prevalence:.2f}%"
    )

    signal_rows.append({
        "reason_code":
            reason_code,

        "expected_from_source":
            expected_count,

        "observed_in_agent_output":
            observed_count,

        "false_positive_codes":
            false_positive_codes,

        "missing_from_output":
            missing_codes,

        "source_prevalence_percent":
            prevalence,
    })

if total_false_positive_codes != 0:
    raise AssertionError(
        "Agent emitted reason codes not supported "
        "by source values."
    )

passed(
    "No unsupported raw reason codes"
)

print(
    "Expected signals omitted from displayed "
    "reason-code lists:",
    total_missing_codes
)

print(
    "NOTE: omissions may occur because the "
    "Phase 10.3.1 contract limits outputs to "
    "five reason codes."
)


# =============================================================================
# G — SIGNAL PREVALENCE / DISCRIMINATIVE AUDIT
# =============================================================================

section(
    "G — SIGNAL PREVALENCE / DISCRIMINATIVE AUDIT"
)

signal_df = pd.DataFrame(
    signal_rows
)

signal_df[
    "prevalence_flag"
] = signal_df[
    "source_prevalence_percent"
].apply(
    lambda x:
        "VERY_COMMON"
        if x >= 90
        else (
            "VERY_RARE"
            if x <= 2
            else "OK"
        )
)

print(
    signal_df[
        [
            "reason_code",
            "source_prevalence_percent",
            "prevalence_flag",
        ]
    ].to_string(
        index=False
    )
)

very_common = signal_df[
    signal_df["prevalence_flag"]
    == "VERY_COMMON"
]

very_rare = signal_df[
    signal_df["prevalence_flag"]
    == "VERY_RARE"
]

if len(very_common):
    warning(
        "One or more signals occur in >=90% "
        "of selected cases"
    )

if len(very_rare):
    warning(
        "One or more signals occur in <=2% "
        "of selected cases"
    )

signal_df.to_csv(
    SIGNAL_AUDIT_FILE,
    index=False
)

print("\nSaved:")
print(SIGNAL_AUDIT_FILE)


# =============================================================================
# H — REPRODUCE PRIORITY LOGIC
# =============================================================================

section("H — REPRODUCE PRIORITY LOGIC")

raw_signal_columns = list(
    signal_map.values()
)

audit["raw_signal_count"] = (
    audit[raw_signal_columns]
    .astype(int)
    .sum(axis=1)
)

audit["strong_signal_count"] = (
    audit[
        [
            "expected_near_threshold",
            "expected_high_disagreement",
            "expected_high_router",
            "expected_emergency",
            "expected_inpatient",
        ]
    ]
    .astype(int)
    .sum(axis=1)
)


def expected_priority(row):

    if (
        row["expected_high_router"]
        and row["strong_signal_count"] >= 3
    ):
        return "HIGH"

    if row["raw_signal_count"] >= 3:
        return "MODERATE"

    return "LOW"


audit["expected_priority"] = audit.apply(
    expected_priority,
    axis=1
)

audit["priority_match"] = (
    audit["expected_priority"]
    == audit["review_priority"]
)

priority_mismatches = int(
    (~audit["priority_match"]).sum()
)

print(
    "Priority mismatches:",
    priority_mismatches
)

if priority_mismatches:
    print(
        audit.loc[
            ~audit["priority_match"],
            [
                "encounter_id",
                "raw_signal_count",
                "strong_signal_count",
                "expected_high_router",
                "expected_priority",
                "review_priority",
            ],
        ].head(20).to_string(
            index=False
        )
    )

    raise AssertionError(
        "Priority logic mismatch detected."
    )

passed(
    "Priority logic exactly reproduced"
)


# =============================================================================
# I — HUMAN REVIEW ACTION CONSISTENCY
# =============================================================================

section(
    "I — HUMAN REVIEW ACTION CONSISTENCY"
)

audit["expected_action"] = np.where(
    audit["review_priority"] == "HIGH",
    "PRIORITY_REVIEW",
    "ROUTINE_REVIEW",
)

action_mismatches = int(
    (
        audit["expected_action"]
        != audit["human_review_action"]
    ).sum()
)

print(
    "Action mismatches:",
    action_mismatches
)

if action_mismatches:
    raise AssertionError(
        "Human-review action mismatch."
    )

passed(
    "Human-review action consistent with priority"
)


# =============================================================================
# J — UNCERTAINTY FLAG CONSISTENCY
# =============================================================================

section(
    "J — UNCERTAINTY FLAG CONSISTENCY"
)

audit[
    "observed_uncertainty_bool"
] = audit[
    "uncertainty_flag"
].apply(parse_bool)

audit[
    "expected_uncertainty_bool"
] = audit[
    "expected_high_disagreement"
].astype(bool)

uncertainty_mismatches = int(
    (
        audit["observed_uncertainty_bool"]
        != audit["expected_uncertainty_bool"]
    ).sum()
)

print(
    "Uncertainty mismatches:",
    uncertainty_mismatches
)

if uncertainty_mismatches:
    raise AssertionError(
        "Uncertainty flag mismatch."
    )

passed(
    "Uncertainty flag exactly reproduced"
)


# =============================================================================
# K — CONFIDENCE CONSISTENCY
# =============================================================================

section("K — CONFIDENCE CONSISTENCY")


def expected_confidence(signal_count):

    if signal_count >= 4:
        return "HIGH"

    if signal_count >= 2:
        return "MEDIUM"

    return "LOW"


audit["expected_confidence"] = (
    audit["raw_signal_count"]
    .apply(expected_confidence)
)

confidence_mismatches = int(
    (
        audit["expected_confidence"]
        != audit["confidence"]
    ).sum()
)

print(
    "Confidence mismatches:",
    confidence_mismatches
)

if confidence_mismatches:
    raise AssertionError(
        "Confidence logic mismatch."
    )

passed(
    "Confidence logic exactly reproduced"
)


# =============================================================================
# L — PRIORITY DISTRIBUTION
# =============================================================================

section("L — PRIORITY DISTRIBUTION")

priority_distribution = (
    audit["review_priority"]
    .value_counts()
    .reindex(
        ["HIGH", "MODERATE", "LOW"],
        fill_value=0
    )
)

priority_percent = (
    priority_distribution
    / EXPECTED_CASES
    * 100
)

priority_table = pd.DataFrame({
    "review_priority":
        priority_distribution.index,

    "cases":
        priority_distribution.values,

    "percent":
        priority_percent.values,
})

print(
    priority_table.to_string(
        index=False
    )
)

priority_table.to_csv(
    PRIORITY_AUDIT_FILE,
    index=False
)

print("\nSaved:")
print(PRIORITY_AUDIT_FILE)

high_percent = float(
    priority_percent["HIGH"]
)

if high_percent < 1:
    warning(
        "HIGH priority represents <1% "
        "of selected cases"
    )


# =============================================================================
# M — DEMOGRAPHIC PRIORITY AUDIT
# =============================================================================

section(
    "M — DEMOGRAPHIC PRIORITY AUDIT"
)

demographic_rows = []

for feature in [
    "gender",
    "race",
    "age_group",
]:

    print(
        f"\n{feature.upper()}"
    )

    for group, group_df in audit.groupby(
        feature,
        dropna=False
    ):

        n = len(group_df)

        high_n = int(
            (
                group_df["review_priority"]
                == "HIGH"
            ).sum()
        )

        moderate_n = int(
            (
                group_df["review_priority"]
                == "MODERATE"
            ).sum()
        )

        low_n = int(
            (
                group_df["review_priority"]
                == "LOW"
            ).sum()
        )

        high_pct = (
            100 * high_n / n
            if n else np.nan
        )

        moderate_pct = (
            100 * moderate_n / n
            if n else np.nan
        )

        low_pct = (
            100 * low_n / n
            if n else np.nan
        )

        demographic_rows.append({
            "feature":
                feature,

            "group":
                group,

            "cases":
                n,

            "high_priority":
                high_n,

            "high_priority_percent":
                high_pct,

            "moderate_priority":
                moderate_n,

            "moderate_priority_percent":
                moderate_pct,

            "low_priority":
                low_n,

            "low_priority_percent":
                low_pct,
        })

        print(
            f"{group}: "
            f"n={n}, "
            f"HIGH={high_n} "
            f"({high_pct:.2f}%), "
            f"MODERATE={moderate_n} "
            f"({moderate_pct:.2f}%), "
            f"LOW={low_n} "
            f"({low_pct:.2f}%)"
        )

demographic_df = pd.DataFrame(
    demographic_rows
)

demographic_df.to_csv(
    DEMOGRAPHIC_AUDIT_FILE,
    index=False
)

print("\nSaved:")
print(DEMOGRAPHIC_AUDIT_FILE)

print(
    "\nNOTE: These are descriptive queue "
    "distributions only."
)

print(
    "They do not establish demographic fairness "
    "or unfairness by themselves."
)


# =============================================================================
# N — SUMMARY TEXT SAFETY AUDIT
# =============================================================================

section(
    "N — SUMMARY TEXT SAFETY AUDIT"
)

summary_lengths = (
    outputs["risk_signal_summary"]
    .fillna("")
    .astype(str)
    .str.len()
)

print(
    "Maximum summary length:",
    int(summary_lengths.max())
)

print(
    "Mean summary length:",
    round(
        float(summary_lengths.mean()),
        2
    )
)

if (
    summary_lengths > 600
).any():
    raise AssertionError(
        "Summary exceeds 600 characters."
    )

passed(
    "Summary length contract"
)

unsafe_patterns = [
    r"\byou have\b",
    r"\bdiagnosed with\b",
    r"\bprescribe\b",
    r"\bstart medication\b",
    r"\bstop medication\b",
    r"\btreatment plan\b",
    r"\bshould take\b",
]

unsafe_matches = []

for row in outputs.itertuples():

    text = str(
        row.risk_signal_summary
    ).lower()

    for pattern in unsafe_patterns:

        if re.search(
            pattern,
            text
        ):
            unsafe_matches.append({
                "encounter_id":
                    int(row.encounter_id),

                "pattern":
                    pattern,

                "text":
                    row.risk_signal_summary,
            })

print(
    "Unsafe summary patterns:",
    len(unsafe_matches)
)

if unsafe_matches:
    print(
        unsafe_matches[:10]
    )

    raise AssertionError(
        "Potential clinical instruction or "
        "diagnostic language detected."
    )

passed(
    "No prohibited clinical instruction language detected"
)


# =============================================================================
# O — SAFETY FLAG AUDIT
# =============================================================================

section("O — SAFETY FLAG AUDIT")

safety_bool = outputs[
    "safety_flag"
].apply(parse_bool)

print(
    "Safety flag TRUE:",
    int(safety_bool.sum())
)

print(
    "Safety flag FALSE:",
    int((~safety_bool).sum())
)

if safety_bool.any():
    raise AssertionError(
        "Unexpected safety violation flag."
    )

passed(
    "No deterministic-agent safety violations"
)


# =============================================================================
# P — PROHIBITED FIELD / LEAKAGE AUDIT
# =============================================================================

section(
    "P — PROHIBITED FIELD / LEAKAGE AUDIT"
)

serialized_columns = (
    " ".join(
        outputs.columns
    ).lower()
)

for field in PROHIBITED_FIELDS:

    if field.lower() in [
        x.lower()
        for x in outputs.columns
    ]:
        raise AssertionError(
            f"Prohibited output column: {field}"
        )

    passed(
        f"{field} absent as output field"
    )


# =============================================================================
# Q — DESCRIPTIVE SIGNAL RANGES
# =============================================================================

section(
    "Q — DESCRIPTIVE SIGNAL RANGES"
)

descriptive_columns = [
    "distance_below_threshold",
    "model_disagreement_std",
    "fn_router_probability",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
    "number_inpatient",
    "time_in_hospital",
]

description = audit[
    descriptive_columns
].describe(
    percentiles=[
        0.05,
        0.25,
        0.50,
        0.75,
        0.95,
    ]
)

print(
    description.to_string()
)

print(
    "\nIMPORTANT:"
)

print(
    "These distributions are diagnostic only."
)

print(
    "Do not change thresholds in Phase 10.3.3."
)


# =============================================================================
# R — QUALITY FLAGS
# =============================================================================

section("R — QUALITY FLAGS")

quality_flags = []

disagreement_prevalence = float(
    audit[
        "expected_high_disagreement"
    ].mean()
    * 100
)

router_high_prevalence = float(
    audit[
        "expected_high_router"
    ].mean()
    * 100
)

if disagreement_prevalence >= 90:
    quality_flags.append(
        "HIGH_MODEL_DISAGREEMENT is present "
        "in >=90% of selected cases and may "
        "provide limited within-queue discrimination."
    )

if router_high_prevalence <= 2:
    quality_flags.append(
        "HIGH_ROUTER_SCORE is present in <=2% "
        "of selected cases and is extremely selective."
    )

if high_percent < 1:
    quality_flags.append(
        "HIGH review priority is assigned to <1% "
        "of selected cases."
    )

if total_missing_codes > 0:
    quality_flags.append(
        "Some valid raw signals are omitted from "
        "displayed reason-code lists because outputs "
        "are limited to five reason codes."
    )

if quality_flags:

    print(
        "QUALITY FLAGS FOUND:"
    )

    for flag in quality_flags:
        print(
            f"- {flag}"
        )

else:
    print(
        "No descriptive quality flags."
    )

print(
    "\nThese are NOT safety failures."
)

print(
    "They identify design characteristics that "
    "should be considered before freezing "
    "the agent prioritization rules."
)


# =============================================================================
# S — SAVE AUDIT SUMMARY
# =============================================================================

section("S — SAVE AUDIT SUMMARY")

audit_summary = {
    "phase":
        "10.3.3",

    "cases_audited":
        EXPECTED_CASES,

    "contract_compliance":
        True,

    "encounter_integrity":
        True,

    "ground_truth_leakage_detected":
        False,

    "unsupported_reason_codes":
        total_false_positive_codes,

    "valid_signals_omitted_from_reason_list":
        total_missing_codes,

    "priority_logic_mismatches":
        priority_mismatches,

    "human_review_action_mismatches":
        action_mismatches,

    "uncertainty_flag_mismatches":
        uncertainty_mismatches,

    "confidence_logic_mismatches":
        confidence_mismatches,

    "unsafe_summary_patterns":
        len(unsafe_matches),

    "safety_flag_true":
        int(safety_bool.sum()),

    "priority_distribution":
        {
            row["review_priority"]:
                {
                    "cases":
                        int(row["cases"]),

                    "percent":
                        float(row["percent"]),
                }
            for _, row
            in priority_table.iterrows()
        },

    "high_model_disagreement_prevalence_percent":
        disagreement_prevalence,

    "high_router_score_prevalence_percent":
        router_high_prevalence,

    "quality_flags":
        quality_flags,

    "rules_changed":
        False,

    "ground_truth_used":
        False,

    "human_review_required":
        True,

    "audit_outputs": [
        str(SIGNAL_AUDIT_FILE),
        str(PRIORITY_AUDIT_FILE),
        str(DEMOGRAPHIC_AUDIT_FILE),
    ],
}

with open(
    AUDIT_SUMMARY_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        audit_summary,
        f,
        indent=2
    )

print(
    json.dumps(
        audit_summary,
        indent=2
    )
)

print("\nSaved:")
print(AUDIT_SUMMARY_FILE)


# =============================================================================
# T — FINAL STATUS
# =============================================================================

section("T — FINAL STATUS")

required_outputs = [
    AUDIT_SUMMARY_FILE,
    SIGNAL_AUDIT_FILE,
    PRIORITY_AUDIT_FILE,
    DEMOGRAPHIC_AUDIT_FILE,
]

for path in required_outputs:

    if not path.exists():
        raise AssertionError(
            f"Missing audit output: {path}"
        )

    print(
        f"{path}: CREATED"
    )

print("\n" + "=" * 80)

print(
    "PHASE 10.3.3 COMPLETE — PASSED"
)

print("=" * 80)

print(
    "\nDeterministic Rescue Review Agent "
    "quality and safety audit completed."
)

print(
    "No ground truth was used."
)

print(
    "No agent thresholds or rules were changed."
)

print(
    "No frozen model or router behavior was modified."
)

print(
    "Any quality flags above are descriptive "
    "and should be evaluated before rule freeze."
)

print(
    "\nNEXT PHASE:"
)

print(
    "PHASE 10.3.4 — AGENT RULE CALIBRATION / FREEZE"
)