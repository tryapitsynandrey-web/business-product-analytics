"""
efficiency_metrics.py — Operational efficiency metric calculations.

All functions are pure, deterministic, and safe for zero denominators.
Inputs are plain floats; no DataFrames or side effects.

Covers:
- Revenue per employee
- Profit per employee
- Support cost per customer
- Cost to serve per customer
- Sales efficiency
- Marketing efficiency
"""

from __future__ import annotations

from core.business_health._utils import safe_divide


def calculate_revenue_per_employee(total_revenue: float, employee_count: float) -> float:
    """
    Revenue Per Employee = Total Revenue / Employee Count.

    A key productivity benchmark for operational efficiency.
    Returns 0.0 when employee count is zero.
    """
    return safe_divide(total_revenue, employee_count)


def calculate_profit_per_employee(net_profit: float, employee_count: float) -> float:
    """
    Profit Per Employee = Net Profit / Employee Count.

    Measures profitability contribution per head.
    Can be negative in loss-making companies.
    Returns 0.0 when employee count is zero.
    """
    return safe_divide(net_profit, employee_count)


def calculate_support_cost_per_customer(support_cost: float, customers: float) -> float:
    """
    Support Cost Per Customer = Support Cost / Customers.

    Tracks the average ongoing cost of servicing each customer.
    Rising cost may indicate product quality or scalability issues.
    Returns 0.0 when customers is zero.
    """
    return safe_divide(support_cost, customers)


def calculate_cost_to_serve_per_customer(total_service_cost: float, customers: float) -> float:
    """
    Cost to Serve Per Customer = Total Service Cost / Customers.

    Broader than support cost; includes all post-sales costs.
    Used for unit-economics benchmarking.
    Returns 0.0 when customers is zero.
    """
    return safe_divide(total_service_cost, customers)


def calculate_sales_efficiency(new_revenue: float, sales_and_marketing_spend: float) -> float:
    """
    Sales Efficiency = New Revenue / Sales & Marketing Spend.

    Also called the 'Magic Number' (when measured over a period).
    Returns 0.0 when spend is zero.
    A value > 1.0 means the business is generating more revenue than it spends on sales.
    """
    return safe_divide(new_revenue, sales_and_marketing_spend)


def calculate_marketing_efficiency(new_customers: float, marketing_spend: float) -> float:
    """
    Marketing Efficiency = New Customers / Marketing Spend.

    Customers acquired per dollar of marketing investment.
    Returns 0.0 when marketing_spend is zero.
    """
    return safe_divide(new_customers, marketing_spend)
