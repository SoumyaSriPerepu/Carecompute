from pathlib import Path
import json

import pandas as pd
import streamlit as st


# ============================================================
# CareCompute — Public Frozen Demo
# ============================================================

st.set_page_config(
    page_title="CareCompute",
    page_icon="🏥",
    layout="wide",
)


ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "demo_data" / "safe_demo_cases"

ROUTING_PATH = DEMO_DIR / "demo_routing.csv"
PACKETS_PATH = DEMO_DIR / "demo_packets.jsonl"
INDEX_PATH = DEMO_DIR / "demo_case_index.csv"


@st.cache_data
def load_demo_data():
    routing = pd.read_csv(ROUTING_PATH)
    case_index = pd.read_csv(INDEX_PATH)

    packets = []
    with open(PACKETS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                packets.append(json.loads(line))

    packet_lookup = {
        packet["demo_case_id"]: packet
        for packet in packets
    }

    return routing, case_index, packet_lookup


routing, case_index, packet_lookup = load_demo_data()

demo_ids = case_index["demo_case_id"].tolist()


# ------------------------------------------------------------
# Header
# ------------------------------------------------------------

st.title("CareCompute")

st.subheader(
    "Selective Agentic AI for False-Negative Rescue "
    "in Hospital Readmission Risk Assessment"
)

st.info(
    "Public frozen research demonstration. "
    "This demo replays a small set of sanitized, precomputed cases. "
    "It does not retrain models, recalculate routing, modify predictions, "
    "or perform autonomous clinical action."
)


# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------

st.sidebar.header("Frozen Runtime")

st.sidebar.write("Primary threshold: **0.115**")
st.sidebar.write("Review budget: **15%**")
st.sidebar.write("Routing source: **Frozen Learned Router**")
st.sidebar.write("Runtime mode: **Human-in-the-loop**")

selected_case = st.sidebar.selectbox(
    "Select a demo case",
    demo_ids,
)

packet = packet_lookup[selected_case]

routing_row = routing[
    routing["demo_case_id"] == selected_case
].iloc[0]


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

st.header("1. Frozen Case Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Primary probability",
        f"{packet['primary_model']['calibrated_probability']:.3f}",
    )

with col2:
    st.metric(
        "Primary threshold",
        f"{packet['primary_model']['decision_threshold']:.3f}",
    )

with col3:
    prediction = packet["primary_model"]["predicted_30d"]
    st.metric(
        "Primary prediction",
        "Negative" if prediction == 0 else "Positive",
    )

with col4:
    st.metric(
        "Review priority",
        packet["rescue_review"]["review_priority"],
    )


# ------------------------------------------------------------
# Primary model
# ------------------------------------------------------------

st.header("2. Primary Model")

probability = packet["primary_model"]["calibrated_probability"]
threshold = packet["primary_model"]["decision_threshold"]
prediction = packet["primary_model"]["predicted_30d"]

if prediction == 0:
    st.success(
        f"Primary model result: NEGATIVE "
        f"({probability:.3f} < {threshold:.3f})"
    )
else:
    st.warning(
        f"Primary model result: POSITIVE "
        f"({probability:.3f} ≥ {threshold:.3f})"
    )

st.caption(
    "The primary prediction is frozen and cannot be modified by CareCompute."
)


# ------------------------------------------------------------
# Rescue router
# ------------------------------------------------------------

st.header("3. Frozen Rescue Router")

router_col1, router_col2, router_col3 = st.columns(3)

with router_col1:
    st.metric(
        "Router probability",
        f"{packet['rescue_router']['fn_router_probability']:.3f}",
    )

with router_col2:
    st.metric(
        "Review budget",
        f"{packet['rescue_router']['review_budget'] * 100:.0f}%",
    )

with router_col3:
    selected = packet["rescue_router"]["selected_for_review"]
    st.metric(
        "Selected for review",
        "YES" if selected else "NO",
    )

st.subheader("Frozen router signals")

signals = pd.DataFrame(
    {
        "Signal": [
            "Calibrated probability",
            "Model disagreement",
            "Number of diagnoses",
            "Outpatient visits",
            "Emergency visits",
        ],
        "Value": [
            routing_row["calibrated_probability"],
            routing_row["model_disagreement_std"],
            routing_row["number_diagnoses"],
            routing_row["number_outpatient"],
            routing_row["number_emergency"],
        ],
    }
)

st.dataframe(
    signals,
    hide_index=True,
    use_container_width=True,
)

st.caption(
    "These are the five frozen signals used by the learned rescue router."
)


# ------------------------------------------------------------
# Rescue Review Agent
# ------------------------------------------------------------

st.header("4. Rescue Review Agent")

priority = packet["rescue_review"]["review_priority"]

if priority == "HIGH":
    st.error("HIGH review priority")
elif priority == "MODERATE":
    st.warning("MODERATE review priority")
else:
    st.info("LOW review priority")

st.write(packet["rescue_review"]["risk_signal_summary"])

st.write(
    "**Reason codes:**",
    packet["rescue_review"]["reason_codes"],
)

st.write(
    "**Human review action:**",
    packet["rescue_review"]["human_review_action"],
)

st.write(
    "**Confidence:**",
    packet["rescue_review"]["confidence"],
)


# ------------------------------------------------------------
# Explanation Agent
# ------------------------------------------------------------

st.header("5. Explanation Agent")

st.write(packet["explanation"]["explanation"])

st.write(
    "**Uncertainty statement:**",
    packet["explanation"]["uncertainty_statement"],
)

st.info(packet["explanation"]["human_review_statement"])


# ------------------------------------------------------------
# Safety
# ------------------------------------------------------------

st.header("6. Safety Guardrail")

guardrail = packet["safety_guardrail"]

if guardrail["passed"]:
    st.success("Safety guardrail: PASSED")
else:
    st.error("Safety guardrail: FAILED")

safety_table = pd.DataFrame(
    {
        "Safety constraint": [
            "Ground truth available to runtime",
            "Patient identifier available",
            "Diagnosis allowed",
            "Treatment recommendation allowed",
            "Medication recommendation allowed",
            "Prediction modification allowed",
            "Router modification allowed",
            "Threshold modification allowed",
            "Autonomous clinical action allowed",
        ],
        "Value": [
            guardrail["ground_truth_available"],
            guardrail["patient_identifier_available"],
            guardrail["diagnosis_allowed"],
            guardrail["treatment_recommendation_allowed"],
            guardrail["medication_recommendation_allowed"],
            guardrail["prediction_modification_allowed"],
            guardrail["router_modification_allowed"],
            guardrail["threshold_modification_allowed"],
            guardrail["autonomous_clinical_action_allowed"],
        ],
    }
)

st.dataframe(
    safety_table,
    hide_index=True,
    use_container_width=True,
)


# ------------------------------------------------------------
# Fairness
# ------------------------------------------------------------

st.header("7. Fairness Monitor")

fairness = packet["fairness_monitor"]

st.write(
    "**Mode:**",
    fairness["mode"],
)

fair1, fair2, fair3 = st.columns(3)

with fair1:
    st.metric(
        "Demographics used for routing",
        "YES" if fairness["demographics_used_for_routing"] else "NO",
    )

with fair2:
    st.metric(
        "Demographics used for priority",
        "YES" if fairness["demographics_used_for_priority"] else "NO",
    )

with fair3:
    st.metric(
        "Subgroup-specific threshold",
        "YES" if fairness["subgroup_specific_threshold"] else "NO",
    )

st.caption(
    "Fairness monitoring is population-level and read-only. "
    "No demographic attributes are included in the public demo cases."
)


# ------------------------------------------------------------
# Final orchestration
# ------------------------------------------------------------

st.header("8. Final Human Review Packet")

st.write(
    "**Workflow disposition:**",
    packet["workflow_disposition"],
)

st.write(
    "**Human review required:**",
    packet["human_review_required"],
)

st.write(
    "**Autonomous clinical action:**",
    packet["autonomous_clinical_action"],
)

if packet["human_review_required"]:
    st.error(
        "HUMAN REVIEW REQUIRED — "
        "CareCompute does not make the final clinical decision."
    )


# ------------------------------------------------------------
# Technical metadata
# ------------------------------------------------------------

with st.expander("Technical runtime metadata"):
    st.json(
        {
            "demo_case_id": packet["demo_case_id"],
            "schema_version": packet["schema_version"],
            "runtime_mode": packet["orchestrator"]["runtime_mode"],
            "routing_source": packet["orchestrator"]["routing_source"],
            "rescue_review_source": packet["orchestrator"]["rescue_review_source"],
            "explanation_source": packet["orchestrator"]["explanation_source"],
        }
    )


st.divider()

st.caption(
    "CareCompute research prototype — frozen human-in-the-loop runtime. "
    "Not for clinical use."
)
