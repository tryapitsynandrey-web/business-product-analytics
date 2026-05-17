import pandas as pd
from app.ui_helpers import (
    format_currency,
    format_number,
    format_percentage,
    safe_metric_value,
    select_metric_value,
    status_badge_text,
    format_file_size,
    format_timestamp,
    db_status_label,
    safe_dataframe_empty_message,
    get_filter_options,
    filter_dataframe_by_values,
    filter_dataframe_by_search,
    filter_dataframe_by_numeric_range,
    prepare_metric_chart_data,
    prepare_status_counts,
    prepare_category_counts,
    prepare_display_dataframe,
    get_executive_metric_values,
    determine_business_status,
    prepare_top_actions,
    filter_customer_360,
    build_customer_profile_summary,
    summarize_filter_state,
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
    assert format_file_size(None) == "Unknown"
    assert format_file_size("invalid") == "Unknown"


def test_format_timestamp():
    # Test a specific known timestamp (e.g., 2023-01-01 00:00:00 UTC = 1672531200)
    assert format_timestamp(1672531200) == "2023-01-01 00:00:00"
    assert format_timestamp(None) == "Unknown"
    assert format_timestamp("invalid") == "Unknown"


def test_db_status_label():
    assert db_status_label(True) == "🟢 Online"
    assert db_status_label(False) == "🔴 Missing"


def test_safe_dataframe_empty_message():
    assert safe_dataframe_empty_message(None, "KPI") == "No KPI data available."
    assert safe_dataframe_empty_message(pd.DataFrame(), "Health") == "No Health data available."
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


def test_prepare_metric_chart_data():
    df = pd.DataFrame({"metric_name": ["A", "B", "C"], "value": [10.5, "invalid", 20]})

    chart_data = prepare_metric_chart_data(df, "metric_name", "value")
    assert len(chart_data) == 2
    assert "B" not in chart_data.index
    assert chart_data.loc["A", "value"] == 10.5

    assert prepare_metric_chart_data(None).empty
    assert prepare_metric_chart_data(df, "missing_col").empty


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


def test_determine_business_status_prioritizes_worst_status():
    assert determine_business_status(pd.DataFrame({"status": ["Healthy", "Watch"]})) == "Watch"
    assert determine_business_status(pd.DataFrame({"status": ["Risk", "Healthy"]})) == "Risk"
    assert (
        determine_business_status(pd.DataFrame({"status": ["Critical", "Healthy"]})) == "Critical"
    )
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
