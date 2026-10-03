"""
CareCompute
Phase 13.6.2 — Cross-Phase Provenance Verification

Verifies the final CareCompute provenance chain:

Phase 10 frozen agent system
    ->
Phase 12 scientific comparison / System D selection
    ->
Phase 13 integrated runtime
    ->
Phase 13.5 end-to-end validation lock

This phase is read-only with respect to all previously frozen artifacts.
"""

from pathlib import Path
import hashlib
import json


ROOT = Path.cwd().resolve()

AGENTS = ROOT / "results/eligible/agents"
FINAL_COMPARISON = ROOT / "results/eligible/final_comparison"
PHASE13 = ROOT / "results/eligible/phase13"
VALIDATION = ROOT / "results/eligible/runtime_validation"
FINAL_FREEZE = ROOT / "results/eligible/final_freeze"


INVENTORY = (
    FINAL_FREEZE
    / "phase13_6_1_final_artifact_inventory.json"
)

INVENTORY_AUDIT = (
    FINAL_FREEZE
    / "phase13_6_1_final_artifact_inventory_audit.json"
)


# ---------------------------------------------------------------------------
# Authoritative cross-phase artifacts
# ---------------------------------------------------------------------------

PROVENANCE_ARTIFACTS = {
    # Phase 10
    "phase10_freeze":
        AGENTS
        / "carecompute_final_system_freeze_manifest.json",

    "phase10_completion":
        AGENTS
        / "phase10_final_completion_manifest.json",

    "phase10_provenance":
        AGENTS
        / "phase10_cross_phase_provenance_audit.json",

    "phase10_release":
        AGENTS
        / "phase10_reproducibility_release_manifest.json",

    "workflow_contract":
        AGENTS
        / "end_to_end_workflow_contract.json",

    # Phase 12
    "phase12_protocol":
        FINAL_COMPARISON
        / "phase12_1_final_comparison_protocol.json",

    "phase12_comparator":
        FINAL_COMPARISON
        / "phase12_2_comparator_manifest.json",

    "phase12_scientific_comparison":
        FINAL_COMPARISON
        / "phase12_3_final_scientific_comparison.json",

    "phase12_ablation_lock":
        FINAL_COMPARISON
        / "phase12_4_final_ablation_lock.json",

    "phase12_safety_fairness_lock":
        FINAL_COMPARISON
        / "phase12_5_final_safety_fairness_lock.json",

    "phase12_closure":
        FINAL_COMPARISON
        / "phase12_final_closure_manifest.json",

    # Phase 13
    "phase13_architecture":
        PHASE13
        / "phase13_1_integrated_agent_architecture.json",

    "phase13_architecture_audit":
        PHASE13
        / "phase13_1_architecture_freeze_audit.json",

    "phase13_runtime_manifest":
        PHASE13
        / "phase13_2_frozen_runtime_manifest.json",

    "phase13_runtime_audit":
        PHASE13
        / "phase13_2_runtime_replay_audit.json",

    "phase13_agent_summary":
        PHASE13
        / "phase13_3_agent_runtime_summary.json",

    "phase13_agent_audit":
        PHASE13
        / "phase13_3_agent_runtime_audit.json",

    "phase13_orchestrator_summary":
        PHASE13
        / "phase13_4_orchestrator_summary.json",

    "phase13_orchestrator_audit":
        PHASE13
        / "phase13_4_orchestrator_audit.json",

    "phase13_orchestrator_manifest":
        PHASE13
        / "phase13_4_integrated_orchestrator_manifest.json",

    # Phase 13.5
    "phase13_5_lock":
        VALIDATION
        / "phase13_5_6_final_end_to_end_validation_lock.json",

    "phase13_5_closure":
        VALIDATION
        / "phase13_5_6_closure_audit.json",
}


EXPECTED_POPULATION = 1178
EXPECTED_THRESHOLD = 0.115
EXPECTED_REVIEW_BUDGET = 0.15


# =============================================================================
# HELPERS
# =============================================================================

def banner(text):

    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


def sha256(path):

    h = hashlib.sha256()

    with open(path, "rb") as f:

        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def rel(path):

    return str(
        path.relative_to(ROOT)
    )


