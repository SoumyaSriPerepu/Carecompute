"""Train the first stupid-simple baseline: logistic regression on the
synthetic (or later, real) patient cohort. If a fancier model cannot beat
this, something is wrong (Phase 2, step 2.1).
"""
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA_PATH = "data/raw/synthetic_patients.csv"
MODEL_PATH = "artifacts/risk_model.joblib"
FEATURE_LIST_PATH = "artifacts/feature_list.json"
METRICS_PATH = "results/tables/baseline_metrics.csv"

NUMERIC_FEATURES = [
    "age", "hr_min", "hr_mean", "hr_max",
    "rr_min", "rr_mean", "rr_max",
    "spo2_min", "spo2_mean", "spo2_max",
    "sbp_min", "sbp_mean", "sbp_max",
    "temp_min", "temp_mean", "temp_max",
    "creatinine", "bun", "wbc", "hemoglobin", "platelets", "glucose", "lactate",
    "has_diabetes", "has_ckd", "has_chf",
]
CATEGORICAL_FEATURES = ["sex", "admission_type"]
OUTCOME = "outcome"


def build_pipeline() -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            ("num", Pipeline([
                ("impute", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
            ]), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    # class_weight="balanced" and a modest C: the synthetic cohort is small
    # (200 rows) with a ~12% outcome rate, which otherwise pushes plain
    # unregularized LBFGS toward quasi-complete separation (overflow
    # warnings, recall collapsing to 0).
    model = LogisticRegression(
        max_iter=1000, C=0.5, class_weight="balanced", solver="liblinear"
    )
    return Pipeline([("preprocess", preprocess), ("model", model)])


def evaluate(y_true, y_prob, threshold: float = 0.5) -> dict:
    y_pred = (y_prob >= threshold).astype(int)
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fnr = fn / (fn + tp) if (fn + tp) > 0 else float("nan")
    return {
        "auroc": roc_auc_score(y_true, y_prob),
        "auprc": average_precision_score(y_true, y_prob),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "fnr": fnr,
    }


def main():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"{DATA_PATH} not found. Run `python src/data/make_synthetic_data.py` first."
        )

    df = pd.read_csv(DATA_PATH)
    features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    X = df[features]
    y = df[OUTCOME]

    # Simple 70/15/15 split; patient-level split is trivial here since one
    # row already equals one patient in the synthetic cohort.
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    val_prob = pipeline.predict_proba(X_val)[:, 1]
    test_prob = pipeline.predict_proba(X_test)[:, 1]

    val_metrics = evaluate(y_val.to_numpy(), val_prob)
    test_metrics = evaluate(y_test.to_numpy(), test_prob)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(METRICS_PATH), exist_ok=True)

    joblib.dump(pipeline, MODEL_PATH)
    with open(FEATURE_LIST_PATH, "w") as f:
        json.dump({"numeric": NUMERIC_FEATURES, "categorical": CATEGORICAL_FEATURES}, f, indent=2)

    metrics_df = pd.DataFrame(
        [
            {"model": "LogisticRegression", "split": "validation", **val_metrics},
            {"model": "LogisticRegression", "split": "test", **test_metrics},
        ]
    )
    metrics_df.to_csv(METRICS_PATH, index=False)

    print("Validation metrics:", val_metrics)
    print("Test metrics:", test_metrics)
    print(f"Saved model to {MODEL_PATH}")
    print(f"Saved feature list to {FEATURE_LIST_PATH}")
    print(f"Saved metrics to {METRICS_PATH}")

    # Sanity check requested by the guide: pass one patient row in, get a
    # risk probability out.
    one_row = X_test.iloc[[0]]
    risk = pipeline.predict_proba(one_row)[0, 1]
    print(f"Example single-patient risk probability: {risk:.4f}")


if __name__ == "__main__":
    main()
