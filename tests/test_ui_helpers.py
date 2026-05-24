import pandas as pd
import pytest
from app.ui_helpers import (
    format_currency,
    format_number,
    format_percentage,
    safe_metric_value,
    select_metric_value,
    status_badge_text,
    format_file_size,
    format_timestamp,
    format_duration,
    build_data_freshness_summary,
    build_custom_scenario_analysis,
    db_status_label,
    safe_dataframe_empty_message,
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
    prepare_display_dataframe,
    get_executive_metric_values,
    determine_business_status,
    prepare_top_actions,
    build_top_actions_overview,
    prepare_action_priority_queue,
    build_decision_brief,
    decision_brief_to_markdown,
    prepare_owner_workload_summary,
    quality_status_for_score,
    build_data_quality_overview,
    prepare_quality_dimension_summary,
    prepare_quality_issue_queue,
    filter_customer_360,
    build_customer_360_overview,
    prepare_customer_360_queue,
    build_customer_profile_summary,
    summarize_filter_state,
    dataframe_to_csv_bytes,
    build_export_filename,
)


def test_format_currency():
    assert format_currency(1234.56) == "$1,234.56"
    assert format_currency(0) == "$0.00"
    assert format_currency("100.5") == "$100.50"
    assert format_currency("invalid") == "N/A"
    assert format_currency(None) == "N/A"


def test_format_percentage():
    assert format_percentage(0.155) == "15.5%"
    assert format_percentage(0) == "0.0%"
    assert format_percentage("0.5") == "50.0%"
    assert format_percentage("invalid") == "N/A"
    assert format_percentage(None) == "N/A"


def test_format_number():
    assert format_number(1234) == "1,234"
    assert format_number(1234.567, decimals=2) == "1,234.57"
    assert format_number(float("nan")) == "N/A"
    assert format_number("invalid") == "N/A"
    assert format_number(None) == "N/A"


def test_safe_metric_value():
    assert safe_metric_value(100) == "100"
    assert safe_metric_value("text") == "text"
    assert safe_metric_value(None) == "N/A"
    assert safe_metric_value(float("nan")) == "N/A"
    assert safe_metric_value(None, fallback="Missing") == "Missing"


def test_select_metric_value():
    df = pd.DataFrame(
        [{"metric_name": "MRR", "value": 1000}, {"metric_name": "Churn", "value": 0.05}]
    )

    assert select_metric_value(df, "MRR") == 1000
    assert select_metric_value(df, "Churn") == 0.05
    assert select_metric_value(df, "Unknown") is None

    empty_df = pd.DataFrame()
    assert select_metric_value(empty_df, "MRR") is None

    bad_df = pd.DataFrame([{"wrong_col": 1}])
    assert select_metric_value(bad_df, "MRR") is None


def test_status_badge_text():
    assert status_badge_text("Healthy") == "🟢 Healthy"
    assert status_badge_text("healthy") == "🟢 Healthy"
    assert status_badge_text("Warning") == "🟡 Warning"
    assert status_badge_text("Critical") == "🔴 Critical"
    assert status_badge_text("Active") == "🟢 Active"
    assert status_badge_text("UnknownStatus") == "Unknownstatus"
    assert status_badge_text(None) == "Unknown"


def test_format_file_size():
    assert format_file_size(500) == "500.0 B"
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(1048576) == "1.0 MB"
    assert format_file_size(1073741824) == "1.0 GB"
    assert format_file_size(1099511627776) == "1.0 TB"
    assert format_file_size(None) == "Unknown"
    assert format_file_size("invalid") == "Unknown"


def test_format_timestamp():
    # Test a specific known timestamp (e.g., 2023-01-01 00:00:00 UTC = 1672531200)
    assert format_timestamp(1672531200) == "2023-01-01 00:00:00"
    assert format_timestamp(None) == "Unknown"
    assert format_timestamp("invalid") == "Unknown"


def test_format_duration():
    assert format_duration(30) == "<1 minute"
    assert format_duration(60) == "1 minute"
    assert format_duration(3600) == "1 hour"
    assert format_duration(86400) == "1 day"
    assert format_duration("invalid") == "Unknown"


