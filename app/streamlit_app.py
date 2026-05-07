import streamlit as st
import pandas as pd
from pathlib import Path

from adapters.sqlite_reader import SQLiteReader
from utils.paths import SQLITE_DB_PATH
from app.ui_helpers import (
    format_currency,
    format_percentage,
    select_metric_value,
    status_badge_text,
    format_file_size,
    format_timestamp,
    db_status_label,
    safe_dataframe_empty_message,
    get_filter_options,
    filter_dataframe_by_values,
    prepare_metric_chart_data,
    prepare_status_counts,
    prepare_category_counts
)

# ── Page Configuration ──────────────────────────────────────────────────
st.set_page_config(
    page_title="ProductPulse",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── DB Status & Initialization ──────────────────────────────────────────
db_path = Path(SQLITE_DB_PATH)
db_exists = db_path.exists()
db_mtime = db_path.stat().st_mtime if db_exists else None
db_size = db_path.stat().st_size if db_exists else None

@st.cache_resource
def get_reader() -> SQLiteReader | None:
    try:
        return SQLiteReader(SQLITE_DB_PATH)
    except FileNotFoundError:
        return None

reader = get_reader()

# ── Safe Data Loader ────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def fetch_data(_reader: SQLiteReader, method_name: str, _mtime: float | None, **kwargs) -> pd.DataFrame:
    if not _reader:
        return pd.DataFrame()
    try:
        method = getattr(_reader, method_name)
        return method(**kwargs)
    except Exception as e:
        st.error(f"Failed to load data ({method_name}): {str(e)}")
        return pd.DataFrame()

# ── Sidebar Navigation & Status ─────────────────────────────────────────
st.sidebar.title("ProductPulse")
st.sidebar.caption("Business Product Analytics")

st.sidebar.divider()
st.sidebar.markdown(f"**DB Status:** {db_status_label(db_exists)}")
if db_exists:
    st.sidebar.caption(f"Last updated: {format_timestamp(db_mtime)}")
    st.sidebar.caption(f"File size: {format_file_size(db_size)}")
else:
    st.sidebar.caption("Missing local database.")

st.sidebar.divider()

pages = [
    "Executive Overview",
    "KPI Summary",
    "Product / Business Health",
    "High-Risk Customers",
    "Recommendations",
    "Intervention Plan",
    "Decision Traces",
    "Metric Lineage"
]

selection = st.sidebar.radio("Navigation", pages)

st.sidebar.divider()
st.sidebar.caption("Local-only mode. No data leaves this machine.")

# ── Missing DB Handling ─────────────────────────────────────────────────
if not db_exists or not reader:
    st.title("ProductPulse")
    st.warning(f"Local SQLite database was not found at `{SQLITE_DB_PATH}`.")
    st.info("Run the pipeline with SQLite persistence enabled, then reload this page.")
    st.code('''
# Ensure persistence.sqlite.enabled is true in config/config.yaml
export PYTHONPATH=src
python src/main.py
''', language="bash")
    st.stop()

# ── Main Content ────────────────────────────────────────────────────────
st.title(selection)

if selection == "Executive Overview":
    kpis = fetch_data(reader, "get_kpi_summary", db_mtime)
    
    st.subheader("Key Business Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        mrr = select_metric_value(kpis, "Total MRR")
        st.metric("Total MRR", format_currency(mrr) if mrr is not None else "N/A")
        
    with col2:
        churn = select_metric_value(kpis, "Churn Rate")
        st.metric("Churn Rate", format_percentage(churn) if churn is not None else "N/A")
        
    with col3:
        arpu = select_metric_value(kpis, "ARPU")
        st.metric("ARPU", format_currency(arpu) if arpu is not None else "N/A")
        
    with col4:
        risk = select_metric_value(kpis, "Revenue at Risk")
        st.metric("Revenue at Risk", format_currency(risk) if risk is not None else "N/A")
        
    st.divider()
    
    col_h1, col_h2 = st.columns([1, 1])
    
    with col_h1:
        st.subheader("Critical Health Areas")
        critical_health = fetch_data(reader, "get_critical_health_scores", db_mtime)
        if not critical_health.empty:
            for _, row in critical_health.iterrows():
                st.error(f"**{row['area']}** (Score: {row['score']}) - {row['explanation']}")
        else:
            st.success("No critical health areas detected.")
            
    with col_h2:
        st.subheader("Top Priority Recommendations")
        top_recs = fetch_data(reader, "get_top_recommendations", db_mtime, limit=3)
        if not top_recs.empty:
            for _, row in top_recs.iterrows():
                impact = format_currency(row.get('estimated_revenue_impact', 0))
                st.info(f"**{row['recommendation_title']}** ({row['category']}) - Impact: {impact}")
        else:
            st.write("No recommendations generated.")

elif selection == "KPI Summary":
    st.write("Complete breakdown of calculated KPIs based on operational signals.")
    kpis = fetch_data(reader, "get_kpi_summary", db_mtime)
    if not kpis.empty:
        col1, col2 = st.columns(2)
        with col1:
            if "metric_name" in kpis.columns:
                search_term = st.text_input("Search Metric", "")
                if search_term:
                    kpis = kpis[kpis["metric_name"].str.contains(search_term, case=False, na=False)]
        with col2:
            if "category" in kpis.columns:
                options = get_filter_options(kpis, "category")
                selected = st.multiselect("Category", options)
                kpis = filter_dataframe_by_values(kpis, "category", selected)
                
        chart_data = prepare_metric_chart_data(kpis)
        if not chart_data.empty:
            st.bar_chart(chart_data)
            
        st.dataframe(kpis, use_container_width=True, hide_index=True)
    else:
        st.info(safe_dataframe_empty_message(kpis, "KPI summary"))

elif selection == "Product / Business Health":
    st.write("Calculated health scores for major product and business areas.")
    health = fetch_data(reader, "get_health_scores", db_mtime)
    if not health.empty:
        if "status" in health.columns:
            options = get_filter_options(health, "status")
            selected = st.multiselect("Status", options)
            health = filter_dataframe_by_values(health, "status", selected)
            
            counts = prepare_status_counts(health, "status")
            if not counts.empty:
                st.bar_chart(counts)
                
        display_health = health.copy()
        if "status" in display_health.columns:
            display_health["status"] = display_health["status"].apply(status_badge_text)
        st.dataframe(display_health, use_container_width=True, hide_index=True)
    else:
        st.info(safe_dataframe_empty_message(health, "health score"))

elif selection == "High-Risk Customers":
    st.write("Customers prioritized by churn risk algorithms.")
    high_risk = fetch_data(reader, "get_high_risk_customers", db_mtime)
    if not high_risk.empty:
        cols = st.columns(4)
        col_idx = 0
        
        if "risk_band" in high_risk.columns:
            with cols[col_idx % 4]:
                options = get_filter_options(high_risk, "risk_band")
                selected = st.multiselect("Risk Band", options)
                high_risk = filter_dataframe_by_values(high_risk, "risk_band", selected)
            col_idx += 1
            
        for segment in ["revenue_segment", "usage_segment", "risk_segment", "nps_segment"]:
            if segment in high_risk.columns:
                with cols[col_idx % 4]:
                    options = get_filter_options(high_risk, segment)
                    selected = st.multiselect(segment.replace("_", " ").title(), options)
                    high_risk = filter_dataframe_by_values(high_risk, segment, selected)
                col_idx += 1
                
        if "risk_band" in high_risk.columns:
            counts = prepare_category_counts(high_risk, "risk_band")
            if not counts.empty:
                st.bar_chart(counts)
                
        st.dataframe(high_risk, use_container_width=True, hide_index=True)
    else:
        st.success("No high-risk customers identified.")

elif selection == "Recommendations":
    st.write("Rule-based business interventions targeted at high-value or at-risk segments.")
    recs = fetch_data(reader, "get_recommendations", db_mtime)
    if not recs.empty:
        col1, col2 = st.columns(2)
        with col1:
            if "confidence_level" in recs.columns:
                options = get_filter_options(recs, "confidence_level")
                selected = st.multiselect("Confidence Level", options)
                recs = filter_dataframe_by_values(recs, "confidence_level", selected)
        with col2:
            if "category" in recs.columns:
                options = get_filter_options(recs, "category")
                selected = st.multiselect("Category", options)
                recs = filter_dataframe_by_values(recs, "category", selected)
                
        if "impact_score" in recs.columns and "recommendation_title" in recs.columns:
            chart_data = prepare_metric_chart_data(recs, metric_column="recommendation_title", value_column="impact_score")
            if not chart_data.empty:
                st.bar_chart(chart_data)
        elif "priority_score" in recs.columns and "recommendation_title" in recs.columns:
            chart_data = prepare_metric_chart_data(recs, metric_column="recommendation_title", value_column="priority_score")
            if not chart_data.empty:
                st.bar_chart(chart_data)
                
        st.dataframe(recs, use_container_width=True, hide_index=True)
    else:
        st.info(safe_dataframe_empty_message(recs, "recommendations"))

elif selection == "Intervention Plan":
    st.write("Strategic plan grouped by impact and effort.")
    plan = fetch_data(reader, "get_intervention_plan", db_mtime)
    if not plan.empty:
        cols = st.columns(3)
        col_idx = 0
        for col_name in ["priority_band", "effort_level", "suggested_owner", "status"]:
            if col_name in plan.columns:
                with cols[col_idx % 3]:
                    options = get_filter_options(plan, col_name)
                    selected = st.multiselect(col_name.replace("_", " ").title(), options)
                    plan = filter_dataframe_by_values(plan, col_name, selected)
                col_idx += 1
                
        if "priority_band" in plan.columns:
            counts = prepare_category_counts(plan, "priority_band")
            if not counts.empty:
                st.bar_chart(counts)
        elif "effort_level" in plan.columns:
            counts = prepare_category_counts(plan, "effort_level")
            if not counts.empty:
                st.bar_chart(counts)
                
        display_plan = plan.copy()
        if "priority_band" in display_plan.columns:
            display_plan["priority_band"] = display_plan["priority_band"].apply(status_badge_text)
        st.dataframe(display_plan, use_container_width=True, hide_index=True)
    else:
        st.info(safe_dataframe_empty_message(plan, "intervention plan"))

elif selection == "Decision Traces":
    st.write("Audit log of all decisions, triggers, and the explicit signals that caused them.")
    traces = fetch_data(reader, "get_decision_traces", db_mtime)
    if not traces.empty:
        st.dataframe(traces, use_container_width=True, hide_index=True)
    else:
        st.info(safe_dataframe_empty_message(traces, "decision traces"))

elif selection == "Metric Lineage":
    st.write("Governance view of all tracked metrics, their formula descriptions, and ownership.")
    lineage = fetch_data(reader, "get_metric_lineage", db_mtime)
    if not lineage.empty:
        cols = st.columns(3)
        col_idx = 0
        for col_name in ["implementation_status", "category", "source_datasets"]:
            if col_name in lineage.columns:
                with cols[col_idx % 3]:
                    options = get_filter_options(lineage, col_name)
                    selected = st.multiselect(col_name.replace("_", " ").title(), options)
                    lineage = filter_dataframe_by_values(lineage, col_name, selected)
                col_idx += 1
                
        st.dataframe(lineage, use_container_width=True, hide_index=True)
    else:
        st.info(safe_dataframe_empty_message(lineage, "metric lineage"))

st.divider()
if st.button("Show refresh instructions"):
    st.info("To refresh data, run the following in your terminal:\\n`export PYTHONPATH=src && python src/main.py`\\nThen reload this page.")
