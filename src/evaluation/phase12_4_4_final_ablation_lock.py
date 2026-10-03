from pathlib import Path
import json
import hashlib
import pandas as pd


print("=" * 80)
print("PHASE 12.4.4 — FINAL ABLATION STUDY LOCK")
print("=" * 80)


# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------

OUT_DIR = Path("results/eligible/final_comparison")

PROTOCOL_PATH = (
    OUT_DIR / "phase12_4_1_ablation_protocol.json"
)

ASSIGNMENTS_PATH = (
    OUT_DIR / "phase12_4_2_ablation_assignments.csv"
)

RESULTS_PATH = (
    OUT_DIR / "phase12_4_2_ablation_results.csv"
)

EXECUTION_AUDIT_PATH = (
    OUT_DIR / "phase12_4_2_ablation_execution_audit.json"
)

CONTRIBUTION_PATH = (
    OUT_DIR / "phase12_4_3_component_contributions.csv"
)

CONTRIBUTION_AUDIT_PATH = (
    OUT_DIR / "phase12_4_3_ablation_contribution_audit.json"
)

FINAL_LOCK_PATH = (
    OUT_DIR / "phase12_4_final_ablation_lock.json"
)


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------

def section(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)

    return h.hexdigest()


# ---------------------------------------------------------------------
# A — VERIFY COMPLETE ABLATION CHAIN
# ---------------------------------------------------------------------

section("A — VERIFY COMPLETE PHASE 12.4 ARTIFACT CHAIN")

required = [
    PROTOCOL_PATH,
    ASSIGNMENTS_PATH,
    RESULTS_PATH,
    EXECUTION_AUDIT_PATH,
    CONTRIBUTION_PATH,
    CONTRIBUTION_AUDIT_PATH,
]

for path in required:
    if not path.exists():
        raise FileNotFoundError(path)

    print("FOUND:", path)

print("Phase 12.4 artifact chain: PASSED")


# ---------------------------------------------------------------------
# B — LOAD FROZEN STATES
# ---------------------------------------------------------------------

section("B — LOAD FROZEN PHASE STATES")

with open(PROTOCOL_PATH) as f:
    protocol = json.load(f)

with open(EXECUTION_AUDIT_PATH) as f:
    execution = json.load(f)

with open(CONTRIBUTION_AUDIT_PATH) as f:
    contribution_audit = json.load(f)

results = pd.read_csv(RESULTS_PATH)
contributions = pd.read_csv(CONTRIBUTION_PATH)

print("12.4.1:", protocol["status"])
print("12.4.2:", execution["status"])
print("12.4.3:", contribution_audit["status"])

if protocol["status"] != "ABLATION_PROTOCOL_FROZEN":
    raise RuntimeError("12.4.1 status invalid.")

if execution["status"] != "FROZEN_COMPONENT_ABLATIONS_EXECUTED":
    raise RuntimeError("12.4.2 status invalid.")

if contribution_audit["status"] != \
        "ABLATION_CONTRIBUTION_ANALYSIS_COMPLETE":
    raise RuntimeError("12.4.3 status invalid.")

print("Phase-state verification: PASSED")


# ---------------------------------------------------------------------
# C — VERIFY LOCKED REFERENCE VALUES
# ---------------------------------------------------------------------

section("C — VERIFY LOCKED REFERENCE VALUES")

full = results[
    results["variant"] == "FULL"
].iloc[0]

reviews = int(full["review_population"])
fn_escalated = int(full["false_negatives_escalated"])
coverage = float(
    full["false_negative_review_coverage"]
)
precision = float(
    full["review_precision_for_false_negative"]
)

print("Full-router reviews:", reviews)
print("Full-router FNs escalated:", fn_escalated)
print("Full-router FN coverage:", f"{coverage:.6f}")
print("Full-router FN review precision:", f"{precision:.6f}")

if reviews != 1178:
    raise RuntimeError("Review budget lock failed.")

if fn_escalated != 110:
    raise RuntimeError("Full-router FN lock failed.")

print("Reference-value lock: PASSED")


# ---------------------------------------------------------------------
# D — VERIFY ALL MATCHED BUDGETS
# ---------------------------------------------------------------------

section("D — VERIFY MATCHED-BUDGET ABLATIONS")

