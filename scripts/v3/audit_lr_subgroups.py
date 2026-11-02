"""Exploratory LR router subgroup false-negative coverage audit."""

from pathlib import Path
import json
import numpy as np
import pandas as pd

BASE = Path("results/eligible/v3")
OUTPUT = BASE / "router_lr_subgroup_audit.json"
BUDGETS = [0.05, 0.10, 0.15, 0.20, 0.25]

audit = pd.read_csv(BASE / "router_subgroup_audit.csv")
scores = pd.read_csv(BASE / "router_lr_validation_scores.csv")

assert audit.encounter_id.is_unique
assert scores.encounter_id.is_unique

df = audit.merge(
    scores[["encounter_id", "lr_router_score"]],
    on="encounter_id",
    how="left",
    validate="one_to_one",
)

assert len(df) == len(audit)
assert df.lr_router_score.notna().all()

order = np.lexsort((
    df.encounter_id.to_numpy(),
    -df.lr_router_score.to_numpy(),
))

results = []

print("=== V3 LR SUBGROUP COVERAGE AUDIT ===")

for budget in BUDGETS:
    k = int(np.floor(len(df) * budget))

    selected = np.zeros(len(df), dtype=bool)
    selected[order[:k]] = True

    assert selected.sum() == k

    print(f"\n=== Budget {budget:.0%} | Reviews {k} ===")

    for attribute in ["race", "gender", "age"]:
        print(f"\n{attribute.upper()}")

        for group, indices in df.groupby(
            attribute, dropna=False
        ).indices.items():

            indices = np.asarray(indices)
            labels = df.actual_30d.to_numpy(dtype=int)[indices]

            total_fn = int(labels.sum())
            captured = int(
                (labels * selected[indices]).sum()
            )
            true_negatives = len(indices) - total_fn

            eligible = (
                len(indices) >= 100
                and total_fn >= 30
                and true_negatives >= 30
            )

            coverage = (
                captured / total_fn
                if total_fn else None
            )

            record = {
                "budget": budget,
                "attribute": attribute,
                "group": str(group),
                "encounters": len(indices),
                "false_negatives": total_fn,
                "fn_captured": captured,
                "fn_coverage": coverage,
                "eligible": eligible,
            }

            results.append(record)

            if eligible:
                print(
                    f"{str(group):18s} "
                    f"FN={total_fn:3d} "
                    f"captured={captured:3d} "
                    f"coverage={coverage:.3f}"
                )

if OUTPUT.exists():
    raise FileExistsError(f"Refusing to overwrite: {OUTPUT}")

OUTPUT.write_text(json.dumps({
    "status": "EXPLORATORY_NOT_INDEPENDENT",
    "method": "LR_exact_topk_subgroup_audit",
    "results": results,
}, indent=2))

print("\nSaved:", OUTPUT)
print("LR SUBGROUP COVERAGE AUDIT: COMPLETE")
