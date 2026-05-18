import pytest
import pandas as pd
from adapters.sqlite_writer import SQLiteWriter


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def writer(db_path):
    return SQLiteWriter(db_path)


def test_writer_creates_database_file(writer, db_path):
    df = pd.DataFrame({"a": [1, 2]})
    writer.write_dataframe("test_table", df)
    assert db_path.exists()


def test_writer_creates_table_from_dataframe(writer):
    df = pd.DataFrame({"col1": [1, 2], "col2": ["A", "B"]})
    writer.write_dataframe("test_table", df)

    assert writer.table_exists("test_table")


def test_writer_validates_required_columns(writer):
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError, match="missing required columns"):
        writer.write_dataframe("test_table", df, expected_columns=["a", "b"])


def test_writer_allows_extra_columns(writer):
    df = pd.DataFrame({"a": [1], "b": [2], "extra": [3]})
    writer.write_dataframe("test_table", df, expected_columns=["a", "b"])

    read_df = writer.read_table("test_table")
    assert "extra" in read_df.columns


def test_writer_raises_value_error_on_missing_required_columns(writer):
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError, match="missing required columns: \\['b'\\]"):
        writer.write_dataframe("test_table", df, expected_columns=["a", "b"])


def test_writer_lists_tables(writer):
    writer.write_dataframe("table1", pd.DataFrame({"a": [1]}))
    writer.write_dataframe("table2", pd.DataFrame({"a": [1]}))

    tables = writer.list_tables()
    assert set(tables) == {"table1", "table2"}


def test_writer_lists_no_tables_when_database_missing(db_path):
    writer = SQLiteWriter(db_path)

    assert writer.list_tables() == []


def test_writer_can_read_table_back_into_dataframe(writer):
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    writer.write_dataframe("test_table", df)

    read_df = writer.read_table("test_table")
    pd.testing.assert_frame_equal(df, read_df)


def test_writer_read_table_raises_for_missing_table(writer):
    with pytest.raises(ValueError, match="does not exist"):
        writer.read_table("missing_table")


def test_writer_replaces_table_deterministically(writer):
    df1 = pd.DataFrame({"a": [1]})
    writer.write_dataframe("test_table", df1)

    df2 = pd.DataFrame({"b": [2]})
    writer.write_dataframe("test_table", df2, if_exists="replace")

    read_df = writer.read_table("test_table")
    assert "b" in read_df.columns
    assert "a" not in read_df.columns


def test_artifact_to_table_writing_works_for_multiple_artifacts(writer):
    artifacts = {
        "kpi_summary": pd.DataFrame(
            {"metric_name": ["a"], "value": [1], "grain": ["b"], "explanation": ["c"]}
        ),
        "data_quality_scores": pd.DataFrame(
            {
                "dataset": ["a"],
                "completeness_score": [1],
                "uniqueness_score": [1],
                "validity_score": [1],
                "referential_integrity_score": [1],
                "overall_score": [1],
                "status": ["a"],
                "business_risk": ["b"],
            }
        ),
    }
    written = writer.write_artifacts(artifacts)
    assert len(written) == 2
    assert writer.table_exists("kpi_summary")
    assert writer.table_exists("data_quality_scores")


def test_writer_normalizes_table_names(writer):
    assert writer.normalize_table_name("KPI Summary-Daily") == "kpi_summary_daily"


def test_writer_appends_rows_when_requested(writer):
    writer.write_dataframe("events", pd.DataFrame({"id": [1]}))
    writer.write_dataframe("events", pd.DataFrame({"id": [2]}), if_exists="append")

    df = writer.read_table("events")
    assert df["id"].tolist() == [1, 2]


def test_writer_fail_mode_raises_when_table_exists(writer):
    writer.write_dataframe("events", pd.DataFrame({"id": [1]}))

    with pytest.raises(ValueError, match="already exists"):
        writer.write_dataframe("events", pd.DataFrame({"id": [2]}), if_exists="fail")
