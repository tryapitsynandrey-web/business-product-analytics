import pytest
from core.health_score import ProductHealthScoreEngine


def test_status_mapping():
    engine = ProductHealthScoreEngine()
    assert engine.assign_status(95) == "Healthy"
    assert engine.assign_status(75) == "Stable"
    assert engine.assign_status(60) == "Watch"
    assert engine.assign_status(40) == "Risk"
    assert engine.assign_status(10) == "Critical"


def test_inverse_scoring():
    engine = ProductHealthScoreEngine()
    # Inverse: lower is better. Churn healthy <= 0.05, risk >= 0.15
    score = engine.calculate_area_score(0.02, 0.05, 0.15, inverse=True)
    assert score == 100.0

    score_mid = engine.calculate_area_score(0.10, 0.05, 0.15, inverse=True)
    assert score_mid == pytest.approx(50.0, rel=1e-5)


def test_product_health_score_output():
    engine = ProductHealthScoreEngine()
    metrics = {"retention_rate": 0.95, "churn_rate": 0.02}
    res = engine.calculate_product_health_score(metrics)
    assert len(res) == 2
    assert res[0]["status"] == "Healthy"
    assert res[1]["status"] == "Healthy"


def test_missing_metrics_safely_handled():
    engine = ProductHealthScoreEngine()
    df = engine.build_health_score_table({"retention_rate": 0.95})
    assert len(df) == 1
    assert df["area"].iloc[0] == "Customer Retention"


def test_critical_metric_produces_critical_status():
    engine = ProductHealthScoreEngine()
    df = engine.build_health_score_table({"churn_rate": 0.50})
    assert df["status"].iloc[0] == "Critical"
    assert df["score"].iloc[0] == 0.0


def test_business_health_summary_scores_revenue_leakage_and_data_quality():
    engine = ProductHealthScoreEngine()
    rows = engine.calculate_business_health_summary(
        {
            "revenue_growth_rate": 0.12,
            "revenue_leakage_ratio": 0.04,
            "data_quality_score": 0.98,
        }
    )

    by_area = {row["area"]: row for row in rows}
    assert by_area["Revenue Growth"]["status"] == "Healthy"
    assert by_area["Revenue Leakage"]["score"] == pytest.approx(75.0)
    assert by_area["Data Quality"]["status"] == "Healthy"
