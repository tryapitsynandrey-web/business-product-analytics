import re
import pandas as pd
import streamlit as st
from typing import Any, Optional

from core.scenario_simulator import ScenarioSimulator

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


def build_custom_scenario_analysis(
    kpis: pd.DataFrame | None,
    customers: pd.DataFrame | None,
    leakages: pd.DataFrame | None,
    churn_improvement_rate: float,
    activation_improvement_rate: float,
    arpu_increase_rate: float,
    failed_payment_recovery_rate: float,
) -> pd.DataFrame:
    """Build custom scenario rows from persisted dashboard data and UI assumptions."""
    source_kpis = kpis if isinstance(kpis, pd.DataFrame) else pd.DataFrame()
    source_customers = customers if isinstance(customers, pd.DataFrame) else pd.DataFrame()
    source_leakages = leakages if isinstance(leakages, pd.DataFrame) else pd.DataFrame()

    customer_ids = source_customers.get(
        "customer_id", pd.Series(index=source_customers.index, dtype=object)
    )
    current_mrr = pd.to_numeric(
        source_customers.get("current_mrr", pd.Series(0.0, index=source_customers.index)),
        errors="coerce",
    ).fillna(0.0)
    leakage_types = source_leakages.get(
        "leakage_type", pd.Series(index=source_leakages.index, dtype=object)
    )
    leakage_losses = pd.to_numeric(
        source_leakages.get(
            "estimated_revenue_loss",
            pd.Series(0.0, index=source_leakages.index),
        ),
        errors="coerce",
    ).fillna(0.0)

    baseline_revenue = _metric_float(source_kpis, "monthly_recurring_revenue")
    churn_rate = _metric_float(source_kpis, "customer_churn_rate")
    activation_rate = _metric_float(source_kpis, "activation_rate")
    arpu = _metric_float(source_kpis, "average_revenue_per_user")
    signups = int(customer_ids.nunique())
    active_customers = int(customer_ids[current_mrr > 0].nunique())
    failed_payment_amount = float(leakage_losses[leakage_types == "Failed Payment"].sum())

    simulator = ScenarioSimulator()
    rows: list[dict[str, Any]] = []
    if baseline_revenue is not None and churn_rate is not None:
        rows.append(
            simulator.simulate_churn_reduction(baseline_revenue, churn_rate, churn_improvement_rate)
        )
    if signups > 0 and activation_rate is not None and arpu is not None:
        rows.append(
            simulator.simulate_activation_increase(
                signups, activation_rate, activation_improvement_rate, arpu
            )
        )
    if active_customers > 0 and arpu is not None:
        rows.append(simulator.simulate_arpu_increase(active_customers, arpu, arpu_increase_rate))
    if failed_payment_amount > 0:
        rows.append(
            simulator.simulate_failed_payment_recovery(
                failed_payment_amount, failed_payment_recovery_rate
            )
        )

    return pd.DataFrame(rows, columns=SCENARIO_ANALYSIS_COLUMNS)


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


@st.cache_data  # type: ignore
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


def build_top_actions_overview(actions: pd.DataFrame | None) -> dict[str, Any]:
    """Return high-signal summary metrics for the current action queue."""
    if actions is None or actions.empty:
        return {
            "actions": 0,
            "critical_high": 0,
            "quick_wins": 0,
            "owners": 0,
            "impact_total": 0.0,
            "average_priority_score": 0.0,
            "top_owner": "Unassigned",
        }

    data = actions.copy()
    priority = data.get("priority_band", pd.Series("", index=data.index))
    effort = data.get("effort_level", pd.Series("", index=data.index))
    owner = data.get("suggested_owner", pd.Series("", index=data.index))
    impact = pd.to_numeric(
        data.get("estimated_revenue_impact", pd.Series(0.0, index=data.index)),
        errors="coerce",
    ).fillna(0.0)
    priority_score = pd.to_numeric(
        data.get("priority_score", pd.Series(0.0, index=data.index)),
        errors="coerce",
    ).fillna(0.0)

    priority_normalized = priority.astype(str).str.strip().str.lower()
    effort_normalized = effort.astype(str).str.strip().str.lower()
    owner_clean = owner.apply(lambda value: _clean_display_value(value, "Unassigned"))
    assigned_owners = owner_clean[owner_clean != "Unassigned"]

    top_owner = "Unassigned"
    if not assigned_owners.empty:
        top_owner = str(assigned_owners.value_counts().idxmax())

    return {
        "actions": int(len(data)),
        "critical_high": int(priority_normalized.isin({"critical", "high"}).sum()),
        "quick_wins": int(effort_normalized.eq("low").sum()),
        "owners": int(assigned_owners.nunique()),
        "impact_total": float(impact.sum()),
        "average_priority_score": float(priority_score.mean()),
        "top_owner": top_owner,
    }


