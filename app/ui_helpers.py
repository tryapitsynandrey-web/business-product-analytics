import re
import pandas as pd
from typing import Any, Optional

EXECUTIVE_METRICS = {
    "monthly_recurring_revenue": "Total MRR",
    "customer_churn_rate": "Churn Rate",
    "average_revenue_per_user": "ARPU",
    "revenue_at_risk": "Revenue at Risk",
}

QUICK_VIEW_OPTIONS = {
    "top_actions": ["All Actions", "High Priority", "Revenue Risk", "Quick Wins", "Owner Queue"],
    "customer_360": ["Retention Focus", "All Customers", "Revenue Risk", "Expansion Watch"],
    "high_risk_customers": ["All High-Risk", "Critical Only", "Revenue Risk"],
    "recommendations": [
        "All Recommendations",
        "High Confidence",
        "Revenue Risk",
        "Retention Focus",
        "Owner Queue",
    ],
    "intervention_plan": ["All Interventions", "High Priority", "Revenue Risk", "Quick Wins"],
    "metric_lineage": ["All Metrics", "Governance Issues", "Owner Review"],
}

QUICK_VIEW_DESCRIPTIONS = {
    "All Actions": "All actions are visible before manual filters.",
    "All Customers": "All customer records are visible before manual filters.",
    "All High-Risk": "All high-risk queue records are visible before manual filters.",
    "All Recommendations": "All recommendations are visible before manual filters.",
    "All Interventions": "All intervention records are visible before manual filters.",
    "All Metrics": "All metric lineage records are visible before manual filters.",
    "High Priority": "Critical and high-priority work, sorted by priority score.",
    "Revenue Risk": "Records with the largest revenue exposure or impact.",
    "Quick Wins": "Low-effort work, sorted by priority score.",
    "Owner Queue": "Records grouped by owner for handoff and review.",
    "Retention Focus": "Customers or actions tied to high churn and retention risk.",
    "Expansion Watch": "Customers with expansion-friendly usage and revenue signals.",
    "Critical Only": "Only records marked Critical.",
    "High Confidence": "Recommendations with stronger confidence signals.",
    "Governance Issues": "Metrics with lineage or ownership issues.",
    "Owner Review": "Metric records sorted by owner and status.",
}


def format_currency(value: object) -> str:
    """Format a float as currency (e.g., $1,234.56)."""
    try:
        val = float(value)  # type: ignore
        return f"${val:,.2f}"
    except (ValueError, TypeError):
        return "N/A"


def format_percentage(value: object) -> str:
    """Format a float as percentage (e.g., 15.5%)."""
    try:
        val = float(value)  # type: ignore
        return f"{val * 100:.1f}%"
    except (ValueError, TypeError):
        return "N/A"


def format_number(value: object, decimals: int = 0) -> str:
    """Format a numeric value with thousands separators."""
    if value is None:
        return "N/A"
    try:
        val = float(value)  # type: ignore
        if val != val:
            return "N/A"
        return f"{val:,.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A"


def safe_metric_value(value: Any, fallback: str = "N/A") -> str:
    """Safely return a metric value as string or fallback if missing."""
    if pd.isna(value) or value is None:
        return fallback
    return str(value)


def select_metric_value(
    df: pd.DataFrame, metric_name: str, value_column: str = "value"
) -> Optional[Any]:
    """Extract a specific metric value from a KPI summary dataframe."""
    if df.empty or "metric_name" not in df.columns or value_column not in df.columns:
        return None

    filtered = df[df["metric_name"] == metric_name]
    if filtered.empty:
        return None

    return filtered.iloc[0][value_column]


def status_badge_text(status: object) -> str:
    """Return a stylized or standard string based on status text."""
    if not isinstance(status, str):
        return "Unknown"

    status = status.title()
    if status in ["Healthy", "Good", "Active"]:
        return f"🟢 {status}"
    elif status in ["Warning", "At Risk", "Medium"]:
        return f"🟡 {status}"
    elif status in ["Critical", "High", "Failed", "Past Due", "Canceled", "Expired"]:
        return f"🔴 {status}"

    return status


def format_file_size(size_bytes: object) -> str:
    """Format bytes into readable string."""
    if size_bytes is None:
        return "Unknown"
    try:
        size = float(size_bytes)  # type: ignore
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    except (ValueError, TypeError):
        return "Unknown"


