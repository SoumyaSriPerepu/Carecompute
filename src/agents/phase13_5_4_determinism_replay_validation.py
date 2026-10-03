"""
CareCompute
Phase 13.5.4 — Determinism and Replay Validation

Purpose
-------
Perform an isolated replay of the frozen Phase 13 runtime without
modifying canonical CareCompute artifacts.

Replay chain:
    Phase 13.2 frozen model/router runtime
    -> Phase 13.3 executable agent runtime
    -> Phase 13.4 integrated orchestrator

The repository is copied to a temporary directory. The replay is
executed only inside that isolated copy.

Canonical artifacts remain read-only.
"""

from pathlib import Path
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile


# =============================================================================
# CONFIGURATION
# =============================================================================

ROOT = Path.cwd().resolve()

PHASE13 = (
    ROOT
    / "results"
    / "eligible"
    / "phase13"
)

VALIDATION = (
    ROOT
    / "results"
    / "eligible"
    / "runtime_validation"
)

VALIDATION.mkdir(
    parents=True,
    exist_ok=True,
)

EXPECTED_POPULATION = 1178


REPLAY_SCRIPTS = [
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
]


# Canonical deterministic data products.
#
# Audit/manifest JSON files may contain metadata about output hashes,
# so primary determinism is established on the actual runtime data
# products first.

DETERMINISTIC_OUTPUTS = [
    Path(
        "results/eligible/phase13/"
        "phase13_2_frozen_routing_runtime.csv"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_2_agent_eligible_runtime.csv"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_3_patient_contexts.csv"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_3_rescue_review_outputs.csv"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_3_explanation_outputs.csv"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_3_agent_runtime_packets.jsonl"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_4_orchestrated_human_review_packets.jsonl"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_4_orchestrator_case_index.csv"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_4_fairness_monitor_snapshot.json"
    ),
]


