"""
PrioritizationEngine — deterministic scoring and ranking of recommendations
and interventions.

Design contract:
    - Priority score formula:  priority_score = impact_score × confidence_weight / effort_weight
    - effort_weight defaults to 1.0 when missing or zero (safe division)
    - Priority bands are assigned from score thresholds
    - Ranking is descending by priority_score (highest first)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Priority band thresholds
# ---------------------------------------------------------------------------

_CRITICAL_THRESHOLD: float = 5000.0
_HIGH_THRESHOLD: float = 1000.0
_MEDIUM_THRESHOLD: float = 200.0

# Effort-level string → numeric weight for safe division
_EFFORT_WEIGHTS: Dict[str, float] = {
    "Low": 1.0,
    "Medium": 2.0,
    "High": 3.0,
}
_DEFAULT_EFFORT_WEIGHT: float = 1.0


def _parse_effort_weight(effort_level: Any) -> float:
    """Convert an effort_level label to a numeric divisor. Defaults to 1.0."""
    if isinstance(effort_level, (int, float)) and effort_level > 0:
        return float(effort_level)
    return _EFFORT_WEIGHTS.get(str(effort_level), _DEFAULT_EFFORT_WEIGHT)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_priority_score(
    impact_score: float,
    confidence_weight: float,
    effort_weight: Any,
) -> float:
    """
    Compute the priority score.

    Formula:
        priority_score = impact_score × confidence_weight / effort_weight

    Parameters
    ----------
    impact_score      : numeric — composite business impact estimate
    confidence_weight : float 0–1 — confidence that the action will succeed
    effort_weight     : numeric or effort label ('Low', 'Medium', 'High')
                        Zero or missing values are treated as 1.0 (safe default)

    Returns
    -------
    float — priority score (higher is more urgent)
    """
    parsed_effort = _parse_effort_weight(effort_weight)
    if parsed_effort <= 0:
        parsed_effort = _DEFAULT_EFFORT_WEIGHT
    return float(impact_score * confidence_weight / parsed_effort)


def assign_priority_band(score: float) -> str:
    """
    Map a priority_score to a human-readable band.

    Thresholds (based on revenue impact × confidence):
        Critical  ≥ 5,000
        High      ≥ 1,000
        Medium    ≥ 200
        Low       <  200
    """
    if score >= _CRITICAL_THRESHOLD:
        return "Critical"
    if score >= _HIGH_THRESHOLD:
        return "High"
    if score >= _MEDIUM_THRESHOLD:
        return "Medium"
    return "Low"


def rank_recommendations(
    recommendations: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Re-compute priority_score for each recommendation dict and return the
    list sorted descending by priority_score, with priority_band added.

    Each recommendation must contain:
        - impact_score          (float)
        - confidence_weight     (float)
        - suggested_owner       (str, optional)

    effort_weight is inferred from the recommendation if present.

    Returns the same list of dicts enriched with:
        - priority_score (recomputed)
        - priority_band
    """
    ranked: List[Dict[str, Any]] = []
    for rec in recommendations:
        effort = rec.get("effort_level", "Low")
        impact = float(rec.get("impact_score", 0.0))
        confidence = float(rec.get("confidence_weight", 0.5))

        score = calculate_priority_score(impact, confidence, effort)
        band = assign_priority_band(score)

        ranked.append({**rec, "priority_score": score, "priority_band": band})

    ranked.sort(key=lambda r: r["priority_score"], reverse=True)
    logger.info("Ranked %d recommendation(s).", len(ranked))
    return ranked


def rank_interventions(
    interventions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Sort a list of intervention dicts by priority_score descending.

    Expects each intervention dict to already have a priority_score field.
    If missing, computes it from impact, confidence, and effort fields.
    """
    enriched: List[Dict[str, Any]] = []
    for iv in interventions:
        if "priority_score" not in iv:
            effort = iv.get("effort_level", "Low")
            impact = float(iv.get("estimated_revenue_impact", 0.0))
            confidence_str = iv.get("confidence_level", "Medium")
            # Map string label back to float
            confidence = {"High": 0.85, "Medium": 0.65, "Low": 0.40}.get(
                confidence_str, 0.65
            )
            score = calculate_priority_score(impact, confidence, effort)
            band = assign_priority_band(score)
            enriched.append({**iv, "priority_score": score, "priority_band": band})
        else:
            score = float(iv["priority_score"])
            band = assign_priority_band(score)
            enriched.append({**iv, "priority_band": band})

    enriched.sort(key=lambda r: r["priority_score"], reverse=True)
    logger.info("Ranked %d intervention(s).", len(enriched))
    return enriched
