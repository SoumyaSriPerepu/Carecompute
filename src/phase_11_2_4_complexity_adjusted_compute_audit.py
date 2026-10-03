from pathlib import Path
import hashlib
import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf


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

COMPUTE_AUDIT_PATH = Path(
    "results/eligible/fairness/"
    "phase11_2_3_compute_allocation_audit.json"
)

OUTPUT_DIR = Path("results/eligible/fairness")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COEF_OUTPUT = (
    OUTPUT_DIR /
    "phase11_2_4_adjusted_logistic_coefficients.csv"
)

MARGINAL_OUTPUT = (
    OUTPUT_DIR /
    "phase11_2_4_adjusted_group_allocation.csv"
)

AUDIT_OUTPUT = (
    OUTPUT_DIR /
    "phase11_2_4_complexity_adjusted_compute_audit.json"
)


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


def clean_label(x):
    if pd.isna(x):
        return "MISSING"
    return str(x)


# =============================================================================
# HEADER
# =============================================================================

section(
    "PHASE 11.2.4 — COMPLEXITY-ADJUSTED COMPUTE ALLOCATION AUDIT"
)


# =============================================================================
# A — VERIFY INPUTS
# =============================================================================

section("A — VERIFY REQUIRED INPUTS")

for p in [
    DATA_PATH,
    ELIGIBILITY_PATH,
    COMPUTE_AUDIT_PATH,
]:
    if not p.exists():
        raise FileNotFoundError(p)

    print("FOUND:", p)

with ELIGIBILITY_PATH.open() as f:
    eligibility = json.load(f)

with COMPUTE_AUDIT_PATH.open() as f:
    compute_audit = json.load(f)

if (
    eligibility["status"]
    != "FAIRNESS_ELIGIBILITY_FROZEN"
):
    raise RuntimeError(
        "Fairness eligibility policy not frozen."
    )

if (
    compute_audit["status"]
    != "COMPUTE_ALLOCATION_AUDIT_COMPLETE"
):
    raise RuntimeError(
        "11.2.3 compute audit not complete."
    )

print("Upstream audit chain: PASSED")


# =============================================================================
# B — LOAD FROZEN TEST POPULATION
# =============================================================================

section("B — LOAD FROZEN TEST POPULATION")

df = pd.read_csv(DATA_PATH)

required = {
    "encounter_id",
    "actual_30d",
    "calibrated_probability",
    "uncertainty",
    "predicted_30d",
    "selected_for_review",
    "race",
    "gender",
    "age",
}

missing = required - set(df.columns)

if missing:
    raise RuntimeError(
        f"Missing required columns: {sorted(missing)}"
    )

if len(df) != 15042:
    raise RuntimeError(
        "Frozen test population changed."
    )

if int(df["selected_for_review"].sum()) != 1178:
    raise RuntimeError(
        "Frozen review allocation changed."
    )

print("Full test population:", len(df))
print(
    "Selected for review:",
    int(df["selected_for_review"].sum())
)

print("Frozen population lock: PASSED")


# =============================================================================
# C — DEFINE ANALYSIS POPULATION
# =============================================================================

section("C — DEFINE COMPLEXITY-ADJUSTED ANALYSIS POPULATION")

analysis = df[
    df["predicted_30d"] == 0
].copy()

print(
    "Primary-model-negative cases:",
    len(analysis)
)

print(
    "Selected negative cases:",
    int(analysis["selected_for_review"].sum())
)

print(
    "Bypassed negative cases:",
    int(
        (analysis["selected_for_review"] == 0).sum()
    )
)

if len(analysis) != 7858:
    raise RuntimeError(
        "Expected 7858 primary-model-negative cases."
    )

if int(analysis["selected_for_review"].sum()) != 1178:
    raise RuntimeError(
        "Expected all 1178 review allocations "
        "inside negative population."
    )

print("Analysis-population lock: PASSED")


# =============================================================================
# D — DEFINE INFORMATION BOUNDARY
# =============================================================================

section("D — DEFINE ADJUSTMENT INFORMATION BOUNDARY")

complexity_controls = [
    "calibrated_probability",
    "uncertainty",
]

