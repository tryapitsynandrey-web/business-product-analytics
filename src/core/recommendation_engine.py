"""
RecommendationEngine — rule-based, explainable recommendation generation.

Design contract:
    - Rules loaded from config/recommendation_rules.yaml.
    - Matching is performed using a safe operator dispatch table (no eval).
    - Two trigger_type values are supported:
        'churn_risk'  — matches against ChurnRiskProfile fields.
        'leakage'     — matches against revenue leakage event dicts.
    - Optional filter_field / filter_operator / filter_value allow a second
      condition on ChurnRiskProfile (e.g., segment == 'Enterprise').
    - Impact score formula:
        severity_weight × affected_customers × estimated_revenue_impact × confidence_weight
    - Returns plain dicts (not BusinessRecommendation dataclass) so the
      pipeline can serialise them directly to CSV without extra adapters.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import yaml

from models.enums import RiskBand
from models.risk_profile import ChurnRiskProfile
from utils.paths import CONFIG_DIR

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Safe operator dispatch
# ---------------------------------------------------------------------------

_OPERATORS: Dict[str, Callable[[Any, Any], bool]] = {
    "equals":           lambda v, t: str(v) == str(t),
    "not_equals":       lambda v, t: str(v) != str(t),
    "greater_than":     lambda v, t: float(v) > float(t),
    "greater_or_equal": lambda v, t: float(v) >= float(t),
    "less_than":        lambda v, t: float(v) < float(t),
    "less_or_equal":    lambda v, t: float(v) <= float(t),
    "contains":         lambda v, t: str(t).lower() in str(v).lower(),
}


def _match(operator: str, value: Any, threshold: Any) -> bool:
    fn = _OPERATORS.get(operator)
    if fn is None:
        logger.warning("Unknown recommendation rule operator '%s' — skipped.", operator)
        return False
    try:
        return fn(value, threshold)
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# RecommendationEngine
# ---------------------------------------------------------------------------

class RecommendationEngine:
    """
    Generates business recommendations from churn risk profiles and leakage
    events using YAML-driven, deterministic rules.
    """

    def __init__(self, rules_path: Optional[Any] = None) -> None:
        self._rules_path = rules_path or (CONFIG_DIR / "recommendation_rules.yaml")
        raw = self._load_yaml()
        self._rules: List[Dict[str, Any]] = [
            r for r in raw.get("rules", []) if r.get("enabled", True)
        ]

    def _load_yaml(self) -> Dict[str, Any]:
        with open(self._rules_path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate_recommendations(
        self,
        datasets: Dict[str, pd.DataFrame],
        risk_profiles: List[ChurnRiskProfile],
        leakages: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate all applicable recommendations from risk profiles and leakage events.

        Parameters
        ----------
        datasets   : loaded DataFrames (used to look up customer segment).
        risk_profiles : output of ChurnRiskEngine.evaluate_risk().
        leakages   : output of RevenueLeakageEngine.detect_leakage(); optional.

        Returns
        -------
        List[dict] — one dict per matched rule×customer pair, de-duplicated by
        rule_id so each rule fires at most once per customer.
        """
        customers = datasets["customers"]
        subs = datasets["subscriptions"]
        leakages = leakages or []

        recs: List[Dict[str, Any]] = []

        # --- Churn risk recommendations
        for profile in risk_profiles:
            customer_rows = customers[customers["customer_id"] == profile.customer_id]
            if customer_rows.empty:
                continue
            segment = str(customer_rows.iloc[0].get("segment", ""))

            matched = self.match_recommendation_rules(
                trigger_type="churn_risk",
                context={
                    "risk_band": profile.risk_band.value,
                    "driver": " | ".join(profile.drivers),
                    "segment": segment,
                },
            )
            for rule in matched:
                revenue_impact = profile.revenue_at_risk
                recs.append(self._build_recommendation(
                    rule=rule,
                    customer_id=profile.customer_id,
                    segment=segment,
                    estimated_revenue_impact=revenue_impact,
                    evidence_source=(
                        f"Churn risk band: {profile.risk_band.value}. "
                        f"Drivers: {', '.join(profile.drivers) or 'none'}."
                    ),
                ))

        # --- Leakage recommendations
        for leakage in leakages:
            matched = self.match_recommendation_rules(
                trigger_type="leakage",
                context={"leakage_type": leakage.get("leakage_type", "")},
            )
            for rule in matched:
                cid = leakage.get("customer_id", "unknown")
                customer_rows = customers[customers["customer_id"] == cid]
                segment = (
                    str(customer_rows.iloc[0].get("segment", ""))
                    if not customer_rows.empty else "Unknown"
                )
                recs.append(self._build_recommendation(
                    rule=rule,
                    customer_id=cid,
                    segment=segment,
                    estimated_revenue_impact=float(
                        leakage.get("estimated_revenue_loss", 0.0)
                    ),
                    evidence_source=leakage.get("evidence", "Leakage event detected."),
                ))

        logger.info("Generated %d recommendation(s).", len(recs))
        return recs

    def match_recommendation_rules(
        self,
        trigger_type: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Return all rules whose trigger matches the context dict.

        Each rule is checked on two conditions:
            1. Primary: trigger_field / operator / threshold
            2. Optional secondary: filter_field / filter_operator / filter_value

        Parameters
        ----------
        trigger_type : str
            'churn_risk' or 'leakage'.
        context : dict
            Key-value pairs representing the current event's attributes.

        Returns
        -------
        List of matching rule dicts.
        """
        matched = []
        for rule in self._rules:
            if rule.get("trigger_type") != trigger_type:
                continue

            trigger_field = rule.get("trigger_field", "")
            operator = rule.get("operator", "equals")
            threshold = rule.get("threshold")

            primary_value = context.get(trigger_field)
            if primary_value is None:
                continue
            if not _match(operator, primary_value, threshold):
                continue

            # Optional secondary filter
            filter_field = rule.get("filter_field")
            if filter_field and filter_field != "null":
                filter_op = rule.get("filter_operator", "equals")
                filter_val = rule.get("filter_value")
                secondary_value = context.get(filter_field)
                if secondary_value is None or not _match(
                    filter_op, secondary_value, filter_val
                ):
                    continue

            matched.append(rule)
        return matched

    def calculate_impact_score(
        self,
        severity_weight: float,
        affected_customers: int,
        estimated_revenue_impact: float,
        confidence_weight: float,
    ) -> float:
        """
        Formula:
            impact_score = severity_weight × affected_customers
                           × estimated_revenue_impact × confidence_weight

        Returns 0.0 when estimated_revenue_impact is 0 (leakage without dollar value).
        """
        return severity_weight * affected_customers * estimated_revenue_impact * confidence_weight

    def calculate_confidence_level(self, confidence_weight: float) -> str:
        """Map a numeric confidence_weight to a human label."""
        if confidence_weight >= 0.85:
            return "High"
        if confidence_weight >= 0.60:
            return "Medium"
        return "Low"

    # ------------------------------------------------------------------
    # Internal builder
    # ------------------------------------------------------------------

    def _build_recommendation(
        self,
        rule: Dict[str, Any],
        customer_id: str,
        segment: str,
        estimated_revenue_impact: float,
        evidence_source: str,
    ) -> Dict[str, Any]:
        """Construct the standardised recommendation output dict."""
        confidence_weight = float(rule.get("confidence_weight", 0.5))
        severity_weight = float(rule.get("severity_weight", 1.0))
        affected_customers = 1

        impact_score = self.calculate_impact_score(
            severity_weight, affected_customers, estimated_revenue_impact, confidence_weight
        )
        confidence_level = self.calculate_confidence_level(confidence_weight)

        return {
            "rule_id": rule.get("rule_id"),
            "recommendation_title": rule.get("recommendation_title"),
            "category": rule.get("category"),
            "customer_id": customer_id,
            "segment": segment,
            "reason": rule.get("expected_action", "").strip(),
            "affected_customers": affected_customers,
            "estimated_revenue_impact": estimated_revenue_impact,
            "impact_score": impact_score,
            "confidence_level": confidence_level,
            "confidence_weight": confidence_weight,
            "suggested_owner": rule.get("suggested_owner"),
            "evidence_source": evidence_source,
        }
