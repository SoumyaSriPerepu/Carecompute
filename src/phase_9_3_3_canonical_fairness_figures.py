from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# =============================================================================
# PHASE 9.3.3 — CANONICAL FAIRNESS FIGURES
# =============================================================================

INPUT_FILE = Path(
    "results/eligible/publication/table_4_final_fn_rescue_fairness.csv"
)

OUTPUT_DIR = Path(
    "results/eligible/publication/figures"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


print("=" * 80)
print("PHASE 9.3.3 — CANONICAL FAIRNESS FIGURES")
print("=" * 80)


# =============================================================================
# 1. LOAD
# =============================================================================

df = pd.read_csv(INPUT_FILE)

print("\nInput shape:", df.shape)

print("\nColumns:")
for col in df.columns:
    print(" -", col)

print("\nFeatures:")
print(df["Feature"].value_counts())


# =============================================================================
# 2. BASIC INTEGRITY
# =============================================================================

print("\n" + "=" * 80)
print("A — BASIC INTEGRITY")
print("=" * 80)

checks = {
    "17 fairness rows": len(df) == 17,
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
# 3. HELPER FUNCTION
# =============================================================================

def make_fairness_figure(
    subset,
    title,
    filename,
    figsize=(8.5, 6),
):

    subset = subset.copy()

    x = np.arange(len(subset))

    values = subset[
        "FN Rescue Rate (%)"
    ].to_numpy()

    lower = (
        values
        - subset["95% CI Lower (%)"].to_numpy()
    )

    upper = (
        subset["95% CI Upper (%)"].to_numpy()
        - values
    )

    yerr = np.vstack([lower, upper])

    fig, ax = plt.subplots(
        figsize=figsize
    )

    ax.errorbar(
        x,
        values,
        yerr=yerr,
        fmt="o",
        markersize=7,
        capsize=5,
        linewidth=1.8,
    )

    ax.set_xticks(x)

    ax.set_xticklabels(
        subset["Group"],
        rotation=35,
        ha="right",
    )

    ax.set_ylabel(
        "False-Negative Rescue Rate (%)"
    )

    ax.set_title(title)

    ax.grid(
        axis="y",
        alpha=0.25,
    )

    # Add point estimate labels
    for i, value in enumerate(values):

        ax.annotate(
            f"{value:.2f}%",
            (i, value),
            xytext=(5, 7),
            textcoords="offset points",
            fontsize=8,
        )

    fig.tight_layout()

    png_file = (
        OUTPUT_DIR
        / f"{filename}.png"
    )

    pdf_file = (
        OUTPUT_DIR
        / f"{filename}.pdf"
    )

    fig.savefig(
        png_file,
        dpi=300,
        bbox_inches="tight",
    )

    fig.savefig(
        pdf_file,
        bbox_inches="tight",
    )

    plt.close(fig)

    print("\nSaved:")
    print(png_file)
    print(pdf_file)


# =============================================================================
# 4. GENDER
# =============================================================================

print("\n" + "=" * 80)
print("B — GENDER")
print("=" * 80)

gender = df[
    df["Feature"] == "gender"
].copy()

gender_order = [
    "Female",
    "Male",
]

gender["Group"] = pd.Categorical(
    gender["Group"],
    categories=gender_order,
    ordered=True,
)

gender = gender.sort_values("Group")

print(
    gender[
        [
            "Group",
            "False Negatives",
            "Rescued False Negatives",
            "FN Rescue Rate (%)",
            "95% CI Lower (%)",
            "95% CI Upper (%)",
        ]
    ].to_string(index=False)
)


female = gender.loc[
    gender["Group"] == "Female",
    "FN Rescue Rate (%)",
].iloc[0]

male = gender.loc[
    gender["Group"] == "Male",
    "FN Rescue Rate (%)",
].iloc[0]

female_check = np.isclose(
    female,
    20.49,
    atol=0.01,
)

male_check = np.isclose(
    male,
    18.96,
    atol=0.01,
)

all_passed &= female_check
all_passed &= male_check

print(
    "\nFemale 20.49%:",
    "PASSED" if female_check else "FAILED",
)

print(
    "Male 18.96%:",
    "PASSED" if male_check else "FAILED",
)


make_fairness_figure(
    gender,
    "False-Negative Rescue Rate by Gender",
    "figure_3a_canonical_gender_fn_rescue",
)


# =============================================================================
# 5. RACE
# =============================================================================

print("\n" + "=" * 80)
print("C — RACE")
print("=" * 80)

race = df[
    df["Feature"] == "race"
].copy()

race_order = [
    "AfricanAmerican",
    "Asian",
    "Caucasian",
    "Hispanic",
    "Other",
    "Missing",
]

race["Group"] = pd.Categorical(
    race["Group"],
    categories=race_order,
    ordered=True,
)

race = race.sort_values("Group")

print(
    race[
        [
            "Group",
            "False Negatives",
            "Rescued False Negatives",
            "FN Rescue Rate (%)",
            "95% CI Lower (%)",
            "95% CI Upper (%)",
        ]
    ].to_string(index=False)
)


aa = race.loc[
    race["Group"] == "AfricanAmerican",
    "FN Rescue Rate (%)",
].iloc[0]

caucasian = race.loc[
    race["Group"] == "Caucasian",
    "FN Rescue Rate (%)",
].iloc[0]

aa_check = np.isclose(
    aa,
    14.02,
    atol=0.01,
)

caucasian_check = np.isclose(
    caucasian,
    22.25,
    atol=0.01,
)

all_passed &= aa_check
all_passed &= caucasian_check

print(
    "\nAfrican American 14.02%:",
    "PASSED" if aa_check else "FAILED",
)

print(
    "Caucasian 22.25%:",
    "PASSED" if caucasian_check else "FAILED",
)


make_fairness_figure(
    race,
    "False-Negative Rescue Rate by Race",
    "figure_3b_canonical_race_fn_rescue",
    figsize=(9, 6),
)


# =============================================================================
# 6. AGE
# =============================================================================

print("\n" + "=" * 80)
print("D — AGE")
print("=" * 80)

age = df[
    df["Feature"] == "age"
].copy()

age_order = [
    "[10-20)",
    "[20-30)",
    "[30-40)",
    "[40-50)",
    "[50-60)",
    "[60-70)",
    "[70-80)",
    "[80-90)",
    "[90-100)",
]

age["Group"] = pd.Categorical(
    age["Group"],
    categories=age_order,
    ordered=True,
)

age = age.sort_values("Group")

print(
    age[
        [
            "Group",
            "False Negatives",
            "Rescued False Negatives",
            "FN Rescue Rate (%)",
            "95% CI Lower (%)",
            "95% CI Upper (%)",
        ]
    ].to_string(index=False)
)


age_70_80 = age.loc[
    age["Group"] == "[70-80)",
    "FN Rescue Rate (%)",
].iloc[0]

age_40_50 = age.loc[
    age["Group"] == "[40-50)",
    "FN Rescue Rate (%)",
].iloc[0]

high_check = np.isclose(
    age_70_80,
    29.93,
    atol=0.01,
)

low_check = np.isclose(
    age_40_50,
    9.52,
    atol=0.01,
)

all_passed &= high_check
all_passed &= low_check

print(
    "\n[70-80) = 29.93%:",
    "PASSED" if high_check else "FAILED",
)

print(
    "[40-50) = 9.52%:",
    "PASSED" if low_check else "FAILED",
)


make_fairness_figure(
    age,
    "False-Negative Rescue Rate by Age Group",
    "figure_3c_canonical_age_fn_rescue",
    figsize=(10, 6),
)


# =============================================================================
# 7. SAVE SOURCE DATA
# =============================================================================

DATA_FILE = (
    OUTPUT_DIR
    / "figure_3_canonical_fairness_data.csv"
)

df.to_csv(
    DATA_FILE,
    index=False,
)


# =============================================================================
# 8. FINAL REPORT
# =============================================================================

print("\n" + "=" * 80)
print("E — CANONICAL FAIRNESS VALUES")
print("=" * 80)

print(f"Female:            {female:.2f}%")
print(f"Male:              {male:.2f}%")
print(
    f"Gender gap:        "
    f"{female - male:.2f} pp"
)

print()

print(
    f"African American:  {aa:.2f}%"
)
print(
    f"Caucasian:         {caucasian:.2f}%"
)
print(
    f"AA - Caucasian:    "
    f"{aa - caucasian:.2f} pp"
)

print()

print(
    f"[70-80):           "
    f"{age_70_80:.2f}%"
)

print(
    f"[40-50):           "
    f"{age_40_50:.2f}%"
)

print(
    f"Stable age gap:    "
    f"{age_70_80 - age_40_50:.2f} pp"
)


print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print(DATA_FILE)


print("\n" + "=" * 80)

if all_passed:
    print(
        "PHASE 9.3.3 COMPLETE — PASSED"
    )
else:
    print(
        "PHASE 9.3.3 COMPLETE — FAILED"
    )

print("=" * 80)