# RescueNet V2.1 — Segmentation and Offline Orchestration

## Research Status

FROZEN_OFFLINE_RESEARCH_PROTOTYPE

V2.1 extends the frozen V2 research with utilization-based
segmentation, additional uncertainty analysis, and an offline
neural review-packet orchestration prototype.

## Frozen Research Configuration

- Routing population: 7,858
- Primary classifier threshold: 0.115
- Review budget: 15%
- Encounters selected: 1,178
- Frozen neural router: MLP-B
- False negatives selected by MLP-B: 112

## Encounter Segmentation

Three encounter-level utilization profiles were evaluated.

Among the 1,178 selected encounters:

| Segment | Selected encounters |
|---|---:|
| Segment 0 | 304 |
| Segment 1 | 740 |
| Segment 2 | 134 |

These segments are not validated clinical risk categories.

## Uncertainty Analysis

Additional uncertainty experiments were performed.

Uncertainty fusion did not demonstrate consistent improvement
and was not promoted into the frozen routing system.

## Offline Orchestration

The system generated 1,178 neural review packets.

- Independent packet validation: PASSED
- Failure-injection tests detected: 9/9
- Human review required: Yes
- Actual clinician review performed: No
- Autonomous clinical action: Not allowed
- Clinical deployment: No

## Scientific Limitations

- Retrospective research using historical encounters
- Post-hoc analyses after final-test outcomes were known
- No independent confirmatory V2.1 evaluation
- No statistically established neural-router superiority
- Segments are not validated clinical risk strata
- Sparse subgroup counts limit fairness interpretation
- No verified deployable five-seed uncertainty ensemble
- Explanation templates are descriptive, not causal
- Offline safety-contract tests do not establish clinical safety
- Full end-to-end retraining reproducibility is not established

## Artifact Integrity

The V2.1 manifest contains 13 verified artifact records.

See:
research_release/verification/frozen_artifact_inventory.json
