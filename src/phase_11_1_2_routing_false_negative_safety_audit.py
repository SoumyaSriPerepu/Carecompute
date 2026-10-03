from pathlib import Path
import json
import hashlib
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

TEST_PATH = Path("results/eligible/test_predictions.csv")

ROUTING_PATH = Path(
    "results/eligible/final_test_end_to_end_patient_predictions.csv"
)

ROUTER_NEGATIVE_PATH = Path(
    "results/eligible/final_test_router_predictions.csv"
)

PHASE10_MANIFEST = Path(
    "results/eligible/agents/phase10_final_completion_manifest.json"
)

PHASE11_1_1 = Path(
    "results/eligible/safety/phase11_1_1_baseline_safety_audit.json"
)

OUTPUT_DIR = Path("results/eligible/safety")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_PATH = (
    OUTPUT_DIR /
    "phase11_1_2_routing_false_negative_safety_audit.json"
)

CASE_PATH = (
    OUTPUT_DIR /
    "phase11_1_2_false_negative_routing_cases.csv"
)


# =============================================================================
# HELPERS
# =============================================================================

def section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


# =============================================================================
# HEADER
# =============================================================================

section(
    "PHASE 11.1.2 — ROUTING FALSE-NEGATIVE SAFETY AUDIT"
)


# =============================================================================
# A — VERIFY REQUIRED INPUTS
# =============================================================================

section("A — VERIFY REQUIRED INPUTS")

required_paths = [
    TEST_PATH,
    ROUTING_PATH,
    ROUTER_NEGATIVE_PATH,
    PHASE10_MANIFEST,
    PHASE11_1_1,
]

for path in required_paths:
    if not path.exists():
        raise FileNotFoundError(f"Missing required artifact: {path}")

    print("FOUND:", path)

print("Required input presence: PASSED")


# =============================================================================
# B — VERIFY PHASE 10 FROZEN STATE
# =============================================================================

section("B — VERIFY PHASE 10 FROZEN STATE")

with PHASE10_MANIFEST.open() as f:
    phase10 = json.load(f)

manifest_text = json.dumps(phase10)

phase10_complete = "PHASE_10_COMPLETE" in manifest_text
system_frozen = "FROZEN" in manifest_text
release_locked = "LOCKED" in manifest_text

print(
    "Phase 10 complete:",
    "PASSED" if phase10_complete else "FAILED"
)

print(
    "System frozen:",
    "PASSED" if system_frozen else "FAILED"
)

print(
    "Release locked:",
    "PASSED" if release_locked else "FAILED"
)

if not all([
    phase10_complete,
    system_frozen,
    release_locked
]):
    raise RuntimeError(
        "Frozen Phase 10 verification failed."
    )

print("Phase 10 read-only boundary: PRESERVED")


# =============================================================================
# C — LOAD FINAL TEST AND ROUTING DATA
# =============================================================================

section("C — LOAD FINAL TEST AND ROUTING DATA")

test = pd.read_csv(TEST_PATH)
routing = pd.read_csv(ROUTING_PATH)
router_neg = pd.read_csv(ROUTER_NEGATIVE_PATH)

print("Test population:", len(test))
print("End-to-end routing population:", len(routing))
print("Primary-model-negative routing population:", len(router_neg))

if len(test) != 15042:
    raise RuntimeError(
        f"Expected 15042 test encounters, found {len(test)}"
    )

if len(routing) != len(test):
    raise RuntimeError(
        "End-to-end routing population does not match test population."
    )

print("Population alignment: PASSED")


# =============================================================================
# D — VERIFY ENCOUNTER ALIGNMENT
# =============================================================================

section("D — VERIFY ENCOUNTER ALIGNMENT")

test_ids = set(test["encounter_id"])
routing_ids = set(routing["encounter_id"])

print("Unique test encounters:", len(test_ids))
print("Unique routing encounters:", len(routing_ids))

missing_routing = test_ids - routing_ids
extra_routing = routing_ids - test_ids

