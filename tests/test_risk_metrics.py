from __future__ import annotations

import pytest

from core.business_health.risk_metrics import (
    calculate_cashflow_risk_score,
    calculate_churn_exposure,
    calculate_customer_concentration_risk,
    calculate_margin_compression,
    calculate_revenue_dependency_score,
)


class TestCustomerConcentrationRisk:
    def test_calculates_largest_customer_share(self):
        assert calculate_customer_concentration_risk(200.0, 1_000.0) == pytest.approx(0.2)

    def test_zero_total_revenue_returns_zero(self):
        assert calculate_customer_concentration_risk(200.0, 0.0) == pytest.approx(0.0)


class TestMarginCompression:
    def test_negative_value_indicates_compression(self):
        assert calculate_margin_compression(0.18, 0.25) == pytest.approx(-0.07)

    def test_positive_value_indicates_expansion(self):
        assert calculate_margin_compression(0.30, 0.25) == pytest.approx(0.05)


class TestCashflowRiskScore:
    def test_boundary_values_follow_risk_bands(self):
        assert calculate_cashflow_risk_score(18.0, 10_000.0) == pytest.approx(0.0)
        assert calculate_cashflow_risk_score(12.0, 10_000.0) == pytest.approx(25.0)
        assert calculate_cashflow_risk_score(6.0, 10_000.0) == pytest.approx(75.0)
        assert calculate_cashflow_risk_score(0.0, 10_000.0) == pytest.approx(100.0)

    def test_mid_critical_band_scales_linearly(self):
        assert calculate_cashflow_risk_score(3.0, 10_000.0) == pytest.approx(87.5)

    def test_burn_rate_argument_does_not_change_current_runway_driven_score(self):
        assert calculate_cashflow_risk_score(9.0, 1_000.0) == pytest.approx(
            calculate_cashflow_risk_score(9.0, 100_000.0)
        )


class TestRevenueDependencyScore:
    def test_calculates_top_segment_share(self):
        assert calculate_revenue_dependency_score(700.0, 1_000.0) == pytest.approx(0.7)

    def test_zero_total_revenue_returns_zero(self):
        assert calculate_revenue_dependency_score(700.0, 0.0) == pytest.approx(0.0)


class TestChurnExposure:
    def test_calculates_revenue_at_risk_share(self):
        assert calculate_churn_exposure(150.0, 1_000.0) == pytest.approx(0.15)

    def test_zero_total_revenue_returns_zero(self):
        assert calculate_churn_exposure(150.0, 0.0) == pytest.approx(0.0)
