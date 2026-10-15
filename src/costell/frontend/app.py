"""Streamlit frontend for the Costell estimation engine — Integrated Flow."""

import csv
from datetime import datetime
from io import StringIO

import plotly.graph_objects as go
import requests
import streamlit as st
from fpdf import FPDF

# --- API Configuration ---
API_URL = "http://127.0.0.1:8000"
ESTIMATE_ENDPOINT = f"{API_URL}/estimate"
DECOMPOSE_ENDPOINT = f"{API_URL}/decompose"

# --- Page Configuration ---
st.set_page_config(page_title="Costell", page_icon="📊", layout="wide")

# --- Header ---
st.title("📊 Costell — AI Cost Estimation")
st.markdown("> *A constellation of signals that reveals your project's true cost.*")
st.markdown("---")


# ============================================================
# PDF Report Generator
# ============================================================
def generate_pdf_report(payload: dict, result: dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(30, 41, 59)
    pdf.rect(0, 0, 210, 30, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_y(8)
    pdf.cell(0, 12, "Costell - Project Cost Estimate", ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_y(35)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(
        0, 6, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C"
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "  Input Parameters", ln=True, fill=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.ln(2)
    for key, value in payload.items():
        label = key.replace("_", " ").title()
        value_str = f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(90, 7, f"  {label}:", border=0)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, value_str, ln=True)
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "  Effort Estimates (person-hours)", ln=True, fill=True)
    pdf.ln(2)
    for label, key in [
        ("P50 (Most Likely)", "p50_effort"),
        ("P80 Lower Bound", "p80_lower_effort"),
        ("P80 Upper Bound", "p80_upper_effort"),
    ]:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(90, 8, f"  {label}", border=0)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, f"{result[key]:,.0f} hrs", ln=True)
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "  Cost Breakdown (P50 Scenario)", ln=True, fill=True)
    pdf.ln(2)
    p50 = result["p50_cost"]
    for label, value in [
        ("Personnel Cost", p50["personnel_cost"]),
        ("Tooling Cost", p50["tooling_cost"]),
        ("Cloud/Infra Cost", p50["cloud_cost"]),
        ("Contingency", p50["contingency"]),
    ]:
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(90, 8, f"  {label}", border=0)
        pdf.cell(0, 8, f"Rs. {value:,.0f}", ln=True)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(220, 230, 241)
    pdf.cell(90, 10, "  TOTAL (P50)", border=0, fill=True)
    pdf.cell(0, 10, f"Rs. {p50['total_cost']:,.0f}", ln=True, fill=True)
    pdf.ln(8)
    safe_budget = result["p80_upper_cost"]["total_cost"]
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_fill_color(212, 237, 218)
    pdf.set_text_color(21, 87, 36)
    pdf.cell(0, 12, "  Safe Budget Recommendation", ln=True, fill=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.ln(2)
    pdf.multi_cell(
        0,
        8,
        f"  To be 80% confident the project stays within budget, plan for a safe budget of Rs. {safe_budget:,.0f}.",
    )
    pdf.set_text_color(0, 0, 0)
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
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["INPUT PARAMETERS"])
    for key, value in payload.items():
        writer.writerow([key.replace("_", " ").title(), value])
    writer.writerow([])
    writer.writerow(["EFFORT ESTIMATES (hours)"])
    writer.writerow(["P50", result["p50_effort"]])
    writer.writerow(["P80 Lower", result["p80_lower_effort"]])
    writer.writerow(["P80 Upper", result["p80_upper_effort"]])
    writer.writerow([])
    writer.writerow(["COST BREAKDOWN (P50, INR)"])
    p50 = result["p50_cost"]
    writer.writerow(["Personnel Cost", p50["personnel_cost"]])
    writer.writerow(["Tooling Cost", p50["tooling_cost"]])
    writer.writerow(["Cloud/Infra Cost", p50["cloud_cost"]])
    writer.writerow(["Contingency", p50["contingency"]])
    writer.writerow(["Total", p50["total_cost"]])
    writer.writerow([])
    writer.writerow(["SAFE BUDGET RECOMMENDATION (INR)"])
    writer.writerow(["P80 Upper Total", result["p80_upper_cost"]["total_cost"]])
    return "\ufeff" + output.getvalue()


