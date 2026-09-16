"""Generate a synthetic ICU patient CSV so coding can start before MIMIC-IV
credentialing is approved. Schema mirrors the feature list in the project
guide (Phase 1, section 4.2). Not for reporting final results.
"""
import numpy as np
import pandas as pd

N_PATIENTS = 200
SEED = 42


def make_synthetic_cohort(n_patients: int = N_PATIENTS, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    age = rng.integers(18, 95, n_patients)

    hr_mean = rng.normal(85, 15, n_patients).clip(40, 180)
    hr_min = (hr_mean - rng.uniform(5, 25, n_patients)).clip(30, None)
    hr_max = (hr_mean + rng.uniform(5, 30, n_patients)).clip(None, 220)

    rr_mean = rng.normal(18, 4, n_patients).clip(8, 40)
    rr_min = (rr_mean - rng.uniform(2, 6, n_patients)).clip(4, None)
    rr_max = (rr_mean + rng.uniform(2, 10, n_patients)).clip(None, 50)

    spo2_mean = rng.normal(96, 3, n_patients).clip(70, 100)
    spo2_min = (spo2_mean - rng.uniform(1, 10, n_patients)).clip(60, None)
    spo2_max = np.minimum(spo2_mean + rng.uniform(0, 3, n_patients), 100)

    sbp_mean = rng.normal(115, 20, n_patients).clip(60, 200)
    sbp_min = (sbp_mean - rng.uniform(5, 25, n_patients)).clip(40, None)
    sbp_max = (sbp_mean + rng.uniform(5, 25, n_patients)).clip(None, 240)

    temp_mean = rng.normal(37.0, 0.6, n_patients).clip(34, 41)
    temp_min = temp_mean - rng.uniform(0.2, 1.0, n_patients)
    temp_max = temp_mean + rng.uniform(0.2, 1.5, n_patients)

    creatinine = rng.gamma(2.0, 0.6, n_patients).clip(0.3, 8)
    bun = rng.gamma(2.5, 8, n_patients).clip(5, 150)
    wbc = rng.normal(10, 4, n_patients).clip(0.5, 40)
    hemoglobin = rng.normal(11.5, 2.2, n_patients).clip(4, 18)
    platelets = rng.normal(220, 90, n_patients).clip(10, 600)
    glucose = rng.normal(130, 45, n_patients).clip(50, 500)
    lactate = rng.gamma(1.5, 1.0, n_patients).clip(0.3, 15)

    admission_type = rng.choice(
        ["EMERGENCY", "URGENT", "ELECTIVE"], n_patients, p=[0.6, 0.25, 0.15]
    )
    has_diabetes = rng.binomial(1, 0.3, n_patients)
    has_ckd = rng.binomial(1, 0.15, n_patients)
    has_chf = rng.binomial(1, 0.18, n_patients)
    sex = rng.choice(["F", "M"], n_patients)

    # Linear risk score built from clinically-plausible directions, then
    # squashed to a probability so the label is learnable but noisy.
    z = (
        0.03 * (age - 60)
        + 0.05 * (spo2_min < 90).astype(float) * (90 - spo2_min)
        + 0.4 * (lactate > 2).astype(float) * (lactate - 2)
        + 0.5 * (creatinine > 1.5).astype(float) * (creatinine - 1.5)
        + 0.6 * has_chf
        + 0.3 * has_ckd
        + 0.4 * (sbp_min < 80).astype(float)
        + 0.4 * (admission_type == "EMERGENCY").astype(float)
        - 2.5
    )
    prob = 1 / (1 + np.exp(-z))
    outcome = rng.binomial(1, prob)

    patient_id = [f"SYN{100000 + i}" for i in range(n_patients)]

    df = pd.DataFrame(
        {
            "patient_id": patient_id,
            "age": age,
            "sex": sex,
            "admission_type": admission_type,
            "hr_min": hr_min.round(1),
            "hr_mean": hr_mean.round(1),
            "hr_max": hr_max.round(1),
            "rr_min": rr_min.round(1),
            "rr_mean": rr_mean.round(1),
            "rr_max": rr_max.round(1),
            "spo2_min": spo2_min.round(1),
            "spo2_mean": spo2_mean.round(1),
            "spo2_max": spo2_max.round(1),
            "sbp_min": sbp_min.round(1),
            "sbp_mean": sbp_mean.round(1),
            "sbp_max": sbp_max.round(1),
            "temp_min": temp_min.round(2),
            "temp_mean": temp_mean.round(2),
            "temp_max": temp_max.round(2),
            "creatinine": creatinine.round(2),
            "bun": bun.round(1),
            "wbc": wbc.round(1),
            "hemoglobin": hemoglobin.round(1),
            "platelets": platelets.round(0),
            "glucose": glucose.round(0),
            "lactate": lactate.round(2),
            "has_diabetes": has_diabetes,
            "has_ckd": has_ckd,
            "has_chf": has_chf,
            "outcome": outcome,
        }
    )
    return df


if __name__ == "__main__":
    df = make_synthetic_cohort()
    out_path = "data/raw/synthetic_patients.csv"
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    print(f"Outcome rate: {df['outcome'].mean():.3f}")
