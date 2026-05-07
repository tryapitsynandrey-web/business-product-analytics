import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from models.schemas import OUTPUT_SCHEMAS

logger = logging.getLogger(__name__)

class SQLiteWriter:
    """
    Adapter for writing schema-validated pandas DataFrames to a local SQLite database.
    """

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def write_dataframe(
        self,
        table_name: str,
        df: pd.DataFrame,
        expected_columns: Optional[List[str]] = None,
        if_exists: str = "replace",
    ) -> None:
        """
        Write a single DataFrame to a SQLite table.

        Validates required columns against `expected_columns` if provided.
        Allows extra columns for forward compatibility.
        """
        if expected_columns:
            missing_columns = [col for col in expected_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(
                    f"DataFrame for table '{table_name}' is missing required columns: {missing_columns}"
                )

        try:
            with sqlite3.connect(self.db_path) as conn:
                df.to_sql(name=table_name, con=conn, if_exists=if_exists, index=False)
                logger.info("Wrote %d rows to SQLite table '%s'", len(df), table_name)
        except Exception as e:
            logger.error("Failed to write table '%s' to SQLite: %s", table_name, e)
            raise

    def write_artifacts(self, artifacts: Dict[str, pd.DataFrame], if_exists: str = "replace") -> List[str]:
        """
        Write a dictionary of artifact DataFrames to SQLite.

        Parameters
        ----------
        artifacts : dict
            Dictionary mapping artifact names to DataFrames.
        if_exists : str
            Behavior if the table exists ("replace", "append", "fail").

        Returns
        -------
        list of str
            Names of the tables successfully written.
        """
        written_tables = []
        for artifact_name, df in artifacts.items():
            table_name = self.normalize_table_name(artifact_name)
            expected_columns = OUTPUT_SCHEMAS.get(artifact_name)
            self.write_dataframe(table_name, df, expected_columns=expected_columns, if_exists=if_exists)
            written_tables.append(table_name)
        return written_tables

    def list_tables(self) -> List[str]:
        """Return a list of all table names in the database."""
        if not self.db_path.exists():
            return []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
        return tables

    def read_table(self, table_name: str) -> pd.DataFrame:
        """Read a table from the database into a DataFrame."""
        if not self.table_exists(table_name):
            raise ValueError(f"Table '{table_name}' does not exist in {self.db_path}")
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", con=conn)
        return df

    def table_exists(self, table_name: str) -> bool:
        """Check if a specific table exists."""
        return table_name in self.list_tables()

    def normalize_table_name(self, artifact_name: str) -> str:
        """
        Normalize artifact names to safe SQLite table names.
        Currently just returns the artifact name directly, but handles edge cases if needed.
        """
        return artifact_name.replace(" ", "_").replace("-", "_").lower()
