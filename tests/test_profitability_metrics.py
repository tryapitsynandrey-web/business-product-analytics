"""
Tests for src/core/business_health/profitability.py
"""

from __future__ import annotations

import pytest
from core.business_health.profitability import (
    calculate_gross_profit,
    calculate_gross_margin,
    calculate_operating_profit,
    calculate_operating_margin,
    calculate_net_profit,
    calculate_net_margin,
    calculate_ebitda,
    calculate_ebitda_margin,
    calculate_roi,
    calculate_roa,
    calculate_roe,
    calculate_roic,
    calculate_payback_period,
)


class TestGrossProfit:
    def test_normal_calculation(self):
        assert calculate_gross_profit(1_000.0, 400.0) == pytest.approx(600.0)

    def test_zero_cogs(self):
        assert calculate_gross_profit(1_000.0, 0.0) == pytest.approx(1_000.0)

    def test_negative_gross_profit(self):
        # COGS exceeds revenue
        assert calculate_gross_profit(300.0, 500.0) == pytest.approx(-200.0)

    def test_zero_revenue(self):
        assert calculate_gross_profit(0.0, 0.0) == pytest.approx(0.0)


class TestGrossMargin:
    def test_normal_calculation(self):
        assert calculate_gross_margin(1_000.0, 300.0) == pytest.approx(0.70)

    def test_zero_revenue_returns_zero(self):
        assert calculate_gross_margin(0.0, 0.0) == pytest.approx(0.0)

    def test_full_margin(self):
        # No COGS → 100% margin
        assert calculate_gross_margin(1_000.0, 0.0) == pytest.approx(1.0)

    def test_negative_margin(self):
        assert calculate_gross_margin(100.0, 200.0) == pytest.approx(-1.0)


class TestOperatingProfit:
    def test_normal_calculation(self):
        # 1000 revenue - 300 COGS - 200 OpEx = 500
        assert calculate_operating_profit(1_000.0, 200.0, 300.0) == pytest.approx(500.0)

    def test_zero_expenses(self):
        assert calculate_operating_profit(1_000.0, 0.0, 0.0) == pytest.approx(1_000.0)

    def test_negative_operating_profit(self):
        assert calculate_operating_profit(100.0, 200.0, 100.0) == pytest.approx(-200.0)


class TestOperatingMargin:
    def test_normal_calculation(self):
        assert calculate_operating_margin(1_000.0, 200.0) == pytest.approx(0.20)

    def test_zero_revenue_returns_zero(self):
        assert calculate_operating_margin(0.0, 100.0) == pytest.approx(0.0)

    def test_negative_margin(self):
        assert calculate_operating_margin(1_000.0, -100.0) == pytest.approx(-0.10)


class TestNetProfit:
    def test_normal_calculation(self):
        assert calculate_net_profit(1_000.0, 800.0) == pytest.approx(200.0)

    def test_loss_scenario(self):
        assert calculate_net_profit(500.0, 700.0) == pytest.approx(-200.0)

    def test_zero_expenses(self):
        assert calculate_net_profit(1_000.0, 0.0) == pytest.approx(1_000.0)


class TestNetMargin:
    def test_normal_calculation(self):
        assert calculate_net_margin(1_000.0, 200.0) == pytest.approx(0.20)

    def test_zero_revenue_returns_zero(self):
        assert calculate_net_margin(0.0, 0.0) == pytest.approx(0.0)

    def test_negative_margin(self):
        assert calculate_net_margin(1_000.0, -100.0) == pytest.approx(-0.10)


class TestEbitda:
    def test_normal_calculation(self):
        # 100 + 20 + 30 + 15 + 5 = 170
        result = calculate_ebitda(100.0, 20.0, 30.0, 15.0, 5.0)
        assert result == pytest.approx(170.0)

    def test_zero_add_backs(self):
        assert calculate_ebitda(100.0, 0.0, 0.0, 0.0, 0.0) == pytest.approx(100.0)

    def test_all_zero(self):
        assert calculate_ebitda(0.0, 0.0, 0.0, 0.0, 0.0) == pytest.approx(0.0)


class TestEbitdaMargin:
    def test_normal_calculation(self):
        assert calculate_ebitda_margin(1_000.0, 250.0) == pytest.approx(0.25)

    def test_zero_revenue_returns_zero(self):
        assert calculate_ebitda_margin(0.0, 100.0) == pytest.approx(0.0)


class TestROI:
    def test_profitable_investment(self):
        # Gain 1500, Cost 1000 → (1500 - 1000) / 1000 = 0.5
        assert calculate_roi(1_500.0, 1_000.0) == pytest.approx(0.5)

    def test_breakeven(self):
        assert calculate_roi(1_000.0, 1_000.0) == pytest.approx(0.0)

    def test_loss_scenario(self):
        assert calculate_roi(500.0, 1_000.0) == pytest.approx(-0.5)

    def test_zero_cost_returns_zero(self):
        assert calculate_roi(500.0, 0.0) == pytest.approx(0.0)


class TestROA:
    def test_normal_calculation(self):
        assert calculate_roa(100_000.0, 1_000_000.0) == pytest.approx(0.10)

    def test_zero_assets_returns_zero(self):
        assert calculate_roa(100_000.0, 0.0) == pytest.approx(0.0)


class TestROE:
    def test_normal_calculation(self):
        assert calculate_roe(50_000.0, 500_000.0) == pytest.approx(0.10)

    def test_zero_equity_returns_zero(self):
        assert calculate_roe(50_000.0, 0.0) == pytest.approx(0.0)


class TestROIC:
    def test_normal_calculation(self):
        assert calculate_roic(80_000.0, 800_000.0) == pytest.approx(0.10)

    def test_zero_capital_returns_zero(self):
        assert calculate_roic(80_000.0, 0.0) == pytest.approx(0.0)


class TestPaybackPeriod:
    def test_normal_calculation(self):
        # 1,000,000 / 250,000 = 4 years
        assert calculate_payback_period(1_000_000.0, 250_000.0) == pytest.approx(4.0)

    def test_zero_inflow_returns_zero(self):
        assert calculate_payback_period(1_000_000.0, 0.0) == pytest.approx(0.0)

    def test_single_year_payback(self):
        assert calculate_payback_period(100_000.0, 100_000.0) == pytest.approx(1.0)
