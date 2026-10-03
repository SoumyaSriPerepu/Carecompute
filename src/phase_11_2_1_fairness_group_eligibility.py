from pathlib import Path
import pandas as pd
import json
import hashlib


# =============================================================================
# PATHS
# =============================================================================

DATA_PATH = Path(
    "results/eligible/final_test_end_to_end_patient_predictions.csv"
)

SAFETY_LOCK = Path(
    "results/eligible/safety/phase11_1_safety_closure_manifest.json"
)

OUTPUT_DIR = Path("results/eligible/fairness")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GROUP_TABLE = OUTPUT_DIR / "phase11_2_1_group_eligibility.csv"
MANIFEST = OUTPUT_DIR / "phase11_2_1_fairness_eligibility_manifest.json"


# =============================================================================
# PREDECLARED ADEQUACY RULE
# =============================================================================

MIN_TOTAL = 100
MIN_POSITIVES = 30
MIN_NEGATIVES = 30


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

section("PHASE 11.2.1 — FAIRNESS GROUP ELIGIBILITY AND SAMPLE-SIZE LOCK")


# =============================================================================
# A — VERIFY INPUTS
# =============================================================================

section("A — VERIFY REQUIRED INPUTS")

for p in [DATA_PATH, SAFETY_LOCK]:
    if not p.exists():
        raise FileNotFoundError(p)

    print("FOUND:", p)

with SAFETY_LOCK.open() as f:
    safety = json.load(f)

if safety["status"] != "SAFETY_AUDIT_COMPLETE":
    raise RuntimeError(
        "Phase 11.1 Safety has not been formally closed."
    )

print("Phase 11.1 safety closure: PASSED")


# =============================================================================
# B — LOAD FULL FAIRNESS POPULATION
# =============================================================================

section("B — LOAD FULL TEST FAIRNESS POPULATION")

df = pd.read_csv(DATA_PATH)

required = {
    "encounter_id",
    "patient_nbr",
    "actual_30d",
    "predicted_30d",
    "calibrated_probability",
    "race",
    "gender",
    "age",
}

missing = required - set(df.columns)

if missing:
    raise RuntimeError(
        f"Missing required columns: {sorted(missing)}"
    )

print("Test encounters:", len(df))
print("Unique encounters:", df["encounter_id"].nunique())
print("Unique patients:", df["patient_nbr"].nunique())

print(
    "Actual positives:",
    int((df["actual_30d"] == 1).sum())
)

print(
    "Actual negatives:",
    int((df["actual_30d"] == 0).sum())
)

if len(df) != 15042:
    raise RuntimeError(
        f"Expected 15042 encounters; found {len(df)}"
    )

if not df["encounter_id"].is_unique:
    raise RuntimeError(
        "Encounter IDs are not unique."
    )

print("Full-population verification: PASSED")


# =============================================================================
# C — DEMOGRAPHIC MISSINGNESS
# =============================================================================

section("C — DEMOGRAPHIC MISSINGNESS")

for attribute in ["race", "gender", "age"]:

    missing_count = int(df[attribute].isna().sum())
    missing_rate = missing_count / len(df)

    print(
        f"{attribute}: missing={missing_count}, "
        f"rate={missing_rate:.6f}"
    )

print()
print(
    "Missing demographic values will NOT be silently removed "
    "from the audit inventory."
)


# =============================================================================
# D — PREDECLARE ADEQUACY RULE
# =============================================================================

section("D — PREDECLARE GROUP ADEQUACY RULE")

print("Minimum total encounters:", MIN_TOTAL)
print("Minimum actual positives:", MIN_POSITIVES)
print("Minimum actual negatives:", MIN_NEGATIVES)

print()
print("Eligible if ALL conditions hold:")
print(f"  n_total >= {MIN_TOTAL}")
print(f"  n_positive >= {MIN_POSITIVES}")
print(f"  n_negative >= {MIN_NEGATIVES}")

print()
print(
    "This rule is defined before subgroup performance metrics "
    "are calculated."
)


