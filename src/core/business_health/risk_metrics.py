"""
risk_metrics.py — Business risk metric calculations.

All functions are pure, deterministic, and safe for zero denominators.
Inputs are plain floats; no DataFrames or side effects.

Covers:
- Customer concentration risk
- Margin compression
- Cash flow risk score
- Revenue dependency score
- Churn exposure
"""

from __future__ import annotations

from core.business_health._utils import safe_divide, clamp_score


def calculate_customer_concentration_risk(
    largest_customer_revenue: float, total_revenue: float
) -> float:
    """
    Customer Concentration Risk = Largest Customer Revenue / Total Revenue.

    Expressed as a decimal (0.0–1.0). High values indicate dangerous dependency
    on a single customer. > 0.2 is a common red-flag threshold.
    Returns 0.0 when total_revenue is zero.
    """
    return safe_divide(largest_customer_revenue, total_revenue)


def calculate_margin_compression(
    current_margin: float, previous_margin: float
) -> float:
    """
    Margin Compression = Current Margin - Previous Margin.

    Negative result means margins are shrinking (compression).
    Positive result means margins are expanding.
    Expressed in margin-point terms (e.g., -0.05 = 5 percentage points of compression).
    """
    return current_margin - previous_margin


def calculate_cashflow_risk_score(
    runway_months: float, burn_rate: float
) -> float:
    """
    Cash Flow Risk Score — 0 to 100 (higher = more risk).

    Score is derived from runway_months:
        - 18+ months: low risk (score = 0)
        - 12–17 months: moderate risk (score scales 25–50)
        - 6–11 months: high risk (score scales 50–75)
        - < 6 months: critical risk (score scales 75–100)

    burn_rate is accepted for future override logic; currently runway drives scoring.
    """
    # burn_rate is retained in the signature as a hook for future logic
    _ = burn_rate

    if runway_months <= 0:
        return 100.0
    if runway_months >= 18:
        return 0.0
    if runway_months >= 12:
        # Linear scale from 0 (at 18) to 25 (at 12)
        return clamp_score((18 - runway_months) / 6 * 25)
    if runway_months >= 6:
        # Linear scale from 25 (at 12) to 75 (at 6)
        return clamp_score(25 + (12 - runway_months) / 6 * 50)
    # < 6 months: scale from 75 (at 6) to 100 (at 0)
    return clamp_score(75 + (6 - runway_months) / 6 * 25)


def calculate_revenue_dependency_score(
    top_segment_revenue: float, total_revenue: float
) -> float:
    """
    Revenue Dependency Score = Top Segment Revenue / Total Revenue.

    Expressed as a decimal (0.0–1.0). A high score means the business
    is overly reliant on one segment. Complements concentration risk at segment level.
    Returns 0.0 when total_revenue is zero.
    """
    return safe_divide(top_segment_revenue, total_revenue)


def calculate_churn_exposure(
    revenue_at_risk: float, total_revenue: float
) -> float:
    """
    Churn Exposure = Revenue At Risk / Total Revenue.

    Expressed as a decimal (0.0–1.0). Proportion of total revenue that is
    at risk of churning within the next cycle.
    Returns 0.0 when total_revenue is zero.
    """
    return safe_divide(revenue_at_risk, total_revenue)
