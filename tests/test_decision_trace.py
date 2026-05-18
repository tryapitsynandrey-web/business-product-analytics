"""
Tests for src/core/decision_trace.py
"""

from __future__ import annotations

import pytest

from core.decision_trace import DecisionTrace, DecisionTraceEngine, _risk_score_to_confidence
from models.enums import RiskBand
from models.risk_profile import ChurnRiskProfile


@pytest.fixture()
def engine() -> DecisionTraceEngine:
    return DecisionTraceEngine()


def _make_profile(
    customer_id: str = "C1",
    risk_band: RiskBand = RiskBand.CRITICAL,
    drivers: list | None = None,
    revenue_at_risk: float = 1000.0,
) -> ChurnRiskProfile:
    return ChurnRiskProfile(
        customer_id=customer_id,
        risk_score=0.9 if risk_band == RiskBand.CRITICAL else 0.45,
        risk_band=risk_band,
        drivers=drivers or ["Failed Payments"],
        revenue_at_risk=revenue_at_risk,
        explanation="Test profile.",
    )


def _make_leakage(
    leakage_type: str = "Failed Payment",
    customer_id: str = "C1",
    revenue_loss: float = 500.0,
) -> dict:
    return {
        "leakage_type": leakage_type,
        "customer_id": customer_id,
        "estimated_revenue_loss": revenue_loss,
        "estimated_loss": revenue_loss,
        "evidence": f"{leakage_type} detected for {customer_id}.",
        "recommended_action": "Investigate.",
        "affected_customers": 1,
    }


def _make_recommendation() -> dict:
    return {
        "rule_id": "REC_001",
        "recommendation_title": "Executive Outreach",
        "category": "retention",
        "customer_id": "C1",
        "segment": "Enterprise",
        "reason": "Schedule executive review.",
        "estimated_revenue_impact": 2000.0,
        "impact_score": 3400.0,
        "confidence_level": "High",
        "evidence_source": "Churn risk band: Critical. Drivers: Failed Payments.",
        "suggested_owner": "Account Executive",
    }


def _make_intervention() -> dict:
    return {
        "intervention_id": "IV-ABCD1234",
        "recommendation_title": "Executive Outreach",
        "category": "retention",
        "target_segment": "Enterprise",
        "estimated_revenue_impact": 2000.0,
        "expected_action": "Schedule executive review.",
        "effort_level": "High",
        "confidence_level": "High",
        "priority_band": "Critical",
    }


# ---------------------------------------------------------------------------
# create_trace factory
# ---------------------------------------------------------------------------


class TestCreateTrace:
    def test_returns_decision_trace_instance(self, engine):
        trace = engine.create_trace(
            entity_type="Test",
            entity_id="E1",
            signal="Test signal",
            triggered_rule="Test rule",
            evidence="Test evidence",
            business_impact="$100",
            generated_action="Do something.",
            confidence_level="High",
        )
        assert isinstance(trace, DecisionTrace)

    def test_trace_has_required_fields(self, engine):
        trace = engine.create_trace(
            entity_type="Test",
            entity_id="E1",
            signal="signal",
            triggered_rule="rule",
            evidence="evidence",
            business_impact="impact",
            generated_action="action",
            confidence_level="Medium",
        )
        assert trace.trace_id.startswith("TRC-")
        assert trace.entity_type == "Test"
        assert trace.entity_id == "E1"
        assert trace.signal == "signal"
        assert trace.confidence_level == "Medium"

    def test_trace_is_stored_internally(self, engine):
        engine.create_trace("T", "E1", "s", "r", "e", "b", "a", "High")
        assert engine.trace_count == 1


def test_risk_score_to_confidence_low_band():
    assert _risk_score_to_confidence(0.1) == "Low"


# ---------------------------------------------------------------------------
# trace_churn_risk
# ---------------------------------------------------------------------------


class TestTraceChurnRisk:
    def test_churn_trace_entity_type_is_churn_risk(self, engine):
        trace = engine.trace_churn_risk(_make_profile())
        assert trace.entity_type == "ChurnRisk"

    def test_churn_trace_entity_id_is_customer_id(self, engine):
        trace = engine.trace_churn_risk(_make_profile(customer_id="C99"))
        assert trace.entity_id == "C99"

    def test_churn_trace_signal_includes_drivers(self, engine):
        profile = _make_profile(drivers=["Failed Payments", "Low NPS"])
        trace = engine.trace_churn_risk(profile)
        assert "Failed Payments" in trace.signal

    def test_churn_trace_business_impact_includes_revenue(self, engine):
        profile = _make_profile(revenue_at_risk=5000.0)
        trace = engine.trace_churn_risk(profile)
        assert "5,000" in trace.business_impact

    def test_low_risk_churn_trace_stored(self, engine):
        profile = _make_profile(risk_band=RiskBand.LOW, revenue_at_risk=0.0)
        trace = engine.trace_churn_risk(profile)
        assert trace is not None