def test_build_data_freshness_summary_statuses():
    now = 1_700_000_000

    fresh = build_data_freshness_summary(now - 3600, now_timestamp=now)
    aging = build_data_freshness_summary(now - 48 * 3600, now_timestamp=now)
    stale = build_data_freshness_summary(now - 96 * 3600, now_timestamp=now)
    missing = build_data_freshness_summary(None, now_timestamp=now)
    unknown = build_data_freshness_summary(float("nan"), now_timestamp=now)

    assert fresh["status"] == "🟢 Fresh"
    assert fresh["age"] == "1 hour"
    assert fresh["severity"] == "success"
    assert fresh["action"] == "Ready for review."
    assert aging["status"] == "🟡 Aging"
    assert aging["severity"] == "warning"
    assert stale["status"] == "🔴 Stale"
    assert stale["severity"] == "error"
    assert missing["status"] == "🔴 Missing"
    assert missing["action"] == "Run `make run`, then reload this page."
    assert unknown["status"] == "🔴 Unknown"


def test_db_status_label():
    assert db_status_label(True) == "🟢 Online"
    assert db_status_label(False) == "🔴 Missing"


def test_safe_dataframe_empty_message():
    assert (
        safe_dataframe_empty_message(None, "KPI")
        == "No KPI data source is available. Run `make run`, then reload this page."
    )
    assert (
        safe_dataframe_empty_message(pd.DataFrame(), "Health")
        == "No Health data available. Run `make run`, then reload this page if this is unexpected."
    )
    assert (
        safe_dataframe_empty_message(pd.DataFrame(), "Customer 360", filtered=True)
        == "No Customer 360 records match the current filters. Clear filters or search, then retry."
    )
    assert safe_dataframe_empty_message(pd.DataFrame({"a": [1]}), "Test") == ""


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


def test_summarize_filter_state():
    assert summarize_filter_state({"Priority": ["High"], "Owner": []}) == "Priority: High"
    assert summarize_filter_state({"Priority": []}) == "No filters applied"
    assert summarize_filter_state({"Priority": []}, empty_label="All rows") == "All rows"


def test_prepare_display_dataframe_formats_selected_columns():
    df = pd.DataFrame(
        [
            {
                "amount": 1234.5,
                "rate": 0.125,
                "status": "Critical",
                "score": 9.876,
            }
        ]
    )

    display = prepare_display_dataframe(
        df,
        currency_columns=["amount"],
        percentage_columns=["rate"],
        status_columns=["status"],
        number_columns=["score"],
    )

    assert display.iloc[0]["amount"] == "$1,234.50"
    assert display.iloc[0]["rate"] == "12.5%"
    assert display.iloc[0]["status"] == "🔴 Critical"
    assert display.iloc[0]["score"] == "9.88"
    assert prepare_display_dataframe(None).empty


def test_dataframe_to_csv_bytes():
    csv_bytes = dataframe_to_csv_bytes(pd.DataFrame({"a": [1], "b": ["x"]}))

    assert csv_bytes == b"a,b\n1,x\n"
    assert dataframe_to_csv_bytes(None) == b""


def test_build_export_filename():
    assert build_export_filename("Top Actions", timestamp=1672531200) == (
        "top-actions_20230101_000000.csv"
    )
    assert build_export_filename("  $$$  ") == "productpulse-export.csv"
    assert build_export_filename("Metric Lineage", timestamp="bad") == "metric-lineage_export.csv"


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


def test_build_custom_scenario_analysis_uses_dashboard_inputs():
    kpis = pd.DataFrame(
        [
            {"metric_name": "monthly_recurring_revenue", "value": 100_000.0},
            {"metric_name": "customer_churn_rate", "value": 0.05},
            {"metric_name": "activation_rate", "value": 0.20},
            {"metric_name": "average_revenue_per_user", "value": 50.0},
        ]
    )
    customers = pd.DataFrame(
        [
            {"customer_id": "C1", "current_mrr": 50.0},
            {"customer_id": "C2", "current_mrr": 0.0},
            {"customer_id": "C3", "current_mrr": 100.0},
        ]
    )
    leakages = pd.DataFrame(
        [
            {"leakage_type": "Failed Payment", "estimated_revenue_loss": 1_000.0},
            {"leakage_type": "Refund", "estimated_revenue_loss": 500.0},
        ]
    )

    scenarios = build_custom_scenario_analysis(
        kpis,
        customers,
        leakages,
        churn_improvement_rate=0.20,
        activation_improvement_rate=0.50,
        arpu_increase_rate=0.10,
        failed_payment_recovery_rate=0.25,
    )

    assert scenarios["scenario_name"].tolist() == [
        "Churn Reduction",
        "Activation Increase",
        "ARPU Increase",
        "Failed Payment Recovery",
    ]
    assert scenarios.loc[0, "monthly_impact"] == 1_000.0
    assert scenarios.loc[1, "monthly_impact"] == pytest.approx(15.0)
    assert scenarios.loc[2, "monthly_impact"] == pytest.approx(10.0)
    assert scenarios.loc[3, "monthly_impact"] == 250.0


