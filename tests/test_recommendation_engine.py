"""
Tests for src/core/recommendation_engine.py

All tests use in-memory DataFrames and hand-crafted ChurnRiskProfile objects.
"""

from __future__ import annotations

import pytest
import pandas as pd

from core.recommendation_engine import RecommendationEngine, _match
from models.enums import RiskBand
from models.risk_profile import ChurnRiskProfile


@pytest.fixture()
def engine() -> RecommendationEngine:
    return RecommendationEngine()


def _make_datasets(customers_data: list | None = None) -> dict:
    if customers_data is None:
        customers_data = [
            {"customer_id": "C1", "segment": "Enterprise", "is_active": True},
            {"customer_id": "C2", "segment": "SMB", "is_active": True},
            {"customer_id": "C3", "segment": "Mid-Market", "is_active": True},
        ]
    customers = pd.DataFrame(customers_data)
    subscriptions = pd.DataFrame(
        {
            "subscription_id": [f"S{i}" for i in range(len(customers_data))],
            "customer_id": [c["customer_id"] for c in customers_data],
            "status": ["Active"] * len(customers_data),
            "monthly_price": [1000.0] * len(customers_data),
            "plan": ["Enterprise"] * len(customers_data),
        }
    )
    return {
        "customers": customers,
        "subscriptions": subscriptions,
        "product_usage": pd.DataFrame(columns=["customer_id", "logins", "key_actions"]),
        "nps_scores": pd.DataFrame(columns=["customer_id", "score", "date"]),
        "support_tickets": pd.DataFrame(columns=["customer_id", "ticket_id"]),
        "transactions": pd.DataFrame(columns=["customer_id", "transaction_id", "amount", "status"]),
    }


def _make_profile(
    customer_id: str,
    risk_band: RiskBand,
    drivers: list | None = None,
    revenue_at_risk: float = 500.0,
) -> ChurnRiskProfile:
    return ChurnRiskProfile(
        customer_id=customer_id,
        risk_score=0.9 if risk_band == RiskBand.CRITICAL else 0.45,
        risk_band=risk_band,
        drivers=drivers or [],
        revenue_at_risk=revenue_at_risk,
        explanation="Test profile.",
    )


class TestChurnRiskRecommendations:
    def test_critical_enterprise_triggers_executive_reachout(self, engine):
        datasets = _make_datasets()
        profiles = [_make_profile("C1", RiskBand.CRITICAL, revenue_at_risk=2000.0)]
        recs = engine.generate_recommendations(datasets, profiles)

        titles = [r["recommendation_title"] for r in recs]
        assert any("Executive" in t for t in titles), (
            f"Expected Executive Reachout recommendation. Got: {titles}"
        )

    def test_high_smb_triggers_reengagement_offer(self, engine):
        datasets = _make_datasets()
        profiles = [_make_profile("C2", RiskBand.HIGH, revenue_at_risk=200.0)]
        recs = engine.generate_recommendations(datasets, profiles)

        titles = [r["recommendation_title"] for r in recs]
        assert any("SMB" in t or "Re-engagement" in t for t in titles), (
            f"Expected SMB re-engagement recommendation. Got: {titles}"
        )

    def test_no_recommendation_for_low_risk_customer(self, engine):
        datasets = _make_datasets([{"customer_id": "C1", "segment": "SMB", "is_active": True}])
        profiles = [
            ChurnRiskProfile(
                customer_id="C1",
                risk_score=0.0,
                risk_band=RiskBand.LOW,
                drivers=[],
                revenue_at_risk=0.0,
                explanation="No risk.",
            )
        ]
        recs = engine.generate_recommendations(datasets, profiles, leakages=[])
        # Low risk with no drivers should trigger no churn-risk rules
        churn_recs = [r for r in recs if r.get("rule_id") in ("REC_001", "REC_003", "REC_006")]
        assert churn_recs == []

    def test_missing_customer_profile_is_skipped(self, engine):
        datasets = _make_datasets()
        profiles = [_make_profile("MISSING", RiskBand.CRITICAL)]

        recs = engine.generate_recommendations(datasets, profiles, leakages=[])

        assert recs == []