def format_timestamp(timestamp: object) -> str:
    """Format UNIX timestamp to human readable string."""
    if timestamp is None:
        return "Unknown"
    try:
        ts_float = float(timestamp)  # type: ignore
        dt = pd.to_datetime(ts_float, unit="s")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return "Unknown"


def format_duration(age_seconds: object) -> str:
    """Format a duration in seconds into a compact human-readable age."""
    try:
        seconds = max(0.0, float(age_seconds))  # type: ignore
    except (ValueError, TypeError):
        return "Unknown"

    if seconds < 60:
        return "<1 minute"
    if seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    if seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''}"

    days = int(seconds // 86400)
    return f"{days} day{'s' if days != 1 else ''}"


def build_data_freshness_summary(
    updated_timestamp: object,
    now_timestamp: object | None = None,
    warning_hours: float = 24.0,
    stale_hours: float = 72.0,
) -> dict[str, str]:
    """Return display-ready freshness fields for the local analytics database."""
    if updated_timestamp is None:
        return {
            "status": "🔴 Missing",
            "updated_at": "Unknown",
            "age": "Unknown",
            "caption": "No local database timestamp is available.",
        }

    try:
        updated = float(updated_timestamp)  # type: ignore
        now = (
            float(now_timestamp)  # type: ignore
            if now_timestamp is not None
            else pd.Timestamp.now().timestamp()
        )
        if updated != updated or now != now:
            raise ValueError("timestamp is NaN")
    except (ValueError, TypeError):
        return {
            "status": "🔴 Unknown",
            "updated_at": "Unknown",
            "age": "Unknown",
            "caption": "Database timestamp could not be parsed.",
        }

    age_seconds = max(0.0, now - updated)
    age_hours = age_seconds / 3600
    if age_hours <= warning_hours:
        status = "🟢 Fresh"
    elif age_hours <= stale_hours:
        status = "🟡 Aging"
    else:
        status = "🔴 Stale"

    age = format_duration(age_seconds)
    return {
        "status": status,
        "updated_at": format_timestamp(updated),
        "age": age,
        "caption": f"Local analytics database was updated {age} ago.",
    }


def db_status_label(exists: bool) -> str:
    """Return stylized DB status."""
    return "🟢 Online" if exists else "🔴 Missing"


def safe_dataframe_empty_message(df: pd.DataFrame | None, label: str) -> str:
    """Return a message indicating a dataframe is empty or missing."""
    if df is None or df.empty:
        return f"No {label} data available."
    return ""


def get_filter_options(df: pd.DataFrame | None, column_name: str) -> list[str]:
    """Get sorted unique values for a column to use in a filter."""
    if df is None or df.empty or column_name not in df.columns:
        return []

    # Drop NAs and convert to strings, then sort
    unique_vals = df[column_name].dropna().unique()
    return sorted([str(x) for x in unique_vals])


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


def filter_dataframe_by_search(
    df: pd.DataFrame | None,
    search_term: str,
    columns: list[str],
) -> pd.DataFrame:
    """Filter rows where any selected column contains the search term."""
    if df is None or df.empty:
        return pd.DataFrame()

    term = str(search_term or "").strip()
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


def apply_quick_view(
    df: pd.DataFrame | None,
    quick_view: str,
) -> pd.DataFrame:
    """Apply a dashboard quick-view preset to a dataframe."""
    if df is None or df.empty:
        return pd.DataFrame()

    view = str(quick_view or "").strip()
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


def prepare_status_counts(df: pd.DataFrame | None, status_column: str = "status") -> pd.DataFrame:
    """Prepare a count of statuses for a bar chart."""
    if df is None or df.empty or status_column not in df.columns:
        return pd.DataFrame()

    counts = df[status_column].value_counts().to_frame("count")
    return counts


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


def determine_business_status(health_scores: pd.DataFrame | None) -> str:
    """Summarize health score statuses into one executive status label."""
    if health_scores is None or health_scores.empty or "status" not in health_scores.columns:
        return "Unknown"

    statuses = set(health_scores["status"].dropna().astype(str))
    if "Critical" in statuses:
        return "Critical"
    if "Risk" in statuses or "At Risk" in statuses:
        return "Risk"
    if "Watch" in statuses or "Warning" in statuses:
        return "Watch"
    return "Healthy"


def prepare_top_actions(
    interventions: pd.DataFrame | None,
    limit: int = 10,
) -> pd.DataFrame:
    """Return top interventions ordered by priority score."""
    if interventions is None or interventions.empty:
        return pd.DataFrame()

    df = interventions.copy()
    if "priority_score" in df.columns:
        df["priority_score"] = pd.to_numeric(df["priority_score"], errors="coerce").fillna(0)
        df = df.sort_values("priority_score", ascending=False)

    display_cols = [
        "intervention_id",
        "recommendation_title",
        "priority_band",
        "estimated_revenue_impact",
        "priority_score",
        "effort_level",
        "suggested_owner",
        "target_segment",
    ]
    cols = [col for col in display_cols if col in df.columns]
    return df[cols].head(limit).reset_index(drop=True)


def filter_customer_360(
    customers: pd.DataFrame | None,
    risk_bands: list[str] | None = None,
    segments: list[str] | None = None,
    plans: list[str] | None = None,
) -> pd.DataFrame:
    """Apply common Customer 360 filters."""
    if customers is None or customers.empty:
        return pd.DataFrame()

    df = customers.copy()
    if risk_bands:
        df = filter_dataframe_by_values(df, "churn_risk_band", risk_bands)
    if segments:
        df = filter_dataframe_by_values(df, "segment", segments)
    if plans:
        df = filter_dataframe_by_values(df, "plan", plans)
    return df


def build_customer_profile_summary(customer_row: pd.Series | dict[str, Any]) -> dict[str, Any]:
    """Return a compact Customer 360 profile summary for display."""
    row = dict(customer_row)
    return {
        "Customer": row.get("customer_id", "Unknown"),
        "Segment": row.get("segment", "Unknown"),
        "Plan": row.get("plan", "Unknown"),
        "Risk Band": row.get("churn_risk_band", "Unknown"),
        "Current MRR": row.get("current_mrr", 0.0),
        "Revenue at Risk": row.get("revenue_at_risk", 0.0),
        "Usage Trend": row.get("usage_trend", "Unknown"),
        "Recommended Action": row.get("recommended_action", "No action required"),
    }


def summarize_filter_state(
    filters: dict[str, list[str] | None], empty_label: str = "No filters applied"
) -> str:
    """Return a compact summary of active filter selections."""
    active = []
    for label, values in filters.items():
        cleaned = [str(value) for value in (values or []) if str(value).strip()]
        if cleaned:
            active.append(f"{label}: {', '.join(cleaned)}")
    return "; ".join(active) if active else empty_label


def prepare_display_dataframe(
    df: pd.DataFrame | None,
    currency_columns: list[str] | None = None,
    percentage_columns: list[str] | None = None,
    status_columns: list[str] | None = None,
    number_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Return a copy formatted for Streamlit table display."""
    if df is None or df.empty:
        return pd.DataFrame()

    display = df.copy()
    for col in currency_columns or []:
        if col in display.columns:
            display[col] = display[col].apply(format_currency)

    for col in percentage_columns or []:
        if col in display.columns:
            display[col] = display[col].apply(format_percentage)

    for col in status_columns or []:
        if col in display.columns:
            display[col] = display[col].apply(status_badge_text)

    for col in number_columns or []:
        if col in display.columns:
            display[col] = display[col].apply(lambda value: format_number(value, decimals=2))

    return display


def dataframe_to_csv_bytes(df: pd.DataFrame | None) -> bytes:
    """Serialize a dataframe to UTF-8 CSV bytes for dashboard downloads."""
    if df is None:
        return b""
    return df.to_csv(index=False).encode("utf-8")


def build_export_filename(label: str, timestamp: object | None = None) -> str:
    """Build a stable, GitHub-safe CSV export filename."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(label).lower()).strip("-")
    if not slug:
        slug = "productpulse-export"

    if timestamp is None:
        return f"{slug}.csv"

    try:
        ts_float = float(timestamp)  # type: ignore
        if ts_float != ts_float:
            raise ValueError("timestamp is NaN")
        suffix = pd.to_datetime(ts_float, unit="s").strftime("%Y%m%d_%H%M%S")
    except (ValueError, TypeError):
        suffix = "export"

    return f"{slug}_{suffix}.csv"
