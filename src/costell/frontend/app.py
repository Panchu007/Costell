"""Streamlit frontend for the Costell estimation engine."""

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
HISTORY_ENDPOINT = f"{API_URL}/history"
KPIS_ENDPOINT = f"{API_URL}/kpis"
COCOMO_ENDPOINT = f"{API_URL}/baselines/cocomo"
ANALOGY_ENDPOINT = f"{API_URL}/baselines/analogy"
MONTE_CARLO_ENDPOINT = f"{API_URL}/baselines/monte-carlo"
JIRA_ENDPOINT = f"{API_URL}/integrations/jira/upload"

# --- Page Configuration ---
st.set_page_config(page_title="Costell", page_icon="📊", layout="wide")

# --- Initialize Session State for Inputs ---
if "manual_effort" not in st.session_state:
    st.session_state["manual_effort"] = 1200.0
if "manual_fp" not in st.session_state:
    st.session_state["manual_fp"] = 450.0
if "wbs_data" not in st.session_state:
    st.session_state["wbs_data"] = None
if "show_results" not in st.session_state:
    st.session_state["show_results"] = False

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
# TABS
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs(
    ["💰 Estimation", "📜 History & KPIs", "🔬 Model Comparison", "🎛️ Scenario Planner"]
)


# ============================================================
# TAB 1: Estimation
# ============================================================
with tab1:
    # --- Sidebar ---
    st.sidebar.header("💰 Financial Parameters")
    blended_hourly_rate = st.sidebar.number_input(
        "Blended Hourly Rate (Rs.)", min_value=100.0, value=2500.0, step=100.0, key="sb_rate"
    )
    tooling_cost_per_month = st.sidebar.number_input(
        "Tooling Cost / Month (Rs.)", min_value=0.0, value=50000.0, step=5000.0, key="sb_tool"
    )
    cloud_cost_per_month = st.sidebar.number_input(
        "Cloud/AI Infra / Month (Rs.)", min_value=0.0, value=80000.0, step=5000.0, key="sb_cloud"
    )
    contingency_percent = st.sidebar.slider(
        "Contingency Buffer (%)", min_value=0, max_value=40, value=15, step=1, key="sb_cont"
    )

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Project Parameters")
    team_size = st.sidebar.number_input("Team Size", min_value=1, value=5, step=1, key="sb_team")
    duration = st.sidebar.number_input(
        "Duration (months)", min_value=1, value=12, step=1, key="sb_dur"
    )
    language = st.sidebar.selectbox(
        "Primary Language / Dev Type",
        ["Python", "Java", "C++", "C#", "3GL", "4GL", "Assembly", "Unknown"],
        index=0,
        key="sb_lang",
    )

    # --- Main Area ---
    project_name = st.text_input("📝 Project Name", value="Untitled Project", key="proj_name")

    st.markdown("## Step 1 — Determine Project Effort")
    effort_mode = st.radio(
        "How would you like to determine the effort?",
        ["✍️ Manual / Jira Input", "🤖 AI Scope Decomposition"],
        horizontal=True,
    )

    # --- Jira CSV Upload (Inside Manual/Jira Mode) ---
    if effort_mode == "✍️ Manual / Jira Input":
        with st.expander("📁 Import Effort from Jira (CSV)"):
            st.markdown(
                "Upload a Jira CSV export to automatically calculate effort from Story Points."
            )
            uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

            if uploaded_file is not None:
                if st.button("Parse Jira CSV"):
                    with st.spinner("Parsing CSV..."):
                        try:
                            files = {
                                "file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")
                            }
                            response = requests.post(JIRA_ENDPOINT, files=files)

                            if response.status_code == 200:
                                data = response.json()
                                st.success(f"✅ Successfully parsed {data['task_count']} tasks!")
                                st.info(
                                    f"Extracted Effort: **{data['estimated_effort_hours']:,.0f} hours** (from {data['total_story_points']} story points)"
                                )

                                # Update session state and rerun
                                st.session_state["manual_effort"] = data["estimated_effort_hours"]
                                st.session_state["manual_fp"] = max(
                                    data["total_story_points"] * 45, 100.0
                                )
                                st.rerun()
                            else:
                                st.error(f"Error: {response.text}")
                        except Exception as e:
                            st.error(f"Failed to connect to API: {e}")

    # --- Effort Inputs (Shared by Manual and AI) ---
    if effort_mode == "✍️ Manual / Jira Input":
        col1, col2 = st.columns(2)
        with col1:
            st.number_input(
                "Estimated Effort (hours)", min_value=1.0, step=50.0, key="manual_effort"
            )
        with col2:
            st.number_input(
                "Adjusted Function Points (AFP)", min_value=1.0, step=10.0, key="manual_fp"
            )

    else:  # AI Scope Decomposition
        prd_text = st.text_area(
            "Paste your Product Requirement Document (PRD):",
            height=200,
            placeholder="Example: Build a food delivery app...",
        )

        if st.button("🔍 Decompose Scope", type="primary"):
            if len(prd_text.strip()) < 50:
                st.warning("Please paste a longer PRD.")
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
                        st.error("❌ Could not connect to the API.")

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

            if st.button("✅ Use this WBS for Cost Calculation"):
                st.session_state["manual_effort"] = total_hours
                st.session_state["manual_fp"] = float(total_tasks * 45)
                st.success(f"Effort set to {total_hours:,.0f} hours. Proceed to Step 2.")

    # --- Calculate Button ---
    st.markdown("---")
    st.markdown("## Step 2 — Calculate Project Cost")

    # Display currently selected effort
    st.caption(
        f"Current Effort Used for Calculation: **{st.session_state['manual_effort']:,.0f} hours** | **{st.session_state['manual_fp']:,.0f} FP**"
    )

    if st.button("🚀 Calculate Full Project Cost", type="primary"):
        payload = {
            "project_name": project_name,
            "estimated_effort": st.session_state["manual_effort"],
            "team_size": float(team_size),
            "duration": float(duration),
            "function_points": st.session_state["manual_fp"],
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
                st.success("✅ Estimate saved to database! View it in the **📜 History** tab.")
            else:
                st.error(f"API Error ({response.status_code}): {response.text}")
        except requests.exceptions.ConnectionError:
            st.error("❌ Could not connect to the API.")

    # --- Display Results ---
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


# ============================================================
# TAB 2: History & KPIs
# ============================================================
with tab2:
    st.header("📜 Project History & Variance Tracking")
    try:
        history_response = requests.get(HISTORY_ENDPOINT, timeout=10)
        history = history_response.json() if history_response.status_code == 200 else []
    except requests.exceptions.ConnectionError:
        st.error("❌ Could not connect to the API.")
        history = []

    if not history:
        st.info("No estimates yet. Create one in the **💰 Estimation** tab first.")
    else:
        st.markdown(f"### 🗂️ All Estimates ({len(history)} total)")
        st.dataframe(
            [
                {
                    "ID": r["id"],
                    "Project": r["project_name"],
                    "Created": r["created_at"][:10],
                    "P50 Effort (hrs)": f"{r['p50_effort']:,.0f}",
                    "Safe Budget (₹)": f"{r['safe_budget']:,.0f}",
                    "Actual Effort": f"{r['actual_effort']:,.0f}" if r["actual_effort"] else "—",
                    "Actual Cost (₹)": f"{r['actual_cost']:,.0f}" if r["actual_cost"] else "—",
                }
                for r in history
            ],
            use_container_width=True,
        )

        st.markdown("---")
        st.markdown("### ✏️ Log Actual Effort & Cost")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            selected_id = st.selectbox(
                "Select Project ID",
                options=[r["id"] for r in history],
                format_func=lambda x: (
                    f"#{x} — {next(r['project_name'] for r in history if r['id'] == x)}"
                ),
            )
        with col2:
            actual_effort = st.number_input(
                "Actual Effort (hrs)", min_value=1.0, value=2000.0, step=50.0
            )
        with col3:
            actual_cost = st.number_input(
                "Actual Cost (₹)", min_value=0.0, value=8000000.0, step=100000.0
            )

        if st.button("💾 Save Actuals"):
            try:
                patch_response = requests.patch(
                    f"{API_URL}/estimates/{selected_id}/actual",
                    json={"actual_effort": actual_effort, "actual_cost": actual_cost},
                    timeout=10,
                )
                if patch_response.status_code == 200:
                    st.success(f"✅ Actuals logged for Project #{selected_id}!")
                    st.rerun()
                else:
                    st.error(f"API Error ({patch_response.status_code}): {patch_response.text}")
            except requests.exceptions.ConnectionError:
                st.error("❌ Could not connect to the API.")

        st.markdown("---")
        st.markdown("### 📊 Variance KPIs")
        try:
            kpis_response = requests.get(KPIS_ENDPOINT, timeout=10)
            kpis = kpis_response.json() if kpis_response.status_code == 200 else {}
        except requests.exceptions.ConnectionError:
            kpis = {}

        if kpis.get("completed_projects", 0) == 0:
            st.info("Log at least one actual to see KPIs.")
        else:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Projects Tracked", kpis["completed_projects"])
            col2.metric("MMRE", f"{kpis['mmre'] * 100:.2f}%" if kpis["mmre"] is not None else "—")
            col3.metric(
                "PRED(25)", f"{kpis['pred_25'] * 100:.0f}%" if kpis["pred_25"] is not None else "—"
            )
            bias = kpis["bias"]
            bias_label = "Underestimate" if bias and bias < 0 else "Overestimate"
            col4.metric("Bias", f"{bias * 100:+.2f}%" if bias is not None else "—", bias_label)
            # --- Estimation Bias Chart ---
            st.markdown("---")
            st.markdown("### 📊 Estimate vs. Actual Effort (Variance)")

            # Filter history for projects that have actuals logged
            completed = [r for r in history if r.get("actual_effort") is not None]

            if completed:
                # Extract data for the chart
                names = [f"#{r['id']} {r['project_name'][:15]}" for r in completed]
                est_efforts = [r["p50_effort"] for r in completed]
                act_efforts = [r["actual_effort"] for r in completed]

                # Calculate variance percentages
                variances = [
                    ((act - est) / est) * 100 for est, act in zip(est_efforts, act_efforts)
                ]

                # Create the grouped bar chart
                fig_bias = go.Figure(
                    data=[
                        go.Bar(
                            name="Estimated (P50)", x=names, y=est_efforts, marker_color="#3b82f6"
                        ),
                        go.Bar(name="Actual", x=names, y=act_efforts, marker_color="#f97316"),
                    ]
                )

                fig_bias.update_layout(
                    title="Estimated vs Actual Effort per Project",
                    yaxis_title="Effort (Hours)",
                    barmode="group",
                    height=400,
                    margin=dict(l=20, r=20, t=50, b=20),
                )
                st.plotly_chart(fig_bias, use_container_width=True)

                # Display the variance percentage table
                st.markdown("#### Variance Breakdown")
                variance_data = []
                for i, r in enumerate(completed):
                    variance_data.append(
                        {
                            "Project": r["project_name"],
                            "Estimated": f"{est_efforts[i]:,.0f}",
                            "Actual": f"{act_efforts[i]:,.0f}",
                            "Variance": f"{variances[i]:+.1f}%",
                            "Status": "🔴 Underestimated"
                            if variances[i] > 0
                            else "🟢 Overestimated",
                        }
                    )
                st.table(variance_data)
            else:
                st.info("Log actuals for at least one project to see the variance chart.")


# ============================================================
# TAB 3: Model Comparison
# ============================================================
with tab3:
    st.header("🔬 Model Comparison & Monte-Carlo Simulation")

    if "payload" not in st.session_state or "result" not in st.session_state:
        st.info("👈 Please run an estimate in the **💰 Estimation** tab first.")
    else:
        payload = st.session_state["payload"]

        if st.button("🔬 Run All Models Comparison", type="primary"):
            with st.spinner("Running all models..."):
                try:
                    ml_effort = st.session_state["result"]["p50_effort"]

                    cocomo_res = requests.post(
                        COCOMO_ENDPOINT,
                        json={
                            "function_points": payload["function_points"],
                            "language": payload["language"],
                        },
                        timeout=10,
                    ).json()
                    cocomo_effort = cocomo_res["effort_hours"]

                    analogy_payload = {
                        "function_points": payload["function_points"],
                        "team_size": payload["team_size"],
                        "duration": payload["duration"],
                        "k_neighbors": 3,
                    }
                    analogy_res = requests.post(
                        ANALOGY_ENDPOINT, json=analogy_payload, timeout=10
                    ).json()
                    analogy_effort = analogy_res["estimated_effort_hours"]

                    mc_payload = {**payload, "n_simulations": 10000}
                    mc_res = requests.post(MONTE_CARLO_ENDPOINT, json=mc_payload, timeout=20)

                    if mc_res.status_code == 200:
                        mc_data = mc_res.json()

                        st.markdown("### 📊 Effort Comparison (Hours)")
                        comparison_df = {
                            "Model": [
                                "CatBoost (ML)",
                                "COCOMO II",
                                "Analogy (k-NN)",
                                "Monte-Carlo (P50)",
                            ],
                            "Estimated Effort (hrs)": [
                                f"{ml_effort:,.0f}",
                                f"{cocomo_effort:,.0f}",
                                f"{analogy_effort:,.0f}",
                                f"{mc_data['base_p50_effort']:,.0f}",
                            ],
                        }
                        st.table(comparison_df)

                        st.markdown("### 🧐 Analyst's Note")
                        diff_cocomo = ((cocomo_effort - ml_effort) / ml_effort) * 100
                        diff_analogy = ((analogy_effort - ml_effort) / ml_effort) * 100

                        st.info(
                            f"**1. CatBoost (ML) is the Primary Model:** It estimates **{ml_effort:,.0f} hours**. Trained on 589 historical projects to smooth out outliers."
                        )
                        st.warning(
                            f"**2. COCOMO II is a Legacy Baseline:** It estimated **{cocomo_effort:,.0f} hours** (*{diff_cocomo:+.1f}% compared to ML*). It overestimates because it assumes 1980s Waterfall development."
                        )
                        st.error(
                            f"**3. Analogy (k-NN) is Susceptible to Outliers:** It estimated **{analogy_effort:,.0f} hours** (*{diff_analogy:+.1f}% compared to ML*). Averaging past projects can skew the result if one project was a disaster."
                        )
                        st.success(
                            f"**4. Monte-Carlo uses ML as its Base:** It takes the CatBoost estimate (**{ml_effort:,.0f} hours**) and simulates 10,000 scenarios for risk thresholds."
                        )

                        st.markdown("### 🎲 Monte-Carlo Cost Distribution")
                        fig_mc = go.Figure(
                            data=[
                                go.Histogram(
                                    x=mc_data["histogram_sample"],
                                    nbinsx=50,
                                    marker_color="rgba(100, 149, 237, 0.7)",
                                )
                            ]
                        )
                        for pct, col in {"P50": "orange", "P80": "red", "P95": "darkred"}.items():
                            fig_mc.add_vline(
                                x=mc_data["percentiles"][pct],
                                line_dash="dash",
                                line_color=col,
                                annotation_text=f"{pct} (₹{mc_data['percentiles'][pct] / 1000000:.1f}M)",
                                annotation_position="top",
                            )
                        fig_mc.update_layout(
                            title="Simulated Total Cost Distribution",
                            xaxis_title="Total Cost (INR)",
                            yaxis_title="Frequency",
                            height=400,
                        )
                        st.plotly_chart(fig_mc, use_container_width=True)

                        st.markdown("### 📈 Risk Thresholds (Cost)")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("P50 (Median)", f"₹{mc_data['percentiles']['P50']:,.0f}")
                        c2.metric("P80 (Safe)", f"₹{mc_data['percentiles']['P80']:,.0f}")
                        c3.metric("P90 (Conservative)", f"₹{mc_data['percentiles']['P90']:,.0f}")
                        c4.metric("P95 (Worst-Case)", f"₹{mc_data['percentiles']['P95']:,.0f}")

                except Exception as e:
                    st.error(f"An error occurred: {e}")


# ============================================================
# TAB 4: Scenario Planner
# ============================================================
with tab4:
    st.header("🎛️ Scenario Planner")
    st.markdown("Compare a **Baseline** plan against a **What-If Scenario**.")

    if "manual_effort" not in st.session_state:
        st.warning("Please run an estimate in the 💰 Estimation tab first.")
    else:
        base_effort = st.session_state["manual_effort"]
        base_fp = st.session_state["manual_fp"]

        col_base, col_scenario = st.columns(2)

        with col_base:
            st.markdown("### 🟦 Baseline Plan")
            base_team = st.number_input("Team Size", min_value=1, value=5, step=1, key="base_team")
            base_duration = st.number_input(
                "Duration (months)", min_value=1, value=12, step=1, key="base_dur"
            )
            base_rate = st.number_input(
                "Hourly Rate (₹)", min_value=100.0, value=2500.0, step=100.0, key="base_rate"
            )
            base_tooling = st.number_input(
                "Tooling / Month (₹)", min_value=0.0, value=50000.0, step=5000.0, key="base_tool"
            )
            base_cloud = st.number_input(
                "Cloud / Month (₹)", min_value=0.0, value=80000.0, step=5000.0, key="base_cloud"
            )

        with col_scenario:
            st.markdown("### 🟧 What-If Scenario")
            scen_team = st.number_input("Team Size", min_value=1, value=8, step=1, key="scen_team")
            scen_duration = st.number_input(
                "Duration (months)", min_value=1, value=8, step=1, key="scen_dur"
            )
            scen_rate = st.number_input(
                "Hourly Rate (₹)", min_value=100.0, value=3000.0, step=100.0, key="scen_rate"
            )
            scen_tooling = st.number_input(
                "Tooling / Month (₹)", min_value=0.0, value=50000.0, step=5000.0, key="scen_tool"
            )
            scen_cloud = st.number_input(
                "Cloud / Month (₹)", min_value=0.0, value=80000.0, step=5000.0, key="scen_cloud"
            )

        if st.button("⚖️ Compare Scenarios", type="primary"):
            with st.spinner("Calculating scenarios..."):
                try:
                    base_payload = {
                        "project_name": "Baseline",
                        "estimated_effort": base_effort,
                        "team_size": float(base_team),
                        "duration": float(base_duration),
                        "function_points": base_fp,
                        "language": "Python",
                        "dataset_source": "user_input",
                        "blended_hourly_rate": base_rate,
                        "tooling_cost_per_month": base_tooling,
                        "cloud_cost_per_month": base_cloud,
                        "contingency_percent": 15.0,
                    }
                    scen_payload = base_payload.copy()
                    scen_payload.update(
                        {
                            "project_name": "Scenario A",
                            "team_size": float(scen_team),
                            "duration": float(scen_duration),
                            "blended_hourly_rate": scen_rate,
                            "tooling_cost_per_month": scen_tooling,
                            "cloud_cost_per_month": scen_cloud,
                        }
                    )

                    res_base = requests.post(ESTIMATE_ENDPOINT, json=base_payload).json()
                    res_scen = requests.post(ESTIMATE_ENDPOINT, json=scen_payload).json()

                    b_p50, b_p80 = (
                        res_base["p50_cost"]["total_cost"],
                        res_base["p80_upper_cost"]["total_cost"],
                    )
                    s_p50, s_p80 = (
                        res_scen["p50_cost"]["total_cost"],
                        res_scen["p80_upper_cost"]["total_cost"],
                    )

                    st.markdown("### 📊 Cost Comparison")
                    fig = go.Figure(
                        data=[
                            go.Bar(
                                name="Baseline",
                                x=["P50 (Most Likely)", "P80 (Safe Budget)"],
                                y=[b_p50, b_p80],
                                marker_color="#3b82f6",
                            ),
                            go.Bar(
                                name="Scenario A",
                                x=["P50 (Most Likely)", "P80 (Safe Budget)"],
                                y=[s_p50, s_p80],
                                marker_color="#f97316",
                            ),
                        ]
                    )
                    fig.update_layout(
                        barmode="group",
                        title="Baseline vs Scenario Cost",
                        yaxis_title="Cost (INR)",
                        height=400,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    st.markdown("### 💡 Financial Impact")
                    delta_p50, delta_p80 = s_p50 - b_p50, s_p80 - b_p80
                    c1, c2 = st.columns(2)
                    c1.metric(
                        "P50 Difference", f"₹{delta_p50:,.0f}", f"{delta_p50 / b_p50 * 100:+.1f}%"
                    )
                    c2.metric(
                        "P80 Difference", f"₹{delta_p80:,.0f}", f"{delta_p80 / b_p80 * 100:+.1f}%"
                    )

                    if delta_p80 < 0:
                        st.success(
                            f"✅ **Scenario A saves ₹{abs(delta_p80):,.0f}** compared to Baseline."
                        )
                    else:
                        st.warning(f"⚠️ **Scenario A costs ₹{delta_p80:,.0f} more** than Baseline.")

                except Exception as e:
                    st.error(f"Error calculating scenarios: {e}")


# --- Footer ---
st.markdown("---")
st.caption("Costell v0.1.0 | Built for the AI-native development era.")
