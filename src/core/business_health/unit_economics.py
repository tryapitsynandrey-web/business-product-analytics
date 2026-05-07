"""
unit_economics.py — Unit economics metric calculations.

All functions are pure, deterministic, and safe for zero denominators.
Inputs are plain floats; no DataFrames or side effects.

Covers:
- LTV
- CAC
- LTV:CAC ratio
- CAC payback period
- Customer profitability
"""

from __future__ import annotations

from core.business_health._utils import safe_divide


def calculate_ltv(arpu: float, gross_margin: float, churn_rate: float) -> float:
    """
    LTV = (ARPU × Gross Margin) / Churn Rate.

    Lifetime Value — the expected revenue a customer generates before churning,
    weighted by gross margin to reflect true profitability.

    Returns 0.0 when churn_rate is zero (infinite lifetime, undefined LTV).
    """
    return safe_divide(arpu * gross_margin, churn_rate)


def calculate_cac(
    marketing_spend: float, sales_spend: float, new_customers: float
) -> float:
    """
    CAC = (Marketing Spend + Sales Spend) / New Customers.

    Customer Acquisition Cost — total spend required to acquire one new customer.
    Returns 0.0 when new_customers is zero.
    """
    return safe_divide(marketing_spend + sales_spend, new_customers)


def calculate_ltv_to_cac_ratio(ltv: float, cac: float) -> float:
    """
    LTV:CAC = LTV / CAC.

    A ratio above 3.0 is generally considered healthy for SaaS.
    Returns 0.0 when CAC is zero.
    """
    return safe_divide(ltv, cac)


def calculate_cac_payback_period(
    cac: float, arpu: float, gross_margin: float
) -> float:
    """
    CAC Payback Period = CAC / (ARPU × Gross Margin).

    Number of months to recover the cost of acquiring a customer through
    gross-margin-adjusted revenue.

    Returns 0.0 when denominator is zero (unrecoverable or undefined).
    """
    return safe_divide(cac, arpu * gross_margin)


def calculate_customer_profitability(
    revenue_per_customer: float, cost_to_serve: float
) -> float:
    """
    Customer Profitability = Revenue Per Customer - Cost to Serve.

    The net margin contribution of a single customer.
    Negative means the company loses money on that customer.
    """
    return revenue_per_customer - cost_to_serve
