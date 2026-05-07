"""
ChurnRiskEngine — explainable, rule-based churn risk scoring.

Design contract:
    - Rules are loaded from config/churn_rules.yaml.
    - Python evaluates each rule using a safe operator dispatch table (no eval).
    - Supported operators: less_than, less_or_equal, greater_than,
      greater_or_equal, equals, not_equals, contains, is_true.
    - Risk score is the weighted sum of triggered rules, capped at 1.0.
    - Risk band thresholds are read from the YAML risk_bands section.
    - A customer with no triggered rules has risk_score = 0.0 and band = Low.
    - Revenue at risk is only populated for High and Critical customers.
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
# Safe operator dispatch — no eval, no exec
# ---------------------------------------------------------------------------

_OPERATORS: Dict[str, Callable[[Any, Any], bool]] = {
    "less_than":        lambda v, t: v < t,
    "less_or_equal":    lambda v, t: v <= t,
    "greater_than":     lambda v, t: v > t,
    "greater_or_equal": lambda v, t: v >= t,
    "equals":           lambda v, t: v == t,
    "not_equals":       lambda v, t: v != t,
    "contains":         lambda v, t: t in v if isinstance(v, (list, str)) else False,
    "is_true":          lambda v, _: bool(v),
}


def _apply_operator(operator: str, value: Any, threshold: Any) -> bool:
    """
    Evaluate a rule condition using the dispatch table.

    Returns False for unknown operators rather than raising, so a bad YAML entry
    disables the rule without crashing the pipeline.
    """
    fn = _OPERATORS.get(operator)
    if fn is None:
        logger.warning("Unknown churn rule operator '%s' — rule skipped.", operator)
        return False
    try:
        return fn(value, threshold)
    except TypeError:
        return False


# ---------------------------------------------------------------------------
# ChurnRiskEngine
# ---------------------------------------------------------------------------

class ChurnRiskEngine:
    """
    Evaluates per-customer churn risk using YAML-driven, deterministic rules.

    Parameters
    ----------
    rules_path : optional
        Override the default config/churn_rules.yaml location.
    """

    def __init__(self, rules_path: Optional[Any] = None) -> None:
        self._rules_path = rules_path or (CONFIG_DIR / "churn_rules.yaml")
        raw = self._load_yaml()
        self._rules: List[Dict[str, Any]] = [
            r for r in raw.get("rules", []) if r.get("enabled", True)
        ]
        bands_cfg = raw.get("risk_bands", {})
        self._critical_threshold: float = float(bands_cfg.get("critical_threshold", 0.65))
        self._high_threshold: float = float(bands_cfg.get("high_threshold", 0.40))
        self._medium_threshold: float = float(bands_cfg.get("medium_threshold", 0.20))

    def _load_yaml(self) -> Dict[str, Any]:
        with open(self._rules_path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    # ------------------------------------------------------------------
    # Signal computation
    # ------------------------------------------------------------------

    def calculate_customer_signals(
        self, datasets: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Compute one row per active customer with all signal columns required
        by the churn rules.

        Signal columns produced:
            logins_last_period      — total logins across all usage records
            latest_nps_score        — most recent NPS score (NaN if missing)
            failed_payment_count    — count of Failed transactions
            support_ticket_count    — count of support tickets
            key_actions_last_period — total key actions across all usage records
        """
        customers = datasets["customers"].copy()
        subs = datasets["subscriptions"]
        usage = datasets["product_usage"]
        nps = datasets["nps_scores"]
        tickets = datasets["support_tickets"]
        transactions = datasets["transactions"]

        # Only score active customers
        active = customers[customers["is_active"] == True][["customer_id"]].copy()

        # logins_last_period
        login_agg = (
            usage.groupby("customer_id")["logins"]
            .sum()
            .reset_index()
            .rename(columns={"logins": "logins_last_period"})
        )

        # key_actions_last_period
        action_agg = (
            usage.groupby("customer_id")["key_actions"]
            .sum()
            .reset_index()
            .rename(columns={"key_actions": "key_actions_last_period"})
        )

        # latest_nps_score — most recent score per customer
        if not nps.empty and "date" in nps.columns:
            nps_sorted = nps.copy()
            nps_sorted["date"] = pd.to_datetime(nps_sorted["date"], errors="coerce")
            latest_nps = (
                nps_sorted.sort_values("date")
                .groupby("customer_id")["score"]
                .last()
                .reset_index()
                .rename(columns={"score": "latest_nps_score"})
            )
        else:
            latest_nps = pd.DataFrame(columns=["customer_id", "latest_nps_score"])

        # failed_payment_count
        failed = (
            transactions[transactions["status"] == "Failed"]
            .groupby("customer_id")
            .size()
            .reset_index(name="failed_payment_count")
        )

        # support_ticket_count
        ticket_count = (
            tickets.groupby("customer_id")
            .size()
            .reset_index(name="support_ticket_count")
        )

        # Merge all signals onto active customers
        signals = active
        signals = signals.merge(login_agg, on="customer_id", how="left")
        signals = signals.merge(action_agg, on="customer_id", how="left")
        signals = signals.merge(latest_nps, on="customer_id", how="left")
        signals = signals.merge(failed, on="customer_id", how="left")
        signals = signals.merge(ticket_count, on="customer_id", how="left")

        # Fill missing numeric signals with zero (no signal = no activity)
        fill_cols = [
            "logins_last_period",
            "key_actions_last_period",
            "failed_payment_count",
            "support_ticket_count",
        ]
        signals[fill_cols] = signals[fill_cols].fillna(0)
        # latest_nps_score stays NaN when no NPS response exists

        return signals

    # ------------------------------------------------------------------
    # Rule application
    # ------------------------------------------------------------------

    def apply_churn_rules(
        self, signals_row: Dict[str, Any]
    ) -> tuple[float, List[str]]:
        """
        Apply all enabled rules to a single customer's signal dict.

        Returns
        -------
        (risk_score, drivers)
            risk_score : float — weighted sum of triggered rules, max 1.0
            drivers    : list of driver_label strings for triggered rules
        """
        risk_score = 0.0
        drivers: List[str] = []

        for rule in self._rules:
            signal_name = rule["signal_name"]
            operator = rule["operator"]
            threshold = rule["threshold"]
            weight = float(rule["weight"])
            driver_label = rule["driver_label"]

            raw_value = signals_row.get(signal_name)

            # Treat missing NPS as no signal (do not flag as low NPS)
            if raw_value is None or (
                signal_name == "latest_nps_score"
                and pd.isna(raw_value)
            ):
                continue

            if _apply_operator(operator, raw_value, threshold):
                risk_score += weight
                drivers.append(driver_label)

        return min(1.0, risk_score), drivers

    # ------------------------------------------------------------------
    # Risk band assignment
    # ------------------------------------------------------------------

    def assign_risk_band(self, risk_score: float) -> RiskBand:
        """Map a numeric risk score to a RiskBand enum using YAML thresholds."""
        if risk_score >= self._critical_threshold:
            return RiskBand.CRITICAL
        if risk_score >= self._high_threshold:
            return RiskBand.HIGH
        if risk_score >= self._medium_threshold:
            return RiskBand.MEDIUM
        return RiskBand.LOW

    # ------------------------------------------------------------------
    # Revenue at risk
    # ------------------------------------------------------------------

    def calculate_revenue_at_risk(
        self,
        customer_id: str,
        risk_band: RiskBand,
        subs: pd.DataFrame,
    ) -> float:
        """
        Sum of monthly_price for the customer's Active subscriptions, only
        populated when risk_band is High or Critical.
        """
        if risk_band not in (RiskBand.HIGH, RiskBand.CRITICAL):
            return 0.0
        customer_subs = subs[
            (subs["customer_id"] == customer_id) & (subs["status"] == "Active")
        ]
        return float(customer_subs["monthly_price"].sum())

    # ------------------------------------------------------------------
    # Main evaluation method
    # ------------------------------------------------------------------

    def evaluate_risk(
        self, datasets: Dict[str, pd.DataFrame]
    ) -> List[ChurnRiskProfile]:
        """
        Score every active customer and return a list of ChurnRiskProfile objects.

        Guarantee: customers with zero triggered rules will have risk_score = 0.0
        and risk_band = Low.  Revenue at risk is 0.0 for Low and Medium bands.
        """
        signals_df = self.calculate_customer_signals(datasets)
        subs = datasets["subscriptions"]
        profiles: List[ChurnRiskProfile] = []

        for signals_dict in signals_df.to_dict("records"):
            customer_id = signals_dict["customer_id"]

            risk_score, drivers = self.apply_churn_rules(signals_dict)
            risk_band = self.assign_risk_band(risk_score)
            revenue_at_risk = self.calculate_revenue_at_risk(
                customer_id, risk_band, subs
            )

            explanation = (
                f"Risk drivers: {', '.join(drivers)}."
                if drivers
                else "No significant risk signals detected."
            )

            profiles.append(
                ChurnRiskProfile(
                    customer_id=customer_id,
                    risk_score=risk_score,
                    risk_band=risk_band,
                    drivers=drivers,
                    revenue_at_risk=revenue_at_risk,
                    explanation=explanation,
                )
            )

        logger.info(
            "Churn risk scored %d active customers. "
            "Critical: %d, High: %d, Medium: %d, Low: %d.",
            len(profiles),
            sum(1 for p in profiles if p.risk_band == RiskBand.CRITICAL),
            sum(1 for p in profiles if p.risk_band == RiskBand.HIGH),
            sum(1 for p in profiles if p.risk_band == RiskBand.MEDIUM),
            sum(1 for p in profiles if p.risk_band == RiskBand.LOW),
        )
        return profiles