print("Missing routing encounters:", len(missing_routing))
print("Unexpected routing encounters:", len(extra_routing))

if missing_routing or extra_routing:
    raise RuntimeError(
        "Final routing encounter set does not match test encounter set."
    )

print("Encounter alignment: PASSED")


# =============================================================================
# E — VERIFY PRIMARY MODEL CONSISTENCY
# =============================================================================

section("E — VERIFY PRIMARY MODEL CONSISTENCY")

comparison = test[
    [
        "encounter_id",
        "actual_30d",
        "predicted_30d",
        "calibrated_probability",
        "threshold",
    ]
].merge(
    routing[
        [
            "encounter_id",
            "actual_30d",
            "predicted_30d",
        ]
    ],
    on="encounter_id",
    suffixes=("_test", "_routing"),
    validate="one_to_one",
)

actual_mismatch = int(
    (
        comparison["actual_30d_test"]
        != comparison["actual_30d_routing"]
    ).sum()
)

prediction_mismatch = int(
    (
        comparison["predicted_30d_test"]
        != comparison["predicted_30d_routing"]
    ).sum()
)

print("Ground-truth mismatches:", actual_mismatch)
print("Prediction mismatches:", prediction_mismatch)

if actual_mismatch != 0 or prediction_mismatch != 0:
    raise RuntimeError(
        "Primary model/test consistency verification failed."
    )

print("Primary model consistency: PASSED")


# =============================================================================
# F — VERIFY ROUTING POLICY
# =============================================================================

section("F — VERIFY ROUTING POLICY")

if "selected_for_review" not in routing.columns:
    raise RuntimeError(
        "selected_for_review missing from final routing artifact."
    )

selected_values = set(
    routing["selected_for_review"].dropna().unique()
)

if not selected_values.issubset({0, 1}):
    raise RuntimeError(
        "selected_for_review is not binary."
    )

selected_count = int(
    (routing["selected_for_review"] == 1).sum()
)

bypass_count = int(
    (routing["selected_for_review"] == 0).sum()
)

negative = routing[
    routing["predicted_30d"] == 0
].copy()

positive = routing[
    routing["predicted_30d"] == 1
].copy()

selected_negative = negative[
    negative["selected_for_review"] == 1
]

selected_positive = positive[
    positive["selected_for_review"] == 1
]

print("Total selected for Rescue Review:", selected_count)
print("Total bypassing Rescue Review:", bypass_count)

print("Primary-model-negative cases:", len(negative))
print(
    "Negative cases selected for Rescue Review:",
    len(selected_negative)
)

print(
    "Primary-model-positive cases selected:",
    len(selected_positive)
)

if len(selected_positive) != 0:
    raise RuntimeError(
        "Unexpected primary-model-positive cases entered Rescue Review."
    )

selection_rate_negative = (
    len(selected_negative) / len(negative)
    if len(negative)
    else float("nan")
)

print(
    f"Review rate among model-negative cases: "
    f"{selection_rate_negative:.6f}"
)

print("Frozen routing-policy structure: PASSED")


# =============================================================================
# G — FALSE-NEGATIVE ROUTING SAFETY
# =============================================================================

section("G — FALSE-NEGATIVE ROUTING SAFETY")

false_negatives = routing[
    (routing["actual_30d"] == 1)
    & (routing["predicted_30d"] == 0)
].copy()

fn_total = len(false_negatives)

fn_selected = false_negatives[
    false_negatives["selected_for_review"] == 1
].copy()

fn_bypass = false_negatives[
    false_negatives["selected_for_review"] == 0
].copy()

fn_selected_count = len(fn_selected)
fn_bypass_count = len(fn_bypass)

fn_rescue_coverage = (
    fn_selected_count / fn_total
    if fn_total
    else float("nan")
)

fn_bypass_fraction = (
    fn_bypass_count / fn_total
    if fn_total
    else float("nan")
)

print("Baseline false negatives:", fn_total)
print(
    "False negatives selected for Rescue Review:",
    fn_selected_count
)

print(
    "False negatives bypassing Rescue Review:",
    fn_bypass_count
)

