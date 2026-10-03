"""
PHASE 10.3.4 — AGENT RULE CALIBRATION / FREEZE

Purpose
-------
Calibrate deterministic Rescue Review Agent rules using ONLY the
approved Phase 10.2 agent-context variables.

IMPORTANT:
- Does NOT use actual_30d.
- Does NOT use case_type.
- Does NOT use router_target.
- Does NOT use patient_nbr.
- Does NOT modify the frozen primary model.
- Does NOT modify the frozen Rescue Router.
- Does NOT modify threshold 0.115.
- Does NOT modify review budget 0.15.

Calibration is based only on distributions within the already-selected
1,178-case human-review queue.
"""

from pathlib import Path
import json

import numpy as np
import pandas as pd


# =============================================================================
# CONFIGURATION
# =============================================================================

CONTEXT_FILE = Path(
    "results/eligible/agents/patient_agent_contexts.csv"
)

OUTPUT_DIR = Path("results/eligible/agents")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RULE_FILE = OUTPUT_DIR / "rescue_review_agent_frozen_rules.json"
CALIBRATION_FILE = OUTPUT_DIR / "agent_rule_calibration_summary.csv"
PRIORITY_FILE = OUTPUT_DIR / "agent_rule_calibrated_priority_distribution.csv"
AUDIT_FILE = OUTPUT_DIR / "agent_rule_freeze_audit.json"

EXPECTED_CASES = 1178
FROZEN_THRESHOLD = 0.115
FROZEN_REVIEW_BUDGET = 0.15


def banner(text):
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


def passed(text):
    print(f"{text}: PASSED")


# =============================================================================
# START
# =============================================================================

banner("PHASE 10.3.4 — AGENT RULE CALIBRATION / FREEZE")


# =============================================================================
# A — LOAD APPROVED AGENT CONTEXT
# =============================================================================

banner("A — LOAD APPROVED PHASE 10.2 CONTEXT")

df = pd.read_csv(CONTEXT_FILE)

print("Input shape:")
print(df.shape)

assert len(df) == EXPECTED_CASES
passed("Exactly 1,178 frozen review cases loaded")


# =============================================================================
# B — GROUND-TRUTH LEAKAGE CHECK
# =============================================================================

banner("B — GROUND-TRUTH / PROHIBITED FIELD CHECK")

prohibited = [
    "actual_30d",
    "case_type",
    "router_target",
    "patient_nbr",
]

for col in prohibited:
    print(f"{col}: {'PRESENT' if col in df.columns else 'NOT PRESENT'}")
    assert col not in df.columns

passed("No retrospective ground truth or prohibited identifier available")


# =============================================================================
# C — VERIFY FROZEN SYSTEM CONTRACT
# =============================================================================

banner("C — FROZEN SYSTEM CONTRACT")

assert np.allclose(df["decision_threshold"], FROZEN_THRESHOLD)
assert (df["selected_for_review"] == 1).all()
assert (df["predicted_30d"] == 0).all()

if "review_budget" in df.columns:
    assert np.allclose(df["review_budget"], FROZEN_REVIEW_BUDGET)

passed("Primary-model threshold remains 0.115")
passed("All cases remain frozen low-risk predictions")
passed("All cases remain frozen Rescue Router selections")
passed("Review budget remains 15%")


# =============================================================================
# D — CALIBRATION VARIABLES
# =============================================================================

banner("D — CALIBRATION VARIABLES")

calibration_variables = [
    "distance_below_threshold",
    "model_disagreement_std",
    "fn_router_probability",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
    "number_inpatient",
    "time_in_hospital",
]

for col in calibration_variables:
    assert col in df.columns, f"Missing calibration variable: {col}"
    print(col, "FOUND")

passed("All approved calibration variables available")


# =============================================================================
# E — DESCRIPTIVE QUANTILES
# =============================================================================

banner("E — DESCRIPTIVE QUANTILES")

quantiles = [0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]

quantile_rows = []

for col in [
    "model_disagreement_std",
    "fn_router_probability",
    "distance_below_threshold",
]:
    print(f"\n{col}")

    q = df[col].quantile(quantiles)

    print(q)

    for quantile, value in q.items():
        quantile_rows.append(
            {
                "variable": col,
                "quantile": quantile,
                "value": value,
            }
        )

quantile_df = pd.DataFrame(quantile_rows)


# =============================================================================
# F — DEFINE CALIBRATED THRESHOLDS
# =============================================================================

banner("F — DEFINE CALIBRATED AGENT THRESHOLDS")

