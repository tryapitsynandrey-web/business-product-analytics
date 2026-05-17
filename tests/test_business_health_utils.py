from __future__ import annotations

import pytest

from core.business_health._utils import clamp_score, percentage_change, safe_divide


class TestSafeDivide:
    def test_divides_normal_values(self):
        assert safe_divide(10.0, 4.0) == pytest.approx(2.5)

    def test_zero_denominator_returns_zero(self):
        assert safe_divide(10.0, 0.0) == pytest.approx(0.0)


class TestPercentageChange:
    def test_positive_percentage_change(self):
        assert percentage_change(120.0, 100.0) == pytest.approx(0.2)

    def test_negative_percentage_change(self):
        assert percentage_change(75.0, 100.0) == pytest.approx(-0.25)

    def test_zero_previous_returns_zero(self):
        assert percentage_change(120.0, 0.0) == pytest.approx(0.0)


class TestClampScore:
    def test_score_inside_bounds_is_unchanged(self):
        assert clamp_score(42.5) == pytest.approx(42.5)

    def test_score_below_zero_clamps_to_zero(self):
        assert clamp_score(-5.0) == pytest.approx(0.0)

    def test_score_above_hundred_clamps_to_hundred(self):
        assert clamp_score(105.0) == pytest.approx(100.0)