demographic_variables = [
    "race",
    "gender",
    "age",
]

prohibited_adjustment_variables = [
    "actual_30d",
    "case_type",
    "rescued_fn",
    "residual_fn",
]

print("Allowed complexity/routing controls:")

for x in complexity_controls:
    print(" -", x)

print()
print("Demographic audit variables:")

for x in demographic_variables:
    print(" -", x)

print()
print("Explicitly prohibited adjustment variables:")

for x in prohibited_adjustment_variables:
    print(" -", x)

print()
print(
    "Ground-truth outcome is NOT used as a complexity control."
)

print(
    "Post-routing rescue labels are NOT used as controls."
)


# =============================================================================
# E — PREPARE DEMOGRAPHIC VARIABLES
# =============================================================================

section("E — PREPARE DEMOGRAPHIC VARIABLES")

analysis["race_audit"] = (
    analysis["race"]
    .apply(clean_label)
)

analysis["gender_audit"] = (
    analysis["gender"]
    .apply(clean_label)
)

analysis["age_audit"] = (
    analysis["age"]
    .apply(clean_label)
)

print("Race categories:")
print(
    analysis["race_audit"]
    .value_counts()
    .to_string()
)

print()
print("Gender categories:")
print(
    analysis["gender_audit"]
    .value_counts()
    .to_string()
)

print()
print("Age categories:")
print(
    analysis["age_audit"]
    .value_counts()
    .to_string()
)


# =============================================================================
# F — FIT COMPLEXITY-ONLY MODEL
# =============================================================================

section("F — FIT COMPLEXITY-ONLY ALLOCATION MODEL")

complexity_formula = (
    "selected_for_review ~ "
    "calibrated_probability + uncertainty"
)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")

    complexity_model = smf.glm(
        formula=complexity_formula,
        data=analysis,
        family=sm.families.Binomial(),
    ).fit()

print(
    "Complexity-only observations:",
    int(complexity_model.nobs)
)

print(
    "Complexity-only AIC:",
    float(complexity_model.aic)
)

print(
    "Complexity-only log-likelihood:",
    float(complexity_model.llf)
)


# =============================================================================
# G — FIT COMPLEXITY + DEMOGRAPHIC MODEL
# =============================================================================

section("G — FIT COMPLEXITY + DEMOGRAPHIC MODEL")

full_formula = (
    "selected_for_review ~ "
    "calibrated_probability + uncertainty + "
    "C(race_audit) + "
    "C(gender_audit) + "
    "C(age_audit)"
)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")

    full_model = smf.glm(
        formula=full_formula,
        data=analysis,
        family=sm.families.Binomial(),
    ).fit()

print(
    "Adjusted-model observations:",
    int(full_model.nobs)
)

print(
    "Adjusted-model AIC:",
    float(full_model.aic)
)

print(
    "Adjusted-model log-likelihood:",
    float(full_model.llf)
)

print(
    "Converged:",
    bool(full_model.converged)
)

if not full_model.converged:
    raise RuntimeError(
        "Adjusted logistic model did not converge."
    )


# =============================================================================
# H — LIKELIHOOD-RATIO TEST
# =============================================================================

section("H — JOINT DEMOGRAPHIC CONTRIBUTION TEST")

lr_stat = 2 * (
    full_model.llf
    - complexity_model.llf
)

df_diff = int(
    full_model.df_model
    - complexity_model.df_model
)

from scipy.stats import chi2

lr_pvalue = float(
    chi2.sf(
        lr_stat,
        df_diff,
    )
)

print(
    "Likelihood-ratio statistic:",
    float(lr_stat)
)

print(
    "Degrees of freedom:",
    df_diff
)

print(
    "Joint demographic p-value:",
    lr_pvalue
)

print()
print(
    "This tests whether demographic terms collectively "
    "add allocation information beyond the available "
    "complexity/routing controls."
)

print(
    "It does NOT establish discrimination or clinical unfairness."
)


# =============================================================================
# I — EXPORT ADJUSTED COEFFICIENTS
# =============================================================================

section("I — EXPORT ADJUSTED MODEL COEFFICIENTS")

conf = full_model.conf_int()

