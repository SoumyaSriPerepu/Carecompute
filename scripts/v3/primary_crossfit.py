"""RescueNet V3: patient-grouped primary-model cross-fitting."""

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


FEATURE_EXCLUSIONS = ["patient_nbr", "encounter_id", "target_30d"]
MODEL_NAMES = ["lr", "rf", "gb"]


def build_models(X):
    numeric = X.select_dtypes(include=np.number).columns.tolist()
    categorical = [c for c in X.columns if c not in numeric]

    def preprocessor(scale_numeric=False, sparse_categorical=False):
        numeric_steps = [("imputer", SimpleImputer(strategy="median"))]

        if scale_numeric:
            numeric_steps.append(("scaler", StandardScaler()))

        return ColumnTransformer(
            transformers=[
                ("num", Pipeline(numeric_steps), numeric),
                (
                    "cat",
                    Pipeline([
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "onehot",
                            OneHotEncoder(
                                handle_unknown="ignore",
                                sparse_output=sparse_categorical,
                            ),
                        ),
                    ]),
                    categorical,
                ),
            ]
        )

    return {
        "lr": Pipeline([
            ("preprocessor", preprocessor(True, True)),
            ("classifier", LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=42,
            )),
        ]),
        "rf": Pipeline([
            ("preprocessor", preprocessor(False, False)),
            ("classifier", RandomForestClassifier(
                n_estimators=300,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )),
        ]),
        "gb": Pipeline([
            ("preprocessor", preprocessor(False, False)),
            ("classifier", HistGradientBoostingClassifier(
                learning_rate=0.05,
                max_iter=200,
                l2_regularization=1.0,
                random_state=42,
            )),
        ]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/processed/eligible/train.csv",
    )
    parser.add_argument(
        "--output",
        default="results/eligible/v3/primary_oof_raw.csv",
    )
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    df = pd.read_csv(args.input, low_memory=False)

    assert df["patient_nbr"].notna().all()
    assert df["encounter_id"].is_unique
    assert df["target_30d"].notna().all()

    X = df.drop(columns=FEATURE_EXCLUSIONS)
    y = df["target_30d"].astype(int)
    groups = df["patient_nbr"]

    splitter = StratifiedGroupKFold(
        n_splits=args.folds,
        shuffle=True,
        random_state=args.seed,
    )

    folds = list(splitter.split(X, y, groups))

    print("=== V3 PRIMARY CROSSFIT ===")
    print("Encounters:", len(df))
    print("Patients:", groups.nunique())
    print("Folds:", len(folds))

    for fold_id, (train_idx, holdout_idx) in enumerate(folds):
        train_patients = set(groups.iloc[train_idx])
        holdout_patients = set(groups.iloc[holdout_idx])
        overlap = len(train_patients & holdout_patients)

        print(
            f"Fold {fold_id}: "
            f"train={len(train_idx)}, "
            f"holdout={len(holdout_idx)}, "
            f"holdout_positives={int(y.iloc[holdout_idx].sum())}, "
            f"patient_overlap={overlap}"
        )
        assert overlap == 0

    if args.dry_run:
        print("DRY RUN PASSED. No models trained.")
        return

    probabilities = {
        name: np.full(len(df), np.nan)
        for name in MODEL_NAMES
    }
    fold_assignment = np.full(len(df), -1, dtype=int)

    for fold_id, (train_idx, holdout_idx) in enumerate(folds):
        print(f"\nTraining fold {fold_id + 1}/{len(folds)}")

        models = build_models(X.iloc[train_idx])

        for name, model in models.items():
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            probabilities[name][holdout_idx] = (
                model.predict_proba(X.iloc[holdout_idx])[:, 1]
            )
            print(f"  {name}: completed")

        fold_assignment[holdout_idx] = fold_id

    assert np.all(fold_assignment >= 0)

    for values in probabilities.values():
        assert np.isfinite(values).all()
        assert ((values >= 0) & (values <= 1)).all()

    matrix = np.column_stack([
        probabilities["lr"],
        probabilities["rf"],
        probabilities["gb"],
    ])

    output = pd.DataFrame({
        "encounter_id": df["encounter_id"],
        "patient_nbr": groups,
        "actual_30d": y,
        "cv_fold": fold_assignment,
        "lr_raw_probability": probabilities["lr"],
        "rf_raw_probability": probabilities["rf"],
        "gb_raw_probability": probabilities["gb"],
        "model_disagreement_std": matrix.std(axis=1),
        "number_diagnoses": df["number_diagnoses"],
        "number_outpatient": df["number_outpatient"],
        "number_emergency": df["number_emergency"],
    })

    destination = Path(args.output)
    if destination.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing artifact: {destination}"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(destination, index=False)

    print("\nSaved:", destination)
    print("Rows:", len(output))
    print("Patient-grouped primary OOF generation: PASS")


if __name__ == "__main__":
    main()
