import pandas as pd
from app.ui_helpers_filter import (
    get_filter_options,
    filter_dataframe_by_values,
    filter_dataframe_by_search,
    filter_dataframe_by_numeric_range,
    get_quick_view_options,
    describe_quick_view,
    apply_quick_view,
    prepare_metric_chart_data,
    prepare_status_counts,
    prepare_category_counts,
    get_executive_metric_values,
)


def test_get_filter_options():
    df = pd.DataFrame({"col": ["A", "B", "A", None, "C"]})
    assert get_filter_options(df, "col") == ["A", "B", "C"]
    assert get_filter_options(df, "missing") == []
    assert get_filter_options(None, "col") == []
    assert get_filter_options(pd.DataFrame(), "col") == []


def test_filter_dataframe_by_values():
    df = pd.DataFrame({"col": ["A", "B", "C"]})
    filtered = filter_dataframe_by_values(df, "col", ["A", "C"])
    assert len(filtered) == 2
    assert "B" not in filtered["col"].values

    # Empty values should return original
    assert len(filter_dataframe_by_values(df, "col", [])) == 3

    # Missing col should return original
    assert len(filter_dataframe_by_values(df, "missing", ["A"])) == 3

    # None handling
    assert filter_dataframe_by_values(None, "col", ["A"]).empty


def test_filter_dataframe_by_search_matches_any_selected_column():
    df = pd.DataFrame(
        [
            {"customer_id": "C1", "segment": "SMB", "recommended_action": "Call customer"},
            {"customer_id": "C2", "segment": "Enterprise", "recommended_action": "Monitor"},
        ]
    )

    filtered = filter_dataframe_by_search(
        df,
        "call",
        ["customer_id", "segment", "recommended_action"],
    )

    assert len(filtered) == 1
    assert filtered.iloc[0]["customer_id"] == "C1"
    assert len(filter_dataframe_by_search(df, "", ["customer_id"])) == 2
    assert len(filter_dataframe_by_search(df, "SMB", ["segment"])) == 1
    assert len(filter_dataframe_by_search(df, "missing", ["unknown"])) == 2
    assert filter_dataframe_by_search(None, "C1", ["customer_id"]).empty


def test_filter_dataframe_by_numeric_range():
    df = pd.DataFrame({"val": [1, 5, 10, 15]})

    filtered = filter_dataframe_by_numeric_range(df, "val", 5, 12)
    assert len(filtered) == 2
    assert 1 not in filtered["val"].values

    filtered_min = filter_dataframe_by_numeric_range(df, "val", 10, None)
    assert len(filtered_min) == 2

    filtered_max = filter_dataframe_by_numeric_range(df, "val", None, 5)
    assert len(filtered_max) == 2

    # Missing col returns original
    assert len(filter_dataframe_by_numeric_range(df, "missing", 1, 10)) == 4

    # None handling
    assert filter_dataframe_by_numeric_range(None, "val", 1, 10).empty


def test_get_quick_view_options_and_description():
    assert "Revenue Risk" in get_quick_view_options("top_actions")
    assert get_quick_view_options("unknown") == ["All"]
    assert describe_quick_view("High Priority") == (
        "Critical and high-priority work, sorted by priority score."
    )


def test_apply_quick_view_high_priority_filters_and_sorts():
    df = pd.DataFrame(
        [
            {"id": "low", "priority_band": "Low", "priority_score": 10},
            {"id": "critical", "priority_band": "Critical", "priority_score": 80},
            {"id": "high", "priority_band": "High", "priority_score": 90},
        ]
    )

    filtered = apply_quick_view(df, "High Priority")

    assert filtered["id"].tolist() == ["high", "critical"]


def test_apply_quick_view_revenue_risk_keeps_largest_exposure():
    df = pd.DataFrame(
        [
            {"id": "a", "estimated_revenue_impact": 10},
            {"id": "b", "estimated_revenue_impact": 20},
            {"id": "c", "estimated_revenue_impact": 30},
            {"id": "d", "estimated_revenue_impact": 100},
        ]
    )

    filtered = apply_quick_view(df, "Revenue Risk")

    assert filtered["id"].tolist() == ["d"]


def test_apply_quick_view_revenue_risk_fallbacks_return_input():
    no_numeric = pd.DataFrame([{"id": "a", "name": "No numeric exposure"}])
    zero_numeric = pd.DataFrame(
        [
            {"id": "a", "estimated_revenue_impact": 0},
            {"id": "b", "estimated_revenue_impact": 0},
        ]
    )

    assert apply_quick_view(no_numeric, "Revenue Risk")["id"].tolist() == ["a"]
    assert apply_quick_view(zero_numeric, "Revenue Risk")["id"].tolist() == ["a", "b"]


def test_apply_quick_view_retention_focus_uses_risk_or_keywords():
    risk_df = pd.DataFrame(
        [
            {"id": "safe", "churn_risk_band": "Low", "churn_risk_score": 0.1},
            {"id": "risk", "churn_risk_band": "High", "churn_risk_score": 0.9},
        ]
    )
    keyword_df = pd.DataFrame(
        [
            {"id": "growth", "recommendation_title": "Expansion offer"},
            {"id": "save", "recommendation_title": "Retention call"},
        ]
    )

    assert apply_quick_view(risk_df, "Retention Focus")["id"].tolist() == ["risk"]
    assert apply_quick_view(keyword_df, "Retention Focus")["id"].tolist() == ["save"]


