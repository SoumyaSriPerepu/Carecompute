"""
CareCompute
Phase 13.6.1 — Final Artifact Inventory

Creates the authoritative inventory of the pre-13.6 CareCompute release.

This phase is read-only with respect to all previously frozen scientific,
runtime, agent, comparison, and validation artifacts.
"""

from pathlib import Path
import csv
import hashlib
import json


ROOT = Path.cwd().resolve()

AGENTS = ROOT / "results/eligible/agents"
FINAL_COMPARISON = ROOT / "results/eligible/final_comparison"
PHASE13 = ROOT / "results/eligible/phase13"
VALIDATION = ROOT / "results/eligible/runtime_validation"

FINAL_FREEZE = ROOT / "results/eligible/final_freeze"
FINAL_FREEZE.mkdir(parents=True, exist_ok=True)


EXPECTED_COUNTS = {
    "SCIENTIFIC_PROVENANCE": 41,
    "SCIENTIFIC_EVALUATION": 20,
    "INTEGRATED_RUNTIME": 20,
    "VALIDATION_EVIDENCE": 13,
    "EXECUTABLE_SOURCE": 10,
}

EXPECTED_RESULT_ARTIFACTS = 94
EXPECTED_SOURCE_ARTIFACTS = 10
EXPECTED_TOTAL = 104


SOURCE_FILES = [
    Path(
        "src/evaluation/"
        "phase13_1_freeze_integrated_agent_architecture.py"
    ),
    Path(
        "src/evaluation/"
        "phase13_2_frozen_model_routing_runtime.py"
    ),
    Path(
        "src/evaluation/"
        "phase13_3_executable_agent_runtime.py"
    ),
    Path(
        "src/evaluation/"
        "phase13_4_integrated_agent_orchestrator.py"
    ),
    Path(
        "src/agents/"
        "phase13_5_1_end_to_end_execution_test.py"
    ),
    Path(
        "src/agents/"
        "phase13_5_2_cross_component_contract_validation.py"
    ),
    Path(
        "src/agents/"
        "phase13_5_3_safety_hitl_validation.py"
    ),
    Path(
        "src/agents/"
        "phase13_5_4_determinism_replay_validation.py"
    ),
    Path(
        "src/agents/"
        "phase13_5_5_failure_edge_case_validation.py"
    ),
    Path(
        "src/agents/"
        "phase13_5_6_final_end_to_end_validation_lock.py"
    ),
]


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


def relative(path):

    return str(
        path.relative_to(ROOT)
    )


def files_in(directory):

    return sorted(
        p
        for p in directory.rglob("*")
        if p.is_file()
    )