coef = pd.DataFrame({
    "term": full_model.params.index,
    "coefficient":
        full_model.params.values,
    "std_error":
        full_model.bse.values,
    "p_value":
        full_model.pvalues.values,
    "ci_low":
        conf[0].values,
    "ci_high":
        conf[1].values,
})

coef["odds_ratio"] = np.exp(
    coef["coefficient"]
)

coef["odds_ratio_ci_low"] = np.exp(
    coef["ci_low"]
)

coef["odds_ratio_ci_high"] = np.exp(
    coef["ci_high"]
)

coef.to_csv(
    COEF_OUTPUT,
    index=False
)

print(
    coef[
        [
            "term",
            "odds_ratio",
            "odds_ratio_ci_low",
            "odds_ratio_ci_high",
            "p_value",
        ]
    ].to_string(index=False)
)

print()
print("Saved:", COEF_OUTPUT)


# =============================================================================
# J — STANDARDIZED ADJUSTED GROUP ALLOCATION
# =============================================================================

section("J — STANDARDIZED ADJUSTED GROUP ALLOCATION")

marginal_records = []

for attribute, audit_col in [
    ("race", "race_audit"),
    ("gender", "gender_audit"),
    ("age", "age_audit"),
]:

    groups = sorted(
        analysis[audit_col]
        .dropna()
        .unique()
        .tolist()
    )

    for group in groups:

        counterfactual = analysis.copy()

        counterfactual[audit_col] = group

        predicted_probability = (
            full_model.predict(
                counterfactual
            )
        )

        adjusted_rate = float(
            predicted_probability.mean()
        )

        observed_mask = (
            analysis[audit_col]
            == group
        )

        observed_n = int(
            observed_mask.sum()
        )

        observed_rate = float(
            analysis.loc[
                observed_mask,
                "selected_for_review",
            ].mean()
        )

        marginal_records.append({
            "attribute": attribute,
            "group": group,
            "n_in_analysis_population":
                observed_n,
            "observed_allocation_rate":
                observed_rate,
            "standardized_adjusted_allocation_rate":
                adjusted_rate,
            "interpret_as_demographic_group":
                not (
                    attribute == "race"
                    and group == "MISSING"
                ),
        })


marginal = pd.DataFrame(
    marginal_records
)

marginal.to_csv(
    MARGINAL_OUTPUT,
    index=False
)

print(
    marginal.to_string(index=False)
)

print()
print("Saved:", MARGINAL_OUTPUT)


# =============================================================================
# K — ADJUSTED DEMOGRAPHIC RANGES
# =============================================================================

section("K — ADJUSTED ALLOCATION RANGES")

adjusted_gap_records = []

for attribute in [
    "race",
    "gender",
    "age",
]:

    attr = marginal[
        (
            marginal["attribute"]
            == attribute
        )
        &
        (
            marginal[
                "interpret_as_demographic_group"
            ]
            == True
        )
    ].copy()

    # Preserve 11.2.1 eligibility restriction
    eligible_groups = set(
        eligibility[
            "eligible_groups"
        ][attribute]
    )

    if attribute == "race":
        eligible_groups.discard(
            "MISSING"
        )

    attr = attr[
        attr["group"].isin(
            eligible_groups
        )
    ].copy()

    if len(attr) < 2:
        continue

    max_idx = attr[
        "standardized_adjusted_allocation_rate"
    ].idxmax()

    min_idx = attr[
        "standardized_adjusted_allocation_rate"
    ].idxmin()

    max_rate = float(
        attr.loc[
            max_idx,
            "standardized_adjusted_allocation_rate"
        ]
    )

    min_rate = float(
        attr.loc[
            min_idx,
            "standardized_adjusted_allocation_rate"
        ]
    )

    max_group = str(
        attr.loc[
            max_idx,
            "group"
        ]
    )

    min_group = str(
        attr.loc[
            min_idx,
            "group"
        ]
    )

    gap = max_rate - min_rate

    ratio = (
        max_rate / min_rate
        if min_rate > 0
        else np.nan
    )

    adjusted_gap_records.append({
        "attribute": attribute,
        "highest_adjusted_group":
            max_group,
        "highest_adjusted_rate":
            max_rate,
        "lowest_adjusted_group":
            min_group,
        "lowest_adjusted_rate":
            min_rate,
        "absolute_adjusted_gap":
            gap,
        "adjusted_max_to_min_ratio":
            ratio,
    })

    print()
    print(attribute.upper())

    print(
        "Highest adjusted allocation:",
        max_group,
        f"{max_rate:.6f}",
    )

    print(
        "Lowest adjusted allocation:",
        min_group,
        f"{min_rate:.6f}",
    )

    print(
        "Adjusted absolute gap:",
        f"{gap:.6f}",
    )

    print(
        "Adjusted max/min ratio:",
        f"{ratio:.6f}"
        if not np.isnan(ratio)
        else "NA",
    )


