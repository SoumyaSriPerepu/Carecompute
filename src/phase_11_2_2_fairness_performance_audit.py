from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
)
from statsmodels.stats.proportion import proportion_confint


# =============================================================================
# PATHS
# =============================================================================

DATA_PATH = Path(
    "results/eligible/final_test_end_to_end_patient_predictions.csv"
)

ELIGIBILITY_PATH = Path(
    "results/eligible/fairness/"
    "phase11_2_1_fairness_eligibility_manifest.json"
)

GROUP_PATH = Path(
    "results/eligible/fairness/"
    "phase11_2_1_group_eligibility.csv"
)

OUTPUT_DIR = Path("results/eligible/fairness")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

METRICS_PATH = (
    OUTPUT_DIR /
    "phase11_2_2_group_performance_metrics.csv"
)

AUDIT_PATH = (
    OUTPUT_DIR /
    "phase11_2_2_fairness_performance_audit.json"
)


# =============================================================================
# LOCKED ANALYSIS SETTINGS
# =============================================================================

N_BOOTSTRAP = 2000
CI_LEVEL = 0.95
ALPHA = 1.0 - CI_LEVEL
RANDOM_SEED = 20260920


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


def stratified_bootstrap_auc_pr(
    y_true,
    y_score,
    n_bootstrap=N_BOOTSTRAP,
    seed=RANDOM_SEED,
):
    """
    Stratified bootstrap:
    positives are sampled with replacement from positives,
    negatives from negatives.

    Returns percentile 95% CIs for AUROC and AUPRC.
    """

    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)

    pos_idx = np.where(y_true == 1)[0]
    neg_idx = np.where(y_true == 0)[0]

    if len(pos_idx) == 0 or len(neg_idx) == 0:
        return np.nan, np.nan, np.nan, np.nan

    rng = np.random.default_rng(seed)

    auc_values = np.empty(n_bootstrap)
    pr_values = np.empty(n_bootstrap)

    for i in range(n_bootstrap):

        sampled_pos = rng.choice(
            pos_idx,
            size=len(pos_idx),
            replace=True,
        )

        sampled_neg = rng.choice(
            neg_idx,
            size=len(neg_idx),
            replace=True,
        )

        idx = np.concatenate(
            [sampled_pos, sampled_neg]
        )

        y_b = y_true[idx]
        score_b = y_score[idx]

        auc_values[i] = roc_auc_score(
            y_b,
            score_b,
        )

        pr_values[i] = average_precision_score(
            y_b,
            score_b,
        )

    lower_q = 100 * (ALPHA / 2)
    upper_q = 100 * (1 - ALPHA / 2)

    auc_low, auc_high = np.percentile(
        auc_values,
        [lower_q, upper_q],
    )

    pr_low, pr_high = np.percentile(
        pr_values,
        [lower_q, upper_q],
    )

    return (
        float(auc_low),
        float(auc_high),
        float(pr_low),
        float(pr_high),
    )


def wilson_interval(successes, total):
    if total == 0:
        return np.nan, np.nan

    low, high = proportion_confint(
        count=successes,
        nobs=total,
        alpha=ALPHA,
        method="wilson",
    )

    return float(low), float(high)


# =============================================================================
# HEADER
# =============================================================================

section(
    "PHASE 11.2.2 — FAIRNESS PERFORMANCE AUDIT WITH CONFIDENCE INTERVALS"
)


# =============================================================================
# A — VERIFY FROZEN ELIGIBILITY
# =============================================================================

section("A — VERIFY FROZEN ELIGIBILITY POLICY")

for p in [
    DATA_PATH,
    ELIGIBILITY_PATH,
    GROUP_PATH,
]:
    if not p.exists():
        raise FileNotFoundError(p)

    print("FOUND:", p)


with ELIGIBILITY_PATH.open() as f:
    eligibility = json.load(f)


if eligibility["status"] != "FAIRNESS_ELIGIBILITY_FROZEN":
    raise RuntimeError(
        "Fairness eligibility policy is not frozen."
    )


rule = eligibility["adequacy_rule"]

print(
    "Minimum total:",
    rule["minimum_total"]
)

print(
    "Minimum positives:",
    rule["minimum_actual_positives"]
)

print(
    "Minimum negatives:",
    rule["minimum_actual_negatives"]
)

print(
    "Eligibility chosen before subgroup performance:",
    rule["rule_selected_before_group_performance"]
)

if not rule["rule_selected_before_group_performance"]:
    raise RuntimeError(
        "Eligibility was not outcome-blind with respect to "
        "subgroup performance."
    )