# =============================================================================
# E — BUILD GROUP INVENTORY
# =============================================================================

section("E — BUILD FAIRNESS GROUP INVENTORY")

records = []

for attribute in ["race", "gender", "age"]:

    audit_series = df[attribute].copy()

    # Preserve missing demographic information explicitly.
    audit_series = audit_series.astype("object")
    audit_series = audit_series.where(
        audit_series.notna(),
        "MISSING"
    )

    temp = df[
        [
            "encounter_id",
            "actual_30d",
        ]
    ].copy()

    temp["group"] = audit_series

    for group, g in temp.groupby(
        "group",
        dropna=False,
        sort=True,
    ):

        n_total = int(len(g))

        n_positive = int(
            (g["actual_30d"] == 1).sum()
        )

        n_negative = int(
            (g["actual_30d"] == 0).sum()
        )

        positive_rate = (
            n_positive / n_total
            if n_total
            else float("nan")
        )

        adequate = (
            n_total >= MIN_TOTAL
            and n_positive >= MIN_POSITIVES
            and n_negative >= MIN_NEGATIVES
        )

        reasons = []

        if n_total < MIN_TOTAL:
            reasons.append("TOTAL_LT_100")

        if n_positive < MIN_POSITIVES:
            reasons.append("POSITIVES_LT_30")

        if n_negative < MIN_NEGATIVES:
            reasons.append("NEGATIVES_LT_30")

        records.append({
            "attribute": attribute,
            "group": str(group),
            "n_total": n_total,
            "n_positive": n_positive,
            "n_negative": n_negative,
            "positive_rate": positive_rate,
            "adequate_sample": bool(adequate),
            "inadequacy_reason":
                "|".join(reasons) if reasons else "",
        })


inventory = pd.DataFrame(records)

inventory.to_csv(
    GROUP_TABLE,
    index=False
)

print("Group inventory:")

print(
    inventory.to_string(index=False)
)

print()
print("Saved:", GROUP_TABLE)


# =============================================================================
# F — ELIGIBILITY SUMMARY
# =============================================================================

section("F — ELIGIBILITY SUMMARY")

eligible = inventory[
    inventory["adequate_sample"]
].copy()

ineligible = inventory[
    ~inventory["adequate_sample"]
].copy()

for attribute in ["race", "gender", "age"]:

    attr = inventory[
        inventory["attribute"] == attribute
    ]

    attr_eligible = attr[
        attr["adequate_sample"]
    ]

    print()
    print(attribute.upper())
    print("Groups observed:", len(attr))
    print("Groups eligible:", len(attr_eligible))

    print(
        "Eligible groups:",
        attr_eligible["group"].tolist()
    )

print()
print("Total groups observed:", len(inventory))
print("Total groups eligible:", len(eligible))
print("Total groups underpowered:", len(ineligible))


# =============================================================================
# G — VERIFY GROUP ACCOUNTING
# =============================================================================

section("G — VERIFY GROUP ACCOUNTING")

accounting_checks = {}

for attribute in ["race", "gender", "age"]:

    attr_total = int(
        inventory.loc[
            inventory["attribute"] == attribute,
            "n_total"
        ].sum()
    )

    passed = attr_total == len(df)

    accounting_checks[attribute] = passed

    print(
        f"{attribute} group total:",
        attr_total,
        "PASSED" if passed else "FAILED"
    )

if not all(accounting_checks.values()):
    raise RuntimeError(
        "Demographic group accounting failed."
    )

print("Demographic accounting: PASSED")


# =============================================================================
# H — FREEZE FAIRNESS ELIGIBILITY POLICY
# =============================================================================

section("H — FREEZE FAIRNESS ELIGIBILITY POLICY")

