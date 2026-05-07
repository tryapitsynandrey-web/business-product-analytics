import pandas as pd
from typing import Any, Optional

def format_currency(value: float) -> str:
    """Format a float as currency (e.g., $1,234.56)."""
    try:
        val = float(value)
        return f"${val:,.2f}"
    except (ValueError, TypeError):
        return "N/A"

def format_percentage(value: float) -> str:
    """Format a float as percentage (e.g., 15.5%)."""
    try:
        val = float(value)
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

def status_badge_text(status: str) -> str:
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

def format_file_size(size_bytes: int | float | None) -> str:
    """Format bytes into readable string."""
    if size_bytes is None:
        return "Unknown"
    try:
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    except (ValueError, TypeError):
        return "Unknown"

def format_timestamp(timestamp: float | None) -> str:
    """Format UNIX timestamp to human readable string."""
    if timestamp is None:
        return "Unknown"
    try:
        dt = pd.to_datetime(timestamp, unit='s')
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

def prepare_category_counts(df: pd.DataFrame | None, category_column: str) -> pd.DataFrame:
    """Prepare a count of categories for a bar chart."""
    if df is None or df.empty or category_column not in df.columns:
        return pd.DataFrame()
        
    counts = df[category_column].value_counts().to_frame("count")
    return counts