# -------------------------------------------------------------------------
# IMPORTANT:
#
# These thresholds are NOT clinical thresholds.
#
# They are queue-relative thresholds used only to summarize and prioritize
# cases that have ALREADY been selected by the frozen Rescue Router.
#
# Quantiles avoid using retrospective outcomes.
# -------------------------------------------------------------------------

DISAGREEMENT_THRESHOLD = float(
    df["model_disagreement_std"].quantile(0.75)
)

ROUTER_HIGH_THRESHOLD = float(
    df["fn_router_probability"].quantile(0.90)
)

NEAR_THRESHOLD_DISTANCE = float(
    df["distance_below_threshold"].quantile(0.10)
)

# Utilization rules remain interpretable absolute rules.
DIAGNOSIS_BURDEN_THRESHOLD = 8
OUTPATIENT_THRESHOLD = 3
EMERGENCY_THRESHOLD = 1
INPATIENT_THRESHOLD = 1
LONG_STAY_THRESHOLD = 7

print("Calibrated thresholds:")
print()
print(
    f"HIGH_MODEL_DISAGREEMENT >= "
    f"{DISAGREEMENT_THRESHOLD:.6f} "
    "(75th percentile)"
)

print(
    f"HIGH_ROUTER_SCORE >= "
    f"{ROUTER_HIGH_THRESHOLD:.6f} "
    "(90th percentile)"
)

print(
    f"NEAR_DECISION_THRESHOLD <= "
    f"{NEAR_THRESHOLD_DISTANCE:.6f} distance "
    "(closest 10%)"
)

print(f"HIGH_DIAGNOSIS_BURDEN >= {DIAGNOSIS_BURDEN_THRESHOLD}")
print(f"HIGH_OUTPATIENT_UTILIZATION >= {OUTPATIENT_THRESHOLD}")
print(f"EMERGENCY_UTILIZATION >= {EMERGENCY_THRESHOLD}")
print(f"INPATIENT_UTILIZATION >= {INPATIENT_THRESHOLD}")
print(f"LONGER_HOSPITAL_STAY >= {LONG_STAY_THRESHOLD}")


# =============================================================================
# G — GENERATE CALIBRATED RAW SIGNALS
# =============================================================================

banner("G — GENERATE CALIBRATED RAW SIGNALS")

signal_df = pd.DataFrame(index=df.index)

signal_df["NEAR_DECISION_THRESHOLD"] = (
    df["distance_below_threshold"] <= NEAR_THRESHOLD_DISTANCE
)

signal_df["HIGH_MODEL_DISAGREEMENT"] = (
    df["model_disagreement_std"] >= DISAGREEMENT_THRESHOLD
)

signal_df["HIGH_ROUTER_SCORE"] = (
    df["fn_router_probability"] >= ROUTER_HIGH_THRESHOLD
)

signal_df["HIGH_DIAGNOSIS_BURDEN"] = (
    df["number_diagnoses"] >= DIAGNOSIS_BURDEN_THRESHOLD
)

signal_df["HIGH_OUTPATIENT_UTILIZATION"] = (
    df["number_outpatient"] >= OUTPATIENT_THRESHOLD
)

signal_df["EMERGENCY_UTILIZATION"] = (
    df["number_emergency"] >= EMERGENCY_THRESHOLD
)

signal_df["INPATIENT_UTILIZATION"] = (
    df["number_inpatient"] >= INPATIENT_THRESHOLD
)

signal_df["LONGER_HOSPITAL_STAY"] = (
    df["time_in_hospital"] >= LONG_STAY_THRESHOLD
)


# =============================================================================
# H — SIGNAL PREVALENCE
# =============================================================================

banner("H — CALIBRATED SIGNAL PREVALENCE")

prevalence_rows = []

for col in signal_df.columns:

    count = int(signal_df[col].sum())
    percent = count / len(signal_df) * 100

    prevalence_rows.append(
        {
            "signal": col,
            "cases": count,
            "percent": percent,
        }
    )

    print(
        f"{col}: "
        f"{count}/{len(signal_df)} "
        f"({percent:.2f}%)"
    )

prevalence_df = pd.DataFrame(prevalence_rows)


# =============================================================================
# I — BUILD PRIORITY SCORE
# =============================================================================

banner("I — BUILD CALIBRATED PRIORITY SCORE")

# Queue-prioritization weights.
#
# Router score and disagreement receive higher weight because they directly
# describe model/router concern.
#
# Utilization variables provide supporting evidence.

