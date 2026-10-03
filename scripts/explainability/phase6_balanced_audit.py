import pandas as pd
import os


# =====================================================
# SETTINGS
# =====================================================

THRESHOLD = 0.115

test_path = (
    "data/processed/eligible/test.csv"
)

prediction_path = (
    "results/eligible/test_predictions.csv"
)

output_dir = (
    "results/eligible/explanations"
)

os.makedirs(
    output_dir,
    exist_ok=True
)


# =====================================================
# 1. LOAD DATA
# =====================================================

test = pd.read_csv(
    test_path,
    low_memory=False
)

pred = pd.read_csv(
    prediction_path
)


print("Test rows:", len(test))
print("Prediction rows:", len(pred))


# =====================================================
# 2. MERGE PREDICTIONS WITH PATIENT DATA
# =====================================================

audit = test.merge(
    pred[
        [
            "encounter_id",
            "calibrated_probability",
            "uncertainty",
            "predicted_30d"
        ]
    ],
    on="encounter_id",
    how="inner"
)


print("Merged rows:", len(audit))


# =====================================================
# 3. CREATE CONFUSION-MATRIX GROUP
# =====================================================

def case_type(row):

    actual = row["target_30d"]
    predicted = row["predicted_30d"]

    if actual == 1 and predicted == 1:
        return "TP"

    elif actual == 0 and predicted == 0:
        return "TN"

    elif actual == 0 and predicted == 1:
        return "FP"

    elif actual == 1 and predicted == 0:
        return "FN"


audit["case_type"] = audit.apply(
    case_type,
    axis=1
)


# =====================================================
# 4. CHECK AVAILABLE CASES
# =====================================================

print()
print("AVAILABLE CASES")
print("-------------------------")

print(
    audit["case_type"].value_counts()
)


# =====================================================
# 5. SELECT 5 FROM EACH GROUP
# =====================================================

selected_parts = []

for group in [
    "TP",
    "TN",
    "FP",
    "FN"
]:

    group_df = audit[
        audit["case_type"] == group
    ]

    selected = group_df.sample(
        n=5,
        random_state=42
    )

    selected_parts.append(
        selected
    )


balanced = pd.concat(
    selected_parts,
    ignore_index=True
)


# =====================================================
# 6. ASSIGN AUDIT NUMBER
# =====================================================

balanced.insert(
    0,
    "audit_case",
    range(
        1,
        len(balanced) + 1
    )
)


# =====================================================
# 7. SHOW IMPORTANT INFORMATION
# =====================================================

columns_to_show = [
    "audit_case",
    "encounter_id",
    "case_type",
    "target_30d",
    "predicted_30d",
    "calibrated_probability",
    "uncertainty",
    "age",
    "gender",
    "race",
    "number_inpatient",
    "number_diagnoses",
    "time_in_hospital"
]


print()
print("BALANCED 20-CASE AUDIT")
print("-------------------------")

print(
    balanced[
        columns_to_show
    ].to_string(
        index=False
    )
)


# =====================================================
# 8. FINAL SAFETY CHECK
# =====================================================

print()
print("FINAL COUNTS")
print("-------------------------")

print(
    balanced[
        "case_type"
    ].value_counts()
)


assert (
    balanced["case_type"]
    .value_counts()
    .to_dict()
    ==
    {
        "TP": 5,
        "TN": 5,
        "FP": 5,
        "FN": 5
    }
)


# =====================================================
# 9. SAVE
# =====================================================

output_path = (
    f"{output_dir}/"
    "balanced_audit_20.csv"
)

balanced.to_csv(
    output_path,
    index=False
)


print()
print(
    "Saved:",
    os.path.exists(
        output_path
    )
)

print(
    "File:",
    output_path
)