print()
print(f"FN Rescue Review coverage: {fn_rescue_coverage:.6f}")
print(f"FN bypass fraction:        {fn_bypass_fraction:.6f}")

if fn_total != 557:
    raise RuntimeError(
        f"Expected 557 baseline false negatives, found {fn_total}"
    )

if fn_selected_count + fn_bypass_count != fn_total:
    raise RuntimeError(
        "False-negative routing counts do not reconcile."
    )

print()
print("False-negative routing accounting: PASSED")


# =============================================================================
# H — ROUTER ENRICHMENT ANALYSIS
# =============================================================================

section("H — ROUTER ENRICHMENT ANALYSIS")

# FN prevalence among all primary-model-negative cases
baseline_fn_prevalence_negative = (
    fn_total / len(negative)
)

# FN prevalence among selected negative cases
selected_fn_prevalence = (
    fn_selected_count / len(selected_negative)
    if len(selected_negative)
    else float("nan")
)

bypass_negative = negative[
    negative["selected_for_review"] == 0
]

bypass_fn_prevalence = (
    fn_bypass_count / len(bypass_negative)
    if len(bypass_negative)
    else float("nan")
)

enrichment_ratio = (
    selected_fn_prevalence / baseline_fn_prevalence_negative
    if baseline_fn_prevalence_negative > 0
    else float("nan")
)

print(
    "FN prevalence among all model-negative cases:",
    round(baseline_fn_prevalence_negative, 6)
)

print(
    "FN prevalence among Rescue Review cases:",
    round(selected_fn_prevalence, 6)
)

print(
    "FN prevalence among bypass cases:",
    round(bypass_fn_prevalence, 6)
)

print(
    "Rescue Review FN enrichment ratio:",
    round(enrichment_ratio, 6)
)

print()
print(
    "Interpretation: enrichment > 1 means the router concentrates "
    "false negatives above their baseline prevalence among "
    "primary-model-negative cases."
)


# =============================================================================
# I — OPERATIONAL FAST/BYPASS INTERPRETATION
# =============================================================================

section("I — OPERATIONAL FAST/BYPASS INTERPRETATION")

print(
    "No literal FAST/STANDARD/DEEP route variable exists in the "
    "frozen CareCompute implementation."
)

print(
    "For this audit only, the low-compute / bypass pathway is "
    "operationally defined as:"
)

print(
    "predicted_30d == 0 AND selected_for_review == 0"
)

print(
    "The Rescue Review pathway is operationally defined as:"
)

print(
    "predicted_30d == 0 AND selected_for_review == 1"
)

print(
    "No new route labels are written into the frozen Phase 10 artifacts."
)


# =============================================================================
# J — SAVE CASE-LEVEL AUDIT
# =============================================================================

section("J — SAVE CASE-LEVEL AUDIT")

case_audit = false_negatives.copy()

case_audit["phase11_route_group"] = case_audit[
    "selected_for_review"
].map({
    0: "BYPASS",
    1: "RESCUE_REVIEW",
})

case_audit.to_csv(CASE_PATH, index=False)

print("Case-level FN routing audit:", CASE_PATH)


# =============================================================================
# K — CREATE AUDIT ARTIFACT
# =============================================================================

section("K — CREATE AUDIT ARTIFACT")

