"""
DecisionTraceEngine — creates structured audit trails for every business
decision made by the ProductPulse analytics engine.

Design contract:
    - Every analytical output (churn score, leakage flag, recommendation,
      intervention) gets a trace record linking signal → rule → action.
    - Traces are deterministic and immutable once created.
    - export_traces() returns a flat list of dicts suitable for CSV export.
    - No analytics logic lives here; this is a traceability / audit layer.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

from models.risk_profile import ChurnRiskProfile

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Trace dataclass (kept from original stub, extended)
# ---------------------------------------------------------------------------


@dataclass
class DecisionTrace:
    """Immutable record of a single business decision and its justification."""

    trace_id: str
    created_at: str  # ISO-8601 UTC timestamp
    entity_type: str  # 'ChurnRisk' | 'RevenueLeakage' | 'Recommendation' | 'Intervention'
    entity_id: str
    signal: str
    triggered_rule: str
    evidence: str
    business_impact: str
    generated_action: str
    confidence_level: str  # 'High' | 'Medium' | 'Low'


def _new_trace_id(sequence: int) -> str:
    return f"TRC-{sequence:010d}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# DecisionTraceEngine
# ---------------------------------------------------------------------------


class DecisionTraceEngine:
    """
    Creates and stores decision traces for all analytical outputs.

    Usage
    -----
    engine = DecisionTraceEngine()
    engine.trace_churn_risk(profile)
    engine.trace_revenue_leakage(leakage_event)
    engine.trace_recommendation(rec)
    engine.trace_intervention(intervention)
    traces = engine.export_traces()
    """

    def __init__(self, created_at: str | None = None) -> None:
        self._traces: List[DecisionTrace] = []
        self._created_at = created_at
        self._next_sequence = 1

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    def create_trace(
        self,
        entity_type: str,
        entity_id: str,
        signal: str,
        triggered_rule: str,
        evidence: str,
        business_impact: str,
        generated_action: str,
        confidence_level: str,
    ) -> DecisionTrace:
        """
        Create and store a single DecisionTrace.

        Returns
        -------
        DecisionTrace
            The created trace object.
        """
        trace = DecisionTrace(
            trace_id=_new_trace_id(self._next_sequence),
            created_at=self._created_at or _utc_now(),
            entity_type=entity_type,
            entity_id=entity_id,
            signal=signal,
            triggered_rule=triggered_rule,
            evidence=evidence,
            business_impact=business_impact,
            generated_action=generated_action,
            confidence_level=confidence_level,
        )
        self._next_sequence += 1
        self._traces.append(trace)
        return trace

    # ------------------------------------------------------------------
    # Specialised trace creators
    # ------------------------------------------------------------------

    def trace_churn_risk(self, profile: ChurnRiskProfile) -> DecisionTrace:
        """
        Create a trace for a ChurnRiskProfile.

        Evidence is the list of triggered drivers.
        Business impact is revenue_at_risk.
        """
        drivers_str = ", ".join(profile.drivers) if profile.drivers else "No risk signals"
        impact_str = (
            f"${profile.revenue_at_risk:,.2f} revenue at risk"
            if profile.revenue_at_risk > 0
            else "No direct revenue at risk identified"
        )
        confidence = _risk_score_to_confidence(profile.risk_score)

        return self.create_trace(
            entity_type="ChurnRisk",
            entity_id=profile.customer_id,
            signal=drivers_str,
            triggered_rule=f"Risk band: {profile.risk_band.value}",
            evidence=profile.explanation,
            business_impact=impact_str,
            generated_action=(
                "Escalate to churn prevention workflow"
                if profile.risk_band.value in ("High", "Critical")
                else "Monitor — no immediate action required"
            ),
            confidence_level=confidence,
        )

    def trace_revenue_leakage(self, leakage: Dict[str, Any]) -> DecisionTrace:
        """
        Create a trace for a revenue leakage event dict.
        """
        loss = float(leakage.get("estimated_revenue_loss", 0.0))
        return self.create_trace(
            entity_type="RevenueLeakage",
            entity_id=str(leakage.get("customer_id", "unknown")),
            signal=str(leakage.get("leakage_type", "Unknown")),
            triggered_rule=f"Leakage type: {leakage.get('leakage_type', 'Unknown')}",
            evidence=str(leakage.get("evidence", "No evidence recorded.")),
            business_impact=f"${loss:,.2f} estimated revenue loss",
            generated_action=str(leakage.get("recommended_action", "Investigate.")),
            confidence_level="High" if loss > 0 else "Medium",
        )

    def trace_recommendation(self, rec: Dict[str, Any]) -> DecisionTrace:
        """
        Create a trace for a recommendation dict from RecommendationEngine.
        """
        return self.create_trace(
            entity_type="Recommendation",
            entity_id=str(rec.get("rule_id", "UNKNOWN")),
            signal=str(rec.get("evidence_source", "No signal recorded.")),
            triggered_rule=str(rec.get("rule_id", "UNKNOWN")),
            evidence=str(rec.get("evidence_source", "")),
            business_impact=(
                f"${float(rec.get('estimated_revenue_impact', 0.0)):,.2f} potential impact "
                f"(score: {float(rec.get('impact_score', 0.0)):.1f})"
            ),
            generated_action=str(rec.get("reason", rec.get("recommendation_title", ""))),
            confidence_level=str(rec.get("confidence_level", "Medium")),
        )

    def trace_intervention(self, intervention: Dict[str, Any]) -> DecisionTrace:
        """
        Create a trace for an intervention dict from InterventionPlanner.
        """
        return self.create_trace(
            entity_type="Intervention",
            entity_id=str(intervention.get("intervention_id", "UNKNOWN")),
            signal=str(intervention.get("recommendation_title", "")),
            triggered_rule=str(intervention.get("category", "general")),
            evidence=(
                f"Segment: {intervention.get('target_segment', 'All')} | "
                f"Effort: {intervention.get('effort_level', 'Unknown')}"
            ),
            business_impact=(
                f"${float(intervention.get('estimated_revenue_impact', 0.0)):,.2f} revenue impact | "
                f"Priority: {intervention.get('priority_band', 'Unknown')}"
            ),
            generated_action=str(intervention.get("expected_action", "")),
            confidence_level=str(intervention.get("confidence_level", "Medium")),
        )

    # ------------------------------------------------------------------
    # Bulk trace creators (used by pipeline)
    # ------------------------------------------------------------------

    def trace_all_churn_risks(self, profiles: List[ChurnRiskProfile]) -> None:
        """Trace every high/critical churn risk profile."""
        for profile in profiles:
            if profile.risk_band.value in ("High", "Critical"):
                self.trace_churn_risk(profile)

    def trace_all_leakages(self, leakages: List[Dict[str, Any]]) -> None:
        """Trace every leakage event with a non-zero revenue loss."""
        for leakage in leakages:
            if float(leakage.get("estimated_revenue_loss", 0.0)) > 0:
                self.trace_revenue_leakage(leakage)

    def trace_all_recommendations(self, recommendations: List[Dict[str, Any]]) -> None:
        """Trace all recommendations."""
        for rec in recommendations:
            self.trace_recommendation(rec)

    def trace_all_interventions(self, interventions: List[Dict[str, Any]]) -> None:
        """Trace all interventions."""
        for iv in interventions:
            self.trace_intervention(iv)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_traces(self) -> List[Dict[str, Any]]:
        """
        Return all stored traces as a flat list of dicts.

        Suitable for direct conversion to a Pandas DataFrame or CSV.
        """
        return [asdict(t) for t in self._traces]

    @property
    def trace_count(self) -> int:
        """Total number of traces recorded."""
        return len(self._traces)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _risk_score_to_confidence(risk_score: float) -> str:
    """Map a 0–1 risk score to a confidence label."""
    if risk_score >= 0.65:
        return "High"
    if risk_score >= 0.40:
        return "Medium"
    return "Low"
