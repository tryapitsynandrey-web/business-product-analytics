"""
DataQualityScorer — per-dataset data quality scoring.

Responsibility:
    Consume ValidationResult issues and live DataFrames to score each dataset
    across four quality dimensions.  Produces a structured quality summary
    that the report generator and pipeline can consume.

Dimensions:
    completeness  — fraction of non-null values in all columns
    uniqueness    — absence of duplicate primary-key values
    validity      — absence of out-of-range / disallowed-value issues
    referential_integrity — absence of orphan FK references

Status bands  (derived from overall_score):
    Good     ≥ 0.90
    Watch    ≥ 0.75
    Risk     ≥ 0.50
    Critical <  0.50
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from utils.validation import ValidationIssue

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Status thresholds
# ---------------------------------------------------------------------------

_GOOD_THRESHOLD: float = 0.90
_WATCH_THRESHOLD: float = 0.75
_RISK_THRESHOLD: float = 0.50

_BUSINESS_RISK = {
    "Good": "Low — dataset meets quality standards.",
    "Watch": "Medium — some issues present; monitor closely before using in decisions.",
    "Risk": "High — notable quality issues; downstream KPIs may be unreliable.",
    "Critical": "Critical — dataset has severe quality problems; do not use in executive reporting.",
}

# Issue check names that map to each quality dimension
_VALIDITY_CHECKS = {
    "allowed_values",
    "numeric_non_negative",
    "nps_range",
    "nps_score_range",
    "date_columns",
    "date_format",
}
_UNIQUENESS_CHECKS = {"no_duplicate_keys", "no_duplicate_primary_keys"}
_INTEGRITY_CHECKS = {"referential_integrity"}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class DatasetQualityScore:
    """Quality score record for a single dataset."""
    dataset: str
    completeness_score: float
    uniqueness_score: float
    validity_score: float
    referential_integrity_score: float
    overall_score: float
    status: str
    business_risk: str


# ---------------------------------------------------------------------------
# Scorer class
# ---------------------------------------------------------------------------

class DataQualityScorer:
    """
    Scores every dataset in the pipeline against four quality dimensions.

    Parameters
    ----------
    issues : list of ValidationIssue
        All issues collected by the validation pass.
    datasets : dict
        Loaded DataFrames keyed by dataset name.
    primary_keys : dict, optional
        Maps dataset name → primary key column name.  Used for uniqueness scoring.
    """

    def __init__(
        self,
        issues: List[ValidationIssue],
        datasets: Dict[str, pd.DataFrame],
        primary_keys: Dict[str, str] | None = None,
    ) -> None:
        self._issues = issues
        self._datasets = datasets
        self._primary_keys: Dict[str, str] = primary_keys or {}

    # ------------------------------------------------------------------
    # Dimension scorers
    # ------------------------------------------------------------------

    def calculate_completeness_score(self, dataset_name: str) -> float:
        """
        Fraction of non-null cells across all columns.

        Returns 1.0 for empty DataFrames (nothing to be null).
        """
        df = self._datasets.get(dataset_name)
        if df is None or df.empty:
            return 1.0
        total_cells = df.size
        if total_cells == 0:
            return 1.0
        null_cells = int(df.isnull().sum().sum())
        return max(0.0, 1.0 - null_cells / total_cells)

    def calculate_uniqueness_score(self, dataset_name: str) -> float:
        """
        1.0 if no duplicate-key issues were recorded for this dataset.
        Falls back to checking the DataFrame directly if a primary key is known.
        """
        df = self._datasets.get(dataset_name)
        pk_col = self._primary_keys.get(dataset_name)

        if df is None or df.empty:
            return 1.0

        # If a primary key column is known, compute directly
        if pk_col and pk_col in df.columns:
            total = len(df)
            unique = df[pk_col].nunique()
            return 1.0 if total == 0 else unique / total

        # Otherwise fall back to validation issues
        duplicates_flagged = any(
            i.dataset == dataset_name and i.check_name in _UNIQUENESS_CHECKS
            for i in self._issues
        )
        return 0.0 if duplicates_flagged else 1.0

    def calculate_validity_score(self, dataset_name: str) -> float:
        """
        1.0 minus the proportion of validity-check issues for this dataset.
        Treats each flagged issue as one validity failure; score floored at 0.
        """
        validity_issues = [
            i for i in self._issues
            if i.dataset == dataset_name and i.check_name in _VALIDITY_CHECKS
            and i.severity == "error"
        ]
        if not validity_issues:
            return 1.0
        # Each issue deducts 0.10; minimum is 0.0
        penalty = min(1.0, len(validity_issues) * 0.10)
        return max(0.0, 1.0 - penalty)

    def calculate_referential_integrity_score(self, dataset_name: str) -> float:
        """
        1.0 if no referential integrity issues were recorded for this dataset.
        Penalties are applied per issue.
        """
        ri_issues = [
            i for i in self._issues
            if i.dataset == dataset_name and i.check_name in _INTEGRITY_CHECKS
            and i.severity == "error"
        ]
        if not ri_issues:
            return 1.0
        penalty = min(1.0, len(ri_issues) * 0.15)
        return max(0.0, 1.0 - penalty)

    # ------------------------------------------------------------------
    # Dataset-level aggregation
    # ------------------------------------------------------------------

    def calculate_dataset_quality_score(self, dataset_name: str) -> DatasetQualityScore:
        """
        Compute the four dimension scores and derive the overall_score and status
        for a single dataset.

        Overall = equal-weight average of the four dimensions.
        """
        completeness = self.calculate_completeness_score(dataset_name)
        uniqueness = self.calculate_uniqueness_score(dataset_name)
        validity = self.calculate_validity_score(dataset_name)
        ri = self.calculate_referential_integrity_score(dataset_name)

        overall = (completeness + uniqueness + validity + ri) / 4.0

        if overall >= _GOOD_THRESHOLD:
            status = "Good"
        elif overall >= _WATCH_THRESHOLD:
            status = "Watch"
        elif overall >= _RISK_THRESHOLD:
            status = "Risk"
        else:
            status = "Critical"

        return DatasetQualityScore(
            dataset=dataset_name,
            completeness_score=round(completeness, 4),
            uniqueness_score=round(uniqueness, 4),
            validity_score=round(validity, 4),
            referential_integrity_score=round(ri, 4),
            overall_score=round(overall, 4),
            status=status,
            business_risk=_BUSINESS_RISK[status],
        )

    # ------------------------------------------------------------------
    # Summary generator
    # ------------------------------------------------------------------

    def generate_quality_summary(self) -> List[DatasetQualityScore]:
        """
        Run calculate_dataset_quality_score for every loaded dataset and return
        a list of DatasetQualityScore records.
        """
        scores: List[DatasetQualityScore] = []
        for name in sorted(self._datasets.keys()):
            score = self.calculate_dataset_quality_score(name)
            scores.append(score)
            logger.info(
                "Data quality  %-25s overall=%.2f  status=%s",
                name, score.overall_score, score.status,
            )
        return scores