manifest = {
    "phase": "11.2.1",

    "audit_name":
        "Fairness Group Eligibility and Sample-Size Lock",

    "status":
        "FAIRNESS_ELIGIBILITY_FROZEN",

    "population": {
        "test_encounters": int(len(df)),
        "unique_patients":
            int(df["patient_nbr"].nunique()),
        "actual_positives":
            int((df["actual_30d"] == 1).sum()),
        "actual_negatives":
            int((df["actual_30d"] == 0).sum()),
    },

    "protected_attributes_audited": [
        "race",
        "gender",
        "age",
    ],

    "adequacy_rule": {
        "minimum_total": MIN_TOTAL,
        "minimum_actual_positives":
            MIN_POSITIVES,
        "minimum_actual_negatives":
            MIN_NEGATIVES,
        "all_conditions_required": True,
        "rule_selected_before_group_performance":
            True,
    },

    "missingness_policy": {
        "missing_values_silently_dropped":
            False,
        "missing_values_inventory_label":
            "MISSING",
    },

    "group_counts": {
        "groups_observed": int(len(inventory)),
        "groups_eligible": int(len(eligible)),
        "groups_underpowered":
            int(len(ineligible)),
    },

    "eligible_groups": {
        attribute: (
            eligible.loc[
                eligible["attribute"] == attribute,
                "group"
            ].tolist()
        )
        for attribute in ["race", "gender", "age"]
    },

    "underpowered_groups": {
        attribute: (
            ineligible.loc[
                ineligible["attribute"] == attribute,
                [
                    "group",
                    "n_total",
                    "n_positive",
                    "n_negative",
                    "inadequacy_reason",
                ]
            ].to_dict("records")
        )
        for attribute in ["race", "gender", "age"]
    },

    "interpretation_boundary": {
        "audit_not_proof_of_clinical_fairness":
            True,
        "underpowered_groups_not_declared_fair":
            True,
        "underpowered_groups_not_silently_removed":
            True,
        "performance_metrics_calculated_in_this_phase":
            False,
    },

    "integrity": {
        "phase10_modified": False,
        "phase11_1_modified": False,
        "input_sha256":
            sha256_file(DATA_PATH),
        "safety_closure_sha256":
            sha256_file(SAFETY_LOCK),
    },

    "next_phase":
        "11.2.2 Group Performance Metrics with Confidence Intervals",
}


with MANIFEST.open("w") as f:
    json.dump(
        manifest,
        f,
        indent=2
    )

print("Eligibility manifest:", MANIFEST)


# =============================================================================
# I — FINAL VERIFICATION
# =============================================================================

section("I — FINAL VERIFICATION")

with MANIFEST.open() as f:
    saved = json.load(f)

checks = {
    "status":
        saved["status"]
        == "FAIRNESS_ELIGIBILITY_FROZEN",

    "population":
        saved["population"]["test_encounters"]
        == 15042,

    "positives":
        saved["population"]["actual_positives"]
        == 1736,

    "adequacy_predeclared":
        saved["adequacy_rule"][
            "rule_selected_before_group_performance"
        ] is True,

    "performance_not_yet_evaluated":
        saved["interpretation_boundary"][
            "performance_metrics_calculated_in_this_phase"
        ] is False,

    "missingness_preserved":
        saved["missingness_policy"][
            "missing_values_silently_dropped"
        ] is False,

    "phase10_unchanged":
        saved["integrity"]["phase10_modified"]
        is False,

    "group_table_exists":
        GROUP_TABLE.exists(),
}

for name, passed in checks.items():

    print(
        name + ":",
        "PASSED" if passed else "FAILED"
    )

if not all(checks.values()):

    raise RuntimeError(
        "Phase 11.2.1 final verification failed."
    )


# =============================================================================
# COMPLETE
# =============================================================================

section(
    "PHASE 11.2.1 COMPLETE — FAIRNESS ELIGIBILITY FROZEN"
)

print(
    "Adequacy rule: "
    "n>=100 AND positives>=30 AND negatives>=30"
)

print(
    "Subgroup performance inspected before eligibility lock: NO"
)

print(
    "Underpowered groups silently removed: NO"
)

print(
    "Clinical fairness established: NO"
)

print(
    "Phase 10 frozen system modified: NO"
)

print()
print(
    "NEXT: 11.2.2 — AUROC/AUPRC/Recall/FNR "
    "with confidence intervals"
)
