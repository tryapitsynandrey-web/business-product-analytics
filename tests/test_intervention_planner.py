"""
Tests for src/core/intervention_planner.py
"""

from __future__ import annotations

import pytest

from core.intervention_planner import InterventionPlanner


@pytest.fixture()
def planner() -> InterventionPlanner:
    return InterventionPlanner()


def _make_recommendation(
    title: str = "Executive Outreach",
    category: str = "retention",
    segment: str = "Enterprise",
    revenue_impact: float = 2000.0,
    confidence_level: str = "High",
    effort_level: str | None = None,
    suggested_owner: str = "Account Executive",
    reason: str = "Schedule executive review.",
) -> dict:
    rec = {
        "recommendation_title": title,
        "category": category,
        "segment": segment,
        "estimated_revenue_impact": revenue_impact,
        "confidence_level": confidence_level,
        "suggested_owner": suggested_owner,
        "reason": reason,
        "affected_customers": 1,
    }
    if effort_level is not None:
        rec["effort_level"] = effort_level
    return rec


# ---------------------------------------------------------------------------
# Record builder
# ---------------------------------------------------------------------------

class TestBuildInterventionRecord:
    def test_record_has_all_required_fields(self, planner):
        rec = _make_recommendation()
        iv = planner.build_intervention_record(rec)

        required = {
            "intervention_id", "recommendation_title", "category",
            "target_segment", "affected_customers", "estimated_revenue_impact",
            "expected_action", "suggested_owner", "confidence_level",
            "effort_level", "priority_score", "priority_band",
        }
        assert required.issubset(iv.keys())

    def test_intervention_id_starts_with_iv_prefix(self, planner):
        iv = planner.build_intervention_record(_make_recommendation())
        assert iv["intervention_id"].startswith("IV-")

    def test_revenue_impact_propagated(self, planner):
        rec = _make_recommendation(revenue_impact=5000.0)
        iv = planner.build_intervention_record(rec)
        assert iv["estimated_revenue_impact"] == pytest.approx(5000.0)

    def test_owner_propagated(self, planner):
        rec = _make_recommendation(suggested_owner="Billing Automation")
        iv = planner.build_intervention_record(rec)
        assert iv["suggested_owner"] == "Billing Automation"

    def test_priority_score_is_positive_for_non_zero_impact(self, planner):
        rec = _make_recommendation(revenue_impact=1000.0, confidence_level="High")
        iv = planner.build_intervention_record(rec)
        assert iv["priority_score"] > 0

    def test_priority_band_is_assigned(self, planner):
        rec = _make_recommendation(revenue_impact=500.0)
        iv = planner.build_intervention_record(rec)
        assert iv["priority_band"] in ("Critical", "High", "Medium", "Low")


# ---------------------------------------------------------------------------
# Effort estimation
# ---------------------------------------------------------------------------

class TestEstimateEffortLevel:
    def test_explicit_effort_level_used(self, planner):
        rec = _make_recommendation(effort_level="Low")
        assert planner.estimate_effort_level(rec) == "Low"

    def test_retention_category_defaults_to_high(self, planner):
        rec = {
            "category": "retention",
            "suggested_owner": "Account Executive",
        }
        assert planner.estimate_effort_level(rec) == "High"

    def test_billing_recovery_category_defaults_to_low(self, planner):
        rec = _make_recommendation(category="billing_recovery")
        assert planner.estimate_effort_level(rec) == "Low"

    def test_automation_owner_infers_low_effort(self, planner):
        rec = {
            "category": "unknown_category",
            "suggested_owner": "Billing Automation",
        }
        assert planner.estimate_effort_level(rec) == "Low"

    def test_missing_category_and_owner_defaults_to_medium(self, planner):
        rec = {}
        assert planner.estimate_effort_level(rec) == "Medium"


# ---------------------------------------------------------------------------
# Revenue protected
# ---------------------------------------------------------------------------

class TestEstimateRevenueProtected:
    def test_revenue_extracted_from_recommendation(self, planner):
        rec = {"estimated_revenue_impact": 3000.0}
        assert planner.estimate_revenue_protected(rec) == pytest.approx(3000.0)

    def test_missing_field_returns_zero(self, planner):
        assert planner.estimate_revenue_protected({}) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Intervention plan creation
# ---------------------------------------------------------------------------

class TestCreateInterventionPlan:
    def test_one_intervention_per_recommendation(self, planner):
        recs = [_make_recommendation(), _make_recommendation(title="Second")]
        plan = planner.create_intervention_plan(recs)
        assert len(plan) == 2

    def test_empty_recommendations_produces_empty_plan(self, planner):
        assert planner.create_intervention_plan([]) == []

    def test_high_revenue_impact_gets_high_priority(self, planner):
        rec = _make_recommendation(revenue_impact=50000.0, confidence_level="High")
        plan = planner.create_intervention_plan([rec])
        assert plan[0]["priority_band"] in ("Critical", "High")

    def test_zero_revenue_impact_gets_low_priority(self, planner):
        rec = _make_recommendation(revenue_impact=0.0, confidence_level="Low")
        plan = planner.create_intervention_plan([rec])
        assert plan[0]["priority_band"] == "Low"
