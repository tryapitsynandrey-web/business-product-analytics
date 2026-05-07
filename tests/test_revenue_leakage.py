"""
Tests for src/core/revenue_leakage.py

All tests use in-memory DataFrames. No iterrows() in the engine is verified
indirectly through correctness tests on aggregated outputs.
"""

from __future__ import annotations

import pytest
import pandas as pd

from core.revenue_leakage import RevenueLeakageEngine


@pytest.fixture()
def engine() -> RevenueLeakageEngine:
    return RevenueLeakageEngine()


def _base_subscriptions(statuses: list, prices: list, customer_ids: list) -> pd.DataFrame:
    return pd.DataFrame({
        "subscription_id": [f"S{i}" for i in range(len(statuses))],
        "customer_id": customer_ids,
        "status": statuses,
        "monthly_price": prices,
        "plan": ["Basic"] * len(statuses),
    })


def _base_transactions(statuses: list, amounts: list, customer_ids: list) -> pd.DataFrame:
    return pd.DataFrame({
        "transaction_id": [f"TX{i}" for i in range(len(statuses))],
        "customer_id": customer_ids,
        "subscription_id": [f"S{i}" for i in range(len(statuses))],
        "amount": amounts,
        "status": statuses,
    })


class TestFailedPaymentLeakage:
    def test_failed_payment_produces_leakage_record(self, engine):
        subs = _base_subscriptions(["Active"], [100.0], ["C1"])
        txns = _base_transactions(["Failed"], [100.0], ["C1"])
        usage = pd.DataFrame(columns=["customer_id", "logins"])

        leakages = engine.detect_leakage(
            {"subscriptions": subs, "transactions": txns, "product_usage": usage}
        )
        failed = [l for l in leakages if l["leakage_type"] == "Failed Payment"]
        assert len(failed) == 1
        assert failed[0]["customer_id"] == "C1"
        assert failed[0]["estimated_revenue_loss"] == pytest.approx(100.0)

    def test_failed_payment_loss_is_summed_per_customer(self, engine):
        # Two failed transactions for the same customer
        subs = _base_subscriptions(["Active"], [200.0], ["C1"])
        txns = _base_transactions(
            ["Failed", "Failed"], [100.0, 100.0], ["C1", "C1"]
        )
        usage = pd.DataFrame(columns=["customer_id", "logins"])

        leakages = engine.detect_leakage(
            {"subscriptions": subs, "transactions": txns, "product_usage": usage}
        )
        failed = [l for l in leakages if l["leakage_type"] == "Failed Payment"]
        assert len(failed) == 1
        assert failed[0]["estimated_revenue_loss"] == pytest.approx(200.0)

    def test_successful_transactions_produce_no_leakage(self, engine):
        subs = _base_subscriptions(["Active"], [100.0], ["C1"])
        txns = _base_transactions(["Success"], [100.0], ["C1"])
        usage = pd.DataFrame(columns=["customer_id", "logins"])

        leakages = engine.detect_leakage(
            {"subscriptions": subs, "transactions": txns, "product_usage": usage}
        )
        failed = [l for l in leakages if l["leakage_type"] == "Failed Payment"]
        assert failed == []


class TestRefundLeakage:
    def test_refund_produces_leakage_record(self, engine):
        subs = _base_subscriptions(["Active"], [100.0], ["C1"])
        txns = _base_transactions(["Refunded"], [100.0], ["C1"])
        usage = pd.DataFrame(columns=["customer_id", "logins"])

        leakages = engine.detect_leakage(
            {"subscriptions": subs, "transactions": txns, "product_usage": usage}
        )
        refunds = [l for l in leakages if l["leakage_type"] == "Refund"]
        assert len(refunds) == 1
        assert refunds[0]["estimated_revenue_loss"] == pytest.approx(100.0)


