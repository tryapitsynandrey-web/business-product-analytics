import streamlit as st
import pandas as pd

from app.ui_helpers import (
    dataframe_to_csv_bytes,
    build_export_filename,
    get_quick_view_options,
    describe_quick_view,
    build_decision_brief,
    decision_brief_to_markdown,
    prepare_owner_workload_summary,
    format_currency,
)


def render_csv_download(
    label: str,
    df: pd.DataFrame,
    filename_label: str,
    key: str,
    db_mtime: float | None = None,
) -> None:
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
    db_mtime: float | None = None,
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


def render_owner_workload(df: pd.DataFrame, key: str, db_mtime: float | None = None) -> None:
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
            db_mtime=db_mtime,
        )


def render_freshness_action(freshness: dict[str, str]) -> None:
    render_status_action(freshness)


def render_status_action(status_info: dict[str, str]) -> None:
    action = status_info.get("action", "")
    if not action:
        return

    severity = status_info.get("severity")
    if severity == "success":
        st.success(action)
    elif severity == "warning":
        st.warning(action)
    elif severity == "error":
        st.error(action)
    else:
        st.info(action)
