"""
Tests for src/core/kpi_engine.py

All tests use in-memory DataFrames. No external data or services.
"""

from __future__ import annotations

import pytest
import pandas as pd
from datetime import date, timedelta

from core.kpi_engine import KPIEngine
from core.metric_governance import MetricGovernance


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def governance() -> MetricGovernance:
    return MetricGovernance()


@pytest.fixture()
def engine(governance) -> KPIEngine:
    return KPIEngine(governance)


def _make_datasets(
    num_customers: int = 3,
    active_flags: list | None = None,
    subscription_statuses: list | None = None,
    monthly_prices: list | None = None,
    plans: list | None = None,
    nps_scores: list | None = None,
    logins: list | None = None,
    key_actions: list | None = None,
    features_used: list | None = None,
    ticket_counts_per_customer: int = 0,
    failed_tx_counts_per_customer: int = 0,
) -> dict:
    """Build a minimal set of DataFrames for KPI testing."""
    if active_flags is None:
        active_flags = [True] * num_customers
    if subscription_statuses is None:
        subscription_statuses = ["Active"] * num_customers
    if monthly_prices is None:
        monthly_prices = [100.0] * num_customers
    if plans is None:
        plans = ["Basic"] * num_customers

    customer_ids = [f"C{i}" for i in range(num_customers)]
    today = date.today()
    signup_dates = [today - timedelta(days=30 * (i + 1)) for i in range(num_customers)]

    customers = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "is_active": active_flags,
            "signup_date": signup_dates,
            "segment": ["SMB"] * num_customers,
        }
    )

    subscriptions = pd.DataFrame(
        {
            "subscription_id": [f"S{i}" for i in range(num_customers)],
            "customer_id": customer_ids,
            "status": subscription_statuses,
            "monthly_price": monthly_prices,
            "plan": plans,
        }
    )

    # product_usage — one record per customer
    usage_logins = logins if logins is not None else [20] * num_customers
    usage_key_actions = key_actions if key_actions is not None else [10] * num_customers
    usage_features = features_used if features_used is not None else [3] * num_customers
    product_usage = pd.DataFrame(
        {
            "usage_id": [f"U{i}" for i in range(num_customers)],
            "customer_id": customer_ids,
            "date": [pd.Timestamp(today - timedelta(days=10))] * num_customers,
            "logins": usage_logins,
            "key_actions": usage_key_actions,
            "features_used": usage_features,
        }
    )

    # nps_scores
    if nps_scores is not None:
        nps_df = pd.DataFrame(
            {
                "score_id": [f"N{i}" for i in range(len(nps_scores))],
                "customer_id": customer_ids[: len(nps_scores)],
                "date": [pd.Timestamp(today - timedelta(days=5))] * len(nps_scores),
                "score": nps_scores,
            }
        )
    else:
        nps_df = pd.DataFrame(columns=["score_id", "customer_id", "date", "score"])

    # support_tickets
    ticket_rows = []
    for cid in customer_ids:
        for j in range(ticket_counts_per_customer):
            ticket_rows.append(
                {"ticket_id": f"T_{cid}_{j}", "customer_id": cid, "status": "Closed"}
            )
    support_tickets = (
        pd.DataFrame(ticket_rows)
        if ticket_rows
        else pd.DataFrame(columns=["ticket_id", "customer_id", "status"])
    )

    # transactions
    tx_rows = []
    for cid in customer_ids:
        for j in range(failed_tx_counts_per_customer):
            tx_rows.append(
                {
                    "transaction_id": f"TX_{cid}_{j}",
                    "customer_id": cid,
                    "subscription_id": f"S{cid}",
                    "amount": 100.0,
                    "status": "Failed",
                }
            )
    transactions = (
        pd.DataFrame(tx_rows)
        if tx_rows
        else pd.DataFrame(
            columns=["transaction_id", "customer_id", "subscription_id", "amount", "status"]
        )
    )

    return {
        "customers": customers,
        "subscriptions": subscriptions,
        "product_usage": product_usage,
        "nps_scores": nps_df,
        "support_tickets": support_tickets,
        "transactions": transactions,
        "acquisition_channels": pd.DataFrame(
            {"channel_name": ["Direct"], "cost_per_acquisition": [0.0]}
        ),
        "targets": pd.DataFrame(
            {"metric_name": ["MRR"], "target_value": [100000.0], "date": [today]}
        ),
    }


# ---------------------------------------------------------------------------
# MRR
# ---------------------------------------------------------------------------


