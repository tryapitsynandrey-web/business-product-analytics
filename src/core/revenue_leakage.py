"""
RevenueLeakageEngine — vectorized detection of revenue leakage events.

Design contract:
    - All detection is vectorized using Pandas; no iterrows().
    - Each leakage type produces a standardised dict with the fields:
        leakage_type, customer_id, estimated_revenue_loss,
        affected_customers, recommended_action, evidence.
    - Returns a flat list of dicts (one per affected customer/subscription).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)

# Billing statuses that represent a legitimate, revenue-generating subscription
_BILLABLE_STATUSES = frozenset({"Active", "Past Due"})


class RevenueLeakageEngine:
    """
    Detects and quantifies revenue leakage using vectorized Pandas operations.
    """

    def detect_leakage(self, datasets: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """
        Run all leakage detectors and return a combined flat list.

        Parameters
        ----------
        datasets : dict
            Must contain 'subscriptions', 'transactions', and 'product_usage'.

        Returns
        -------
        List[dict]
            One dict per leakage event.
        """
        subs = datasets["subscriptions"]
        transactions = datasets["transactions"]
        usage = datasets.get("product_usage", pd.DataFrame())

        results: List[Dict[str, Any]] = []
        results.extend(self._detect_failed_payments(transactions))
        results.extend(self._detect_refunds(transactions))
        results.extend(self._detect_unpaid_active_subscriptions(subs))
        results.extend(self._detect_active_usage_without_billing(subs, usage))

        logger.info(
            "Revenue leakage detection complete: %d event(s) across %d type(s).",
            len(results),
            len({r["leakage_type"] for r in results}),
        )
        return results

    # ------------------------------------------------------------------
    # Individual detectors — all vectorized
    # ------------------------------------------------------------------

    def _detect_failed_payments(self, transactions: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Flag every Failed transaction as a leakage event.

        Evidence: transaction_id and amount.
        """
        failed = transactions[transactions["status"] == "Failed"].copy()
        if failed.empty:
            return []

        # Aggregate per customer for the summary record
        agg = (
            failed.groupby("customer_id")
            .agg(
                estimated_revenue_loss=("amount", "sum"),
                event_count=("transaction_id", "count"),
            )
            .reset_index()
        )

        results = []
        for row in agg.to_dict("records"):
            loss = float(row["estimated_revenue_loss"])
            results.append(
                {
                    "leakage_type": "Failed Payment",
                    "customer_id": row["customer_id"],
                    "estimated_revenue_loss": loss,
                    "estimated_loss": loss,  # backward-compat alias
                    "affected_customers": 1,
                    "recommended_action": (
                        "Trigger automated dunning sequence: retry payment, "
                        "then request updated payment method."
                    ),
                    "evidence": (
                        f"{int(row['event_count'])} failed transaction(s) totalling ${loss:,.2f}."
                    ),
                }
            )
        return results

    def _detect_refunds(self, transactions: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Flag every Refunded transaction as realised revenue leakage.

        Evidence: transaction_id and refunded amount.
        """
        refunded = transactions[transactions["status"] == "Refunded"].copy()
        if refunded.empty:
            return []

        agg = (
            refunded.groupby("customer_id")
            .agg(
                estimated_revenue_loss=("amount", "sum"),
                event_count=("transaction_id", "count"),
            )
            .reset_index()
        )

        results = []
        for row in agg.to_dict("records"):
            loss = float(row["estimated_revenue_loss"])
            results.append(
                {
                    "leakage_type": "Refund",
                    "customer_id": row["customer_id"],
                    "estimated_revenue_loss": loss,
                    "estimated_loss": loss,
                    "affected_customers": 1,
                    "recommended_action": (
                        "Review refund reason. If product issue, escalate to "
                        "engineering. If billing error, correct and re-invoice."
                    ),
                    "evidence": (
                        f"{int(row['event_count'])} refunded transaction(s) totalling ${loss:,.2f}."
                    ),
                }
            )
        return results

    def _detect_unpaid_active_subscriptions(self, subs: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Flag subscriptions in Past Due status — service is being delivered but
        not paid for.

        Evidence: subscription_id and monthly_price.
        """
        past_due = subs[subs["status"] == "Past Due"].copy()
        if past_due.empty:
            return []

        results = []
        for row in past_due.to_dict("records"):
            loss = float(row["monthly_price"])
            results.append(
                {
                    "leakage_type": "Unpaid Active Subscription",
                    "customer_id": row["customer_id"],
                    "estimated_revenue_loss": loss,
                    "estimated_loss": loss,
                    "affected_customers": 1,
                    "recommended_action": (
                        "Escalate to finance for account hold review. "
                        "Send formal payment demand notice."
                    ),
                    "evidence": (
                        f"Subscription {row['subscription_id']} is Past Due — "
                        f"${loss:,.2f}/month outstanding."
                    ),
                }
            )
        return results

    def _detect_active_usage_without_billing(
        self, subs: pd.DataFrame, usage: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """
        Identify customers who have product usage records but whose subscription
        status is Canceled or Expired — i.e., they are using the product without
        a valid billing relationship.

        Evidence: presence in product_usage but absent from billable subscriptions.
        """
        if usage.empty:
            return []

        billable_customers = set(subs.loc[subs["status"].isin(_BILLABLE_STATUSES), "customer_id"])
        usage_customers = set(usage["customer_id"].unique())

        # Customers with usage but no billable subscription. Sort explicitly so
        # generated CSV and report artifacts remain reproducible across runs.
        unbilled = sorted(usage_customers - billable_customers)

        if not unbilled:
            return []

        # Estimate loss: we can only flag the anomaly; MRR unknown without active sub
        # Use a zero estimate to be conservative — the flag itself is the value
        results = []
        for cid in unbilled:
            results.append(
                {
                    "leakage_type": "Active Usage Without Billing",
                    "customer_id": cid,
                    "estimated_revenue_loss": 0.0,
                    "estimated_loss": 0.0,
                    "affected_customers": 1,
                    "recommended_action": (
                        "Audit account access. Revoke product access if subscription "
                        "is Canceled/Expired and no grace period applies."
                    ),
                    "evidence": (
                        f"Customer {cid} has product usage records but no Active "
                        "or Past Due subscription found."
                    ),
                }
            )
        return results