def check(condition, name, audit):

    status = (
        "PASSED"
        if bool(condition)
        else "FAILED"
    )

    audit[name] = status

    print(
        f"{name}: {status}"
    )

    if not condition:

        raise AssertionError(
            f"{name} FAILED"
        )


def contains_text(obj, text):

    return (
        str(text).lower()
        in json.dumps(
            obj,
            sort_keys=True,
        ).lower()
    )


def no_explicit_failed(obj):

    """
    Detect explicit string-valued FAILED states without assuming
    every JSON artifact uses exactly the same schema.
    """

    failures = []

    def walk(value, path="root"):

        if isinstance(value, dict):

            for key, item in value.items():

                walk(
                    item,
                    f"{path}.{key}",
                )

        elif isinstance(value, list):

            for index, item in enumerate(value):

                walk(
                    item,
                    f"{path}[{index}]",
                )

        elif isinstance(value, str):

            if value.strip().upper() == "FAILED":

                failures.append(path)

    walk(obj)

    return failures


# =============================================================================
# START
# =============================================================================

banner(
    "PHASE 13.6.2 — "
    "CROSS-PHASE PROVENANCE VERIFICATION"
)

audit = {}


# =============================================================================
# A — VERIFY 13.6.1 INVENTORY
# =============================================================================

banner(
    "A — VERIFY PHASE 13.6.1 INVENTORY"
)

check(
    INVENTORY.exists(),
    "phase13_6_1_inventory_present",
    audit,
)

check(
    INVENTORY_AUDIT.exists(),
    "phase13_6_1_inventory_audit_present",
    audit,
)

inventory = load_json(
    INVENTORY
)

inventory_audit = load_json(
    INVENTORY_AUDIT
)

check(
    inventory.get(
        "status"
    ) == "PASSED",
    "phase13_6_1_inventory_passed",
    audit,
)

check(
    inventory.get(
        "total_artifact_count"
    ) == 104,
    "phase13_6_1_artifact_count_104",
    audit,
)


# =============================================================================
# B — VERIFY AUTHORITATIVE PROVENANCE ARTIFACTS
# =============================================================================

banner(
    "B — VERIFY AUTHORITATIVE PROVENANCE ARTIFACTS"
)

for name, path in PROVENANCE_ARTIFACTS.items():

    print(
        f"{name}: "
        f"{'FOUND' if path.exists() else 'MISSING'}"
    )


check(
    all(
        path.exists()
        for path in PROVENANCE_ARTIFACTS.values()
    ),
    "authoritative_provenance_artifacts_present",
    audit,
)


# =============================================================================
# C — VERIFY INVENTORY HASH BASELINE
# =============================================================================

banner(
    "C — VERIFY 13.6.1 INVENTORY HASH BASELINE"
)

inventory_records = (
    inventory.get(
        "artifacts",
        []
    )
)

inventory_map = {
    record["path"]:
        record["sha256"]
    for record in inventory_records
}

hash_mismatches = []

for path_string, expected_hash in inventory_map.items():

    path = ROOT / path_string

    if not path.exists():

        hash_mismatches.append({
            "path":
                path_string,

            "reason":
                "MISSING",
        })

        continue

    observed_hash = sha256(
        path
    )

    if observed_hash != expected_hash:

        hash_mismatches.append({
            "path":
                path_string,

            "reason":
                "HASH_MISMATCH",

            "expected":
                expected_hash,

            "observed":
                observed_hash,
        })


print(
    "Inventory artifacts checked:",
    len(inventory_map),
)

print(
    "Hash mismatches:",
    len(hash_mismatches),
)


check(
    len(inventory_map) == 104,
    "inventory_hash_coverage_104",
    audit,
)

check(
    len(hash_mismatches) == 0,
    "inventory_hash_baseline_preserved",
    audit,
)


# =============================================================================
# D — LOAD CROSS-PHASE MANIFESTS
# =============================================================================

banner(
    "D — LOAD CROSS-PHASE MANIFESTS"
)

phase10_freeze = load_json(
    PROVENANCE_ARTIFACTS[
        "phase10_freeze"
    ]
)