def classify_role(category, path):

    name = path.name.lower()

    if category == "SCIENTIFIC_PROVENANCE":

        if "freeze" in name:
            return "FROZEN_AGENT_PROVENANCE"

        if "audit" in name:
            return "AGENT_AUDIT_EVIDENCE"

        if "contract" in name:
            return "AGENT_CONTRACT"

        if "policy" in name:
            return "AGENT_POLICY"

        if "sample" in name:
            return "REFERENCE_SAMPLE"

        if "summary" in name:
            return "AGENT_SUMMARY"

        return "AGENT_SCIENTIFIC_ARTIFACT"

    if category == "SCIENTIFIC_EVALUATION":

        if "comparison" in name:
            return "SYSTEM_COMPARISON"

        if "ablation" in name:
            return "ABLATION_EVIDENCE"

        if "fairness" in name:
            return "FAIRNESS_EVIDENCE"

        if "protocol" in name:
            return "EVALUATION_PROTOCOL"

        if "closure" in name:
            return "SCIENTIFIC_CLOSURE"

        return "SCIENTIFIC_EVALUATION_ARTIFACT"

    if category == "INTEGRATED_RUNTIME":

        if "architecture" in name:
            return "INTEGRATED_ARCHITECTURE"

        if "runtime" in name:
            return "FROZEN_RUNTIME"

        if "context" in name:
            return "PATIENT_CONTEXT"

        if "rescue" in name:
            return "RESCUE_REVIEW_OUTPUT"

        if "explanation" in name:
            return "EXPLANATION_OUTPUT"

        if "packet" in name:
            return "HUMAN_REVIEW_PACKET"

        if "fairness" in name:
            return "RUNTIME_FAIRNESS_MONITOR"

        if "orchestrator" in name:
            return "INTEGRATED_ORCHESTRATOR"

        if "audit" in name:
            return "RUNTIME_AUDIT"

        return "INTEGRATED_RUNTIME_ARTIFACT"

    if category == "VALIDATION_EVIDENCE":

        if "lock" in name:
            return "VALIDATION_LOCK"

        if "audit" in name:
            return "VALIDATION_AUDIT"

        if "mismatch" in name:
            return "CONTRACT_MISMATCH_EVIDENCE"

        if "violation" in name:
            return "SAFETY_VIOLATION_EVIDENCE"

        if "replay" in name:
            return "DETERMINISM_REPLAY_EVIDENCE"

        if "edge_case" in name:
            return "FAILURE_TEST_EVIDENCE"

        if "summary" in name:
            return "VALIDATION_SUMMARY"

        return "VALIDATION_ARTIFACT"

    if category == "EXECUTABLE_SOURCE":

        if "phase13_1" in name:
            return "ARCHITECTURE_FREEZE_SOURCE"

        if "phase13_2" in name:
            return "MODEL_ROUTER_RUNTIME_SOURCE"

        if "phase13_3" in name:
            return "EXECUTABLE_AGENT_SOURCE"

        if "phase13_4" in name:
            return "ORCHESTRATOR_SOURCE"

        if "phase13_5" in name:
            return "VALIDATION_SOURCE"

        return "EXECUTABLE_SOURCE"

    return "UNCLASSIFIED"


