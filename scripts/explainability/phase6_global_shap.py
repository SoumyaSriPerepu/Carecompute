import pandas as pd
import numpy as np
import joblib
import shap
import os


# =====================================================
# SETTINGS
# =====================================================

SAMPLE_SIZE = 500
RANDOM_STATE = 42


# =====================================================
# 1. LOAD MODEL
# =====================================================

model = joblib.load(
    "src/models/saved/eligible/"
    "gradient_boosting.joblib"
)

preprocessor = model.named_steps[
    "preprocessor"
]

classifier = model.named_steps[
    "classifier"
]


# =====================================================
# 2. LOAD TEST DATA
# =====================================================

test = pd.read_csv(
    "data/processed/eligible/test.csv",
    low_memory=False
)

X_test = test.drop(
    columns=[
        "patient_nbr",
        "encounter_id",
        "target_30d"
    ]
)


print(
    "Total test encounters:",
    len(X_test)
)


# =====================================================
# 3. SAMPLE 500 PATIENT ENCOUNTERS
# =====================================================

sample_size = min(
    SAMPLE_SIZE,
    len(X_test)
)

X_sample = X_test.sample(
    n=sample_size,
    random_state=RANDOM_STATE
)


print(
    "SHAP sample size:",
    len(X_sample)
)


# =====================================================
# 4. TRANSFORM FEATURES
# =====================================================

X_transformed = (
    preprocessor.transform(
        X_sample
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


# =====================================================
# 5. SHAP EXPLAINER
# =====================================================

explainer = shap.Explainer(
    classifier
)

shap_values = explainer(
    X_transformed
)


print(
    "SHAP shape:",
    shap_values.values.shape
)


# =====================================================
# 6. GLOBAL IMPORTANCE
# =====================================================

mean_abs_shap = np.mean(
    np.abs(
        shap_values.values
    ),
    axis=0
)


global_importance = pd.DataFrame({
    "feature":
        feature_names,

    "mean_absolute_shap":
        mean_abs_shap
})


# =====================================================
# 7. CLEAN FEATURE NAMES
# =====================================================

global_importance[
    "feature"
] = (
    global_importance[
        "feature"
    ]
    .str.replace(
        "num__",
        "",
        regex=False
    )
    .str.replace(
        "cat__",
        "",
        regex=False
    )
)


# =====================================================
# 8. SORT
# =====================================================

global_importance = (
    global_importance
    .sort_values(
        "mean_absolute_shap",
        ascending=False
    )
    .reset_index(
        drop=True
    )
)


global_importance.insert(
    0,
    "rank",
    range(
        1,
        len(global_importance) + 1
    )
)


# =====================================================
# 9. PRINT TOP 20
# =====================================================

print()
print("GLOBAL SHAP — TOP 20")
print("-------------------------")

print(
    global_importance
    .head(20)
    .to_string(
        index=False
    )
)


# =====================================================
# 10. SAVE
# =====================================================

output_dir = (
    "results/eligible/explanations"
)

os.makedirs(
    output_dir,
    exist_ok=True
)

output_path = (
    f"{output_dir}/"
    "global_shap_importance.csv"
)

global_importance.to_csv(
    output_path,
    index=False
)


print()
print(
    "Saved:",
    os.path.exists(
        output_path
    )
)

print(
    "File:",
    output_path
)

