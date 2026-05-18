"""
profitability.py — Profitability and return metric calculations.

All functions are pure, deterministic, and safe for zero denominators.
Inputs are plain floats; no DataFrames or side effects.

Covers:
- Gross / operating / net profit and margin
- EBITDA and EBITDA margin
- ROI, ROA, ROE, ROIC, payback period
"""

from __future__ import annotations

from core.business_health._utils import safe_divide


# ---------------------------------------------------------------------------
# Profitability Metrics
# ---------------------------------------------------------------------------


def calculate_gross_profit(revenue: float, cost_of_goods_sold: float) -> float:
    """
    Gross Profit = Revenue - Cost of Goods Sold.

    Represents the profit after deducting direct production costs.
    Can be negative if COGS exceeds revenue.
    """
    return revenue - cost_of_goods_sold


def calculate_gross_margin(revenue: float, cost_of_goods_sold: float) -> float:
    """
    Gross Margin = Gross Profit / Revenue.

    Expressed as a decimal (0.0–1.0). Returns 0.0 when revenue is zero.
    A higher gross margin indicates more efficient production/delivery.
    """
    gross_profit = calculate_gross_profit(revenue, cost_of_goods_sold)
    return safe_divide(gross_profit, revenue)


def calculate_operating_profit(
    revenue: float,
    operating_expenses: float,
    cost_of_goods_sold: float,
) -> float:
    """
    Operating Profit (EBIT) = Revenue - COGS - Operating Expenses.

    Reflects profit from core operations before interest and taxes.
    """
    return revenue - cost_of_goods_sold - operating_expenses


def calculate_operating_margin(revenue: float, operating_profit: float) -> float:
    """
    Operating Margin = Operating Profit / Revenue.

    Expressed as a decimal. Returns 0.0 when revenue is zero.
    """
    return safe_divide(operating_profit, revenue)


def calculate_net_profit(revenue: float, total_expenses: float) -> float:
    """
    Net Profit = Revenue - Total Expenses.

    Bottom-line profit after all costs, interest, and taxes.
    """
    return revenue - total_expenses


def calculate_net_margin(revenue: float, net_profit: float) -> float:
    """
    Net Margin = Net Profit / Revenue.

    Expressed as a decimal. Returns 0.0 when revenue is zero.
    The definitive measure of overall profitability efficiency.
    """
    return safe_divide(net_profit, revenue)


def calculate_ebitda(
    net_income: float,
    interest: float,
    taxes: float,
    depreciation: float,
    amortization: float,
) -> float:
    """
    EBITDA = Net Income + Interest + Taxes + Depreciation + Amortization.

    Used to approximate operational cash generation. Excludes non-cash and
    financing items to allow cross-company comparison.
    """
    return net_income + interest + taxes + depreciation + amortization


def calculate_ebitda_margin(revenue: float, ebitda: float) -> float:
    """
    EBITDA Margin = EBITDA / Revenue.

    Expressed as a decimal. Returns 0.0 when revenue is zero.
    """
    return safe_divide(ebitda, revenue)


# ---------------------------------------------------------------------------
# Return Metrics
# ---------------------------------------------------------------------------


def calculate_roi(gain_from_investment: float, cost_of_investment: float) -> float:
    """
    ROI = (Gain - Cost) / Cost.

    Expressed as a decimal. Returns 0.0 when cost is zero.
    Positive ROI means the investment generated profit.
    """
    if not cost_of_investment:
        return 0.0
    return (gain_from_investment - cost_of_investment) / cost_of_investment


def calculate_roa(net_income: float, total_assets: float) -> float:
    """
    ROA = Net Income / Total Assets.

    Measures how efficiently assets generate profit.
    Returns 0.0 when total_assets is zero.
    """
    return safe_divide(net_income, total_assets)


def calculate_roe(net_income: float, shareholder_equity: float) -> float:
    """
    ROE = Net Income / Shareholder Equity.

    Measures profitability relative to shareholder investment.
    Returns 0.0 when equity is zero.
    """
    return safe_divide(net_income, shareholder_equity)


def calculate_roic(nopat: float, invested_capital: float) -> float:
    """
    ROIC = NOPAT / Invested Capital.

    NOPAT = Net Operating Profit After Tax.
    Measures how well capital is deployed across the business.
    Returns 0.0 when invested_capital is zero.
    """
    return safe_divide(nopat, invested_capital)


def calculate_payback_period(initial_investment: float, annual_cash_inflow: float) -> float:
    """
    Payback Period = Initial Investment / Annual Cash Inflow.

    Returns the number of years to recover the investment.
    Returns 0.0 when annual_cash_inflow is zero (unrecoverable).
    """
    return safe_divide(initial_investment, annual_cash_inflow)
