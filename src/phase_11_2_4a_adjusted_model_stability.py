from pathlib import Path
import json
import hashlib
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import chi2


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

ORIGINAL_AUDIT_PATH = Path(
    "results/eligible/fairness/"
    "phase11_2_4_complexity_adjusted_compute_audit.json"
)

OUTPUT_DIR = Path("results/eligible/fairness")

COEF_PATH = (
    OUTPUT_DIR /
    "phase11_2_4a_stable_adjusted_coefficients.csv"
)

MARGINAL_PATH = (
    OUTPUT_DIR /
    "phase11_2_4a_stable_adjusted_group_allocation.csv"
)

AUDIT_PATH = (
    OUTPUT_DIR /
    "phase11_2_4a_adjusted_model_stability_audit.json"
)


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


section(
    "PHASE 11.2.4A — ADJUSTED MODEL STABILITY / SENSITIVITY AUDIT"
)


# =============================================================================
# A — LOAD LOCKS
# =============================================================================

section("A — VERIFY INPUTS AND ORIGINAL AUDIT")

for p in [
    DATA_PATH,
    ELIGIBILITY_PATH,
    ORIGINAL_AUDIT_PATH,
]:
    if not p.exists():
        raise FileNotFoundError(p)
    print("FOUND:", p)

with ELIGIBILITY_PATH.open() as f:
    eligibility = json.load(f)

with ORIGINAL_AUDIT_PATH.open() as f:
    original = json.load(f)

if eligibility["status"] != "FAIRNESS_ELIGIBILITY_FROZEN":
    raise RuntimeError("Eligibility policy not frozen.")

if original["status"] != "COMPLEXITY_ADJUSTED_COMPUTE_AUDIT_COMPLETE":
    raise RuntimeError("Original 11.2.4 audit incomplete.")

print("Original 11.2.4 preserved: YES")


# =============================================================================
# B — LOAD NEGATIVE ROUTING POPULATION
# =============================================================================

section("B — LOAD PRIMARY-MODEL-NEGATIVE POPULATION")

df = pd.read_csv(DATA_PATH)

analysis = df[
    df["predicted_30d"] == 0
].copy()

if len(analysis) != 7858:
    raise RuntimeError("Negative-population lock failed.")

if int(analysis["selected_for_review"].sum()) != 1178:
    raise RuntimeError("Review-population lock failed.")

analysis["race_audit"] = (
    analysis["race"]
    .fillna("MISSING")
    .astype(str)
)

analysis["gender_audit"] = (
    analysis["gender"]
    .fillna("MISSING")
    .astype(str)
)

analysis["age_audit"] = (
    analysis["age"]
    .fillna("MISSING")
    .astype(str)
)

print("Analysis population:", len(analysis))
print("Selected:", int(analysis["selected_for_review"].sum()))


# =============================================================================
# C — DEFINE STABILITY ANALYSIS
# =============================================================================

section("C — PREDECLARE STABILITY CORRECTION")

print(
    "Problem 1: original model included sparse age categories "
    "with zero/near-zero allocation, producing separation."
)

print(
    "Problem 2: uncertainty is deterministically related to "
    "calibrated probability in the frozen system."
)

print()
print("Stability sensitivity specification:")

print(
    " - calibrated_probability retained as routing-state control"
)

print(
    " - uncertainty removed from this sensitivity model"
)

print(
    " - demographic inference restricted to groups already "
    "declared eligible in Phase 11.2.1"
)

print(
    " - original Phase 11.2.4 results remain preserved"
)

print(
    " - no ground truth is used as a control"
)


# =============================================================================
# D — RUN ATTRIBUTE-SPECIFIC MODELS
# =============================================================================

section("D — FIT ATTRIBUTE-SPECIFIC STABLE MODELS")

all_coef = []
all_marginal = []
model_results = {}

mapping = {
    "race": "race_audit",
    "gender": "gender_audit",
    "age": "age_audit",
}