class TestLeakageRecommendations:
    def test_failed_payment_leakage_triggers_billing_recommendation(self, engine):
        datasets = _make_datasets()
        leakages = [
            {
                "leakage_type": "Failed Payment",
                "customer_id": "C1",
                "estimated_revenue_loss": 100.0,
                "evidence": "1 failed transaction.",
                "affected_customers": 1,
                "recommended_action": "Retry payment.",
            }
        ]
        recs = engine.generate_recommendations(datasets, [], leakages=leakages)
        billing_recs = [r for r in recs if r.get("category") == "billing_recovery"]
        assert len(billing_recs) > 0

    def test_unpaid_subscription_triggers_past_due_escalation(self, engine):
        datasets = _make_datasets()
        leakages = [
            {
                "leakage_type": "Unpaid Active Subscription",
                "customer_id": "C2",
                "estimated_revenue_loss": 200.0,
                "evidence": "Past Due.",
                "affected_customers": 1,
                "recommended_action": "Escalate.",
            }
        ]
        recs = engine.generate_recommendations(datasets, [], leakages=leakages)
        assert any("Past-Due" in r["recommendation_title"] for r in recs)

    def test_no_recommendation_without_matching_trigger(self, engine):
        datasets = _make_datasets()
        leakages = [
            {
                "leakage_type": "Unknown Leakage Type",
                "customer_id": "C1",
                "estimated_revenue_loss": 0.0,
                "evidence": "N/A",
                "affected_customers": 1,
                "recommended_action": "Unknown.",
            }
        ]
        recs = engine.generate_recommendations(datasets, [], leakages=leakages)
        # No rule should match an unknown leakage type
        unknown_recs = [r for r in recs if r.get("evidence_source") == "N/A"]
        assert unknown_recs == []


class TestImpactScore:
    def test_impact_score_formula_is_correct(self, engine):
        score = engine.calculate_impact_score(
            severity_weight=2.0,
            affected_customers=1,
            estimated_revenue_impact=500.0,
            confidence_weight=0.8,
        )
        assert score == pytest.approx(2.0 * 1 * 500.0 * 0.8)

    def test_impact_score_zero_when_revenue_impact_is_zero(self, engine):
        score = engine.calculate_impact_score(
            severity_weight=3.0,
            affected_customers=5,
            estimated_revenue_impact=0.0,
            confidence_weight=0.9,
        )
        assert score == pytest.approx(0.0)


class TestConfidenceLevel:
    def test_high_confidence_label_above_085(self, engine):
        assert engine.calculate_confidence_level(0.90) == "High"

    def test_medium_confidence_label_between_060_085(self, engine):
        assert engine.calculate_confidence_level(0.70) == "Medium"

    def test_low_confidence_label_below_060(self, engine):
        assert engine.calculate_confidence_level(0.40) == "Low"

    def test_boundary_085_is_high(self, engine):
        assert engine.calculate_confidence_level(0.85) == "High"

    def test_boundary_060_is_medium(self, engine):
        assert engine.calculate_confidence_level(0.60) == "Medium"


class TestMatchRecommendationRules:
    def test_churn_risk_match_by_risk_band(self, engine):
        matched = engine.match_recommendation_rules(
            trigger_type="churn_risk",
            context={"risk_band": "Critical", "segment": "Enterprise", "driver": ""},
        )
        assert any(r["rule_id"] == "REC_001" for r in matched)

    def test_leakage_match_by_type(self, engine):
        matched = engine.match_recommendation_rules(
            trigger_type="leakage",
            context={"leakage_type": "Failed Payment"},
        )
        assert any(r["rule_id"] == "REC_002" for r in matched)

    def test_wrong_trigger_type_returns_empty(self, engine):
        matched = engine.match_recommendation_rules(
            trigger_type="churn_risk",
            context={"leakage_type": "Failed Payment"},
        )
        leakage_rules = [r for r in matched if r.get("trigger_type") == "leakage"]
        assert leakage_rules == []


def test_match_returns_false_for_unknown_operator_and_value_errors():
    assert _match("unknown", "x", "x") is False
    assert _match("greater_than", "not-a-number", 1) is False
