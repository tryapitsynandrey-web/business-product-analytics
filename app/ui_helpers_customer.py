import pandas as pd
from typing import Any

from core.scenario_simulator import ScenarioSimulator
from app.ui_helpers_format import (
    CUSTOMER_QUEUE_COLUMNS,
    CUSTOMER_RISK_ORDER,
    QUALITY_SCORE_COLUMNS,
    QUALITY_STATUS_ORDER,
    SCENARIO_ANALYSIS_COLUMNS,
    format_percentage,
)
from app.ui_helpers_filter import (
    _metric_float,
    filter_dataframe_by_values,
)


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
    signups = customer_ids.nunique()
    active_customers = customer_ids[current_mrr > 0].nunique()
    failed_payment_amount = leakage_losses[leakage_types == "Failed Payment"].sum()

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
        "customers": len(data),
        "active_customers": active_mask.sum(),
        "high_risk_customers": high_risk_mask.sum(),
        "revenue_at_risk": revenue_at_risk.sum(),
        "current_mrr": current_mrr.sum(),
        "average_risk_score": risk_score.mean(),
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
