"""Streamlit frontend for the Costell estimation engine."""

import csv
from datetime import datetime
from io import StringIO

import plotly.graph_objects as go
import requests
import streamlit as st
from fpdf import FPDF

# --- API Configuration ---
API_URL = "http://127.0.0.1:8000/estimate"

# --- Page Configuration ---
st.set_page_config(
    page_title="Costell",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# PDF Report Generator
# ============================================================
def generate_pdf_report(payload: dict, result: dict) -> bytes:
    """Generate a professional PDF report with inputs and estimates."""

    pdf = FPDF()
    pdf.add_page()

    # --- Header ---
    pdf.set_fill_color(30, 41, 59)  # Dark navy
    pdf.rect(0, 0, 210, 30, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_y(8)
    pdf.cell(0, 12, "Costell - Project Cost Estimate", ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_y(35)

    # --- Timestamp ---
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(
        0,
        6,
        f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ln=True,
        align="C",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    # --- Section: Input Parameters ---
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "  Input Parameters", ln=True, fill=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.ln(2)

    for key, value in payload.items():
        label = key.replace("_", " ").title()
        if isinstance(value, (int, float)):
            value_str = f"{value:,.2f}"
        else:
            value_str = str(value)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(90, 7, f"  {label}:", border=0)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, value_str, ln=True)

    pdf.ln(6)

    # --- Section: Effort Estimates ---
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "  Effort Estimates (person-hours)", ln=True, fill=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(90, 8, "  P50 (Most Likely)", border=0)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"{result['p50_effort']:,.0f} hrs", ln=True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(90, 8, "  P80 Lower Bound", border=0)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"{result['p80_lower_effort']:,.0f} hrs", ln=True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(90, 8, "  P80 Upper Bound", border=0)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"{result['p80_upper_effort']:,.0f} hrs", ln=True)

    pdf.ln(6)

    # --- Section: Cost Breakdown (P50) ---
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "  Cost Breakdown (P50 Scenario)", ln=True, fill=True)
    pdf.ln(2)

    p50 = result["p50_cost"]
    rows = [
        ("Personnel Cost", p50["personnel_cost"]),
        ("Tooling Cost", p50["tooling_cost"]),
        ("Cloud/Infra Cost", p50["cloud_cost"]),
        ("Contingency", p50["contingency"]),
    ]

    for label, value in rows:
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(90, 8, f"  {label}", border=0)
        pdf.cell(0, 8, f"Rs. {value:,.0f}", ln=True)

    # Total row (bold, highlighted)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(220, 230, 241)
    pdf.cell(90, 10, "  TOTAL (P50)", border=0, fill=True)
    pdf.cell(0, 10, f"Rs. {p50['total_cost']:,.0f}", ln=True, fill=True)

    pdf.ln(8)

    # --- Section: Safe Budget Recommendation ---
    safe_budget = result["p80_upper_cost"]["total_cost"]
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_fill_color(212, 237, 218)  # Light green
    pdf.set_text_color(21, 87, 36)
    pdf.cell(0, 12, "  Safe Budget Recommendation", ln=True, fill=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.ln(2)
    pdf.multi_cell(
        0,
        8,
        f"  To be 80% confident the project stays within budget, "
        f"plan for a safe budget of Rs. {safe_budget:,.0f}.",
    )
    pdf.set_text_color(0, 0, 0)

    # --- Footer ---
    pdf.set_y(-20)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(
        0,
        10,
        "Costell v0.1.0 | AI-powered cost estimation for the AI-native development era.",
        align="C",
    )

    return bytes(pdf.output())


# ============================================================
# CSV Export Helper
# ============================================================
def generate_csv_report(payload: dict, result: dict) -> str:
    """Generate a CSV report as a string."""
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")

    # Section 1: Inputs
    writer.writerow(["INPUT PARAMETERS"])
    for key, value in payload.items():
        writer.writerow([key.replace("_", " ").title(), value])
    writer.writerow([])

    # Section 2: Effort
    writer.writerow(["EFFORT ESTIMATES (hours)"])
    writer.writerow(["P50", result["p50_effort"]])
    writer.writerow(["P80 Lower", result["p80_lower_effort"]])
    writer.writerow(["P80 Upper", result["p80_upper_effort"]])
    writer.writerow([])

    # Section 3: Cost Breakdown
    writer.writerow(["COST BREAKDOWN (P50, INR)"])
    p50 = result["p50_cost"]
    writer.writerow(["Personnel Cost", p50["personnel_cost"]])
    writer.writerow(["Tooling Cost", p50["tooling_cost"]])
    writer.writerow(["Cloud/Infra Cost", p50["cloud_cost"]])
    writer.writerow(["Contingency", p50["contingency"]])
    writer.writerow(["Total", p50["total_cost"]])
    writer.writerow([])

    # Section 4: Safe Budget
    writer.writerow(["SAFE BUDGET RECOMMENDATION (INR)"])
    writer.writerow(["P80 Upper Total", result["p80_upper_cost"]["total_cost"]])

    # Prepend BOM for Excel compatibility
    return "\ufeff" + output.getvalue()


# ============================================================
# Header
# ============================================================
st.title("📊 Costell — AI Cost Estimation")
st.markdown("> *A constellation of signals that reveals your project's true cost.*")
st.markdown("---")


# ============================================================
# Sidebar: Inputs
# ============================================================
st.sidebar.header("📋 Project Parameters")

estimated_effort = st.sidebar.number_input(
    "Estimated Effort (hours)", min_value=1.0, value=1200.0, step=50.0
)
team_size = st.sidebar.number_input("Team Size", min_value=1, value=5, step=1)
duration = st.sidebar.number_input("Duration (months)", min_value=1, value=12, step=1)
function_points = st.sidebar.number_input(
    "Adjusted Function Points (AFP)", min_value=1.0, value=450.0, step=10.0
)
language = st.sidebar.selectbox(
    "Primary Language / Dev Type",
    ["Python", "Java", "C++", "C#", "3GL", "4GL", "Assembly", "Unknown"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.header("💰 Financial Parameters")

blended_hourly_rate = st.sidebar.number_input(
    "Blended Hourly Rate (Rs.)",
    min_value=100.0,
    value=2500.0,
    step=100.0,
    help="Average cost per team member per hour.",
)
tooling_cost_per_month = st.sidebar.number_input(
    "Tooling Cost / Month (Rs.)",
    min_value=0.0,
    value=50000.0,
    step=5000.0,
    help="Jira, IDE licenses, Figma, etc.",
)
cloud_cost_per_month = st.sidebar.number_input(
    "Cloud/AI Infra / Month (Rs.)",
    min_value=0.0,
    value=80000.0,
    step=5000.0,
    help="AWS, GCP, LLM API calls, etc.",
)
contingency_percent = st.sidebar.slider(
    "Contingency Buffer (%)",
    min_value=0,
    max_value=40,
    value=15,
    step=1,
    help="Safety margin for surprises.",
)


# ============================================================
# Main: Predict & Display
# ============================================================
predict_button = st.button("🚀 Predict Project Cost", type="primary")

if predict_button:
    payload = {
        "estimated_effort": estimated_effort,
        "team_size": float(team_size),
        "duration": float(duration),
        "function_points": function_points,
        "language": language,
        "dataset_source": "user_input",
        "blended_hourly_rate": blended_hourly_rate,
        "tooling_cost_per_month": tooling_cost_per_month,
        "cloud_cost_per_month": cloud_cost_per_month,
        "contingency_percent": float(contingency_percent),
    }

    try:
        with st.spinner("Calculating the budget range..."):
            response = requests.post(API_URL, json=payload, timeout=15)

        if response.status_code == 200:
            data = response.json()

            # Store in session state so downloads persist
            st.session_state["payload"] = payload
            st.session_state["result"] = data
            st.session_state["show_results"] = True

        else:
            st.error(f"API Error ({response.status_code}): {response.text}")

    except requests.exceptions.ConnectionError:
        st.error(
            "❌ Could not connect to the API. Please ensure the FastAPI server is running:\n\n"
            "`uvicorn costell.api.main:app --reload`"
        )


# --- Display Results (persists across reruns) ---
if st.session_state.get("show_results"):
    data = st.session_state["result"]
    payload = st.session_state["payload"]

    # --- Top-level Cost Metrics ---
    st.markdown("### 💰 Total Project Cost (INR)")

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "P50 (Most Likely)",
        f"₹{data['p50_cost']['total_cost']:,.0f}",
        f"{data['p50_effort']:,.0f} hrs",
    )
    col2.metric(
        "P80 Lower Bound",
        f"₹{data['p80_lower_cost']['total_cost']:,.0f}",
        f"{data['p80_lower_effort']:,.0f} hrs",
    )
    col3.metric(
        "P80 Upper Bound",
        f"₹{data['p80_upper_cost']['total_cost']:,.0f}",
        f"{data['p80_upper_effort']:,.0f} hrs",
    )

    # --- Safe Budget Recommendation ---
    safe_budget = data["p80_upper_cost"]["total_cost"]
    st.success(
        f"**Safe Budget Recommendation:** Request **₹{safe_budget:,.0f}** "
        f"to be **80% confident** the project stays within budget."
    )

    # --- Download Buttons ---
    st.markdown("### 📥 Download Report")
    col_pdf, col_csv, _ = st.columns([1, 1, 2])

    with col_pdf:
        pdf_bytes = generate_pdf_report(payload, data)
        st.download_button(
            label="📄 Download PDF",
            data=pdf_bytes,
            file_name=f"costell_estimate_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    with col_csv:
        csv_str = generate_csv_report(payload, data)
        st.download_button(
            label="📊 Download CSV",
            data=csv_str,
            file_name=f"costell_estimate_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # --- Cost Breakdown Table ---
    st.markdown("### 📊 Cost Breakdown (P50 Scenario)")
    p50 = data["p50_cost"]
    breakdown_df = {
        "Component": ["Personnel", "Tooling", "Cloud/Infra", "Contingency", "**Total**"],
        "Cost (INR)": [
            f"₹{p50['personnel_cost']:,.0f}",
            f"₹{p50['tooling_cost']:,.0f}",
            f"₹{p50['cloud_cost']:,.0f}",
            f"₹{p50['contingency']:,.0f}",
            f"**₹{p50['total_cost']:,.0f}**",
        ],
    }
    st.table(breakdown_df)

    # --- Cost Range Chart ---
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=[data["p80_upper_cost"]["total_cost"] - data["p80_lower_cost"]["total_cost"]],
            y=["Project Cost"],
            base=[data["p80_lower_cost"]["total_cost"]],
            orientation="h",
            marker=dict(color="rgba(100, 149, 237, 0.5)"),
            name="P80 Range",
            hovertemplate="Lower: ₹%{base:,.0f}<br>Upper: ₹%{x:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[data["p50_cost"]["total_cost"]],
            y=["Project Cost"],
            mode="markers",
            marker=dict(color="red", size=18, symbol="diamond"),
            name="P50 (Most Likely)",
            hovertemplate="P50: ₹%{x:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Total Project Cost with 80% Confidence Interval",
        xaxis_title="Cost (INR)",
        showlegend=True,
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Pie Chart ---
    st.markdown("### 🥧 Where the Money Goes (P50)")
    pie_fig = go.Figure(
        data=[
            go.Pie(
                labels=["Personnel", "Tooling", "Cloud/Infra", "Contingency"],
                values=[
                    p50["personnel_cost"],
                    p50["tooling_cost"],
                    p50["cloud_cost"],
                    p50["contingency"],
                ],
                hole=0.4,
            )
        ]
    )
    pie_fig.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(pie_fig, use_container_width=True)


# --- Footer ---
st.markdown("---")
st.caption("Costell v0.1.0 | Built for the AI-native development era.")
