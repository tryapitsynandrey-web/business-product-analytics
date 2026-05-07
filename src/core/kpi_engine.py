"""
KPIEngine — deterministic calculation of all ProductPulse business KPIs.

Design contract:
    - Every metric is explicitly implemented in Python (not via YAML formula eval).
    - metric_catalog.yaml defines governance contracts; this file executes them.
    - Every calculation returns a typed MetricResult.
    - Zero denominators are always handled explicitly.
    - MetricGovernance is consulted before each calculation.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional

import pandas as pd

from core.metric_governance import MetricGovernance
from models.metrics import MetricResult

logger = logging.getLogger(__name__)

# Activation threshold: number of cumulative key actions required
# to consider a customer "activated".  Sourced from catalog interpretation.
_ACTIVATION_KEY_ACTION_THRESHOLD: int = 5

# Plans considered "expansion" (high-tier upsells)
_EXPANSION_PLANS: frozenset = frozenset({"Premium", "Enterprise"})

# Statuses that represent revenue-bearing subscriptions
_ACTIVE_STATUSES: frozenset = frozenset({"Active", "Past Due"})


def _safe_divide(numerator: float, denominator: float, fallback: float = 0.0) -> float:
    """Return numerator / denominator, or fallback when denominator is zero."""
    return numerator / denominator if denominator != 0 else fallback


class KPIEngine:
    """
    Calculates all SaaS KPIs governed by the metric catalog.

    Parameters
    ----------
    governance : MetricGovernance
        Gatekeeper instance used to validate contracts before calculation.
    """

    SUPPORTED_METRICS = {
        "monthly_recurring_revenue": "calculate_mrr",
        "average_revenue_per_user": "calculate_arpu",
        "expansion_revenue": "calculate_expansion_revenue",
        "contraction_revenue": "calculate_contraction_revenue",
        "gross_revenue_retention": "calculate_gross_revenue_retention",
        "net_revenue_retention": "calculate_net_revenue_retention",
        "revenue_at_risk": "calculate_revenue_at_risk",
        "activation_rate": "calculate_activation_rate",
        "usage_frequency": "calculate_usage_frequency",
        "key_action_rate": "calculate_key_action_rate",
        "engagement_drop_rate": "calculate_engagement_drop_rate",
        "feature_adoption_proxy": "calculate_feature_adoption_proxy",
        "customer_churn_rate": "calculate_customer_churn_rate",
        "retention_rate": "calculate_retention_rate",
        "average_nps": "calculate_average_nps",
        "support_burden": "calculate_support_burden",
        "time_to_activation": "calculate_time_to_activation",
    }

    def __init__(self, governance: MetricGovernance) -> None:
        self.governance = governance

    @classmethod
    def get_supported_metrics(cls) -> Dict[str, str]:
        return dict(cls.SUPPORTED_METRICS)

    def _active_customer_ids(self, datasets: Dict[str, pd.DataFrame]) -> set[str]:
        """Return a set of customer IDs for all currently active customers."""
        customers = datasets["customers"]
        return set(customers.loc[customers["is_active"] == True, "customer_id"])

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------

    def calculate_kpis(
        self,
        datasets: Dict[str, pd.DataFrame],
        target_date: date,
    ) -> List[MetricResult]:
        """
        Run all enabled metrics through their governance contract, then calculate.

        Parameters
        ----------
        datasets : dict
            Loaded DataFrames, keyed by dataset name.
        target_date : date
            The date to stamp on every MetricResult.

        Returns
        -------
        List[MetricResult]
            One entry per successfully calculated metric.
        """
        results: List[MetricResult] = []

        calculators = {
            "monthly_recurring_revenue": self.calculate_mrr,
            "average_revenue_per_user": self.calculate_arpu,
            "expansion_revenue": self.calculate_expansion_revenue,
            "contraction_revenue": self.calculate_contraction_revenue,
            "gross_revenue_retention": self.calculate_gross_revenue_retention,
            "net_revenue_retention": self.calculate_net_revenue_retention,
            "revenue_at_risk": self.calculate_revenue_at_risk,
            "activation_rate": self.calculate_activation_rate,
            "usage_frequency": self.calculate_usage_frequency,
            "key_action_rate": self.calculate_key_action_rate,
            "engagement_drop_rate": self.calculate_engagement_drop_rate,
            "feature_adoption_proxy": self.calculate_feature_adoption_proxy,
            "customer_churn_rate": self.calculate_customer_churn_rate,
            "retention_rate": self.calculate_retention_rate,
            "average_nps": self.calculate_average_nps,
            "support_burden": self.calculate_support_burden,
            "time_to_activation": self.calculate_time_to_activation,
        }

        for metric_name, fn in calculators.items():
            if not self.governance.validate_metric(metric_name, datasets):
                logger.warning("Skipping metric '%s' — governance check failed.", metric_name)
                continue
            try:
                result = fn(datasets, target_date)
                if result is not None:
                    results.append(result)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Error calculating metric '%s': %s", metric_name, exc)

        return results

    # ------------------------------------------------------------------
    # Revenue KPIs
    # ------------------------------------------------------------------

    def calculate_mrr(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """Sum of monthly_price for Active and Past Due subscriptions."""
        subs = datasets["subscriptions"]
        active = subs[subs["status"].isin(_ACTIVE_STATUSES)]
        value = float(active["monthly_price"].sum())
        return MetricResult(
            metric_name="monthly_recurring_revenue",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation="Sum of monthly_price for Active and Past Due subscriptions.",
        )

    def calculate_arpu(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """MRR divided by count of unique paying customers."""
        subs = datasets["subscriptions"]
        active = subs[subs["status"].isin(_ACTIVE_STATUSES)]
        mrr = float(active["monthly_price"].sum())
        unique_customers = active["customer_id"].nunique()
        value = _safe_divide(mrr, unique_customers)
        return MetricResult(
            metric_name="average_revenue_per_user",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=f"MRR ${mrr:,.2f} / {unique_customers} active customers.",
        )

    def calculate_expansion_revenue(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """MRR from Premium and Enterprise plan subscriptions that are Active."""
        subs = datasets["subscriptions"]
        expansion = subs[
            subs["status"].isin(_ACTIVE_STATUSES) & subs["plan"].isin(_EXPANSION_PLANS)
        ]
        value = float(expansion["monthly_price"].sum())
        return MetricResult(
            metric_name="expansion_revenue",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=(
                f"MRR from {len(expansion)} Active Premium/Enterprise subscriptions."
            ),
        )

    def calculate_contraction_revenue(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """MRR from Past Due subscriptions — revenue owed but not yet collected."""
        subs = datasets["subscriptions"]
        past_due = subs[subs["status"] == "Past Due"]
        value = float(past_due["monthly_price"].sum())
        return MetricResult(
            metric_name="contraction_revenue",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=f"Monthly price at risk across {len(past_due)} Past Due subscriptions.",
        )

    def calculate_gross_revenue_retention(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """Active MRR / (Active + Past Due + Canceled MRR), bounded [0, 1]."""
        subs = datasets["subscriptions"]
        active_mrr = float(
            subs[subs["status"].isin(_ACTIVE_STATUSES)]["monthly_price"].sum()
        )
        total_mrr = float(
            subs[subs["status"].isin({"Active", "Past Due", "Canceled"})][
                "monthly_price"
            ].sum()
        )
        value = min(1.0, _safe_divide(active_mrr, total_mrr))
        return MetricResult(
            metric_name="gross_revenue_retention",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=(
                f"Active MRR ${active_mrr:,.2f} / Total billed MRR ${total_mrr:,.2f}."
            ),
        )

    def calculate_net_revenue_retention(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """(Active MRR + Expansion MRR) / Total billed MRR. Can exceed 1.0."""
        subs = datasets["subscriptions"]
        active_mrr = float(
            subs[subs["status"].isin(_ACTIVE_STATUSES)]["monthly_price"].sum()
        )
        expansion_mrr = float(
            subs[
                subs["status"].isin(_ACTIVE_STATUSES) & subs["plan"].isin(_EXPANSION_PLANS)
            ]["monthly_price"].sum()
        )
        total_billed = float(
            subs[subs["status"].isin({"Active", "Past Due", "Canceled"})][
                "monthly_price"
            ].sum()
        )
        value = _safe_divide(active_mrr + expansion_mrr, total_billed)
        return MetricResult(
            metric_name="net_revenue_retention",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=(
                f"(Active ${active_mrr:,.2f} + Expansion ${expansion_mrr:,.2f}) "
                f"/ Total billed ${total_billed:,.2f}."
            ),
        )

    def calculate_revenue_at_risk(
        self,
        datasets: Dict[str, pd.DataFrame],
        target_date: date,
        high_risk_customer_ids: Optional[List[str]] = None,
    ) -> MetricResult:
        """
        MRR from customers flagged as High or Critical churn risk.

        When called from the pipeline, high_risk_customer_ids is populated by
        the ChurnRiskEngine result. When called standalone (e.g. in tests), it
        falls back to Past Due customers as a proxy.
        """
        subs = datasets["subscriptions"]
        if high_risk_customer_ids:
            at_risk = subs[
                subs["customer_id"].isin(high_risk_customer_ids)
                & subs["status"].isin(_ACTIVE_STATUSES)
            ]
        else:
            # Fallback proxy: Past Due subscriptions represent known revenue risk
            at_risk = subs[subs["status"] == "Past Due"]

        value = float(at_risk["monthly_price"].sum())
        return MetricResult(
            metric_name="revenue_at_risk",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=(
                f"MRR from {at_risk['customer_id'].nunique()} at-risk customers: "
                f"${value:,.2f}."
            ),
        )

    # ------------------------------------------------------------------
    # Product KPIs
    # ------------------------------------------------------------------

    def calculate_activation_rate(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """Customers with >5 cumulative key_actions / total customers."""
        customers = datasets["customers"]
        usage = datasets["product_usage"]

        total = len(customers)
        if total == 0:
            return MetricResult(
                metric_name="activation_rate",
                value=0.0,
                date_calculated=target_date,
                grain="overall",
                explanation="No customers to evaluate.",
            )

        user_actions = (
            usage.groupby("customer_id")["key_actions"].sum()
        )
        activated_count = int(
            (user_actions > _ACTIVATION_KEY_ACTION_THRESHOLD).sum()
        )
        value = _safe_divide(activated_count, total)
        return MetricResult(
            metric_name="activation_rate",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=(
                f"{activated_count}/{total} customers exceeded "
                f"{_ACTIVATION_KEY_ACTION_THRESHOLD} cumulative key actions."
            ),
        )

    def calculate_usage_frequency(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """Mean monthly logins per active customer."""
        customers = datasets["customers"]
        usage = datasets["product_usage"]

        active_ids = self._active_customer_ids(datasets)
        active_usage = usage[usage["customer_id"].isin(active_ids)]

        if active_usage.empty:
            return MetricResult(
                metric_name="usage_frequency",
                value=0.0,
                date_calculated=target_date,
                grain="overall",
                explanation="No active customer usage records found.",
            )

        monthly_logins = (
            active_usage.groupby("customer_id")["logins"].mean()
        )
        value = float(monthly_logins.mean())
        return MetricResult(
            metric_name="usage_frequency",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=f"Mean monthly logins per active customer: {value:.1f}.",
        )

    def calculate_key_action_rate(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """Total key_actions / total logins for active customers."""
        customers = datasets["customers"]
        usage = datasets["product_usage"]

        active_ids = self._active_customer_ids(datasets)
        active_usage = usage[usage["customer_id"].isin(active_ids)]

        total_logins = float(active_usage["logins"].sum())
        total_key_actions = float(active_usage["key_actions"].sum())
        value = _safe_divide(total_key_actions, total_logins)
        return MetricResult(
            metric_name="key_action_rate",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=(
                f"{total_key_actions:,.0f} key actions / {total_logins:,.0f} logins "
                f"= {value:.2f} actions per login."
            ),
        )

    def calculate_engagement_drop_rate(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """
        Proportion of active customers whose logins in the most recent period
        are below 20% of their own 3-period average — indicating significant drop.
        """
        customers = datasets["customers"]
        usage = datasets["product_usage"]

        active_ids = self._active_customer_ids(datasets)
        active_usage = usage[usage["customer_id"].isin(active_ids)].copy()

        if active_usage.empty or "date" not in active_usage.columns:
            return MetricResult(
                metric_name="engagement_drop_rate",
                value=0.0,
                date_calculated=target_date,
                grain="overall",
                explanation="Insufficient usage data to calculate engagement drop rate.",
            )

        active_usage["date"] = pd.to_datetime(active_usage["date"])
        active_usage = active_usage.sort_values("date")

        # Use the last 3 distinct period dates available
        periods = sorted(active_usage["date"].unique())
        if len(periods) < 2:
            return MetricResult(
                metric_name="engagement_drop_rate",
                value=0.0,
                date_calculated=target_date,
                grain="overall",
                explanation="Not enough historical periods to calculate drop rate.",
            )

        latest_period = periods[-1]
        baseline_periods = periods[-4:-1]  # up to 3 prior periods

        latest = (
            active_usage[active_usage["date"] == latest_period]
            .groupby("customer_id")["logins"].sum()
        )
        baseline = (
            active_usage[active_usage["date"].isin(baseline_periods)]
            .groupby("customer_id")["logins"].mean()
        )

        comparison = pd.DataFrame({"latest": latest, "baseline": baseline}).dropna()
        if comparison.empty:
            return MetricResult(
                metric_name="engagement_drop_rate",
                value=0.0,
                date_calculated=target_date,
                grain="overall",
                explanation="No overlapping customers between latest and baseline periods.",
            )

        dropped = (comparison["latest"] < comparison["baseline"] * 0.20).sum()
        value = _safe_divide(int(dropped), len(comparison))
        return MetricResult(
            metric_name="engagement_drop_rate",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=(
                f"{dropped}/{len(comparison)} active customers showed "
                ">80% drop vs 3-period baseline."
            ),
        )

    def calculate_feature_adoption_proxy(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """Mean features_used per active customer per usage record."""
        customers = datasets["customers"]
        usage = datasets["product_usage"]

        active_ids = self._active_customer_ids(datasets)
        active_usage = usage[usage["customer_id"].isin(active_ids)]

        if active_usage.empty:
            return MetricResult(
                metric_name="feature_adoption_proxy",
                value=0.0,
                date_calculated=target_date,
                grain="overall",
                explanation="No active customer usage records found.",
            )

        value = float(active_usage["features_used"].mean())
        return MetricResult(
            metric_name="feature_adoption_proxy",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=f"Mean features used per active customer session: {value:.1f}.",
        )

    # ------------------------------------------------------------------
    # Customer KPIs
    # ------------------------------------------------------------------

    def calculate_customer_churn_rate(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """Customers with Canceled subscriptions / total customers."""
        customers = datasets["customers"]
        subs = datasets["subscriptions"]

        total = len(customers)
        churned_ids = subs.loc[subs["status"] == "Canceled", "customer_id"].unique()
        churned = len(churned_ids)
        value = _safe_divide(churned, total)
        return MetricResult(
            metric_name="customer_churn_rate",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=f"{churned} churned customers / {total} total = {value:.1%}.",
        )

    def calculate_retention_rate(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """1 minus customer_churn_rate."""
        churn_result = self.calculate_customer_churn_rate(datasets, target_date)
        value = max(0.0, 1.0 - churn_result.value)
        return MetricResult(
            metric_name="retention_rate",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=f"1 - churn_rate ({churn_result.value:.1%}) = {value:.1%}.",
        )

    def calculate_average_nps(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """Mean of all NPS scores."""
        nps = datasets["nps_scores"]
        scores = pd.to_numeric(nps["score"], errors="coerce").dropna()

        if scores.empty:
            return MetricResult(
                metric_name="average_nps",
                value=0.0,
                date_calculated=target_date,
                grain="overall",
                explanation="No NPS scores available.",
            )

        value = float(scores.mean())
        return MetricResult(
            metric_name="average_nps",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=f"Mean NPS across {len(scores)} responses: {value:.2f}.",
        )

    def calculate_support_burden(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """Mean number of support tickets per active customer."""
        customers = datasets["customers"]
        tickets = datasets["support_tickets"]

        active_count = len(self._active_customer_ids(datasets))
        if active_count == 0:
            return MetricResult(
                metric_name="support_burden",
                value=0.0,
                date_calculated=target_date,
                grain="overall",
                explanation="No active customers.",
            )

        total_tickets = len(tickets)
        value = _safe_divide(total_tickets, active_count)
        return MetricResult(
            metric_name="support_burden",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=(
                f"{total_tickets} total tickets / {active_count} active customers "
                f"= {value:.2f} tickets per customer."
            ),
        )

    def calculate_time_to_activation(
        self, datasets: Dict[str, pd.DataFrame], target_date: date
    ) -> MetricResult:
        """
        Mean days from signup_date to first usage record with key_actions > 0.
        Only considers customers who have at least one qualifying usage record.
        """
        customers = datasets["customers"]
        usage = datasets["product_usage"]

        usage = usage.copy()
        usage["date"] = pd.to_datetime(usage["date"])
        customers = customers.copy()
        customers["signup_date"] = pd.to_datetime(customers["signup_date"])

        # Find first date each customer had key_actions > 0
        qualifying = usage[usage["key_actions"] > 0]
        first_action = (
            qualifying.groupby("customer_id")["date"].min().reset_index()
        )
        first_action.columns = ["customer_id", "first_action_date"]

        merged = customers[["customer_id", "signup_date"]].merge(
            first_action, on="customer_id", how="inner"
        )

        if merged.empty:
            return MetricResult(
                metric_name="time_to_activation",
                value=0.0,
                date_calculated=target_date,
                grain="overall",
                explanation="No customers have completed a key action.",
            )

        merged["days_to_activation"] = (
            merged["first_action_date"] - merged["signup_date"]
        ).dt.days
        # Drop negative values (data artifact) and compute mean
        valid = merged[merged["days_to_activation"] >= 0]
        value = float(valid["days_to_activation"].mean()) if not valid.empty else 0.0
        return MetricResult(
            metric_name="time_to_activation",
            value=value,
            date_calculated=target_date,
            grain="overall",
            explanation=(
                f"Mean days to first key action across {len(valid)} activated "
                f"customers: {value:.1f} days."
            ),
        )