def test_apply_quick_view_quick_wins_and_governance_issues():
    work_df = pd.DataFrame(
        [
            {"id": "large", "effort_level": "High", "priority_score": 100},
            {"id": "small", "effort_level": "Low", "priority_score": 50},
        ]
    )
    lineage_df = pd.DataFrame(
        [
            {"id": "ok", "lineage_status": "Healthy"},
            {"id": "issue", "lineage_status": "Missing"},
        ]
    )

    assert apply_quick_view(work_df, "Quick Wins")["id"].tolist() == ["small"]
    assert apply_quick_view(lineage_df, "Governance Issues")["id"].tolist() == ["issue"]


def test_apply_quick_view_additional_presets():
    df = pd.DataFrame(
        [
            {
                "id": "a",
                "suggested_owner": "Sales",
                "priority_score": 20,
                "confidence_level": "Low",
                "usage_trend": "Flat",
                "risk_band": "Critical",
            },
            {
                "id": "b",
                "suggested_owner": "CS",
                "priority_score": 80,
                "confidence_level": "High",
                "usage_trend": "Increasing",
                "risk_band": "High",
            },
        ]
    )

    assert apply_quick_view(df, "All Actions")["id"].tolist() == ["a", "b"]
    assert apply_quick_view(df, "Owner Queue")["id"].tolist() == ["b", "a"]
    assert apply_quick_view(df, "Expansion Watch")["id"].tolist() == ["b"]
    assert apply_quick_view(df, "Critical Only")["id"].tolist() == ["a"]
    assert apply_quick_view(df, "High Confidence")["id"].tolist() == ["b"]
    assert apply_quick_view(df, "Unknown Preset")["id"].tolist() == ["a", "b"]
    assert apply_quick_view(None, "All").empty


def test_apply_quick_view_score_fallbacks():
    priority_df = pd.DataFrame(
        [
            {"id": "low", "priority_score": 10},
            {"id": "medium", "priority_score": 50},
            {"id": "top", "priority_score": 100},
        ]
    )
    confidence_df = pd.DataFrame(
        [
            {"id": "low", "confidence_weight": 0.2},
            {"id": "top", "confidence_weight": 0.9},
        ]
    )
    expansion_df = pd.DataFrame(
        [
            {"id": "small", "current_mrr": 10},
            {"id": "large", "current_mrr": 100},
        ]
    )

    assert apply_quick_view(priority_df, "High Priority")["id"].tolist() == ["top"]
    assert apply_quick_view(confidence_df, "High Confidence")["id"].tolist() == ["top"]
    assert apply_quick_view(expansion_df, "Expansion Watch")["id"].tolist() == ["large"]


def test_apply_quick_view_governance_and_owner_review_fallbacks():
    no_status_df = pd.DataFrame([{"id": "a", "metric_name": "m1"}])
    owner_df = pd.DataFrame(
        [
            {"id": "b", "metric_owner": "Data", "lineage_status": "Missing"},
            {"id": "a", "metric_owner": "Analytics", "lineage_status": "Healthy"},
        ]
    )

    assert apply_quick_view(no_status_df, "Governance Issues")["id"].tolist() == ["a"]
    assert apply_quick_view(owner_df, "Owner Review")["id"].tolist() == ["a", "b"]


def test_prepare_metric_chart_data():
    df = pd.DataFrame({"metric_name": ["A", "B", "C"], "value": [10.5, "invalid", 20]})

    chart_data = prepare_metric_chart_data(df, "metric_name", "value")
    assert len(chart_data) == 2
    assert "B" not in chart_data.index
    assert chart_data.loc["A", "value"] == 10.5

    assert prepare_metric_chart_data(None).empty
    assert prepare_metric_chart_data(df, "missing_col").empty
    assert prepare_metric_chart_data(
        pd.DataFrame({"metric_name": ["A"], "value": ["invalid"]})
    ).empty


def test_prepare_status_counts():
    df = pd.DataFrame({"status": ["Healthy", "Healthy", "Warning", "Critical"]})
    counts = prepare_status_counts(df, "status")

    assert len(counts) == 3
    assert counts.loc["Healthy", "count"] == 2
    assert counts.loc["Warning", "count"] == 1

    assert prepare_status_counts(None).empty
    assert prepare_status_counts(df, "missing_col").empty


def test_prepare_category_counts():
    df = pd.DataFrame({"category": ["Cat1", "Cat2", "Cat1"]})
    counts = prepare_category_counts(df, "category")

    assert len(counts) == 2
    assert counts.loc["Cat1", "count"] == 2

    assert prepare_category_counts(None).empty


def test_get_executive_metric_values_uses_canonical_names():
    df = pd.DataFrame(
        [
            {"metric_name": "monthly_recurring_revenue", "value": 1000.0},
            {"metric_name": "customer_churn_rate", "value": 0.05},
            {"metric_name": "average_revenue_per_user", "value": 100.0},
            {"metric_name": "revenue_at_risk", "value": 250.0},
        ]
    )

    values = get_executive_metric_values(df)

    assert values["monthly_recurring_revenue"] == 1000.0
    assert values["customer_churn_rate"] == 0.05
    assert values["average_revenue_per_user"] == 100.0
    assert values["revenue_at_risk"] == 250.0