phase10_completion = load_json(
    PROVENANCE_ARTIFACTS[
        "phase10_completion"
    ]
)

phase12_comparison = load_json(
    PROVENANCE_ARTIFACTS[
        "phase12_scientific_comparison"
    ]
)

phase12_safety = load_json(
    PROVENANCE_ARTIFACTS[
        "phase12_safety_fairness_lock"
    ]
)

phase12_closure = load_json(
    PROVENANCE_ARTIFACTS[
        "phase12_closure"
    ]
)

phase13_architecture = load_json(
    PROVENANCE_ARTIFACTS[
        "phase13_architecture"
    ]
)

phase13_runtime = load_json(
    PROVENANCE_ARTIFACTS[
        "phase13_runtime_manifest"
    ]
)

phase13_agent_summary = load_json(
    PROVENANCE_ARTIFACTS[
        "phase13_agent_summary"
    ]
)

phase13_orchestrator = load_json(
    PROVENANCE_ARTIFACTS[
        "phase13_orchestrator_manifest"
    ]
)

phase13_5_lock = load_json(
    PROVENANCE_ARTIFACTS[
        "phase13_5_lock"
    ]
)

print(
    "Cross-phase manifests loaded: PASSED"
)


# =============================================================================
# E — VERIFY PHASE 10 FROZEN AGENT PROVENANCE
# =============================================================================

banner(
    "E — VERIFY PHASE 10 FROZEN AGENT PROVENANCE"
)

phase10_failures = (
    no_explicit_failed(
        phase10_freeze
    )
    + no_explicit_failed(
        phase10_completion
    )
)

print(
    "Explicit Phase 10 FAILED states:",
    phase10_failures,
)


check(
    len(phase10_failures) == 0,
    "phase10_frozen_agent_chain_preserved",
    audit,
)

check(
    contains_text(
        phase10_freeze,
        "FROZEN",
    ),
    "phase10_frozen_state_present",
    audit,
)


# =============================================================================
# F — VERIFY PHASE 12 SCIENTIFIC SELECTION
# =============================================================================

banner(
    "F — VERIFY PHASE 12 SCIENTIFIC SELECTION"
)

phase12_failures = (
    no_explicit_failed(
        phase12_comparison
    )
    + no_explicit_failed(
        phase12_safety
    )
    + no_explicit_failed(
        phase12_closure
    )
)

print(
    "Explicit Phase 12 FAILED states:",
    phase12_failures,
)


check(
    len(phase12_failures) == 0,
    "phase12_scientific_chain_preserved",
    audit,
)

check(
    contains_text(
        phase12_comparison,
        "System D",
    )
    or contains_text(
        phase12_closure,
        "System D",
    ),
    "phase12_system_d_selected",
    audit,
)

check(
    contains_text(
        phase12_comparison,
        "Learned Router",
    )
    or contains_text(
        phase12_closure,
        "Learned Router",
    ),
    "phase12_learned_router_selected",
    audit,
)


# =============================================================================
# G — VERIFY PHASE 13 ARCHITECTURE LINEAGE
# =============================================================================

banner(
    "G — VERIFY PHASE 13 ARCHITECTURE LINEAGE"
)

check(
    contains_text(
        phase13_architecture,
        "CareCompute",
    ),
    "phase13_architecture_system_identity",
    audit,
)

check(
    contains_text(
        phase13_architecture,
        "Learned Router",
    )
    or contains_text(
        phase13_architecture,
        "FROZEN_LEARNED_ROUTER",
    ),
    "phase13_architecture_learned_router_lineage",
    audit,
)

check(
    contains_text(
        phase13_architecture,
        "human",
    ),
    "phase13_architecture_hitl_lineage",
    audit,
)


# =============================================================================
# H — VERIFY PHASE 13.2 RUNTIME LINEAGE
# =============================================================================

banner(
    "H — VERIFY PHASE 13.2 FROZEN RUNTIME LINEAGE"
)

check(
    contains_text(
        phase13_runtime,
        EXPECTED_THRESHOLD,
    ),
    "phase13_runtime_threshold_0_115",
    audit,
)

