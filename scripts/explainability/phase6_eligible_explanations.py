import pandas as pd
import numpy as np
import joblib
import shap
import json
import os


# =========================================================
# 1. LOAD MODEL AND CALIBRATOR
# =========================================================

model = joblib.load(
    "src/models/saved/eligible/gradient_boosting.joblib"
)

calibrator = joblib.load(
    "src/models/saved/eligible/isotonic_calibrator.joblib"
)


# =========================================================
# 2. LOAD TEST DATA
# =========================================================

test = pd.read_csv(
    "data/processed/eligible/test.csv"
)

X_test = test.drop(
    columns=[
        "patient_nbr",
        "encounter_id",
        "target_30d"
    ]
)

y_test = test["target_30d"]


# =========================================================
# 3. GET MODEL PARTS
# =========================================================

preprocessor = model.named_steps["preprocessor"]
classifier = model.named_steps["classifier"]


# =========================================================
# 4. SELECT 20 CASES
# =========================================================

X_explain = X_test.iloc[:20].copy()

X_transformed = preprocessor.transform(
    X_explain
)

feature_names = preprocessor.get_feature_names_out()


# =========================================================
# 5. COMPUTE SHAP
# =========================================================

explainer = shap.TreeExplainer(
    classifier
)

shap_values = explainer.shap_values(
    X_transformed
)


# =========================================================
# 6. CLEAN FEATURE NAMES
# =========================================================

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


# =========================================================
# 7. CHECK WHETHER TRANSFORMED FEATURE IS ACTIVE
# =========================================================

def is_active_feature(
    feature_index,
    transformed_row
):

    name = feature_names[
        feature_index
    ]

    value = transformed_row[
        feature_index
    ]

    # Numeric features are always retained.
    if name.startswith("num__"):
        return True

    # One-hot categorical feature:
    # only retain the category actually present.
    if name.startswith("cat__"):
        return value > 0.5

    return True


# =========================================================
# 8. BUILD EXPLANATIONS
# =========================================================

explanations = []

for i in range(20):

    patient_shap = np.asarray(
        shap_values[i]
    ).flatten()

    transformed_row = np.asarray(
        X_transformed[i]
    ).flatten()

    explanation_df = pd.DataFrame({
        "feature": feature_names,
        "shap_value": patient_shap,
        "transformed_value": transformed_row,
        "feature_index": np.arange(
            len(feature_names)
        )
    })

    explanation_df["active"] = [
        is_active_feature(
            int(index),
            transformed_row
        )
        for index in explanation_df[
            "feature_index"
        ]
    ]

    # IMPORTANT:
    # Only active categorical features
    # and numeric features remain.
    active_df = explanation_df[
        explanation_df["active"]
    ].copy()

    positive = (
        active_df[
            active_df["shap_value"] > 0
        ]
        .sort_values(
            "shap_value",
            ascending=False
        )
        .head(5)
    )

    negative = (
        active_df[
            active_df["shap_value"] < 0
        ]
        .sort_values(
            "shap_value",
            ascending=True
        )
        .head(5)
    )

    raw_prob = model.predict_proba(
        X_explain.iloc[[i]]
    )[0, 1]

    cal_prob = calibrator.predict(
        [raw_prob]
    )[0]

    uncertainty = (
        1 - abs(
            2 * cal_prob - 1
        )
    )

    positive_list = [
        [
            clean_feature_name(
                row["feature"]
            ),
            float(
                row["shap_value"]
            )
        ]
        for _, row
        in positive.iterrows()
    ]

    negative_list = [
        [
            clean_feature_name(
                row["feature"]
            ),
            float(
                row["shap_value"]
            )
        ]
        for _, row
        in negative.iterrows()
    ]

    explanation = {

        "encounter_id": int(
            test.iloc[i][
                "encounter_id"
            ]
        ),

        "actual_30d": int(
            y_test.iloc[i]
        ),

        "risk": float(
            cal_prob
        ),

        "uncertainty": float(
            uncertainty
        ),

        "top_risk_factors":
            positive_list,

        "top_protective_factors":
            negative_list
    }

    explanations.append(
        explanation
    )


# =========================================================
# 9. SAVE JSON
# =========================================================

os.makedirs(
    "results/eligible/explanations",
    exist_ok=True
)

output_path = (
    "results/eligible/explanations/"
    "shap_explanations_20.json"
)

with open(
    output_path,
    "w"
) as f:

    json.dump(
        explanations,
        f,
        indent=2
    )


# =========================================================
# 10. CHECK PATIENT #1
# =========================================================

print()
print("PHASE 6 CHECK")
print("-------------------------")

print(
    "Number of explanations:",
    len(explanations)
)

print(
    "SHAP shape:",
    np.asarray(
        shap_values
    ).shape
)

print(
    "File saved:",
    os.path.exists(
        output_path
    )
)

print()
print(
    "PATIENT 1 ACTUAL VALUES"
)
print("-------------------------")

columns_to_check = [
    "age",
    "race",
    "gender",
    "number_inpatient",
    "number_diagnoses",
    "discharge_disposition_id",
    "admission_source_id",
    "medical_specialty",
    "diabetesMed"
]

print(
    test.iloc[0][
        columns_to_check
    ]
)

print()
print(
    "PATIENT 1 FILTERED EXPLANATION"
)
print("-------------------------")

print(
    json.dumps(
        explanations[0],
        indent=2
    )
)
