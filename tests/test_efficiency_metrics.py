"""
Tests for src/core/business_health/efficiency_metrics.py
"""

from __future__ import annotations

import pytest
from core.business_health.efficiency_metrics import (
    calculate_revenue_per_employee,
    calculate_profit_per_employee,
    calculate_support_cost_per_customer,
    calculate_cost_to_serve_per_customer,
    calculate_sales_efficiency,
    calculate_marketing_efficiency,
)


class TestRevenuePerEmployee:
    def test_normal_calculation(self):
        assert calculate_revenue_per_employee(1_500_000.0, 10.0) == pytest.approx(150_000.0)

    def test_zero_employees_returns_zero(self):
        assert calculate_revenue_per_employee(1_500_000.0, 0.0) == pytest.approx(0.0)


class TestProfitPerEmployee:
    def test_profitable(self):
        assert calculate_profit_per_employee(500_000.0, 10.0) == pytest.approx(50_000.0)

    def test_loss_per_employee(self):
        assert calculate_profit_per_employee(-200_000.0, 10.0) == pytest.approx(-20_000.0)

    def test_zero_employees_returns_zero(self):
        assert calculate_profit_per_employee(500_000.0, 0.0) == pytest.approx(0.0)


class TestSupportCostPerCustomer:
    def test_normal(self):
        assert calculate_support_cost_per_customer(50_000.0, 500.0) == pytest.approx(100.0)

    def test_zero_customers_returns_zero(self):
        assert calculate_support_cost_per_customer(50_000.0, 0.0) == pytest.approx(0.0)


class TestCostToServePerCustomer:
    def test_normal(self):
        assert calculate_cost_to_serve_per_customer(200_000.0, 400.0) == pytest.approx(500.0)

    def test_zero_customers_returns_zero(self):
        assert calculate_cost_to_serve_per_customer(200_000.0, 0.0) == pytest.approx(0.0)


class TestSalesEfficiency:
    def test_greater_than_one(self):
        assert calculate_sales_efficiency(200_000.0, 100_000.0) == pytest.approx(2.0)

    def test_less_than_one(self):
        assert calculate_sales_efficiency(50_000.0, 100_000.0) == pytest.approx(0.5)

    def test_zero_spend_returns_zero(self):
        assert calculate_sales_efficiency(200_000.0, 0.0) == pytest.approx(0.0)


class TestMarketingEfficiency:
    def test_normal(self):
        # 50 customers / $10,000 = 0.005 customers per dollar
        assert calculate_marketing_efficiency(50.0, 10_000.0) == pytest.approx(0.005)

    def test_zero_spend_returns_zero(self):
        assert calculate_marketing_efficiency(50.0, 0.0) == pytest.approx(0.0)
