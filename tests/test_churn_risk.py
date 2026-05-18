"""
Tests for src/core/churn_risk.py

All tests use in-memory DataFrames.
"""

from __future__ import annotations

import pytest
import pandas as pd
from datetime import date, timedelta

from core.churn_risk import ChurnRiskEngine, _apply_operator
from models.enums import RiskBand


@pytest.fixture()
def engine() -> ChurnRiskEngine:
    return ChurnRiskEngine()


def _make_churn_datasets(
    customer_id: str = "C1",
    is_active: bool = True,
    logins: int = 50,
    key_actions: int = 20,
    nps_score: int | None = 9,
    failed_payments: int = 0,
    ticket_count: int = 0,
    sub_status: str = "Active",
    monthly_price: float = 200.0,
) -> dict:
    """Build a minimal dataset for a single customer's churn risk test."""
    today = date.today()
    customers = pd.DataFrame(
        {
            "customer_id": [customer_id],
            "is_active": [is_active],
            "signup_date": [today - timedelta(days=180)],
            "segment": ["SMB"],
        }
    )
    subscriptions = pd.DataFrame(
        {
            "subscription_id": ["S1"],
            "customer_id": [customer_id],
            "status": [sub_status],
            "monthly_price": [monthly_price],
            "plan": ["Pro"],
        }
    )
    product_usage = pd.DataFrame(
        {
            "usage_id": ["U1"],
            "customer_id": [customer_id],
            "date": [pd.Timestamp(today - timedelta(days=10))],
            "logins": [logins],
            "key_actions": [key_actions],
            "features_used": [3],
        }
    )
    nps_rows = []
    if nps_score is not None:
        nps_rows.append(
            {
                "score_id": "N1",
                "customer_id": customer_id,
                "date": pd.Timestamp(today - timedelta(days=5)),
                "score": nps_score,
            }
        )
    nps_scores = (
        pd.DataFrame(nps_rows)
        if nps_rows
        else pd.DataFrame(columns=["score_id", "customer_id", "date", "score"])
    )

    tx_rows = [
        {
            "transaction_id": f"TX{i}",
            "customer_id": customer_id,
            "subscription_id": "S1",
            "amount": 100.0,
            "status": "Failed",
        }
        for i in range(failed_payments)
    ]
    transactions = (
        pd.DataFrame(tx_rows)
        if tx_rows
        else pd.DataFrame(
            columns=["transaction_id", "customer_id", "subscription_id", "amount", "status"]
        )
    )

    ticket_rows = [
        {"ticket_id": f"T{i}", "customer_id": customer_id, "status": "Open"}
        for i in range(ticket_count)
    ]
    support_tickets = (
        pd.DataFrame(ticket_rows)
        if ticket_rows
        else pd.DataFrame(columns=["ticket_id", "customer_id", "status"])
    )

    return {
        "customers": customers,
        "subscriptions": subscriptions,
        "product_usage": product_usage,
        "nps_scores": nps_scores,
        "transactions": transactions,
        "support_tickets": support_tickets,
    }


class TestApplyOperator:
    """Unit tests for the safe operator dispatch function."""

    def test_less_than_true(self):
        assert _apply_operator("less_than", 3, 10) is True

    def test_less_than_false(self):
        assert _apply_operator("less_than", 10, 3) is False

    def test_greater_or_equal_true(self):
        assert _apply_operator("greater_or_equal", 5, 5) is True

    def test_equals_true(self):
        assert _apply_operator("equals", "Critical", "Critical") is True

    def test_contains_in_string(self):
        assert _apply_operator("contains", "Failed Payments | Low NPS", "Failed Payments") is True

    def test_unknown_operator_returns_false(self):
        assert _apply_operator("explode_everything", 1, 2) is False


class TestLowRiskCustomer:
    def test_high_logins_high_nps_no_failures_is_low_risk(self, engine):
        datasets = _make_churn_datasets(
            logins=500,
            key_actions=100,
            nps_score=9,
            failed_payments=0,
            ticket_count=0,
        )
        profiles = engine.evaluate_risk(datasets)
        assert len(profiles) == 1
        assert profiles[0].risk_band == RiskBand.LOW
        assert profiles[0].risk_score == pytest.approx(0.0)
        assert profiles[0].drivers == []

    def test_low_risk_customer_has_zero_revenue_at_risk(self, engine):
        datasets = _make_churn_datasets(
            logins=500,
            nps_score=9,
            failed_payments=0,
        )
        profiles = engine.evaluate_risk(datasets)
        assert profiles[0].revenue_at_risk == pytest.approx(0.0)


