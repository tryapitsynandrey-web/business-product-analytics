"""
Tests for src/core/business_health/growth_metrics.py
"""

from __future__ import annotations

import pytest
from core.business_health.growth_metrics import (
    calculate_customer_growth_rate,
    calculate_user_growth_rate,
    calculate_activation_growth_rate,
    calculate_retention_growth_rate,
    calculate_growth_efficiency,
)


class TestCustomerGrowthRate:
    def test_positive_growth(self):
        assert calculate_customer_growth_rate(1_200.0, 1_000.0) == pytest.approx(0.20)

    def test_contraction(self):
        assert calculate_customer_growth_rate(800.0, 1_000.0) == pytest.approx(-0.20)

    def test_zero_previous_returns_zero(self):
        assert calculate_customer_growth_rate(100.0, 0.0) == pytest.approx(0.0)

    def test_no_change(self):
        assert calculate_customer_growth_rate(1_000.0, 1_000.0) == pytest.approx(0.0)


class TestUserGrowthRate:
    def test_positive_growth(self):
        assert calculate_user_growth_rate(5_500.0, 5_000.0) == pytest.approx(0.10)

    def test_zero_previous_returns_zero(self):
        assert calculate_user_growth_rate(5_500.0, 0.0) == pytest.approx(0.0)

    def test_decline(self):
        assert calculate_user_growth_rate(4_000.0, 5_000.0) == pytest.approx(-0.20)


class TestActivationGrowthRate:
    def test_improving_activation(self):
        assert calculate_activation_growth_rate(0.60, 0.50) == pytest.approx(0.20)

    def test_declining_activation(self):
        assert calculate_activation_growth_rate(0.40, 0.50) == pytest.approx(-0.20)

    def test_zero_previous_returns_zero(self):
        assert calculate_activation_growth_rate(0.50, 0.0) == pytest.approx(0.0)


class TestRetentionGrowthRate:
    def test_improving_retention(self):
        assert calculate_retention_growth_rate(0.90, 0.80) == pytest.approx(0.125)

    def test_declining_retention(self):
        assert calculate_retention_growth_rate(0.70, 0.80) == pytest.approx(-0.125)

    def test_zero_previous_returns_zero(self):
        assert calculate_retention_growth_rate(0.90, 0.0) == pytest.approx(0.0)


class TestGrowthEfficiency:
    def test_efficient_growth(self):
        assert calculate_growth_efficiency(200_000.0, 100_000.0) == pytest.approx(2.0)

    def test_zero_spend_returns_zero(self):
        assert calculate_growth_efficiency(200_000.0, 0.0) == pytest.approx(0.0)

    def test_inefficient_growth(self):
        assert calculate_growth_efficiency(50_000.0, 100_000.0) == pytest.approx(0.5)