# ============================================================
# SIDEBAR: Financial Parameters (always visible)
# ============================================================
st.sidebar.header("💰 Financial Parameters")
blended_hourly_rate = st.sidebar.number_input(
    "Blended Hourly Rate (Rs.)", min_value=100.0, value=2500.0, step=100.0
)
tooling_cost_per_month = st.sidebar.number_input(
    "Tooling Cost / Month (Rs.)", min_value=0.0, value=50000.0, step=5000.0
)
cloud_cost_per_month = st.sidebar.number_input(
    "Cloud/AI Infra / Month (Rs.)", min_value=0.0, value=80000.0, step=5000.0
)
contingency_percent = st.sidebar.slider(
    "Contingency Buffer (%)", min_value=0, max_value=40, value=15, step=1
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Project Parameters")
team_size = st.sidebar.number_input("Team Size", min_value=1, value=5, step=1)
duration = st.sidebar.number_input("Duration (months)", min_value=1, value=12, step=1)
language = st.sidebar.selectbox(
    "Primary Language / Dev Type",
    ["Python", "Java", "C++", "C#", "3GL", "4GL", "Assembly", "Unknown"],
    index=0,
)


# ============================================================
# MAIN: Effort Mode Selector
# ============================================================
st.markdown("## Step 1 — Determine Project Effort")
effort_mode = st.radio(
    "How would you like to determine the effort?",
    ["✍️ Manual Input", "🤖 AI Scope Decomposition"],
    horizontal=True,
)

# Initialize session state for effort and WBS
if "final_effort" not in st.session_state:
    st.session_state["final_effort"] = 1200.0
if "function_points" not in st.session_state:
    st.session_state["function_points"] = 450.0
if "wbs_data" not in st.session_state:
    st.session_state["wbs_data"] = None


# --- Path A: Manual Input ---
if effort_mode == "✍️ Manual Input":
    col1, col2 = st.columns(2)
    with col1:
        st.session_state["final_effort"] = st.number_input(
            "Estimated Effort (hours)",
            min_value=1.0,
            value=st.session_state["final_effort"],
            step=50.0,
        )
    with col2:
        st.session_state["function_points"] = st.number_input(
            "Adjusted Function Points (AFP)",
            min_value=1.0,
            value=st.session_state["function_points"],
            step=10.0,
        )


# --- Path B: AI Scope Decomposition ---
else:
    prd_text = st.text_area(
        "Paste your Product Requirement Document (PRD):",
        height=200,
        placeholder="Example: Build a food delivery app with user login, restaurant listing, cart, online payment, and order tracking...",
    )

    if st.button("🔍 Decompose Scope", type="primary"):
        if len(prd_text.strip()) < 50:
            st.warning("Please paste a longer PRD (at least 50 characters).")
        else:
            with st.spinner("Analyzing your PRD with the LLM..."):
                try:
                    response = requests.post(
                        DECOMPOSE_ENDPOINT, json={"prd_text": prd_text}, timeout=30
                    )
                    if response.status_code == 200:
                        st.session_state["wbs_data"] = response.json()
                    else:
                        st.error(f"API Error ({response.status_code}): {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Could not connect to the API. Is FastAPI running?")

    if st.session_state.get("wbs_data"):
        wbs = st.session_state["wbs_data"]

        st.markdown("### 📋 Project Summary")
        st.info(wbs["project_summary"])

        st.markdown("### 🗂️ Work Breakdown Structure")
        st.table(
            {
                "Task": [t["name"] for t in wbs["tasks"]],
                "Description": [t["description"] for t in wbs["tasks"]],
                "Complexity": [t["complexity"] for t in wbs["tasks"]],
                "Estimated Hours": [t["estimated_hours"] for t in wbs["tasks"]],
            }
        )

        total_hours = sum(t["estimated_hours"] for t in wbs["tasks"])
        total_tasks = len(wbs["tasks"])

        col1, col2 = st.columns(2)
        col1.metric("Total Tasks", total_tasks)
        col2.metric("Total Estimated Effort", f"{total_hours:,.0f} hrs")

        # Auto-populate the effort for the cost calculation
        st.session_state["final_effort"] = total_hours
        st.session_state["function_points"] = float(total_tasks * 45)  # Heuristic: ~45 FP per task

        st.success(
            f"✅ The estimated **{total_hours:,.0f} hours** from the WBS will be used for the cost calculation below."
        )


# ============================================================
# MAIN: Step 2 — Calculate Cost
# ============================================================
st.markdown("---")
st.markdown("## Step 2 — Calculate Project Cost")

if st.button("🚀 Calculate Full Project Cost", type="primary"):
    payload = {
        "estimated_effort": st.session_state["final_effort"],
        "team_size": float(team_size),
        "duration": float(duration),
        "function_points": st.session_state["function_points"],
        "language": language,
        "dataset_source": "user_input",
        "blended_hourly_rate": blended_hourly_rate,
        "tooling_cost_per_month": tooling_cost_per_month,
        "cloud_cost_per_month": cloud_cost_per_month,
        "contingency_percent": float(contingency_percent),
    }
    try:
        with st.spinner("Running ML model and financial calculations..."):
            response = requests.post(ESTIMATE_ENDPOINT, json=payload, timeout=15)
        if response.status_code == 200:
            st.session_state["payload"] = payload
            st.session_state["result"] = response.json()
            st.session_state["show_results"] = True
        else:
            st.error(f"API Error ({response.status_code}): {response.text}")
    except requests.exceptions.ConnectionError:
        st.error("❌ Could not connect to the API. Is FastAPI running?")


# ============================================================
# MAIN: Results
# ============================================================
if st.session_state.get("show_results"):
    data = st.session_state["result"]
    payload = st.session_state["payload"]

    st.markdown("---")
    st.markdown("## 💰 Prediction Results")

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

    safe_budget = data["p80_upper_cost"]["total_cost"]
    st.success(
        f"**Safe Budget Recommendation:** Request **₹{safe_budget:,.0f}** to be **80% confident** the project stays within budget."
    )

    st.markdown("### 📥 Download Report")
    col_pdf, col_csv, _ = st.columns([1, 1, 2])
    with col_pdf:
        st.download_button(
            "📄 Download PDF",
            data=generate_pdf_report(payload, data),
            file_name=f"costell_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with col_csv:
        st.download_button(
            "📊 Download CSV",
            data=generate_csv_report(payload, data),
            file_name=f"costell_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("### 📊 Cost Breakdown (P50 Scenario)")
    p50 = data["p50_cost"]
    st.table(
        {
            "Component": ["Personnel", "Tooling", "Cloud/Infra", "Contingency", "Total"],
            "Cost (INR)": [
                f"₹{p50['personnel_cost']:,.0f}",
                f"₹{p50['tooling_cost']:,.0f}",
                f"₹{p50['cloud_cost']:,.0f}",
                f"₹{p50['contingency']:,.0f}",
                f"₹{p50['total_cost']:,.0f}",
            ],
        }
    )

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=[data["p80_upper_cost"]["total_cost"] - data["p80_lower_cost"]["total_cost"]],
            y=["Project Cost"],
            base=[data["p80_lower_cost"]["total_cost"]],
            orientation="h",
            marker=dict(color="rgba(100, 149, 237, 0.5)"),
            name="P80 Range",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[data["p50_cost"]["total_cost"]],
            y=["Project Cost"],
            mode="markers",
            marker=dict(color="red", size=18, symbol="diamond"),
            name="P50 (Most Likely)",
        )
    )
    fig.update_layout(
        title="Total Project Cost with 80% Confidence Interval",
        xaxis_title="Cost (INR)",
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

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
