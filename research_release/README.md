# CareCompute / RescueNet Research Release

## Scope

This repository documents three research stages:

- CareCompute V1: Logistic regression rescue routing
- RescueNet V2: Neural rescue routing and multi-budget evaluation
- RescueNet V2.1: Utilization segmentation and offline orchestration

## Frozen Research Artifacts

The V2 research manifest records 16 verified artifacts.

The V2.1 research manifest records 13 verified artifacts.

All 29 manifest-listed artifacts passed SHA-256 verification.

See:
verification/frozen_artifact_inventory.json

## Reproducibility

V1 source code and research methodology are included.

The V2 and V2.1 experimental artifacts are preserved
locally but are not included in this public release.

The V2.1 offline orchestration source is included.

Complete V2/V2.1 model-training and experimental
reproduction scripts have not been located in the
repository.

Therefore, full end-to-end retraining reproducibility
is not established.

The public verification inventory records checksums
of frozen local artifacts. It does not independently
make those artifacts available for reproduction.

## Scientific Findings

At the frozen 15% review budget:

- V1 logistic regression: 110 false negatives escalated
- V2 MLP-B: 112 false negatives escalated

Statistically reliable superiority of MLP-B over
logistic regression was not demonstrated.

V2.1 produced 1,178 offline neural review packets.

The three utilization segments are not validated
clinical risk categories.

Uncertainty fusion was not promoted into the
frozen routing system.

## Safety and Deployment

This project is retrospective research.

No prospective clinical validation was performed.

No actual clinician review was performed in V2.1.

The offline workflow requires human review and
does not authorize autonomous clinical actions.

The research does not establish clinical safety
or suitability for deployment.

## Data Release Policy

Patient-level and encounter-level research records,
predictions, generated review packets, and trained
model artifacts are excluded pending a separate
privacy, licensing, and reproducibility review.

The Streamlit demonstration is separate from
the frozen V2/V2.1 evaluation artifacts.