def test_build_custom_scenario_analysis_returns_schema_without_inputs():
    scenarios = build_custom_scenario_analysis(
        None,
        None,
        None,
        churn_improvement_rate=0.10,
        activation_improvement_rate=0.10,
        arpu_increase_rate=0.05,
        failed_payment_recovery_rate=0.30,
    )

    assert scenarios.empty
    assert scenarios.columns.tolist() == [
        "scenario_name",
        "baseline_value",
        "simulated_value",
        "monthly_impact",
        "annualized_impact",
        "confidence_note",
    ]


def test_determine_business_status_prioritizes_worst_status():
    assert determine_business_status(pd.DataFrame({"status": ["Healthy", "Watch"]})) == "Watch"
    assert determine_business_status(pd.DataFrame({"status": ["Risk", "Healthy"]})) == "Risk"
    assert (
        determine_business_status(pd.DataFrame({"status": ["Critical", "Healthy"]})) == "Critical"
    )
    assert determine_business_status(pd.DataFrame({"status": ["Healthy", "Good"]})) == "Healthy"
    assert determine_business_status(pd.DataFrame()) == "Unknown"


def test_prepare_top_actions_sorts_by_priority_score():
    df = pd.DataFrame(
        [
            {
                "intervention_id": "IV-2",
                "recommendation_title": "B",
                "priority_score": 10,
                "priority_band": "Low",
            },
            {
                "intervention_id": "IV-1",
                "recommendation_title": "A",
                "priority_score": 50,
                "priority_band": "High",
            },
        ]
    )

    actions = prepare_top_actions(df, limit=1)

    assert len(actions) == 1
    assert actions.iloc[0]["intervention_id"] == "IV-1"


def test_prepare_top_actions_handles_empty_and_missing_score():
    assert prepare_top_actions(None).empty
    df = pd.DataFrame(
        [
            {"intervention_id": "IV-1", "recommendation_title": "A"},
            {"intervention_id": "IV-2", "recommendation_title": "B"},
        ]
    )

    actions = prepare_top_actions(df)

    assert actions["intervention_id"].tolist() == ["IV-1", "IV-2"]


def test_build_top_actions_overview_summarizes_current_queue():
    df = pd.DataFrame(
        [
            {
                "intervention_id": "IV-1",
                "priority_band": "Critical",
                "estimated_revenue_impact": 1000,
                "priority_score": 90,
                "effort_level": "Low",
                "suggested_owner": "Customer Success",
            },
            {
                "intervention_id": "IV-2",
                "priority_band": "High",
                "estimated_revenue_impact": 500,
                "priority_score": 60,
                "effort_level": "Medium",
                "suggested_owner": "Customer Success",
            },
            {
                "intervention_id": "IV-3",
                "priority_band": "Low",
                "estimated_revenue_impact": 100,
                "priority_score": 15,
                "effort_level": "Low",
                "suggested_owner": "Product",
            },
        ]
    )

    overview = build_top_actions_overview(df)

    assert overview["actions"] == 3
    assert overview["critical_high"] == 2
    assert overview["quick_wins"] == 2
    assert overview["owners"] == 2
    assert overview["impact_total"] == 1600.0
    assert overview["average_priority_score"] == pytest.approx(55.0)
    assert overview["top_owner"] == "Customer Success"


def test_build_top_actions_overview_handles_empty_and_unassigned_owner():
    assert build_top_actions_overview(None)["actions"] == 0

    overview = build_top_actions_overview(
        pd.DataFrame(
            [
                {"intervention_id": "IV-1", "priority_band": "Low", "suggested_owner": None},
                {"intervention_id": "IV-2", "priority_band": "Medium"},
            ]
        )
    )

    assert overview["critical_high"] == 0
    assert overview["owners"] == 0
    assert overview["top_owner"] == "Unassigned"


