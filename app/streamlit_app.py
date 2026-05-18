import streamlit as st
import pandas as pd
from pathlib import Path

from adapters.sqlite_reader import SQLiteReader
from utils.paths import SQLITE_DB_PATH

try:
    from app.ui_helpers import (
        format_currency,
        format_percentage,
        format_file_size,
        format_timestamp,
        build_data_freshness_summary,
        db_status_label,
        safe_dataframe_empty_message,
        dataframe_to_csv_bytes,
        build_export_filename,
        get_filter_options,
        filter_dataframe_by_values,
        filter_dataframe_by_search,
        get_quick_view_options,
        describe_quick_view,
        apply_quick_view,
        prepare_metric_chart_data,
        prepare_status_counts,
        prepare_category_counts,
        prepare_display_dataframe,
        get_executive_metric_values,
        determine_business_status,
        prepare_top_actions,
        build_decision_brief,
        decision_brief_to_markdown,
        prepare_owner_workload_summary,
        filter_customer_360,
        build_customer_profile_summary,
        summarize_filter_state,
    )
except ModuleNotFoundError:
    from ui_helpers import (
        format_currency,
        format_percentage,
        format_file_size,
        format_timestamp,
        build_data_freshness_summary,
        db_status_label,
        safe_dataframe_empty_message,
        dataframe_to_csv_bytes,
        build_export_filename,
        get_filter_options,
        filter_dataframe_by_values,
        filter_dataframe_by_search,
        get_quick_view_options,
        describe_quick_view,
        apply_quick_view,
        prepare_metric_chart_data,
        prepare_status_counts,
        prepare_category_counts,
        prepare_display_dataframe,
        get_executive_metric_values,
        determine_business_status,
        prepare_top_actions,
        build_decision_brief,
        decision_brief_to_markdown,
        prepare_owner_workload_summary,
        filter_customer_360,
        build_customer_profile_summary,
        summarize_filter_state,
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
        st.error(f"Failed to load data ({method_name}): {str(e)}")
        return pd.DataFrame()


@st.cache_data(show_spinner=False)
def fetch_table_inventory(_reader: SQLiteReader | None, _mtime: float | None) -> pd.DataFrame:
    if not _reader:
        return pd.DataFrame(columns=["table", "rows"])

    rows = []
    try:
        table_names = sorted(_reader.list_tables())
    except Exception as e:
        st.error(f"Failed to load table inventory: {str(e)}")
        return pd.DataFrame(columns=["table", "rows"])

    for table_name in table_names:
        try:
            rows.append({"table": table_name, "rows": _reader.get_table_row_count(table_name)})
        except ValueError:
            continue
    return pd.DataFrame(rows)


def render_csv_download(label: str, df: pd.DataFrame, filename_label: str, key: str) -> None:
    if df.empty:
        return

    st.download_button(
        label,
        data=dataframe_to_csv_bytes(df),
        file_name=build_export_filename(filename_label, db_mtime),
        mime="text/csv",
        key=key,
    )


def render_quick_view(view_name: str, key: str) -> str:
    options = get_quick_view_options(view_name)
    selected = st.radio("Quick View", options, horizontal=True, key=key)
    st.caption(describe_quick_view(selected))
    return selected


def render_decision_brief(
    title: str,
    df: pd.DataFrame,
    quick_view: str,
    key: str,
) -> None:
    brief = build_decision_brief(df, title, quick_view)

    with st.expander("Decision Brief", expanded=True):
        metric_cols = st.columns(3)
        with metric_cols[0]:
            st.metric("Records", int(brief["records"]))
        with metric_cols[1]:
            st.metric(str(brief["impact_label"]), str(brief["formatted_impact"]))
        with metric_cols[2]:
            st.metric("Critical / High", int(brief["urgent_count"]))

        st.write(str(brief["summary"]))
        st.caption(str(brief["why_it_matters"]))

        top_actions = brief.get("top_actions", [])
        if isinstance(top_actions, list) and top_actions:
            actions_df = pd.DataFrame(top_actions)
            actions_df = actions_df.rename(
                columns={
                    "title": "Record",
                    "action": "Next Action",
                    "owner": "Owner",
                    "status": "Status",
                    "impact": "Impact",
                }
            )
            display_cols = ["Record", "Next Action", "Owner", "Status", "Impact"]
            st.dataframe(actions_df[display_cols], width="stretch", hide_index=True)

        st.download_button(
            "Download decision brief MD",
            data=decision_brief_to_markdown(brief).encode("utf-8"),
            file_name=build_export_filename(f"{key}-decision-brief", db_mtime).replace(
                ".csv", ".md"
            ),
            mime="text/markdown",
            key=f"download_{key}_decision_brief",
        )


def render_owner_workload(df: pd.DataFrame, key: str) -> None:
    summary = prepare_owner_workload_summary(df)
    if summary.empty:
        return

    with st.expander("Owner Workload", expanded=False):
        display = summary.rename(
            columns={
                "owner": "Owner",
                "records": "Records",
                "critical_high": "Critical / High",
                "impact_total": "Impact Total",
            }
        )
        display["Impact Total"] = display["Impact Total"].apply(format_currency)
        st.dataframe(display, width="stretch", hide_index=True)
        render_csv_download(
            "Download owner workload CSV",
            summary,
            f"{key}-owner-workload",
            f"download_{key}_owner_workload",
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

st.sidebar.divider()

pages = [
    "Executive Cockpit",
    "Top Actions",
    "Customer 360",
    "KPI Summary",
    "Product / Business Health",
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
    st.info("Run the local pipeline, then reload this page.")
    st.code(
        """
make run
""",
        language="bash",
    )
    st.stop()

# ── Main Content ────────────────────────────────────────────────────────
st.title(selection)

if selection == "Executive Cockpit":
    kpis = fetch_data(reader, "get_kpi_summary", db_mtime)
    health = fetch_data(reader, "get_health_scores", db_mtime)
    high_risk = fetch_data(reader, "get_high_risk_customers", db_mtime)
    plan = fetch_data(reader, "get_intervention_plan", db_mtime)
    leakages = fetch_data(reader, "read_table", db_mtime, table_name="revenue_leakage")
    metric_values = get_executive_metric_values(kpis)
    table_inventory = fetch_table_inventory(reader, db_mtime)
    freshness = build_data_freshness_summary(db_mtime)

    st.subheader("Data Freshness")
    freshness_row_1 = st.columns(2)
    with freshness_row_1[0]:
        st.metric("Database Freshness", freshness["status"])
    with freshness_row_1[1]:
        st.metric("Data Age", freshness["age"])

    freshness_row_2 = st.columns(2)
    with freshness_row_2[0]:
        st.metric("Last Updated", freshness["updated_at"])
    with freshness_row_2[1]:
        st.metric("Local DB Size", format_file_size(db_size))

    if not table_inventory.empty:
        total_rows = pd.to_numeric(table_inventory["rows"], errors="coerce").sum()
        inv_col1, inv_col2 = st.columns(2)
        with inv_col1:
            st.metric("Tables Loaded", len(table_inventory))
        with inv_col2:
            st.metric("Rows Available", f"{int(total_rows):,}")
        st.caption(freshness["caption"])
        with st.expander("Data Inventory", expanded=False):
            display_inventory = prepare_display_dataframe(table_inventory, number_columns=["rows"])
            st.dataframe(display_inventory, width="stretch", hide_index=True)
            render_csv_download(
                "Download data inventory CSV",
                table_inventory,
                "data-inventory",
                "download_data_inventory",
            )
    else:
        st.caption(freshness["caption"])

    st.divider()

    st.subheader("Business Snapshot")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        mrr = metric_values["monthly_recurring_revenue"]
        st.metric("Total MRR", format_currency(mrr) if mrr is not None else "N/A")

    with col2:
        churn = metric_values["customer_churn_rate"]
        st.metric("Churn Rate", format_percentage(churn) if churn is not None else "N/A")

    with col3:
        arpu = metric_values["average_revenue_per_user"]
        st.metric("ARPU", format_currency(arpu) if arpu is not None else "N/A")

    with col4:
        risk = metric_values["revenue_at_risk"]
        st.metric("Revenue at Risk", format_currency(risk) if risk is not None else "N/A")

    with col5:
        st.metric("Business Status", determine_business_status(health))

    st.divider()

    col_h1, col_h2, col_h3 = st.columns([1, 1, 1])

    with col_h1:
        st.subheader("Health Areas")
        critical_health = fetch_data(reader, "get_critical_health_scores", db_mtime)
        if not critical_health.empty:
            for _, row in critical_health.iterrows():
                st.error(f"**{row['area']}** (Score: {row['score']}) - {row['explanation']}")
        else:
            st.success("No critical health areas detected.")

    with col_h2:
        st.subheader("Risk Queue")
        st.metric("High / Critical Customers", len(high_risk))
        if not high_risk.empty and "risk_band" in high_risk.columns:
            risk_counts = prepare_category_counts(high_risk, "risk_band")
            if not risk_counts.empty:
                st.bar_chart(risk_counts)
        else:
            st.success("No high-risk customers identified.")

    with col_h3:
        st.subheader("Revenue Leakage")
        leakage_total = (
            pd.to_numeric(leakages["estimated_revenue_loss"], errors="coerce").sum()
            if not leakages.empty and "estimated_revenue_loss" in leakages.columns
            else 0.0
        )
        st.metric("Identified Leakage", format_currency(leakage_total))
        if not leakages.empty and "leakage_type" in leakages.columns:
            leakage_counts = prepare_category_counts(leakages, "leakage_type")
            if not leakage_counts.empty:
                st.bar_chart(leakage_counts)

    st.divider()
    st.subheader("Top Actions")
    top_actions = prepare_top_actions(plan, limit=5)
    if not top_actions.empty:
        render_decision_brief(
            "Executive Top Actions",
            top_actions,
            "Executive Cockpit",
            "executive_top_actions",
        )
        display_actions = prepare_display_dataframe(
            top_actions,
            currency_columns=["estimated_revenue_impact"],
            status_columns=["priority_band"],
            number_columns=["priority_score"],
        )
        st.dataframe(display_actions, width="stretch", hide_index=True)
        render_csv_download(
            "Download top actions CSV",
            top_actions,
            "executive-top-actions",
            "download_executive_top_actions",
        )
    else:
        st.info(safe_dataframe_empty_message(top_actions, "top actions"))

elif selection == "Top Actions":
    st.write("Prioritized business actions sorted by expected impact and urgency.")
    plan = fetch_data(reader, "get_intervention_plan", db_mtime)
    if not plan.empty:
        quick_view = render_quick_view("top_actions", "quick_view_top_actions")
        plan = apply_quick_view(plan, quick_view)

        col1, col2, col3 = st.columns(3)
        with col1:
            priority = st.multiselect("Priority", get_filter_options(plan, "priority_band"))
            plan = filter_dataframe_by_values(plan, "priority_band", priority)
        with col2:
            owner = st.multiselect("Owner", get_filter_options(plan, "suggested_owner"))
            plan = filter_dataframe_by_values(plan, "suggested_owner", owner)
        with col3:
            effort = st.multiselect("Effort", get_filter_options(plan, "effort_level"))
            plan = filter_dataframe_by_values(plan, "effort_level", effort)

        search_term = st.text_input("Search Actions", "")
        plan = filter_dataframe_by_search(
            plan,
            search_term,
            ["recommendation_title", "suggested_owner", "target_segment", "expected_action"],
        )
        st.caption(
            summarize_filter_state(
                {
                    "Quick View": [] if quick_view == "All Actions" else [quick_view],
                    "Priority": priority,
                    "Owner": owner,
                    "Effort": effort,
                    "Search": [search_term] if search_term else [],
                },
                empty_label="Showing all actions",
            )
        )

        summary_cols = st.columns(3)
        with summary_cols[0]:
            st.metric("Actions in View", len(plan))
        with summary_cols[1]:
            high_count = (
                plan["priority_band"].astype(str).isin(["Critical", "High"]).sum()
                if "priority_band" in plan.columns
                else 0
            )
            st.metric("Critical / High", int(high_count))
        with summary_cols[2]:
            impact_total = (
                pd.to_numeric(plan["estimated_revenue_impact"], errors="coerce").sum()
                if "estimated_revenue_impact" in plan.columns
                else 0.0
            )
            st.metric("Revenue Impact", format_currency(impact_total))

        render_decision_brief("Top Actions", plan, quick_view, "top_actions")
        render_owner_workload(plan, "top_actions")

        top_actions = prepare_top_actions(plan, limit=25)
        if not top_actions.empty:
            chart_data = prepare_metric_chart_data(
                plan,
                metric_column="recommendation_title",
                value_column="priority_score",
            )
            if not chart_data.empty:
                st.bar_chart(chart_data.head(25))
            display_actions = prepare_display_dataframe(
                top_actions,
                currency_columns=["estimated_revenue_impact"],
                status_columns=["priority_band"],
                number_columns=["priority_score"],
            )
            st.dataframe(display_actions, width="stretch", hide_index=True)
            render_csv_download(
                "Download current actions CSV",
                top_actions,
                "top-actions",
                "download_top_actions",
            )
        else:
            st.info(safe_dataframe_empty_message(top_actions, "top actions"))
    else:
        st.info(safe_dataframe_empty_message(plan, "intervention plan"))

elif selection == "Customer 360":
    st.write("Customer-level operational, revenue, risk, and recommendation view.")
    customers = fetch_data(reader, "get_customer_360", db_mtime)
    recs = fetch_data(reader, "get_recommendations", db_mtime)
    traces = fetch_data(reader, "get_decision_traces", db_mtime)

    if not customers.empty:
        quick_view = render_quick_view("customer_360", "quick_view_customer_360")
        customers = apply_quick_view(customers, quick_view)

        col1, col2, col3 = st.columns(3)
        with col1:
            risk_options = get_filter_options(customers, "churn_risk_band")
            risk_bands = st.multiselect(
                "Risk Band",
                risk_options,
            )
        with col2:
            segments = st.multiselect("Segment", get_filter_options(customers, "segment"))
        with col3:
            plans = st.multiselect("Plan", get_filter_options(customers, "plan"))

        filtered_customers = filter_customer_360(customers, risk_bands, segments, plans)
        search_term = st.text_input("Search Customers", "")
        filtered_customers = filter_dataframe_by_search(
            filtered_customers,
            search_term,
            ["customer_id", "segment", "plan", "recommended_action", "main_driver"],
        )
        st.caption(
            summarize_filter_state(
                {
                    "Quick View": [] if quick_view == "All Customers" else [quick_view],
                    "Risk Band": risk_bands,
                    "Segment": segments,
                    "Plan": plans,
                    "Search": [search_term] if search_term else [],
                },
                empty_label="Showing default customer queue",
            )
        )
        st.caption(f"{len(filtered_customers)} customer(s) in current view")

        render_decision_brief(
            "Customer 360",
            filtered_customers,
            quick_view,
            "customer_360",
        )

        if not filtered_customers.empty:
            options = filtered_customers["customer_id"].astype(str).tolist()
            selected_customer = st.selectbox("Customer", options)
            selected_row = filtered_customers[
                filtered_customers["customer_id"].astype(str) == selected_customer
            ].iloc[0]
            summary = build_customer_profile_summary(selected_row)

            metric_row_1 = st.columns(2)
            with metric_row_1[0]:
                st.metric("Current MRR", format_currency(summary["Current MRR"]))
            with metric_row_1[1]:
                st.metric("Revenue at Risk", format_currency(summary["Revenue at Risk"]))

            metric_row_2 = st.columns(2)
            with metric_row_2[0]:
                st.metric("Risk Band", summary["Risk Band"])
            with metric_row_2[1]:
                st.metric("Usage Trend", summary["Usage Trend"])

            detail_left, detail_right = st.columns([1, 1])
            with detail_left:
                st.subheader("Profile")
                profile_rows = pd.DataFrame(
                    [
                        {
                            "field": key,
                            "value": (
                                format_currency(value)
                                if key in {"Current MRR", "Revenue at Risk"}
                                else str(value)
                            ),
                        }
                        for key, value in summary.items()
                    ]
                )
                st.dataframe(profile_rows, width="stretch", hide_index=True)
            with detail_right:
                st.subheader("Recommended Action")
                st.info(str(summary["Recommended Action"]))

            st.subheader("Customer Recommendations")
            customer_recs = (
                recs[recs["customer_id"].astype(str) == selected_customer]
                if not recs.empty and "customer_id" in recs.columns
                else pd.DataFrame()
            )
            if not customer_recs.empty:
                display_recs = prepare_display_dataframe(
                    customer_recs,
                    currency_columns=["estimated_revenue_impact"],
                    status_columns=["priority_band", "confidence_level"],
                    number_columns=["priority_score", "impact_score"],
                )
                st.dataframe(display_recs, width="stretch", hide_index=True)
                render_csv_download(
                    "Download customer recommendations CSV",
                    customer_recs,
                    "customer-recommendations",
                    "download_customer_recommendations",
                )
            else:
                st.info("No recommendations for this customer.")

            st.subheader("Decision Trace")
            customer_traces = (
                traces[traces["entity_id"].astype(str) == selected_customer]
                if not traces.empty and "entity_id" in traces.columns
                else pd.DataFrame()
            )
            if not customer_traces.empty:
                st.dataframe(customer_traces, width="stretch", hide_index=True)
                render_csv_download(
                    "Download customer trace CSV",
                    customer_traces,
                    "customer-decision-trace",
                    "download_customer_trace",
                )
            else:
                st.info("No customer-specific trace records.")

            st.subheader("Filtered Customer List")
            display_customers = prepare_display_dataframe(
                filtered_customers,
                currency_columns=["current_mrr", "total_revenue", "revenue_at_risk"],
                status_columns=["churn_risk_band", "health_status"],
                number_columns=["churn_risk_score", "latest_usage_frequency"],
            )
            st.dataframe(display_customers, width="stretch", hide_index=True)
            render_csv_download(
                "Download filtered customers CSV",
                filtered_customers,
                "filtered-customers",
                "download_filtered_customers",
            )
        else:
            st.info("No customers match the selected filters.")
    else:
        st.info(safe_dataframe_empty_message(customers, "Customer 360"))

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

        display_kpis = prepare_display_dataframe(kpis, number_columns=["value"])
        st.dataframe(display_kpis, width="stretch", hide_index=True)
        render_csv_download("Download KPI summary CSV", kpis, "kpi-summary", "download_kpis")
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

        display_health = prepare_display_dataframe(
            health,
            status_columns=["status"],
            number_columns=["score"],
        )
        st.dataframe(display_health, width="stretch", hide_index=True)
        render_csv_download(
            "Download health scores CSV",
            health,
            "health-scores",
            "download_health_scores",
        )
    else:
        st.info(safe_dataframe_empty_message(health, "health score"))

elif selection == "High-Risk Customers":
    st.write("Customers prioritized by churn risk algorithms.")
    high_risk = fetch_data(reader, "get_high_risk_customers", db_mtime)
    if not high_risk.empty:
        quick_view = render_quick_view("high_risk_customers", "quick_view_high_risk")
        high_risk = apply_quick_view(high_risk, quick_view)

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

        render_decision_brief(
            "High-Risk Customers",
            high_risk,
            quick_view,
            "high_risk_customers",
        )

        display_high_risk = prepare_display_dataframe(
            high_risk,
            currency_columns=["revenue_at_risk"],
            status_columns=["risk_band", "health_status"],
            number_columns=["risk_score", "churn_risk_score"],
        )
        st.dataframe(display_high_risk, width="stretch", hide_index=True)
        render_csv_download(
            "Download high-risk customers CSV",
            high_risk,
            "high-risk-customers",
            "download_high_risk_customers",
        )
    else:
        st.success("No high-risk customers identified.")

elif selection == "Recommendations":
    st.write("Rule-based business interventions targeted at high-value or at-risk segments.")
    recs = fetch_data(reader, "get_recommendations", db_mtime)
    if not recs.empty:
        quick_view = render_quick_view("recommendations", "quick_view_recommendations")
        recs = apply_quick_view(recs, quick_view)

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
        search_term = st.text_input("Search Recommendations", "")
        recs = filter_dataframe_by_search(
            recs,
            search_term,
            ["recommendation_title", "reason", "customer_id", "segment", "suggested_owner"],
        )

        render_decision_brief("Recommendations", recs, quick_view, "recommendations")
        render_owner_workload(recs, "recommendations")

        if "impact_score" in recs.columns and "recommendation_title" in recs.columns:
            chart_data = prepare_metric_chart_data(
                recs, metric_column="recommendation_title", value_column="impact_score"
            )
            if not chart_data.empty:
                st.bar_chart(chart_data)
        elif "priority_score" in recs.columns and "recommendation_title" in recs.columns:
            chart_data = prepare_metric_chart_data(
                recs, metric_column="recommendation_title", value_column="priority_score"
            )
            if not chart_data.empty:
                st.bar_chart(chart_data)

        display_recs = prepare_display_dataframe(
            recs,
            currency_columns=["estimated_revenue_impact"],
            status_columns=["confidence_level", "priority_band"],
            number_columns=["impact_score", "priority_score", "confidence_weight"],
        )
        st.dataframe(display_recs, width="stretch", hide_index=True)
        render_csv_download(
            "Download recommendations CSV",
            recs,
            "recommendations",
            "download_recommendations",
        )
    else:
        st.info(safe_dataframe_empty_message(recs, "recommendations"))

elif selection == "Intervention Plan":
    st.write("Strategic plan grouped by impact and effort.")
    plan = fetch_data(reader, "get_intervention_plan", db_mtime)
    if not plan.empty:
        quick_view = render_quick_view("intervention_plan", "quick_view_intervention_plan")
        plan = apply_quick_view(plan, quick_view)

        cols = st.columns(3)
        col_idx = 0
        for col_name in ["priority_band", "effort_level", "suggested_owner", "status"]:
            if col_name in plan.columns:
                with cols[col_idx % 3]:
                    options = get_filter_options(plan, col_name)
                    selected = st.multiselect(col_name.replace("_", " ").title(), options)
                    plan = filter_dataframe_by_values(plan, col_name, selected)
                col_idx += 1
        search_term = st.text_input("Search Plan", "")
        plan = filter_dataframe_by_search(
            plan,
            search_term,
            ["recommendation_title", "expected_action", "suggested_owner", "target_segment"],
        )

        render_decision_brief("Intervention Plan", plan, quick_view, "intervention_plan")
        render_owner_workload(plan, "intervention_plan")

        if "priority_band" in plan.columns:
            counts = prepare_category_counts(plan, "priority_band")
            if not counts.empty:
                st.bar_chart(counts)
        elif "effort_level" in plan.columns:
            counts = prepare_category_counts(plan, "effort_level")
            if not counts.empty:
                st.bar_chart(counts)

        display_plan = prepare_display_dataframe(
            plan,
            currency_columns=["estimated_revenue_impact"],
            status_columns=["priority_band", "confidence_level"],
            number_columns=["priority_score"],
        )
        st.dataframe(display_plan, width="stretch", hide_index=True)
        render_csv_download(
            "Download intervention plan CSV",
            plan,
            "intervention-plan",
            "download_intervention_plan",
        )
    else:
        st.info(safe_dataframe_empty_message(plan, "intervention plan"))

elif selection == "Decision Traces":
    st.write("Audit log of all decisions, triggers, and the explicit signals that caused them.")
    traces = fetch_data(reader, "get_decision_traces", db_mtime)
    if not traces.empty:
        trace_search = st.text_input("Search Traces", "")
        traces = filter_dataframe_by_search(
            traces,
            trace_search,
            ["entity_type", "entity_id", "signal", "triggered_rule", "generated_action"],
        )
        st.dataframe(traces, width="stretch", hide_index=True)
        render_csv_download(
            "Download decision traces CSV",
            traces,
            "decision-traces",
            "download_decision_traces",
        )
    else:
        st.info(safe_dataframe_empty_message(traces, "decision traces"))

elif selection == "Metric Lineage":
    st.write("Governance view of all tracked metrics, their formula descriptions, and ownership.")
    lineage = fetch_data(reader, "get_metric_lineage", db_mtime)
    if not lineage.empty:
        quick_view = render_quick_view("metric_lineage", "quick_view_metric_lineage")
        lineage = apply_quick_view(lineage, quick_view)

        cols = st.columns(3)
        col_idx = 0
        for col_name in ["lineage_status", "category", "source_datasets"]:
            if col_name in lineage.columns:
                with cols[col_idx % 3]:
                    options = get_filter_options(lineage, col_name)
                    selected = st.multiselect(col_name.replace("_", " ").title(), options)
                    lineage = filter_dataframe_by_values(lineage, col_name, selected)
                col_idx += 1

        display_lineage = prepare_display_dataframe(lineage, status_columns=["lineage_status"])
        st.dataframe(display_lineage, width="stretch", hide_index=True)
        render_csv_download(
            "Download metric lineage CSV",
            lineage,
            "metric-lineage",
            "download_metric_lineage",
        )
    else:
        st.info(safe_dataframe_empty_message(lineage, "metric lineage"))

st.divider()
if st.button("Show refresh instructions"):
    st.info("To refresh data, run `make run` in your terminal, then reload this page.")