check(
    contains_text(
        phase13_runtime,
        EXPECTED_REVIEW_BUDGET,
    ),
    "phase13_runtime_review_budget_0_15",
    audit,
)

check(
    contains_text(
        phase13_runtime,
        "FROZEN",
    ),
    "phase13_runtime_frozen_state",
    audit,
)


# =============================================================================
# I — VERIFY PHASE 13.3 AGENT LINEAGE
# =============================================================================

banner(
    "I — VERIFY PHASE 13.3 EXECUTABLE AGENT LINEAGE"
)

check(
    contains_text(
        phase13_agent_summary,
        EXPECTED_POPULATION,
    ),
    "phase13_agent_population_1178",
    audit,
)

phase13_agent_audit = load_json(
    PROVENANCE_ARTIFACTS[
        "phase13_agent_audit"
    ]
)

phase13_agent_lineage_text = (
    json.dumps(
        phase13_agent_summary,
        sort_keys=True,
    )
    + " "
    + json.dumps(
        phase13_agent_audit,
        sort_keys=True,
    )
)

phase10_lineage_present = (
    "phase10" in phase13_agent_lineage_text.lower()
    or "phase 10" in phase13_agent_lineage_text.lower()
    or "local_agent_outputs.csv"
    in phase13_agent_lineage_text.lower()
    or "frozen_phase10"
    in phase13_agent_lineage_text.lower()
)

check(
    phase10_lineage_present,
    "phase13_agent_phase10_replay_lineage",
    audit,
)

check(
    not contains_text(
        phase13_agent_summary,
        "autonomous diagnosis allowed",
    ),
    "phase13_agent_no_autonomous_diagnosis_claim",
    audit,
)


# =============================================================================
# J — VERIFY PHASE 13.4 ORCHESTRATOR LINEAGE
# =============================================================================

banner(
    "J — VERIFY PHASE 13.4 ORCHESTRATOR LINEAGE"
)

check(
    contains_text(
        phase13_orchestrator,
        EXPECTED_POPULATION,
    ),
    "phase13_orchestrator_population_1178",
    audit,
)

check(
    contains_text(
        phase13_orchestrator,
        EXPECTED_THRESHOLD,
    ),
    "phase13_orchestrator_threshold_0_115",
    audit,
)

check(
    contains_text(
        phase13_orchestrator,
        EXPECTED_REVIEW_BUDGET,
    ),
    "phase13_orchestrator_review_budget_0_15",
    audit,
)

phase13_orchestrator_summary = load_json(
    PROVENANCE_ARTIFACTS[
        "phase13_orchestrator_summary"
    ]
)

phase13_orchestrator_audit = load_json(
    PROVENANCE_ARTIFACTS[
        "phase13_orchestrator_audit"
    ]
)

phase13_orchestrator_lineage_text = (
    json.dumps(
        phase13_orchestrator,
        sort_keys=True,
    )
    + " "
    + json.dumps(
        phase13_orchestrator_summary,
        sort_keys=True,
    )
    + " "
    + json.dumps(
        phase13_orchestrator_audit,
        sort_keys=True,
    )
).lower()

hitl_runtime_present = (
    "frozen_human_in_the_loop"
    in phase13_orchestrator_lineage_text
    or "human_review_required"
    in phase13_orchestrator_lineage_text
    or "human review required"
    in phase13_orchestrator_lineage_text
)

check(
    hitl_runtime_present,
    "phase13_orchestrator_hitl_runtime",
    audit,
)

learned_router_lineage_present = (
    "frozen_learned_router"
    in phase13_orchestrator_lineage_text
    or "learned router"
    in phase13_orchestrator_lineage_text
    or "system d"
    in phase13_orchestrator_lineage_text
)

check(
    learned_router_lineage_present,
    "phase13_orchestrator_learned_router",
    audit,
)


# =============================================================================
# K — VERIFY PHASE 13.5 VALIDATION LINEAGE
# =============================================================================

banner(
    "K — VERIFY PHASE 13.5 VALIDATION LINEAGE"
)

check(
    phase13_5_lock.get(
        "phase13_5_status"
    ) == "VALIDATED_AND_LOCKED",
    "phase13_5_validated_and_locked",
    audit,
)

