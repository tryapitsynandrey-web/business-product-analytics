"""
Tests for src/core/business_health/revenue_metrics.py
"""

from __future__ import annotations

import pytest
from core.business_health.revenue_metrics import (
    calculate_arr,
    calculate_revenue_growth_rate,
    calculate_revenue_concentration,
    calculate_recurring_revenue_ratio,
    calculate_expansion_revenue_ratio,
    calculate_refund_rate,
    calculate_failed_payment_rate,
)


class TestCalculateArr:
    def test_normal_calculation(self):
        assert calculate_arr(10_000.0) == pytest.approx(120_000.0)

    def test_zero_mrr(self):
        assert calculate_arr(0.0) == pytest.approx(0.0)

    def test_large_mrr(self):
        assert calculate_arr(500_000.0) == pytest.approx(6_000_000.0)


class TestRevenueGrowthRate:
    def test_positive_growth(self):
        # 1200 vs 1000 → 20% growth
        assert calculate_revenue_growth_rate(1_200.0, 1_000.0) == pytest.approx(0.20)

    def test_contraction(self):
        assert calculate_revenue_growth_rate(800.0, 1_000.0) == pytest.approx(-0.20)

    def test_zero_previous_returns_zero(self):
        assert calculate_revenue_growth_rate(1_000.0, 0.0) == pytest.approx(0.0)

    def test_flat_growth(self):
        assert calculate_revenue_growth_rate(1_000.0, 1_000.0) == pytest.approx(0.0)


class TestRevenueConcentration:
    def test_high_concentration(self):
        assert calculate_revenue_concentration(100_000.0, 50_000.0) == pytest.approx(0.50)

    def test_low_concentration(self):
        assert calculate_revenue_concentration(100_000.0, 5_000.0) == pytest.approx(0.05)

    def test_zero_total_returns_zero(self):
        assert calculate_revenue_concentration(0.0, 0.0) == pytest.approx(0.0)


class TestRecurringRevenueRatio:
    def test_fully_recurring(self):
        assert calculate_recurring_revenue_ratio(1_000.0, 1_000.0) == pytest.approx(1.0)

    def test_half_recurring(self):
        assert calculate_recurring_revenue_ratio(500.0, 1_000.0) == pytest.approx(0.50)

    def test_zero_total_returns_zero(self):
        assert calculate_recurring_revenue_ratio(500.0, 0.0) == pytest.approx(0.0)


class TestExpansionRevenueRatio:
    def test_normal(self):
        assert calculate_expansion_revenue_ratio(200.0, 1_000.0) == pytest.approx(0.20)

    def test_zero_expansion(self):
        assert calculate_expansion_revenue_ratio(0.0, 1_000.0) == pytest.approx(0.0)

    def test_zero_total_returns_zero(self):
        assert calculate_expansion_revenue_ratio(200.0, 0.0) == pytest.approx(0.0)


class TestRefundRate:
    def test_normal(self):
        assert calculate_refund_rate(50.0, 1_000.0) == pytest.approx(0.05)

    def test_zero_refunds(self):
        assert calculate_refund_rate(0.0, 1_000.0) == pytest.approx(0.0)

    def test_zero_total_returns_zero(self):
        assert calculate_refund_rate(50.0, 0.0) == pytest.approx(0.0)


class TestFailedPaymentRate:
    def test_normal(self):
        assert calculate_failed_payment_rate(30.0, 1_000.0) == pytest.approx(0.03)

    def test_zero_failures(self):
        assert calculate_failed_payment_rate(0.0, 1_000.0) == pytest.approx(0.0)

    def test_zero_total_returns_zero(self):
        assert calculate_failed_payment_rate(30.0, 0.0) == pytest.approx(0.0)
