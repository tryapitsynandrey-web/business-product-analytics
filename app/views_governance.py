import streamlit as st
import pandas as pd
from typing import Callable

from adapters.sqlite_reader import SQLiteReader
from app.ui_helpers import (
    apply_quick_view,
    get_filter_options,
    filter_dataframe_by_values,
    filter_dataframe_by_search,
    build_data_quality_overview,
    prepare_quality_dimension_summary,
    prepare_quality_issue_queue,
    prepare_display_dataframe,
    safe_dataframe_empty_message,
    prepare_status_counts,
)
from app.ui_renderers import (
    render_csv_download,
    render_quick_view,
)


def render_data_quality(
    reader: SQLiteReader,
    db_mtime: float | None,
    fetch_data: Callable[..., pd.DataFrame],
) -> None:
    quality = fetch_data(reader, "read_table", db_mtime, table_name="data_quality_scores")
    if not quality.empty:
        col1, col2 = st.columns(2)
        with col1:
            if "status" in quality.columns:
                selected_status = st.multiselect("Status", get_filter_options(quality, "status"))
                quality = filter_dataframe_by_values(quality, "status", selected_status)
        with col2:
            search_term = st.text_input("Search Dataset", "")
            quality = filter_dataframe_by_search(quality, search_term, ["dataset", "business_risk"])

        overview = build_data_quality_overview(quality)
        metric_cols = st.columns(4)
        with metric_cols[0]:
            st.metric("Datasets", str(overview["datasets"]))
        with metric_cols[1]:
            st.metric("Average Score", str(overview["average_score_display"]))
        with metric_cols[2]:
            st.metric("Needs Attention", str(overview["needs_attention"]))
        with metric_cols[3]:
            st.metric("Worst Status", str(overview["worst_status"]))

        st.caption(
            f"Lowest dimension: {overview['lowest_dimension']} "
            f"({overview['lowest_dimension_display']})."
        )

        dimension_summary = prepare_quality_dimension_summary(quality)
        if not dimension_summary.empty:
            chart_data = dimension_summary.set_index("dimension")[["average_score"]]
            st.bar_chart(chart_data)

        issue_queue = prepare_quality_issue_queue(quality)
        if not issue_queue.empty:
            st.subheader("Quality Queue")
            display_queue = prepare_display_dataframe(
                issue_queue,
                percentage_columns=["overall_score", "lowest_dimension_score"],
                status_columns=["status"],
            )
            st.dataframe(display_queue, width="stretch", hide_index=True)
            render_csv_download(
                "Download quality queue CSV",
                issue_queue,
                "data-quality-queue",
                "download_data_quality_queue",
                db_mtime=db_mtime,
            )

        display_quality = prepare_display_dataframe(
            quality,
            percentage_columns=[
                "completeness_score",
                "uniqueness_score",
                "validity_score",
                "referential_integrity_score",
                "overall_score",
            ],
            status_columns=["status"],
        )
        st.dataframe(display_quality, width="stretch", hide_index=True)
        render_csv_download(
            "Download data quality CSV",
            quality,
            "data-quality",
            "download_data_quality",
            db_mtime=db_mtime,
        )
    else:
        st.info(safe_dataframe_empty_message(quality, "data quality"))


def render_product_business_health(
    reader: SQLiteReader,
    db_mtime: float | None,
    fetch_data: Callable[..., pd.DataFrame],
) -> None:
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
            db_mtime=db_mtime,
        )
    else:
        st.info(safe_dataframe_empty_message(health, "health score"))


def render_decision_traces(
    reader: SQLiteReader,
    db_mtime: float | None,
    fetch_data: Callable[..., pd.DataFrame],
) -> None:
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
            db_mtime=db_mtime,
        )
    else:
        st.info(safe_dataframe_empty_message(traces, "decision traces"))


def render_metric_lineage(
    reader: SQLiteReader,
    db_mtime: float | None,
    fetch_data: Callable[..., pd.DataFrame],
) -> None:
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
            db_mtime=db_mtime,
        )
    else:
        st.info(safe_dataframe_empty_message(lineage, "metric lineage"))
