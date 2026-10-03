import pandas as pd
import numpy as np
import joblib
import shap
import json
import os


# ============================================================
# PHASE 6 — BALANCED SHAP EXPLANATION AUDIT
#
# Goal:
# Explain exactly 20 deliberately selected test cases:
#
# 5 True Positives
# 5 True Negatives
# 5 False Positives
# 5 False Negatives
# ============================================================


# ============================================================
# 1. SETTINGS
# ============================================================

MODEL_PATH = (
    "src/models/saved/eligible/"
    "gradient_boosting.joblib"
)

CALIBRATOR_PATH = (
    "src/models/saved/eligible/"
    "isotonic_calibrator.joblib"
)

TEST_PATH = (
    "data/processed/eligible/test.csv"
)

AUDIT_PATH = (
    "results/eligible/explanations/"
    "balanced_audit_20.csv"
)

OUTPUT_DIR = (
    "results/eligible/explanations"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    + "/balanced_shap_explanations_20.json"
)

THRESHOLD = 0.115


# ============================================================
# 2. LOAD MODEL AND CALIBRATOR
# ============================================================

print()
print("Loading model and calibrator...")

model = joblib.load(
    MODEL_PATH
)

calibrator = joblib.load(
    CALIBRATOR_PATH
)

print(
    "Model type:",
    type(model)
)

print(
    "Calibrator type:",
    type(calibrator)
)


# ============================================================
# 3. GET PREPROCESSOR AND CLASSIFIER
# ============================================================

preprocessor = model.named_steps[
    "preprocessor"
]

classifier = model.named_steps[
    "classifier"
]


# ============================================================
# 4. LOAD ELIGIBLE TEST DATA
# ============================================================

test = pd.read_csv(
    TEST_PATH,
    low_memory=False
)

print()
print(
    "Eligible test encounters:",
    len(test)
)


# ============================================================
# 5. LOAD BALANCED AUDIT CASES
# ============================================================

balanced_audit = pd.read_csv(
    AUDIT_PATH,
    low_memory=False
)

print(
    "Balanced audit rows:",
    len(balanced_audit)
)


# ============================================================
# 6. SAFETY CHECK — EXACTLY 20 CASES
# ============================================================

if len(balanced_audit) != 20:

    raise ValueError(
        "Balanced audit should contain exactly 20 cases."
    )


# ============================================================
# 7. CHECK CASE-TYPE COUNTS
# ============================================================

case_counts = (
    balanced_audit[
        "case_type"
    ]
    .value_counts()
)

print()
print("BALANCED AUDIT COUNTS")
print("-------------------------")

print(case_counts)


for case_type in [
    "TP",
    "TN",
    "FP",
    "FN"
]:

    count = (
        case_counts.get(
            case_type,
            0
        )
    )

    if count != 5:

        raise ValueError(
            f"{case_type} should have 5 cases, "
            f"but found {count}."
        )


# ============================================================
# 8. GET AUDIT ENCOUNTER IDS
# ============================================================

audit_ids = (
    balanced_audit[
        "encounter_id"
    ]
    .tolist()
)


# ============================================================
# 9. SELECT EXACT SAME CASES FROM TEST DATA
# ============================================================

test_indexed = test.set_index(
    "encounter_id",
    drop=False
)


missing_ids = [
    encounter_id
    for encounter_id in audit_ids
    if encounter_id
    not in test_indexed.index
]


if len(missing_ids) > 0:

    raise ValueError(
        "Some audit encounters were not "
        "found in the eligible test set: "
        f"{missing_ids}"
    )


selected_test = (
    test_indexed
    .loc[audit_ids]
    .reset_index(
        drop=True
    )
)


print()
print(
    "Balanced cases loaded:",
    len(selected_test)
)


# ============================================================
# 10. VERIFY ORDER
# ============================================================

selected_ids = (
    selected_test[
        "encounter_id"
    ]
    .tolist()
)

if selected_ids != audit_ids:

    raise ValueError(
        "Encounter order does not match "
        "balanced audit order."
    )


print(
    "Encounter order check: PASSED"
)


# ============================================================
# 11. CREATE MODEL INPUT
# ============================================================

drop_columns = [
    "patient_nbr",
    "encounter_id",
    "target_30d"
]


X_explain = (
    selected_test
    .drop(
        columns=drop_columns
    )
    .copy()
)

y_explain = (
    selected_test[
        "target_30d"
    ]
    .copy()
)


print(
    "X_explain shape:",
    X_explain.shape
)


# ============================================================
# 12. TRANSFORM FEATURES
# ============================================================

X_transformed = (
    preprocessor.transform(
        X_explain
    )
)

feature_names = (
    preprocessor
    .get_feature_names_out()
)


print(
    "Transformed shape:",
    X_transformed.shape
)

print(
    "Feature names:",
    len(feature_names)
)


if (
    X_transformed.shape[1]
    != len(feature_names)
):

    raise ValueError(
        "Number of transformed columns "
        "does not match feature names."
    )