def test_prepare_action_priority_queue_sorts_by_score_impact_and_effort():
    df = pd.DataFrame(
        [
            {
                "intervention_id": "IV-2",
                "recommendation_title": "B",
                "priority_score": 80,
                "estimated_revenue_impact": 500,
                "effort_level": "Medium",
            },
            {
                "intervention_id": "IV-1",
                "recommendation_title": "A",
                "priority_score": 80,
                "estimated_revenue_impact": 500,
                "effort_level": "Low",
            },
            {
                "intervention_id": "IV-3",
                "recommendation_title": "C",
                "priority_score": 70,
                "estimated_revenue_impact": 1000,
                "effort_level": "Low",
            },
        ]
    )

    queue = prepare_action_priority_queue(df, limit=2)

    assert queue["intervention_id"].tolist() == ["IV-1", "IV-2"]
    assert queue.columns.tolist() == [
        "intervention_id",
        "recommendation_title",
        "estimated_revenue_impact",
        "priority_score",
        "effort_level",
    ]


def test_prepare_action_priority_queue_handles_empty_and_missing_id():
    assert prepare_action_priority_queue(None).empty

    queue = prepare_action_priority_queue(pd.DataFrame([{"priority_score": 10}]))

    assert queue["intervention_id"].tolist() == [""]
    assert queue["priority_score"].tolist() == [10]


def test_build_decision_brief_summarizes_intervention_view():
    df = pd.DataFrame(
        [
            {
                "intervention_id": "IV-1",
                "recommendation_title": "Executive save motion",
                "expected_action": "Schedule executive review.",
                "priority_band": "High",
                "estimated_revenue_impact": 1000.0,
                "priority_score": 90.0,
                "suggested_owner": "Customer Success",
            },
            {
                "intervention_id": "IV-2",
                "recommendation_title": "Monitor usage",
                "expected_action": "Track product activity.",
                "priority_band": "Low",
                "estimated_revenue_impact": 500.0,
                "priority_score": 10.0,
                "suggested_owner": "Product",
            },
        ]
    )

    brief = build_decision_brief(df, "Top Actions", "High Priority")

    assert brief["records"] == 2
    assert brief["impact_label"] == "Estimated Revenue Impact"
    assert brief["formatted_impact"] == "$1,500.00"
    assert brief["urgent_count"] == 1
    assert brief["top_actions"][0]["title"] == "Executive save motion"
    assert brief["top_actions"][0]["owner"] == "Customer Success"


def test_build_decision_brief_handles_customer_risk_view():
    df = pd.DataFrame(
        [
            {
                "customer_id": "C-001",
                "segment": "Enterprise",
                "churn_risk_band": "Critical",
                "revenue_at_risk": 400.0,
                "churn_risk_score": 0.95,
                "recommended_action": "Run retention call.",
            },
            {
                "customer_id": "C-002",
                "segment": "SMB",
                "churn_risk_band": "Low",
                "revenue_at_risk": 0.0,
                "churn_risk_score": 0.1,
                "recommended_action": "Monitor.",
            },
        ]
    )

    brief = build_decision_brief(df, "Customer 360", "Retention Focus")

    assert brief["records"] == 2
    assert brief["impact_label"] == "Revenue at Risk"
    assert brief["formatted_impact"] == "$400.00"
    assert brief["urgent_count"] == 1
    assert brief["top_actions"][0]["title"] == "C-001"
    assert brief["top_actions"][0]["action"] == "Run retention call."


def test_decision_brief_empty_and_markdown_export():
    brief = build_decision_brief(pd.DataFrame(), "Recommendations", "Revenue Risk")
    markdown = decision_brief_to_markdown(brief)

    assert brief["records"] == 0
    assert brief["top_actions"] == []
    assert "No rows match current decision view." in brief["summary"]
    assert "# Recommendations" in markdown
    assert "- Quick view: Revenue Risk" in markdown


