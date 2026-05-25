import streamlit as st
import pandas as pd
from pathlib import Path

from adapters.sqlite_reader import SQLiteReader
from utils.paths import SQLITE_DB_PATH
from app.ui_helpers import (
    build_demo_readiness_summary,
    db_status_label,
    format_file_size,
    format_timestamp,
    safe_dataframe_empty_message,
)
from app.views_executive import render_executive_cockpit, render_top_actions_page
from app.views_customer import (
    render_customer_360,
    render_high_risk_customers,
    render_recommendations,
    render_intervention_plan,
)
from app.views_analytics import (
    render_kpi_summary,
    render_scenario_simulator,
    render_cohort_retention,
    render_funnel_analysis,
)
from app.views_governance import (
    render_data_quality,
    render_product_business_health,
    render_decision_traces,
    render_metric_lineage,
)

# ── Page Configuration ──────────────────────────────────────────────────
st.set_page_config(
    page_title="ProductPulse", page_icon="📈", layout="wide", initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetric"] {
        border: 1px solid rgba(49, 51, 63, 0.16);
        border-radius: 8px;
        padding: 12px 14px;
        background: rgba(250, 250, 250, 0.65);
    }
    </style>
    """,
    unsafe_allow_html=True,
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
def fetch_data(
    _reader: SQLiteReader, method_name: str, _mtime: float | None, **kwargs
) -> pd.DataFrame:
    if not _reader:
        return pd.DataFrame()
    try:
        method = getattr(_reader, method_name)
        return method(**kwargs)
    except Exception as e:
        st.error(
            f"Failed to load data for `{method_name}`. "
            f"Run `make run`, then reload this page. Details: {str(e)}"
        )
        return pd.DataFrame()


@st.cache_data(show_spinner=False)
def fetch_table_inventory(_reader: SQLiteReader | None, _mtime: float | None) -> pd.DataFrame:
    if not _reader:
        return pd.DataFrame(columns=["table", "rows"])

    rows = []
    try:
        table_names = sorted(_reader.list_tables())
    except Exception as e:
        st.error(
            "Failed to load table inventory. Run `make run`, then reload this page. "
            f"Details: {str(e)}"
        )
        return pd.DataFrame(columns=["table", "rows"])

    for table_name in table_names:
        try:
            rows.append({"table": table_name, "rows": _reader.get_table_row_count(table_name)})
        except ValueError:
            continue
    return pd.DataFrame(rows)


sidebar_inventory = fetch_table_inventory(reader, db_mtime)
sidebar_total_rows = 0
if not sidebar_inventory.empty:
    sidebar_total_rows = int(pd.to_numeric(sidebar_inventory["rows"], errors="coerce").sum())
demo_readiness = build_demo_readiness_summary(
    db_exists,
    len(sidebar_inventory),
    sidebar_total_rows,
)


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

st.sidebar.markdown(f"**Demo:** {demo_readiness['status']}")
st.sidebar.caption(demo_readiness["summary"])
with st.sidebar.expander("Demo commands", expanded=False):
    st.code(
        """
make reset-demo
make dashboard
""",
        language="bash",
    )
    st.caption(demo_readiness["action"])

st.sidebar.divider()

pages = [
    "Executive Cockpit",
    "Top Actions",
    "Customer 360",
    "KPI Summary",
    "Data Quality",
    "Product / Business Health",
    "Scenario Simulator",
    "Cohort Retention",
    "Funnel Analysis",
    "High-Risk Customers",
    "Recommendations",
    "Intervention Plan",
    "Decision Traces",
    "Metric Lineage",
]

selection = st.sidebar.radio("Navigation", pages)

st.sidebar.divider()
st.sidebar.caption("Local-only mode. No data leaves this machine.")

# ── Missing DB Handling ─────────────────────────────────────────────────
if not db_exists or not reader:
    st.title("ProductPulse")
    st.warning(f"Local SQLite database was not found at `{SQLITE_DB_PATH}`.")
    st.info(safe_dataframe_empty_message(None, "dashboard database"))
    st.code(
        """
make reset-demo
make dashboard
""",
        language="bash",
    )
    st.stop()

# ── Main Content ────────────────────────────────────────────────────────
st.title(selection)

if selection == "Executive Cockpit":
    render_executive_cockpit(reader, db_mtime, db_size, sidebar_inventory, fetch_data)

elif selection == "Top Actions":
    render_top_actions_page(reader, db_mtime, fetch_data)

elif selection == "Customer 360":
    render_customer_360(reader, db_mtime, fetch_data)

elif selection == "KPI Summary":
    render_kpi_summary(reader, db_mtime, fetch_data)

elif selection == "Data Quality":
    render_data_quality(reader, db_mtime, fetch_data)

elif selection == "Product / Business Health":
    render_product_business_health(reader, db_mtime, fetch_data)

elif selection == "Scenario Simulator":
    render_scenario_simulator(reader, db_mtime, fetch_data)

elif selection == "Cohort Retention":
    render_cohort_retention(reader, db_mtime, fetch_data)

elif selection == "Funnel Analysis":
    render_funnel_analysis(reader, db_mtime, fetch_data)

elif selection == "High-Risk Customers":
    render_high_risk_customers(reader, db_mtime, fetch_data)

elif selection == "Recommendations":
    render_recommendations(reader, db_mtime, fetch_data)

elif selection == "Intervention Plan":
    render_intervention_plan(reader, db_mtime, fetch_data)

elif selection == "Decision Traces":
    render_decision_traces(reader, db_mtime, fetch_data)

elif selection == "Metric Lineage":
    render_metric_lineage(reader, db_mtime, fetch_data)

st.divider()
if st.button("Show demo reset command"):
    st.info("To rebuild from the configured seed, run `make reset-demo`, then reload this page.")
    st.code(
        """
make reset-demo
make dashboard
""",
        language="bash",
    )
