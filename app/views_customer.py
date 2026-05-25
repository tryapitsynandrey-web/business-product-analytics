import streamlit as st
import pandas as pd
from typing import Callable

from adapters.sqlite_reader import SQLiteReader
from app.ui_helpers import (
    apply_quick_view,
    get_filter_options,
    filter_dataframe_by_values,
    filter_dataframe_by_search,
    summarize_filter_state,
    build_customer_360_overview,
    prepare_customer_360_queue,
    build_customer_profile_summary,
    prepare_display_dataframe,
    format_currency,
    safe_dataframe_empty_message,
    prepare_metric_chart_data,
    prepare_category_counts,
)
from app.ui_renderers import (
    render_csv_download,
    render_quick_view,
    render_decision_brief,
    render_owner_workload,
)


def render_customer_360(
    reader: SQLiteReader,
    db_mtime: float | None,
    fetch_data: Callable[..., pd.DataFrame],
) -> None:
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

        from app.ui_helpers import filter_customer_360
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

        overview = build_customer_360_overview(filtered_customers)
        overview_cols = st.columns(4)
        with overview_cols[0]:
            st.metric("Customers", overview["customers"])
        with overview_cols[1]:
            st.metric("Active Customers", overview["active_customers"])
        with overview_cols[2]:
            st.metric("High / Critical", overview["high_risk_customers"])
        with overview_cols[3]:
            st.metric("Revenue at Risk", format_currency(overview["revenue_at_risk"]))
        st.caption(f"Most common risk driver: {overview['top_driver']}")

        render_decision_brief(
            "Customer 360",
            filtered_customers,
            quick_view,
            "customer_360",
            db_mtime=db_mtime,
        )

        if not filtered_customers.empty:
            customer_queue = prepare_customer_360_queue(filtered_customers)
            options = filtered_customers["customer_id"].astype(str).tolist()
            customer_labels = {
                str(row["customer_id"]): (
                    f"{row['customer_id']} | {row.get('churn_risk_band', 'Unknown')} | "
                    f"{format_currency(row.get('revenue_at_risk', 0.0))} at risk"
                )
                for _, row in filtered_customers.iterrows()
            }
            selected_customer = st.selectbox(
                "Customer",
                options,
                format_func=lambda customer_id: customer_labels.get(customer_id, customer_id),
            )
            selected_row = filtered_customers[
                filtered_customers["customer_id"].astype(str) == selected_customer
            ].iloc[0]
            summary = build_customer_profile_summary(selected_row)

            profile_tab, recommendations_tab, trace_tab, queue_tab = st.tabs(
                ["Profile", "Recommendations", "Decision Trace", "Queue"]
            )

            with profile_tab:
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
                st.info(str(summary["Recommended Action"]))

            with recommendations_tab:
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
                        db_mtime=db_mtime,
                    )
                else:
                    st.info(
                        safe_dataframe_empty_message(
                            customer_recs, "customer recommendations", filtered=True
                        )
                    )

            with trace_tab:
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
                        db_mtime=db_mtime,
                    )
                else:
                    st.info(
                        safe_dataframe_empty_message(
                            customer_traces, "customer decision traces", filtered=True
                        )
                    )

            with queue_tab:
                display_queue = prepare_display_dataframe(
                    customer_queue,
                    currency_columns=["current_mrr", "revenue_at_risk"],
                    status_columns=["churn_risk_band", "health_status"],
                    number_columns=["churn_risk_score"],
                )
                st.dataframe(display_queue, width="stretch", hide_index=True)
                render_csv_download(
                    "Download filtered customers CSV",
                    filtered_customers,
                    "filtered-customers",
                    "download_filtered_customers",
                    db_mtime=db_mtime,
                )
        else:
            st.info(safe_dataframe_empty_message(filtered_customers, "customers", filtered=True))
    else:
        st.info(safe_dataframe_empty_message(customers, "Customer 360"))


def render_high_risk_customers(
    reader: SQLiteReader,
    db_mtime: float | None,
    fetch_data: Callable[..., pd.DataFrame],
) -> None:
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
            db_mtime=db_mtime,
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
            db_mtime=db_mtime,
        )
    else:
        st.success("No high-risk customers identified.")


def render_recommendations(
    reader: SQLiteReader,
    db_mtime: float | None,
    fetch_data: Callable[..., pd.DataFrame],
) -> None:
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

        render_decision_brief(
            "Recommendations", recs, quick_view, "recommendations", db_mtime=db_mtime
        )
        render_owner_workload(recs, "recommendations", db_mtime=db_mtime)

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
            db_mtime=db_mtime,
        )
    else:
        st.info(safe_dataframe_empty_message(recs, "recommendations"))


def render_intervention_plan(
    reader: SQLiteReader,
    db_mtime: float | None,
    fetch_data: Callable[..., pd.DataFrame],
) -> None:
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

        render_decision_brief(
            "Intervention Plan", plan, quick_view, "intervention_plan", db_mtime=db_mtime
        )
        render_owner_workload(plan, "intervention_plan", db_mtime=db_mtime)

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
            db_mtime=db_mtime,
        )
    else:
        st.info(safe_dataframe_empty_message(plan, "intervention plan"))
