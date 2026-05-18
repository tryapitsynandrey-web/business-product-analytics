import pandas as pd
import pytest
from core.churn_analysis import ChurnAnalysisEngine


@pytest.fixture
def subscriptions():
    return pd.DataFrame(
        [
            {
                "customer_id": "1",
                "status": "Active",
                "plan": "Pro",
                "start_date": "2023-01-01",
                "end_date": None,
            },
            {
                "customer_id": "2",
                "status": "Canceled",
                "plan": "Basic",
                "start_date": "2023-01-15",
                "end_date": "2023-03-15",
            },
            {
                "customer_id": "3",
                "status": "Past Due",
                "plan": "Pro",
                "start_date": "2023-02-01",
                "end_date": None,
            },
        ]
    )


@pytest.fixture
def customers():
    return pd.DataFrame(
        [
            {"customer_id": "1", "segment": "Enterprise"},
            {"customer_id": "2", "segment": "SMB"},
            {"customer_id": "3", "segment": "Mid-Market"},
        ]
    )


def test_churn_rate_calculation():
    engine = ChurnAnalysisEngine()
    rate = engine.calculate_churn_rate(80, 20)
    assert rate == 0.2
    assert engine.calculate_churn_rate(0, 0) == 0.0


def test_retention_rate_calculation():
    engine = ChurnAnalysisEngine()
    rate = engine.calculate_retention_rate(80, 20)
    assert rate == 0.8
    assert engine.calculate_retention_rate(0, 0) == 0.0


def test_summarize_churn_health(subscriptions):
    engine = ChurnAnalysisEngine()
    summary = engine.summarize_churn_health(subscriptions)
    assert summary["active_customers"] == 2
    assert summary["churned_customers"] == 1
    assert summary["churn_rate"] == pytest.approx(0.333, rel=1e-2)


def test_churn_by_plan(subscriptions):
    engine = ChurnAnalysisEngine()
    df = engine.analyze_churn_by_plan(subscriptions)
    pro = df[df["plan"] == "Pro"].iloc[0]
    assert pro["active_customers"] == 2
    assert pro["churned_customers"] == 0
    basic = df[df["plan"] == "Basic"].iloc[0]
    assert basic["active_customers"] == 0
    assert basic["churned_customers"] == 1


def test_churn_by_month_counts_active_and_churned_customers(subscriptions):
    engine = ChurnAnalysisEngine()
    df = engine.analyze_churn_by_month(subscriptions)

    march = df[df["period"] == "2023-03"].iloc[0]
    assert march["active_customers"] >= 3
    assert march["churned_customers"] == 1
    assert march["churn_rate"] == pytest.approx(0.25)


def test_churn_by_segment_includes_unknown_segment_for_unmatched_customer(subscriptions, customers):
    engine = ChurnAnalysisEngine()
    extra = pd.DataFrame(
        [
            {
                "customer_id": "4",
                "status": "Canceled",
                "plan": "Pro",
                "start_date": "2023-03-01",
                "end_date": "2023-04-01",
            }
        ]
    )
    df = engine.analyze_churn_by_segment(
        pd.concat([subscriptions, extra], ignore_index=True), customers
    )

    unknown = df[df["segment"] == "Unknown"].iloc[0]
    assert unknown["churned_customers"] == 1
    assert unknown["retention_rate"] == 0.0


def test_zero_active_customers():
    engine = ChurnAnalysisEngine()
    df = pd.DataFrame(
        [
            {
                "customer_id": "1",
                "status": "Canceled",
                "plan": "Basic",
                "start_date": "2023-01-15",
                "end_date": "2023-03-15",
            }
        ]
    )
    summary = engine.summarize_churn_health(df)
    assert summary["active_customers"] == 0
    assert summary["churned_customers"] == 1
    assert summary["churn_rate"] == 1.0


def test_empty_input():
    engine = ChurnAnalysisEngine()
    df = pd.DataFrame()
    summary = engine.summarize_churn_health(df)
    assert summary["active_customers"] == 0
    assert summary["churn_rate"] == 0.0

    assert engine.analyze_churn_by_month(df).empty
    assert engine.analyze_churn_by_segment(df, df).empty
    assert engine.analyze_churn_by_plan(df).empty


def test_churn_by_month_handles_all_missing_start_dates():
    engine = ChurnAnalysisEngine()
    df = pd.DataFrame(
        [
            {
                "customer_id": "1",
                "status": "Active",
                "plan": "Pro",
                "start_date": None,
                "end_date": None,
            }
        ]
    )

    assert engine.analyze_churn_by_month(df).empty


def test_summarize_churn_health_status_bands():
    engine = ChurnAnalysisEngine()

    def records(active_count, canceled_count):
        rows = [
            {"customer_id": f"a{i}", "status": "Active", "plan": "Pro"}
            for i in range(active_count)
        ]
        rows.extend(
            {"customer_id": f"c{i}", "status": "Canceled", "plan": "Pro"}
            for i in range(canceled_count)
        )
        return pd.DataFrame(rows)

    assert engine.summarize_churn_health(records(96, 4))["status"] == "Healthy"
    assert engine.summarize_churn_health(records(95, 5))["status"] == "Watch"
    assert engine.summarize_churn_health(records(92, 8))["status"] == "Risk"
    assert engine.summarize_churn_health(records(80, 20))["status"] == "Critical"
