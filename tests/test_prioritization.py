"""
Tests for src/core/prioritization.py
"""

from __future__ import annotations

import pytest

import core.prioritization as prioritization
from core.prioritization import (
    assign_priority_band,
    calculate_priority_score,
    rank_interventions,
    rank_recommendations,
)


# ---------------------------------------------------------------------------
# Priority score formula
# ---------------------------------------------------------------------------

class TestCalculatePriorityScore:
    def test_basic_formula(self):
        score = calculate_priority_score(
            impact_score=1000.0,
            confidence_weight=0.8,
            effort_weight="Low",
        )
        # Low effort = 1.0 divisor: 1000 * 0.8 / 1.0 = 800.0
        assert score == pytest.approx(800.0)

    def test_high_effort_reduces_score(self):
        low = calculate_priority_score(10000.0, 0.9, "Low")
        high = calculate_priority_score(10000.0, 0.9, "High")
        assert high < low

    def test_medium_effort_is_between_low_and_high(self):
        low = calculate_priority_score(5000.0, 0.8, "Low")
        med = calculate_priority_score(5000.0, 0.8, "Medium")
        high = calculate_priority_score(5000.0, 0.8, "High")
        assert high < med < low

    def test_zero_impact_produces_zero_score(self):
        score = calculate_priority_score(0.0, 0.9, "Low")
        assert score == pytest.approx(0.0)

    def test_zero_effort_weight_defaults_to_1(self):
        # Passing 0 as effort_weight should not raise; defaults to 1.0
        score = calculate_priority_score(100.0, 0.5, 0)
        assert score == pytest.approx(50.0)

    def test_numeric_effort_weight_used_directly(self):
        score = calculate_priority_score(100.0, 1.0, 2.0)
        assert score == pytest.approx(50.0)

    def test_non_positive_parsed_effort_defaults_to_one(self, monkeypatch):
        monkeypatch.setattr(prioritization, "_parse_effort_weight", lambda _: 0.0)

        score = calculate_priority_score(100.0, 0.5, "Low")

        assert score == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Priority band assignment
# ---------------------------------------------------------------------------

class TestAssignPriorityBand:
    def test_above_critical_threshold_is_critical(self):
        assert assign_priority_band(10000.0) == "Critical"

    def test_above_high_threshold_is_high(self):
        assert assign_priority_band(2000.0) == "High"

    def test_above_medium_threshold_is_medium(self):
        assert assign_priority_band(500.0) == "Medium"

    def test_below_medium_threshold_is_low(self):
        assert assign_priority_band(50.0) == "Low"

    def test_zero_is_low(self):
        assert assign_priority_band(0.0) == "Low"

    def test_exact_critical_boundary(self):
        assert assign_priority_band(5000.0) == "Critical"

    def test_exact_high_boundary(self):
        assert assign_priority_band(1000.0) == "High"


# ---------------------------------------------------------------------------
# Ranking recommendations
# ---------------------------------------------------------------------------

class TestRankRecommendations:
    def _make_recs(self) -> list:
        return [
            {
                "recommendation_title": "Low priority",
                "impact_score": 100.0,
                "confidence_weight": 0.5,
                "effort_level": "High",
            },
            {
                "recommendation_title": "High priority",
                "impact_score": 5000.0,
                "confidence_weight": 0.9,
                "effort_level": "Low",
            },
            {
                "recommendation_title": "Medium priority",
                "impact_score": 1000.0,
                "confidence_weight": 0.7,
                "effort_level": "Medium",
            },
        ]

    def test_highest_score_first(self):
        ranked = rank_recommendations(self._make_recs())
        assert ranked[0]["recommendation_title"] == "High priority"

    def test_all_records_have_priority_score(self):
        ranked = rank_recommendations(self._make_recs())
        for r in ranked:
            assert "priority_score" in r
            assert isinstance(r["priority_score"], float)

    def test_all_records_have_priority_band(self):
        ranked = rank_recommendations(self._make_recs())
        for r in ranked:
            assert r["priority_band"] in ("Critical", "High", "Medium", "Low")

    def test_empty_list_returns_empty(self):
        assert rank_recommendations([]) == []

    def test_descending_order(self):
        ranked = rank_recommendations(self._make_recs())
        scores = [r["priority_score"] for r in ranked]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Ranking interventions
# ---------------------------------------------------------------------------

class TestRankInterventions:
    def _make_interventions(self) -> list:
        return [
            {
                "intervention_id": "IV-001",
                "priority_score": 50.0,
                "effort_level": "Low",
                "confidence_level": "High",
            },
            {
                "intervention_id": "IV-002",
                "priority_score": 8000.0,
                "effort_level": "Low",
                "confidence_level": "High",
            },
        ]

    def test_highest_score_first(self):
        ranked = rank_interventions(self._make_interventions())
        assert ranked[0]["intervention_id"] == "IV-002"

    def test_priority_band_assigned(self):
        ranked = rank_interventions(self._make_interventions())
        assert ranked[0]["priority_band"] == "Critical"
        assert ranked[1]["priority_band"] == "Low"

    def test_empty_list_returns_empty(self):
        assert rank_interventions([]) == []

    def test_missing_priority_score_is_computed_from_intervention_fields(self):
        ranked = rank_interventions(
            [
                {
                    "intervention_id": "IV-003",
                    "estimated_revenue_impact": 3000.0,
                    "confidence_level": "High",
                    "effort_level": "Medium",
                }
            ]
        )

        assert ranked[0]["priority_score"] == pytest.approx(1275.0)
        assert ranked[0]["priority_band"] == "High"
