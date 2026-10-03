from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# PHASE 9.1 — FINAL PUBLICATION TABLES
# ============================================================

print("=" * 80)
print("PHASE 9.1 — FINAL PUBLICATION TABLES")
print("=" * 80)


# ============================================================
# PATHS
# ============================================================

RESULTS_DIR = Path("results/eligible")
OUTPUT_DIR = RESULTS_DIR / "publication_tables"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# HELPER
# ============================================================

def save_table(df, filename, title):

    path = OUTPUT_DIR / filename

    df.to_csv(
        path,
        index=False
    )

    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    print(
        df.to_string(
            index=False
        )
    )

    print("\nSaved:")
    print(path)


# ============================================================
# TABLE 1
# PRIMARY MODEL PERFORMANCE
# ============================================================

metrics_file = (
    RESULTS_DIR
    / "final_test_metrics.csv"
)

metrics = pd.read_csv(
    metrics_file
)

table1 = metrics[
    [
        "threshold",
        "AUROC",
        "AUPRC",
        "Recall",
        "Precision",
        "F1",
        "FNR",
        "Specificity",
        "Brier",
        "TN",
        "FP",
        "FN",
        "TP"
    ]
].copy()


# Convert selected rates to percentages

percent_columns = [
    "Recall",
    "Precision",
    "F1",
    "FNR",
    "Specificity"
]

for col in percent_columns:
    table1[col] = (
        table1[col] * 100
    )


table1 = table1.rename(
    columns={
        "threshold": "Decision Threshold",
        "AUROC": "AUROC",
        "AUPRC": "AUPRC",
        "Recall": "Recall (%)",
        "Precision": "Precision (%)",
        "F1": "F1 (%)",
        "FNR": "False Negative Rate (%)",
        "Specificity": "Specificity (%)",
        "Brier": "Brier Score",
        "TN": "TN",
        "FP": "FP",
        "FN": "FN",
        "TP": "TP"
    }
)


save_table(
    table1,
    "table_1_primary_model_performance.csv",
    "TABLE 1 — PRIMARY MODEL FINAL TEST PERFORMANCE"
)


# ============================================================
# TABLE 2
# LOCKED 15% REVIEW STRATEGY COMPARISON
# ============================================================

sensitivity_file = (
    RESULTS_DIR
    / "final_test_router_sensitivity.csv"
)

sensitivity = pd.read_csv(
    sensitivity_file
)

table2 = sensitivity[
    np.isclose(
        sensitivity["budget"],
        0.15
    )
].copy()


table2["FN Capture Rate (%)"] = (
    table2["fn_capture_rate"] * 100
)

table2["Review Precision (%)"] = (
    table2["review_precision"] * 100
)

if "overall_test_review_rate" in table2.columns:

    table2["Overall Test Review Rate (%)"] = (
        table2["overall_test_review_rate"] * 100
    )


table2["FN Captured"] = (
    table2["fn_captured"].round(2)
)


keep_columns = [
    "method",
    "patients_reviewed"
]

if "Overall Test Review Rate (%)" in table2.columns:
    keep_columns.append(
        "Overall Test Review Rate (%)"
    )

keep_columns += [
    "FN Captured",
    "FN Capture Rate (%)",
    "Review Precision (%)"
]


table2 = table2[
    keep_columns
].copy()


table2 = table2.rename(
    columns={
        "method": "Review Strategy",
        "patients_reviewed": "Patients Reviewed"
    }
)


strategy_order = [
    "Probability",
    "Rescue Router",
    "Disagreement",
    "Random"
]

table2["order"] = (
    table2["Review Strategy"]
    .map(
        {
            name: i
            for i, name
            in enumerate(strategy_order)
        }
    )
)

table2 = (
    table2
    .sort_values("order")
    .drop(columns="order")
)


save_table(
    table2,
    "table_2_locked_15pct_review_comparison.csv",
    "TABLE 2 — LOCKED 15% LOW-RISK REVIEW COMPARISON"
)


# ============================================================
# TABLE 3
# BOOTSTRAP INFERENCE
# ============================================================

bootstrap_ci_file = (
    RESULTS_DIR
    / "final_test_bootstrap_confidence_intervals.csv"
)

bootstrap_comparison_file = (
    RESULTS_DIR
    / "final_test_bootstrap_paired_comparisons.csv"
)

bootstrap_ci = pd.read_csv(
    bootstrap_ci_file
)

bootstrap_comparisons = pd.read_csv(
    bootstrap_comparison_file
)


table3a = bootstrap_ci.copy()

for col in [
    "point_estimate",
    "bootstrap_mean",
    "ci_lower",
    "ci_upper"
]:

    table3a[col] = (
        table3a[col] * 100
    )


table3a = table3a.rename(
    columns={
        "method": "Review Strategy",
        "point_estimate": "Point FN Capture (%)",
        "bootstrap_mean": "Bootstrap Mean (%)",
        "ci_lower": "95% CI Lower (%)",
        "ci_upper": "95% CI Upper (%)"
    }
)


save_table(
    table3a,
    "table_3a_bootstrap_confidence_intervals.csv",
    "TABLE 3A — BOOTSTRAP CONFIDENCE INTERVALS"
)


table3b = bootstrap_comparisons.copy()
# Convert bootstrap comparison probabilities to percentages
for col in [
    "probability_a_better",
    "probability_equal",
    "probability_a_worse"
]:
    if col in table3b.columns:
        table3b[col] = table3b[col] * 100

for col in [
    "mean_difference",
    "ci_lower",
    "ci_upper"
]:

    table3b[col] = (
        table3b[col] * 100
    )


