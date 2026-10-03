from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# =============================================================================
# PHASE 9.3.2 — CANONICAL FIGURE 2
# LOCKED 15% BOOTSTRAP COMPARISON
# =============================================================================

INPUT_FILE = Path(
    "results/eligible/canonical_bootstrap_confidence_intervals.csv"
)

OUTPUT_DIR = Path(
    "results/eligible/publication/figures"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


print("=" * 80)
print("PHASE 9.3.2 — CANONICAL BOOTSTRAP FIGURE")
print("=" * 80)


# =============================================================================
# 1. LOAD
# =============================================================================

df = pd.read_csv(INPUT_FILE)

print("\nInput shape:", df.shape)
print("\nInput:")
print(df.to_string(index=False))


# =============================================================================
# 2. EXPECTED METHODS
# =============================================================================

method_order = [
    "Probability",
    "Rescue Router",
    "Disagreement",
    "Random",
]

expected_methods = set(method_order)

assert set(df["method"]) == expected_methods

print("\nExpected strategies present: PASSED")


# =============================================================================
# 3. CONVERT TO PERCENT IF NECESSARY
# =============================================================================

plot_df = df.copy()

for col in [
    "point_estimate",
    "bootstrap_mean",
    "ci_lower",
    "ci_upper",
]:
    if plot_df[col].max() <= 1:
        plot_df[col] = plot_df[col] * 100


# =============================================================================
# 4. CANONICAL VALUE ASSERTIONS
# =============================================================================

expected = {
    "Probability": 20.813356,
    "Rescue Router": 19.748654,
    "Disagreement": 18.312388,
    "Random": 14.991092,
}

print("\n" + "=" * 80)
print("A — CANONICAL POINT ESTIMATE CHECK")
print("=" * 80)

all_passed = True

for method, expected_value in expected.items():

    observed = plot_df.loc[
        plot_df["method"] == method,
        "point_estimate",
    ].iloc[0]

    passed = np.isclose(
        observed,
        expected_value,
        atol=1e-5,
    )

    all_passed = all_passed and passed

    print(
        f"{method:17s} "
        f"observed={observed:.6f}% "
        f"expected={expected_value:.6f}% "
        f"{'PASSED' if passed else 'FAILED'}"
    )


# =============================================================================
# 5. ORDER DATA
# =============================================================================

plot_df["method"] = pd.Categorical(
    plot_df["method"],
    categories=method_order,
    ordered=True,
)

plot_df = (
    plot_df
    .sort_values("method")
    .reset_index(drop=True)
)


# =============================================================================
# 6. ERROR BARS
# =============================================================================

lower_error = (
    plot_df["point_estimate"]
    - plot_df["ci_lower"]
)

upper_error = (
    plot_df["ci_upper"]
    - plot_df["point_estimate"]
)

yerr = np.vstack(
    [lower_error, upper_error]
)


# =============================================================================
# 7. CREATE FIGURE
# =============================================================================

print("\n" + "=" * 80)
print("B — GENERATING FIGURE")
print("=" * 80)

fig, ax = plt.subplots(
    figsize=(8.5, 6)
)

x = np.arange(len(plot_df))

ax.errorbar(
    x,
    plot_df["point_estimate"],
    yerr=yerr,
    fmt="o",
    markersize=8,
    capsize=6,
    linewidth=2,
)


# Random expectation reference
random_value = expected["Random"]

ax.axhline(
    random_value,
    linestyle="--",
    linewidth=1.5,
    alpha=0.6,
)


# =============================================================================
# 8. VALUE LABELS
# =============================================================================

for i, row in plot_df.iterrows():

    ax.annotate(
        f'{row["point_estimate"]:.2f}%',
        (
            i,
            row["point_estimate"],
        ),
        xytext=(8, 8),
        textcoords="offset points",
        fontsize=9,
    )


# =============================================================================
# 9. FORMATTING
# =============================================================================

ax.set_xticks(x)

ax.set_xticklabels(
    plot_df["method"]
)

ax.set_ylabel(
    "False-Negative Capture Rate (%)",
    fontsize=11,
)

ax.set_xlabel(
    "Review Strategy",
    fontsize=11,
)

ax.set_title(
    "False-Negative Capture at the Locked 15% Review Budget",
    fontsize=13,
)

ax.grid(
    axis="y",
    alpha=0.25,
)

fig.tight_layout()


# =============================================================================
# 10. SAVE
# =============================================================================

PNG_FILE = (
    OUTPUT_DIR
    / "figure_2_canonical_locked_15pct_bootstrap.png"
)

PDF_FILE = (
    OUTPUT_DIR
    / "figure_2_canonical_locked_15pct_bootstrap.pdf"
)

DATA_FILE = (
    OUTPUT_DIR
    / "figure_2_canonical_data.csv"
)

fig.savefig(
    PNG_FILE,
    dpi=300,
    bbox_inches="tight",
)

fig.savefig(
    PDF_FILE,
    bbox_inches="tight",
)

plt.close(fig)

plot_df.to_csv(
    DATA_FILE,
    index=False,
)


# =============================================================================
# 11. PUBLICATION VALUES
# =============================================================================

print("\n" + "=" * 80)
print("C — FIGURE 2 VALUES")
print("=" * 80)

print(
    plot_df[
        [
            "method",
            "point_estimate",
            "ci_lower",
            "ci_upper",
        ]
    ].to_string(index=False)
)


print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print(PNG_FILE)
print(PDF_FILE)
print(DATA_FILE)


print("\n" + "=" * 80)

if all_passed:
    print("PHASE 9.3.2 COMPLETE — PASSED")
else:
    print("PHASE 9.3.2 COMPLETE — FAILED")

print("=" * 80)