print("Eligibility lock: PASSED")


# =============================================================================
# B — LOAD FULL TEST POPULATION
# =============================================================================

section("B — LOAD FULL TEST POPULATION")

df = pd.read_csv(DATA_PATH)
inventory = pd.read_csv(GROUP_PATH)

required = {
    "encounter_id",
    "actual_30d",
    "predicted_30d",
    "calibrated_probability",
    "race",
    "gender",
    "age",
}

missing = required - set(df.columns)

if missing:
    raise RuntimeError(
        f"Missing columns: {sorted(missing)}"
    )


print("Test encounters:", len(df))

print(
    "Actual positives:",
    int((df["actual_30d"] == 1).sum())
)

print(
    "Actual negatives:",
    int((df["actual_30d"] == 0).sum())
)

if len(df) != 15042:
    raise RuntimeError(
        "Final test population changed."
    )

print("Population lock: PASSED")


# =============================================================================
# C — VERIFY GLOBAL PERFORMANCE
# =============================================================================

section("C — VERIFY GLOBAL PERFORMANCE")

y = df["actual_30d"].astype(int)
score = df["calibrated_probability"].astype(float)
pred = df["predicted_30d"].astype(int)

global_auc = roc_auc_score(y, score)

global_auprc = average_precision_score(
    y,
    score,
)

global_tp = int(
    ((y == 1) & (pred == 1)).sum()
)

global_fn = int(
    ((y == 1) & (pred == 0)).sum()
)

global_recall = (
    global_tp /
    (global_tp + global_fn)
)

global_fnr = (
    global_fn /
    (global_tp + global_fn)
)

print(f"Global AUROC: {global_auc:.6f}")
print(f"Global AUPRC: {global_auprc:.6f}")
print(f"Global Recall: {global_recall:.6f}")
print(f"Global FNR: {global_fnr:.6f}")

print("Global FN:", global_fn)

if global_fn != 557:
    raise RuntimeError(
        "Global false-negative lock failed."
    )

print("Global performance verification: PASSED")


# =============================================================================
# D — ANALYSIS SETTINGS
# =============================================================================

section("D — CONFIDENCE-INTERVAL SETTINGS")

print("AUROC/AUPRC CI method: stratified bootstrap")
print("Bootstrap replicates:", N_BOOTSTRAP)
print("Bootstrap seed:", RANDOM_SEED)

print(
    "Recall/FNR CI method: Wilson binomial interval"
)

print(
    "Confidence level:",
    CI_LEVEL
)

print()
print(
    "Bootstrap resampling is performed within each "
    "subgroup and preserves positive/negative sample counts."
)


# =============================================================================
# E — CALCULATE ELIGIBLE-GROUP PERFORMANCE
# =============================================================================

section("E — CALCULATE ELIGIBLE-GROUP PERFORMANCE")

records = []

eligible_inventory = inventory[
    inventory["adequate_sample"] == True
].copy()


for attribute in ["race", "gender", "age"]:

    groups = eligible_inventory.loc[
        eligible_inventory["attribute"] == attribute,
        "group"
    ].tolist()

    for group in groups:

        if group == "MISSING":

            mask = df[attribute].isna()

        else:

            mask = (
                df[attribute].astype(str)
                == str(group)
            )

        g = df.loc[mask].copy()

        y_g = g["actual_30d"].astype(int).to_numpy()

        score_g = (
            g["calibrated_probability"]
            .astype(float)
            .to_numpy()
        )

        pred_g = (
            g["predicted_30d"]
            .astype(int)
            .to_numpy()
        )

        n_total = len(g)
        n_positive = int((y_g == 1).sum())
        n_negative = int((y_g == 0).sum())

        tp = int(
            ((y_g == 1) & (pred_g == 1)).sum()
        )

        fn = int(
            ((y_g == 1) & (pred_g == 0)).sum()
        )

        tn = int(
            ((y_g == 0) & (pred_g == 0)).sum()
        )

        fp = int(
            ((y_g == 0) & (pred_g == 1)).sum()
        )

        auc = roc_auc_score(
            y_g,
            score_g,
        )

        auprc = average_precision_score(
            y_g,
            score_g,
        )

        recall = (
            tp / (tp + fn)
            if (tp + fn)
            else np.nan
        )

        fnr = (
            fn / (tp + fn)
            if (tp + fn)
            else np.nan
        )

        (
            auc_low,
            auc_high,
            auprc_low,
            auprc_high,
        ) = stratified_bootstrap_auc_pr(
            y_g,
            score_g,
        )

        recall_low, recall_high = (
            wilson_interval(
                tp,
                tp + fn,
            )
        )

        fnr_low, fnr_high = (
            wilson_interval(
                fn,
                tp + fn,
            )
        )

        records.append({
            "attribute": attribute,
            "group": group,

            "n_total": n_total,
            "n_positive": n_positive,
            "n_negative": n_negative,

            "tp": tp,
            "fn": fn,
            "tn": tn,
            "fp": fp,

            "auroc": auc,
            "auroc_ci_low": auc_low,
            "auroc_ci_high": auc_high,

            "auprc": auprc,
            "auprc_ci_low": auprc_low,
            "auprc_ci_high": auprc_high,

            "recall": recall,
            "recall_ci_low": recall_low,
            "recall_ci_high": recall_high,

            "fnr": fnr,
            "fnr_ci_low": fnr_low,
            "fnr_ci_high": fnr_high,

            "positive_prevalence":
                n_positive / n_total,

            "adequate_sample": True,

            "interpret_as_demographic_group":
                False
                if (
                    attribute == "race"
                    and group == "MISSING"
                )
                else True,
        })