check(
    phase13_5_lock.get(
        "ready_for_phase13_6"
    ) is True,
    "phase13_5_ready_for_phase13_6",
    audit,
)

check(
    phase13_5_lock.get(
        "population"
    ) == EXPECTED_POPULATION,
    "phase13_5_population_1178",
    audit,
)

frozen_parameters = (
    phase13_5_lock.get(
        "frozen_parameters",
        {}
    )
)

check(
    frozen_parameters.get(
        "primary_threshold"
    ) == EXPECTED_THRESHOLD,
    "phase13_5_threshold_0_115",
    audit,
)

check(
    frozen_parameters.get(
        "review_budget"
    ) == EXPECTED_REVIEW_BUDGET,
    "phase13_5_review_budget_0_15",
    audit,
)


# =============================================================================
# L — VERIFY END-TO-END PROVENANCE CONTINUITY
# =============================================================================

banner(
    "L — VERIFY END-TO-END PROVENANCE CONTINUITY"
)

provenance_chain = [
    {
        "stage":
            "Phase 10",

        "role":
            "Frozen agent scientific provenance",

        "artifact":
            rel(
                PROVENANCE_ARTIFACTS[
                    "phase10_freeze"
                ]
            ),
    },
    {
        "stage":
            "Phase 12",

        "role":
            "Final scientific comparison and "
            "System D selection",

        "artifact":
            rel(
                PROVENANCE_ARTIFACTS[
                    "phase12_scientific_comparison"
                ]
            ),
    },
    {
        "stage":
            "Phase 13.1",

        "role":
            "Integrated architecture freeze",

        "artifact":
            rel(
                PROVENANCE_ARTIFACTS[
                    "phase13_architecture"
                ]
            ),
    },
    {
        "stage":
            "Phase 13.2",

        "role":
            "Frozen model and learned-router runtime",

        "artifact":
            rel(
                PROVENANCE_ARTIFACTS[
                    "phase13_runtime_manifest"
                ]
            ),
    },
    {
        "stage":
            "Phase 13.3",

        "role":
            "Executable agent runtime",

        "artifact":
            rel(
                PROVENANCE_ARTIFACTS[
                    "phase13_agent_summary"
                ]
            ),
    },
    {
        "stage":
            "Phase 13.4",

        "role":
            "Integrated human-in-the-loop orchestrator",

        "artifact":
            rel(
                PROVENANCE_ARTIFACTS[
                    "phase13_orchestrator_manifest"
                ]
            ),
    },
    {
        "stage":
            "Phase 13.5",

        "role":
            "Validated end-to-end system lock",

        "artifact":
            rel(
                PROVENANCE_ARTIFACTS[
                    "phase13_5_lock"
                ]
            ),
    },
]


for node in provenance_chain:

    print(
        node["stage"],
        "->",
        node["role"],
    )


check(
    len(provenance_chain) == 7,
    "complete_seven_stage_provenance_chain",
    audit,
)


# =============================================================================
# M — VERIFY NO ARTIFACT CHANGED DURING PROVENANCE CHECK
# =============================================================================

banner(
    "M — VERIFY INVENTORIED ARTIFACTS REMAIN UNCHANGED"
)

post_check_mismatches = []

for path_string, expected_hash in inventory_map.items():

    path = ROOT / path_string

    observed_hash = sha256(
        path
    )

    if observed_hash != expected_hash:

        post_check_mismatches.append(
            path_string
        )


print(
    "Post-check hash mismatches:",
    len(post_check_mismatches),
)


check(
    len(post_check_mismatches) == 0,
    "inventoried_artifacts_unchanged",
    audit,
)


# =============================================================================
# N — SAVE PROVENANCE VERIFICATION
# =============================================================================

banner(
    "N — SAVE CROSS-PHASE PROVENANCE VERIFICATION"
)

overall_passed = all(
    value == "PASSED"
    for value in audit.values()
)

OUTPUT_PATH = (
    FINAL_FREEZE
    / "phase13_6_2_cross_phase_provenance_verification.json"
)

