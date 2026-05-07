"""
Customer360Engine — builds a unified analytical profile per customer.

Design contract:
    - One output row per customer (based on the customers dataset).
    - All signals are computed from pre-loaded DataFrames; no external calls.
    - Churn risk and recommendations are joined in from engine outputs.
    - Missing data (NPS, usage) is handled explicitly with safe defaults.
    - Usage trend is computed per-customer from multi-period usage data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from models.risk_profile import ChurnRiskProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Usage trend thresholds
# ---------------------------------------------------------------------------
_TREND_INCREASE_THRESHOLD: float = 0.10   # >10% increase
_TREND_DECLINE_THRESHOLD: float = -0.10   # >10% decline


# ---------------------------------------------------------------------------
# Customer360Engine
# ---------------------------------------------------------------------------

class Customer360Engine:
    """
    Builds a Customer 360 analytical view from pipeline outputs.

    Parameters
    ----------
    datasets : dict of DataFrames — all loaded datasets.
    risk_profiles : list of ChurnRiskProfile — from ChurnRiskEngine.
    recommendations : list of dicts — from RecommendationEngine.
    """

    def __init__(
        self,
        datasets: Dict[str, pd.DataFrame],
        risk_profiles: List[ChurnRiskProfile],
        recommendations: List[Dict[str, Any]],
    ) -> None:
        self._datasets = datasets
        self._risk_profiles = risk_profiles
        self._recommendations = recommendations

        # Index risk profiles by customer_id for O(1) join
        self._risk_index: Dict[str, ChurnRiskProfile] = {
            p.customer_id: p for p in risk_profiles
        }
        # Index first recommendation per customer
        self._rec_index: Dict[str, Dict[str, Any]] = {}
        for rec in recommendations:
            cid = str(rec.get("customer_id", ""))
            if cid and cid not in self._rec_index:
                self._rec_index[cid] = rec

    # ------------------------------------------------------------------
    # Main builder
    # ------------------------------------------------------------------

    def build_customer_360_view(self) -> pd.DataFrame:
        """
        Compute and return a DataFrame with one row per customer containing
        all 360 fields.
        """
        customers = self._datasets["customers"].copy()
        subs = self._datasets["subscriptions"]
        transactions = self._datasets["transactions"]
        usage = self._datasets["product_usage"]
        tickets = self._datasets["support_tickets"]
        nps = self._datasets["nps_scores"]

        # ── Subscription fields ───────────────────────────────────────
        active_subs = subs[subs["status"].isin({"Active", "Past Due"})]
        mrr_by_cust = (
            active_subs.groupby("customer_id")["monthly_price"]
            .sum()
            .reset_index()
            .rename(columns={"monthly_price": "current_mrr"})
        )
        plan_by_cust = (
            subs.sort_values("status")
            .groupby("customer_id")["plan"]
            .first()
            .reset_index()
        )
        status_by_cust = (
            subs.sort_values("status")
            .groupby("customer_id")["status"]
            .first()
            .reset_index()
            .rename(columns={"status": "subscription_status"})
        )

        # ── Total revenue ─────────────────────────────────────────────
        success_tx = transactions[transactions["status"] == "Success"]
        total_revenue = (
            success_tx.groupby("customer_id")["amount"]
            .sum()
            .reset_index()
            .rename(columns={"amount": "total_revenue"})
        )

        # ── Usage signals ─────────────────────────────────────────────
        usage_freq = (
            usage.groupby("customer_id")["logins"]
            .mean()
            .reset_index()
            .rename(columns={"logins": "latest_usage_frequency"})
        )
        usage_trend_series = self.calculate_usage_trend(usage)

        # ── NPS ───────────────────────────────────────────────────────
        if not nps.empty and "date" in nps.columns:
            nps_copy = nps.copy()
            nps_copy["date"] = pd.to_datetime(nps_copy["date"], errors="coerce")
            latest_nps = (
                nps_copy.sort_values("date")
                .groupby("customer_id")["score"]
                .last()
                .reset_index()
                .rename(columns={"score": "latest_nps"})
            )
        else:
            latest_nps = pd.DataFrame(columns=["customer_id", "latest_nps"])

        # ── Support ───────────────────────────────────────────────────
        ticket_counts = (
            tickets.groupby("customer_id")
            .size()
            .reset_index(name="support_ticket_count")
        )

        # ── Failed payments ───────────────────────────────────────────
        failed_tx = transactions[transactions["status"] == "Failed"]
        failed_counts = (
            failed_tx.groupby("customer_id")
            .size()
            .reset_index(name="failed_payment_count")
        )

        # ── Assemble ──────────────────────────────────────────────────
        df = customers[["customer_id", "segment", "is_active", "signup_date"]].copy()

        # Add country / acquisition_channel if present
        if "country" in customers.columns:
            df["country"] = customers["country"]
        else:
            df["country"] = "Unknown"
        if "acquisition_channel" in customers.columns:
            df["acquisition_channel"] = customers["acquisition_channel"]
        else:
            df["acquisition_channel"] = "Unknown"

        df = df.merge(plan_by_cust, on="customer_id", how="left")
        df = df.merge(status_by_cust, on="customer_id", how="left")
        df = df.merge(mrr_by_cust, on="customer_id", how="left")
        df = df.merge(total_revenue, on="customer_id", how="left")
        df = df.merge(usage_freq, on="customer_id", how="left")
        df = df.merge(usage_trend_series, on="customer_id", how="left")
        df = df.merge(latest_nps, on="customer_id", how="left")
        df = df.merge(ticket_counts, on="customer_id", how="left")
        df = df.merge(failed_counts, on="customer_id", how="left")

        # Fill numeric defaults
        numeric_fill = {
            "current_mrr": 0.0,
            "total_revenue": 0.0,
            "latest_usage_frequency": 0.0,
            "support_ticket_count": 0,
            "failed_payment_count": 0,
        }
        df = df.fillna(numeric_fill)

        # ── Attach churn risk ─────────────────────────────────────────
        df = self.attach_churn_risk(df)

        # ── Attach recommendations ────────────────────────────────────
        df = self.attach_recommendations(df)

        # ── Summarise health ─────────────────────────────────────────
        df = self.summarize_customer_health(df)

        logger.info("Built Customer 360 view for %d customers.", len(df))
        return df

    # ------------------------------------------------------------------
    # Signal helpers
    # ------------------------------------------------------------------

    def calculate_usage_trend(self, usage: pd.DataFrame) -> pd.DataFrame:
        """
        Compute a per-customer usage trend label by comparing the most recent
        period's logins to the prior period.

        Labels: Increasing | Stable | Declining | No Data
        """
        if usage.empty or "date" not in usage.columns:
            empty = usage[["customer_id"]].drop_duplicates() if not usage.empty else pd.DataFrame(columns=["customer_id"])
            empty["usage_trend"] = "No Data"
            return empty

        u = usage.copy()
        u["date"] = pd.to_datetime(u["date"], errors="coerce")
        u = u.sort_values("date")

        periods = sorted(u["date"].unique())
        if len(periods) < 2:
            result = u[["customer_id"]].drop_duplicates()
            result["usage_trend"] = "No Data"
            return result

        latest = periods[-1]
        previous = periods[-2]

        latest_logins = (
            u[u["date"] == latest]
            .groupby("customer_id")["logins"]
            .sum()
        )
        prev_logins = (
            u[u["date"] == previous]
            .groupby("customer_id")["logins"]
            .sum()
        )

        comparison = pd.DataFrame({
            "latest": latest_logins,
            "previous": prev_logins,
        }).fillna(0)

        import numpy as np

        prev = comparison["previous"]
        latest = comparison["latest"]

        change = (latest - prev) / prev.replace(0, np.nan)

        conditions = [
            (prev == 0) & (latest == 0),
            (prev == 0) & (latest > 0),
            change > _TREND_INCREASE_THRESHOLD,
            change < _TREND_DECLINE_THRESHOLD
        ]
        choices = [
            "No Data",
            "Increasing",
            "Increasing",
            "Declining"
        ]

        comparison["usage_trend"] = np.select(conditions, choices, default="Stable")
        return comparison[["usage_trend"]].reset_index().rename(
            columns={"index": "customer_id"}
        )

    def attach_churn_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        """Join churn risk fields onto the 360 DataFrame from the risk index."""
        df = df.copy()
        df["churn_risk_score"] = df["customer_id"].map(
            lambda cid: self._risk_index[cid].risk_score
            if cid in self._risk_index else 0.0
        )
        df["churn_risk_band"] = df["customer_id"].map(
            lambda cid: self._risk_index[cid].risk_band.value
            if cid in self._risk_index else "Low"
        )
        df["revenue_at_risk"] = df["customer_id"].map(
            lambda cid: self._risk_index[cid].revenue_at_risk
            if cid in self._risk_index else 0.0
        )
        df["main_driver"] = df["customer_id"].map(
            lambda cid: self._risk_index[cid].drivers[0]
            if cid in self._risk_index and self._risk_index[cid].drivers
            else "None"
        )
        return df

    def attach_recommendations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add the highest-priority recommended_action per customer."""
        df = df.copy()
        df["recommended_action"] = df["customer_id"].map(
            lambda cid: self._rec_index[cid].get("recommendation_title", "Monitor")
            if cid in self._rec_index else "No action required"
        )
        return df

    def summarize_customer_health(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Derive a simplified health_status column from churn_risk_band.
        Keeps logic in one place and avoids scattering thresholds.
        """
        _band_to_health = {
            "Critical": "Critical",
            "High": "At Risk",
            "Medium": "Watch",
            "Low": "Healthy",
        }
        df = df.copy()
        df["health_status"] = df["churn_risk_band"].map(
            lambda b: _band_to_health.get(str(b), "Healthy")
        )
        return df
