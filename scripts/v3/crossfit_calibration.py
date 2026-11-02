"""RescueNet V3: patient-disjoint cross-fitted isotonic calibration."""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression


INPUT = Path("results/eligible/v3/primary_oof_raw.csv")
OUTPUT = Path("results/eligible/v3/primary_oof_calibrated.csv")

if OUTPUT.exists():
    raise FileExistsError(f"Refusing to overwrite: {OUTPUT}")

df = pd.read_csv(INPUT)

required = [
    "encounter_id",
    "patient_nbr",
    "actual_30d",
    "cv_fold",
    "gb_raw_probability",
]

assert df[required].notna().all().all()
assert df["encounter_id"].is_unique

calibrated = np.full(len(df), np.nan)

print("=== RESCUENET V3 CROSSFIT CALIBRATION ===")

for fold in sorted(df["cv_fold"].unique()):
    fit_mask = df["cv_fold"] != fold
    eval_mask = df["cv_fold"] == fold

    fit_patients = set(df.loc[fit_mask, "patient_nbr"])
    eval_patients = set(df.loc[eval_mask, "patient_nbr"])

    overlap = len(fit_patients & eval_patients)
    assert overlap == 0, f"Patient leakage in fold {fold}"

    calibrator = IsotonicRegression(out_of_bounds="clip")

    calibrator.fit(
        df.loc[fit_mask, "gb_raw_probability"],
        df.loc[fit_mask, "actual_30d"],
    )

    calibrated[eval_mask.to_numpy()] = calibrator.predict(
        df.loc[eval_mask, "gb_raw_probability"]
    )

    print(
        f"Fold {fold}: "
        f"calibration_fit={fit_mask.sum()}, "
        f"heldout={eval_mask.sum()}, "
        f"patient_overlap={overlap}"
    )

assert np.isfinite(calibrated).all()
assert ((calibrated >= 0) & (calibrated <= 1)).all()

df["calibrated_probability"] = calibrated

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT, index=False)

print("\nSaved:", OUTPUT)
print("Rows:", len(df))
print("Calibration range:", calibrated.min(), calibrated.max())
print("CROSSFIT CALIBRATION: PASS")