def prepare_action_priority_queue(
    actions: pd.DataFrame | None,
    limit: int = 25,
) -> pd.DataFrame:
    """Return a compact action queue sorted by priority, impact, and effort."""
    if actions is None or actions.empty:
        return pd.DataFrame(columns=ACTION_QUEUE_COLUMNS)

    data = actions.copy()
    priority_score = pd.to_numeric(
        data.get("priority_score", pd.Series(0.0, index=data.index)),
        errors="coerce",
    ).fillna(0.0)
    impact = pd.to_numeric(
        data.get("estimated_revenue_impact", pd.Series(0.0, index=data.index)),
        errors="coerce",
    ).fillna(0.0)
    effort = data.get("effort_level", pd.Series("", index=data.index))
    effort_order = effort.astype(str).str.strip().str.lower().map(ACTION_EFFORT_ORDER).fillna(9)

    data["_priority_score"] = priority_score
    data["_estimated_revenue_impact"] = impact
    data["_effort_order"] = effort_order
    data["intervention_id"] = data.get("intervention_id", pd.Series("", index=data.index)).astype(
        str
    )
    display_cols = [col for col in ACTION_QUEUE_COLUMNS if col in data.columns]
    return (
        data.sort_values(
            ["_priority_score", "_estimated_revenue_impact", "_effort_order", "intervention_id"],
            ascending=[False, False, True, True],
        )[display_cols]
        .head(limit)
        .reset_index(drop=True)
    )


def _first_existing_column(df: pd.DataFrame, columns: list[str]) -> str | None:
    for col in columns:
        if col in df.columns:
            return col
    return None


def _clean_display_value(value: object, fallback: str = "Unknown") -> str:
    if value is None:
        return fallback

    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "<na>", "none"}:
        return fallback
    return text


def _sum_first_existing_numeric(
    df: pd.DataFrame,
    columns: list[str],
) -> tuple[str | None, float]:
    for col in columns:
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce").fillna(0)
            return col, float(values.sum())
    return None, 0.0


def _row_first_existing_numeric(row: pd.Series, columns: list[str]) -> tuple[str | None, float]:
    for col in columns:
        if col not in row.index:
            continue
        value = pd.to_numeric(pd.Series([row[col]]), errors="coerce").fillna(0).iloc[0]
        return col, float(value)
    return None, 0.0


def _count_urgent_records(df: pd.DataFrame) -> int:
    return int(_urgent_record_mask(df).sum())


def _urgent_record_mask(df: pd.DataFrame) -> pd.Series:
    available = [col for col in DECISION_BRIEF_STATUS_COLUMNS if col in df.columns]
    mask = pd.Series(False, index=df.index)
    if not available:
        return mask

    urgent_values = {"critical", "high"}
    for col in available:
        values = df[col].astype(str).str.strip().str.lower()
        mask = mask | values.isin(urgent_values)
    return mask


def _sort_decision_brief_rows(df: pd.DataFrame) -> pd.DataFrame:
    available = [col for col in DECISION_BRIEF_SORT_COLUMNS if col in df.columns]
    if not available:
        return df

    score = pd.Series(0.0, index=df.index)
    for col in available:
        values = pd.to_numeric(df[col], errors="coerce").fillna(0)
        score = score.where(score >= values, values)

    if not bool(score.gt(0).any()):
        return df

    sortable = df.copy()
    sortable["_decision_brief_sort_score"] = score
    return sortable.sort_values("_decision_brief_sort_score", ascending=False).drop(
        columns=["_decision_brief_sort_score"]
    )


