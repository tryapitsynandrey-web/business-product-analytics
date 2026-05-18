"""
growth_metrics.py — Business growth metric calculations.

All functions are pure, deterministic, and safe for zero denominators.
Inputs are plain floats; no DataFrames or side effects.

Covers:
- Customer growth rate
- User growth rate
- Activation growth rate
- Retention growth rate
- Growth efficiency
"""

from __future__ import annotations

from core.business_health._utils import safe_divide, percentage_change


def calculate_customer_growth_rate(current_customers: float, previous_customers: float) -> float:
    """
    Customer Growth Rate = (Current - Previous) / |Previous|.

    Expressed as a decimal. Returns 0.0 when previous is zero.
    """
    return percentage_change(current_customers, previous_customers)


def calculate_user_growth_rate(current_users: float, previous_users: float) -> float:
    """
    User Growth Rate = (Current - Previous) / |Previous|.

    Expressed as a decimal. Returns 0.0 when previous is zero.
    Measures growth in total active or registered users.
    """
    return percentage_change(current_users, previous_users)


def calculate_activation_growth_rate(
    current_activation_rate: float, previous_activation_rate: float
) -> float:
    """
    Activation Growth Rate = (Current Rate - Previous Rate) / |Previous Rate|.

    Expressed as a decimal. Returns 0.0 when previous rate is zero.
    Positive means more users are reaching the activation milestone.
    """
    return percentage_change(current_activation_rate, previous_activation_rate)


def calculate_retention_growth_rate(
    current_retention_rate: float, previous_retention_rate: float
) -> float:
    """
    Retention Growth Rate = (Current Rate - Previous Rate) / |Previous Rate|.

    Expressed as a decimal. Returns 0.0 when previous rate is zero.
    Positive means retention is improving period-over-period.
    """
    return percentage_change(current_retention_rate, previous_retention_rate)


def calculate_growth_efficiency(revenue_growth: float, sales_and_marketing_spend: float) -> float:
    """
    Growth Efficiency = Revenue Growth / Sales & Marketing Spend.

    Measures how much revenue growth is generated per dollar of S&M spend.
    Returns 0.0 when spend is zero.
    A ratio > 1.0 means each dollar of spend generated more than one dollar of growth.
    """
    return safe_divide(revenue_growth, sales_and_marketing_spend)
