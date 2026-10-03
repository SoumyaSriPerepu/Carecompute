import pandas as pd
import numpy as np
import joblib
import os

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import (
    RandomForestClassifier,
    HistGradientBoostingClassifier
)

from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    recall_score,
    precision_score,
    f1_score,
    confusion_matrix,
    brier_score_loss
)


# =====================================================
# 1. LOAD ELIGIBLE SPLITS
# =====================================================

train = pd.read_csv(
    "data/processed/eligible/train.csv",
    low_memory=False
)

val = pd.read_csv(
    "data/processed/eligible/validation.csv",
    low_memory=False
)


# =====================================================
# 2. TARGET AND FEATURES
# =====================================================

y_train = train["target_30d"]
y_val = val["target_30d"]

drop_columns = [
    "patient_nbr",
    "encounter_id",
    "target_30d"
]

X_train = train.drop(
    columns=drop_columns
)

X_val = val.drop(
    columns=drop_columns
)


# =====================================================
# 3. IDENTIFY COLUMN TYPES
# =====================================================

numeric_columns = (
    X_train
    .select_dtypes(include=np.number)
    .columns
    .tolist()
)

categorical_columns = [
    column
    for column in X_train.columns
    if column not in numeric_columns
]

print("Numeric columns:", len(numeric_columns))
print("Categorical columns:", len(categorical_columns))


# =====================================================
# 4. LOGISTIC PREPROCESSOR
# =====================================================

lr_numeric = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(strategy="median")
        ),
        (
            "scaler",
            StandardScaler()
        )
    ]
)

categorical = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(
                strategy="most_frequent"
            )
        ),
        (
            "onehot",
            OneHotEncoder(
                handle_unknown="ignore"
            )
        )
    ]
)

lr_preprocessor = ColumnTransformer(
    transformers=[
        (
            "num",
            lr_numeric,
            numeric_columns
        ),
        (
            "cat",
            categorical,
            categorical_columns
        )
    ]
)


# =====================================================
# 5. TREE PREPROCESSOR
# =====================================================

tree_numeric = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(strategy="median")
        )
    ]
)

tree_categorical = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(
                strategy="most_frequent"
            )
        ),
        (
            "onehot",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False
            )
        )
    ]
)

tree_preprocessor = ColumnTransformer(
    transformers=[
        (
            "num",
            tree_numeric,
            numeric_columns
        ),
        (
            "cat",
            tree_categorical,
            categorical_columns
        )
    ]
)


# =====================================================
# 6. MODELS
# =====================================================

logistic_model = Pipeline(
    steps=[
        (
            "preprocessor",
            lr_preprocessor
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=42
            )
        )
    ]
)

random_forest_model = Pipeline(
    steps=[
        (
            "preprocessor",
            tree_preprocessor
        ),
        (
            "classifier",
            RandomForestClassifier(
                n_estimators=300,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1
            )
        )
    ]
)

gradient_boosting_model = Pipeline(
    steps=[
        (
            "preprocessor",
            tree_preprocessor
        ),
        (
            "classifier",
            HistGradientBoostingClassifier(
                learning_rate=0.05,
                max_iter=200,
                l2_regularization=1.0,
                random_state=42
            )
        )
    ]
)


models = {
    "Logistic Regression":
        logistic_model,

    "Random Forest":
        random_forest_model,

    "Gradient Boosting":
        gradient_boosting_model
}


# =====================================================
# 7. TRAIN + EVALUATE
# =====================================================

results = []

os.makedirs(
    "src/models/saved/eligible",
    exist_ok=True
)

os.makedirs(
    "results/eligible",
    exist_ok=True
)


for name, model in models.items():

    print()
    print("=" * 50)
    print("TRAINING:", name)
    print("=" * 50)

    model.fit(
        X_train,
        y_train
    )

    probability = model.predict_proba(
        X_val
    )[:, 1]

    prediction = (
        probability >= 0.5
    ).astype(int)

    auroc = roc_auc_score(
        y_val,
        probability
    )

    auprc = average_precision_score(
        y_val,
        probability
    )

    recall = recall_score(
        y_val,
        prediction
    )

    precision = precision_score(
        y_val,
        prediction
    )

    f1 = f1_score(
        y_val,
        prediction
    )

    brier = brier_score_loss(
        y_val,
        probability
    )

    cm = confusion_matrix(
        y_val,
        prediction
    )

    tn, fp, fn, tp = cm.ravel()

    fnr = fn / (fn + tp)

    print("AUROC:", auroc)
    print("AUPRC:", auprc)
    print("Recall:", recall)
    print("Precision:", precision)
    print("F1:", f1)
    print("False Negative Rate:", fnr)
    print("Brier:", brier)

    results.append({
        "Model": name,
        "AUROC": auroc,
        "AUPRC": auprc,
        "Recall": recall,
        "Precision": precision,
        "F1": f1,
        "FNR": fnr,
        "Brier": brier
    })

    filename = (
        name
        .lower()
        .replace(" ", "_")
    )

    joblib.dump(
        model,
        f"src/models/saved/eligible/"
        f"{filename}.joblib"
    )


# =====================================================
# 8. MODEL COMPARISON
# =====================================================

results_df = pd.DataFrame(
    results
)

print()
print("=" * 50)
print("EXPERIMENT B MODEL COMPARISON")
print("=" * 50)

print(
    results_df.to_string(
        index=False
    )
)

results_df.to_csv(
    "results/eligible/"
    "model_comparison.csv",
    index=False
)

print()
print(
    "Saved model comparison:",
    os.path.exists(
        "results/eligible/"
        "model_comparison.csv"
    )
)