def _build_decision_brief_actions(df: pd.DataFrame, max_items: int) -> list[dict[str, str]]:
    title_col = _first_existing_column(df, DECISION_BRIEF_TITLE_COLUMNS)
    action_col = _first_existing_column(df, DECISION_BRIEF_ACTION_COLUMNS)
    owner_col = _first_existing_column(df, DECISION_BRIEF_OWNER_COLUMNS)
    status_col = _first_existing_column(df, DECISION_BRIEF_STATUS_COLUMNS)

    actions = []
    for _, row in _sort_decision_brief_rows(df).head(max_items).iterrows():
        impact_col, impact_value = _row_first_existing_numeric(row, DECISION_BRIEF_IMPACT_COLUMNS)
        impact_label = DECISION_BRIEF_IMPACT_LABELS.get(impact_col or "", "Impact")

        title = _clean_display_value(row.get(title_col), "Record") if title_col else "Record"
        action = (
            _clean_display_value(row.get(action_col), "Review record details.")
            if action_col
            else "Review record details."
        )
        owner = (
            _clean_display_value(row.get(owner_col), "Unassigned") if owner_col else "Unassigned"
        )
        status = _clean_display_value(row.get(status_col), "Unscored") if status_col else "Unscored"

        actions.append(
            {
                "title": title,
                "action": action,
                "owner": owner,
                "status": status,
                "impact_label": impact_label,
                "impact": format_currency(impact_value),
            }
        )

    return actions


def build_decision_brief(
    df: pd.DataFrame | None,
    title: str,
    quick_view: str = "All",
    max_items: int = 3,
) -> dict[str, Any]:
    """Return a display-ready decision brief for the current dashboard view."""
    if df is None or df.empty:
        return {
            "title": title,
            "quick_view": quick_view,
            "records": 0,
            "impact_label": "Revenue Impact",
            "impact_total": 0.0,
            "formatted_impact": format_currency(0.0),
            "urgent_count": 0,
            "summary": "No rows match current decision view.",
            "why_it_matters": "Adjust filters or refresh source data before assigning work.",
            "top_actions": [],
        }

    data = df.copy()
    impact_col, impact_total = _sum_first_existing_numeric(data, DECISION_BRIEF_IMPACT_COLUMNS)
    impact_label = DECISION_BRIEF_IMPACT_LABELS.get(impact_col or "", "Revenue Impact")
    urgent_count = _count_urgent_records(data)
    records = len(data)
    formatted_impact = format_currency(impact_total)

    summary = (
        f"{records} record(s) in {quick_view} with {impact_label.lower()} of "
        f"{formatted_impact} and {urgent_count} critical/high item(s)."
    )

    if impact_total > 0 and urgent_count > 0:
        why_it_matters = (
            f"Focus here first: urgent records carry {formatted_impact} in tracked exposure."
        )
    elif impact_total > 0:
        why_it_matters = f"Use this view to protect or capture {formatted_impact}."
    elif urgent_count > 0:
        why_it_matters = "Use this view to clear urgent operational risk."
    else:
        why_it_matters = "Use this view to assign owners and validate next operational actions."

    return {
        "title": title,
        "quick_view": quick_view,
        "records": records,
        "impact_label": impact_label,
        "impact_total": impact_total,
        "formatted_impact": formatted_impact,
        "urgent_count": urgent_count,
        "summary": summary,
        "why_it_matters": why_it_matters,
        "top_actions": _build_decision_brief_actions(data, max_items),
    }


