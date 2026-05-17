from core.root_cause_analysis import RootCauseAnalysisEngine


def test_metric_change_cause():
    engine = RootCauseAnalysisEngine()
    causes = engine.analyze_metric_change("MRR", 90, 100, {"new_sales": -0.5, "churn": 0.05})
    assert len(causes) == 1
    assert "new_sales" in causes[0]["cause"]


def test_churn_driver_detection():
    engine = RootCauseAnalysisEngine()
    causes = engine.analyze_churn_drivers(
        {"churn_rate": 0.15}, support_summary={"support_burden": 3.0}
    )
    assert len(causes) == 1
    assert causes[0]["cause"] == "High support burden"


def test_revenue_drop_driver_detection():
    engine = RootCauseAnalysisEngine()
    causes = engine.analyze_revenue_drop_drivers(
        {"revenue_growth_rate": -0.15}, refund_summary={"refund_rate": 0.10}
    )
    assert len(causes) == 1
    assert causes[0]["severity"] == "Critical"


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