weights = {
    "NEAR_DECISION_THRESHOLD": 2,
    "HIGH_MODEL_DISAGREEMENT": 2,
    "HIGH_ROUTER_SCORE": 3,
    "HIGH_DIAGNOSIS_BURDEN": 1,
    "HIGH_OUTPATIENT_UTILIZATION": 1,
    "EMERGENCY_UTILIZATION": 1,
    "INPATIENT_UTILIZATION": 1,
    "LONGER_HOSPITAL_STAY": 1,
}

priority_score = np.zeros(len(df), dtype=int)

for signal, weight in weights.items():
    priority_score += signal_df[signal].astype(int).values * weight

df_cal = df.copy()
df_cal["agent_priority_score"] = priority_score

print(df_cal["agent_priority_score"].describe())


# =============================================================================
# J — CALIBRATE PRIORITY LEVELS
# =============================================================================

banner("J — CALIBRATE PRIORITY LEVELS")

# We want HIGH to represent a meaningful but selective part of the
# already-selected queue.
#
# No outcomes are used.
#
# Score thresholds are deterministic and interpretable.

def assign_priority(score):
    if score >= 6:
        return "HIGH"
    elif score >= 3:
        return "MODERATE"
    else:
        return "LOW"


df_cal["review_priority"] = (
    df_cal["agent_priority_score"].apply(assign_priority)
)

df_cal["human_review_action"] = np.where(
    df_cal["review_priority"] == "HIGH",
    "PRIORITY_REVIEW",
    "ROUTINE_REVIEW",
)


# =============================================================================
# K — PRIORITY DISTRIBUTION
# =============================================================================

banner("K — CALIBRATED PRIORITY DISTRIBUTION")

priority_counts = (
    df_cal["review_priority"]
    .value_counts()
    .reindex(["HIGH", "MODERATE", "LOW"], fill_value=0)
)

priority_distribution = pd.DataFrame(
    {
        "review_priority": priority_counts.index,
        "cases": priority_counts.values,
    }
)

priority_distribution["percent"] = (
    priority_distribution["cases"] / len(df_cal) * 100
)

print(priority_distribution.to_string(index=False))


# =============================================================================
# L — PRIORITY QUALITY CHECK
# =============================================================================

banner("L — PRIORITY QUALITY CHECK")

high_percent = float(
    priority_distribution.loc[
        priority_distribution["review_priority"] == "HIGH",
        "percent",
    ].iloc[0]
)

moderate_percent = float(
    priority_distribution.loc[
        priority_distribution["review_priority"] == "MODERATE",
        "percent",
    ].iloc[0]
)

low_percent = float(
    priority_distribution.loc[
        priority_distribution["review_priority"] == "LOW",
        "percent",
    ].iloc[0]
)

print(f"HIGH: {high_percent:.2f}%")
print(f"MODERATE: {moderate_percent:.2f}%")
print(f"LOW: {low_percent:.2f}%")

quality_flags = []

if high_percent < 3:
    quality_flags.append(
        "HIGH priority remains below 3% of selected cases."
    )

if high_percent > 25:
    quality_flags.append(
        "HIGH priority exceeds 25% of selected cases."
    )

if moderate_percent < 10:
    quality_flags.append(
        "MODERATE priority is unusually rare."
    )

if low_percent < 10:
    quality_flags.append(
        "LOW priority is unusually rare."
    )

if quality_flags:
    print("\nQUALITY FLAGS:")
    for flag in quality_flags:
        print("-", flag)
else:
    passed("Priority distribution is operationally usable")


# =============================================================================
# M — DEMOGRAPHIC DESCRIPTIVE AUDIT
# =============================================================================

banner("M — DESCRIPTIVE DEMOGRAPHIC PRIORITY DISTRIBUTION")

demographic_rows = []

for feature in ["gender", "race", "age_group"]:

    print(f"\n{feature.upper()}")

    for group, group_df in df_cal.groupby(feature, dropna=False):

        n = len(group_df)

        counts = (
            group_df["review_priority"]
            .value_counts()
            .reindex(["HIGH", "MODERATE", "LOW"], fill_value=0)
        )

        row = {
            "feature": feature,
            "group": group,
            "n": n,
            "high_cases": int(counts["HIGH"]),
            "moderate_cases": int(counts["MODERATE"]),
            "low_cases": int(counts["LOW"]),
            "high_percent": counts["HIGH"] / n * 100,
            "moderate_percent": counts["MODERATE"] / n * 100,
            "low_percent": counts["LOW"] / n * 100,
        }

        demographic_rows.append(row)

        print(
            f"{group}: "
            f"n={n}, "
            f"HIGH={row['high_percent']:.2f}%, "
            f"MODERATE={row['moderate_percent']:.2f}%, "
            f"LOW={row['low_percent']:.2f}%"
        )

