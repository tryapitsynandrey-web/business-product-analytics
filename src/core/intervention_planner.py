"""
InterventionPlanner — converts business recommendations into actionable
intervention records with effort estimates, revenue projections, and priority scores.

Design contract:
    - Input: list of recommendation dicts (from RecommendationEngine)
    - Output: list of intervention dicts (one per recommendation)
    - Revenue impact is propagated from the recommendation's estimated_revenue_impact
    - Effort and owner are inferred from the recommendation rule metadata
    - Priority score and band are derived via PrioritizationEngine
    - No analytics logic — this is a transformation / enrichment layer
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List

from core.prioritization import calculate_priority_score, assign_priority_band

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Effort inference rules
# ---------------------------------------------------------------------------

# Maps recommendation category to default effort level
_CATEGORY_EFFORT: Dict[str, str] = {
    "retention": "High",
    "billing_recovery": "Low",
    "engagement": "Medium",
    "upsell": "Medium",
}

# Maps ownership keywords to default effort
_OWNER_EFFORT_HINTS: Dict[str, str] = {
    "automation": "Low",
    "csm": "High",
    "customer success": "High",
    "account executive": "High",
    "finance": "Medium",
    "marketing": "Low",
    "billing": "Low",
}

# Confidence level string → numeric weight
_CONFIDENCE_WEIGHTS: Dict[str, float] = {
    "High": 0.85,
    "Medium": 0.65,
    "Low": 0.40,
}


# ---------------------------------------------------------------------------
# InterventionPlanner class
# ---------------------------------------------------------------------------

class InterventionPlanner:
    """
    Transforms recommendation dicts into structured intervention records.
    """

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def create_intervention_plan(
        self, recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert every recommendation into an intervention record.

        Parameters
        ----------
        recommendations : list of dicts from RecommendationEngine

        Returns
        -------
        List of intervention dicts, each containing all required fields.
        """
        interventions: List[Dict[str, Any]] = []
        for rec in recommendations:
            intervention = self.build_intervention_record(rec)
            interventions.append(intervention)

        logger.info("Created %d intervention(s) from %d recommendation(s).",
                    len(interventions), len(recommendations))
        return interventions

    # ------------------------------------------------------------------
    # Estimation helpers
    # ------------------------------------------------------------------

    def estimate_effort_level(self, recommendation: Dict[str, Any]) -> str:
        """
        Infer effort level from the recommendation's category and suggested_owner.

        Priority: explicit 'effort_level' field > category lookup > owner hint > Medium default.
        """
        if recommendation.get("effort_level"):
            return str(recommendation["effort_level"])

        category = str(recommendation.get("category", "")).lower()
        if category in _CATEGORY_EFFORT:
            return _CATEGORY_EFFORT[category]

        owner = str(recommendation.get("suggested_owner", "")).lower()
        for keyword, effort in _OWNER_EFFORT_HINTS.items():
            if keyword in owner:
                return effort

        return "Medium"

    def estimate_revenue_protected(self, recommendation: Dict[str, Any]) -> float:
        """
        Return the estimated revenue impact from the recommendation dict.

        Falls back to 0.0 safely.
        """
        return float(recommendation.get("estimated_revenue_impact", 0.0))

    def suggest_owner(self, recommendation: Dict[str, Any]) -> str:
        """Return the suggested_owner from the recommendation, defaulting to 'Unassigned'."""
        return str(recommendation.get("suggested_owner", "Unassigned"))

    # ------------------------------------------------------------------
    # Record builder
    # ------------------------------------------------------------------

    def build_intervention_record(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a single, fully-populated intervention dict from a recommendation.

        Required fields in output:
            intervention_id, recommendation_title, category, target_segment,
            affected_customers, estimated_revenue_impact, expected_action,
            suggested_owner, confidence_level, effort_level, priority_score,
            priority_band
        """
        effort_level = self.estimate_effort_level(recommendation)
        revenue_impact = self.estimate_revenue_protected(recommendation)
        suggested_owner = self.suggest_owner(recommendation)

        confidence_level = str(recommendation.get("confidence_level", "Medium"))
        confidence_weight = _CONFIDENCE_WEIGHTS.get(confidence_level, 0.65)

        priority_score = calculate_priority_score(
            impact_score=revenue_impact,
            confidence_weight=confidence_weight,
            effort_weight=effort_level,
        )
        priority_band = assign_priority_band(priority_score)

        return {
            "intervention_id": f"IV-{uuid.uuid4().hex[:8].upper()}",
            "recommendation_title": recommendation.get("recommendation_title", "Unnamed"),
            "category": recommendation.get("category", "general"),
            "target_segment": recommendation.get("segment", "All"),
            "affected_customers": int(recommendation.get("affected_customers", 1)),
            "estimated_revenue_impact": revenue_impact,
            "expected_action": recommendation.get("reason", "See recommendation details."),
            "suggested_owner": suggested_owner,
            "confidence_level": confidence_level,
            "effort_level": effort_level,
            "priority_score": round(priority_score, 2),
            "priority_band": priority_band,
        }