# ============================================================
# 13. CREATE SHAP EXPLAINER
# ============================================================

print()
print(
    "Calculating SHAP values..."
)

explainer = shap.Explainer(
    classifier
)

shap_result = explainer(
    X_transformed
)

shap_values = (
    shap_result.values
)


print(
    "SHAP shape:",
    shap_values.shape
)


# ============================================================
# 14. CLEAN FEATURE NAME
# ============================================================

def clean_feature_name(name):

    name = name.replace(
        "num__",
        ""
    )

    name = name.replace(
        "cat__",
        ""
    )

    return name


# ============================================================
# 15. IDENTIFY ORIGINAL CATEGORICAL COLUMNS
# ============================================================

categorical_columns = (
    X_explain
    .select_dtypes(
        exclude=np.number
    )
    .columns
    .tolist()
)


# Some numeric-looking columns were intentionally treated
# as categorical by the model preprocessing.
#
# We recover the actual categorical columns directly from
# the fitted ColumnTransformer where possible.

try:

    cat_transformer_info = [
        transformer
        for transformer in preprocessor.transformers_
        if transformer[0] == "cat"
    ]

    if len(cat_transformer_info) > 0:

        categorical_columns = list(
            cat_transformer_info[0][2]
        )

except Exception:

    pass


# Sort longest names first.
# This prevents a short column name from incorrectly
# matching part of a longer feature name.

categorical_columns = sorted(
    categorical_columns,
    key=len,
    reverse=True
)


# ============================================================
# 16. CHECK WHETHER A TRANSFORMED FEATURE IS ACTIVE
# ============================================================

def is_active_feature(
    transformed_feature_name,
    patient_row
):

    clean_name = clean_feature_name(
        transformed_feature_name
    )

    # ----------------------------------------
    # NUMERIC FEATURE
    # ----------------------------------------

    if transformed_feature_name.startswith(
        "num__"
    ):

        return True


    # ----------------------------------------
    # CATEGORICAL / ONE-HOT FEATURE
    # ----------------------------------------

    if transformed_feature_name.startswith(
        "cat__"
    ):

        for column in categorical_columns:

            prefix = column + "_"

            if clean_name.startswith(
                prefix
            ):

                category = clean_name[
                    len(prefix):
                ]

                actual_value = (
                    patient_row.get(
                        column,
                        np.nan
                    )
                )

                # Missing values may have been
                # imputed during preprocessing.

                if pd.isna(actual_value):

                    return False

                return (
                    str(actual_value)
                    == str(category)
                )

        # If we cannot safely map the encoded
        # feature back to an original column,
        # don't present it as an active patient
        # characteristic.

        return False


    return True


# ============================================================
# 17. GENERATE RAW + CALIBRATED PROBABILITIES
# ============================================================

raw_probabilities = (
    model.predict_proba(
        X_explain
    )[:, 1]
)

calibrated_probabilities = (
    calibrator.predict(
        raw_probabilities
    )
)

uncertainties = (
    1
    - np.abs(
        2
        * calibrated_probabilities
        - 1
    )
)

predicted_classes = (
    calibrated_probabilities
    >= THRESHOLD
).astype(int)


# ============================================================
# 18. BUILD EXPLANATIONS
# ============================================================

explanations = []


