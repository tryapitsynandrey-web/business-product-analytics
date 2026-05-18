"""
revenue_metrics.py — Revenue health metric calculations.

All functions are pure, deterministic, and safe for zero denominators.
Inputs are plain floats; no DataFrames or side effects.

Covers:
- ARR
- Revenue growth rate
- Revenue concentration
- Recurring revenue ratio
- Expansion revenue ratio
- Refund rate
- Failed payment rate
"""

from __future__ import annotations

from core.business_health._utils import safe_divide, percentage_change


def calculate_arr(mrr: float) -> float:
    """
    ARR = MRR × 12.

    Annual Recurring Revenue. Annualises the monthly subscription base.
    """
    return mrr * 12.0


def calculate_revenue_growth_rate(current_revenue: float, previous_revenue: float) -> float:
    """
    Revenue Growth Rate = (Current - Previous) / |Previous|.

    Expressed as a decimal. Returns 0.0 when previous_revenue is zero.
    Positive = growth, negative = contraction.
    """
    return percentage_change(current_revenue, previous_revenue)


def calculate_revenue_concentration(total_revenue: float, largest_customer_revenue: float) -> float:
    """
    Revenue Concentration = Largest Customer Revenue / Total Revenue.

    Expressed as a decimal (0.0–1.0). High concentration signals risk.
    Returns 0.0 when total_revenue is zero.
    """
    return safe_divide(largest_customer_revenue, total_revenue)


def calculate_recurring_revenue_ratio(recurring_revenue: float, total_revenue: float) -> float:
    """
    Recurring Revenue Ratio = Recurring Revenue / Total Revenue.

    Measures the proportion of revenue that is predictable.
    Returns 0.0 when total_revenue is zero.
    """
    return safe_divide(recurring_revenue, total_revenue)


def calculate_expansion_revenue_ratio(expansion_revenue: float, total_revenue: float) -> float:
    """
    Expansion Revenue Ratio = Expansion Revenue / Total Revenue.

    Tracks the share of revenue coming from upsells and upgrades.
    Returns 0.0 when total_revenue is zero.
    """
    return safe_divide(expansion_revenue, total_revenue)


def calculate_refund_rate(refunds: float, total_revenue: float) -> float:
    """
    Refund Rate = Refunds / Total Revenue.

    Expressed as a decimal. Returns 0.0 when total_revenue is zero.
    High refund rates signal product-market fit or billing issues.
    """
    return safe_divide(refunds, total_revenue)


def calculate_failed_payment_rate(failed_payments: float, total_payments: float) -> float:
    """
    Failed Payment Rate = Failed Payments / Total Payments.

    Expressed as a decimal. Returns 0.0 when total_payments is zero.
    A rising rate indicates billing infrastructure or fraud issues.
    """
    return safe_divide(failed_payments, total_payments)
