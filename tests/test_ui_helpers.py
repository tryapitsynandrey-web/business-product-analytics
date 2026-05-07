import pandas as pd
import pytest
from app.ui_helpers import (
    format_currency,
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
    filter_dataframe_by_numeric_range,
    prepare_metric_chart_data,
    prepare_status_counts,
    prepare_category_counts
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

def test_safe_metric_value():
    assert safe_metric_value(100) == "100"
    assert safe_metric_value("text") == "text"
    assert safe_metric_value(None) == "N/A"
    assert safe_metric_value(float('nan')) == "N/A"
    assert safe_metric_value(None, fallback="Missing") == "Missing"

def test_select_metric_value():
    df = pd.DataFrame([
        {"metric_name": "MRR", "value": 1000},
        {"metric_name": "Churn", "value": 0.05}
    ])
    
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
    df = pd.DataFrame({
        "metric_name": ["A", "B", "C"],
        "value": [10.5, "invalid", 20]
    })
    
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
