
from pathlib import Path
import hashlib
import json
import math

import numpy as np
import pandas as pd

V2 = Path("results/eligible/v2")
V21 = Path("results/eligible/v2_1")

PREDICTIONS = V2 / "phase15_4_neural_test_predictions.csv"
SEGMENTS = V21 / "phase16_2_test_segment_assignments.csv"
MODEL = V2 / "phase15_3_selected_mlp_b.joblib"

PACKETS = V21 / "phase16_4_neural_review_packets.jsonl"
SUMMARY = V21 / "phase16_4_integration_summary.json"

BUDGET = 0.15
THRESHOLD = 0.115

SEGMENT_NAMES = {
    0: "Outpatient-utilization profile",
    1: "No recorded outpatient/emergency utilization",
    2: "Emergency-utilization profile",
}

GUARDRAIL = {
    "passed": True,
    "ground_truth_available": False,
    "patient_identifier_available": False,
    "diagnosis_allowed": False,
    "treatment_recommendation_allowed": False,
    "medication_recommendation_allowed": False,
    "prediction_modification_allowed": False,
    "router_modification_allowed": False,
    "priority_modification_allowed": False,
    "threshold_modification_allowed": False,
    "review_budget_modification_allowed": False,
    "autonomous_clinical_action_allowed": False,
}

FAIRNESS = {
    "mode": "READ_ONLY_POPULATION_AUDIT",
    "individual_decision_modification": False,
    "demographics_used_for_routing": False,
    "demographics_used_for_priority": False,
    "subgroup_specific_threshold": False,
}

PROHIBITED = {
    "actual_30d",
    "router_target",
    "patient_nbr",
    "gender",
    "race",
    "age",
    "raw_probability",
    "fn_router_probability",
}

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def clean_id(value):
    return str(value).strip()

def build_signal_explanations(row):
    signals = []

    if row["number_emergency"] > 0:
        signals.append(
            "Recorded emergency-service utilization is present."
        )

    if row["number_outpatient"] > 0:
        signals.append(
            "Recorded outpatient utilization is present."
        )

    if row["number_diagnoses"] >= 7:
        signals.append(
            "The recorded number of diagnoses is at least seven."
        )

    if row["model_disagreement_std"] >= 0.171856978:
        signals.append(
            "The existing model-disagreement signal exceeds "
            "a previously established audit threshold."
        )

    if not signals:
        signals.append(
            "The frozen neural router selected this encounter "
            "based on its combined input features."
        )

    return signals

