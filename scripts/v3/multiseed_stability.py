"""Exploratory multi-seed stability audit for RescueNet V3."""

from pathlib import Path
from itertools import combinations
import json
import random

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.nn import functional as F

BASE = Path("results/eligible/v3")
OUTPUT = BASE / "router_multiseed_stability.json"

SEEDS = [42, 123, 2026, 7, 99]
BUDGETS = [0.05, 0.10, 0.15, 0.20, 0.25]
FEATURES = [
    "calibrated_probability",
    "model_disagreement_std",
    "number_diagnoses",
    "number_outpatient",
    "number_emergency",
]

EPOCHS = 60
BATCH_SIZE = 512
LR = 0.001
RANK_WEIGHT = 0.2

train = pd.read_csv(BASE / "router_dev_train.csv")
val = pd.read_csv(BASE / "router_dev_validation.csv")

assert set(train.patient_nbr).isdisjoint(set(val.patient_nbr))
assert val.encounter_id.is_unique

scaler = StandardScaler()
X_train = scaler.fit_transform(train[FEATURES])
X_val = scaler.transform(val[FEATURES])

y_train = train.actual_30d.to_numpy(dtype=np.float32)
y_val = val.actual_30d.to_numpy(dtype=int)
encounter_ids = val.encounter_id.to_numpy()

X_tensor = torch.tensor(X_train, dtype=torch.float32)
y_tensor = torch.tensor(y_train, dtype=torch.float32)
X_val_tensor = torch.tensor(X_val, dtype=torch.float32)

positive_weight = torch.tensor(
    [(len(y_train) - y_train.sum()) / y_train.sum()],
    dtype=torch.float32,
)

all_results = []
selected_sets = {str(b): [] for b in BUDGETS}

for seed in SEEDS:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    model = nn.Sequential(
        nn.Linear(len(FEATURES), 32),
        nn.ReLU(),
        nn.Linear(32, 16),
        nn.ReLU(),
        nn.Linear(16, 1),
    )

    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    bce = nn.BCEWithLogitsLoss(pos_weight=positive_weight)

    for epoch in range(EPOCHS):
        model.train()
        permutation = torch.randperm(len(X_tensor))

        for start in range(0, len(permutation), BATCH_SIZE):
            idx = permutation[start:start + BATCH_SIZE]
            xb = X_tensor[idx]
            yb = y_tensor[idx]

            logits = model(xb).squeeze(-1)
            classification_loss = bce(logits, yb)

            positives = logits[yb == 1]
            negatives = logits[yb == 0]

            if len(positives) and len(negatives):
                differences = positives[:, None] - negatives[None, :]
                ranking_loss = F.softplus(-differences).mean()
            else:
                ranking_loss = logits.new_tensor(0.0)

            loss = classification_loss + RANK_WEIGHT * ranking_loss

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    model.eval()
    with torch.no_grad():
        scores = model(X_val_tensor).squeeze(-1).numpy()

    order = np.lexsort((encounter_ids, -scores))
    seed_results = []

    for budget in BUDGETS:
        k = int(np.floor(len(val) * budget))
        indices = order[:k]
        captured = int(y_val[indices].sum())

        selected_sets[str(budget)].append(
            set(encounter_ids[indices].tolist())
        )

        seed_results.append({
            "budget": budget,
            "review_slots": k,
            "fn_captured": captured,
            "fn_coverage": captured / int(y_val.sum()),
        })

    all_results.append({
        "seed": seed,
        "results": seed_results,
    })

    print(f"Seed {seed}: " + ", ".join(
        f"{r['budget']:.0%}={r['fn_captured']}"
        for r in seed_results
    ), flush=True)

summary = []

for budget_index, budget in enumerate(BUDGETS):
    captures = [
        run["results"][budget_index]["fn_captured"]
        for run in all_results
    ]

    sets = selected_sets[str(budget)]
    jaccards = []

    for first, second in combinations(sets, 2):
        union = len(first | second)
        jaccards.append(len(first & second) / union)

    summary.append({
        "budget": budget,
        "mean_fn_captured": float(np.mean(captures)),
        "std_fn_captured": float(np.std(captures, ddof=1)),
        "min_fn_captured": int(min(captures)),
        "max_fn_captured": int(max(captures)),
        "mean_pairwise_jaccard": float(np.mean(jaccards)),
        "min_pairwise_jaccard": float(min(jaccards)),
    })

if OUTPUT.exists():
    raise FileExistsError(f"Refusing to overwrite: {OUTPUT}")

OUTPUT.write_text(json.dumps({
    "status": "EXPLORATORY_NOT_INDEPENDENT",
    "seeds": SEEDS,
    "epochs": EPOCHS,
    "rank_weight": RANK_WEIGHT,
    "validation_encounters": len(val),
    "validation_false_negatives": int(y_val.sum()),
    "runs": all_results,
    "summary": summary,
}, indent=2))

print("\n=== MULTI-SEED STABILITY SUMMARY ===")
for result in summary:
    print(
        f"{result['budget']:.0%}: "
        f"FN={result['mean_fn_captured']:.2f}"
        f" ± {result['std_fn_captured']:.2f}, "
        f"Jaccard={result['mean_pairwise_jaccard']:.4f}"
    )

print("\nSaved:", OUTPUT)
print("MULTI-SEED STABILITY AUDIT: COMPLETE")
