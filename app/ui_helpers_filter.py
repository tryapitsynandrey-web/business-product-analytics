import re
import pandas as pd
import streamlit as st
from typing import Any, Optional

from app.ui_helpers_format import (
    EXECUTIVE_METRICS,
    QUICK_VIEW_OPTIONS,
    QUICK_VIEW_DESCRIPTIONS,
    select_metric_value,
)


def get_filter_options(df: pd.DataFrame | None, column_name: str) -> list[str]:
    """Get sorted unique values for a column to use in a filter."""
    if df is None or df.empty or column_name not in df.columns:
        return []

    # Drop NAs and convert to strings, then sort
    unique_vals = df[column_name].dropna().unique()
    return sorted([str(x) for x in unique_vals])


@st.cache_data  # type: ignore
def filter_dataframe_by_values(
    df: pd.DataFrame | None, column_name: str, selected_values: list[str]
) -> pd.DataFrame:
    """Filter a dataframe by a list of selected values for a specific column."""
    if df is None or df.empty:
        return pd.DataFrame()

    df_copy = df.copy()
    if column_name not in df_copy.columns or not selected_values:
        return df_copy

    # We convert column values to string for safe comparison
    mask = df_copy[column_name].astype(str).isin(selected_values)
    return df_copy[mask]


@st.cache_data  # type: ignore
def filter_dataframe_by_search(
    df: pd.DataFrame | None,
    search_term: str,
    columns: list[str],
) -> pd.DataFrame:
    """Filter rows where any selected column contains the search term."""
    if df is None or df.empty:
        return pd.DataFrame()

    term = (search_term or "").strip()
    if not term:
        return df.copy()

    df_copy = df.copy()
    searchable_columns = [col for col in columns if col in df_copy.columns]
    if not searchable_columns:
        return df_copy

    mask = pd.Series(False, index=df_copy.index)
    for col in searchable_columns:
        mask = mask | df_copy[col].astype(str).str.contains(term, case=False, na=False)
    return df_copy[mask]


@st.cache_data  # type: ignore
def filter_dataframe_by_numeric_range(
    df: pd.DataFrame | None, column_name: str, min_value: float | None, max_value: float | None
) -> pd.DataFrame:
    """Filter a dataframe by a numeric range."""
    if df is None or df.empty:
        return pd.DataFrame()

    df_copy = df.copy()
    if column_name not in df_copy.columns:
        return df_copy

    mask = pd.Series(True, index=df_copy.index)

    if min_value is not None:
        mask = mask & (df_copy[column_name] >= min_value)
    if max_value is not None:
        mask = mask & (df_copy[column_name] <= max_value)

    return df_copy[mask]


def get_quick_view_options(view_name: str) -> list[str]:
    """Return quick-view preset labels for a dashboard view."""
    return QUICK_VIEW_OPTIONS.get(view_name, ["All"])


def describe_quick_view(quick_view: str) -> str:
    """Return a short user-facing description of a quick-view preset."""
    return QUICK_VIEW_DESCRIPTIONS.get(quick_view, "Custom quick view.")


def _filter_by_any_value(
    df: pd.DataFrame,
    columns: list[str],
    values: set[str],
) -> pd.DataFrame:
    available = [col for col in columns if col in df.columns]
    if not available:
        return df

    mask = pd.Series(False, index=df.index)
    for col in available:
        mask = mask | df[col].astype(str).str.lower().isin(values)
    return df[mask]


def _filter_by_keywords(
    df: pd.DataFrame,
    columns: list[str],
    keywords: tuple[str, ...],
) -> pd.DataFrame:
    available = [col for col in columns if col in df.columns]
    if not available:
        return df

    pattern = "|".join(re.escape(keyword) for keyword in keywords)
    mask = pd.Series(False, index=df.index)
    for col in available:
        mask = mask | df[col].astype(str).str.contains(pattern, case=False, na=False)
    return df[mask]


