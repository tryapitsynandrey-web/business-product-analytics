import pytest
import pandas as pd
from pathlib import Path
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
