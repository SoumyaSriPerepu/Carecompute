import pandas as pd
import numpy as np
import os


# ============================================================
# PHASE 7.6.4 — FAIR ROUTER COMPARISON
# ============================================================

ROUTER_DATA_PATH = (
    "results/eligible/router_validation.csv"
)

RESCUE_PATH = (
    "results/eligible/"
    "fn_rescue_router_predictions.csv"
)

OUTPUT_PATH = (
    "results/eligible/"
    "router_comparison.csv"
)


print("=" * 70)
print("PHASE 7.6.4 — FAIR ROUTER COMPARISON")
print("=" * 70)


# ============================================================
# 1. LOAD DATA
# ============================================================

router = pd.read_csv(
    ROUTER_DATA_PATH,
    low_memory=False
)

rescue = pd.read_csv(
    RESCUE_PATH,
    low_memory=False
)


print()
print("Router validation rows:", len(router))
print("Rescue-router rows:", len(rescue))


# ============================================================
# 2. KEEP ONLY MODEL-NEGATIVE CASES
#
# We compare routing methods on exactly the SAME population:
#
# TN + FN
#
# This prevents an unfair comparison with methods that rank
# the entire validation population.
# ============================================================

low_risk = router[
    router["predicted_30d"] == 0
].copy()


print()
print("MODEL-NEGATIVE POPULATION")
print("-" * 50)

print(
    low_risk["case_type"].value_counts()
)


total_negative_predictions = len(
    low_risk
)

total_fn = int(
    (low_risk["case_type"] == "FN").sum()
)


print()
print(
    "Total model-negative cases:",
    total_negative_predictions
)

print(
    "Total false negatives:",
    total_fn
)

print(
    "FN prevalence:",
    total_fn / total_negative_predictions
)


# ============================================================
# 3. MERGE CROSS-VALIDATED RESCUE ROUTER SCORE
#
# IMPORTANT:
# Use the OUT-OF-FOLD router probability generated in 7.6.3.
# ============================================================

rescue_scores = rescue[
    [
        "encounter_id",
        "fn_router_probability"
    ]
].copy()


low_risk = low_risk.merge(
    rescue_scores,
    on="encounter_id",
    how="left",
    validate="one_to_one"
)


print()
print(
    "Missing rescue scores:",
    low_risk[
        "fn_router_probability"
    ].isna().sum()
)


if (
    low_risk[
        "fn_router_probability"
    ].isna().sum()
    != 0
):
    raise ValueError(
        "Some model-negative cases are missing "
        "FN rescue router scores."
    )


# ============================================================
# 4. DEFINE ROUTING SCORES
#
# Higher score = review earlier.
# ============================================================

# Method A:
# Higher calibrated risk among negative predictions.
low_risk[
    "score_probability"
] = low_risk[
    "calibrated_probability"
]


# Method B:
# Smaller distance from decision boundary should be reviewed
# first, so multiply distance by -1.
low_risk[
    "score_boundary"
] = -low_risk[
    "boundary_distance"
]


# Method C:
# Larger disagreement should be reviewed first.
low_risk[
    "score_disagreement"
] = low_risk[
    "model_disagreement_std"
]


# Method D:
# Cross-validated learned rescue router.
low_risk[
    "score_rescue_router"
] = low_risk[
    "fn_router_probability"
]


# ============================================================
# 5. REVIEW BUDGETS
#
# These percentages refer to the model-negative population.
# ============================================================

review_budgets = [
    0.05,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.40,
    0.50
]


methods = {

    "Probability":
        "score_probability",

    "Boundary":
        "score_boundary",

    "Disagreement":
        "score_disagreement",

    "Rescue Router":
        "score_rescue_router"
}


# ============================================================
# 6. RANDOM BASELINE
#
# Instead of one random draw, estimate expected performance
# analytically.
#
# If we review X% of the negative population randomly,
# expected FN capture is approximately X%.
# ============================================================

results = []


