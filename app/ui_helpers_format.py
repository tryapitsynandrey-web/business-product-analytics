import re
import pandas as pd
from typing import Any, Optional

EXECUTIVE_METRICS = {
    "monthly_recurring_revenue": "Total MRR",
    "customer_churn_rate": "Churn Rate",
    "average_revenue_per_user": "ARPU",
    "revenue_at_risk": "Revenue at Risk",
}

QUALITY_SCORE_COLUMNS = {
    "completeness_score": "Completeness",
    "uniqueness_score": "Uniqueness",
    "validity_score": "Validity",
    "referential_integrity_score": "Referential Integrity",
}

QUALITY_STATUS_ORDER = {
    "critical": 0,
    "risk": 1,
    "watch": 2,
    "good": 3,
}

DECISION_BRIEF_IMPACT_COLUMNS = [
    "estimated_revenue_impact",
    "revenue_at_risk",
    "estimated_revenue_loss",
    "estimated_loss",
    "current_mrr",
    "total_revenue",
]

DECISION_BRIEF_IMPACT_LABELS = {
    "estimated_revenue_impact": "Estimated Revenue Impact",
    "revenue_at_risk": "Revenue at Risk",
    "estimated_revenue_loss": "Estimated Revenue Loss",
    "estimated_loss": "Estimated Loss",
    "current_mrr": "Current MRR",
    "total_revenue": "Total Revenue",
}

DECISION_BRIEF_TITLE_COLUMNS = [
    "recommendation_title",
    "customer_id",
    "intervention_id",
    "metric_name",
    "leakage_type",
    "trace_id",
    "rule_id",
]

DECISION_BRIEF_ACTION_COLUMNS = [
    "expected_action",
    "recommended_action",
    "generated_action",
    "reason",
    "business_impact",
    "explanation",
]

DECISION_BRIEF_OWNER_COLUMNS = [
    "suggested_owner",
    "owner",
    "metric_owner",
    "category",
    "segment",
    "target_segment",
]

DECISION_BRIEF_STATUS_COLUMNS = [
    "priority_band",
    "risk_band",
    "churn_risk_band",
    "confidence_level",
    "status",
    "health_status",
    "lineage_status",
]

DECISION_BRIEF_SORT_COLUMNS = [
    "priority_score",
    "impact_score",
    "risk_score",
    "churn_risk_score",
    "estimated_revenue_impact",
    "revenue_at_risk",
    "estimated_revenue_loss",
    "current_mrr",
]

CUSTOMER_QUEUE_COLUMNS = [
    "customer_id",
    "segment",
    "plan",
    "churn_risk_band",
    "health_status",
    "current_mrr",
    "revenue_at_risk",
    "churn_risk_score",
    "usage_trend",
    "main_driver",
    "recommended_action",
]

CUSTOMER_RISK_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}

ACTION_QUEUE_COLUMNS = [
    "intervention_id",
    "recommendation_title",
    "priority_band",
    "estimated_revenue_impact",
    "priority_score",
    "effort_level",
    "suggested_owner",
    "target_segment",
    "expected_action",
]

ACTION_EFFORT_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
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

SCENARIO_ANALYSIS_COLUMNS = [
    "scenario_name",
    "baseline_value",
    "simulated_value",
    "monthly_impact",
    "annualized_impact",
    "confidence_note",
]


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
            "action": "Run `make run`, then reload this page.",
            "severity": "error",
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
            "action": "Run `make run`, then reload this page.",
            "severity": "error",
        }

    age_seconds = max(0.0, now - updated)
    age_hours = age_seconds / 3600
    if age_hours <= warning_hours:
        status = "🟢 Fresh"
        severity = "success"
        action = "Ready for review."
    elif age_hours <= stale_hours:
        status = "🟡 Aging"
        severity = "warning"
        action = "Run `make run` before sharing or making decisions from this snapshot."
    else:
        status = "🔴 Stale"
        severity = "error"
        action = "Run `make run` before using this dashboard for review."

    age = format_duration(age_seconds)
    return {
        "status": status,
        "updated_at": format_timestamp(updated),
        "age": age,
        "caption": f"Local analytics database was updated {age} ago.",
        "action": action,
        "severity": severity,
    }


def build_demo_readiness_summary(
    db_exists: bool,
    table_count: int = 0,
    total_rows: int = 0,
) -> dict[str, str]:
    """Return display-ready demo readiness guidance for reviewers."""
    if not db_exists:
        return {
            "status": "Setup needed",
            "severity": "error",
            "summary": "No local demo database found.",
            "action": "Run `make reset-demo` to rebuild the deterministic demo snapshot.",
        }

    if table_count <= 0:
        return {
            "status": "Needs refresh",
            "severity": "warning",
            "summary": "Local demo database is present, but no readable tables were found.",
            "action": "Run `make reset-demo`, then reload this page.",
        }

    return {
        "status": "Reviewer ready",
        "severity": "success",
        "summary": f"{table_count} table(s) and {total_rows:,} row(s) are available.",
        "action": "Use the dashboard flow, or run `make reset-demo` for a clean snapshot.",
    }


def db_status_label(exists: bool) -> str:
    """Return stylized DB status."""
    return "🟢 Online" if exists else "🔴 Missing"


def safe_dataframe_empty_message(
    df: pd.DataFrame | None,
    label: str,
    *,
    filtered: bool = False,
) -> str:
    """Return a message indicating a dataframe is empty or missing."""
    if filtered:
        return f"No {label} records match the current filters. Clear filters or search, then retry."
    if df is None:
        return f"No {label} data source is available. Run `make run`, then reload this page."
    if df.empty:
        return f"No {label} data available. Run `make run`, then reload this page if this is unexpected."
    return ""


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
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
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
