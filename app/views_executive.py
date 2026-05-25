import streamlit as st
import pandas as pd
from typing import Callable

from adapters.sqlite_reader import SQLiteReader
from app.ui_helpers import (
    get_executive_metric_values,
    build_data_freshness_summary,
    format_file_size,
    prepare_display_dataframe,
    format_currency,
    format_percentage,
    determine_business_status,
    prepare_top_actions,
    build_top_actions_overview,
    prepare_action_priority_queue,
    apply_quick_view,
    get_filter_options,
    filter_dataframe_by_values,
    filter_dataframe_by_search,
    prepare_metric_chart_data,
    prepare_category_counts,
    safe_dataframe_empty_message,
)
from app.ui_renderers import (
    render_csv_download,
    render_quick_view,
    render_decision_brief,
    render_owner_workload,
    render_freshness_action,
)


def render_executive_cockpit(
    reader: SQLiteReader,
    db_mtime: float | None,
    db_size: int | None,
    sidebar_inventory: pd.DataFrame,
    fetch_data: Callable[..., pd.DataFrame],
) -> None:
    kpis = fetch_data(reader, "get_kpi_summary", db_mtime)
    health = fetch_data(reader, "get_health_scores", db_mtime)
    high_risk = fetch_data(reader, "get_high_risk_customers", db_mtime)
    plan = fetch_data(reader, "get_intervention_plan", db_mtime)
    leakages = fetch_data(reader, "read_table", db_mtime, table_name="revenue_leakage")
    metric_values = get_executive_metric_values(kpis)
    table_inventory = sidebar_inventory
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
                db_mtime=db_mtime,
            )
    else:
        st.caption(freshness["caption"])
    render_freshness_action(freshness)

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
            db_mtime=db_mtime,
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
            db_mtime=db_mtime,
        )
    else:
        st.info(safe_dataframe_empty_message(top_actions, "top actions"))


def render_top_actions_page(
    reader: SQLiteReader,
    db_mtime: float | None,
    fetch_data: Callable[..., pd.DataFrame],
) -> None:
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
        from app.ui_helpers import summarize_filter_state
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

        overview = build_top_actions_overview(plan)
        summary_cols = st.columns(4)
        with summary_cols[0]:
            st.metric("Actions in View", overview["actions"])
        with summary_cols[1]:
            st.metric("Critical / High", overview["critical_high"])
        with summary_cols[2]:
            st.metric("Quick Wins", overview["quick_wins"])
        with summary_cols[3]:
            st.metric("Revenue Impact", format_currency(overview["impact_total"]))
        st.caption(f"Primary owner in current view: {overview['top_owner']}")

        render_decision_brief("Top Actions", plan, quick_view, "top_actions", db_mtime=db_mtime)

        action_queue = prepare_action_priority_queue(plan, limit=25)
        if not action_queue.empty:
            queue_tab, owner_tab, chart_tab = st.tabs(["Action Queue", "Owner Workload", "Chart"])

            with queue_tab:
                action_options = action_queue["intervention_id"].astype(str).tolist()
                action_labels = {
                    str(row["intervention_id"]): (
                        f"{row['intervention_id']} | {row.get('priority_band', 'Unscored')} | "
                        f"{format_currency(row.get('estimated_revenue_impact', 0.0))}"
                    )
                    for _, row in action_queue.iterrows()
                }
                selected_action = st.selectbox(
                    "Action",
                    action_options,
                    format_func=lambda action_id: action_labels.get(action_id, action_id),
                )
                selected_action_row = action_queue[
                    action_queue["intervention_id"].astype(str) == selected_action
                ].iloc[0]
                st.info(str(selected_action_row.get("expected_action", "Review action details.")))

                display_actions = prepare_display_dataframe(
                    action_queue,
                    currency_columns=["estimated_revenue_impact"],
                    status_columns=["priority_band"],
                    number_columns=["priority_score"],
                )
                st.dataframe(display_actions, width="stretch", hide_index=True)
                render_csv_download(
                    "Download current actions CSV",
                    plan,
                    "top-actions",
                    "download_top_actions",
                    db_mtime=db_mtime,
                )

            with owner_tab:
                render_owner_workload(plan, "top_actions", db_mtime=db_mtime)

            with chart_tab:
                chart_data = prepare_metric_chart_data(
                    plan,
                    metric_column="recommendation_title",
                    value_column="priority_score",
                )
                if not chart_data.empty:
                    st.bar_chart(chart_data.head(25))
                else:
                    st.info("No priority chart data in current view.")
        else:
            top_actions = prepare_top_actions(plan, limit=25)
            st.info(
                safe_dataframe_empty_message(
                    top_actions,
                    "top actions",
                    filtered=True,
                )
            )
    else:
        st.info(safe_dataframe_empty_message(plan, "intervention plan"))
