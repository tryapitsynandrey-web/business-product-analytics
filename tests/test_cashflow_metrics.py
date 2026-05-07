"""
Tests for src/core/business_health/cashflow.py
"""

from __future__ import annotations

import pytest
from core.business_health.cashflow import (
    calculate_operating_cash_flow,
    calculate_free_cash_flow,
    calculate_burn_rate,
    calculate_runway,
    calculate_cash_conversion_cycle,
)


class TestOperatingCashFlow:
    def test_normal_calculation(self):
        # 100 + 30 - 20 = 110
        assert calculate_operating_cash_flow(100.0, 30.0, 20.0) == pytest.approx(110.0)

    def test_zero_adjustments(self):
        assert calculate_operating_cash_flow(200.0, 0.0, 0.0) == pytest.approx(200.0)

    def test_working_capital_increase_reduces_cash(self):
        # Higher WC change means more cash consumed
        assert calculate_operating_cash_flow(100.0, 10.0, 50.0) == pytest.approx(60.0)

    def test_negative_net_income(self):
        assert calculate_operating_cash_flow(-50.0, 20.0, 10.0) == pytest.approx(-40.0)


class TestFreeCashFlow:
    def test_normal_positive_fcf(self):
        assert calculate_free_cash_flow(200.0, 50.0) == pytest.approx(150.0)

    def test_negative_fcf(self):
        # High capex relative to operating cash flow
        assert calculate_free_cash_flow(100.0, 200.0) == pytest.approx(-100.0)

    def test_zero_capex(self):
        assert calculate_free_cash_flow(100.0, 0.0) == pytest.approx(100.0)


class TestBurnRate:
    def test_positive_burn(self):
        # Spending more than earning
        assert calculate_burn_rate(100_000.0, 60_000.0) == pytest.approx(40_000.0)

    def test_cash_flow_positive(self):
        # Inflow > outflow → negative burn
        assert calculate_burn_rate(60_000.0, 100_000.0) == pytest.approx(-40_000.0)

    def test_break_even(self):
        assert calculate_burn_rate(50_000.0, 50_000.0) == pytest.approx(0.0)


class TestRunway:
    def test_normal_calculation(self):
        # 600_000 / 50_000 = 12 months
        assert calculate_runway(600_000.0, 50_000.0) == pytest.approx(12.0)

    def test_zero_burn_returns_zero(self):
        # Positive or zero burn → runway undefined
        assert calculate_runway(600_000.0, 0.0) == pytest.approx(0.0)

    def test_negative_burn_returns_zero(self):
        # Company is cash-flow positive — runway concept does not apply
        assert calculate_runway(600_000.0, -10_000.0) == pytest.approx(0.0)

    def test_large_balance(self):
        assert calculate_runway(1_800_000.0, 100_000.0) == pytest.approx(18.0)


class TestCashConversionCycle:
    def test_normal_positive_ccc(self):
        # 30 + 45 - 30 = 45 days
        assert calculate_cash_conversion_cycle(30.0, 45.0, 30.0) == pytest.approx(45.0)

    def test_negative_ccc(self):
        # Long payables relative to inventory + receivables
        assert calculate_cash_conversion_cycle(10.0, 10.0, 60.0) == pytest.approx(-40.0)

    def test_zero_ccc(self):
        assert calculate_cash_conversion_cycle(20.0, 20.0, 40.0) == pytest.approx(0.0)
