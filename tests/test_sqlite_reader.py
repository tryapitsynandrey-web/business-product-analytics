import pandas as pd
import pytest
import sqlite3

from adapters.sqlite_reader import SQLiteReader
from adapters.sqlite_writer import SQLiteWriter


@pytest.fixture
def populated_db_path(tmp_path):
    """Fixture providing a populated SQLite database for testing."""
    db_path = tmp_path / "test.db"
    writer = SQLiteWriter(db_path)

    # Create some mock data
    kpi_data = pd.DataFrame(
        [
            {
                "metric_name": "MRR",
                "value": 10000.0,
                "grain": "monthly",
                "explanation": "Total MRR",
            },
            {
                "metric_name": "Churn Rate",
                "value": 0.05,
                "grain": "monthly",
                "explanation": "Monthly churn",
            },
        ]
    )

    health_data = pd.DataFrame(
        [
            {"area": "Usage", "score": 85, "status": "Healthy", "explanation": "High usage"},
            {"area": "Support", "score": 30, "status": "Critical", "explanation": "Many tickets"},
        ]
    )

    churn_risk_data = pd.DataFrame(
        [
            {
                "customer_id": "C001",
                "risk_score": 0.9,
                "risk_band": "Critical",
                "drivers": "x",
                "revenue_at_risk": 100.0,
                "explanation": "high risk",
            },
            {
                "customer_id": "C002",
                "risk_score": 0.2,
                "risk_band": "Low",
                "drivers": "y",
                "revenue_at_risk": 0.0,
                "explanation": "low risk",
            },
        ]
    )

    recommendations_data = pd.DataFrame(
        [
            {
                "rule_id": "R1",
                "recommendation_title": "Up-sell",
                "category": "Growth",
                "customer_id": "C1",
                "segment": "A",
                "reason": "X",
                "affected_customers": 1,
                "estimated_revenue_impact": 500,
                "impact_score": 0.8,
                "confidence_level": "High",
                "confidence_weight": 1.0,
                "suggested_owner": "Sales",
                "evidence_source": "Data",
                "priority_score": 90.0,
                "priority_band": "High",
            },
            {
                "rule_id": "R2",
                "recommendation_title": "Save",
                "category": "Retention",
                "customer_id": "C2",
                "segment": "B",
                "reason": "Y",
                "affected_customers": 1,
                "estimated_revenue_impact": 100,
                "impact_score": 0.4,
                "confidence_level": "Low",
                "confidence_weight": 0.5,
                "suggested_owner": "Support",
                "evidence_source": "Data",
                "priority_score": 20.0,
                "priority_band": "Low",
            },
        ]
    )

    writer.write_dataframe("kpi_summary", kpi_data)
    writer.write_dataframe("health_scores", health_data)
    writer.write_dataframe("churn_risk_profiles", churn_risk_data)
    writer.write_dataframe("recommendations", recommendations_data)

    # Also write empty tables for UI methods
    writer.write_dataframe(
        "customer_360",
        pd.DataFrame(
            columns=[
                "customer_id",
                "segment",
                "is_active",
                "signup_date",
                "country",
                "acquisition_channel",
                "plan",
                "subscription_status",
                "current_mrr",
                "total_revenue",
                "latest_usage_frequency",
                "usage_trend",
                "latest_nps",
                "support_ticket_count",
                "failed_payment_count",
                "churn_risk_score",
                "churn_risk_band",
                "revenue_at_risk",
                "main_driver",
                "recommended_action",
                "health_status",
                "revenue_segment",
                "usage_segment",
                "risk_segment",
                "nps_segment",
            ]
        ),
    )
    writer.write_dataframe(
        "intervention_plan",
        pd.DataFrame(
            columns=[
                "intervention_id",
                "recommendation_title",
                "category",
                "target_segment",
                "affected_customers",
                "estimated_revenue_impact",
                "expected_action",
                "suggested_owner",
                "confidence_level",
                "effort_level",
                "priority_score",
                "priority_band",
            ]
        ),
    )
    writer.write_dataframe(
        "decision_traces",
        pd.DataFrame(
            columns=[
                "trace_id",
                "created_at",
                "entity_type",
                "entity_id",
                "signal",
                "triggered_rule",
                "evidence",
                "business_impact",
                "generated_action",
                "confidence_level",
            ]
        ),
    )
    writer.write_dataframe(
        "metric_lineage",
        pd.DataFrame(
            columns=[
                "metric_name",
                "display_name",
                "category",
                "source_datasets",
                "required_columns",
                "formula_description",
                "business_owner",
                "business_purpose",
                "risk_if_misread",
                "lineage_status",
            ]
        ),
    )
    writer.write_dataframe(
        "scenario_analysis",
        pd.DataFrame(
            [
                {
                    "scenario_name": "Churn Reduction",
                    "baseline_value": 0.05,
                    "simulated_value": 0.045,
                    "monthly_impact": 500.0,
                    "annualized_impact": 6000.0,
                    "confidence_note": "Assumption",
                }
            ]
        ),
    )
    writer.write_dataframe(
        "cohort_summary",
        pd.DataFrame(
            [
                {
                    "cohort_month": "2026-01",
                    "period_number": 0,
                    "customers_in_cohort": 10,
                    "retained_customers": 9,
                    "retention_rate": 0.9,
                    "revenue": 1000.0,
                    "revenue_per_customer": 100.0,
                }
            ]
        ),
    )
    writer.write_dataframe(
        "funnel_summary",
        pd.DataFrame(
            [
                {
                    "step": "Signup",
                    "users": 10,
                    "conversion_rate": 1.0,
                    "dropoff_rate": 0.0,
                    "previous_step_users": 10,
                }
            ]
        ),
    )
    writer.write_dataframe(
        "segment_funnel",
        pd.DataFrame(
            [
                {
                    "segment": "SMB",
                    "step": "Signup",
                    "users": 10,
                    "conversion_rate": 1.0,
                    "dropoff_rate": 0.0,
                    "previous_step_users": 10,
                }
            ]
        ),
    )

    return db_path