class TestUnpaidActiveSubscription:
    def test_past_due_subscription_flagged(self, engine):
        subs = _base_subscriptions(["Past Due"], [300.0], ["C1"])
        txns = pd.DataFrame(columns=["transaction_id", "customer_id", "subscription_id", "amount", "status"])
        usage = pd.DataFrame(columns=["customer_id", "logins"])

        leakages = engine.detect_leakage(
            {"subscriptions": subs, "transactions": txns, "product_usage": usage}
        )
        unpaid = [l for l in leakages if l["leakage_type"] == "Unpaid Active Subscription"]
        assert len(unpaid) == 1
        assert unpaid[0]["estimated_revenue_loss"] == pytest.approx(300.0)

    def test_active_subscription_not_flagged_as_unpaid(self, engine):
        subs = _base_subscriptions(["Active"], [200.0], ["C1"])
        txns = pd.DataFrame(columns=["transaction_id", "customer_id", "subscription_id", "amount", "status"])
        usage = pd.DataFrame(columns=["customer_id", "logins"])

        leakages = engine.detect_leakage(
            {"subscriptions": subs, "transactions": txns, "product_usage": usage}
        )
        unpaid = [l for l in leakages if l["leakage_type"] == "Unpaid Active Subscription"]
        assert unpaid == []


class TestActiveUsageWithoutBilling:
    def test_usage_without_active_subscription_flagged(self, engine):
        # C2 has usage but only a Canceled subscription
        subs = _base_subscriptions(
            ["Active", "Canceled"], [100.0, 200.0], ["C1", "C2"]
        )
        txns = pd.DataFrame(columns=["transaction_id", "customer_id", "subscription_id", "amount", "status"])
        usage = pd.DataFrame({
            "usage_id": ["U1", "U2"],
            "customer_id": ["C1", "C2"],
            "logins": [10, 5],
        })

        leakages = engine.detect_leakage(
            {"subscriptions": subs, "transactions": txns, "product_usage": usage}
        )
        unbilled = [l for l in leakages if l["leakage_type"] == "Active Usage Without Billing"]
        assert any(l["customer_id"] == "C2" for l in unbilled)

    def test_billable_customer_with_usage_not_flagged(self, engine):
        subs = _base_subscriptions(["Active"], [100.0], ["C1"])
        txns = pd.DataFrame(columns=["transaction_id", "customer_id", "subscription_id", "amount", "status"])
        usage = pd.DataFrame({"usage_id": ["U1"], "customer_id": ["C1"], "logins": [10]})

        leakages = engine.detect_leakage(
            {"subscriptions": subs, "transactions": txns, "product_usage": usage}
        )
        unbilled = [l for l in leakages if l["leakage_type"] == "Active Usage Without Billing"]
        assert unbilled == []


class TestOutputStructure:
    def test_all_leakage_records_have_required_fields(self, engine):
        subs = _base_subscriptions(["Past Due", "Canceled"], [100.0, 50.0], ["C1", "C2"])
        txns = _base_transactions(["Failed"], [100.0], ["C1"])
        usage = pd.DataFrame({"usage_id": ["U1"], "customer_id": ["C2"], "logins": [10]})

        leakages = engine.detect_leakage(
            {"subscriptions": subs, "transactions": txns, "product_usage": usage}
        )
        required_fields = {
            "leakage_type", "customer_id", "estimated_revenue_loss",
            "affected_customers", "recommended_action", "evidence",
        }
        for record in leakages:
            assert required_fields.issubset(record.keys()), (
                f"Missing fields in leakage record: {required_fields - record.keys()}"
            )

    def test_no_transactions_produces_no_payment_leakage(self, engine):
        subs = _base_subscriptions(["Active"], [100.0], ["C1"])
        txns = pd.DataFrame(columns=["transaction_id", "customer_id", "subscription_id", "amount", "status"])
        usage = pd.DataFrame(columns=["customer_id", "logins"])

        leakages = engine.detect_leakage(
            {"subscriptions": subs, "transactions": txns, "product_usage": usage}
        )
        payment_types = {"Failed Payment", "Refund"}
        payment_leakages = [l for l in leakages if l["leakage_type"] in payment_types]
        assert payment_leakages == []