if not (results["review_population"] == 1178).all():
    raise RuntimeError(
        "At least one ablation violates review budget."
    )

for _, row in results.iterrows():
    print(
        row["variant"],
        "-> reviews:",
        int(row["review_population"]),
        "| FNs:",
        int(row["false_negatives_escalated"])
    )

print("All ablation budgets: PASSED")


# ---------------------------------------------------------------------
# E — LOCK COMPONENT FINDINGS
# ---------------------------------------------------------------------

section("E — LOCK OBSERVED COMPONENT FINDINGS")

supportive = contributions[
    contributions["contribution_class"] == "SUPPORTIVE"
]

non_supportive = contributions[
    contributions["contribution_class"]
    == "NON_SUPPORTIVE_IN_ABLATION"
]

neutral = contributions[
    contributions["contribution_class"] == "NEUTRAL"
]

print(
    "Supportive:",
    supportive["removed_feature"].tolist()
)

print(
    "Neutral:",
    neutral["removed_feature"].tolist()
)

print(
    "Non-supportive under frozen ablation:",
    non_supportive["removed_feature"].tolist()
)

expected_supportive = {
    "calibrated_probability",
    "number_diagnoses",
}

expected_non_supportive = {
    "model_disagreement_std",
    "number_outpatient",
    "number_emergency",
}

if set(supportive["removed_feature"]) != expected_supportive:
    raise RuntimeError(
        "Supportive-component lock failed."
    )

if set(non_supportive["removed_feature"]) != expected_non_supportive:
    raise RuntimeError(
        "Non-supportive-component lock failed."
    )

print("Component finding lock: PASSED")


# ---------------------------------------------------------------------
# F — LOCK NUMERIC ABLATION RESULTS
# ---------------------------------------------------------------------

section("F — LOCK NUMERIC ABLATION RESULTS")

expected_fn = {
    "FULL": 110,
    "DROP_CALIBRATED_PROBABILITY": 101,
    "DROP_MODEL_DISAGREEMENT": 112,
    "DROP_NUMBER_DIAGNOSES": 109,
    "DROP_NUMBER_OUTPATIENT": 116,
    "DROP_NUMBER_EMERGENCY": 113,
}

for variant, expected in expected_fn.items():

    row = results[
        results["variant"] == variant
    ]

    if len(row) != 1:
        raise RuntimeError(
            f"Missing or duplicated variant: {variant}"
        )

    observed = int(
        row.iloc[0]["false_negatives_escalated"]
    )

    print(
        variant,
        "expected:",
        expected,
        "observed:",
        observed
    )

    if observed != expected:
        raise RuntimeError(
            f"{variant} numeric lock failed."
        )

print("Numeric ablation lock: PASSED")


# ---------------------------------------------------------------------
# G — SCIENTIFIC CONCLUSION
# ---------------------------------------------------------------------

section("G — FREEZE SCIENTIFIC CONCLUSION")

scientific_conclusion = {
    "primary_finding":
        (
            "Under a fixed 1,178-case review budget, "
            "calibrated primary-model probability showed "
            "the strongest supportive contribution to the "
            "frozen learned router. Removing this signal "
            "reduced false-negative escalation from 110 to "
            "101 cases."
        ),

    "secondary_finding":
        (
            "Removing number_diagnoses produced a small "
            "reduction from 110 to 109 escalated false "
            "negatives."
        ),

    "negative_ablation_finding":
        (
            "Removal of model_disagreement_std, "
            "number_outpatient, or number_emergency produced "
            "slightly higher false-negative escalation on the "
            "frozen final test set."
        ),

    "interpretation_boundary":
        (
            "These findings are descriptive matched-budget "
            "ablations of the frozen router and do not establish "
            "causal clinical feature importance."
        ),

    "no_posthoc_optimization":
        (
            "The observed improvements in several ablated "
            "variants are not used to modify, retrain, select, "
            "or retune the frozen learned router."
        ),
}

for key, value in scientific_conclusion.items():
    print()
    print(key + ":")
    print(value)


# ---------------------------------------------------------------------
# H — CAPTURE FINAL ARTIFACT HASHES
# ---------------------------------------------------------------------

section("H — CAPTURE FINAL PHASE 12.4 HASHES")

artifact_hashes = {}

for path in required:
    digest = sha256(path)
    artifact_hashes[str(path)] = digest

    print(path.name, "->", digest)