def decision_brief_to_markdown(brief: dict[str, Any]) -> str:
    """Serialize a decision brief to Markdown for local handoff/export."""
    title = _clean_display_value(brief.get("title"), "Decision Brief")
    lines = [
        f"# {title}",
        "",
        f"- Quick view: {_clean_display_value(brief.get('quick_view'), 'All')}",
        f"- Records: {int(brief.get('records', 0) or 0)}",
        (
            f"- {_clean_display_value(brief.get('impact_label'), 'Revenue Impact')}: "
            f"{_clean_display_value(brief.get('formatted_impact'), '$0.00')}"
        ),
        f"- Critical/high items: {int(brief.get('urgent_count', 0) or 0)}",
        "",
        "## Summary",
        "",
        _clean_display_value(brief.get("summary"), "No summary available."),
        "",
        "## Why It Matters",
        "",
        _clean_display_value(brief.get("why_it_matters"), "No impact note available."),
    ]

    top_actions = brief.get("top_actions", [])
    if isinstance(top_actions, list) and top_actions:
        lines.extend(["", "## Top Actions", ""])
        for index, item in enumerate(top_actions, start=1):
            if not isinstance(item, dict):
                continue
            action_title = _clean_display_value(item.get("title"), "Record")
            action_text = _clean_display_value(item.get("action"), "Review record details.")
            owner = _clean_display_value(item.get("owner"), "Unassigned")
            status = _clean_display_value(item.get("status"), "Unscored")
            impact = _clean_display_value(item.get("impact"), "$0.00")
            lines.append(
                f"{index}. **{action_title}** - {action_text} "
                f"(owner: {owner}; status: {status}; impact: {impact})"
            )

    return "\n".join(lines).strip() + "\n"


def prepare_owner_workload_summary(
    df: pd.DataFrame | None,
    owner_columns: list[str] | None = None,
    impact_columns: list[str] | None = None,
    max_groups: int = 8,
) -> pd.DataFrame:
    """Summarize action workload by owner for dashboard handoff views."""
    columns = ["owner", "records", "critical_high", "impact_total"]
    if df is None or df.empty:
        return pd.DataFrame(columns=columns)

    data = df.copy()
    owner_col = _first_existing_column(
        data,
        owner_columns or ["suggested_owner", "owner", "metric_owner"],
    )
    if owner_col is None:
        return pd.DataFrame(columns=columns)

    impact_col = _first_existing_column(data, impact_columns or DECISION_BRIEF_IMPACT_COLUMNS)
    impact_values = (
        pd.to_numeric(data[impact_col], errors="coerce").fillna(0)
        if impact_col is not None
        else pd.Series(0.0, index=data.index)
    )

    grouped = pd.DataFrame(
        {
            "_owner": data[owner_col].apply(
                lambda value: _clean_display_value(value, "Unassigned")
            ),
            "_impact": impact_values,
            "_urgent": _urgent_record_mask(data),
        }
    )
    summary = (
        grouped.groupby("_owner", dropna=False)
        .agg(
            records=("_owner", "size"),
            critical_high=("_urgent", "sum"),
            impact_total=("_impact", "sum"),
        )
        .reset_index()
        .rename(columns={"_owner": "owner"})
    )
    summary["records"] = summary["records"].astype(int)
    summary["critical_high"] = summary["critical_high"].astype(int)
    summary["impact_total"] = summary["impact_total"].astype(float)

    return (
        summary.sort_values(
            ["critical_high", "impact_total", "records", "owner"],
            ascending=[False, False, False, True],
        )
        .head(max_groups)
        .reset_index(drop=True)
    )


def quality_status_for_score(score: object) -> str:
    """Map a normalized quality score to a dashboard status band."""
    try:
        value = float(score)  # type: ignore
    except (TypeError, ValueError):
        return "Unknown"

    if value >= 0.90:
        return "Good"
    if value >= 0.75:
        return "Watch"
    if value >= 0.50:
        return "Risk"
    return "Critical"


def _lowest_quality_dimension(row: pd.Series) -> tuple[str, float]:
    values = []
    for col, label in QUALITY_SCORE_COLUMNS.items():
        if col not in row.index:
            continue
        score = pd.to_numeric(pd.Series([row[col]]), errors="coerce").iloc[0]
        if pd.isna(score):
            continue
        values.append((label, float(score)))

    if not values:
        return "Unknown", 0.0
    return min(values, key=lambda item: item[1])