def test_decision_brief_why_it_matters_variants_and_markdown_skip():
    impact_only = build_decision_brief(
        pd.DataFrame([{"recommendation_title": "A", "estimated_revenue_impact": 10}]),
        "Impact",
    )
    urgent_only = build_decision_brief(
        pd.DataFrame([{"recommendation_title": "B", "priority_band": "High"}]),
        "Urgent",
    )
    neutral = build_decision_brief(pd.DataFrame([{"recommendation_title": "C"}]), "Neutral")

    markdown = decision_brief_to_markdown(
        {
            "title": "Mixed",
            "quick_view": "All",
            "records": 1,
            "impact_label": "Impact",
            "formatted_impact": "$0.00",
            "urgent_count": 0,
            "summary": "Summary",
            "why_it_matters": "Why",
            "top_actions": ["bad-item", {"title": "Good", "action": "Act"}],
        }
    )

    assert "protect or capture" in impact_only["why_it_matters"]
    assert "clear urgent operational risk" in urgent_only["why_it_matters"]
    assert "assign owners" in neutral["why_it_matters"]
    assert "Good" in markdown
    assert "bad-item" not in markdown


def test_decision_brief_falls_back_for_blank_values_and_zero_sort_score():
    brief = build_decision_brief(
        pd.DataFrame(
            [
                {
                    "recommendation_title": "nan",
                    "recommended_action": "   ",
                    "suggested_owner": "none",
                    "priority_band": "<NA>",
                    "priority_score": 0,
                }
            ]
        ),
        "Fallbacks",
    )

    action = brief["top_actions"][0]
    assert action["title"] == "Record"
    assert action["action"] == "Review record details."
    assert action["owner"] == "Unassigned"
    assert action["status"] == "Unscored"


def test_prepare_owner_workload_summary_groups_and_sorts():
    df = pd.DataFrame(
        [
            {
                "suggested_owner": "Sales",
                "priority_band": "High",
                "estimated_revenue_impact": 100.0,
            },
            {
                "suggested_owner": "Success",
                "priority_band": "Critical",
                "estimated_revenue_impact": 300.0,
            },
            {
                "suggested_owner": "Sales",
                "priority_band": "Low",
                "estimated_revenue_impact": 50.0,
            },
        ]
    )

    summary = prepare_owner_workload_summary(df)

    assert summary["owner"].tolist() == ["Success", "Sales"]
    assert summary["records"].tolist() == [1, 2]
    assert summary["critical_high"].tolist() == [1, 1]
    assert summary["impact_total"].tolist() == [300.0, 150.0]


def test_prepare_owner_workload_summary_handles_missing_owner():
    assert prepare_owner_workload_summary(None).empty
    assert prepare_owner_workload_summary(pd.DataFrame()).empty
    assert prepare_owner_workload_summary(pd.DataFrame({"priority_band": ["High"]})).empty


def test_quality_status_for_score_uses_expected_bands():
    assert quality_status_for_score(0.95) == "Good"
    assert quality_status_for_score(0.8) == "Watch"
    assert quality_status_for_score(0.6) == "Risk"
    assert quality_status_for_score(0.4) == "Critical"
    assert quality_status_for_score("bad") == "Unknown"


def test_build_data_quality_overview_summarizes_scores():
    df = pd.DataFrame(
        [
            {
                "dataset": "customers",
                "completeness_score": 0.95,
                "uniqueness_score": 1.0,
                "validity_score": 0.9,
                "referential_integrity_score": 1.0,
                "overall_score": 0.9625,
                "status": "Good",
                "business_risk": "Low",
            },
            {
                "dataset": "subscriptions",
                "completeness_score": 0.7,
                "uniqueness_score": 0.8,
                "validity_score": 0.6,
                "referential_integrity_score": 0.4,
                "overall_score": 0.65,
                "status": "Risk",
                "business_risk": "High",
            },
        ]
    )

    overview = build_data_quality_overview(df)

    assert overview["datasets"] == 2
    assert overview["average_score_display"] == "80.6%"
    assert overview["needs_attention"] == 1
    assert overview["worst_status"] == "Risk"
    assert overview["lowest_dimension"] == "Referential Integrity"


def test_build_data_quality_overview_without_overall_or_status():
    df = pd.DataFrame(
        [
            {"dataset": "customers", "completeness_score": 0.8, "validity_score": 0.7},
            {"dataset": "subscriptions"},
        ]
    )

    overview = build_data_quality_overview(df)

    assert overview["datasets"] == 2
    assert overview["needs_attention"] == 2