demographic_df = pd.DataFrame(demographic_rows)

print()
print("NOTE:")
print("These are descriptive queue distributions.")
print("They are not evidence of fairness or unfairness by themselves.")


# =============================================================================
# N — CREATE CALIBRATION SUMMARY
# =============================================================================

banner("N — CREATE CALIBRATION SUMMARY")

calibration_summary = pd.DataFrame(
    [
        {
            "rule": "NEAR_DECISION_THRESHOLD",
            "threshold": NEAR_THRESHOLD_DISTANCE,
            "definition": "distance_below_threshold <= threshold",
            "calibration_basis": "10th percentile",
        },
        {
            "rule": "HIGH_MODEL_DISAGREEMENT",
            "threshold": DISAGREEMENT_THRESHOLD,
            "definition": "model_disagreement_std >= threshold",
            "calibration_basis": "75th percentile",
        },
        {
            "rule": "HIGH_ROUTER_SCORE",
            "threshold": ROUTER_HIGH_THRESHOLD,
            "definition": "fn_router_probability >= threshold",
            "calibration_basis": "90th percentile",
        },
        {
            "rule": "HIGH_DIAGNOSIS_BURDEN",
            "threshold": DIAGNOSIS_BURDEN_THRESHOLD,
            "definition": "number_diagnoses >= threshold",
            "calibration_basis": "interpretable fixed rule",
        },
        {
            "rule": "HIGH_OUTPATIENT_UTILIZATION",
            "threshold": OUTPATIENT_THRESHOLD,
            "definition": "number_outpatient >= threshold",
            "calibration_basis": "interpretable fixed rule",
        },
        {
            "rule": "EMERGENCY_UTILIZATION",
            "threshold": EMERGENCY_THRESHOLD,
            "definition": "number_emergency >= threshold",
            "calibration_basis": "interpretable fixed rule",
        },
        {
            "rule": "INPATIENT_UTILIZATION",
            "threshold": INPATIENT_THRESHOLD,
            "definition": "number_inpatient >= threshold",
            "calibration_basis": "interpretable fixed rule",
        },
        {
            "rule": "LONGER_HOSPITAL_STAY",
            "threshold": LONG_STAY_THRESHOLD,
            "definition": "time_in_hospital >= threshold",
            "calibration_basis": "interpretable fixed rule",
        },
    ]
)

print(calibration_summary.to_string(index=False))


# =============================================================================
# O — DEFINE FROZEN RULE PACKAGE
# =============================================================================

banner("O — DEFINE FROZEN RULE PACKAGE")

frozen_rules = {
    "rule_version": "10.3.4",
    "agent_name": "CareCompute Rescue Review Agent",
    "status": "FROZEN",
    "population": "Frozen Rescue Router selected cases only",
    "expected_population": EXPECTED_CASES,
    "frozen_primary_model_threshold": FROZEN_THRESHOLD,
    "frozen_router_review_budget": FROZEN_REVIEW_BUDGET,

    "signal_rules": {
        "NEAR_DECISION_THRESHOLD": {
            "field": "distance_below_threshold",
            "operator": "<=",
            "threshold": NEAR_THRESHOLD_DISTANCE,
            "basis": "10th percentile of frozen selected queue",
        },
        "HIGH_MODEL_DISAGREEMENT": {
            "field": "model_disagreement_std",
            "operator": ">=",
            "threshold": DISAGREEMENT_THRESHOLD,
            "basis": "75th percentile of frozen selected queue",
        },
        "HIGH_ROUTER_SCORE": {
            "field": "fn_router_probability",
            "operator": ">=",
            "threshold": ROUTER_HIGH_THRESHOLD,
            "basis": "90th percentile of frozen selected queue",
        },
        "HIGH_DIAGNOSIS_BURDEN": {
            "field": "number_diagnoses",
            "operator": ">=",
            "threshold": DIAGNOSIS_BURDEN_THRESHOLD,
        },
        "HIGH_OUTPATIENT_UTILIZATION": {
            "field": "number_outpatient",
            "operator": ">=",
            "threshold": OUTPATIENT_THRESHOLD,
        },
        "EMERGENCY_UTILIZATION": {
            "field": "number_emergency",
            "operator": ">=",
            "threshold": EMERGENCY_THRESHOLD,
        },
        "INPATIENT_UTILIZATION": {
            "field": "number_inpatient",
            "operator": ">=",
            "threshold": INPATIENT_THRESHOLD,
        },
        "LONGER_HOSPITAL_STAY": {
            "field": "time_in_hospital",
            "operator": ">=",
            "threshold": LONG_STAY_THRESHOLD,
        },
    },

    "signal_weights": weights,

    "priority_rules": {
        "HIGH": "agent_priority_score >= 6",
        "MODERATE": "3 <= agent_priority_score < 6",
        "LOW": "agent_priority_score < 3",
    },

    "human_review_actions": {
        "HIGH": "PRIORITY_REVIEW",
        "MODERATE": "ROUTINE_REVIEW",
        "LOW": "ROUTINE_REVIEW",
    },

    "constraints": {
        "ground_truth_used_for_calibration": False,
        "may_change_primary_prediction": False,
        "may_change_primary_probability": False,
        "may_change_router_probability": False,
        "may_change_router_selection": False,
        "may_change_model_threshold": False,
        "may_change_review_budget": False,
        "may_diagnose": False,
        "may_recommend_treatment": False,
        "may_recommend_medication": False,
        "human_review_required": True,
    },
}

