from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# =============================================================================
# PHASE 9.3.1 — CANONICAL FIGURE 1
# FN CAPTURE VS REVIEW BUDGET
# =============================================================================

SENSITIVITY_FILE = Path(
    "results/eligible/final_test_router_sensitivity.csv"
)

CANONICAL_FILE = Path(
    "results/eligible/canonical_locked_15pct_results.csv"
)

OUTPUT_DIR = Path(
    "results/eligible/publication/figures"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


print("=" * 80)
print("PHASE 9.3.1 — CANONICAL FIGURE 1 SYNCHRONIZATION")
print("=" * 80)


# =============================================================================
# 1. LOAD DATA
# =============================================================================

sensitivity = pd.read_csv(SENSITIVITY_FILE)
canonical = pd.read_csv(CANONICAL_FILE)

print("\nSensitivity input shape:", sensitivity.shape)
print("Canonical input shape:", canonical.shape)

print("\nSensitivity methods:")
print(sensitivity["method"].unique())

print("\nBudgets:")
print(sorted(sensitivity["budget"].unique()))

print("\nCanonical locked results:")
print(
    canonical[
        [
            "method",
            "patients_reviewed",
            "fn_capture_percent",
            "tie_rule",
        ]
    ].to_string(index=False)
)


# =============================================================================
# 2. STANDARDIZE VALUES TO PERCENT
# =============================================================================

plot_df = sensitivity.copy()

# Convert capture rate to percent
plot_df["fn_capture_percent"] = (
    plot_df["fn_capture_rate"] * 100
)

plot_df["budget_percent"] = (
    plot_df["budget"] * 100
)


# =============================================================================
# 3. REPLACE LOCKED 15% POINT WITH CANONICAL VALUES
#
# This is critical because probability ranking has a large cutoff tie.
# The canonical probability value uses expected random selection within
# the cutoff tie.
# =============================================================================

LOCKED_BUDGET = 0.15

for _, row in canonical.iterrows():

    method = row["method"]
    canonical_capture = row["fn_capture_percent"]

    mask = (
        (plot_df["method"] == method)
        & np.isclose(plot_df["budget"], LOCKED_BUDGET)
    )

    if mask.sum() != 1:
        raise ValueError(
            f"Expected exactly one 15% row for {method}, "
            f"found {mask.sum()}"
        )

    old_value = plot_df.loc[
        mask, "fn_capture_percent"
    ].iloc[0]

    plot_df.loc[
        mask, "fn_capture_percent"
    ] = canonical_capture

    print(
        f"\n{method}: "
        f"15% point {old_value:.6f}% "
        f"-> {canonical_capture:.6f}%"
    )


# =============================================================================
# 4. CANONICAL ASSERTIONS
# =============================================================================

expected = {
    "Probability": 20.813356,
    "Rescue Router": 19.748654,
    "Disagreement": 18.312388,
    "Random": 14.991092,
}

print("\n" + "=" * 80)
print("A — LOCKED 15% CANONICAL CHECK")
print("=" * 80)

all_passed = True

for method, expected_value in expected.items():

    row = plot_df[
        (plot_df["method"] == method)
        & np.isclose(
            plot_df["budget"],
            LOCKED_BUDGET
        )
    ]

    observed = row[
        "fn_capture_percent"
    ].iloc[0]

    passed = np.isclose(
        observed,
        expected_value,
        atol=1e-5
    )

    all_passed = all_passed and passed

    print(
        f"{method:17s} "
        f"observed={observed:.6f}% "
        f"expected={expected_value:.6f}% "
        f"{'PASSED' if passed else 'FAILED'}"
    )


# =============================================================================
# 5. CREATE FIGURE
# =============================================================================

print("\n" + "=" * 80)
print("B — GENERATING CANONICAL FIGURE 1")
print("=" * 80)


method_order = [
    "Probability",
    "Rescue Router",
    "Disagreement",
    "Random",
]


fig, ax = plt.subplots(
    figsize=(8.5, 6.0)
)


for method in method_order:

    temp = (
        plot_df[
            plot_df["method"] == method
        ]
        .sort_values("budget")
    )

    ax.plot(
        temp["budget_percent"],
        temp["fn_capture_percent"],
        marker="o",
        linewidth=2,
        markersize=5,
        label=method,
    )


# Locked operating point
ax.axvline(
    15,
    linestyle="--",
    linewidth=1.5,
    alpha=0.7,
)

ax.text(
    15.5,
    ax.get_ylim()[1] * 0.93,
    "Locked 15% budget",
    fontsize=9,
)


# =============================================================================
# 6. ANNOTATE CANONICAL 15% VALUES
# =============================================================================

annotation_offsets = {
    "Probability": (8, 10),
    "Rescue Router": (8, -15),
    "Disagreement": (8, -18),
    "Random": (8, -18),
}


for method in method_order:

    row = plot_df[
        (plot_df["method"] == method)
        & np.isclose(
            plot_df["budget"],
            LOCKED_BUDGET
        )
    ]

    x = 15
    y = row[
        "fn_capture_percent"
    ].iloc[0]

    ax.annotate(
        f"{y:.2f}%",
        xy=(x, y),
        xytext=annotation_offsets[method],
        textcoords="offset points",
        fontsize=9,
    )


# =============================================================================
# 7. FORMATTING
# =============================================================================

ax.set_xlabel(
    "Review Budget (% of Low-Risk Population)",
    fontsize=11,
)

ax.set_ylabel(
    "False-Negative Capture Rate (%)",
    fontsize=11,
)

ax.set_title(
    "False-Negative Capture vs Review Budget",
    fontsize=13,
)

ax.grid(
    alpha=0.25
)

ax.legend(
    frameon=False
)

fig.tight_layout()


# =============================================================================
# 8. SAVE
# =============================================================================

PNG_FILE = (
    OUTPUT_DIR
    / "figure_1_canonical_fn_capture_vs_review_budget.png"
)

PDF_FILE = (
    OUTPUT_DIR
    / "figure_1_canonical_fn_capture_vs_review_budget.pdf"
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


# =============================================================================
# 9. SAVE FIGURE DATA
# =============================================================================

FIGURE_DATA_FILE = (
    OUTPUT_DIR
    / "figure_1_canonical_data.csv"
)

plot_df.to_csv(
    FIGURE_DATA_FILE,
    index=False
)


# =============================================================================
# 10. FINAL REPORT
# =============================================================================

print("\nCanonical locked points used:")

locked = plot_df[
    np.isclose(
        plot_df["budget"],
        LOCKED_BUDGET
    )
][
    [
        "method",
        "budget_percent",
        "fn_capture_percent",
    ]
].copy()

locked = locked.sort_values(
    "fn_capture_percent",
    ascending=False,
)

print(
    locked.to_string(
        index=False
    )
)


print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print(PNG_FILE)
print(PDF_FILE)
print(FIGURE_DATA_FILE)


print("\n" + "=" * 80)

if all_passed:
    print(
        "PHASE 9.3.1 COMPLETE — PASSED"
    )
else:
    print(
        "PHASE 9.3.1 COMPLETE — FAILED"
    )

print("=" * 80)