"""
DataWriter — IO adapter for the ProductPulse analytics pipeline.

Responsibility:
    Persist processed DataFrames and markdown report text to disk.
    Guarantees that target directories exist before writing.
    Contains no analytical logic.
"""

import logging
from pathlib import Path
from typing import Dict

import pandas as pd

from utils.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)


class DataWriter:
    """
    Writes pipeline outputs to the processed and exports directories.

    Parameters
    ----------
    processed_dir : Path, optional
        Target directory for processed CSV outputs.
        Defaults to <project_root>/data/processed.
    exports_dir : Path, optional
        Target directory for export artifact CSVs.
        Defaults to <project_root>/data/exports.
    reports_dir : Path, optional
        Target directory for markdown reports.
        Defaults to <project_root>/reports.
    """

    def __init__(
        self,
        processed_dir: Path | None = None,
        exports_dir: Path | None = None,
        reports_dir: Path | None = None,
    ) -> None:
        self.processed_dir: Path = (
            processed_dir if processed_dir is not None
            else PROJECT_ROOT / "data" / "processed"
        )
        self.exports_dir: Path = (
            exports_dir if exports_dir is not None
            else PROJECT_ROOT / "data" / "exports"
        )
        self.reports_dir: Path = (
            reports_dir if reports_dir is not None
            else PROJECT_ROOT / "reports"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_dir(self, directory: Path) -> None:
        """Create the directory and any missing parents if not already present."""
        directory.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public write methods
    # ------------------------------------------------------------------

    def write_processed(self, dataframes: Dict[str, pd.DataFrame]) -> None:
        """
        Write each DataFrame in `dataframes` to data/processed/ as a CSV.

        Parameters
        ----------
        dataframes : dict of str -> DataFrame
            Key is used as the filename stem (e.g. 'kpi_summary' → kpi_summary.csv).
        """
        self._ensure_dir(self.processed_dir)

        for name, df in dataframes.items():
            path = self.processed_dir / f"{name}.csv"
            df.to_csv(path, index=False)
            logger.debug("Written processed output '%s' to %s", name, path)

    def write_exports(self, dataframes: Dict[str, pd.DataFrame]) -> None:
        """
        Write each DataFrame to data/exports/ as a CSV.

        Intended for stakeholder-facing export artifacts.

        Parameters
        ----------
        dataframes : dict of str -> DataFrame
        """
        self._ensure_dir(self.exports_dir)

        for name, df in dataframes.items():
            path = self.exports_dir / f"{name}.csv"
            df.to_csv(path, index=False)
            logger.debug("Written export artifact '%s' to %s", name, path)

    def write_report(self, filename: str, content: str) -> None:
        """
        Write a markdown report string to the reports directory.

        Parameters
        ----------
        filename : str
            Filename including extension, e.g. 'executive_summary.md'.
        content : str
            Full markdown text to write.
        """
        self._ensure_dir(self.reports_dir)

        path = self.reports_dir / filename
        path.write_text(content, encoding="utf-8")
        logger.debug("Written report '%s' to %s", filename, path)

    def write_markdown(self, filename: str, content: str) -> None:
        """Alias for write_report — accepts a filename and raw markdown string."""
        self.write_report(filename, content)

    def write_dicts_as_csv(
        self,
        target: str,
        records: list,
        filename: str,
    ) -> None:
        """
        Write a list of dicts to CSV in the specified target directory.

        Parameters
        ----------
        target : str
            One of 'processed', 'exports'.
        records : list of dict
            Data to write.  An empty list produces an empty CSV.
        filename : str
            Filename stem (without extension), e.g. 'intervention_plan'.
        """
        directory = self.processed_dir if target == "processed" else self.exports_dir
        self._ensure_dir(directory)

        df = pd.DataFrame(records)
        path = directory / f"{filename}.csv"
        df.to_csv(path, index=False)
        logger.debug("Written dict-list CSV '%s' to %s", filename, path)

    def validate_output_schema(self, data: pd.DataFrame | list, expected_columns: list, artifact_name: str, allow_extra: bool = True) -> None:
        """Validate output data matches the expected column schema."""
        if isinstance(data, pd.DataFrame):
            cols = data.columns.tolist()
        elif isinstance(data, list):
            if not data:
                return
            cols = list(data[0].keys())
        else:
            raise ValueError(f"Data must be DataFrame or list of dicts. Got {type(data)}")
            
        missing = [c for c in expected_columns if c not in cols]
        if missing:
            raise ValueError(f"Output schema validation failed for '{artifact_name}'. Missing required columns: {missing}")
            
        if not allow_extra:
            extra = [c for c in cols if c not in expected_columns]
            if extra:
                raise ValueError(f"Output schema validation failed for '{artifact_name}'. Extra columns not allowed: {extra}")

    def write_dataframe_with_schema(self, df: pd.DataFrame, path: Path | str, expected_columns: list, artifact_name: str, allow_extra: bool = True) -> None:
        """Validate dataframe schema and write to disk."""
        self.validate_output_schema(df, expected_columns, artifact_name, allow_extra=allow_extra)
        
        filepath = Path(path)
        self._ensure_dir(filepath.parent)
        df.to_csv(filepath, index=False)
        logger.debug("Written schema-validated DataFrame '%s' to %s", artifact_name, filepath)

    def write_dicts_as_csv_with_schema(self, records: list, path: Path | str, expected_columns: list, artifact_name: str, allow_extra: bool = True) -> None:
        """Validate dict records schema and write to disk."""
        self.validate_output_schema(records, expected_columns, artifact_name, allow_extra=allow_extra)
        
        filepath = Path(path)
        self._ensure_dir(filepath.parent)
        df = pd.DataFrame(records)
        df.to_csv(filepath, index=False)
        logger.debug("Written schema-validated dict-list '%s' to %s", artifact_name, filepath)
