from core.root_cause_analysis import RootCauseAnalysisEngine


def test_metric_change_cause():
    engine = RootCauseAnalysisEngine()
    causes = engine.analyze_metric_change("MRR", 90, 100, {"new_sales": -0.5, "churn": 0.05})
    assert len(causes) == 1
    assert "new_sales" in causes[0]["cause"]


def test_metric_change_ignores_zero_baseline_and_small_changes():
    engine = RootCauseAnalysisEngine()

    assert engine.analyze_metric_change("MRR", 100, 0, {"sales": 0.5}) == []
    assert engine.analyze_metric_change("MRR", 102, 100, {"sales": 0.5}) == []


def test_churn_driver_detection():
    engine = RootCauseAnalysisEngine()
    causes = engine.analyze_churn_drivers(
        {"churn_rate": 0.15}, support_summary={"support_burden": 3.0}
    )
    assert len(causes) == 1
    assert causes[0]["cause"] == "High support burden"


def test_churn_driver_detection_covers_low_churn_usage_and_nps_paths():
    engine = RootCauseAnalysisEngine()

    assert engine.analyze_churn_drivers({"churn_rate": 0.01}) == []
    causes = engine.analyze_churn_drivers(
        {"churn_rate": 0.08},
        usage_summary={"engagement_drop_rate": 0.3},
        nps_summary={"average_nps": 5},
    )
    assert {cause["cause"] for cause in causes} == {"Engagement drop", "Low NPS"}


def test_revenue_drop_driver_detection():
    engine = RootCauseAnalysisEngine()
    causes = engine.analyze_revenue_drop_drivers(
        {"revenue_growth_rate": -0.15}, refund_summary={"refund_rate": 0.10}
    )
    assert len(causes) == 1
    assert causes[0]["severity"] == "Critical"


def test_revenue_drop_driver_detection_covers_non_drop_failed_payments_and_fallback():
    engine = RootCauseAnalysisEngine()

    assert engine.analyze_revenue_drop_drivers({"revenue_growth_rate": 0.01}) == []
    failed = engine.analyze_revenue_drop_drivers(
        {"revenue_growth_rate": -0.05},
        failed_payment_summary={"failed_payment_rate": 0.09},
    )
    fallback = engine.analyze_revenue_drop_drivers({"revenue_growth_rate": -0.05})

    assert failed[0]["cause"] == "Failed payments"
    assert fallback[0]["cause"] == "Contraction or Churn"


def test_ranking_by_severity():
    engine = RootCauseAnalysisEngine()
    causes = [
        {"severity": "Low", "confidence": "High"},
        {"severity": "Critical", "confidence": "Low"},
        {"severity": "High", "confidence": "High"},
    ]
    ranked = engine.rank_root_causes(causes)
    assert ranked[0]["severity"] == "Critical"
    assert ranked[1]["severity"] == "High"
    assert ranked[2]["severity"] == "Low"


def test_missing_optional_data_safe_handling():
    engine = RootCauseAnalysisEngine()
    causes = engine.analyze_churn_drivers({"churn_rate": 0.08})
    assert len(causes) == 1
    assert causes[0]["cause"] == "Unknown churn driver"


def test_build_root_cause_summary_returns_ranked_dataframe():
    engine = RootCauseAnalysisEngine()
    causes = [
        {
            "cause": "Low",
            "evidence": "x",
            "severity": "Low",
            "confidence": "High",
            "recommended_investigation": "a",
        },
        {
            "cause": "Critical",
            "evidence": "y",
            "severity": "Critical",
            "confidence": "Low",
            "recommended_investigation": "b",
        },
    ]

    df = engine.build_root_cause_summary(causes)

    assert df["cause"].tolist() == ["Critical", "Low"]


def test_empty_root_cause_summary_returns_expected_schema():
    engine = RootCauseAnalysisEngine()

    df = engine.build_root_cause_summary([])

    assert list(df.columns) == [
        "cause",
        "evidence",
        "severity",
        "confidence",
        "recommended_investigation",
    ]