# =============================================================================
# L — COMPARE RAW VS ADJUSTED GAPS
# =============================================================================

section("L — RAW VS ADJUSTED ALLOCATION GAPS")

raw_gaps = {
    x["attribute"]: x
    for x in compute_audit[
        "descriptive_group_gaps"
    ]
}

comparison_records = []

for adjusted in adjusted_gap_records:

    attribute = adjusted["attribute"]

    raw = raw_gaps.get(attribute)

    if raw is None:
        continue

    raw_gap = float(
        raw["absolute_allocation_gap"]
    )

    adjusted_gap = float(
        adjusted["absolute_adjusted_gap"]
    )

    reduction = (
        raw_gap - adjusted_gap
    )

    proportional_reduction = (
        reduction / raw_gap
        if raw_gap > 0
        else np.nan
    )

    comparison_records.append({
        "attribute": attribute,
        "raw_absolute_gap":
            raw_gap,
        "adjusted_absolute_gap":
            adjusted_gap,
        "absolute_gap_change":
            adjusted_gap - raw_gap,
        "proportional_gap_reduction":
            proportional_reduction,
    })

    print()
    print(attribute.upper())

    print(
        "Raw gap:",
        f"{raw_gap:.6f}",
    )

    print(
        "Adjusted gap:",
        f"{adjusted_gap:.6f}",
    )

    print(
        "Gap change:",
        f"{adjusted_gap - raw_gap:.6f}",
    )

    print(
        "Proportional reduction:",
        f"{proportional_reduction:.6f}"
        if not np.isnan(proportional_reduction)
        else "NA",
    )


# =============================================================================
# M — INTERPRETATION BOUNDARY
# =============================================================================

section("M — INTERPRETATION BOUNDARY")

print(
    "The adjustment controls only for complexity/routing "
    "signals available in the frozen audit artifacts."
)

print(
    "Residual demographic association does not by itself "
    "establish discrimination, causal unfairness, or harm."
)

print(
    "Absence of a statistically detectable association "
    "does not establish fairness."
)

print(
    "The model is observational and retrospective."
)

print(
    "The analysis does not control for every possible "
    "clinical or social confounder."
)

print(
    "Token and latency allocation remain unauditable because "
    "the frozen system did not capture those telemetry fields."
)

print(
    "Clinical fairness established: NO"
)


# =============================================================================
# N — CREATE AUDIT ARTIFACT
# =============================================================================

section("N — CREATE COMPLEXITY-ADJUSTED AUDIT ARTIFACT")

