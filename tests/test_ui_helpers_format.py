import pandas as pd
from app.ui_helpers_format import (
    format_currency,
    format_percentage,
    format_number,
    safe_metric_value,
    select_metric_value,
    status_badge_text,
    format_file_size,
    format_timestamp,
    format_duration,
    build_data_freshness_summary,
    build_demo_readiness_summary,
    db_status_label,
    safe_dataframe_empty_message,
    prepare_display_dataframe,
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


def test_build_demo_readiness_summary():
    missing = build_demo_readiness_summary(False)
    empty = build_demo_readiness_summary(True, table_count=0)
    ready = build_demo_readiness_summary(True, table_count=12, total_rows=3456)

    assert missing["status"] == "Setup needed"
    assert missing["severity"] == "error"
    assert missing["action"] == "Run `make reset-demo` to rebuild the deterministic demo snapshot."
    assert empty["status"] == "Needs refresh"
    assert empty["severity"] == "warning"
    assert ready["status"] == "Reviewer ready"
    assert ready["severity"] == "success"
    assert ready["summary"] == "12 table(s) and 3,456 row(s) are available."


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


def test_build_export_filename_handles_nan_timestamp():
    assert build_export_filename("Report", timestamp=float("nan")) == "report_export.csv"
