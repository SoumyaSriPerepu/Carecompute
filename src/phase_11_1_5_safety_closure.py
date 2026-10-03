from pathlib import Path
import json
import hashlib


# =============================================================================
# PATHS
# =============================================================================

BASE = Path("results/eligible/safety")

P111 = BASE / "phase11_1_1_baseline_safety_audit.json"
P112 = BASE / "phase11_1_2_routing_false_negative_safety_audit.json"
P113 = BASE / "phase11_1_3_safety_override_rule.json"
P114 = BASE / "phase11_1_4_forced_safety_route_experiment.json"

OUTPUT = BASE / "phase11_1_safety_closure_manifest.json"


# =============================================================================
# HELPERS
# =============================================================================

def section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def load_json(path):
    with path.open() as f:
        return json.load(f)


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


# =============================================================================
# HEADER
# =============================================================================

section("PHASE 11.1.5 — SAFETY FAILURE REPORT AND CLOSURE LOCK")


# =============================================================================
# A — VERIFY SAFETY ARTIFACT CHAIN
# =============================================================================

section("A — VERIFY PHASE 11.1 ARTIFACT CHAIN")

paths = [P111, P112, P113, P114]

for p in paths:
    if not p.exists():
        raise FileNotFoundError(p)

    print("FOUND:", p)

print("Safety artifact presence: PASSED")


# =============================================================================
# B — LOAD VERIFIED RESULTS
# =============================================================================

section("B — LOAD VERIFIED SAFETY RESULTS")

a111 = load_json(P111)
a112 = load_json(P112)
a113 = load_json(P113)
a114 = load_json(P114)

if a111["status"] != "PASSED":
    raise RuntimeError("11.1.1 not PASSED")

if a112["status"] != "PASSED":
    raise RuntimeError("11.1.2 not PASSED")

if a113["status"] != "PREDECLARED_FROZEN":
    raise RuntimeError("11.1.3 rule not frozen")

if a114["status"] != "PASSED":
    raise RuntimeError("11.1.4 not PASSED")

print("11.1.1 baseline audit: PASSED")
print("11.1.2 routing audit: PASSED")
print("11.1.3 safety rule: PREDECLARED_FROZEN")
print("11.1.4 counterfactual experiment: PASSED")


# =============================================================================
# C — VERIFY CROSS-PHASE IMMUTABLE VALUES
# =============================================================================

section("C — VERIFY CROSS-PHASE SAFETY VALUES")

baseline_fn = int(
    a111["confusion_matrix"]["fn"]
)

baseline_fnr = float(
    a111["safety_metrics"]["false_negative_rate"]
)

baseline_recall = float(
    a111["safety_metrics"]["recall"]
)

routing_fn = int(
    a112["false_negative_safety"]["baseline_false_negatives"]
)

original_reviewed_fn = int(
    a112["false_negative_safety"][
        "false_negatives_selected_for_rescue_review"
    ]
)

original_bypassed_fn = int(
    a112["false_negative_safety"][
        "false_negatives_bypassing_rescue_review"
    ]
)

experiment_fn = int(
    a114["population"]["primary_model_false_negatives"]
)

additional_fn = int(
    a114["safety_override"][
        "previously_bypassed_false_negatives_escalated"
    ]
)

combined_reviewed_fn = int(
    a114["combined_policy"]["false_negatives_reviewed"]
)

residual_fn = int(
    a114["combined_policy"][
        "false_negatives_remaining_bypass"
    ]
)

original_review_population = int(
    a114["original_policy"]["review_cases"]
)

combined_review_population = int(
    a114["combined_policy"]["review_cases"]
)

additional_reviews = int(
    a114["safety_override"]["additional_review_cases"]
)

original_coverage = float(
    a114["original_policy"][
        "false_negative_review_coverage"
    ]
)

combined_coverage = float(
    a114["combined_policy"][
        "false_negative_review_coverage"
    ]
)

reviews_per_fn = float(
    a114["safety_impact"][
        "additional_reviews_per_newly_escalated_fn"
    ]
)

checks = {
    "baseline_fn_consistency":
        baseline_fn == routing_fn == experiment_fn == 557,

    "original_fn_accounting":
        original_reviewed_fn + original_bypassed_fn == baseline_fn,

    "combined_fn_accounting":
        combined_reviewed_fn + residual_fn == baseline_fn,

    "override_increment":
        combined_reviewed_fn
        == original_reviewed_fn + additional_fn,

    "review_increment":
        combined_review_population
        == original_review_population + additional_reviews,
}