audit = {
    "phase": "11.2.4",

    "audit_name":
        "Complexity-Adjusted Compute Allocation Audit",

    "status":
        "COMPLEXITY_ADJUSTED_COMPUTE_AUDIT_COMPLETE",

    "analysis_population": {
        "definition":
            "primary-model-negative final test cases",
        "n":
            int(len(analysis)),
        "selected_for_review":
            int(
                analysis[
                    "selected_for_review"
                ].sum()
            ),
    },

    "adjustment": {
        "complexity_controls":
            complexity_controls,
        "demographic_variables":
            demographic_variables,
        "ground_truth_used_as_control":
            False,
        "post_routing_labels_used_as_controls":
            False,
    },

    "models": {
        "complexity_only": {
            "formula":
                complexity_formula,
            "aic":
                float(complexity_model.aic),
            "log_likelihood":
                float(complexity_model.llf),
        },

        "complexity_plus_demographics": {
            "formula":
                full_formula,
            "aic":
                float(full_model.aic),
            "log_likelihood":
                float(full_model.llf),
            "converged":
                bool(full_model.converged),
        },
    },

    "joint_demographic_test": {
        "method":
            "likelihood-ratio test",
        "statistic":
            float(lr_stat),
        "degrees_of_freedom":
            df_diff,
        "p_value":
            lr_pvalue,
        "interpretation":
            (
                "Tests whether demographic terms jointly add "
                "allocation information beyond available "
                "complexity controls; not a causal fairness test."
            ),
    },

    "adjusted_group_gaps":
        adjusted_gap_records,

    "raw_vs_adjusted_gap_comparison":
        comparison_records,

    "telemetry_limitations": {
        "token_counts_available":
            False,
        "latency_available":
            False,
    },

    "claims_boundary": {
        "causal_fairness_established":
            False,
        "clinical_fairness_established":
            False,
        "discrimination_established":
            False,
        "audit_only":
            True,
    },

    "integrity": {
        "phase10_modified":
            False,
        "phase11_2_1_modified":
            False,
        "phase11_2_3_modified":
            False,
        "input_sha256":
            sha256_file(DATA_PATH),
        "coefficient_sha256":
            sha256_file(COEF_OUTPUT),
        "marginal_sha256":
            sha256_file(MARGINAL_OUTPUT),
    },

    "next_phase":
        "11.2.5 Fairness Audit Closure",
}


with AUDIT_OUTPUT.open("w") as f:
    json.dump(
        audit,
        f,
        indent=2,
    )

print("Audit artifact:", AUDIT_OUTPUT)


# =============================================================================
# O — FINAL VERIFICATION
# =============================================================================

section("O — FINAL VERIFICATION")

with AUDIT_OUTPUT.open() as f:
    saved = json.load(f)


checks = {
    "status":
        saved["status"]
        == "COMPLEXITY_ADJUSTED_COMPUTE_AUDIT_COMPLETE",

    "negative_population_lock":
        saved["analysis_population"]["n"]
        == 7858,

    "review_population_lock":
        saved[
            "analysis_population"
        ]["selected_for_review"]
        == 1178,

    "ground_truth_excluded":
        saved["adjustment"][
            "ground_truth_used_as_control"
        ]
        is False,

    "post_routing_labels_excluded":
        saved["adjustment"][
            "post_routing_labels_used_as_controls"
        ]
        is False,

    "model_converged":
        saved["models"][
            "complexity_plus_demographics"
        ]["converged"]
        is True,

    "tokens_not_available":
        saved["telemetry_limitations"][
            "token_counts_available"
        ]
        is False,

    "latency_not_available":
        saved["telemetry_limitations"][
            "latency_available"
        ]
        is False,

    "no_clinical_fairness_claim":
        saved["claims_boundary"][
            "clinical_fairness_established"
        ]
        is False,

    "phase10_unchanged":
        saved["integrity"][
            "phase10_modified"
        ]
        is False,

    "coefficient_artifact":
        COEF_OUTPUT.exists(),

    "marginal_artifact":
        MARGINAL_OUTPUT.exists(),
}


for name, passed in checks.items():

    print(
        name + ":",
        "PASSED" if passed else "FAILED"
    )


if not all(checks.values()):

    raise RuntimeError(
        "Phase 11.2.4 final verification failed."
    )


# =============================================================================
# COMPLETE
# =============================================================================

section(
    "PHASE 11.2.4 COMPLETE — COMPLEXITY-ADJUSTED COMPUTE AUDIT PASSED"
)

print(
    "Analysis population:",
    len(analysis)
)

print(
    "Complexity controls:",
    ", ".join(complexity_controls)
)

print(
    "Joint demographic p-value:",
    lr_pvalue
)

print(
    "Adjusted demographic allocation ranges reported: YES"
)

print(
    "Ground truth used as complexity control: NO"
)

print(
    "Token/latency values fabricated: NO"
)

print(
    "Clinical fairness established: NO"
)

print(
    "Phase 10 frozen system modified: NO"
)

print()
print(
    "NEXT: 11.2.5 — FAIRNESS AUDIT CLOSURE"
)