def main():
    assert PREDICTIONS.exists()
    assert SEGMENTS.exists()
    assert MODEL.exists()

    assert not PACKETS.exists(), "Packet artifact already exists"
    assert not SUMMARY.exists(), "Summary artifact already exists"

    pred = pd.read_csv(PREDICTIONS)
    seg = pd.read_csv(SEGMENTS)

    assert len(pred) == 7858
    assert len(seg) == len(pred)
    assert pred["encounter_id"].is_unique
    assert seg["encounter_id"].is_unique

    pred["_id"] = pred["encounter_id"].map(clean_id)
    seg["_id"] = seg["encounter_id"].map(clean_id)

    assert set(pred["_id"]) == set(seg["_id"])

    assert (pred["predicted_30d"] == 0).all()
    assert np.allclose(
        pred["threshold"].astype(float),
        THRESHOLD
    )

    merged = pred.merge(
        seg[["_id", "segment"]],
        on="_id",
        how="left",
        validate="one_to_one"
    )

    assert merged["segment"].notna().all()
    assert set(merged["segment"].astype(int)) <= {0, 1, 2}

    scores = pd.to_numeric(
        merged["v2_mlp_probability"],
        errors="raise"
    )

    assert np.isfinite(scores).all()

    merged["_score"] = scores

    ranked = merged.sort_values(
        ["_score", "_id"],
        ascending=[False, True],
        kind="mergesort"
    )

    n = math.floor(len(ranked) * BUDGET)
    assert n == 1178

    selected = ranked.head(n)

    packets = []

    for _, row in selected.iterrows():
        segment = int(row["segment"])
        signals = build_signal_explanations(row)

        packet = {
            "schema_version": "16.4.5",
            "encounter_id": clean_id(row["encounter_id"]),
            "orchestrator": {
                "system": "RescueNet V2.1",
                "phase": "16.4",
                "runtime_mode": "OFFLINE_HUMAN_REVIEW_SIMULATION",
                "routing_source": "FROZEN_V2_MLP_B",
                "explanation_source": "DETERMINISTIC_V21_TEMPLATES",
            },
            "primary_model": {
                "calibrated_probability": float(
                    row["calibrated_probability"]
                ),
                "decision_threshold": THRESHOLD,
                "predicted_30d": 0,
            },
            "rescue_router": {
                "v2_mlp_probability": float(row["_score"]),
                "review_budget": BUDGET,
                "selected_for_review": 1,
            },
            "utilization_segment": {
                "segment_id": segment,
                "profile": SEGMENT_NAMES[segment],
                "clinical_risk_category": None,
            },
            "rescue_review": {
                "review_priority": "REVIEW_REQUIRED",
                "risk_signal_summary": (
                    "The frozen neural router selected this "
                    "primary-negative encounter for additional "
                    "human review within the fixed review budget."
                ),
                "reason_codes": [
                    "FROZEN_NEURAL_ROUTER_SELECTION"
                ],
                "human_review_action": "REVIEW_REQUIRED",
                "safety_flag": False,
            },
            "explanation": {
                "schema_version": "16.4",
                "review_priority": "REVIEW_REQUIRED",
                "explanation": (
                    "This encounter was selected by a frozen "
                    "neural routing score. Listed utilization "
                    "signals provide descriptive context only; "
                    "they are not validated causal explanations "
                    "of the neural model's prediction."
                ),
                "signal_explanations": signals,
                "uncertainty_statement": (
                    "Neural ensemble uncertainty was evaluated "
                    "experimentally but was not promoted into "
                    "the frozen routing decision."
                ),
                "human_review_statement": (
                    "Human review is required. RescueNet does "
                    "not independently diagnose, recommend "
                    "treatment or medication, change predictions, "
                    "or initiate clinical action."
                ),
                "safety_flag": False,
            },
            "safety_guardrail": dict(GUARDRAIL),
            "fairness_monitor": dict(FAIRNESS),
            "human_review_required": True,
            "workflow_disposition": "HUMAN_REVIEW_REQUIRED",
            "autonomous_clinical_action": False,
        }

        packets.append(packet)

    assert len(packets) == n
    assert len({
        p["encounter_id"] for p in packets
    }) == n

    serialized = [
        json.dumps(p, sort_keys=True, allow_nan=False)
        for p in packets
    ]

    forbidden_tokens = [
        f'"{name}"'
        for name in PROHIBITED
    ]

    for line in serialized:
        for token in forbidden_tokens:
            assert token not in line, (
                f"Prohibited field leaked: {token}"
            )

    summary = {
        "project": "RescueNet V2.1",
        "phase": "16.4.5",
        "status": "OFFLINE_PACKETS_GENERATED",
        "population": len(pred),
        "review_budget": BUDGET,
        "selected_encounters": n,
        "primary_threshold": THRESHOLD,
        "router": "FROZEN_V2_MLP_B",
        "segment_counts": {
            str(k): int(v)
            for k, v in selected["segment"]
            .value_counts().sort_index().items()
        },
        "human_review_required_for_all": True,
        "autonomous_clinical_action_allowed": False,
        "uncertainty_fusion_promoted": False,
        "clinical_deployment": False,
        "input_sha256": {
            str(p): sha256(p)
            for p in [PREDICTIONS, SEGMENTS, MODEL]
        },
    }

    V21.mkdir(parents=True, exist_ok=True)

    with PACKETS.open("x", encoding="utf-8") as f:
        for line in serialized:
            f.write(line + "\n")

    summary["packet_sha256"] = sha256(PACKETS)

    with SUMMARY.open("x", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("=" * 76)
    print("PHASE 16.4.5 — V2.1 NEURAL AGENT ORCHESTRATOR")
    print("=" * 76)
    print("Routing population:", len(pred))
    print("Neural-selected encounters:", n)
    print("Selected segment counts:", summary["segment_counts"])
    print("Human review required: YES")
    print("Autonomous clinical action: NO")
    print("Neural uncertainty fusion: NOT PROMOTED")
    print("Packet SHA256:", summary["packet_sha256"])
    print("Packets:", PACKETS)
    print("Summary:", SUMMARY)
    print("Frozen V2 modified: NO")
    print("STATUS: PHASE 16.4.5 COMPLETE")

if __name__ == "__main__":
    main()
