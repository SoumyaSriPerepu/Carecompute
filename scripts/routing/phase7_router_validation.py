import pandas as pd
import numpy as np
import joblib
import os


# ============================================================
# PHASE 7.6.1 — CREATE VALIDATION ROUTER DATASET
# ============================================================

print("=" * 70)
print("PHASE 7.6.1 — VALIDATION ROUTER DATASET")
print("=" * 70)


# ------------------------------------------------------------
# 1. SETTINGS
# ------------------------------------------------------------

VALIDATION_PATH = "data/processed/eligible/validation.csv"

MODEL_DIR = "src/models/saved/eligible"

CALIBRATOR_PATH = (
    MODEL_DIR + "/isotonic_calibrator.joblib"
)

OUTPUT_PATH = (
    "results/eligible/router_validation.csv"
)

LOCKED_THRESHOLD = 0.115


# ------------------------------------------------------------
# 2. LOAD VALIDATION DATA
# ------------------------------------------------------------

val = pd.read_csv(
    VALIDATION_PATH,
    low_memory=False
)

print()
print("Validation encounters:", len(val))
print("Positive rate:", val["target_30d"].mean())


# ------------------------------------------------------------
# 3. CREATE MODEL FEATURES
# ------------------------------------------------------------

drop_columns = [
    "patient_nbr",
    "encounter_id",
    "target_30d"
]

X_val = val.drop(
    columns=drop_columns
)

y_val = val["target_30d"].astype(int)


# ------------------------------------------------------------
# 4. LOAD MODELS
# ------------------------------------------------------------

logistic_model = joblib.load(
    MODEL_DIR + "/logistic_regression.joblib"
)

random_forest_model = joblib.load(
    MODEL_DIR + "/random_forest.joblib"
)

gradient_model = joblib.load(
    MODEL_DIR + "/gradient_boosting.joblib"
)

calibrator = joblib.load(
    CALIBRATOR_PATH
)

print("Models loaded: PASSED")


# ------------------------------------------------------------
# 5. GET MODEL PROBABILITIES
# ------------------------------------------------------------

print()
print("Generating probabilities...")


lr_prob = logistic_model.predict_proba(
    X_val
)[:, 1]

rf_prob = random_forest_model.predict_proba(
    X_val
)[:, 1]

gb_raw_prob = gradient_model.predict_proba(
    X_val
)[:, 1]


# ------------------------------------------------------------
# 6. CALIBRATE LOCKED GB MODEL
# ------------------------------------------------------------

gb_cal_prob = calibrator.predict(
    gb_raw_prob
)


# ------------------------------------------------------------
# 7. LOCKED GB PREDICTION
# ------------------------------------------------------------

predicted_30d = (
    gb_cal_prob >= LOCKED_THRESHOLD
).astype(int)


# ------------------------------------------------------------
# 8. ORIGINAL UNCERTAINTY
# ------------------------------------------------------------

probability_uncertainty = (
    1 - np.abs(
        2 * gb_cal_prob - 1
    )
)


# ------------------------------------------------------------
# 9. DECISION BOUNDARY DISTANCE
# ------------------------------------------------------------

boundary_distance = np.abs(
    gb_cal_prob - LOCKED_THRESHOLD
)


# Convert distance into an uncertainty-style score.
# Larger = closer to decision boundary.

boundary_uncertainty = (
    1 / (1 + boundary_distance)
)


# ------------------------------------------------------------
# 10. MODEL DISAGREEMENT
# ------------------------------------------------------------

probability_matrix = np.column_stack(
    [
        lr_prob,
        rf_prob,
        gb_raw_prob
    ]
)

model_disagreement_std = np.std(
    probability_matrix,
    axis=1
)

model_disagreement_range = (
    np.max(probability_matrix, axis=1)
    -
    np.min(probability_matrix, axis=1)
)


# ------------------------------------------------------------
# 11. CREATE ROUTER TABLE
# ------------------------------------------------------------

router = pd.DataFrame({

    "encounter_id":
        val["encounter_id"].values,

    "patient_nbr":
        val["patient_nbr"].values,

    "actual_30d":
        y_val.values,

    "predicted_30d":
        predicted_30d,

    "calibrated_probability":
        gb_cal_prob,

    "raw_probability":
        gb_raw_prob,

    "probability_uncertainty":
        probability_uncertainty,

    "boundary_distance":
        boundary_distance,

    "boundary_uncertainty":
        boundary_uncertainty,

    "model_disagreement_std":
        model_disagreement_std,

    "model_disagreement_range":
        model_disagreement_range,

    # Useful patient-history / clinical signals

    "number_inpatient":
        val["number_inpatient"].values,

    "number_emergency":
        val["number_emergency"].values,

    "number_outpatient":
        val["number_outpatient"].values,

    "number_diagnoses":
        val["number_diagnoses"].values,

    "time_in_hospital":
        val["time_in_hospital"].values,

    "age":
        val["age"].values,

    "gender":
        val["gender"].values,

    "race":
        val["race"].values
})


# ------------------------------------------------------------
# 12. CASE TYPE
# ------------------------------------------------------------

def get_case_type(row):

    actual = int(row["actual_30d"])
    predicted = int(row["predicted_30d"])

    if actual == 1 and predicted == 1:
        return "TP"

    if actual == 0 and predicted == 0:
        return "TN"

    if actual == 0 and predicted == 1:
        return "FP"

    return "FN"


router["case_type"] = router.apply(
    get_case_type,
    axis=1
)


# ------------------------------------------------------------
# 13. BASIC CHECKS
# ------------------------------------------------------------

print()
print("CASE COUNTS")
print("-------------------------")

print(
    router["case_type"].value_counts()
)


print()
print("ROUTER SIGNAL SUMMARY")
print("-------------------------")

print(
    router[
        [
            "calibrated_probability",
            "probability_uncertainty",
            "boundary_distance",
            "model_disagreement_std",
            "number_inpatient",
            "number_emergency"
        ]
    ].describe()
)


# ------------------------------------------------------------
# 14. FALSE NEGATIVE CHECK
# ------------------------------------------------------------

fn = router[
    router["case_type"] == "FN"
]

print()
print("FALSE NEGATIVES:", len(fn))

print()
print("FALSE NEGATIVE SIGNAL MEANS")
print("-------------------------")

print(
    fn[
        [
            "calibrated_probability",
            "boundary_distance",
            "model_disagreement_std",
            "number_inpatient",
            "number_emergency",
            "number_diagnoses"
        ]
    ].mean()
)


# ------------------------------------------------------------
# 15. SAVE
# ------------------------------------------------------------

os.makedirs(
    "results/eligible",
    exist_ok=True
)

router.to_csv(
    OUTPUT_PATH,
    index=False
)


print()
print("FILE SAVED")
print("-------------------------")

print(
    os.path.exists(
        OUTPUT_PATH
    )
)

print("File:", OUTPUT_PATH)


print()
print("=" * 70)
print("PHASE 7.6.1 COMPLETE")
print("=" * 70)