def make_record(category, path):

    return {
        "category": category,
        "role": classify_role(
            category,
            path,
        ),
        "path": relative(path),
        "filename": path.name,
        "extension": (
            path.suffix.lower()
            if path.suffix
            else ""
        ),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


# =============================================================================
# START
# =============================================================================

banner(
    "PHASE 13.6.1 — FINAL ARTIFACT INVENTORY"
)

audit = {}
records = []


# =============================================================================
# A — VERIFY RELEASE DIRECTORIES
# =============================================================================

banner("A — VERIFY RELEASE DIRECTORIES")

directories = {
    "SCIENTIFIC_PROVENANCE":
        AGENTS,

    "SCIENTIFIC_EVALUATION":
        FINAL_COMPARISON,

    "INTEGRATED_RUNTIME":
        PHASE13,

    "VALIDATION_EVIDENCE":
        VALIDATION,
}


for category, directory in directories.items():

    status = (
        "FOUND"
        if directory.exists()
        else "MISSING"
    )

    print(
        f"{category}: "
        f"{directory.relative_to(ROOT)} "
        f"-> {status}"
    )

    if not directory.exists():

        raise FileNotFoundError(
            directory
        )


audit[
    "release_directories_present"
] = "PASSED"


# =============================================================================
# B — INVENTORY RESULT ARTIFACTS
# =============================================================================

banner("B — INVENTORY RESULT ARTIFACTS")

for category, directory in directories.items():

    category_files = files_in(
        directory
    )

    print(
        f"{category}: "
        f"{len(category_files)}"
    )

    for path in category_files:

        records.append(
            make_record(
                category,
                path,
            )
        )


# =============================================================================
# C — VERIFY RESULT COUNTS
# =============================================================================

banner("C — VERIFY RESULT ARTIFACT COUNTS")

for category in [
    "SCIENTIFIC_PROVENANCE",
    "SCIENTIFIC_EVALUATION",
    "INTEGRATED_RUNTIME",
    "VALIDATION_EVIDENCE",
]:

    observed = sum(
        1
        for record in records
        if record["category"]
        == category
    )

    expected = EXPECTED_COUNTS[
        category
    ]

    print(
        f"{category}: "
        f"observed={observed} "
        f"expected={expected}"
    )

    if observed != expected:

        raise AssertionError(
            f"{category} artifact count "
            f"changed: expected "
            f"{expected}, observed "
            f"{observed}"
        )


result_count = len(records)

print(
    "\nTotal result artifacts:",
    result_count,
)

if result_count != EXPECTED_RESULT_ARTIFACTS:

    raise AssertionError(
        "Expected "
        f"{EXPECTED_RESULT_ARTIFACTS} "
        "result artifacts, observed "
        f"{result_count}."
    )


audit[
    "result_artifact_counts"
] = "PASSED"


# =============================================================================
# D — VERIFY EXECUTABLE SOURCE
# =============================================================================

banner("D — VERIFY EXECUTABLE SOURCE")

for relative_path in SOURCE_FILES:

    path = ROOT / relative_path

    status = (
        "FOUND"
        if path.exists()
        else "MISSING"
    )

    print(
        f"{relative_path}: {status}"
    )

    if not path.exists():

        raise FileNotFoundError(
            path
        )

    records.append(
        make_record(
            "EXECUTABLE_SOURCE",
            path,
        )
    )


source_count = sum(
    1
    for record in records
    if record["category"]
    == "EXECUTABLE_SOURCE"
)

print(
    "\nExecutable source files:",
    source_count,
)

if source_count != EXPECTED_SOURCE_ARTIFACTS:

    raise AssertionError(
        "Executable source count mismatch."
    )


audit[
    "executable_source_inventory"
] = "PASSED"


# =============================================================================
# E — VERIFY GLOBAL RELEASE COUNT
# =============================================================================

banner("E — VERIFY GLOBAL RELEASE COUNT")

print(
    "Result artifacts:",
    result_count,
)

print(
    "Source artifacts:",
    source_count,
)

print(
    "Total pre-13.6 release artifacts:",
    len(records),
)

if len(records) != EXPECTED_TOTAL:

    raise AssertionError(
        f"Expected {EXPECTED_TOTAL} "
        f"release artifacts, "
        f"observed {len(records)}."
    )


audit[
    "global_release_count"
] = "PASSED"


# =============================================================================
# F — VERIFY UNIQUE PATHS
# =============================================================================

banner("F — VERIFY UNIQUE ARTIFACT PATHS")

paths = [
    record["path"]
    for record in records
]

unique_paths = set(
    paths
)

print(
    "Inventory rows:",
    len(paths),
)

print(
    "Unique paths:",
    len(unique_paths),
)

if len(paths) != len(unique_paths):

    duplicates = sorted({
        path
        for path in paths
        if paths.count(path) > 1
    })

    print(
        "Duplicate paths:",
        duplicates,
    )

    raise AssertionError(
        "Duplicate artifacts detected."
    )


audit[
    "unique_artifact_paths"
] = "PASSED"


# =============================================================================
# G — VERIFY HASH COMPLETENESS
# =============================================================================

banner("G — VERIFY SHA-256 COMPLETENESS")

bad_hashes = [
    record["path"]
    for record in records
    if len(
        record["sha256"]
    ) != 64
]

print(
    "Invalid hashes:",
    len(bad_hashes),
)

if bad_hashes:

    print(
        bad_hashes
    )

    raise AssertionError(
        "Invalid SHA-256 values."
    )


audit[
    "sha256_complete"
] = "PASSED"


# =============================================================================
# H — SUMMARIZE INVENTORY
# =============================================================================

banner("H — FINAL INVENTORY SUMMARY")

category_summary = {}

for category in EXPECTED_COUNTS:

    count = sum(
        1
        for record in records
        if record["category"]
        == category
    )

    category_summary[
        category
    ] = count

    print(
        f"{category}: {count}"
    )


print(
    "\nTOTAL:",
    len(records),
)


# =============================================================================
# I — SAVE CSV INVENTORY
# =============================================================================

banner("I — SAVE FINAL INVENTORY CSV")

CSV_PATH = (
    FINAL_FREEZE
    / "phase13_6_1_final_artifact_inventory.csv"
)

with open(
    CSV_PATH,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "category",
            "role",
            "path",
            "filename",
            "extension",
            "size_bytes",
            "sha256",
        ],
    )

    writer.writeheader()

    writer.writerows(
        records
    )


print(
    "Saved:",
    CSV_PATH.relative_to(ROOT),
)