table3b = table3b.rename(
    columns={
        "comparison": "Comparison",
        "mean_difference": "Mean Difference (pp)",
        "ci_lower": "95% CI Lower (pp)",
        "ci_upper": "95% CI Upper (pp)",
        "bootstrap_p_value": "Bootstrap p-value",
        "probability_a_better": "P(A Better) (%)",
        "probability_equal": "P(Equal) (%)",
        "probability_a_worse": "P(A Worse) (%)"
    }
)


save_table(
    table3b,
    "table_3b_paired_bootstrap_comparisons.csv",
    "TABLE 3B — PAIRED BOOTSTRAP COMPARISONS"
)


# ============================================================
# TABLE 4
# FINAL TEST FAIRNESS
# ============================================================

fairness_file = (
    RESULTS_DIR
    / "final_test_fairness_subgroup_rates.csv"
)

fairness = pd.read_csv(
    fairness_file
)


table4 = fairness.copy()


for col in [
    "fn_rescue_rate",
    "ci_lower",
    "ci_upper"
]:

    table4[col] = (
        table4[col] * 100
    )


table4 = table4.rename(
    columns={
        "feature": "Demographic Feature",
        "group": "Group",
        "total_false_negatives": "False Negatives",
        "rescued_false_negatives": "Rescued FN",
        "missed_false_negatives": "Residual FN",
        "fn_rescue_rate": "FN Rescue Rate (%)",
        "ci_lower": "95% CI Lower (%)",
        "ci_upper": "95% CI Upper (%)"
    }
)


save_table(
    table4,
    "table_4_subgroup_fn_rescue_rates.csv",
    "TABLE 4 — SUBGROUP FALSE-NEGATIVE RESCUE"
)


# ============================================================
# TABLE 5
# END-TO-END SIMULATED IMPACT
# ============================================================

e2e_file = (
    RESULTS_DIR
    / "final_test_end_to_end_fairness.csv"
)

e2e = pd.read_csv(
    e2e_file
)


table5 = e2e.copy()


# These columns were saved as fractions in the source CSV.
for col in [
    "primary_fnr",
    "simulated_residual_fnr",
    "absolute_fnr_reduction",
    "conditional_fn_rescue_rate"
]:

    if table5[col].max() <= 1.0:
        table5[col] = (
            table5[col] * 100
        )


table5 = table5.rename(
    columns={
        "feature": "Demographic Feature",
        "group": "Group",
        "actual_positives": "Actual Positives",
        "true_positives": "True Positives",
        "false_negatives": "False Negatives",
        "rescued_false_negatives": "Rescued FN",
        "primary_fnr": "Primary FNR (%)",
        "simulated_residual_fnr":
            "Simulated Residual FNR (%)",
        "absolute_fnr_reduction":
            "Absolute FNR Reduction (pp)",
        "conditional_fn_rescue_rate":
            "Conditional FN Rescue (%)"
    }
)


save_table(
    table5,
    "table_5_end_to_end_fairness_impact.csv",
    "TABLE 5 — SIMULATED END-TO-END FAIRNESS IMPACT"
)


# ============================================================
# TABLE 6
# KEY RESULTS SUMMARY
# ============================================================

primary = metrics.iloc[0]

router15 = sensitivity[
    (
        np.isclose(
            sensitivity["budget"],
            0.15
        )
    )
    &
    (
        sensitivity["method"]
        == "Rescue Router"
    )
].iloc[0]


random15 = sensitivity[
    (
        np.isclose(
            sensitivity["budget"],
            0.15
        )
    )
    &
    (
        sensitivity["method"]
        == "Random"
    )
].iloc[0]


prob15 = sensitivity[
    (
        np.isclose(
            sensitivity["budget"],
            0.15
        )
    )
    &
    (
        sensitivity["method"]
        == "Probability"
    )
].iloc[0]


table6 = pd.DataFrame(
    [
        {
            "Result":
                "Primary model AUROC",
            "Value":
                primary["AUROC"]
        },
        {
            "Result":
                "Primary model AUPRC",
            "Value":
                primary["AUPRC"]
        },
        {
            "Result":
                "Primary model recall (%)",
            "Value":
                primary["Recall"] * 100
        },
        {
            "Result":
                "Primary model false negatives",
            "Value":
                primary["FN"]
        },
        {
            "Result":
                "Rescue router FN capture at 15% (%)",
            "Value":
                router15["fn_capture_rate"] * 100
        },
        {
            "Result":
                "Probability FN capture at 15% (%)",
            "Value":
                prob15["fn_capture_rate"] * 100
        },
        {
            "Result":
                "Random FN capture at 15% (%)",
            "Value":
                random15["fn_capture_rate"] * 100
        },
        {
            "Result":
                "Router lift over random",
            "Value":
                (
                    router15["fn_capture_rate"]
                    /
                    random15["fn_capture_rate"]
                )
        },
        {
            "Result":
                "Primary FNR (%)",
            "Value":
                32.09
        },
        {
            "Result":
                "Simulated residual FNR (%)",
            "Value":
                25.75
        },
        {
            "Result":
                "Absolute FNR reduction (pp)",
            "Value":
                6.34
        }
    ]
)


save_table(
    table6,
    "table_6_key_results_summary.csv",
    "TABLE 6 — KEY RESULTS SUMMARY"
)


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 80)
print("PHASE 9.1 COMPLETE")
print("=" * 80)

print("\nPublication tables directory:")
print(OUTPUT_DIR)

print("\nFiles:")

for f in sorted(
    OUTPUT_DIR.glob("*.csv")
):

    print(" -", f)