def _filter_top_numeric_quantile(
    df: pd.DataFrame,
    columns: list[str],
    quantile: float = 0.75,
) -> pd.DataFrame:
    available = [col for col in columns if col in df.columns]
    if not available:
        return df

    score = pd.Series(0.0, index=df.index)
    for col in available:
        values = pd.to_numeric(df[col], errors="coerce").fillna(0)
        score = score.where(score >= values, values)

    positive = score[score > 0]
    if positive.empty:
        return df

    threshold = positive.quantile(quantile)
    filtered = df[score >= threshold]
    return filtered if not filtered.empty else df


def _sort_by_existing_columns(
    df: pd.DataFrame,
    columns: list[str],
    ascending: list[bool],
) -> pd.DataFrame:
    available_columns = []
    available_ascending = []
    for col, asc in zip(columns, ascending):
        if col in df.columns:
            available_columns.append(col)
            available_ascending.append(asc)

    if not available_columns:
        return df

    sortable = df.copy()
    numeric_columns = {
        "estimated_revenue_impact",
        "revenue_at_risk",
        "current_mrr",
        "total_revenue",
    }
    for col in available_columns:
        if col.endswith("_score") or col in numeric_columns:
            sortable[col] = pd.to_numeric(sortable[col], errors="coerce").fillna(0)
    return sortable.sort_values(available_columns, ascending=available_ascending)


@st.cache_data  # type: ignore
def apply_quick_view(
    df: pd.DataFrame | None,
    quick_view: str,
) -> pd.DataFrame:
    """Apply a dashboard quick-view preset to a dataframe."""
    if df is None or df.empty:
        return pd.DataFrame()

    view = (quick_view or "").strip()
    data = df.copy()
    if view.startswith("All ") or view == "All":
        return data

    if view == "High Priority":
        priority_columns = ["priority_band", "risk_band", "churn_risk_band", "status"]
        filtered = _filter_by_any_value(
            data,
            priority_columns,
            {"critical", "high"},
        )
        if (filtered.empty or not any(col in data.columns for col in priority_columns)) and (
            "priority_score" in data.columns
        ):
            scores = pd.to_numeric(data["priority_score"], errors="coerce").fillna(0)
            filtered = data[scores >= scores.quantile(0.75)]
        return _sort_by_existing_columns(filtered, ["priority_score"], [False])

    if view == "Revenue Risk":
        filtered = _filter_top_numeric_quantile(
            data,
            [
                "estimated_revenue_impact",
                "revenue_at_risk",
                "current_mrr",
                "total_revenue",
            ],
        )
        return _sort_by_existing_columns(
            filtered,
            ["estimated_revenue_impact", "revenue_at_risk", "current_mrr", "total_revenue"],
            [False, False, False, False],
        )

    if view == "Quick Wins":
        filtered = _filter_by_any_value(data, ["effort_level"], {"low", "small"})
        return _sort_by_existing_columns(filtered, ["priority_score"], [False])

    if view == "Owner Queue":
        return _sort_by_existing_columns(
            data,
            ["suggested_owner", "owner", "priority_score", "estimated_revenue_impact"],
            [True, True, False, False],
        )

    if view == "Retention Focus":
        risk_columns = ["churn_risk_band", "risk_band", "priority_band"]
        filtered = _filter_by_any_value(
            data,
            risk_columns,
            {"critical", "high"},
        )
        if filtered.empty or not any(col in data.columns for col in risk_columns):
            keyword_filtered = _filter_by_keywords(
                data,
                [
                    "recommendation_title",
                    "reason",
                    "expected_action",
                    "recommended_action",
                    "main_driver",
                    "category",
                ],
                ("retention", "churn", "save", "renewal"),
            )
            filtered = keyword_filtered if not keyword_filtered.empty else filtered
        return _sort_by_existing_columns(
            filtered,
            ["churn_risk_score", "risk_score", "priority_score", "revenue_at_risk"],
            [False, False, False, False],
        )

    if view == "Expansion Watch":
        expansion_columns = ["usage_trend", "recommended_action", "main_driver", "segment", "plan"]
        filtered = _filter_by_keywords(
            data,
            expansion_columns,
            ("increasing", "expansion", "upsell", "growth", "enterprise"),
        )
        if filtered.empty or not any(col in data.columns for col in expansion_columns):
            filtered = _filter_top_numeric_quantile(data, ["current_mrr", "total_revenue"], 0.75)
        return _sort_by_existing_columns(filtered, ["current_mrr", "total_revenue"], [False, False])

    if view == "Critical Only":
        return _filter_by_any_value(
            data,
            ["risk_band", "churn_risk_band", "priority_band", "status"],
            {"critical"},
        )

    if view == "High Confidence":
        confidence_columns = ["confidence_level"]
        filtered = _filter_by_any_value(data, ["confidence_level"], {"high"})
        if (filtered.empty or not any(col in data.columns for col in confidence_columns)) and (
            "confidence_weight" in data.columns
        ):
            weights = pd.to_numeric(data["confidence_weight"], errors="coerce").fillna(0)
            filtered = data[weights >= weights.quantile(0.75)]
        return _sort_by_existing_columns(
            filtered,
            ["confidence_weight", "priority_score", "impact_score"],
            [False, False, False],
        )

    if view == "Governance Issues":
        healthy_values = {"healthy", "active", "ready", "good", "ok"}
        available = [col for col in ["lineage_status", "status"] if col in data.columns]
        if not available:
            return data
        mask = pd.Series(False, index=data.index)
        for col in available:
            values = data[col].astype(str).str.lower()
            mask = mask | (~values.isin(healthy_values))
        return data[mask]

    if view == "Owner Review":
        return _sort_by_existing_columns(
            data,
            ["owner", "metric_owner", "lineage_status"],
            [True, True, True],
        )

    return data