metrics = pd.DataFrame(records)

metrics.to_csv(
    METRICS_PATH,
    index=False
)

print(
    metrics[
        [
            "attribute",
            "group",
            "n_total",
            "n_positive",
            "auroc",
            "auroc_ci_low",
            "auroc_ci_high",
            "auprc",
            "auprc_ci_low",
            "auprc_ci_high",
            "recall",
            "recall_ci_low",
            "recall_ci_high",
            "fnr",
            "fnr_ci_low",
            "fnr_ci_high",
        ]
    ].to_string(index=False)
)

print()
print("Saved:", METRICS_PATH)


# =============================================================================
# F — REPORT UNDERPOWERED GROUPS
# =============================================================================

section("F — UNDERPOWERED GROUPS")

underpowered = inventory[
    inventory["adequate_sample"] == False
].copy()

if len(underpowered):

    print(
        underpowered[
            [
                "attribute",
                "group",
                "n_total",
                "n_positive",
                "n_negative",
                "inadequacy_reason",
            ]
        ].to_string(index=False)
    )

else:
    print("None")

print()
print(
    "Underpowered groups are disclosed but are not used "
    "for primary subgroup performance inference."
)


# =============================================================================
# G — DESCRIPTIVE PERFORMANCE GAPS
# =============================================================================

section("G — DESCRIPTIVE PERFORMANCE GAPS")

gap_records = []

for attribute in ["race", "gender", "age"]:

    attr = metrics[
        (metrics["attribute"] == attribute)
        & (
            metrics[
                "interpret_as_demographic_group"
            ] == True
        )
    ].copy()

    if len(attr) < 2:
        continue

    for metric in [
        "auroc",
        "auprc",
        "recall",
        "fnr",
    ]:

        max_idx = attr[metric].idxmax()
        min_idx = attr[metric].idxmin()

        maximum = float(
            attr.loc[max_idx, metric]
        )

        minimum = float(
            attr.loc[min_idx, metric]
        )

        gap = maximum - minimum

        max_group = str(
            attr.loc[max_idx, "group"]
        )

        min_group = str(
            attr.loc[min_idx, "group"]
        )

        gap_records.append({
            "attribute": attribute,
            "metric": metric,
            "maximum": maximum,
            "maximum_group": max_group,
            "minimum": minimum,
            "minimum_group": min_group,
            "absolute_range": gap,
        })

        print(
            f"{attribute} | {metric}: "
            f"range={gap:.6f} "
            f"({min_group}={minimum:.6f}, "
            f"{max_group}={maximum:.6f})"
        )


# =============================================================================
# H — AUDIT INTERPRETATION BOUNDARY
# =============================================================================

section("H — INTERPRETATION BOUNDARY")

print(
    "Confidence intervals quantify sampling uncertainty; "
    "they do not prove equality or fairness."
)

print(
    "Overlapping confidence intervals do not establish "
    "absence of disparity."
)

print(
    "Non-overlapping confidence intervals are not, by "
    "themselves, a formal multiple-comparison test."
)

print(
    "AUPRC depends on outcome prevalence and therefore "
    "must be interpreted alongside subgroup prevalence."
)

print(
    "The MISSING race category is audited for missingness "
    "behavior but is not interpreted as a racial group."
)

