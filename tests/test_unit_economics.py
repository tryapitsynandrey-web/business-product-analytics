"""
Tests for src/core/business_health/unit_economics.py
"""

from __future__ import annotations

import pytest
from core.business_health.unit_economics import (
    calculate_ltv,
    calculate_cac,
    calculate_ltv_to_cac_ratio,
    calculate_cac_payback_period,
    calculate_customer_profitability,
)


class TestCalculateLtv:
    def test_normal_calculation(self):
        # (200 × 0.70) / 0.05 = 2800
        assert calculate_ltv(200.0, 0.70, 0.05) == pytest.approx(2_800.0)

    def test_zero_churn_returns_zero(self):
        # Infinite LTV not representable; return 0
        assert calculate_ltv(200.0, 0.70, 0.0) == pytest.approx(0.0)

    def test_zero_arpu(self):
        assert calculate_ltv(0.0, 0.70, 0.05) == pytest.approx(0.0)

    def test_zero_gross_margin(self):
        assert calculate_ltv(200.0, 0.0, 0.05) == pytest.approx(0.0)


class TestCalculateCac:
    def test_normal_calculation(self):
        # (50_000 + 30_000) / 100 = 800
        assert calculate_cac(50_000.0, 30_000.0, 100.0) == pytest.approx(800.0)

    def test_zero_new_customers_returns_zero(self):
        assert calculate_cac(50_000.0, 30_000.0, 0.0) == pytest.approx(0.0)

    def test_no_sales_spend(self):
        assert calculate_cac(40_000.0, 0.0, 80.0) == pytest.approx(500.0)


class TestCalculateLtvToCacRatio:
    def test_healthy_ratio(self):
        # 2800 / 800 = 3.5
        assert calculate_ltv_to_cac_ratio(2_800.0, 800.0) == pytest.approx(3.5)

    def test_zero_cac_returns_zero(self):
        assert calculate_ltv_to_cac_ratio(2_800.0, 0.0) == pytest.approx(0.0)

    def test_equal_ltv_and_cac(self):
        assert calculate_ltv_to_cac_ratio(1_000.0, 1_000.0) == pytest.approx(1.0)


class TestCalculateCacPaybackPeriod:
    def test_normal_calculation(self):
        # 800 / (200 × 0.70) = 800 / 140 ≈ 5.71 months
        result = calculate_cac_payback_period(800.0, 200.0, 0.70)
        assert result == pytest.approx(800 / 140)

    def test_zero_arpu_returns_zero(self):
        assert calculate_cac_payback_period(800.0, 0.0, 0.70) == pytest.approx(0.0)

    def test_zero_gross_margin_returns_zero(self):
        assert calculate_cac_payback_period(800.0, 200.0, 0.0) == pytest.approx(0.0)


class TestCalculateCustomerProfitability:
    def test_profitable_customer(self):
        assert calculate_customer_profitability(500.0, 200.0) == pytest.approx(300.0)

    def test_unprofitable_customer(self):
        assert calculate_customer_profitability(200.0, 500.0) == pytest.approx(-300.0)

    def test_break_even(self):
        assert calculate_customer_profitability(300.0, 300.0) == pytest.approx(0.0)