def test_build_data_quality_overview_without_score_columns():
    overview = build_data_quality_overview(pd.DataFrame([{"dataset": "customers"}]))

    assert overview["lowest_dimension"] == "Unknown"
    assert overview["lowest_dimension_score"] == 0.0


def test_build_data_quality_overview_handles_empty_status_series_branch():
    class NonEmptyFrame(pd.DataFrame):
        @property
        def _constructor(self):
            return NonEmptyFrame

        @property
        def empty(self):
            return False

    overview = build_data_quality_overview(NonEmptyFrame(columns=["overall_score"]))

    assert overview["datasets"] == 0
    assert overview["worst_status"] == "Unknown"


def test_prepare_quality_dimension_summary_orders_lowest_first():
    df = pd.DataFrame(
        [
            {
                "completeness_score": 0.9,
                "uniqueness_score": 1.0,
                "validity_score": 0.7,
                "referential_integrity_score": 0.8,
            }
        ]
    )

    summary = prepare_quality_dimension_summary(df)

    assert summary["dimension"].tolist()[0] == "Validity"
    assert summary.iloc[0]["status"] == "Risk"


def test_prepare_quality_dimension_summary_skips_missing_and_invalid_columns():
    summary = prepare_quality_dimension_summary(
        pd.DataFrame([{"dataset": "customers", "completeness_score": "bad"}])
    )

    assert summary.empty


def test_prepare_quality_issue_queue_adds_weakest_dimension_and_sorts_risk():
    df = pd.DataFrame(
        [
            {
                "dataset": "customers",
                "completeness_score": 0.95,
                "uniqueness_score": 1.0,
                "validity_score": 0.9,
                "referential_integrity_score": 1.0,
                "overall_score": 0.96,
                "status": "Good",
                "business_risk": "Low",
            },
            {
                "dataset": "subscriptions",
                "completeness_score": 0.5,
                "uniqueness_score": 0.7,
                "validity_score": 0.6,
                "referential_integrity_score": 0.4,
                "overall_score": 0.55,
                "status": "Risk",
                "business_risk": "High",
            },
        ]
    )

    queue = prepare_quality_issue_queue(df)

    assert queue["dataset"].tolist() == ["subscriptions", "customers"]
    assert queue.iloc[0]["lowest_dimension"] == "Referential Integrity"
    assert queue.iloc[0]["lowest_dimension_score"] == 0.4


def test_prepare_quality_issue_queue_derives_missing_columns():
    queue = prepare_quality_issue_queue(
        pd.DataFrame(
            [
                {"dataset": "customers", "completeness_score": "bad"},
                {"dataset": "subscriptions", "validity_score": 0.8},
            ]
        )
    )

    assert queue.iloc[0]["dataset"] == "customers"
    assert queue.iloc[0]["status"] == "Critical"
    assert queue.iloc[0]["business_risk"] == ""


def test_quality_helpers_handle_missing_data():
    assert build_data_quality_overview(None)["datasets"] == 0
    assert prepare_quality_dimension_summary(None).empty
    assert prepare_quality_issue_queue(None).empty
    assert prepare_quality_issue_queue(pd.DataFrame({"status": ["Good"]})).empty


def test_filter_customer_360_handles_empty_and_optional_filters():
    df = pd.DataFrame([{"customer_id": "C1", "segment": "SMB"}])

    assert filter_customer_360(None).empty
    assert filter_customer_360(df)["customer_id"].tolist() == ["C1"]


def test_filter_customer_360_applies_common_filters():
    df = pd.DataFrame(
        [
            {"customer_id": "C1", "churn_risk_band": "High", "segment": "SMB", "plan": "Pro"},
            {
                "customer_id": "C2",
                "churn_risk_band": "Low",
                "segment": "Enterprise",
                "plan": "Basic",
            },
        ]
    )

    filtered = filter_customer_360(df, risk_bands=["High"], segments=["SMB"], plans=["Pro"])

    assert len(filtered) == 1
    assert filtered.iloc[0]["customer_id"] == "C1"