# Everything we want to prove remained unchanged in the canonical repo.
CANONICAL_LOCK_FILES = [
    Path(
        "results/eligible/phase13/"
        "phase13_1_integrated_agent_architecture.json"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_2_frozen_routing_runtime.csv"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_2_agent_eligible_runtime.csv"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_2_frozen_runtime_manifest.json"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_2_runtime_replay_audit.json"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_3_patient_contexts.csv"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_3_rescue_review_outputs.csv"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_3_explanation_outputs.csv"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_3_agent_runtime_packets.jsonl"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_3_agent_runtime_summary.json"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_3_agent_runtime_audit.json"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_4_orchestrated_human_review_packets.jsonl"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_4_orchestrator_case_index.csv"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_4_fairness_monitor_snapshot.json"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_4_orchestrator_summary.json"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_4_orchestrator_audit.json"
    ),
    Path(
        "results/eligible/phase13/"
        "phase13_4_integrated_orchestrator_manifest.json"
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


def check(condition, name, audit):

    result = bool(condition)

    audit[name] = (
        "PASSED"
        if result
        else "FAILED"
    )

    print(
        f"{name}: "
        f"{audit[name]}"
    )

    if not result:

        raise AssertionError(
            f"{name} FAILED"
        )


def count_csv_rows(path):

    with open(
        path,
        "r",
        encoding="utf-8",
        newline="",
    ) as f:

        reader = csv.reader(f)

        try:
            next(reader)
        except StopIteration:
            return 0

        return sum(1 for _ in reader)


def count_jsonl(path):

    count = 0

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        for line in f:

            if line.strip():
                count += 1

    return count


def copy_repo(source, destination):

    ignore = shutil.ignore_patterns(
        ".git",
        "__pycache__",
        "*.pyc",
        ".DS_Store",
        "runtime_validation",
    )

    shutil.copytree(
        source,
        destination,
        ignore=ignore,
        dirs_exist_ok=True,
    )


def run_script(repo, relative_script):

    script = repo / relative_script

    result = subprocess.run(
        [
            sys.executable,
            str(script),
        ],
        cwd=str(repo),
        text=True,
        capture_output=True,
        env=os.environ.copy(),
    )

    return result


# =============================================================================
# START
# =============================================================================

banner(
    "PHASE 13.5.4 — "
    "DETERMINISM AND REPLAY VALIDATION"
)

audit = {}


# =============================================================================
# A — VERIFY REPLAY COMPONENTS
# =============================================================================

banner("A — VERIFY REPLAY COMPONENTS")

for script in REPLAY_SCRIPTS:

    path = ROOT / script

    print(
        f"{script}: "
        f"{'FOUND' if path.exists() else 'MISSING'}"
    )

    if not path.exists():
        raise FileNotFoundError(path)


check(
    all(
        (ROOT / script).exists()
        for script in REPLAY_SCRIPTS
    ),
    "replay_scripts_present",
    audit,
)


# =============================================================================
# B — VERIFY CANONICAL OUTPUTS
# =============================================================================

banner("B — VERIFY CANONICAL OUTPUTS")

for relative in DETERMINISTIC_OUTPUTS:

    path = ROOT / relative

    print(
        f"{relative}: "
        f"{'FOUND' if path.exists() else 'MISSING'}"
    )

    if not path.exists():
        raise FileNotFoundError(path)


check(
    all(
        (ROOT / p).exists()
        for p in DETERMINISTIC_OUTPUTS
    ),
    "canonical_outputs_present",
    audit,
)


# =============================================================================
# C — CAPTURE CANONICAL PRE-REPLAY HASHES
# =============================================================================

banner(
    "C — CAPTURE CANONICAL PRE-REPLAY HASHES"
)

canonical_pre_hashes = {}

for relative in CANONICAL_LOCK_FILES:

    path = ROOT / relative

    if not path.exists():
        raise FileNotFoundError(path)

    digest = sha256(path)

    canonical_pre_hashes[
        str(relative)
    ] = digest

    print(
        f"{relative} -> {digest}"
    )


# =============================================================================
# D — CAPTURE EXPECTED DETERMINISTIC HASHES
# =============================================================================

banner(
    "D — CAPTURE EXPECTED "
    "DETERMINISTIC OUTPUT HASHES"
)

expected_hashes = {}

for relative in DETERMINISTIC_OUTPUTS:

    digest = sha256(
        ROOT / relative
    )

    expected_hashes[
        str(relative)
    ] = digest

    print(
        f"{relative} -> {digest}"
    )


# =============================================================================
# E — CREATE ISOLATED REPLAY ENVIRONMENT
# =============================================================================

banner(
    "E — CREATE ISOLATED REPLAY ENVIRONMENT"
)

temp_root = Path(
    tempfile.mkdtemp(
        prefix="carecompute_phase13_replay_"
    )
)

replay_root = (
    temp_root
    / "carecompute"
)

print(
    "Temporary replay root:",
    replay_root,
)

copy_repo(
    ROOT,
    replay_root,
)

check(
    replay_root.exists(),
    "isolated_repo_created",
    audit,
)


# =============================================================================
# F — EXECUTE PHASE 13.2 IN ISOLATION
# =============================================================================

banner(
    "F — REPLAY PHASE 13.2 "
    "MODEL + ROUTER RUNTIME"
)

result_13_2 = run_script(
    replay_root,
    REPLAY_SCRIPTS[0],
)

print(
    "Return code:",
    result_13_2.returncode,
)

if result_13_2.returncode != 0:

    print("\n--- STDOUT ---")
    print(
        result_13_2.stdout[-10000:]
    )

    print("\n--- STDERR ---")
    print(
        result_13_2.stderr[-10000:]
    )


check(
    result_13_2.returncode == 0,
    "phase13_2_replay_execution",
    audit,
)


# =============================================================================
# G — EXECUTE PHASE 13.3 IN ISOLATION
# =============================================================================

banner(
    "G — REPLAY PHASE 13.3 "
    "EXECUTABLE AGENTS"
)

result_13_3 = run_script(
    replay_root,
    REPLAY_SCRIPTS[1],
)

print(
    "Return code:",
    result_13_3.returncode,
)

if result_13_3.returncode != 0:

    print("\n--- STDOUT ---")
    print(
        result_13_3.stdout[-10000:]
    )

    print("\n--- STDERR ---")
    print(
        result_13_3.stderr[-10000:]
    )


check(
    result_13_3.returncode == 0,
    "phase13_3_replay_execution",
    audit,
)


# =============================================================================
# H — EXECUTE PHASE 13.4 IN ISOLATION
# =============================================================================

banner(
    "H — REPLAY PHASE 13.4 "
    "INTEGRATED ORCHESTRATOR"
)

result_13_4 = run_script(
    replay_root,
    REPLAY_SCRIPTS[2],
)

print(
    "Return code:",
    result_13_4.returncode,
)

if result_13_4.returncode != 0:

    print("\n--- STDOUT ---")
    print(
        result_13_4.stdout[-10000:]
    )

    print("\n--- STDERR ---")
    print(
        result_13_4.stderr[-10000:]
    )


check(
    result_13_4.returncode == 0,
    "phase13_4_replay_execution",
    audit,
)


# =============================================================================
# I — VERIFY REPLAY POPULATION
# =============================================================================

banner("I — VERIFY REPLAY POPULATION")

replay_population_files = {
    "phase13_2_agent_eligible":
        Path(
            "results/eligible/phase13/"
            "phase13_2_agent_eligible_runtime.csv"
        ),

    "phase13_3_contexts":
        Path(
            "results/eligible/phase13/"
            "phase13_3_patient_contexts.csv"
        ),

    "phase13_3_packets":
        Path(
            "results/eligible/phase13/"
            "phase13_3_agent_runtime_packets.jsonl"
        ),

    "phase13_4_packets":
        Path(
            "results/eligible/phase13/"
            "phase13_4_orchestrated_human_review_packets.jsonl"
        ),

    "phase13_4_case_index":
        Path(
            "results/eligible/phase13/"
            "phase13_4_orchestrator_case_index.csv"
        ),
}


for name, relative in (
    replay_population_files.items()
):

    path = replay_root / relative

    if path.suffix == ".csv":

        count = count_csv_rows(
            path
        )

    else:

        count = count_jsonl(
            path
        )

    print(
        f"{name}: {count}"
    )

    check(
        count == EXPECTED_POPULATION,
        f"{name}_population_lock",
        audit,
    )


# =============================================================================
# J — COMPARE REPLAY OUTPUT HASHES
# =============================================================================

banner(
    "J — COMPARE REPLAY OUTPUT HASHES"
)

comparison = []

for relative in DETERMINISTIC_OUTPUTS:

    canonical_hash = (
        expected_hashes[
            str(relative)
        ]
    )

    replay_path = (
        replay_root
        / relative
    )

    if not replay_path.exists():

        comparison.append({
            "artifact":
                str(relative),

            "canonical_sha256":
                canonical_hash,

            "replay_sha256":
                None,

            "exact_match":
                False,
        })

        print(
            f"{relative}: MISSING"
        )

        continue

    replay_hash = sha256(
        replay_path
    )

    exact = (
        canonical_hash
        == replay_hash
    )

    comparison.append({
        "artifact":
            str(relative),

        "canonical_sha256":
            canonical_hash,

        "replay_sha256":
            replay_hash,

        "exact_match":
            exact,
    })

    print(
        f"{relative}: "
        f"{'EXACT MATCH' if exact else 'MISMATCH'}"
    )


exact_matches = sum(
    1
    for item in comparison
    if item["exact_match"]
)

print(
    "\nExact deterministic matches:",
    f"{exact_matches}/"
    f"{len(DETERMINISTIC_OUTPUTS)}",
)

check(
    exact_matches
    == len(DETERMINISTIC_OUTPUTS),
    "deterministic_output_exact_match",
    audit,
)


# =============================================================================
# K — VERIFY CANONICAL REPO WAS NOT MODIFIED
# =============================================================================

banner(
    "K — VERIFY CANONICAL REPO "
    "WAS NOT MODIFIED"
)

canonical_post_hashes = {}

for relative in CANONICAL_LOCK_FILES:

    path = ROOT / relative

    digest = sha256(path)

    canonical_post_hashes[
        str(relative)
    ] = digest

    check(
        digest
        == canonical_pre_hashes[
            str(relative)
        ],
        (
            "canonical_unchanged__"
            + relative.name
        ),
        audit,
    )


# =============================================================================
# L — SAVE REPLAY COMPARISON
# =============================================================================

banner("L — SAVE REPLAY COMPARISON")

comparison_path = (
    VALIDATION
    / "phase13_5_4_replay_hash_comparison.csv"
)

with open(
    comparison_path,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "artifact",
            "canonical_sha256",
            "replay_sha256",
            "exact_match",
        ],
    )

    writer.writeheader()
    writer.writerows(
        comparison
    )


print(
    "Saved:",
    comparison_path,
)


# =============================================================================
# M — SAVE REPLAY LOGS
# =============================================================================

banner("M — SAVE REPLAY LOGS")

logs = {
    "phase13_2": {
        "return_code":
            result_13_2.returncode,

        "stdout":
            result_13_2.stdout,

        "stderr":
            result_13_2.stderr,
    },

    "phase13_3": {
        "return_code":
            result_13_3.returncode,

        "stdout":
            result_13_3.stdout,

        "stderr":
            result_13_3.stderr,
    },

    "phase13_4": {
        "return_code":
            result_13_4.returncode,

        "stdout":
            result_13_4.stdout,

        "stderr":
            result_13_4.stderr,
    },
}


log_path = (
    VALIDATION
    / "phase13_5_4_replay_execution_log.json"
)

with open(
    log_path,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        logs,
        f,
        indent=2,
    )


print(
    "Saved:",
    log_path,
)


# =============================================================================
# N — SAVE VALIDATION AUDIT
# =============================================================================

banner("N — SAVE VALIDATION AUDIT")

overall_passed = all(
    value == "PASSED"
    for value in audit.values()
)


audit_output = {
    "system":
        "CareCompute",

    "phase":
        "13.5.4",

    "validation":
        "DETERMINISM_AND_ISOLATED_REPLAY",

    "replay_mode":
        "TEMPORARY_ISOLATED_REPOSITORY",

    "population":
        EXPECTED_POPULATION,

    "scripts_replayed": [
        str(x)
        for x in REPLAY_SCRIPTS
    ],

    "deterministic_outputs":
        comparison,

    "exact_match_count":
        exact_matches,

    "expected_match_count":
        len(DETERMINISTIC_OUTPUTS),

    "canonical_pre_hashes":
        canonical_pre_hashes,

    "canonical_post_hashes":
        canonical_post_hashes,

    "checks":
        audit,

    "overall_status":
        "PASSED"
        if overall_passed
        else "FAILED",
}


audit_path = (
    VALIDATION
    / "phase13_5_4_determinism_replay_audit.json"
)

with open(
    audit_path,
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
    audit_path,
)


# =============================================================================
# O — CLEAN TEMPORARY REPLAY
# =============================================================================

banner(
    "O — CLEAN TEMPORARY REPLAY ENVIRONMENT"
)

shutil.rmtree(
    temp_root,
    ignore_errors=True,
)

check(
    not temp_root.exists(),
    "temporary_replay_removed",
    audit,
)

print(
    "Temporary replay environment removed."
)


# =============================================================================
# FINAL
# =============================================================================

banner(
    "PHASE 13.5.4 COMPLETE — "
    "DETERMINISM + REPLAY VALIDATION"
)

print("\nSYSTEM")
print(" CareCompute")

print("\nREPLAY")
print(" Isolated temporary repository")

print("\nCOMPONENTS")
print(" Phase 13.2: REPLAYED")
print(" Phase 13.3: REPLAYED")
print(" Phase 13.4: REPLAYED")

print("\nPOPULATION")
print(f" {EXPECTED_POPULATION}")

print("\nDETERMINISTIC OUTPUTS")
print(
    f" Exact matches: "
    f"{exact_matches}/"
    f"{len(DETERMINISTIC_OUTPUTS)}"
)

print("\nCANONICAL ARTIFACT MODIFICATION")
print(" NONE")

print("\nFINAL STATUS")

if overall_passed:

    print(
        " DETERMINISM_AND_REPLAY_VALIDATED"
    )

else:

    print(
        " DETERMINISM_AND_REPLAY_FAILED"
    )


print(
    "\nAudit:",
    audit_path,
)

print(
    "Hash comparison:",
    comparison_path,
)

print(
    "Replay log:",
    log_path,
)


if not overall_passed:

    raise SystemExit(
        "Phase 13.5.4 validation failed."
    )


banner(
    "NEXT: PHASE 13.5.5 — "
    "FAILURE AND EDGE-CASE VALIDATION"
)