import pandas as pd
from typing import Any, Optional

EXECUTIVE_METRICS = {
    "monthly_recurring_revenue": "Total MRR",
    "customer_churn_rate": "Churn Rate",
    "average_revenue_per_user": "ARPU",
    "revenue_at_risk": "Revenue at Risk",
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

def safe_metric_value(value: Any, fallback: str = "N/A") -> str:
    """Safely return a metric value as string or fallback if missing."""
    if pd.isna(value) or value is None:
        return fallback
    return str(value)

def select_metric_value(df: pd.DataFrame, metric_name: str, value_column: str = "value") -> Optional[Any]:
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
        for unit in ['B', 'KB', 'MB', 'GB']:
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
        dt = pd.to_datetime(ts_float, unit='s')
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return "Unknown"

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

def filter_dataframe_by_values(df: pd.DataFrame | None, column_name: str, selected_values: list[str]) -> pd.DataFrame:
    """Filter a dataframe by a list of selected values for a specific column."""
    if df is None or df.empty:
        return pd.DataFrame()
        
    df_copy = df.copy()
    if column_name not in df_copy.columns or not selected_values:
        return df_copy
        
    # We convert column values to string for safe comparison
    mask = df_copy[column_name].astype(str).isin(selected_values)
    return df_copy[mask]

def filter_dataframe_by_numeric_range(df: pd.DataFrame | None, column_name: str, min_value: float | None, max_value: float | None) -> pd.DataFrame:
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

def prepare_metric_chart_data(df: pd.DataFrame | None, metric_column: str = "metric_name", value_column: str = "value") -> pd.DataFrame:
    """Prepare data for a KPI metric bar chart, ensuring numeric values and setting index."""
    if df is None or df.empty or metric_column not in df.columns or value_column not in df.columns:
        return pd.DataFrame()
        
    chart_data = df.copy()
    
    # Convert values to numeric, dropping those that can't be converted
    chart_data[value_column] = pd.to_numeric(chart_data[value_column], errors='coerce')
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

def prepare_category_counts(df: pd.DataFrame | None, category_column: str = "category") -> pd.DataFrame:
    """Prepare a count of categories for a bar chart."""
    if df is None or df.empty or category_column not in df.columns:
        return pd.DataFrame()
        
    counts = df[category_column].value_counts().to_frame("count")
    return counts

def get_executive_metric_values(kpis: pd.DataFrame | None) -> dict[str, Optional[Any]]:
    """Return the main executive KPI values keyed by canonical metric name."""
    source = kpis if kpis is not None else pd.DataFrame()
    return {
        metric_name: select_metric_value(source, metric_name)
        for metric_name in EXECUTIVE_METRICS
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
