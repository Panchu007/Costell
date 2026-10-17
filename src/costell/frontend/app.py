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

# --- Page Configuration ---
st.set_page_config(page_title="Costell", page_icon="📊", layout="wide")

# --- Header ---
st.title("📊 Costell — AI Cost Estimation")
st.markdown("> *A constellation of signals that reveals your project's true cost.*")
st.markdown("---")


# ============================================================
# PDF Report Generator (Kept from previous)
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
# CSV Export Helper (Kept from previous)
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
tab1, tab2, tab3 = st.tabs(["💰 Estimation", "📜 History & KPIs", "🔬 Model Comparison"])


# ============================================================
# TAB 1: Estimation (Kept from previous)
# ============================================================
with tab1:
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

    project_name = st.text_input("📝 Project Name", value="Untitled Project")

    st.markdown("## Step 1 — Determine Project Effort")
    effort_mode = st.radio(
        "How would you like to determine the effort?",
        ["✍️ Manual Input", "🤖 AI Scope Decomposition"],
        horizontal=True,
    )

    if "final_effort" not in st.session_state:
        st.session_state["final_effort"] = 1200.0
    if "function_points" not in st.session_state:
        st.session_state["function_points"] = 450.0
    if "wbs_data" not in st.session_state:
        st.session_state["wbs_data"] = None

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
    else:
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
            st.session_state["final_effort"] = total_hours
            st.session_state["function_points"] = float(total_tasks * 45)
            st.success(
                f"✅ The estimated **{total_hours:,.0f} hours** from the WBS will be used for the cost calculation below."
            )

    st.markdown("---")
    st.markdown("## Step 2 — Calculate Project Cost")
    if st.button("🚀 Calculate Full Project Cost", type="primary"):
        payload = {
            "project_name": project_name,
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
                st.success("✅ Estimate saved to database! View it in the **📜 History** tab.")
            else:
                st.error(f"API Error ({response.status_code}): {response.text}")
        except requests.exceptions.ConnectionError:
            st.error("❌ Could not connect to the API.")

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
# TAB 2: History & KPIs (Kept from previous)
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
        st.caption("After a project is complete, log the actuals here to track variance over time.")
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
        st.caption("Calculated from all projects with logged actuals.")
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


# ============================================================
# TAB 3: Model Comparison & Monte-Carlo
# ============================================================
with tab3:
    st.header("🔬 Model Comparison & Monte-Carlo Simulation")
    st.markdown(
        "Run the same project through all four estimation models: "
        "**ML (CatBoost)**, **COCOMO II**, **Analogy (k-NN)**, and **Monte-Carlo**."
    )

    if "payload" not in st.session_state or "result" not in st.session_state:
        st.info(
            "👈 Please run an estimate in the **💰 Estimation** tab first to populate the inputs."
        )
    else:
        payload = st.session_state["payload"]
        st.markdown("### Inputs (from Tab 1)")
        st.json(payload, expanded=False)

        if st.button("🔬 Run All Models Comparison", type="primary"):
            with st.spinner("Running all models..."):
                try:
                    # 1. CatBoost (already in session state)
                    ml_effort = st.session_state["result"]["p50_effort"]

                    # 2. COCOMO II
                    cocomo_payload = {
                        "function_points": payload["function_points"],
                        "language": payload["language"],
                    }
                    cocomo_res = requests.post(
                        COCOMO_ENDPOINT, json=cocomo_payload, timeout=10
                    ).json()
                    cocomo_effort = cocomo_res["effort_hours"]

                    # 3. Analogy (k-NN)
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

                    # 4. Monte Carlo
                    mc_payload = {**payload, "n_simulations": 10000}
                    mc_res = requests.post(MONTE_CARLO_ENDPOINT, json=mc_payload, timeout=20)

                    if mc_res.status_code == 200:
                        mc_data = mc_res.json()

                        # --- Display Comparison Table ---
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
                        # --- Analyst's Note: Why ML Wins ---
                        st.markdown("### 🧐 Analyst's Note: Why the models differ")

                        # Calculate the percentage differences dynamically
                        diff_cocomo = ((cocomo_effort - ml_effort) / ml_effort) * 100
                        diff_analogy = ((analogy_effort - ml_effort) / ml_effort) * 100

                        st.info(
                            f"**1. CatBoost (ML) is the Primary Model:** It estimates **{ml_effort:,.0f} hours**. "
                            f"This model is trained on 589 historical projects and learns complex, non-linear relationships "
                            f"between team size, duration, and function points. It smooths out outliers to provide the most realistic baseline."
                        )

                        st.warning(
                            f"**2. COCOMO II is a Legacy Baseline:** It estimated **{cocomo_effort:,.0f} hours** "
                            f"(*{diff_cocomo:+.1f}% compared to ML*). COCOMO II is a rigid, formula-based model designed in the 1980s for "
                            f"Waterfall development. It assumes massive amounts of boilerplate code and lacks the flexibility to "
                            f"account for modern agile workflows or AI-assisted coding, leading to severe overestimation."
                        )

                        st.error(
                            f"**3. Analogy (k-NN) is Susceptible to Outliers:** It estimated **{analogy_effort:,.0f} hours** "
                            f"(*{diff_analogy:+.1f}% compared to ML*). This model simply averages the 3 most similar historical projects. "
                            f"If even one of those past projects was a catastrophic failure (e.g., took 10,000 hours), it skews the entire "
                            f"average. This proves why pure analogy is risky without ML correction."
                        )

                        st.success(
                            f"**4. Monte-Carlo uses ML as its Base:** It doesn't estimate effort from scratch. It takes the CatBoost P50 "
                            f"estimate (**{ml_effort:,.0f} hours**) and runs 10,000 simulations to generate the risk thresholds. "
                            f"This hybrid approach gives you both an accurate point estimate AND a safe budget range."
                        )

                        # --- Display Monte-Carlo Histogram ---
                        st.markdown("### 🎲 Monte-Carlo Cost Distribution")
                        st.markdown(
                            f"Ran **{mc_data['n_simulations']:,}** simulations. "
                            f"The **P80 safe budget** is **₹{mc_data['percentiles']['P80']:,.0f}**."
                        )

                        # Create histogram
                        fig_mc = go.Figure(
                            data=[
                                go.Histogram(
                                    x=mc_data["histogram_sample"],
                                    nbinsx=50,
                                    marker_color="rgba(100, 149, 237, 0.7)",
                                )
                            ]
                        )

                        # Add vertical lines for P50, P80, P95
                        colors = {"P50": "orange", "P80": "red", "P95": "darkred"}
                        for pct, col in colors.items():
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
                            showlegend=False,
                            height=400,
                            margin=dict(l=20, r=20, t=50, b=20),
                        )
                        st.plotly_chart(fig_mc, use_container_width=True)

                        # --- Display Percentiles ---
                        st.markdown("### 📈 Risk Thresholds (Cost)")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("P50 (Median)", f"₹{mc_data['percentiles']['P50']:,.0f}")
                        c2.metric("P80 (Safe)", f"₹{mc_data['percentiles']['P80']:,.0f}")
                        c3.metric("P90 (Conservative)", f"₹{mc_data['percentiles']['P90']:,.0f}")
                        c4.metric("P95 (Worst-Case)", f"₹{mc_data['percentiles']['P95']:,.0f}")

                    else:
                        st.error(f"Monte-Carlo API Error: {mc_res.text}")

                except requests.exceptions.ConnectionError:
                    st.error("❌ Could not connect to the API.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")


# --- Footer ---
st.markdown("---")
st.caption("Costell v0.1.0 | Built for the AI-native development era.")