for i in range(
    len(selected_test)
):

    patient_row = (
        X_explain
        .iloc[i]
    )

    patient_shap = (
        shap_values[i]
    )


    explanation_df = pd.DataFrame(
        {
            "feature":
                feature_names,

            "shap_value":
                patient_shap
        }
    )


    # ========================================================
    # KEEP ONLY FEATURES THAT ARE ACTIVE FOR THIS PATIENT
    # ========================================================

    active_mask = []

    for feature in (
        explanation_df[
            "feature"
        ]
    ):

        active_mask.append(
            is_active_feature(
                feature,
                patient_row
            )
        )


    active_df = (
        explanation_df[
            active_mask
        ]
        .copy()
    )


    # ========================================================
    # CLEAN FEATURE NAMES
    # ========================================================

    active_df[
        "feature"
    ] = (
        active_df[
            "feature"
        ]
        .apply(
            clean_feature_name
        )
    )


    # ========================================================
    # TOP POSITIVE SHAP FACTORS
    # ========================================================

    positive_df = (
        active_df[
            active_df[
                "shap_value"
            ] > 0
        ]
        .sort_values(
            "shap_value",
            ascending=False
        )
        .head(5)
    )


    # ========================================================
    # TOP NEGATIVE SHAP FACTORS
    # ========================================================

    negative_df = (
        active_df[
            active_df[
                "shap_value"
            ] < 0
        ]
        .sort_values(
            "shap_value",
            ascending=True
        )
        .head(5)
    )


    # ========================================================
    # CONVERT TO JSON-FRIENDLY LISTS
    # ========================================================

    top_risk_factors = []

    for _, row in (
        positive_df.iterrows()
    ):

        top_risk_factors.append(
            [
                str(
                    row[
                        "feature"
                    ]
                ),
                float(
                    row[
                        "shap_value"
                    ]
                )
            ]
        )


    top_protective_factors = []

    for _, row in (
        negative_df.iterrows()
    ):

        top_protective_factors.append(
            [
                str(
                    row[
                        "feature"
                    ]
                ),
                float(
                    row[
                        "shap_value"
                    ]
                )
            ]
        )


    # ========================================================
    # CASE INFORMATION
    # ========================================================

    encounter_id = int(
        selected_test
        .iloc[i][
            "encounter_id"
        ]
    )

    actual = int(
        y_explain.iloc[i]
    )

    predicted = int(
        predicted_classes[i]
    )

    case_type = str(
        balanced_audit
        .iloc[i][
            "case_type"
        ]
    )


    # ========================================================
    # VERIFY CASE TYPE
    # ========================================================

    if (
        actual == 1
        and predicted == 1
    ):

        calculated_case_type = "TP"

    elif (
        actual == 0
        and predicted == 0
    ):

        calculated_case_type = "TN"

    elif (
        actual == 0
        and predicted == 1
    ):

        calculated_case_type = "FP"

    else:

        calculated_case_type = "FN"


    if (
        calculated_case_type
        != case_type
    ):

        raise ValueError(
            f"Case type mismatch for "
            f"encounter {encounter_id}: "
            f"audit says {case_type}, "
            f"calculated {calculated_case_type}"
        )


    # ========================================================
    # FINAL STRUCTURED EXPLANATION
    # ========================================================

    explanation = {

        "audit_case":
            int(
                balanced_audit
                .iloc[i][
                    "audit_case"
                ]
            ),

        "encounter_id":
            encounter_id,

        "case_type":
            case_type,

        "actual_30d":
            actual,

        "predicted_30d":
            predicted,

        "threshold":
            float(
                THRESHOLD
            ),

        "raw_probability":
            float(
                raw_probabilities[i]
            ),

        "risk":
            float(
                calibrated_probabilities[i]
            ),

        "uncertainty":
            float(
                uncertainties[i]
            ),

        "top_risk_factors":
            top_risk_factors,

        "top_protective_factors":
            top_protective_factors
    }


    explanations.append(
        explanation
    )


# ============================================================
# 19. SAVE JSON
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


with open(
    OUTPUT_PATH,
    "w"
) as file:

    json.dump(
        explanations,
        file,
        indent=2
    )


# ============================================================
# 20. FINAL PHASE 6 CHECKS
# ============================================================

print()
print("=" * 60)

print(
    "PHASE 6 BALANCED EXPLANATION CHECK"
)

print("=" * 60)

print(
    "Number of explanations:",
    len(explanations)
)

print(
    "SHAP shape:",
    shap_values.shape
)

print(
    "File saved:",
    os.path.exists(
        OUTPUT_PATH
    )
)


# ============================================================
# 21. COUNT EXPLANATION TYPES
# ============================================================

explanation_case_counts = (
    pd.Series(
        [
            item[
                "case_type"
            ]
            for item
            in explanations
        ]
    )
    .value_counts()
)


print()
print("EXPLANATION CASE COUNTS")
print("-------------------------")

print(
    explanation_case_counts
)


# ============================================================
# 22. VERIFY EXACT 5/5/5/5
# ============================================================

for case_type in [
    "TP",
    "TN",
    "FP",
    "FN"
]:

    count = (
        explanation_case_counts
        .get(
            case_type,
            0
        )
    )

    if count != 5:

        raise ValueError(
            f"Final explanations contain "
            f"{count} {case_type} cases "
            "instead of 5."
        )


# ============================================================
# 23. CHECK FOR EXPIRED CATEGORY
# ============================================================

with open(
    OUTPUT_PATH,
    "r"
) as file:

    saved_text = file.read()


expired_feature_count = (
    saved_text.count(
        "discharge_disposition_id_11"
    )
)


print()
print(
    "Expired feature count:",
    expired_feature_count
)


if expired_feature_count != 0:

    raise ValueError(
        "Expired discharge category "
        "appeared in eligible explanations."
    )


# ============================================================
# 24. PRINT FIRST EXPLANATION
# ============================================================

print()
print("FIRST BALANCED EXPLANATION")
print("-------------------------")

print(
    json.dumps(
        explanations[0],
        indent=2
    )
)


# ============================================================
# 25. FINAL SUCCESS MESSAGE
# ============================================================

print()
print("=" * 60)

print(
    "BALANCED SHAP AUDIT COMPLETE"
)

print("=" * 60)

print(
    "20 explanations: PASSED"
)

print(
    "5 TP / 5 TN / 5 FP / 5 FN: PASSED"
)

print(
    "Expired category absent: PASSED"
)

print(
    "Output:",
    OUTPUT_PATH
)
