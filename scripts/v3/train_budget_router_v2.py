"""RescueNet V3 exploratory ranking-aware neural router."""

from pathlib import Path
import json
import random

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from torch import nn

BASE = Path("results/eligible/v3")
TRAIN = BASE / "router_dev_train.csv"
VAL = BASE / "router_dev_validation.csv"
OUTPUT = BASE / "router_budget_v2_exploratory.json"

FEATURES = [
    "calibrated_probability",
    "model_disagreement_std",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
]
BUDGETS = [0.05, 0.10, 0.15, 0.20, 0.25]

SEED = 42
EPOCHS = 60
BATCH_SIZE = 512
LR = 0.001
BUDGET_WEIGHT = 0.2
TEMPERATURE = 0.5

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

train = pd.read_csv(TRAIN)
val = pd.read_csv(VAL)

assert set(train.patient_nbr).isdisjoint(set(val.patient_nbr))

scaler = StandardScaler()
X_train = scaler.fit_transform(train[FEATURES])
X_val = scaler.transform(val[FEATURES])

y_train = train.actual_30d.to_numpy(dtype=np.float32)
y_val = val.actual_30d.to_numpy(dtype=int)

device = torch.device("cpu")

X_tensor = torch.tensor(X_train, dtype=torch.float32)
y_tensor = torch.tensor(y_train, dtype=torch.float32)

model = nn.Sequential(
    nn.Linear(len(FEATURES), 32),
    nn.ReLU(),
    nn.Linear(32, 16),
    nn.ReLU(),
    nn.Linear(16, 1),
).to(device)

optimizer = torch.optim.Adam(model.parameters(), lr=LR)
bce = nn.BCEWithLogitsLoss(
    pos_weight=torch.tensor(
        [(len(y_train) - y_train.sum()) / y_train.sum()],
        dtype=torch.float32,
    )
)

for epoch in range(EPOCHS):
    model.train()
    permutation = torch.randperm(len(X_tensor))
    losses = []

    for start in range(0, len(permutation), BATCH_SIZE):
        idx = permutation[start:start + BATCH_SIZE]
        xb = X_tensor[idx]
        yb = y_tensor[idx]

        logits = model(xb).squeeze(-1)
        classification_loss = bce(logits, yb)



        # Capacity-constrained soft top-K surrogate.
        # Solve for a threshold that approximately allocates
        # the requested fraction of soft review capacity.

        soft_coverages = []
        capacity_errors = []

        for budget in BUDGETS:
            detached = logits.detach()

            low = detached.min() - 30.0 * TEMPERATURE
            high = detached.max() + 30.0 * TEMPERATURE

            for _ in range(40):
                midpoint = (low + high) / 2.0

                fraction = torch.sigmoid(
                    (detached - midpoint) / TEMPERATURE
                ).mean()

                if fraction > budget:
                    low = midpoint
                else:
                    high = midpoint

            cutoff = ((low + high) / 2.0).detach()

            weights = torch.sigmoid(
                (logits - cutoff) / TEMPERATURE
            )

            capacity_errors.append(
                torch.abs(weights.mean().detach() - budget)
            )

            coverage = (
                (weights * yb).sum()
                / yb.sum().clamp_min(1.0)
            )

            soft_coverages.append(coverage)

        budget_loss = 1.0 - torch.stack(
            soft_coverages
        ).mean()

        loss = (
            classification_loss
            + BUDGET_WEIGHT * budget_loss
        )

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        losses.append(loss.item())

    if (epoch + 1) % 10 == 0:
        print(
            f"Epoch {epoch + 1}/{EPOCHS} "
            f"loss={np.mean(losses):.5f}",
            flush=True,
        )

model.eval()
with torch.no_grad():
    scores = model(
        torch.tensor(X_val, dtype=torch.float32)
    ).squeeze(-1).numpy()

order = np.lexsort(
    (val.encounter_id.to_numpy(), -scores)
)

total_fn = int(y_val.sum())
results = []

print("\n=== V3 BUDGET-AWARE ROUTER V2 — EXPLORATORY ===")
for budget in BUDGETS:
    k = int(np.floor(len(val) * budget))
    captured = int(y_val[order[:k]].sum())
    coverage = captured / total_fn

    results.append({
        "budget": budget,
        "review_slots": k,
        "fn_captured": captured,
        "fn_coverage": coverage,
        "review_precision": captured / k,
    })

    print(
        f"{budget:.0%}: reviews={k}, "
        f"FN_captured={captured}, "
        f"FN_coverage={coverage:.4f}"
    )

if OUTPUT.exists():
    raise FileExistsError(f"Refusing to overwrite: {OUTPUT}")

OUTPUT.write_text(json.dumps({
    "status": "EXPLORATORY_NOT_INDEPENDENT",
    "seed": SEED,
    "epochs": EPOCHS,
    "budget_weight": BUDGET_WEIGHT,
    "temperature": TEMPERATURE,
    "objective": "capacity_constrained_soft_topk_detached_cutoff",
    "features": FEATURES,
    "results": results,
}, indent=2))

print("Saved:", OUTPUT)
print("BUDGET-AWARE ROUTER V2 EXPERIMENT: COMPLETE")
