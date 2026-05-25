import streamlit as st
import pandas as pd
from typing import Callable

from adapters.sqlite_reader import SQLiteReader
from app.ui_helpers import (
    get_filter_options,
    filter_dataframe_by_values,
    prepare_metric_chart_data,
    prepare_display_dataframe,
    format_currency,
    format_percentage,
    safe_dataframe_empty_message,
    build_custom_scenario_analysis,
)
from app.ui_renderers import (
    render_csv_download,
)


def render_kpi_summary(
    reader: SQLiteReader,
    db_mtime: float | None,
    fetch_data: Callable[..., pd.DataFrame],
) -> None:
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
        render_csv_download(
            "Download KPI summary CSV",
            kpis,
            "kpi-summary",
            "download_kpis",
            db_mtime=db_mtime,
        )
    else:
        st.info(safe_dataframe_empty_message(kpis, "KPI summary"))


def render_scenario_simulator(
    reader: SQLiteReader,
    db_mtime: float | None,
    fetch_data: Callable[..., pd.DataFrame],
) -> None:
    st.write("Modeled business impact from standard improvement scenarios.")
    scenarios = fetch_data(reader, "get_scenario_analysis", db_mtime)
    kpis = fetch_data(reader, "get_kpi_summary", db_mtime)
    customers = fetch_data(reader, "get_customer_360", db_mtime)
    leakages = fetch_data(reader, "read_table", db_mtime, table_name="revenue_leakage")
    if not scenarios.empty:
        monthly_total = (
            pd.to_numeric(scenarios["monthly_impact"], errors="coerce").sum()
            if "monthly_impact" in scenarios.columns
            else 0.0
        )
        annual_total = (
            pd.to_numeric(scenarios["annualized_impact"], errors="coerce").sum()
            if "annualized_impact" in scenarios.columns
            else 0.0
        )
        best_row = (
            scenarios.sort_values("annualized_impact", ascending=False).iloc[0]
            if "annualized_impact" in scenarios.columns
            else None
        )

        metric_cols = st.columns(3)
        with metric_cols[0]:
            st.metric("Scenarios", len(scenarios))
        with metric_cols[1]:
            st.metric("Monthly Upside", format_currency(monthly_total))
        with metric_cols[2]:
            st.metric("Annualized Upside", format_currency(annual_total))

        if best_row is not None:
            st.info(
                f"Highest modeled upside: {best_row['scenario_name']} "
                f"({format_currency(best_row['annualized_impact'])} annualized)."
            )

        chart_data = scenarios.copy()
        if {"scenario_name", "annualized_impact"}.issubset(chart_data.columns):
            chart_data = chart_data.set_index("scenario_name")[["annualized_impact"]]
            st.bar_chart(chart_data)

        display_scenarios = prepare_display_dataframe(
            scenarios,
            currency_columns=["monthly_impact", "annualized_impact"],
            number_columns=["baseline_value", "simulated_value"],
        )
        st.dataframe(display_scenarios, width="stretch", hide_index=True)
        render_csv_download(
            "Download scenario analysis CSV",
            scenarios,
            "scenario-analysis",
            "download_scenario_analysis",
            db_mtime=db_mtime,
        )
    else:
        st.info(safe_dataframe_empty_message(scenarios, "scenario analysis"))

    st.divider()
    st.subheader("Custom Assumptions")
    assumption_cols = st.columns(4)
    with assumption_cols[0]:
        churn_improvement_rate = (
            st.slider("Churn reduction", min_value=0, max_value=50, value=10, step=1) / 100
        )
    with assumption_cols[1]:
        activation_improvement_rate = (
            st.slider("Activation lift", min_value=0, max_value=100, value=10, step=1) / 100
        )
    with assumption_cols[2]:
        arpu_increase_rate = (
            st.slider("ARPU increase", min_value=0, max_value=50, value=5, step=1) / 100
        )
    with assumption_cols[3]:
        failed_payment_recovery_rate = (
            st.slider("Failed-payment recovery", min_value=0, max_value=100, value=30, step=1)
            / 100
        )

    custom_scenarios = build_custom_scenario_analysis(
        kpis,
        customers,
        leakages,
        churn_improvement_rate,
        activation_improvement_rate,
        arpu_increase_rate,
        failed_payment_recovery_rate,
    )
    if not custom_scenarios.empty:
        custom_monthly_total = pd.to_numeric(
            custom_scenarios["monthly_impact"], errors="coerce"
        ).sum()
        custom_annual_total = pd.to_numeric(
            custom_scenarios["annualized_impact"], errors="coerce"
        ).sum()
        custom_metric_cols = st.columns(2)
        with custom_metric_cols[0]:
            st.metric("Custom Monthly Upside", format_currency(custom_monthly_total))
        with custom_metric_cols[1]:
            st.metric("Custom Annualized Upside", format_currency(custom_annual_total))

        custom_chart = custom_scenarios.set_index("scenario_name")[["annualized_impact"]]
        st.bar_chart(custom_chart)
        display_custom_scenarios = prepare_display_dataframe(
            custom_scenarios,
            currency_columns=["monthly_impact", "annualized_impact"],
            number_columns=["baseline_value", "simulated_value"],
        )
        st.dataframe(display_custom_scenarios, width="stretch", hide_index=True)
        render_csv_download(
            "Download custom scenario CSV",
            custom_scenarios,
            "custom-scenario-analysis",
            "download_custom_scenario_analysis",
            db_mtime=db_mtime,
        )
    else:
        st.info("Custom scenarios need KPI, customer, or revenue leakage inputs.")