def test_build_customer_360_overview_summarizes_active_view():
    df = pd.DataFrame(
        [
            {
                "customer_id": "C1",
                "is_active": True,
                "churn_risk_band": "High",
                "current_mrr": 100,
                "revenue_at_risk": 100,
                "churn_risk_score": 0.8,
                "main_driver": "Low NPS",
            },
            {
                "customer_id": "C2",
                "is_active": False,
                "churn_risk_band": "Low",
                "current_mrr": 0,
                "revenue_at_risk": 0,
                "churn_risk_score": 0.1,
                "main_driver": "Low NPS",
            },
            {
                "customer_id": "C3",
                "is_active": "active",
                "churn_risk_band": "Critical",
                "current_mrr": 200,
                "revenue_at_risk": 150,
                "churn_risk_score": 0.9,
                "main_driver": "Failed Payments",
            },
        ]
    )

    overview = build_customer_360_overview(df)

    assert overview["customers"] == 3
    assert overview["active_customers"] == 2
    assert overview["high_risk_customers"] == 2
    assert overview["revenue_at_risk"] == 250.0
    assert overview["current_mrr"] == 300.0
    assert overview["average_risk_score"] == pytest.approx(0.6)
    assert overview["top_driver"] == "Low NPS"


def test_build_customer_360_overview_handles_empty_and_missing_columns():
    assert build_customer_360_overview(None)["customers"] == 0

    overview = build_customer_360_overview(
        pd.DataFrame(
            [
                {"customer_id": "C1", "current_mrr": 100, "main_driver": "Unknown"},
                {"customer_id": "C2", "current_mrr": 0, "main_driver": None},
            ]
        )
    )

    assert overview["active_customers"] == 1
    assert overview["high_risk_customers"] == 0
    assert overview["top_driver"] == "Unknown"

    missing_driver = build_customer_360_overview(pd.DataFrame([{"customer_id": "C1"}]))
    assert missing_driver["top_driver"] == "Unknown"


def test_prepare_customer_360_queue_sorts_and_limits_by_risk():
    df = pd.DataFrame(
        [
            {
                "customer_id": "C2",
                "churn_risk_band": "Low",
                "churn_risk_score": 0.1,
                "revenue_at_risk": 10,
                "current_mrr": 50,
            },
            {
                "customer_id": "C3",
                "churn_risk_band": "Critical",
                "churn_risk_score": 0.7,
                "revenue_at_risk": 50,
                "current_mrr": 100,
            },
            {
                "customer_id": "C1",
                "churn_risk_band": "High",
                "churn_risk_score": 0.9,
                "revenue_at_risk": 200,
                "current_mrr": 150,
            },
        ]
    )

    queue = prepare_customer_360_queue(df, limit=2)

    assert queue["customer_id"].tolist() == ["C3", "C1"]
    assert queue.columns.tolist() == [
        "customer_id",
        "churn_risk_band",
        "current_mrr",
        "revenue_at_risk",
        "churn_risk_score",
    ]


def test_prepare_customer_360_queue_handles_empty_and_missing_customer_id():
    assert prepare_customer_360_queue(None).empty

    queue = prepare_customer_360_queue(
        pd.DataFrame([{"churn_risk_band": "High", "revenue_at_risk": 25}])
    )

    assert queue["customer_id"].tolist() == [""]
    assert queue["revenue_at_risk"].tolist() == [25]


def test_build_customer_profile_summary_returns_display_fields():
    row = {
        "customer_id": "C1",
        "segment": "SMB",
        "plan": "Pro",
        "churn_risk_band": "High",
        "current_mrr": 199.0,
        "revenue_at_risk": 199.0,
        "usage_trend": "Declining",
        "recommended_action": "Call customer",
    }

    summary = build_customer_profile_summary(row)

    assert summary["Customer"] == "C1"
    assert summary["Revenue at Risk"] == 199.0
    assert summary["Recommended Action"] == "Call customer"


def test_prepare_display_dataframe_ignores_missing_requested_columns():
    df = pd.DataFrame([{"amount": 10}])

    display = prepare_display_dataframe(
        df,
        currency_columns=["missing_currency"],
        percentage_columns=["missing_percentage"],
        status_columns=["missing_status"],
        number_columns=["missing_number"],
    )

    assert display.equals(df)


def test_build_export_filename_handles_nan_timestamp():
    assert build_export_filename("Report", timestamp=float("nan")) == "report_export.csv"