@pytest.fixture
def empty_db_path(tmp_path):
    db_path = tmp_path / "empty.db"
    with sqlite3.connect(db_path):
        pass
    return db_path


def test_reader_raises_file_not_found_for_missing_db(tmp_path):
    missing_db = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        SQLiteReader(missing_db)


def test_reader_lists_tables(populated_db_path):
    reader = SQLiteReader(populated_db_path)
    tables = reader.list_tables()
    assert "kpi_summary" in tables
    assert "health_scores" in tables


def test_reader_detects_existing_table(populated_db_path):
    reader = SQLiteReader(populated_db_path)
    assert reader.table_exists("kpi_summary") is True


def test_reader_returns_false_for_missing_table_safely(populated_db_path):
    reader = SQLiteReader(populated_db_path)
    assert reader.table_exists("revenue_leakage") is False
    assert reader.table_exists("unknown_table_not_in_schema") is False


def test_reader_reads_full_table(populated_db_path):
    reader = SQLiteReader(populated_db_path)
    df = reader.read_table("kpi_summary")
    assert not df.empty
    assert len(df) == 2
    assert list(df.columns) == ["metric_name", "value", "grain", "explanation"]


def test_reader_returns_empty_for_allowed_missing_tables(empty_db_path):
    reader = SQLiteReader(empty_db_path)

    assert reader.read_table("kpi_summary").empty
    assert reader.read_columns("kpi_summary", ["metric_name"]).empty
    assert reader.read_top("kpi_summary").empty
    assert reader.get_high_risk_customers().empty
    assert reader.get_top_recommendations().empty
    assert reader.get_critical_health_scores().empty