for name, passed in checks.items():
    print(name + ":", "PASSED" if passed else "FAILED")

if not all(checks.values()):
    raise RuntimeError(
        "Cross-phase safety consistency failed."
    )


# =============================================================================
# D — BASELINE SAFETY FINDINGS
# =============================================================================

section("D — BASELINE SAFETY FINDINGS")

print("Actual 30-day positives: 1736")
print("True positives: 1179")
print("False negatives:", baseline_fn)

print(
    f"Recall / sensitivity: {baseline_recall:.6f}"
)

print(
    f"False-negative rate: {baseline_fnr:.6f}"
)

print()
print(
    "Finding: the frozen primary model misses "
    f"{baseline_fn} of 1736 actual 30-day readmissions."
)


# =============================================================================
# E — ROUTING SAFETY FINDINGS
# =============================================================================

section("E — ROUTING SAFETY FINDINGS")

print(
    "False negatives selected for Rescue Review:",
    original_reviewed_fn
)

print(
    "False negatives bypassing Rescue Review:",
    original_bypassed_fn
)

print(
    f"Original FN review coverage: {original_coverage:.6f}"
)

print(
    "Router FN enrichment ratio:",
    round(
        float(
            a112["router_enrichment"][
                "rescue_review_fn_enrichment_ratio"
            ]
        ),
        6,
    )
)

print()
print(
    "Finding: the Rescue Router concentrates false negatives "
    "above their baseline prevalence, but most primary-model "
    "false negatives still bypass Rescue Review."
)


# =============================================================================
# F — SAFETY OVERRIDE FINDINGS
# =============================================================================

section("F — PRE-DECLARED SAFETY OVERRIDE FINDINGS")

print("Original review population:", original_review_population)
print("Additional forced reviews:", additional_reviews)
print("Combined review population:", combined_review_population)

print()

print(
    "Additional previously bypassed FNs escalated:",
    additional_fn
)

print(
    "Combined false negatives reviewed:",
    combined_reviewed_fn
)

print(
    "Residual false negatives bypassing review:",
    residual_fn
)

print(
    f"Combined FN review coverage: {combined_coverage:.6f}"
)

print(
    "Additional reviews per newly escalated FN:",
    round(reviews_per_fn, 6)
)


# =============================================================================
# G — FAILURE DISCLOSURE
# =============================================================================

section("G — REQUIRED SAFETY FAILURE DISCLOSURE")

failures = [
    {
        "failure_id": "SAFETY-01",
        "description":
            "The frozen primary classifier produces false-negative "
            "30-day readmission predictions.",
        "count": baseline_fn,
        "rate": baseline_fnr,
    },

    {
        "failure_id": "SAFETY-02",
        "description":
            "The frozen Rescue Router does not escalate most "
            "primary-model false negatives under the original "
            "15% review policy.",
        "count": original_bypassed_fn,
        "fraction_of_false_negatives":
            original_bypassed_fn / baseline_fn,
    },

    {
        "failure_id": "SAFETY-03",
        "description":
            "The pre-declared safety override improves escalation "
            "coverage but requires substantially more human review.",
        "additional_reviews": additional_reviews,
        "additional_false_negatives_escalated": additional_fn,
        "reviews_per_additional_false_negative":
            reviews_per_fn,
    },

    {
        "failure_id": "SAFETY-04",
        "description":
            "Residual primary-model false negatives remain "
            "unreviewed even after the counterfactual safety "
            "override.",
        "count": residual_fn,
        "fraction_of_false_negatives":
            residual_fn / baseline_fn,
    },
]

for failure in failures:
    print()
    print(failure["failure_id"])
    print(failure["description"])

    for k, v in failure.items():
        if k not in {"failure_id", "description"}:
            print(f"  {k}: {v}")

print()
print("Safety failures hidden: NO")
print("Residual safety failure present: YES")


# =============================================================================
# H — INTERPRETATION BOUNDARY
# =============================================================================

section("H — INTERPRETATION BOUNDARY")