# ---------------------------------------------------------------------------
# trace_revenue_leakage
# ---------------------------------------------------------------------------


class TestTraceRevenueLeakage:
    def test_leakage_trace_entity_type(self, engine):
        trace = engine.trace_revenue_leakage(_make_leakage())
        assert trace.entity_type == "RevenueLeakage"

    def test_leakage_trace_business_impact_includes_amount(self, engine):
        trace = engine.trace_revenue_leakage(_make_leakage(revenue_loss=750.0))
        assert "750" in trace.business_impact

    def test_leakage_trace_signal_is_leakage_type(self, engine):
        trace = engine.trace_revenue_leakage(_make_leakage(leakage_type="Refund"))
        assert "Refund" in trace.signal


# ---------------------------------------------------------------------------
# trace_recommendation
# ---------------------------------------------------------------------------


class TestTraceRecommendation:
    def test_recommendation_trace_entity_type(self, engine):
        trace = engine.trace_recommendation(_make_recommendation())
        assert trace.entity_type == "Recommendation"

    def test_recommendation_trace_generated_action_non_empty(self, engine):
        trace = engine.trace_recommendation(_make_recommendation())
        assert len(trace.generated_action) > 0


# ---------------------------------------------------------------------------
# trace_intervention
# ---------------------------------------------------------------------------


class TestTraceIntervention:
    def test_intervention_trace_entity_type(self, engine):
        trace = engine.trace_intervention(_make_intervention())
        assert trace.entity_type == "Intervention"

    def test_intervention_trace_entity_id(self, engine):
        trace = engine.trace_intervention(_make_intervention())
        assert trace.entity_id == "IV-ABCD1234"


# ---------------------------------------------------------------------------
# export_traces
# ---------------------------------------------------------------------------


class TestExportTraces:
    def test_export_returns_list_of_dicts(self, engine):
        engine.trace_churn_risk(_make_profile())
        traces = engine.export_traces()
        assert isinstance(traces, list)
        assert all(isinstance(t, dict) for t in traces)

    def test_exported_dicts_have_required_keys(self, engine):
        engine.trace_churn_risk(_make_profile())
        traces = engine.export_traces()
        required = {
            "trace_id",
            "created_at",
            "entity_type",
            "entity_id",
            "signal",
            "triggered_rule",
            "evidence",
            "business_impact",
            "generated_action",
            "confidence_level",
        }
        for trace in traces:
            assert required.issubset(trace.keys())

    def test_empty_engine_exports_empty_list(self, engine):
        assert engine.export_traces() == []

    def test_trace_count_matches_export_length(self, engine):
        engine.trace_churn_risk(_make_profile("C1"))
        engine.trace_churn_risk(_make_profile("C2"))
        engine.trace_revenue_leakage(_make_leakage())
        assert engine.trace_count == len(engine.export_traces())


class TestBulkTraceCreators:
    def test_bulk_trace_methods_filter_and_trace_expected_entities(self, engine):
        engine.trace_all_churn_risks(
            [
                _make_profile("LOW", risk_band=RiskBand.LOW, revenue_at_risk=0.0),
                _make_profile("HIGH", risk_band=RiskBand.HIGH, revenue_at_risk=1000.0),
            ]
        )
        engine.trace_all_leakages(
            [
                _make_leakage(customer_id="ZERO", revenue_loss=0.0),
                _make_leakage(customer_id="LOSS", revenue_loss=25.0),
            ]
        )
        engine.trace_all_recommendations([_make_recommendation()])
        engine.trace_all_interventions([_make_intervention()])

        traces = engine.export_traces()
        assert [trace["entity_type"] for trace in traces] == [
            "ChurnRisk",
            "RevenueLeakage",
            "Recommendation",
            "Intervention",
        ]
        assert traces[0]["entity_id"] == "HIGH"
        assert traces[1]["entity_id"] == "LOSS"