# =============================================================================
# J — SAVE JSON INVENTORY
# =============================================================================

banner("J — SAVE FINAL INVENTORY JSON")

JSON_PATH = (
    FINAL_FREEZE
    / "phase13_6_1_final_artifact_inventory.json"
)

inventory_json = {
    "system":
        "CareCompute",

    "phase":
        "13.6.1",

    "inventory_name":
        "FINAL_PRE_FREEZE_ARTIFACT_INVENTORY",

    "system_variant":
        "System D — Learned Router",

    "runtime_mode":
        "FROZEN_HUMAN_IN_THE_LOOP",

    "artifact_counts":
        category_summary,

    "result_artifact_count":
        result_count,

    "source_artifact_count":
        source_count,

    "total_artifact_count":
        len(records),

    "artifacts":
        records,

    "audit":
        audit,

    "status":
        "PASSED",
}


with open(
    JSON_PATH,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        inventory_json,
        f,
        indent=2,
        sort_keys=True,
    )


print(
    "Saved:",
    JSON_PATH.relative_to(ROOT),
)


# =============================================================================
# K — HASH INVENTORY ARTIFACTS
# =============================================================================

banner("K — HASH INVENTORY ARTIFACTS")

csv_hash = sha256(
    CSV_PATH
)

json_hash = sha256(
    JSON_PATH
)

print(
    CSV_PATH.relative_to(ROOT),
    "->",
    csv_hash,
)

print(
    JSON_PATH.relative_to(ROOT),
    "->",
    json_hash,
)


# =============================================================================
# L — SAVE INVENTORY AUDIT
# =============================================================================

banner("L — SAVE INVENTORY AUDIT")

AUDIT_PATH = (
    FINAL_FREEZE
    / "phase13_6_1_final_artifact_inventory_audit.json"
)

inventory_audit = {
    "system":
        "CareCompute",

    "phase":
        "13.6.1",

    "checks":
        audit,

    "expected_counts":
        EXPECTED_COUNTS,

    "observed_counts":
        category_summary,

    "expected_total":
        EXPECTED_TOTAL,

    "observed_total":
        len(records),

    "inventory_csv":
        str(
            CSV_PATH.relative_to(ROOT)
        ),

    "inventory_csv_sha256":
        csv_hash,

    "inventory_json":
        str(
            JSON_PATH.relative_to(ROOT)
        ),

    "inventory_json_sha256":
        json_hash,

    "phase13_6_1_status":
        "PASSED",
}


with open(
    AUDIT_PATH,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        inventory_audit,
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
    "PHASE 13.6.1 COMPLETE — "
    "FINAL ARTIFACT INVENTORY VERIFIED"
)

print("\nSYSTEM")
print(" CareCompute")

print("\nFINAL SYSTEM")
print(" System D — Learned Router")

print("\nARTIFACT INVENTORY")

print(
    " Scientific provenance:",
    category_summary[
        "SCIENTIFIC_PROVENANCE"
    ],
)

print(
    " Scientific evaluation:",
    category_summary[
        "SCIENTIFIC_EVALUATION"
    ],
)

print(
    " Integrated runtime:",
    category_summary[
        "INTEGRATED_RUNTIME"
    ],
)

print(
    " Validation evidence:",
    category_summary[
        "VALIDATION_EVIDENCE"
    ],
)

print(
    " Executable source:",
    category_summary[
        "EXECUTABLE_SOURCE"
    ],
)

print(
    "\nTOTAL PRE-FREEZE ARTIFACTS:",
    len(records),
)

print("\nINTEGRITY")
print(" Unique artifact paths: YES")
print(" SHA-256 coverage: 100%")

print("\nPREVIOUS ARTIFACT MODIFICATION")
print(" NONE")

print("\nFINAL STATUS")
print(" FINAL_ARTIFACT_INVENTORY_VERIFIED")

print(
    "\nInventory:",
    JSON_PATH.relative_to(ROOT),
)

print(
    "Inventory audit:",
    AUDIT_PATH.relative_to(ROOT),
)


banner(
    "NEXT: PHASE 13.6.2 — "
    "CROSS-PHASE PROVENANCE VERIFICATION"
)