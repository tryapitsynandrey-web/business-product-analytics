import pytest
import pandas as pd
from adapters.data_writer import DataWriter


@pytest.fixture
def data_writer(tmp_path):
    return DataWriter(
        processed_dir=tmp_path / "processed",
        exports_dir=tmp_path / "exports",
        reports_dir=tmp_path / "reports",
    )


def test_validate_output_schema_passes_when_columns_exist(data_writer):
    df = pd.DataFrame({"a": [1], "b": [2]})
    # Should not raise
    data_writer.validate_output_schema(df, ["a", "b"], "test_artifact")


def test_validate_output_schema_allows_extra_by_default(data_writer):
    df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
    data_writer.validate_output_schema(df, ["a", "b"], "test_artifact")

    with pytest.raises(ValueError, match="Extra columns not allowed"):
        data_writer.validate_output_schema(df, ["a", "b"], "test_artifact", allow_extra=False)


def test_validate_output_schema_fails_when_column_missing(data_writer):
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError, match="Missing required columns"):
        data_writer.validate_output_schema(df, ["a", "b"], "test_artifact")


def test_validate_output_schema_dict_records(data_writer):
    records = [{"a": 1, "b": 2}]
    data_writer.validate_output_schema(records, ["a", "b"], "test_artifact")

    bad_records = [{"a": 1}]
    with pytest.raises(ValueError, match="Missing required columns"):
        data_writer.validate_output_schema(bad_records, ["a", "b"], "test_artifact")


def test_validate_output_schema_empty_records_safe(data_writer):
    # Should just return and not raise error for empty records
    data_writer.validate_output_schema([], ["a", "b"], "test_artifact")


def test_validate_output_schema_rejects_invalid_data_type(data_writer):
    with pytest.raises(ValueError, match="Data must be DataFrame or list of dicts"):
        data_writer.validate_output_schema({"a": 1}, ["a"], "test_artifact")


def test_validate_output_schema_disallows_extra_when_none_missing(data_writer):
    df = pd.DataFrame({"a": [1], "b": [2]})

    data_writer.validate_output_schema(df, ["a", "b"], "test_artifact", allow_extra=False)


def test_write_processed_and_exports_create_csv_files(data_writer):
    processed_df = pd.DataFrame({"metric_name": ["MRR"], "value": [100.0]})
    export_df = pd.DataFrame({"customer_id": ["C1"], "risk_score": [0.9]})

    data_writer.write_processed({"kpi_summary": processed_df})
    data_writer.write_exports({"churn_risk_profiles": export_df})

    processed_path = data_writer.processed_dir / "kpi_summary.csv"
    export_path = data_writer.exports_dir / "churn_risk_profiles.csv"
    assert processed_path.exists()
    assert export_path.exists()
    pd.testing.assert_frame_equal(pd.read_csv(processed_path), processed_df)
    pd.testing.assert_frame_equal(pd.read_csv(export_path), export_df)


def test_write_report_and_markdown_create_report_files(data_writer):
    data_writer.write_report("executive_summary.md", "# Summary")
    data_writer.write_markdown("risk_register.md", "# Risks")

    assert (data_writer.reports_dir / "executive_summary.md").read_text(
        encoding="utf-8"
    ) == "# Summary"
    assert (data_writer.reports_dir / "risk_register.md").read_text(encoding="utf-8") == "# Risks"


def test_write_dicts_as_csv_routes_to_requested_directory(data_writer):
    records = [{"intervention_id": "INT-1", "priority_band": "High"}]

    data_writer.write_dicts_as_csv("processed", records, "intervention_plan")
    data_writer.write_dicts_as_csv("exports", records, "intervention_plan_export")

    assert (data_writer.processed_dir / "intervention_plan.csv").exists()
    assert (data_writer.exports_dir / "intervention_plan_export.csv").exists()


def test_schema_validated_writers_persist_data(data_writer):
    df_path = data_writer.processed_dir / "validated_df.csv"
    records_path = data_writer.exports_dir / "validated_records.csv"
    df = pd.DataFrame({"a": [1], "b": [2]})
    records = [{"a": 3, "b": 4}]

    data_writer.write_dataframe_with_schema(df, df_path, ["a", "b"], "validated_df")
    data_writer.write_dicts_as_csv_with_schema(
        records,
        records_path,
        ["a", "b"],
        "validated_records",
    )

    pd.testing.assert_frame_equal(pd.read_csv(df_path), df)
    pd.testing.assert_frame_equal(pd.read_csv(records_path), pd.DataFrame(records))