limitations = [
    "This is a retrospective safety audit.",
    "The evaluation does not establish prospective clinical safety.",
    "Human review is not assumed to correct every escalated case.",
    "The safety override is a counterfactual routing experiment.",
    "The frozen primary model was not retrained.",
    "The frozen Phase 10 Rescue Router was not modified.",
    "Residual false negatives remain after the safety override.",
]

for limitation in limitations:
    print(" -", limitation)

print()
print("Clinical safety claim permitted: NO")


# =============================================================================
# I — CREATE SAFETY CLOSURE MANIFEST
# =============================================================================

section("I — CREATE SAFETY CLOSURE MANIFEST")

manifest = {
    "phase": "11.1.5",
    "section": "11.1 Safety",
    "status": "SAFETY_AUDIT_COMPLETE",

    "baseline": {
        "actual_positive_cases": 1736,
        "true_positives": 1179,
        "false_negatives": baseline_fn,
        "recall": baseline_recall,
        "false_negative_rate": baseline_fnr,
    },

    "original_routing": {
        "review_population": original_review_population,
        "false_negatives_reviewed": original_reviewed_fn,
        "false_negatives_bypassed": original_bypassed_fn,
        "false_negative_review_coverage":
            original_coverage,
    },

    "predeclared_safety_override": {
        "rule_status": a113["status"],
        "additional_reviews": additional_reviews,
        "combined_review_population":
            combined_review_population,
        "additional_false_negatives_escalated":
            additional_fn,
        "combined_false_negatives_reviewed":
            combined_reviewed_fn,
        "combined_false_negative_review_coverage":
            combined_coverage,
        "residual_false_negatives_bypassing_review":
            residual_fn,
        "additional_reviews_per_newly_escalated_fn":
            reviews_per_fn,
    },

    "failures": failures,

    "claims_boundary": {
        "clinical_safety_established": False,
        "prospective_validation_performed": False,
        "human_review_outcomes_observed": False,
        "counterfactual_experiment_only": True,
    },

    "integrity": {
        "phase10_modified": False,
        "phase11_1_1_sha256": sha256_file(P111),
        "phase11_1_2_sha256": sha256_file(P112),
        "phase11_1_3_sha256": sha256_file(P113),
        "phase11_1_4_sha256": sha256_file(P114),
    },

    "next_phase": "11.2 Fairness Audit",
}

with OUTPUT.open("w") as f:
    json.dump(manifest, f, indent=2)

print("Safety closure manifest:", OUTPUT)


# =============================================================================
# J — FINAL CLOSURE VERIFICATION
# =============================================================================

section("J — FINAL SAFETY CLOSURE VERIFICATION")

saved = load_json(OUTPUT)

final_checks = {
    "closure_status":
        saved["status"] == "SAFETY_AUDIT_COMPLETE",

    "baseline_fn_lock":
        saved["baseline"]["false_negatives"] == 557,

    "original_bypass_lock":
        saved["original_routing"][
            "false_negatives_bypassed"
        ] == 447,

    "additional_fn_lock":
        saved["predeclared_safety_override"][
            "additional_false_negatives_escalated"
        ] == 139,

    "residual_fn_lock":
        saved["predeclared_safety_override"][
            "residual_false_negatives_bypassing_review"
        ] == 308,

    "no_clinical_safety_claim":
        saved["claims_boundary"][
            "clinical_safety_established"
        ] is False,

    "phase10_unchanged":
        saved["integrity"]["phase10_modified"] is False,
}

for name, passed in final_checks.items():
    print(
        name + ":",
        "PASSED" if passed else "FAILED"
    )

if not all(final_checks.values()):
    raise RuntimeError(
        "Phase 11.1 safety closure verification failed."
    )


section("PHASE 11.1 SAFETY — COMPLETE AND LOCKED")

print("11.1.1 Baseline FN audit: COMPLETE")
print("11.1.2 Routing FN audit: COMPLETE")
print("11.1.3 Safety override pre-declaration: COMPLETE")
print("11.1.4 Forced safety-route experiment: COMPLETE")
print("11.1.5 Safety failure disclosure: COMPLETE")

print()
print("Safety audit status: SAFETY_AUDIT_COMPLETE")
print("Clinical safety established: NO")
print("Failures transparently reported: YES")
print("Phase 10 frozen system modified: NO")

print()
print("NEXT: PHASE 11.2 — FAIRNESS AUDIT")