def build_data_quality_overview(df: pd.DataFrame | None) -> dict[str, object]:
    """Return headline metrics for a data quality score table."""
    if df is None or df.empty:
        return {
            "datasets": 0,
            "average_score": 0.0,
            "average_score_display": format_percentage(0.0),
            "needs_attention": 0,
            "worst_status": "Unknown",
            "lowest_dimension": "Unknown",
            "lowest_dimension_score": 0.0,
            "lowest_dimension_display": format_percentage(0.0),
        }

    data = df.copy()
    if "overall_score" in data.columns:
        scores = pd.to_numeric(data["overall_score"], errors="coerce").fillna(0)
    else:
        available_scores = [col for col in QUALITY_SCORE_COLUMNS if col in data.columns]
        if available_scores:
            scores = data[available_scores].apply(pd.to_numeric, errors="coerce").mean(axis=1)
        else:
            scores = pd.Series(0.0, index=data.index)

    statuses = (
        data["status"].astype(str).str.lower()
        if "status" in data.columns
        else scores.apply(quality_status_for_score).astype(str).str.lower()
    )
    attention_mask = statuses.isin({"watch", "risk", "critical"})
    worst_status = "Unknown"
    if not statuses.empty:
        worst_key = min(statuses, key=lambda status: QUALITY_STATUS_ORDER.get(status, 999))
        worst_status = worst_key.title()

    dimension_summary = prepare_quality_dimension_summary(data)
    if dimension_summary.empty:
        lowest_dimension = "Unknown"
        lowest_dimension_score = 0.0
    else:
        first_row = dimension_summary.iloc[0]
        lowest_dimension = str(first_row["dimension"])
        lowest_dimension_score = float(first_row["average_score"])

    average_score = scores.mean() if not scores.empty else 0.0
    return {
        "datasets": len(data),
        "average_score": average_score,
        "average_score_display": format_percentage(average_score),
        "needs_attention": attention_mask.sum(),
        "worst_status": worst_status,
        "lowest_dimension": lowest_dimension,
        "lowest_dimension_score": lowest_dimension_score,
        "lowest_dimension_display": format_percentage(lowest_dimension_score),
    }


def prepare_quality_dimension_summary(df: pd.DataFrame | None) -> pd.DataFrame:
    """Return average data quality scores by dimension, lowest first."""
    columns = ["dimension", "average_score", "status"]
    if df is None or df.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for col, label in QUALITY_SCORE_COLUMNS.items():
        if col not in df.columns:
            continue
        values = pd.to_numeric(df[col], errors="coerce").dropna()
        if values.empty:
            continue
        average_score = values.mean()
        rows.append(
            {
                "dimension": label,
                "average_score": average_score,
                "status": quality_status_for_score(average_score),
            }
        )

    if not rows:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(rows).sort_values("average_score", ascending=True).reset_index(drop=True)


def prepare_quality_issue_queue(df: pd.DataFrame | None) -> pd.DataFrame:
    """Return datasets ordered by quality risk with their weakest dimension."""
    columns = [
        "dataset",
        "status",
        "overall_score",
        "lowest_dimension",
        "lowest_dimension_score",
        "business_risk",
    ]
    if df is None or df.empty:
        return pd.DataFrame(columns=columns)

    data = df.copy()
    if "dataset" not in data.columns:
        return pd.DataFrame(columns=columns)

    if "overall_score" in data.columns:
        data["overall_score"] = pd.to_numeric(data["overall_score"], errors="coerce").fillna(0.0)  # type: ignore
    else:
        score_cols = [col for col in QUALITY_SCORE_COLUMNS if col in data.columns]
        data["overall_score"] = (
            data[score_cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)
            if score_cols
            else pd.Series(0.0, index=data.index)
        )

    if "status" not in data.columns:
        data["status"] = data["overall_score"].apply(quality_status_for_score)
    if "business_risk" not in data.columns:
        data["business_risk"] = ""

    weakest = data.apply(_lowest_quality_dimension, axis=1)
    data["lowest_dimension"] = [item[0] for item in weakest]
    data["lowest_dimension_score"] = [item[1] for item in weakest]
    data["_status_order"] = (
        data["status"].astype(str).str.lower().map(QUALITY_STATUS_ORDER).fillna(999)
    )

    return (
        data[columns + ["_status_order"]]
        .sort_values(["_status_order", "overall_score", "dataset"], ascending=True)
        .drop(columns=["_status_order"])
        .reset_index(drop=True)
    )


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