class TestMRR:
    def test_mrr_sums_active_and_past_due_only(self, engine):
        datasets = _make_datasets(
            num_customers=3,
            subscription_statuses=["Active", "Past Due", "Canceled"],
            monthly_prices=[100.0, 200.0, 300.0],
        )
        result = engine.calculate_mrr(datasets, date.today())
        # Only Active ($100) + Past Due ($200) = $300
        assert result.value == pytest.approx(300.0)
        assert result.metric_name == "monthly_recurring_revenue"

    def test_mrr_zero_when_all_canceled(self, engine):
        datasets = _make_datasets(
            subscription_statuses=["Canceled", "Canceled", "Canceled"],
            monthly_prices=[100.0, 200.0, 300.0],
        )
        result = engine.calculate_mrr(datasets, date.today())
        assert result.value == pytest.approx(0.0)

    def test_mrr_zero_with_no_subscriptions(self, engine):
        datasets = _make_datasets(num_customers=0)
        result = engine.calculate_mrr(datasets, date.today())
        assert result.value == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# ARPU
# ---------------------------------------------------------------------------


class TestARPU:
    def test_arpu_is_mrr_divided_by_paying_customers(self, engine):
        datasets = _make_datasets(
            num_customers=2,
            subscription_statuses=["Active", "Active"],
            monthly_prices=[200.0, 400.0],
        )
        result = engine.calculate_arpu(datasets, date.today())
        # MRR = 600, paying customers = 2 → ARPU = 300
        assert result.value == pytest.approx(300.0)
        assert result.metric_name == "average_revenue_per_user"

    def test_arpu_zero_when_no_active_customers(self, engine):
        datasets = _make_datasets(
            num_customers=1,
            subscription_statuses=["Canceled"],
            monthly_prices=[500.0],
        )
        result = engine.calculate_arpu(datasets, date.today())
        assert result.value == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Churn Rate
# ---------------------------------------------------------------------------


class TestChurnRate:
    def test_churn_rate_correct_proportion(self, engine):
        datasets = _make_datasets(
            num_customers=4,
            subscription_statuses=["Active", "Canceled", "Canceled", "Active"],
        )
        result = engine.calculate_customer_churn_rate(datasets, date.today())
        # 2 churned / 4 total = 0.5
        assert result.value == pytest.approx(0.5)
        assert result.metric_name == "customer_churn_rate"

    def test_churn_rate_zero_when_all_active(self, engine):
        datasets = _make_datasets(
            num_customers=2,
            subscription_statuses=["Active", "Active"],
        )
        result = engine.calculate_customer_churn_rate(datasets, date.today())
        assert result.value == pytest.approx(0.0)

    def test_churn_rate_zero_customers_safe(self, engine):
        datasets = _make_datasets(num_customers=0)
        result = engine.calculate_customer_churn_rate(datasets, date.today())
        assert result.value == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# NPS Average
# ---------------------------------------------------------------------------


class TestAverageNPS:
    def test_nps_mean_of_scores(self, engine):
        datasets = _make_datasets(num_customers=3, nps_scores=[8, 4, 10])
        result = engine.calculate_average_nps(datasets, date.today())
        assert result.value == pytest.approx(22 / 3)
        assert result.metric_name == "average_nps"

    def test_nps_zero_when_no_scores(self, engine):
        datasets = _make_datasets(num_customers=2, nps_scores=None)
        result = engine.calculate_average_nps(datasets, date.today())
        assert result.value == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Support Burden
# ---------------------------------------------------------------------------


class TestSupportBurden:
    def test_support_burden_mean_tickets_per_active_customer(self, engine):
        datasets = _make_datasets(
            num_customers=2,
            active_flags=[True, True],
            ticket_counts_per_customer=3,
        )
        result = engine.calculate_support_burden(datasets, date.today())
        # 6 tickets / 2 active customers = 3.0
        assert result.value == pytest.approx(3.0)
        assert result.metric_name == "support_burden"

    def test_support_burden_zero_when_no_active_customers(self, engine):
        datasets = _make_datasets(
            num_customers=2,
            active_flags=[False, False],
            ticket_counts_per_customer=5,
        )
        result = engine.calculate_support_burden(datasets, date.today())
        assert result.value == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Activation Rate
# ---------------------------------------------------------------------------


class TestActivationRate:
    def test_activation_rate_customers_above_threshold(self, engine):
        # Threshold = 5 key actions.  Two customers above, one below.
        datasets = _make_datasets(
            num_customers=3,
            key_actions=[10, 0, 20],
        )
        result = engine.calculate_activation_rate(datasets, date.today())
        assert result.value == pytest.approx(2 / 3)
        assert result.metric_name == "activation_rate"

    def test_activation_rate_zero_customers_safe(self, engine):
        datasets = _make_datasets(num_customers=0)
        result = engine.calculate_activation_rate(datasets, date.today())
        assert result.value == pytest.approx(0.0)

    def test_activation_rate_zero_when_none_activated(self, engine):
        datasets = _make_datasets(num_customers=3, key_actions=[0, 0, 0])
        result = engine.calculate_activation_rate(datasets, date.today())
        assert result.value == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Revenue at Risk