print("Artifact hashes captured: PASSED")


# ---------------------------------------------------------------------
# I — CREATE FINAL LOCK MANIFEST
# ---------------------------------------------------------------------

section("I — CREATE FINAL ABLATION LOCK MANIFEST")

manifest = {
    "phase": "12.4",

    "status": "ABLATION_STUDY_FROZEN",

    "population": {
        "primary_model_negative_cases": 7858,
        "primary_model_false_negatives": 557,
    },

    "review_budget": {
        "cases": 1178,
        "rate": 1178 / 7858,
    },

    "full_router": {
        "false_negatives_escalated": fn_escalated,
        "false_negative_review_coverage": coverage,
        "review_precision_for_false_negative": precision,
    },

    "ablation_false_negatives_escalated": expected_fn,

    "supportive_components":
        supportive["removed_feature"].tolist(),

    "neutral_components":
        neutral["removed_feature"].tolist(),

    "non_supportive_in_ablation":
        non_supportive["removed_feature"].tolist(),

    "scientific_conclusion":
        scientific_conclusion,

    "artifact_hashes":
        artifact_hashes,

    "integrity": {
        "primary_model_modified": False,
        "primary_threshold_modified": False,
        "router_retrained": False,
        "router_retuned": False,
        "review_budget_modified": False,
        "test_outcomes_used_for_routing": False,
        "posthoc_best_ablation_selected": False,
        "phase10_modified": False,
        "phase11_modified": False,
        "phase12_1_to_12_3_modified": False,
    },

    "next_phase":
        "12.5 — Final safety and fairness audit",
}

with open(FINAL_LOCK_PATH, "w") as f:
    json.dump(
        manifest,
        f,
        indent=2
    )

print("Saved:", FINAL_LOCK_PATH)


# ---------------------------------------------------------------------
# J — FINAL VERIFICATION
# ---------------------------------------------------------------------

section("J — FINAL VERIFICATION")

checks = {
    "phase12_4_1_frozen":
        protocol["status"] ==
        "ABLATION_PROTOCOL_FROZEN",

    "phase12_4_2_complete":
        execution["status"] ==
        "FROZEN_COMPONENT_ABLATIONS_EXECUTED",

    "phase12_4_3_complete":
        contribution_audit["status"] ==
        "ABLATION_CONTRIBUTION_ANALYSIS_COMPLETE",

    "population_lock":
        execution["population"]["cases"] == 7858,

    "primary_fn_lock":
        execution["population"][
            "primary_false_negatives"
        ] == 557,

    "review_budget_lock":
        reviews == 1178,

    "full_router_fn_lock":
        fn_escalated == 110,

    "all_ablation_budgets_matched":
        bool(
            (
                results["review_population"]
                == 1178
            ).all()
        ),

    "five_components_analyzed":
        len(contributions) == 5,

    "no_router_retraining":
        execution["integrity"][
            "router_retrained"
        ] is False,

    "no_router_retuning":
        execution["integrity"][
            "router_retuned"
        ] is False,

    "final_lock_exists":
        FINAL_LOCK_PATH.exists(),
}

for name, passed in checks.items():
    print(
        f"{name}:",
        "PASSED" if passed else "FAILED"
    )

if not all(checks.values()):
    raise RuntimeError(
        "Phase 12.4 final lock verification failed."
    )


print()
print("=" * 80)
print(
    "PHASE 12.4 COMPLETE — "
    "ABLATION STUDY PASSED AND FROZEN"
)
print("=" * 80)

print()
print("Full learned router:")
print(" Reviews:", reviews)
print(" FNs escalated:", fn_escalated)
print(
    " FN coverage:",
    f"{coverage:.2%}"
)

print()
print("Ablation findings:")

for _, row in contributions.sort_values(
    "contribution_rank"
).iterrows():

    print(
        f" {row['removed_feature']}: "
        f"{int(row['false_negatives_escalated'])} FNs "
        f"({row['contribution_class']})"
    )

print()
print("Router changed after ablation: NO")
print("Best test-set ablation adopted: NO")
print("Post-hoc optimization performed: NO")

print()
print(
    "NEXT: PHASE 12.5 — "
    "FINAL SAFETY AND FAIRNESS AUDIT"
)