for budget in review_budgets:

    n_review = int(
        np.ceil(
            total_negative_predictions
            * budget
        )
    )


    # --------------------------------------------------------
    # Actual routing methods
    # --------------------------------------------------------

    for method_name, score_column in methods.items():

        ranked = (
            low_risk
            .sort_values(
                score_column,
                ascending=False
            )
            .reset_index(
                drop=True
            )
        )


        reviewed = ranked.iloc[
            :n_review
        ]


        fn_captured = int(
            (
                reviewed[
                    "case_type"
                ]
                == "FN"
            ).sum()
        )


        fn_capture_rate = (
            fn_captured
            / total_fn
        )


        review_precision = (
            fn_captured
            / n_review
        )


        overall_validation_review_rate = (
            n_review
            / len(router)
        )


        results.append({

            "method":
                method_name,

            "low_risk_review_budget":
                budget,

            "patients_reviewed":
                n_review,

            "overall_validation_review_rate":
                overall_validation_review_rate,

            "fn_captured":
                fn_captured,

            "fn_capture_rate":
                fn_capture_rate,

            "review_precision":
                review_precision
        })


    # --------------------------------------------------------
    # Expected random baseline
    # --------------------------------------------------------

    expected_random_fn = (
        total_fn
        * n_review
        / total_negative_predictions
    )


    results.append({

        "method":
            "Random",

        "low_risk_review_budget":
            budget,

        "patients_reviewed":
            n_review,

        "overall_validation_review_rate":
            n_review / len(router),

        "fn_captured":
            expected_random_fn,

        "fn_capture_rate":
            expected_random_fn / total_fn,

        "review_precision":
            total_fn / total_negative_predictions
    })


# ============================================================
# 7. CREATE RESULT TABLE
# ============================================================

results_df = pd.DataFrame(
    results
)


# ============================================================
# 8. PRINT LONG-FORM RESULTS
# ============================================================

print()
print("FULL ROUTER COMPARISON")
print("-" * 70)

print(
    results_df.to_string(
        index=False
    )
)


# ============================================================
# 9. CREATE EASY-TO-READ FN CAPTURE TABLE
# ============================================================

capture_table = (
    results_df
    .pivot(
        index="low_risk_review_budget",
        columns="method",
        values="fn_capture_rate"
    )
)


print()
print("=" * 70)
print("FALSE-NEGATIVE CAPTURE RATE")
print("=" * 70)

print(
    capture_table.to_string()
)


# ============================================================
# 10. REVIEW PRECISION TABLE
# ============================================================

precision_table = (
    results_df
    .pivot(
        index="low_risk_review_budget",
        columns="method",
        values="review_precision"
    )
)


print()
print("=" * 70)
print("REVIEW PRECISION")
print("=" * 70)

print(
    precision_table.to_string()
)


# ============================================================
# 11. DETERMINE BEST METHOD AT EACH BUDGET
# ============================================================

non_random = results_df[
    results_df["method"] != "Random"
].copy()


best_rows = (
    non_random
    .sort_values(
        [
            "low_risk_review_budget",
            "fn_capture_rate"
        ],
        ascending=[
            True,
            False
        ]
    )
    .groupby(
        "low_risk_review_budget"
    )
    .first()
    .reset_index()
)


print()
print("=" * 70)
print("BEST METHOD AT EACH REVIEW BUDGET")
print("=" * 70)

print(
    best_rows[
        [
            "low_risk_review_budget",
            "method",
            "patients_reviewed",
            "overall_validation_review_rate",
            "fn_captured",
            "fn_capture_rate",
            "review_precision"
        ]
    ].to_string(
        index=False
    )
)


# ============================================================
# 12. RESCUE ROUTER IMPROVEMENT OVER RANDOM
# ============================================================

rescue_results = results_df[
    results_df["method"]
    == "Rescue Router"
].copy()


rescue_results[
    "lift_over_random"
] = (
    rescue_results[
        "fn_capture_rate"
    ]
    /
    rescue_results[
        "low_risk_review_budget"
    ]
)


print()
print("=" * 70)
print("RESCUE ROUTER LIFT OVER RANDOM")
print("=" * 70)

print(
    rescue_results[
        [
            "low_risk_review_budget",
            "fn_capture_rate",
            "lift_over_random"
        ]
    ].to_string(
        index=False
    )
)


# ============================================================
# 13. SAVE
# ============================================================

os.makedirs(
    "results/eligible",
    exist_ok=True
)


results_df.to_csv(
    OUTPUT_PATH,
    index=False
)


capture_table.to_csv(
    "results/eligible/"
    "router_fn_capture_comparison.csv"
)


precision_table.to_csv(
    "results/eligible/"
    "router_review_precision_comparison.csv"
)


best_rows.to_csv(
    "results/eligible/"
    "router_best_method_by_budget.csv",
    index=False
)


print()
print("FILES SAVED")
print("-" * 70)

print(
    os.path.exists(
        OUTPUT_PATH
    )
)

print(
    "Main file:",
    OUTPUT_PATH
)


print()
print("=" * 70)
print("PHASE 7.6.4 COMPLETE")
print("=" * 70)