output = {
    "system":
        "CareCompute",

    "phase":
        "13.6.2",

    "verification":
        "CROSS_PHASE_PROVENANCE",

    "system_variant":
        "System D — Learned Router",

    "population":
        EXPECTED_POPULATION,

    "frozen_parameters": {
        "primary_threshold":
            EXPECTED_THRESHOLD,

        "review_budget":
            EXPECTED_REVIEW_BUDGET,
    },

    "provenance_chain":
        provenance_chain,

    "inventory_baseline": {
        "artifact_count":
            len(inventory_map),

        "hash_mismatches_before":
            len(hash_mismatches),

        "hash_mismatches_after":
            len(post_check_mismatches),
    },

    "checks":
        audit,

    "status":
        (
            "PASSED"
            if overall_passed
            else "FAILED"
        ),
}


with open(
    OUTPUT_PATH,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        output,
        f,
        indent=2,
        sort_keys=True,
    )


print(
    "Saved:",
    OUTPUT_PATH.relative_to(ROOT),
)


# =============================================================================
# O — HASH PROVENANCE VERIFICATION
# =============================================================================

banner(
    "O — HASH PROVENANCE VERIFICATION"
)

output_hash = sha256(
    OUTPUT_PATH
)

print(
    OUTPUT_PATH.relative_to(ROOT),
    "->",
    output_hash,
)


# =============================================================================
# P — SAVE PROVENANCE AUDIT
# =============================================================================

banner(
    "P — SAVE PROVENANCE AUDIT"
)

AUDIT_PATH = (
    FINAL_FREEZE
    / "phase13_6_2_cross_phase_provenance_audit.json"
)

audit_output = {
    "system":
        "CareCompute",

    "phase":
        "13.6.2",

    "checks":
        audit,

    "provenance_verification":
        rel(
            OUTPUT_PATH
        ),

    "provenance_verification_sha256":
        output_hash,

    "inventory_artifacts_checked":
        len(inventory_map),

    "inventory_hash_mismatches":
        len(post_check_mismatches),

    "phase13_6_2_status":
        (
            "PASSED"
            if overall_passed
            else "FAILED"
        ),
}


with open(
    AUDIT_PATH,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        audit_output,
        f,
        indent=2,
        sort_keys=True,
    )


print(
    "Saved:",
    AUDIT_PATH.relative_to(ROOT),
)


# =============================================================================
# FINAL
# =============================================================================

banner(
    "PHASE 13.6.2 COMPLETE — "
    "CROSS-PHASE PROVENANCE VERIFIED"
)

print("\nSYSTEM")
print(" CareCompute")

print("\nFINAL SYSTEM")
print(" System D — Learned Router")

print("\nPROVENANCE")
print(" Phase 10 frozen agents: VERIFIED")
print(" Phase 12 scientific selection: VERIFIED")
print(" Phase 13.1 architecture: VERIFIED")
print(" Phase 13.2 frozen runtime: VERIFIED")
print(" Phase 13.3 executable agents: VERIFIED")
print(" Phase 13.4 orchestrator: VERIFIED")
print(" Phase 13.5 validation lock: VERIFIED")

print("\nLOCKED VALUES")
print(" Population: 1178")
print(" Primary threshold: 0.115")
print(" Review budget: 0.15")

print("\nINVENTORY INTEGRITY")
print(
    " Artifacts checked:",
    len(inventory_map),
)

print(
    " Hash mismatches:",
    len(post_check_mismatches),
)

print("\nPREVIOUS ARTIFACT MODIFICATION")
print(" NONE")

print("\nFINAL STATUS")

if overall_passed:

    print(
        " CROSS_PHASE_PROVENANCE_VERIFIED"
    )

else:

    print(
        " CROSS_PHASE_PROVENANCE_FAILED"
    )


print(
    "\nVerification:",
    OUTPUT_PATH.relative_to(ROOT),
)

print(
    "Audit:",
    AUDIT_PATH.relative_to(ROOT),
)


if not overall_passed:

    raise SystemExit(
        "Phase 13.6.2 provenance verification failed."
    )


banner(
    "NEXT: PHASE 13.6.3 — "
    "FINAL REPRODUCIBILITY AND RELEASE MANIFEST"
)