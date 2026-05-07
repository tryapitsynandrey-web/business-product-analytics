"""
Tests for src/core/business_health/business_health_score.py
"""

from __future__ import annotations

import pytest
from core.business_health.business_health_score import (
    BusinessHealthScoreEngine,
    AreaScore,
    CompositeScore,
    score_profitability,
    score_revenue_health,
    score_cashflow,
    score_unit_economics,
    score_growth,
    score_efficiency,
    score_risk,
    _status_from_score,
)


class TestStatusFromScore:
    def test_healthy_at_80(self):
        assert _status_from_score(80.0) == "Healthy"

    def test_healthy_above_80(self):
        assert _status_from_score(95.0) == "Healthy"

    def test_stable_at_65(self):
        assert _status_from_score(65.0) == "Stable"

    def test_watch_at_50(self):
        assert _status_from_score(50.0) == "Watch"

    def test_risk_at_30(self):
        assert _status_from_score(30.0) == "Risk"

    def test_critical_below_30(self):
        assert _status_from_score(15.0) == "Critical"

    def test_zero_is_critical(self):
        assert _status_from_score(0.0) == "Critical"


class TestScoreProfitability:
    def test_returns_area_score(self):
        result = score_profitability(0.70, 0.20, 0.10)
        assert isinstance(result, AreaScore)
        assert result.area == "profitability"

    def test_excellent_margins_produce_high_score(self):
        result = score_profitability(0.80, 0.25, 0.15)
        assert result.score >= 80.0

    def test_zero_margins_produce_low_score(self):
        result = score_profitability(0.0, 0.0, 0.0)
        assert result.score == pytest.approx(0.0)

    def test_status_consistent_with_score(self):
        result = score_profitability(0.80, 0.25, 0.15)
        assert result.status == _status_from_score(result.score)


class TestScoreRevenueHealth:
    def test_returns_area_score(self):
        result = score_revenue_health(0.20, 0.80, 0.01, 0.02)
        assert isinstance(result, AreaScore)
        assert result.area == "revenue"

    def test_excellent_inputs_high_score(self):
        result = score_revenue_health(0.30, 0.90, 0.005, 0.01)
        assert result.score >= 80.0

    def test_zero_growth_low_score(self):
        result = score_revenue_health(0.0, 0.0, 0.10, 0.10)
        assert result.score < 50.0


class TestScoreCashflow:
    def test_long_runway_high_score(self):
        result = score_cashflow(24.0, 50_000.0)
        assert result.score >= 80.0
        assert result.area == "cashflow"

    def test_zero_runway_critical(self):
        result = score_cashflow(0.0, -10_000.0)
        assert result.status == "Critical"

    def test_score_is_clamped_0_to_100(self):
        result = score_cashflow(100.0, 999_999.0)
        assert 0.0 <= result.score <= 100.0


class TestScoreUnitEconomics:
    def test_healthy_ltv_cac_ratio(self):
        result = score_unit_economics(5.0, 6.0)
        assert result.score >= 80.0
        assert result.area == "unit_economics"

    def test_poor_ltv_cac_low_score(self):
        result = score_unit_economics(0.5, 36.0)
        assert result.score < 50.0

    def test_zero_inputs_low_score(self):
        # LTV:CAC of 0 → 0 score, but cac_payback of 0 months scores 100 (inverse — 0 is perfect)
        # Weighted blend: 0 * 0.6 + 100 * 0.4 = 40. Score reflects this mixed signal.
        result = score_unit_economics(0.0, 0.0)
        assert result.score < 50.0


class TestScoreGrowth:
    def test_strong_growth_high_score(self):
        result = score_growth(0.20, 0.40, 2.0)
        assert result.score >= 80.0
        assert result.area == "growth"

    def test_zero_growth_zero_score(self):
        result = score_growth(0.0, 0.0, 0.0)
        assert result.score == pytest.approx(0.0)


class TestScoreEfficiency:
    def test_high_efficiency_high_score(self):
        result = score_efficiency(200_000.0, 2.0)
        assert result.score >= 80.0
        assert result.area == "efficiency"

    def test_zero_efficiency_zero_score(self):
        result = score_efficiency(0.0, 0.0)
        assert result.score == pytest.approx(0.0)


class TestScoreRisk:
    def test_low_risk_high_score(self):
        # Targets: concentration <= 10%, churn exposure <= 5%, cashflow risk <= 20
        # 5% vs 10% target → 50/100; 2% vs 5% target → 60/100; cf_score inverted 90/100
        # Weighted: 50*0.35 + 60*0.35 + 90*0.30 = 17.5 + 21 + 27 = 65.5 — Stable range
        result = score_risk(0.05, 0.02, 10.0)
        assert result.score >= 60.0
        assert result.status in {"Stable", "Healthy"}

    def test_high_risk_low_score(self):
        result = score_risk(0.80, 0.50, 90.0)
        assert result.score < 20.0


class TestBusinessHealthScoreEngine:
    def setup_method(self):
        self.engine = BusinessHealthScoreEngine()

    def test_returns_composite_score(self):
        result = self.engine.calculate()
        assert isinstance(result, CompositeScore)

    def test_composite_score_bounded_0_to_100(self):
        result = self.engine.calculate()
        assert 0.0 <= result.composite_score <= 100.0

    def test_seven_area_scores_returned(self):
        result = self.engine.calculate()
        assert len(result.area_scores) == 7

    def test_area_names_present(self):
        result = self.engine.calculate()
        areas = {a.area for a in result.area_scores}
        expected = {"profitability", "revenue", "cashflow", "unit_economics", "growth", "efficiency", "risk"}
        assert areas == expected

    def test_status_is_valid_label(self):
        result = self.engine.calculate()
        valid = {"Healthy", "Stable", "Watch", "Risk", "Critical"}
        assert result.status in valid
        for area in result.area_scores:
            assert area.status in valid

    def test_excellent_inputs_produce_healthy_status(self):
        result = self.engine.calculate(
            profitability_inputs={"gross_margin": 0.80, "operating_margin": 0.30, "net_margin": 0.20},
            revenue_inputs={"revenue_growth_rate": 0.30, "recurring_revenue_ratio": 0.90, "refund_rate": 0.005, "failed_payment_rate": 0.01},
            cashflow_inputs={"runway_months": 24.0, "free_cash_flow": 100_000.0},
            unit_economics_inputs={"ltv_to_cac": 5.0, "cac_payback_months": 6.0},
            growth_inputs={"customer_growth_rate": 0.20, "revenue_growth_rate": 0.30, "growth_efficiency": 2.0},
            efficiency_inputs={"revenue_per_employee": 200_000.0, "sales_efficiency": 2.0},
            risk_inputs={"customer_concentration": 0.05, "churn_exposure": 0.02, "cashflow_risk_score": 5.0},
        )
        assert result.status in {"Healthy", "Stable"}
        assert result.composite_score >= 70.0

    def test_empty_inputs_produce_low_score(self):
        result = self.engine.calculate()
        assert result.composite_score < 50.0

    def test_deterministic_for_same_inputs(self):
        inputs = dict(
            profitability_inputs={"gross_margin": 0.65, "operating_margin": 0.15, "net_margin": 0.08},
        )
        r1 = self.engine.calculate(**inputs)
        r2 = self.engine.calculate(**inputs)
        assert r1.composite_score == r2.composite_score

    def test_explanation_references_weakest_area(self):
        result = self.engine.calculate()
        assert "Weakest area" in result.explanation