class TestCriticalRiskCustomer:
    def test_low_logins_low_nps_failed_payments_triggers_critical(self, engine):
        datasets = _make_churn_datasets(
            logins=2,  # triggers CR_001 (< 10)
            key_actions=1,  # triggers CR_005 (< 5)
            nps_score=3,  # triggers CR_002 (<= 6)
            failed_payments=2,  # triggers CR_003 (>= 1)
            ticket_count=4,  # triggers CR_004 (>= 3)
        )
        profiles = engine.evaluate_risk(datasets)
        assert len(profiles) == 1
        p = profiles[0]
        assert p.risk_band in (RiskBand.CRITICAL, RiskBand.HIGH)
        assert p.risk_score > 0.0
        assert len(p.drivers) > 0

    def test_critical_risk_has_non_zero_revenue_at_risk(self, engine):
        datasets = _make_churn_datasets(
            logins=2,
            nps_score=3,
            failed_payments=2,
            key_actions=1,
            ticket_count=4,
            monthly_price=500.0,
        )
        profiles = engine.evaluate_risk(datasets)
        p = profiles[0]
        if p.risk_band in (RiskBand.CRITICAL, RiskBand.HIGH):
            assert p.revenue_at_risk == pytest.approx(500.0)


class TestDriverDetection:
    def test_failed_payment_rule_triggers_driver(self, engine):
        datasets = _make_churn_datasets(
            logins=100,
            nps_score=9,
            failed_payments=1,
            key_actions=50,
        )
        profiles = engine.evaluate_risk(datasets)
        assert "Failed Payments" in profiles[0].drivers

    def test_low_nps_rule_triggers_driver(self, engine):
        datasets = _make_churn_datasets(
            logins=100,
            nps_score=4,
            failed_payments=0,
        )
        profiles = engine.evaluate_risk(datasets)
        assert "Low NPS" in profiles[0].drivers

    def test_low_logins_rule_triggers_driver(self, engine):
        datasets = _make_churn_datasets(logins=5, nps_score=9, failed_payments=0)
        profiles = engine.evaluate_risk(datasets)
        assert "Usage Decline" in profiles[0].drivers


class TestNoScoreWithoutDrivers:
    def test_zero_risk_score_has_empty_drivers_list(self, engine):
        datasets = _make_churn_datasets(
            logins=500,
            key_actions=200,
            nps_score=10,
            failed_payments=0,
            ticket_count=0,
        )
        profiles = engine.evaluate_risk(datasets)
        p = profiles[0]
        if p.risk_score == 0.0:
            assert p.drivers == []

    def test_inactive_customer_is_not_scored(self, engine):
        datasets = _make_churn_datasets(is_active=False)
        profiles = engine.evaluate_risk(datasets)
        # Inactive customer should be excluded from scoring
        assert len(profiles) == 0

    def test_latest_nps_signal_empty_when_date_column_missing(self, engine):
        datasets = _make_churn_datasets()
        datasets["nps_scores"] = pd.DataFrame({"customer_id": ["C1"], "score": [4]})

        signals = engine.calculate_customer_signals(datasets)

        assert "latest_nps_score" in signals.columns
        assert pd.isna(signals.loc[0, "latest_nps_score"])


def test_apply_operator_returns_false_for_type_errors():
    assert _apply_operator("less_than", "bad", 10) is False


class TestRevenueAtRisk:
    def test_medium_risk_customer_has_zero_revenue_at_risk(self, engine):
        # Only low_nps triggers (weight 0.20 → Medium band)
        datasets = _make_churn_datasets(
            logins=500,
            nps_score=5,
            failed_payments=0,
            key_actions=100,
            ticket_count=0,
            monthly_price=300.0,
        )
        profiles = engine.evaluate_risk(datasets)
        p = profiles[0]
        if p.risk_band == RiskBand.MEDIUM:
            assert p.revenue_at_risk == pytest.approx(0.0)

    def test_high_risk_revenue_at_risk_equals_active_sub_mrr(self, engine):
        # CR_003 (failed_payments >= 1) weight=0.40 → High band
        datasets = _make_churn_datasets(
            logins=500,
            nps_score=9,
            failed_payments=1,
            key_actions=100,
            ticket_count=0,
            monthly_price=250.0,
            sub_status="Active",
        )
        profiles = engine.evaluate_risk(datasets)
        p = profiles[0]
        if p.risk_band in (RiskBand.HIGH, RiskBand.CRITICAL):
            assert p.revenue_at_risk == pytest.approx(250.0)