def test_reader_rejects_empty_column_list_when_table_exists(populated_db_path):
    reader = SQLiteReader(populated_db_path)

    with pytest.raises(ValueError, match="Columns list cannot be empty"):
        reader.read_columns("kpi_summary", [])


def test_reader_reads_selected_columns(populated_db_path):
    reader = SQLiteReader(populated_db_path)
    df = reader.read_columns("kpi_summary", ["metric_name", "value"])
    assert not df.empty
    assert list(df.columns) == ["metric_name", "value"]


def test_reader_raises_error_for_unknown_table(populated_db_path):
    reader = SQLiteReader(populated_db_path)
    with pytest.raises(ValueError, match="Unknown table name"):
        reader.read_table("invalid_table_name")


def test_reader_raises_error_for_unknown_column(populated_db_path):
    reader = SQLiteReader(populated_db_path)
    with pytest.raises(ValueError, match="Failed to read columns"):
        reader.read_columns("kpi_summary", ["metric_name", "non_existent_column"])


def test_reader_raises_error_for_invalid_column_name(populated_db_path):
    reader = SQLiteReader(populated_db_path)
    with pytest.raises(ValueError, match="Invalid column name"):
        reader.read_columns("kpi_summary", ["metric_name; DROP TABLE kpi_summary;"])


def test_reader_reads_top_n_rows(populated_db_path):
    reader = SQLiteReader(populated_db_path)
    df = reader.read_top("kpi_summary", limit=1)
    assert len(df) == 1


def test_reader_handles_invalid_limit(populated_db_path):
    reader = SQLiteReader(populated_db_path)
    with pytest.raises(ValueError, match="Limit cannot be negative"):
        reader.read_top("kpi_summary", limit=-5)


def test_row_count_works(populated_db_path):
    reader = SQLiteReader(populated_db_path)
    count = reader.get_table_row_count("kpi_summary")
    assert count == 2

    empty_count = reader.get_table_row_count("revenue_leakage")
    assert empty_count == 0


def test_ui_ready_methods_return_dataframes(populated_db_path):
    reader = SQLiteReader(populated_db_path)

    assert isinstance(reader.get_kpi_summary(), pd.DataFrame)
    assert isinstance(reader.get_health_scores(), pd.DataFrame)
    assert isinstance(reader.get_customer_360(), pd.DataFrame)
    assert isinstance(reader.get_recommendations(), pd.DataFrame)
    assert isinstance(reader.get_intervention_plan(), pd.DataFrame)
    assert isinstance(reader.get_scenario_analysis(), pd.DataFrame)
    assert isinstance(reader.get_cohort_summary(), pd.DataFrame)
    assert isinstance(reader.get_funnel_summary(), pd.DataFrame)
    assert isinstance(reader.get_segment_funnel(), pd.DataFrame)
    assert isinstance(reader.get_decision_traces(), pd.DataFrame)
    assert isinstance(reader.get_metric_lineage(), pd.DataFrame)


def test_high_risk_customers_query(populated_db_path):
    reader = SQLiteReader(populated_db_path)
    df = reader.get_high_risk_customers()
    assert len(df) == 1
    assert df.iloc[0]["customer_id"] == "C001"
    assert df.iloc[0]["risk_band"] == "Critical"


def test_top_recommendations_query(populated_db_path):
    reader = SQLiteReader(populated_db_path)
    df = reader.get_top_recommendations(limit=1)
    assert len(df) == 1
    assert df.iloc[0]["rule_id"] == "R1"
    assert df.iloc[0]["priority_score"] == 90.0


def test_top_recommendations_rejects_negative_limit(populated_db_path):
    reader = SQLiteReader(populated_db_path)

    with pytest.raises(ValueError, match="Limit cannot be negative"):
        reader.get_top_recommendations(limit=-1)


def test_critical_health_scores_query(populated_db_path):
    reader = SQLiteReader(populated_db_path)
    df = reader.get_critical_health_scores()
    assert len(df) == 1
    assert df.iloc[0]["area"] == "Support"