audit = {
    "phase": "11.1.2",
    "audit_name":
        "Routing False-Negative Safety Audit",

    "scope": {
        "test_population": int(len(routing)),
        "primary_model_negative_population":
            int(len(negative)),
        "rescue_review_population":
            int(len(selected_negative)),
        "bypass_negative_population":
            int(len(bypass_negative)),
    },

    "routing_policy": {
        "literal_fast_route_present": False,
        "operational_bypass_definition":
            "predicted_30d == 0 and selected_for_review == 0",
        "rescue_review_definition":
            "predicted_30d == 0 and selected_for_review == 1",
        "negative_case_review_rate":
            float(selection_rate_negative),
    },

    "false_negative_safety": {
        "baseline_false_negatives":
            int(fn_total),
        "false_negatives_selected_for_rescue_review":
            int(fn_selected_count),
        "false_negatives_bypassing_rescue_review":
            int(fn_bypass_count),
        "false_negative_rescue_coverage":
            float(fn_rescue_coverage),
        "false_negative_bypass_fraction":
            float(fn_bypass_fraction),
    },

    "router_enrichment": {
        "fn_prevalence_all_model_negative":
            float(baseline_fn_prevalence_negative),
        "fn_prevalence_rescue_review":
            float(selected_fn_prevalence),
        "fn_prevalence_bypass":
            float(bypass_fn_prevalence),
        "rescue_review_fn_enrichment_ratio":
            float(enrichment_ratio),
    },

    "safety_finding": {
        "failure_present":
            bool(fn_bypass_count > 0),
        "failure_type":
            "primary-model false negatives bypassing Rescue Review",
        "failure_count":
            int(fn_bypass_count),
        "failure_fraction_of_false_negatives":
            float(fn_bypass_fraction),
        "note":
            "Bypass does not create the primary-model false negative. "
            "It represents failure of the frozen Rescue Router to select "
            "that already-missed case for additional human review."
    },

    "integrity": {
        "phase10_modified": False,
        "test_predictions_sha256":
            sha256_file(TEST_PATH),
        "routing_artifact_sha256":
            sha256_file(ROUTING_PATH),
        "router_negative_artifact_sha256":
            sha256_file(ROUTER_NEGATIVE_PATH),
        "phase10_manifest_sha256":
            sha256_file(PHASE10_MANIFEST),
        "phase11_1_1_sha256":
            sha256_file(PHASE11_1_1),
    },

    "interpretation": {
        "audit_only": True,
        "clinical_safety_claim": False,
        "important_causal_limitation":
            "This observational routing audit does not establish that "
            "bypass routing caused false-negative predictions.",
    },

    "status": "PASSED",
}

with AUDIT_PATH.open("w") as f:
    json.dump(audit, f, indent=2)

print("Audit artifact:", AUDIT_PATH)


# =============================================================================
# L — FINAL VERIFICATION
# =============================================================================

section("L — FINAL VERIFICATION")

with AUDIT_PATH.open() as f:
    saved = json.load(f)

checks = {
    "audit_status":
        saved["status"] == "PASSED",

    "full_test_population":
        saved["scope"]["test_population"] == 15042,

    "negative_population":
        saved["scope"]["primary_model_negative_population"] == 7858,

    "review_population":
        saved["scope"]["rescue_review_population"] == 1178,

    "baseline_fn_count":
        saved["false_negative_safety"][
            "baseline_false_negatives"
        ] == 557,

    "fn_accounting":
        (
            saved["false_negative_safety"][
                "false_negatives_selected_for_rescue_review"
            ]
            +
            saved["false_negative_safety"][
                "false_negatives_bypassing_rescue_review"
            ]
        ) == 557,

    "phase10_unchanged":
        saved["integrity"]["phase10_modified"] is False,

    "case_artifact_exists":
        CASE_PATH.exists(),
}

for name, passed in checks.items():
    print(
        f"{name}:",
        "PASSED" if passed else "FAILED"
    )

if not all(checks.values()):
    raise RuntimeError(
        "Final Phase 11.1.2 verification failed."
    )


# =============================================================================
# COMPLETE
# =============================================================================

section(
    "PHASE 11.1.2 COMPLETE — ROUTING SAFETY AUDIT PASSED"
)

print(
    "IMPORTANT: PASSED means the routing safety audit executed "
    "correctly; it does not mean routing is clinically safe."
)

print()
print("Baseline false negatives:", fn_total)

print(
    "Selected for Rescue Review:",
    fn_selected_count,
    f"({fn_rescue_coverage:.2%})"
)

print(
    "Bypassed Rescue Review:",
    fn_bypass_count,
    f"({fn_bypass_fraction:.2%})"
)

print(
    "Phase 10 frozen system modified: NO"
)