def build_customer_360_overview(customers: pd.DataFrame | None) -> dict[str, Any]:
    """Return high-signal Customer 360 metrics for the active view."""
    if customers is None or customers.empty:
        return {
            "customers": 0,
            "active_customers": 0,
            "high_risk_customers": 0,
            "revenue_at_risk": 0.0,
            "current_mrr": 0.0,
            "average_risk_score": 0.0,
            "top_driver": "Unknown",
        }

    data = customers.copy()
    current_mrr = pd.to_numeric(
        data.get("current_mrr", pd.Series(0.0, index=data.index)),
        errors="coerce",
    ).fillna(0.0)
    revenue_at_risk = pd.to_numeric(
        data.get("revenue_at_risk", pd.Series(0.0, index=data.index)),
        errors="coerce",
    ).fillna(0.0)
    risk_score = pd.to_numeric(
        data.get("churn_risk_score", pd.Series(0.0, index=data.index)),
        errors="coerce",
    ).fillna(0.0)
    risk_band = data.get("churn_risk_band", pd.Series("", index=data.index))
    high_risk_mask = risk_band.astype(str).str.strip().str.lower().isin({"critical", "high"})

    if "is_active" in data.columns:
        active_mask = (
            data["is_active"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin({"true", "1", "yes", "active"})
        )
    else:
        active_mask = current_mrr > 0

    top_driver = "Unknown"
    if "main_driver" in data.columns:
        drivers = data["main_driver"].dropna().astype(str).str.strip()
        drivers = drivers[~drivers.str.lower().isin({"", "nan", "none", "unknown"})]
        if not drivers.empty:
            top_driver = str(drivers.value_counts().idxmax())

    return {
        "customers": int(len(data)),
        "active_customers": int(active_mask.sum()),
        "high_risk_customers": int(high_risk_mask.sum()),
        "revenue_at_risk": float(revenue_at_risk.sum()),
        "current_mrr": float(current_mrr.sum()),
        "average_risk_score": float(risk_score.mean()),
        "top_driver": top_driver,
    }


def prepare_customer_360_queue(
    customers: pd.DataFrame | None,
    limit: int = 25,
) -> pd.DataFrame:
    """Return a compact Customer 360 queue sorted by risk and revenue exposure."""
    if customers is None or customers.empty:
        return pd.DataFrame(columns=CUSTOMER_QUEUE_COLUMNS)

    data = customers.copy()
    risk_band = data.get("churn_risk_band", pd.Series("", index=data.index))
    risk_order = risk_band.astype(str).str.strip().str.lower().map(CUSTOMER_RISK_ORDER).fillna(4)
    risk_score = pd.to_numeric(
        data.get("churn_risk_score", pd.Series(0.0, index=data.index)),
        errors="coerce",
    ).fillna(0.0)
    revenue_at_risk = pd.to_numeric(
        data.get("revenue_at_risk", pd.Series(0.0, index=data.index)),
        errors="coerce",
    ).fillna(0.0)

    data["_risk_order"] = risk_order
    data["_risk_score"] = risk_score
    data["_revenue_at_risk"] = revenue_at_risk
    data["customer_id"] = data.get("customer_id", pd.Series("", index=data.index)).astype(str)
    display_cols = [col for col in CUSTOMER_QUEUE_COLUMNS if col in data.columns]
    return (
        data.sort_values(
            ["_risk_order", "_risk_score", "_revenue_at_risk", "customer_id"],
            ascending=[True, False, False, True],
        )[display_cols]
        .head(limit)
        .reset_index(drop=True)
    )


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
        cleaned = [value for value in (values or []) if value.strip()]
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