print(json.dumps(frozen_rules, indent=2))


# =============================================================================
# P — SAVE OUTPUTS
# =============================================================================

banner("P — SAVE CALIBRATION / FREEZE OUTPUTS")

quantile_df.to_csv(
    OUTPUT_DIR / "agent_rule_calibration_quantiles.csv",
    index=False,
)

calibration_summary.to_csv(
    CALIBRATION_FILE,
    index=False,
)

priority_distribution.to_csv(
    PRIORITY_FILE,
    index=False,
)

demographic_df.to_csv(
    OUTPUT_DIR / "agent_rule_calibrated_demographic_priority.csv",
    index=False,
)

with open(RULE_FILE, "w") as f:
    json.dump(frozen_rules, f, indent=2)

print("Saved:")
print(OUTPUT_DIR / "agent_rule_calibration_quantiles.csv")
print(CALIBRATION_FILE)
print(PRIORITY_FILE)
print(OUTPUT_DIR / "agent_rule_calibrated_demographic_priority.csv")
print(RULE_FILE)


# =============================================================================
# Q — FREEZE AUDIT
# =============================================================================

banner("Q — FINAL RULE FREEZE AUDIT")

freeze_audit = {
    "phase": "10.3.4",
    "cases": len(df_cal),
    "rule_version": "10.3.4",
    "status": "FROZEN",
    "ground_truth_used": False,
    "prohibited_fields_available": False,
    "primary_model_modified": False,
    "router_modified": False,
    "threshold_modified": False,
    "review_budget_modified": False,
    "diagnosis_allowed": False,
    "treatment_recommendation_allowed": False,
    "human_review_required": True,
    "priority_distribution": {
        row["review_priority"]: {
            "cases": int(row["cases"]),
            "percent": float(row["percent"]),
        }
        for _, row in priority_distribution.iterrows()
    },
    "quality_flags": quality_flags,
}

with open(AUDIT_FILE, "w") as f:
    json.dump(freeze_audit, f, indent=2)

print(json.dumps(freeze_audit, indent=2))

print()
passed("No ground truth used")
passed("Primary model unchanged")
passed("Rescue Router unchanged")
passed("Decision threshold unchanged")
passed("Review budget unchanged")
passed("Human review remains mandatory")


# =============================================================================
# R — RELOAD FROZEN RULES
# =============================================================================

banner("R — RELOAD FROZEN RULE PACKAGE")

with open(RULE_FILE, "r") as f:
    reloaded_rules = json.load(f)

assert reloaded_rules["rule_version"] == "10.3.4"
assert reloaded_rules["status"] == "FROZEN"
assert (
    reloaded_rules["constraints"]["ground_truth_used_for_calibration"]
    is False
)
assert (
    reloaded_rules["constraints"]["human_review_required"]
    is True
)

passed("Frozen rule package reload")
passed("Ground-truth prohibition preserved")
passed("Human-review requirement preserved")


# =============================================================================
# S — FINAL STATUS
# =============================================================================

banner("S — FINAL STATUS")

print(f"{RULE_FILE}: CREATED")
print(f"{CALIBRATION_FILE}: CREATED")
print(f"{PRIORITY_FILE}: CREATED")
print(f"{AUDIT_FILE}: CREATED")

banner("PHASE 10.3.4 COMPLETE — RULES FROZEN")

print(
    "Agent prioritization rules calibrated using only approved "
    "review-queue signals."
)

print(
    "No retrospective outcome labels were used."
)

print(
    "The frozen primary model and Rescue Router were not modified."
)

print()
print("NEXT PHASE:")
print("PHASE 10.4 — EXPLANATION AGENT")