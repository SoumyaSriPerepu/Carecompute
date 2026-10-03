from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# PHASE 8.3 — PUBLICATION FIGURES
# FIGURE 1: FN CAPTURE VS REVIEW BUDGET
# ============================================================

INPUT_FILE = Path(
    "results/eligible/final_test_router_sensitivity.csv"
)

OUTPUT_DIR = Path(
    "results/eligible/figures"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(INPUT_FILE)

print("=" * 80)
print("PHASE 8.3.1 — FN CAPTURE VS REVIEW BUDGET")
print("=" * 80)

print("\nInput shape:", df.shape)

print("\nColumns:")
for col in df.columns:
    print(" -", col)

print("\nMethods:")
print(df["method"].unique())

print("\nBudgets:")
print(sorted(df["budget"].unique()))


# ============================================================
# VALIDATE
# ============================================================

required_columns = [
    "budget",
    "method",
    "fn_capture_rate"
]

missing = [
    col
    for col in required_columns
    if col not in df.columns
]

assert not missing, (
    f"Missing required columns: {missing}"
)

expected_methods = {
    "Probability",
    "Disagreement",
    "Rescue Router",
    "Random"
}

actual_methods = set(
    df["method"].unique()
)

assert expected_methods.issubset(
    actual_methods
), (
    "Expected methods not found. "
    f"Found: {actual_methods}"
)


# ============================================================
# PREPARE DATA
# ============================================================

plot_df = df.copy()

plot_df["review_budget_percent"] = (
    plot_df["budget"] * 100
)

plot_df["fn_capture_percent"] = (
    plot_df["fn_capture_rate"] * 100
)

plot_df = plot_df.sort_values(
    [
        "method",
        "budget"
    ]
)


# ============================================================
# CREATE FIGURE
# ============================================================

fig, ax = plt.subplots(
    figsize=(8.5, 5.5)
)

methods = [
    "Probability",
    "Disagreement",
    "Rescue Router",
    "Random"
]

markers = {
    "Probability": "o",
    "Disagreement": "s",
    "Rescue Router": "^",
    "Random": "x"
}

linestyles = {
    "Probability": "-",
    "Disagreement": "-",
    "Rescue Router": "-",
    "Random": "--"
}

for method in methods:

    subset = plot_df[
        plot_df["method"] == method
    ].sort_values("budget")

    ax.plot(
        subset["review_budget_percent"],
        subset["fn_capture_percent"],
        marker=markers[method],
        linestyle=linestyles[method],
        linewidth=2,
        markersize=6,
        label=method
    )


# ============================================================
# LOCKED OPERATING POINT
# ============================================================

ax.axvline(
    x=15,
    linestyle=":",
    linewidth=1.5
)

ax.text(
    15.8,
    55,
    "Locked 15% review budget",
    rotation=90,
    va="top",
    fontsize=9
)


# ============================================================
# LABELS
# ============================================================

ax.set_xlabel(
    "Low-Risk Review Budget (%)",
    fontsize=11
)

ax.set_ylabel(
    "False Negatives Captured (%)",
    fontsize=11
)

ax.set_title(
    "False-Negative Capture Across Review Budgets",
    fontsize=13,
    pad=12
)

ax.grid(
    alpha=0.25
)

ax.legend(
    frameon=False
)

ax.set_xlim(
    3,
    52
)

ax.set_ylim(
    0,
    max(
        plot_df["fn_capture_percent"]
    ) + 5
)

fig.tight_layout()


# ============================================================
# SAVE
# ============================================================

png_file = (
    OUTPUT_DIR
    / "figure_1_fn_capture_vs_review_budget.png"
)

pdf_file = (
    OUTPUT_DIR
    / "figure_1_fn_capture_vs_review_budget.pdf"
)

fig.savefig(
    png_file,
    dpi=300,
    bbox_inches="tight"
)

fig.savefig(
    pdf_file,
    bbox_inches="tight"
)

plt.close(fig)


# ============================================================
# PRINT LOCKED 15% VALUES
# ============================================================

locked = plot_df[
    plot_df["budget"] == 0.15
][
    [
        "method",
        "fn_capture_percent"
    ]
].copy()

print("\n" + "=" * 80)
print("LOCKED 15% OPERATING POINT")
print("=" * 80)

print(
    locked.to_string(
        index=False
    )
)

print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print(png_file)
print(pdf_file)

print("\n" + "=" * 80)
print("PHASE 8.3.1 COMPLETE")
print("=" * 80)

# ============================================================
# PHASE 8.3.2
# FIGURE 2 — LOCKED 15% FN CAPTURE WITH BOOTSTRAP 95% CI
# ============================================================

print("\n" + "=" * 80)
print("PHASE 8.3.2 — LOCKED 15% BOOTSTRAP COMPARISON")
print("=" * 80)

BOOTSTRAP_FILE = Path(
    "results/eligible/final_test_bootstrap_confidence_intervals.csv"
)

bootstrap_df = pd.read_csv(
    BOOTSTRAP_FILE
)

print("\nBootstrap input shape:", bootstrap_df.shape)

print("\nColumns:")
for col in bootstrap_df.columns:
    print(" -", col)

print("\nBootstrap results:")
print(
    bootstrap_df.to_string(
        index=False
    )
)


# ============================================================
# VALIDATE
# ============================================================

required_bootstrap_columns = [
    "method",
    "point_estimate",
    "ci_lower",
    "ci_upper"
]

missing = [
    col
    for col in required_bootstrap_columns
    if col not in bootstrap_df.columns
]

assert not missing, (
    f"Missing bootstrap columns: {missing}"
)


# ============================================================
# ORDER METHODS
# ============================================================

method_order = [
    "Probability",
    "Rescue Router",
    "Disagreement",
    "Random"
]

fig2_df = (
    bootstrap_df
    .set_index("method")
    .loc[method_order]
    .reset_index()
)
# Convert proportions to percentages for plotting
for col in [
    "point_estimate",
    "bootstrap_mean",
    "ci_lower",
    "ci_upper"
]:
    fig2_df[col] = fig2_df[col] * 100

# ============================================================
# ERROR BAR DISTANCES
# ============================================================

fig2_df["lower_error"] = (
    fig2_df["point_estimate"]
    - fig2_df["ci_lower"]
)

fig2_df["upper_error"] = (
    fig2_df["ci_upper"]
    - fig2_df["point_estimate"]
)

# Numerical protection in case bootstrap rounding causes
# a tiny negative error distance.
fig2_df["lower_error"] = (
    fig2_df["lower_error"]
    .clip(lower=0)
)

fig2_df["upper_error"] = (
    fig2_df["upper_error"]
    .clip(lower=0)
)


# ============================================================
# CREATE FIGURE
# ============================================================

fig2, ax2 = plt.subplots(
    figsize=(8, 5.5)
)

x_positions = range(
    len(fig2_df)
)

bars = ax2.bar(
    x_positions,
    fig2_df["point_estimate"],
    width=0.65
)

ax2.errorbar(
    x_positions,
    fig2_df["point_estimate"],
    yerr=[
        fig2_df["lower_error"],
        fig2_df["upper_error"]
    ],
    fmt="none",
    capsize=5,
    linewidth=1.5
)


# ============================================================
# RANDOM EXPECTATION REFERENCE
# ============================================================

random_value = float(
    fig2_df.loc[
        fig2_df["method"] == "Random",
        "point_estimate"
    ].iloc[0]
)

ax2.axhline(
    y=random_value,
    linestyle="--",
    linewidth=1.3
)

ax2.text(
    3.45,
    random_value + 0.35,
    "Random expectation",
    ha="right",
    va="bottom",
    fontsize=9
)


# ============================================================
# VALUE LABELS
# ============================================================

for bar, value in zip(
    bars,
    fig2_df["point_estimate"]
):

    ax2.text(
        bar.get_x()
        + bar.get_width() / 2,
        bar.get_height() + 0.7,
        f"{value:.1f}%",
        ha="center",
        va="bottom",
        fontsize=10
    )


# ============================================================
# AXES
# ============================================================

ax2.set_xticks(
    list(x_positions)
)

ax2.set_xticklabels(
    fig2_df["method"]
)

ax2.set_ylabel(
    "False Negatives Captured (%)",
    fontsize=11
)

ax2.set_xlabel(
    "Review Prioritization Strategy",
    fontsize=11
)

ax2.set_title(
    "False-Negative Capture at the Locked 15% Review Budget",
    fontsize=13,
    pad=12
)

ax2.set_ylim(
    0,
    max(fig2_df["ci_upper"]) + 5
)

ax2.grid(
    axis="y",
    alpha=0.25
)

fig2.tight_layout()


# ============================================================
# SAVE FIGURE 2
# ============================================================

figure2_png = (
    OUTPUT_DIR
    / "figure_2_locked_15pct_bootstrap.png"
)

figure2_pdf = (
    OUTPUT_DIR
    / "figure_2_locked_15pct_bootstrap.pdf"
)

fig2.savefig(
    figure2_png,
    dpi=300,
    bbox_inches="tight"
)

fig2.savefig(
    figure2_pdf,
    bbox_inches="tight"
)

plt.close(fig2)


# ============================================================
# PRINT FINAL VALUES
# ============================================================

print("\n" + "=" * 80)
print("FIGURE 2 VALUES")
print("=" * 80)

print(
    fig2_df[
        [
            "method",
            "point_estimate",
            "ci_lower",
            "ci_upper"
        ]
    ].to_string(
        index=False
    )
)

print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print(figure2_png)
print(figure2_pdf)

print("\n" + "=" * 80)
print("PHASE 8.3.2 COMPLETE")
print("=" * 80)

# ============================================================
# PHASE 8.3.3
# FAIRNESS FIGURES — SUBGROUP FN RESCUE RATES
# ============================================================

print("\n" + "=" * 80)
print("PHASE 8.3.3 — FAIRNESS FIGURES")
print("=" * 80)

FAIRNESS_FILE = Path(
    "results/eligible/final_test_fairness_subgroup_rates.csv"
)

fairness_df = pd.read_csv(FAIRNESS_FILE)

print("\nInput shape:", fairness_df.shape)

print("\nColumns:")
for col in fairness_df.columns:
    print(" -", col)

print("\nFeatures:")
print(fairness_df["feature"].unique())


# ============================================================
# VALIDATE
# ============================================================

required = [
    "feature",
    "group",
    "total_false_negatives",
    "rescued_false_negatives",
    "fn_rescue_rate",
    "ci_lower",
    "ci_upper"
]

missing = [
    col for col in required
    if col not in fairness_df.columns
]

assert not missing, (
    f"Missing fairness columns: {missing}"
)


# ============================================================
# HELPER FUNCTION
# ============================================================

def make_fairness_figure(
    data,
    feature,
    group_order,
    filename,
    title
):

    subset = data[
        data["feature"] == feature
    ].copy()

    subset["group"] = (
        subset["group"]
        .fillna("Missing")
        .astype(str)
    )

    subset = (
        subset
        .set_index("group")
        .reindex(group_order)
        .dropna(
            subset=["fn_rescue_rate"]
        )
        .reset_index()
    )

    # Phase 8.2 CSV already stores these values
    # as percentages, e.g. 20.48 = 20.48%.
   # Convert proportions to percentages for plotting
    rates = subset["fn_rescue_rate"] * 100

    ci_lower = subset["ci_lower"] * 100
    ci_upper = subset["ci_upper"] * 100

    lower_error = (
    rates - ci_lower
    ).clip(lower=0)

    upper_error = (
    ci_upper - rates
    ).clip(lower=0)

    lower_error = (
        rates - subset["ci_lower"]
    ).clip(lower=0)

    upper_error = (
        subset["ci_upper"] - rates
    ).clip(lower=0)

    fig, ax = plt.subplots(
        figsize=(8.5, 5.5)
    )

    x = range(len(subset))

    bars = ax.bar(
        x,
        rates,
        width=0.65
    )

    ax.errorbar(
        x,
        rates,
        yerr=[
            lower_error,
            upper_error
        ],
        fmt="none",
        capsize=5,
        linewidth=1.5
    )

    # Overall locked rescue rate
    overall_rate = 19.748654

    ax.axhline(
        y=overall_rate,
        linestyle="--",
        linewidth=1.3,
        label="Overall rescue rate (19.75%)"
    )

    # Add n and percentage above each bar
    for bar, rate, n in zip(
        bars,
        rates,
        subset["total_false_negatives"]
    ):

        ax.text(
            bar.get_x()
            + bar.get_width() / 2,
            bar.get_height() + 1.2,
            f"{rate:.1f}%\n(n={int(n)})",
            ha="center",
            va="bottom",
            fontsize=9
        )

    ax.set_xticks(
        list(x)
    )

    ax.set_xticklabels(
        subset["group"],
        rotation=30
        if feature != "gender"
        else 0,
        ha="right"
        if feature != "gender"
        else "center"
    )

    ax.set_ylabel(
        "False-Negative Rescue Rate (%)",
        fontsize=11
    )

    ax.set_xlabel(
        feature.capitalize(),
        fontsize=11
    )

    ax.set_title(
        title,
        fontsize=13,
        pad=12
    )

    ymax = max(
    ci_upper.max() + 8,
    35
)

    ax.set_ylim(
        0,
        ymax
    )

    ax.grid(
        axis="y",
        alpha=0.25
    )

    ax.legend(
        frameon=False
    )

    fig.tight_layout()

    png = OUTPUT_DIR / f"{filename}.png"
    pdf = OUTPUT_DIR / f"{filename}.pdf"

    fig.savefig(
        png,
        dpi=300,
        bbox_inches="tight"
    )

    fig.savefig(
        pdf,
        bbox_inches="tight"
    )

    plt.close(fig)

    print("\n", feature.upper())
    print(
        subset[
            [
                "group",
                "total_false_negatives",
                "rescued_false_negatives",
                "fn_rescue_rate",
                "ci_lower",
                "ci_upper"
            ]
        ].to_string(index=False)
    )

    print("\nSaved:")
    print(png)
    print(pdf)


# ============================================================
# FIGURE 3A — GENDER
# ============================================================

make_fairness_figure(
    fairness_df,
    feature="gender",
    group_order=[
        "Female",
        "Male"
    ],
    filename="figure_3a_gender_fn_rescue",
    title="False-Negative Rescue Rate by Gender"
)


# ============================================================
# FIGURE 3B — RACE
# ============================================================

make_fairness_figure(
    fairness_df,
    feature="race",
    group_order=[
        "AfricanAmerican",
        "Asian",
        "Caucasian",
        "Hispanic",
        "Other",
        "Missing"
    ],
    filename="figure_3b_race_fn_rescue",
    title="False-Negative Rescue Rate by Race"
)


# ============================================================
# FIGURE 3C — AGE
# ============================================================

make_fairness_figure(
    fairness_df,
    feature="age",
    group_order=[
        "[10-20)",
        "[20-30)",
        "[30-40)",
        "[40-50)",
        "[50-60)",
        "[60-70)",
        "[70-80)",
        "[80-90)",
        "[90-100)"
    ],
    filename="figure_3c_age_fn_rescue",
    title="False-Negative Rescue Rate by Age Group"
)


print("\n" + "=" * 80)
print("PHASE 8.3.3 COMPLETE")
print("=" * 80)

# ============================================================
# PHASE 8.3.4
# END-TO-END PERFECT-REVIEW SIMULATION
# ============================================================

print("\n" + "=" * 80)
print("PHASE 8.3.4 — END-TO-END PERFECT-REVIEW SIMULATION")
print("=" * 80)

ROUTER_PREDICTIONS_FILE = Path(
    "results/eligible/final_test_router_predictions.csv"
)

router_test = pd.read_csv(
    ROUTER_PREDICTIONS_FILE
)

print("\nInput shape:", router_test.shape)


# ============================================================
# IMPORTANT:
# final_test_router_predictions.csv contains LOW-RISK patients
# only. Therefore:
#
# FN counts and rescued FN counts come from router_test.
# TP counts must come from the original final test population.
# ============================================================

FINAL_METRICS_FILE = Path(
    "results/eligible/final_test_metrics.csv"
)

final_metrics = pd.read_csv(
    FINAL_METRICS_FILE
)

total_fn = int(
    final_metrics.loc[0, "FN"]
)

total_tp = int(
    final_metrics.loc[0, "TP"]
)

rescued_fn = int(
    (
        (router_test["case_type"] == "FN")
        &
        (router_test["selected_for_review"] == 1)
    ).sum()
)

residual_fn = (
    total_fn - rescued_fn
)

total_actual_positive = (
    total_fn + total_tp
)

primary_fnr = (
    total_fn
    / total_actual_positive
)

simulated_residual_fnr = (
    residual_fn
    / total_actual_positive
)

absolute_reduction = (
    primary_fnr
    - simulated_residual_fnr
)

relative_reduction = (
    absolute_reduction
    / primary_fnr
)


# ============================================================
# OVERALL RESULTS
# ============================================================

print("\n" + "=" * 80)
print("OVERALL END-TO-END IMPACT")
print("=" * 80)

print("True positives:", total_tp)
print("False negatives:", total_fn)
print("Total actual positives:", total_actual_positive)

print("\nFalse negatives selected for review:", rescued_fn)
print("Residual false negatives:", residual_fn)

print(
    f"\nPrimary model FNR: "
    f"{primary_fnr:.4f} "
    f"({primary_fnr * 100:.2f}%)"
)

print(
    f"Simulated residual miss rate: "
    f"{simulated_residual_fnr:.4f} "
    f"({simulated_residual_fnr * 100:.2f}%)"
)

print(
    f"Absolute reduction: "
    f"{absolute_reduction * 100:.2f} percentage points"
)

print(
    f"Relative reduction in missed positives: "
    f"{relative_reduction * 100:.2f}%"
)


# ============================================================
# CREATE OVERALL FIGURE
# ============================================================

overall_labels = [
    "Primary Model",
    "After Rescue Review*"
]

overall_values = [
    primary_fnr * 100,
    simulated_residual_fnr * 100
]

fig4, ax4 = plt.subplots(
    figsize=(7, 5.5)
)

bars = ax4.bar(
    overall_labels,
    overall_values,
    width=0.55
)

for bar, value in zip(
    bars,
    overall_values
):
    ax4.text(
        bar.get_x()
        + bar.get_width() / 2,
        bar.get_height() + 0.8,
        f"{value:.2f}%",
        ha="center",
        va="bottom",
        fontsize=11
    )

ax4.set_ylabel(
    "Miss Rate Among Actual Positives (%)",
    fontsize=11
)

ax4.set_title(
    "Simulated End-to-End Impact of Rescue Review",
    fontsize=13,
    pad=12
)

ax4.set_ylim(
    0,
    max(overall_values) + 8
)

ax4.grid(
    axis="y",
    alpha=0.25
)

ax4.text(
    0.5,
    -0.15,
    "*Assumes every reviewed false negative is correctly identified.",
    transform=ax4.transAxes,
    ha="center",
    fontsize=9
)

fig4.tight_layout()

figure4_png = (
    OUTPUT_DIR
    / "figure_4_end_to_end_rescue_impact.png"
)

figure4_pdf = (
    OUTPUT_DIR
    / "figure_4_end_to_end_rescue_impact.pdf"
)

fig4.savefig(
    figure4_png,
    dpi=300,
    bbox_inches="tight"
)

fig4.savefig(
    figure4_pdf,
    bbox_inches="tight"
)

plt.close(fig4)


# ============================================================
# SAVE NUMERIC SUMMARY
# ============================================================

impact_summary = pd.DataFrame(
    {
        "metric": [
            "true_positives",
            "false_negatives",
            "rescued_false_negatives",
            "residual_false_negatives",
            "primary_fnr",
            "simulated_residual_miss_rate",
            "absolute_fnr_reduction",
            "relative_fn_reduction"
        ],
        "value": [
            total_tp,
            total_fn,
            rescued_fn,
            residual_fn,
            primary_fnr,
            simulated_residual_fnr,
            absolute_reduction,
            relative_reduction
        ]
    }
)

impact_summary_file = (
    Path("results/eligible")
    / "final_test_end_to_end_impact.csv"
)

impact_summary.to_csv(
    impact_summary_file,
    index=False
)


# ============================================================
# RACE-SPECIFIC IMPACT
# ============================================================

# We can determine FN rescue counts from the router file,
# but subgroup TP counts are not available in this low-risk-only
# file. Therefore we do NOT fabricate subgroup FNRs here.
#
# Instead, calculate the rescue fraction among false negatives,
# which is directly supported by the locked test data.

race_fn = router_test[
    router_test["case_type"] == "FN"
].copy()

race_fn["race"] = (
    race_fn["race"]
    .fillna("Missing")
)

race_rows = []

for race_group, group_df in race_fn.groupby("race"):

    group_fn = len(group_df)

    group_rescued = int(
        group_df["selected_for_review"].sum()
    )

    group_residual = (
        group_fn - group_rescued
    )

    rescue_rate = (
        group_rescued / group_fn
        if group_fn > 0
        else float("nan")
    )

    race_rows.append(
        {
            "race": race_group,
            "false_negatives": group_fn,
            "rescued_false_negatives": group_rescued,
            "residual_false_negatives": group_residual,
            "fn_rescue_rate": rescue_rate
        }
    )

race_impact = pd.DataFrame(
    race_rows
)

race_impact_file = (
    Path("results/eligible")
    / "final_test_race_rescue_impact.csv"
)

race_impact.to_csv(
    race_impact_file,
    index=False
)

print("\n" + "=" * 80)
print("RACE-SPECIFIC FN RESCUE")
print("=" * 80)

print(
    race_impact.to_string(
        index=False
    )
)


# ============================================================
# AFRICAN AMERICAN VS CAUCASIAN RESCUE GAP
# ============================================================

stable_race = race_impact[
    race_impact["race"].isin(
        [
            "AfricanAmerican",
            "Caucasian"
        ]
    )
].copy()

if len(stable_race) == 2:

    aa_rate = float(
        stable_race.loc[
            stable_race["race"]
            == "AfricanAmerican",
            "fn_rescue_rate"
        ].iloc[0]
    )

    cauc_rate = float(
        stable_race.loc[
            stable_race["race"]
            == "Caucasian",
            "fn_rescue_rate"
        ].iloc[0]
    )

    gap = (
        aa_rate - cauc_rate
    )

    print(
        "\nAfrican American FN rescue rate:",
        f"{aa_rate * 100:.2f}%"
    )

    print(
        "Caucasian FN rescue rate:",
        f"{cauc_rate * 100:.2f}%"
    )

    print(
        "African American - Caucasian gap:",
        f"{gap * 100:.2f} percentage points"
    )


# ============================================================
# FINAL OUTPUT
# ============================================================

print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print(figure4_png)
print(figure4_pdf)
print(impact_summary_file)
print(race_impact_file)

print("\n" + "=" * 80)
print("PHASE 8.3.4 COMPLETE")
print("=" * 80)

# ============================================================
# PHASE 8.3.6
# END-TO-END FAIRNESS IMPACT FIGURE
# ============================================================

print("\n" + "=" * 80)
print("PHASE 8.3.6 — END-TO-END FAIRNESS IMPACT FIGURE")
print("=" * 80)

E2E_FAIRNESS_FILE = Path(
    "results/eligible/final_test_end_to_end_fairness.csv"
)

e2e = pd.read_csv(E2E_FAIRNESS_FILE)

print("\nInput shape:", e2e.shape)


# ============================================================
# MAIN RACE COMPARISON
# ============================================================

race_plot = e2e[
    (e2e["feature"] == "race")
    &
    (
        e2e["group"].isin(
            [
                "AfricanAmerican",
                "Caucasian"
            ]
        )
    )
].copy()

race_order = [
    "AfricanAmerican",
    "Caucasian"
]

race_plot = (
    race_plot
    .set_index("group")
    .loc[race_order]
    .reset_index()
)

race_plot["primary_percent"] = (
    race_plot["primary_fnr"] * 100
)

race_plot["residual_percent"] = (
    race_plot["simulated_residual_fnr"] * 100
)


# ============================================================
# PLOT
# ============================================================

fig5, ax5 = plt.subplots(
    figsize=(8, 5.5)
)

x = np.arange(
    len(race_plot)
)

width = 0.34

bars_primary = ax5.bar(
    x - width / 2,
    race_plot["primary_percent"],
    width,
    label="Primary model"
)

bars_residual = ax5.bar(
    x + width / 2,
    race_plot["residual_percent"],
    width,
    label="After simulated rescue review"
)


# ============================================================
# VALUE LABELS
# ============================================================

for bars in [
    bars_primary,
    bars_residual
]:

    for bar in bars:

        height = bar.get_height()

        ax5.text(
            bar.get_x()
            + bar.get_width() / 2,
            height + 0.6,
            f"{height:.2f}%",
            ha="center",
            va="bottom",
            fontsize=10
        )


# ============================================================
# LABELS
# ============================================================

ax5.set_xticks(x)

ax5.set_xticklabels(
    [
        "African American",
        "Caucasian"
    ]
)

ax5.set_ylabel(
    "Miss Rate Among Actual Positives (%)",
    fontsize=11
)

ax5.set_title(
    "Simulated End-to-End Miss Rate by Race",
    fontsize=13,
    pad=12
)

ax5.set_ylim(
    0,
    40
)

ax5.grid(
    axis="y",
    alpha=0.25
)

ax5.legend(
    frameon=False
)


# ============================================================
# GAP ANNOTATION
# ============================================================

aa_primary = float(
    race_plot.loc[
        race_plot["group"] == "AfricanAmerican",
        "primary_percent"
    ].iloc[0]
)

cauc_primary = float(
    race_plot.loc[
        race_plot["group"] == "Caucasian",
        "primary_percent"
    ].iloc[0]
)

aa_after = float(
    race_plot.loc[
        race_plot["group"] == "AfricanAmerican",
        "residual_percent"
    ].iloc[0]
)

cauc_after = float(
    race_plot.loc[
        race_plot["group"] == "Caucasian",
        "residual_percent"
    ].iloc[0]
)

primary_gap = aa_primary - cauc_primary
residual_gap = aa_after - cauc_after

annotation = (
    f"AA–Caucasian gap:\n"
    f"{primary_gap:.2f} pp → "
    f"{residual_gap:.2f} pp"
)

ax5.text(
    0.98,
    0.95,
    annotation,
    transform=ax5.transAxes,
    ha="right",
    va="top",
    fontsize=10
)


# ============================================================
# SIMULATION DISCLAIMER
# ============================================================

ax5.text(
    0.5,
    -0.14,
    "*After-review values assume every selected false negative "
    "is correctly identified during review.",
    transform=ax5.transAxes,
    ha="center",
    fontsize=9
)

fig5.tight_layout()


# ============================================================
# SAVE
# ============================================================

figure5_png = (
    OUTPUT_DIR
    / "figure_5_end_to_end_race_fairness.png"
)

figure5_pdf = (
    OUTPUT_DIR
    / "figure_5_end_to_end_race_fairness.pdf"
)

fig5.savefig(
    figure5_png,
    dpi=300,
    bbox_inches="tight"
)

fig5.savefig(
    figure5_pdf,
    bbox_inches="tight"
)

plt.close(fig5)


print("\nAfrican American:")
print(
    f"  {aa_primary:.2f}% -> "
    f"{aa_after:.2f}%"
)

print("\nCaucasian:")
print(
    f"  {cauc_primary:.2f}% -> "
    f"{cauc_after:.2f}%"
)

print(
    f"\nPrimary gap: "
    f"{primary_gap:.2f} pp"
)

print(
    f"Residual gap: "
    f"{residual_gap:.2f} pp"
)

print(
    f"Gap change: "
    f"{residual_gap - primary_gap:+.2f} pp"
)

print("\nFILES SAVED:")
print(figure5_png)
print(figure5_pdf)

print("\n" + "=" * 80)
print("PHASE 8.3.6 COMPLETE")
print("=" * 80)