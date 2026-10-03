from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# =============================================================================
# PHASE 9.3.4 — CANONICAL END-TO-END FIGURES
# =============================================================================

INPUT_FILE = Path(
    "results/eligible/publication/table_5_final_end_to_end_fairness.csv"
)

OUTPUT_DIR = Path(
    "results/eligible/publication/figures"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


print("=" * 80)
print("PHASE 9.3.4 — CANONICAL END-TO-END FIGURES")
print("=" * 80)


# =============================================================================
# 1. LOAD
# =============================================================================

df = pd.read_csv(INPUT_FILE)

print("\nInput shape:", df.shape)

print("\nColumns:")
for col in df.columns:
    print(" -", col)


# =============================================================================
# 2. BASIC INTEGRITY
# =============================================================================

print("\n" + "=" * 80)
print("A — BASIC INTEGRITY")
print("=" * 80)

checks = {
    "17 rows": len(df) == 17,
    "Gender present": (df["Feature"] == "gender").any(),
    "Race present": (df["Feature"] == "race").any(),
    "Age present": (df["Feature"] == "age").any(),
}

all_passed = True

for name, passed in checks.items():

    all_passed &= passed

    print(
        f"{name}: "
        f"{'PASSED' if passed else 'FAILED'}"
    )


# =============================================================================
# 3. OVERALL END-TO-END VALUES
# =============================================================================

actual_positives = int(
    df.loc[
        df["Feature"] == "gender",
        "Actual Positives"
    ].sum()
)

true_positives = int(
    df.loc[
        df["Feature"] == "gender",
        "True Positives"
    ].sum()
)

false_negatives = int(
    df.loc[
        df["Feature"] == "gender",
        "False Negatives"
    ].sum()
)

rescued_fn = int(
    df.loc[
        df["Feature"] == "gender",
        "Rescued False Negatives"
    ].sum()
)

residual_fn = (
    false_negatives - rescued_fn
)

primary_fnr = (
    false_negatives
    / actual_positives
    * 100
)

residual_fnr = (
    residual_fn
    / actual_positives
    * 100
)

absolute_reduction = (
    primary_fnr - residual_fnr
)

relative_reduction = (
    rescued_fn
    / false_negatives
    * 100
)


print("\n" + "=" * 80)
print("B — OVERALL END-TO-END VALUES")
print("=" * 80)

print("Actual positives:", actual_positives)
print("True positives:", true_positives)
print("False negatives:", false_negatives)
print("Rescued false negatives:", rescued_fn)
print("Residual false negatives:", residual_fn)

print(f"Primary FNR: {primary_fnr:.2f}%")
print(f"Residual FNR: {residual_fnr:.2f}%")
print(
    f"Absolute reduction: "
    f"{absolute_reduction:.2f} pp"
)
print(
    f"Relative reduction in missed positives: "
    f"{relative_reduction:.2f}%"
)


# =============================================================================
# 4. ASSERT OVERALL CANONICAL VALUES
# =============================================================================

overall_checks = {
    "Actual positives = 1736":
        actual_positives == 1736,

    "False negatives = 557":
        false_negatives == 557,

    "Rescued FN = 110":
        rescued_fn == 110,

    "Residual FN = 447":
        residual_fn == 447,

    "Primary FNR = 32.09%":
        np.isclose(primary_fnr, 32.09, atol=0.01),

    "Residual FNR = 25.75%":
        np.isclose(residual_fnr, 25.75, atol=0.01),
}

for name, passed in overall_checks.items():

    all_passed &= passed

    print(
        f"{name}: "
        f"{'PASSED' if passed else 'FAILED'}"
    )


# =============================================================================
# 5. FIGURE 4 — OVERALL END-TO-END IMPACT
# =============================================================================

print("\n" + "=" * 80)
print("C — FIGURE 4")
print("=" * 80)

labels = [
    "Primary Model",
    "After Perfect Review",
]

values = [
    primary_fnr,
    residual_fnr,
]

fig, ax = plt.subplots(
    figsize=(7.5, 5.5)
)

x = np.arange(len(labels))

bars = ax.bar(
    x,
    values,
    width=0.55,
)

ax.set_xticks(x)
ax.set_xticklabels(labels)

ax.set_ylabel(
    "False-Negative Rate (%)"
)

ax.set_title(
    "Simulated End-to-End Impact of Targeted Review"
)

ax.grid(
    axis="y",
    alpha=0.25,
)

for bar, value in zip(bars, values):

    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.5,
        f"{value:.2f}%",
        ha="center",
        fontsize=10,
    )

ax.text(
    0.5,
    max(values) * 0.55,
    f"−{absolute_reduction:.2f} pp",
    ha="center",
    fontsize=11,
)

fig.tight_layout()


FIG4_PNG = (
    OUTPUT_DIR
    / "figure_4_canonical_end_to_end_impact.png"
)

FIG4_PDF = (
    OUTPUT_DIR
    / "figure_4_canonical_end_to_end_impact.pdf"
)

fig.savefig(
    FIG4_PNG,
    dpi=300,
    bbox_inches="tight",
)

fig.savefig(
    FIG4_PDF,
    bbox_inches="tight",
)

plt.close(fig)

print("Saved:")
print(FIG4_PNG)
print(FIG4_PDF)


# =============================================================================
# 6. RACE DATA
# =============================================================================

race = df[
    df["Feature"] == "race"
].copy()