# ---------------------------------------------------------------------------


class TestRevenueAtRisk:
    def test_revenue_at_risk_sums_active_mrr_of_at_risk_customers(self, engine):
        datasets = _make_datasets(
            num_customers=3,
            subscription_statuses=["Active", "Active", "Active"],
            monthly_prices=[100.0, 200.0, 300.0],
        )
        # Only C0 and C1 are "at risk"
        result = engine.calculate_revenue_at_risk(
            datasets, date.today(), high_risk_customer_ids=["C0", "C1"]
        )
        assert result.value == pytest.approx(300.0)
        assert result.metric_name == "revenue_at_risk"

    def test_revenue_at_risk_zero_when_no_high_risk_customers(self, engine):
        datasets = _make_datasets(num_customers=2)
        result = engine.calculate_revenue_at_risk(datasets, date.today(), high_risk_customer_ids=[])
        # Falls back to Past Due proxy
        assert result.value == pytest.approx(0.0)


def test_kpi_engine_supported_metrics():
    from core.kpi_engine import KPIEngine

    supported = KPIEngine.get_supported_metrics()
    assert "monthly_recurring_revenue" in supported
    assert supported["monthly_recurring_revenue"] == "calculate_mrr"


def test_calculate_kpis_skips_metrics_that_fail_governance(monkeypatch, engine):
    def fake_validate_metric(metric_name, datasets):
        return metric_name != "monthly_recurring_revenue"

    monkeypatch.setattr(engine.governance, "validate_metric", fake_validate_metric)

    results = engine.calculate_kpis(_make_datasets(), date.today())

    assert "monthly_recurring_revenue" not in {result.metric_name for result in results}


def test_calculate_kpis_logs_and_continues_when_calculator_raises(monkeypatch, engine):
    def boom(datasets, target_date):
        raise RuntimeError("broken calculator")

    monkeypatch.setattr(engine, "calculate_mrr", boom)

    results = engine.calculate_kpis(_make_datasets(), date.today())

    assert "monthly_recurring_revenue" not in {result.metric_name for result in results}
    assert results


def test_calculate_kpis_skips_none_calculator_results(monkeypatch, engine):
    monkeypatch.setattr(engine, "calculate_mrr", lambda datasets, target_date: None)

    results = engine.calculate_kpis(_make_datasets(), date.today())

    assert "monthly_recurring_revenue" not in {result.metric_name for result in results}
    assert results


def test_usage_and_feature_metrics_return_zero_without_active_usage(engine):
    datasets = _make_datasets(num_customers=2, active_flags=[False, False])

    usage = engine.calculate_usage_frequency(datasets, date.today())
    features = engine.calculate_feature_adoption_proxy(datasets, date.today())

    assert usage.value == 0.0
    assert features.value == 0.0


def test_engagement_drop_rate_insufficient_data_paths(engine):
    datasets = _make_datasets(num_customers=1)
    no_date = _make_datasets(num_customers=1)
    no_date["product_usage"] = no_date["product_usage"].drop(columns=["date"])

    no_date_result = engine.calculate_engagement_drop_rate(no_date, date.today())
    single_period_result = engine.calculate_engagement_drop_rate(datasets, date.today())

    assert no_date_result.value == 0.0
    assert single_period_result.value == 0.0


def test_engagement_drop_rate_returns_zero_without_overlapping_customers(engine):
    today = pd.Timestamp(date.today())
    datasets = _make_datasets(num_customers=2)
    datasets["product_usage"] = pd.DataFrame(
        [
            {
                "usage_id": "U1",
                "customer_id": "C0",
                "date": today,
                "logins": 10,
                "key_actions": 1,
                "features_used": 1,
            },
            {
                "usage_id": "U2",
                "customer_id": "C1",
                "date": today - pd.Timedelta(days=30),
                "logins": 10,
                "key_actions": 1,
                "features_used": 1,
            },
        ]
    )

    result = engine.calculate_engagement_drop_rate(datasets, date.today())

    assert result.value == 0.0
    assert "No overlapping customers" in result.explanation


def test_time_to_activation_zero_when_no_customer_has_key_action(engine):
    datasets = _make_datasets(num_customers=2, key_actions=[0, 0])

    result = engine.calculate_time_to_activation(datasets, date.today())

    assert result.value == 0.0
