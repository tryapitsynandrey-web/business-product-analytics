"""
DataLoader — IO adapter for the ProductPulse analytics pipeline.

Responsibility:
    Read required CSV files from the configured synthetic data directory,
    enforce expected schema types on date columns, and surface clear
    errors if any dataset is missing.  No business logic lives here.
"""

import logging
from pathlib import Path
from typing import Dict, List

import pandas as pd

from utils.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)

# Date columns that must be parsed upon load, keyed by dataset name.
# This mapping lives here — not in the analytical core — because type
# enforcement on load is an IO concern.  It intentionally includes
# physical CSV columns (end_date, date_closed) that the validation
# config does not require, since they are produced by the synthetic
# data generator and must be parsed before downstream engines use them.
_DATE_COLUMNS: Dict[str, List[str]] = {
    "customers": ["signup_date"],
    "subscriptions": ["start_date", "end_date"],
    "transactions": ["transaction_date"],
    "product_usage": ["date"],
    "support_tickets": ["date_opened", "date_closed"],
    "nps_scores": ["date"],
    "targets": ["date"],
}


class DataLoader:
    """
    Loads all required SaaS datasets from CSV files.

    Parameters
    ----------
    data_dir : Path
        Directory that contains the CSV files to load.
        Defaults to <project_root>/data/synthetic.
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir: Path = (
            data_dir if data_dir is not None else PROJECT_ROOT / "data" / "synthetic"
        )

    def load_all(
        self,
        required_datasets: List[str] | None = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Load every required dataset from CSV into a dictionary of DataFrames.

        Parameters
        ----------
        required_datasets : list of str, optional
            Names of the datasets to load (without .csv extension).
            Defaults to the standard eight SaaS datasets.

        Returns
        -------
        dict of str -> pd.DataFrame

        Raises
        ------
        FileNotFoundError
            Raised immediately when a required file does not exist on disk.
        """
        if required_datasets is None:
            required_datasets = [
                "customers",
                "subscriptions",
                "transactions",
                "product_usage",
                "support_tickets",
                "nps_scores",
                "acquisition_channels",
                "targets",
            ]

        datasets: Dict[str, pd.DataFrame] = {}

        for name in required_datasets:
            path = self.data_dir / f"{name}.csv"

            if not path.exists():
                raise FileNotFoundError(
                    f"Required dataset '{name}' not found at: {path}. "
                    "Run the synthetic data generator first or check the configured "
                    "data path in config/config.yaml."
                )

            logger.debug("Loading dataset '%s' from %s", name, path)
            df = pd.read_csv(path)

            # Parse date columns so downstream engines receive proper dtypes.
            for col in _DATE_COLUMNS.get(name, []):
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")

            datasets[name] = df
            logger.debug("Loaded '%s': %d rows, %d columns.", name, len(df), len(df.columns))

        return datasets