print(
    "This remains a retrospective model audit, not proof "
    "of clinical fairness."
)


# =============================================================================
# I — CREATE AUDIT ARTIFACT
# =============================================================================

section("I — CREATE FAIRNESS PERFORMANCE ARTIFACT")

audit = {
    "phase": "11.2.2",

    "audit_name":
        "Subgroup Performance with Confidence Intervals",

    "status":
        "FAIRNESS_PERFORMANCE_AUDIT_COMPLETE",

    "population": {
        "test_encounters": int(len(df)),
        "actual_positives":
            int((y == 1).sum()),
        "actual_negatives":
            int((y == 0).sum()),
    },

    "global_performance": {
        "auroc": float(global_auc),
        "auprc": float(global_auprc),
        "recall": float(global_recall),
        "fnr": float(global_fnr),
    },

    "ci_method": {
        "auroc_auprc":
            "stratified percentile bootstrap",
        "bootstrap_replicates":
            N_BOOTSTRAP,
        "bootstrap_seed":
            RANDOM_SEED,
        "recall_fnr":
            "Wilson binomial confidence interval",
        "confidence_level":
            CI_LEVEL,
    },

    "eligibility_policy": {
        "manifest":
            str(ELIGIBILITY_PATH),
        "manifest_sha256":
            sha256_file(ELIGIBILITY_PATH),
        "policy_modified":
            False,
    },

    "eligible_group_count":
        int(len(metrics)),

    "underpowered_group_count":
        int(len(underpowered)),

    "descriptive_gaps":
        gap_records,

    "special_handling": {
        "missing_race_category_reported":
            True,
        "missing_race_interpreted_as_racial_group":
            False,
    },

    "claims_boundary": {
        "clinical_fairness_established":
            False,
        "formal_disparity_hypothesis_tests_performed":
            False,
        "multiple_comparison_adjustment_performed":
            False,
        "audit_only":
            True,
    },

    "integrity": {
        "phase10_modified":
            False,
        "eligibility_policy_modified":
            False,
        "input_sha256":
            sha256_file(DATA_PATH),
        "metrics_sha256":
            sha256_file(METRICS_PATH),
    },

    "next_phase":
        "11.2.3 Compute Allocation Audit",
}


with AUDIT_PATH.open("w") as f:
    json.dump(
        audit,
        f,
        indent=2
    )

print("Audit artifact:", AUDIT_PATH)


# =============================================================================
# J — FINAL VERIFICATION
# =============================================================================

section("J — FINAL VERIFICATION")

with AUDIT_PATH.open() as f:
    saved = json.load(f)

checks = {
    "status":
        saved["status"]
        == "FAIRNESS_PERFORMANCE_AUDIT_COMPLETE",

    "population":
        saved["population"][
            "test_encounters"
        ] == 15042,

    "fn_lock":
        global_fn == 557,

    "eligibility_unchanged":
        saved["eligibility_policy"][
            "policy_modified"
        ] is False,

    "eligible_count":
        saved["eligible_group_count"]
        == int(len(eligible_inventory)),

    "underpowered_disclosed":
        saved["underpowered_group_count"]
        == int(len(underpowered)),

    "missing_race_not_demographic":
        saved["special_handling"][
            "missing_race_interpreted_as_racial_group"
        ] is False,

    "no_clinical_fairness_claim":
        saved["claims_boundary"][
            "clinical_fairness_established"
        ] is False,

    "phase10_unchanged":
        saved["integrity"][
            "phase10_modified"
        ] is False,

    "metrics_artifact":
        METRICS_PATH.exists(),
}

for name, passed in checks.items():

    print(
        name + ":",
        "PASSED" if passed else "FAILED"
    )

if not all(checks.values()):

    raise RuntimeError(
        "Phase 11.2.2 verification failed."
    )


# =============================================================================
# COMPLETE
# =============================================================================

section(
    "PHASE 11.2.2 COMPLETE — SUBGROUP PERFORMANCE AUDIT PASSED"
)

print(
    "Eligible groups evaluated:",
    len(metrics)
)

print(
    "Underpowered groups disclosed:",
    len(underpowered)
)

print(
    "Metrics: AUROC, AUPRC, Recall, FNR"
)

print(
    "95% confidence intervals: YES"
)

print(
    "Clinical fairness established: NO"
)

print(
    "Phase 10 frozen system modified: NO"
)

print()
print(
    "NEXT: 11.2.3 — COMPUTE ALLOCATION AUDIT "
    "(agent calls, tokens, latency by group)"
)