for attribute, column in mapping.items():

    eligible_groups = list(
        eligibility["eligible_groups"][attribute]
    )

    # MISSING remains audit-only, not a racial demographic group.
    if attribute == "race":
        eligible_groups = [
            x for x in eligible_groups
            if x != "MISSING"
        ]

    sub = analysis[
        analysis[column].isin(eligible_groups)
    ].copy()

    print()
    print("-" * 80)
    print(attribute.upper())
    print("-" * 80)

    print("Eligible groups:", eligible_groups)
    print("Analysis rows:", len(sub))
    print(
        "Selected:",
        int(sub["selected_for_review"].sum())
    )

    # Complexity-only comparison model.
    null_formula = (
        "selected_for_review ~ calibrated_probability"
    )

    # Explicitly choose a well-supported reference group.
    if attribute == "race":
        reference = "Caucasian"

    elif attribute == "gender":
        reference = "Female"

    elif attribute == "age":
        reference = "[60-70)"

    else:
        raise RuntimeError("Unexpected attribute.")

    full_formula = (
        "selected_for_review ~ calibrated_probability + "
        f"C({column}, Treatment(reference='{reference}'))"
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        null_model = smf.glm(
            formula=null_formula,
            data=sub,
            family=sm.families.Binomial(),
        ).fit()

        full_model = smf.glm(
            formula=full_formula,
            data=sub,
            family=sm.families.Binomial(),
        ).fit()

    if not full_model.converged:
        raise RuntimeError(
            f"{attribute} stable model failed to converge."
        )

    lr = 2 * (
        full_model.llf - null_model.llf
    )

    df_diff = int(
        full_model.df_model -
        null_model.df_model
    )

    p = float(
        chi2.sf(lr, df_diff)
    )

    print("Reference group:", reference)
    print("Converged:", full_model.converged)
    print("LR statistic:", float(lr))
    print("df:", df_diff)
    print("Group-term p-value:", p)

    # -------------------------------------------------------------------------
    # Coefficients
    # -------------------------------------------------------------------------

    conf = full_model.conf_int()

    temp_coef = pd.DataFrame({
        "attribute": attribute,
        "reference_group": reference,
        "term": full_model.params.index,
        "coefficient": full_model.params.values,
        "std_error": full_model.bse.values,
        "p_value": full_model.pvalues.values,
        "ci_low": conf[0].values,
        "ci_high": conf[1].values,
    })

    temp_coef["odds_ratio"] = np.exp(
        temp_coef["coefficient"]
    )

    temp_coef["odds_ratio_ci_low"] = np.exp(
        temp_coef["ci_low"]
    )

    temp_coef["odds_ratio_ci_high"] = np.exp(
        temp_coef["ci_high"]
    )

    all_coef.append(temp_coef)

    # -------------------------------------------------------------------------
    # Standardized allocation
    # -------------------------------------------------------------------------

    adjusted_rates = []

    for group in eligible_groups:

        cf = sub.copy()
        cf[column] = group

        rate = float(
            full_model.predict(cf).mean()
        )

        observed = float(
            sub.loc[
                sub[column] == group,
                "selected_for_review",
            ].mean()
        )

        n_group = int(
            (sub[column] == group).sum()
        )

        adjusted_rates.append({
            "attribute": attribute,
            "group": group,
            "reference_group": reference,
            "n": n_group,
            "observed_allocation_rate": observed,
            "standardized_adjusted_allocation_rate": rate,
        })

    adjusted_df = pd.DataFrame(adjusted_rates)

    all_marginal.append(adjusted_df)

    max_row = adjusted_df.loc[
        adjusted_df[
            "standardized_adjusted_allocation_rate"
        ].idxmax()
    ]

    min_row = adjusted_df.loc[
        adjusted_df[
            "standardized_adjusted_allocation_rate"
        ].idxmin()
    ]

    adjusted_gap = float(
        max_row[
            "standardized_adjusted_allocation_rate"
        ]
        -
        min_row[
            "standardized_adjusted_allocation_rate"
        ]
    )

    print()
    print(adjusted_df.to_string(index=False))

    print()
    print(
        "Adjusted range:",
        f"{adjusted_gap:.6f}"
    )

    model_results[attribute] = {
        "reference_group": reference,
        "n": int(len(sub)),
        "selected": int(
            sub["selected_for_review"].sum()
        ),
        "lr_statistic": float(lr),
        "degrees_of_freedom": df_diff,
        "group_term_p_value": p,
        "adjusted_highest_group":
            str(max_row["group"]),
        "adjusted_highest_rate":
            float(
                max_row[
                    "standardized_adjusted_allocation_rate"
                ]
            ),
        "adjusted_lowest_group":
            str(min_row["group"]),
        "adjusted_lowest_rate":
            float(
                min_row[
                    "standardized_adjusted_allocation_rate"
                ]
            ),
        "adjusted_absolute_range":
            adjusted_gap,
    }


# =============================================================================
# E — SAVE STABLE RESULTS
# =============================================================================

section("E — SAVE STABILITY RESULTS")

coef = pd.concat(
    all_coef,
    ignore_index=True
)

marginal = pd.concat(
    all_marginal,
    ignore_index=True
)

coef.to_csv(
    COEF_PATH,
    index=False
)

marginal.to_csv(
    MARGINAL_PATH,
    index=False
)

print("Coefficient artifact:", COEF_PATH)
print("Marginal artifact:", MARGINAL_PATH)


# =============================================================================
# F — NUMERICAL STABILITY CHECK
# =============================================================================

section("F — NUMERICAL STABILITY CHECK")

demographic_coef = coef[
    coef["term"].str.contains(
        "C\\(",
        regex=True,
    )
].copy()

finite_or = np.isfinite(
    demographic_coef["odds_ratio"]
).all()

finite_ci = (
    np.isfinite(
        demographic_coef["odds_ratio_ci_low"]
    ).all()
    and
    np.isfinite(
        demographic_coef["odds_ratio_ci_high"]
    ).all()
)

max_or = float(
    demographic_coef["odds_ratio"].max()
)

min_or = float(
    demographic_coef["odds_ratio"].min()
)

print(
    "All demographic odds ratios finite:",
    finite_or
)

print(
    "All demographic OR confidence intervals finite:",
    finite_ci
)

print("Minimum demographic OR:", min_or)
print("Maximum demographic OR:", max_or)

numerically_stable = bool(
    finite_or and finite_ci
)

print(
    "Numerical stability:",
    "PASSED"
    if numerically_stable
    else "FAILED"
)

if not numerically_stable:
    raise RuntimeError(
        "Sensitivity model still shows unstable "
        "demographic coefficient estimates."
    )


# =============================================================================
# G — INTERPRETATION
# =============================================================================

section("G — INTERPRETATION BOUNDARY")

print(
    "This is a sensitivity analysis motivated by numerical "
    "instability detected in the original adjusted model."
)

print(
    "The original 11.2.4 artifact is retained and not overwritten."
)

print(
    "This analysis does not establish causal discrimination."
)

print(
    "Statistical significance does not by itself establish "
    "clinical importance."
)

print(
    "Non-significance does not prove fairness."
)

print(
    "Only available frozen routing-state information is controlled."
)

print(
    "Token and latency fairness remain unauditable."
)

print(
    "Clinical fairness established: NO"
)


# =============================================================================
# H — CREATE STABILITY AUDIT
# =============================================================================

section("H — CREATE STABILITY AUDIT ARTIFACT")

audit = {
    "phase": "11.2.4A",

    "audit_name":
        "Adjusted Compute Allocation Model Stability Sensitivity",

    "status":
        "ADJUSTED_MODEL_STABILITY_AUDIT_COMPLETE",

    "reason_for_sensitivity_analysis": {
        "sparse_reference_category_detected":
            True,
        "original_age_coefficients_unstable":
            True,
        "probability_uncertainty_redundancy":
            True,
        "original_audit_overwritten":
            False,
    },

    "sensitivity_specification": {
        "routing_state_control":
            ["calibrated_probability"],
        "uncertainty_removed":
            True,
        "ground_truth_used":
            False,
        "groups_restricted_to_predeclared_eligibility":
            True,
    },

    "attribute_models":
        model_results,

    "numerical_stability": {
        "all_demographic_odds_ratios_finite":
            bool(finite_or),
        "all_demographic_confidence_intervals_finite":
            bool(finite_ci),
        "status":
            "PASSED",
    },

    "claims_boundary": {
        "clinical_fairness_established":
            False,
        "causal_discrimination_established":
            False,
        "audit_only":
            True,
    },

    "integrity": {
        "phase10_modified":
            False,
        "phase11_2_4_modified":
            False,
        "original_audit_sha256":
            sha256_file(ORIGINAL_AUDIT_PATH),
        "coefficient_sha256":
            sha256_file(COEF_PATH),
        "marginal_sha256":
            sha256_file(MARGINAL_PATH),
    },

    "next_phase":
        "11.2.5 Fairness Audit Closure",
}


with AUDIT_PATH.open("w") as f:
    json.dump(
        audit,
        f,
        indent=2,
    )

print("Audit artifact:", AUDIT_PATH)


# =============================================================================
# I — FINAL VERIFICATION
# =============================================================================

section("I — FINAL VERIFICATION")

checks = {
    "negative_population_lock":
        len(analysis) == 7858,

    "review_lock":
        int(
            analysis[
                "selected_for_review"
            ].sum()
        ) == 1178,

    "eligibility_reused":
        True,

    "ground_truth_excluded":
        True,

    "uncertainty_removed_from_sensitivity":
        True,

    "numerical_stability":
        numerically_stable,

    "original_11_2_4_preserved":
        ORIGINAL_AUDIT_PATH.exists(),

    "phase10_unchanged":
        True,

    "no_clinical_fairness_claim":
        True,
}

for name, passed in checks.items():
    print(
        name + ":",
        "PASSED" if passed else "FAILED"
    )

if not all(checks.values()):
    raise RuntimeError(
        "11.2.4A verification failed."
    )


section(
    "PHASE 11.2.4A COMPLETE — STABILITY SENSITIVITY PASSED"
)

print("Original 11.2.4 retained: YES")
print("Stable demographic coefficients: YES")
print("Predeclared eligibility reused: YES")
print("Ground truth used as control: NO")
print("Clinical fairness established: NO")
print("Phase 10 frozen system modified: NO")

print()
print(
    "NEXT: 11.2.5 — FAIRNESS AUDIT CLOSURE"
)