aa = race[
    race["Group"] == "AfricanAmerican"
].iloc[0]

ca = race[
    race["Group"] == "Caucasian"
].iloc[0]


aa_primary = float(
    aa["Primary FNR (%)"]
)

aa_residual = float(
    aa["Residual FNR (%)"]
)

ca_primary = float(
    ca["Primary FNR (%)"]
)

ca_residual = float(
    ca["Residual FNR (%)"]
)


primary_gap = (
    aa_primary - ca_primary
)

residual_gap = (
    aa_residual - ca_residual
)

gap_change = (
    residual_gap - primary_gap
)


print("\n" + "=" * 80)
print("D — RACE END-TO-END VALUES")
print("=" * 80)

print(
    f"African American: "
    f"{aa_primary:.2f}% -> "
    f"{aa_residual:.2f}%"
)

print(
    f"Caucasian: "
    f"{ca_primary:.2f}% -> "
    f"{ca_residual:.2f}%"
)

print(
    f"Primary gap: "
    f"{primary_gap:.2f} pp"
)

print(
    f"Residual gap: "
    f"{residual_gap:.2f} pp"
)

print(
    f"Gap change: "
    f"{gap_change:+.2f} pp"
)


# =============================================================================
# 7. RACE ASSERTIONS
# =============================================================================

race_checks = {
    "AA primary = 33.75%":
        np.isclose(
            aa_primary,
            33.75,
            atol=0.01
        ),

    "AA residual = 29.02%":
        np.isclose(
            aa_residual,
            29.02,
            atol=0.01
        ),

    "Caucasian primary = 31.43%":
        np.isclose(
            ca_primary,
            31.43,
            atol=0.01
        ),

    "Caucasian residual = 24.44%":
        np.isclose(
            ca_residual,
            24.44,
            atol=0.01
        ),
}

for name, passed in race_checks.items():

    all_passed &= passed

    print(
        f"{name}: "
        f"{'PASSED' if passed else 'FAILED'}"
    )


# =============================================================================
# 8. FIGURE 5 — RACE FAIRNESS IMPACT
# =============================================================================

print("\n" + "=" * 80)
print("E — FIGURE 5")
print("=" * 80)

groups = [
    "African American",
    "Caucasian",
]

primary_values = [
    aa_primary,
    ca_primary,
]

residual_values = [
    aa_residual,
    ca_residual,
]

x = np.arange(len(groups))

width = 0.34

fig, ax = plt.subplots(
    figsize=(8, 5.5)
)

bars1 = ax.bar(
    x - width / 2,
    primary_values,
    width,
    label="Primary Model",
)

bars2 = ax.bar(
    x + width / 2,
    residual_values,
    width,
    label="After Perfect Review",
)

ax.set_xticks(x)

ax.set_xticklabels(
    groups
)

ax.set_ylabel(
    "False-Negative Rate (%)"
)

ax.set_title(
    "End-to-End False-Negative Rate by Race"
)

ax.legend(
    frameon=False
)

ax.grid(
    axis="y",
    alpha=0.25
)


for bars in [bars1, bars2]:

    for bar in bars:

        value = bar.get_height()

        ax.text(
            bar.get_x()
            + bar.get_width() / 2,
            value + 0.5,
            f"{value:.2f}%",
            ha="center",
            fontsize=9,
        )


fig.tight_layout()


FIG5_PNG = (
    OUTPUT_DIR
    / "figure_5_canonical_race_fairness.png"
)

FIG5_PDF = (
    OUTPUT_DIR
    / "figure_5_canonical_race_fairness.pdf"
)

fig.savefig(
    FIG5_PNG,
    dpi=300,
    bbox_inches="tight",
)

fig.savefig(
    FIG5_PDF,
    bbox_inches="tight",
)

plt.close(fig)

print("Saved:")
print(FIG5_PNG)
print(FIG5_PDF)


# =============================================================================
# 9. SAVE CANONICAL FIGURE DATA
# =============================================================================

summary = pd.DataFrame(
    {
        "Result": [
            "Primary overall FNR",
            "Residual overall FNR",
            "Absolute FNR reduction",
            "Relative missed-positive reduction",
            "African American primary FNR",
            "African American residual FNR",
            "Caucasian primary FNR",
            "Caucasian residual FNR",
            "Primary race FNR gap",
            "Residual race FNR gap",
            "Race FNR gap change",
        ],
        "Value": [
            primary_fnr,
            residual_fnr,
            absolute_reduction,
            relative_reduction,
            aa_primary,
            aa_residual,
            ca_primary,
            ca_residual,
            primary_gap,
            residual_gap,
            gap_change,
        ],
    }
)

DATA_FILE = (
    OUTPUT_DIR
    / "figure_4_5_canonical_data.csv"
)

summary.to_csv(
    DATA_FILE,
    index=False,
)


# =============================================================================
# 10. FINAL REPORT
# =============================================================================

print("\n" + "=" * 80)
print("F — FINAL CANONICAL FIGURE VALUES")
print("=" * 80)

print(summary.to_string(index=False))


print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print(FIG4_PNG)
print(FIG4_PDF)
print(FIG5_PNG)
print(FIG5_PDF)
print(DATA_FILE)


print("\n" + "=" * 80)

if all_passed:
    print(
        "PHASE 9.3.4 COMPLETE — PASSED"
    )
else:
    print(
        "PHASE 9.3.4 COMPLETE — FAILED"
    )

print("=" * 80)