def render_cohort_retention(
    reader: SQLiteReader,
    db_mtime: float | None,
    fetch_data: Callable[..., pd.DataFrame],
) -> None:
    st.write("Signup cohort retention and revenue by period.")
    cohorts = fetch_data(reader, "get_cohort_summary", db_mtime)
    if not cohorts.empty:
        selected_cohorts = st.multiselect(
            "Cohort Month",
            get_filter_options(cohorts, "cohort_month"),
        )
        cohorts = filter_dataframe_by_values(cohorts, "cohort_month", selected_cohorts)

        metric_cols = st.columns(3)
        with metric_cols[0]:
            st.metric("Cohorts", cohorts["cohort_month"].nunique())
        with metric_cols[1]:
            retention_avg = (
                pd.to_numeric(cohorts["retention_rate"], errors="coerce").mean()
                if "retention_rate" in cohorts.columns
                else 0.0
            )
            st.metric("Avg Retention", format_percentage(retention_avg))
        with metric_cols[2]:
            revenue_total = (
                pd.to_numeric(cohorts["revenue"], errors="coerce").sum()
                if "revenue" in cohorts.columns
                else 0.0
            )
            st.metric("Cohort Revenue", format_currency(revenue_total))

        if {"period_number", "retention_rate"}.issubset(cohorts.columns):
            retention_chart = (
                cohorts.groupby("period_number")["retention_rate"].mean().reset_index()
            )
            retention_chart = retention_chart.set_index("period_number")
            st.line_chart(retention_chart)

        display_cohorts = prepare_display_dataframe(
            cohorts,
            currency_columns=["revenue", "revenue_per_customer"],
            percentage_columns=["retention_rate"],
            number_columns=["period_number", "customers_in_cohort", "retained_customers"],
        )
        st.dataframe(display_cohorts, width="stretch", hide_index=True)
        render_csv_download(
            "Download cohort summary CSV",
            cohorts,
            "cohort-summary",
            "download_cohort_summary",
            db_mtime=db_mtime,
        )
    else:
        st.info(safe_dataframe_empty_message(cohorts, "cohort summary"))


def render_funnel_analysis(
    reader: SQLiteReader,
    db_mtime: float | None,
    fetch_data: Callable[..., pd.DataFrame],
) -> None:
    st.write("Activation funnel conversion and drop-off by step and segment.")
    funnel = fetch_data(reader, "get_funnel_summary", db_mtime)
    segment_funnel = fetch_data(reader, "get_segment_funnel", db_mtime)
    if not funnel.empty:
        bottleneck = (
            funnel[funnel["step"] != "Signup"].sort_values("dropoff_rate", ascending=False).head(1)
            if {"step", "dropoff_rate"}.issubset(funnel.columns)
            else pd.DataFrame()
        )

        metric_cols = st.columns(3)
        with metric_cols[0]:
            st.metric("Funnel Steps", len(funnel))
        with metric_cols[1]:
            final_users = int(funnel.iloc[-1]["users"]) if "users" in funnel.columns else 0
            st.metric("Final Step Users", final_users)
        with metric_cols[2]:
            if not bottleneck.empty:
                st.metric(
                    "Largest Drop-off",
                    format_percentage(float(bottleneck.iloc[0]["dropoff_rate"])),
                )
            else:
                st.metric("Largest Drop-off", "N/A")

        if not bottleneck.empty:
            st.warning(f"Bottleneck step: {bottleneck.iloc[0]['step']}")

        if {"step", "users"}.issubset(funnel.columns):
            st.bar_chart(funnel.set_index("step")[["users"]])

        display_funnel = prepare_display_dataframe(
            funnel,
            percentage_columns=["conversion_rate", "dropoff_rate"],
            number_columns=["users", "previous_step_users"],
        )
        st.dataframe(display_funnel, width="stretch", hide_index=True)
        render_csv_download(
            "Download funnel summary CSV",
            funnel,
            "funnel-summary",
            "download_funnel_summary",
            db_mtime=db_mtime,
        )

        if not segment_funnel.empty:
            st.subheader("Segment Funnel")
            selected_segments = st.multiselect(
                "Segment",
                get_filter_options(segment_funnel, "segment"),
            )
            segment_view = filter_dataframe_by_values(segment_funnel, "segment", selected_segments)
            display_segment_funnel = prepare_display_dataframe(
                segment_view,
                percentage_columns=["conversion_rate", "dropoff_rate"],
                number_columns=["users", "previous_step_users"],
            )
            st.dataframe(display_segment_funnel, width="stretch", hide_index=True)
            render_csv_download(
                "Download segment funnel CSV",
                segment_view,
                "segment-funnel",
                "download_segment_funnel",
                db_mtime=db_mtime,
            )
    else:
        st.info(safe_dataframe_empty_message(funnel, "funnel summary"))