@st.cache_data  # type: ignore
def prepare_metric_chart_data(
    df: pd.DataFrame | None, metric_column: str = "metric_name", value_column: str = "value"
) -> pd.DataFrame:
    """Prepare data for a KPI metric bar chart, ensuring numeric values and setting index."""
    if df is None or df.empty or metric_column not in df.columns or value_column not in df.columns:
        return pd.DataFrame()

    chart_data = df.copy()

    # Convert values to numeric, dropping those that can't be converted
    chart_data[value_column] = pd.to_numeric(chart_data[value_column], errors="coerce")
    chart_data = chart_data.dropna(subset=[value_column])

    if chart_data.empty:
        return pd.DataFrame()

    chart_data = chart_data.set_index(metric_column)
    return chart_data[[value_column]]


@st.cache_data  # type: ignore
def prepare_status_counts(df: pd.DataFrame | None, status_column: str = "status") -> pd.DataFrame:
    """Prepare a count of statuses for a bar chart."""
    if df is None or df.empty or status_column not in df.columns:
        return pd.DataFrame()

    counts = df[status_column].value_counts().to_frame("count")
    return counts


@st.cache_data  # type: ignore
def prepare_category_counts(
    df: pd.DataFrame | None, category_column: str = "category"
) -> pd.DataFrame:
    """Prepare a count of categories for a bar chart."""
    if df is None or df.empty or category_column not in df.columns:
        return pd.DataFrame()

    counts = df[category_column].value_counts().to_frame("count")
    return counts


def get_executive_metric_values(kpis: pd.DataFrame | None) -> dict[str, Optional[Any]]:
    """Return the main executive KPI values keyed by canonical metric name."""
    source = kpis if kpis is not None else pd.DataFrame()
    return {
        metric_name: select_metric_value(source, metric_name) for metric_name in EXECUTIVE_METRICS
    }


def _metric_float(kpis: pd.DataFrame, metric_name: str) -> float | None:
    value = select_metric_value(kpis, metric_name)
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    return float(numeric)
