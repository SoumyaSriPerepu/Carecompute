# CARE-Compute

Safety-Constrained Adaptive Compute for Healthcare AI Agents on Google Cloud.

**Research question:** Can healthcare AI learn when it needs to "think" more,
so that compute, latency, tokens, and cost are reduced without hurting safety
or prediction quality?

**Clinical task (v1):** From data available during the first 24 hours of an
ICU stay, predict whether a patient will experience clinical deterioration
(operationalized as 48-hour/in-hospital mortality) during the next 24 hours.

> **This is a research prototype. It is not for real clinical decision-making.**

## Pipeline

```
Patient health data
        |
Prediction model -> risk + uncertainty
        |
Manager/Router decides how much AI work is needed
        |
Run only the needed agents -> final result + compute log
```

## Project layout

```
care-compute/
├── data/
│   ├── raw/          # source data (synthetic fallback +, later, approved MIMIC-IV extracts)
│   ├── interim/       # intermediate cleaning steps
│   └── processed/     # final train/val/test tables
├── notebooks/
├── src/
│   ├── data/          # cohort building, patient-level splitting
│   ├── models/        # baseline training, calibration, uncertainty
│   ├── agents/         # prediction / evidence / explanation / verifier agents
│   ├── router/          # static rule router + learned router
│   ├── evaluation/     # final test run, bootstrap CIs, fairness, ablations
│   └── cloud/          # FastAPI service + structured logging for GCP
├── configs/            # split seeds, experiment configs
├── artifacts/          # frozen models, feature lists (gitignored)
├── results/
│   ├── tables/
│   ├── figures/
│   └── logs/
├── tests/
├── requirements.txt
└── README.md
```

## Data

Final dataset target: **MIMIC-IV** (restricted; requires PhysioNet
credentialing, CITI training, and a signed data-use agreement). Real MIMIC
data must never be committed to this repository — see `.gitignore`.

While credentialing is pending, development uses a synthetic patient CSV with
the same schema. Generate it with:

```bash
python src/data/make_synthetic_data.py
```

This writes `data/raw/synthetic_patients.csv` (200 rows) with the feature set
described in `PROJECT_LOG.md` and the project guide, plus a binary `outcome`
column. All reported final results must come from the approved real dataset,
not the synthetic fallback.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
pip install -r requirements.txt
python -c "import pandas, sklearn"   # should run with no error
```

## Baseline model

Train a first logistic-regression baseline on the synthetic data:

```bash
python src/models/train_baseline.py
```

Metrics are written to `results/tables/baseline_metrics.csv` and the frozen
model to `artifacts/risk_model.joblib`.

## Status

See `PROJECT_LOG.md` for the running build log and next steps, and the
project guide for the full 10-phase plan (baselines, agents, static/learned
routing, GCP deployment, safety/fairness testing, ablations).
