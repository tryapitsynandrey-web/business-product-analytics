import sqlite3
import pandas as pd
from pathlib import Path
from typing import List, Union

from models.schemas import SQLITE_ALLOWED_TABLES, SQLITE_UI_QUERY_TABLES

class SQLiteReader:
    """Safe, read-only adapter for SQLite persistence layer."""

    def __init__(self, db_path: Union[Path, str]):
        self.db_path = Path(db_path)
        if not self.db_path.exists() or not self.db_path.is_file():
            raise FileNotFoundError(f"SQLite database not found at {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get a read-only connection to the database. Does not create files."""
        # URI mode requires sqlite3 to be compiled with URI support, which is true in modern Python
        # Using uri=True and mode=ro ensures we do not create a file
        return sqlite3.connect(f"file:{self.db_path.absolute()}?mode=ro", uri=True)

    def _validate_table_name(self, table_name: str) -> None:
        """Validate table name against known allowed tables to prevent SQL injection."""
        if table_name not in SQLITE_ALLOWED_TABLES:
            raise ValueError(f"Unknown table name: {table_name}")

    def list_tables(self) -> List[str]:
        """List all tables present in the database."""
        query = "SELECT name FROM sqlite_master WHERE type='table';"
        with self._get_connection() as conn:
            cursor = conn.execute(query)
            tables = [row[0] for row in cursor.fetchall()]
        return tables

    def table_exists(self, table_name: str) -> bool:
        """Safely check if a table exists."""
        if table_name not in SQLITE_ALLOWED_TABLES:
            return False
        return table_name in self.list_tables()

    def get_table_row_count(self, table_name: str) -> int:
        """Get the number of rows in a table."""
        self._validate_table_name(table_name)
        if not self.table_exists(table_name):
            return 0
            
        query = f"SELECT COUNT(*) FROM {table_name}"
        with self._get_connection() as conn:
            cursor = conn.execute(query)
            return cursor.fetchone()[0]

    def read_table(self, table_name: str) -> pd.DataFrame:
        """Read an entire table into a pandas DataFrame."""
        self._validate_table_name(table_name)
        if not self.table_exists(table_name):
            return pd.DataFrame()
            
        query = f"SELECT * FROM {table_name}"
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def read_columns(self, table_name: str, columns: List[str]) -> pd.DataFrame:
        """Read specific columns from a table."""
        self._validate_table_name(table_name)
        if not self.table_exists(table_name):
            return pd.DataFrame()
            
        if not columns:
            raise ValueError("Columns list cannot be empty")
            
        # Ensure columns don't contain SQL injection vectors by checking against alphanumeric/underscores
        for col in columns:
            if not col.isidentifier():
                raise ValueError(f"Invalid column name: {col}")
                
        cols_str = ", ".join(columns)
        query = f"SELECT {cols_str} FROM {table_name}"
        
        with self._get_connection() as conn:
            # We can let SQLite catch missing columns natively, but we will catch the sqlite3.OperationalError
            try:
                return pd.read_sql_query(query, conn)
            except (sqlite3.OperationalError, pd.errors.DatabaseError) as e:
                raise ValueError(f"Failed to read columns: {e}")

    def read_top(self, table_name: str, limit: int = 10) -> pd.DataFrame:
        """Read top N rows from a table."""
        self._validate_table_name(table_name)
        if limit < 0:
            raise ValueError("Limit cannot be negative")
            
        if not self.table_exists(table_name):
            return pd.DataFrame()
            
        query = f"SELECT * FROM {table_name} LIMIT ?"
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn, params=(limit,))

    # ── UI Query Methods ──────────────────────────────────────────────────

    def get_kpi_summary(self) -> pd.DataFrame:
        return self.read_table("kpi_summary")

    def get_health_scores(self) -> pd.DataFrame:
        return self.read_table("health_scores")

    def get_customer_360(self) -> pd.DataFrame:
        return self.read_table("customer_360")

    def get_recommendations(self) -> pd.DataFrame:
        return self.read_table("recommendations")

    def get_intervention_plan(self) -> pd.DataFrame:
        return self.read_table("intervention_plan")

    def get_decision_traces(self) -> pd.DataFrame:
        return self.read_table("decision_traces")

    def get_metric_lineage(self) -> pd.DataFrame:
        return self.read_table("metric_lineage")

    def get_high_risk_customers(self) -> pd.DataFrame:
        """Return customers with High or Critical churn risk band."""
        if not self.table_exists("churn_risk_profiles"):
            return pd.DataFrame()
            
        query = "SELECT * FROM churn_risk_profiles WHERE risk_band IN ('High', 'Critical') ORDER BY risk_score DESC"
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def get_top_recommendations(self, limit: int = 10) -> pd.DataFrame:
        """Return top prioritized recommendations."""
        if limit < 0:
            raise ValueError("Limit cannot be negative")
            
        if not self.table_exists("recommendations"):
            return pd.DataFrame()
            
        query = "SELECT * FROM recommendations ORDER BY priority_score DESC LIMIT ?"
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn, params=(limit,))

    def get_critical_health_scores(self) -> pd.DataFrame:
        """Return health areas with Critical status."""
        if not self.table_exists("health_scores"):
            return pd.DataFrame()
            
        query = "SELECT * FROM health_scores WHERE status = 'Critical'"
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)
